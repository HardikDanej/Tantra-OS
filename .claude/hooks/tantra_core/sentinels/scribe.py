"""
scribe.py -- Tantra Scribe: the step ledger and the Run Brief.

Why it exists: Tantra orchestrators re-dispatch agents (Step 7's revision
loop, a stalled background child, a follow-up after compaction). Without a
record, every re-dispatch starts from zero and re-does work that already
finished, and after a compaction the orchestrator re-reads history to find
out what happened. Scribe keeps the record the harness guarantees (hooks
fire whether or not the model remembers to log) and hands it back at the two
moments it saves tokens:

  * SubagentStart of a re-dispatch -> a Run Brief: the earlier run's final
    response (head + tail) so this run continues it. A re-dispatch is
    recognised only by the identical prompt or the orchestrators'
    "redispatch" marker (recorded from the parent's PreToolUse(Agent)); a
    new task for the same agent type, or a parallel fan-out sibling, gets
    nothing, because another task's output would mislead it.
  * SessionStart after compact/resume -> a compact state brief: dispatches,
    pending approval gates, last checkpoint, saved outputs.

It also adds a depth note when an agent starts at Claude Code's spawn-depth
limit (the Agent tool is withheld there, so dispatches from it would fail),
and at Stop (workspace scope) writes one summary line per turn with activity
to <workspace>/memory/sentinel_runs.jsonl for trigger_registry.py and
observability_report.py.

The ledger is always written, whatever the mode; mode only governs the
injected briefs. DEFAULTS below are overridable under "scribe" in
~/.tantra/config.json.
"""
import os
import re
import time
from collections import Counter, defaultdict

from .. import state
from . import common

DEFAULTS = {
    "mode": "assist",
    "brief_chars": 3500,
    "output_cap": 20000,
    "depth_limit": 3,
    "compaction_brief_chars": 3000,
    "summary_dispatch_list_cap": 50,
    "launch_window_s": 120,
}


# ---- PreToolUse(Agent), parent side: what is about to be dispatched ---------
# The orchestrators' dispatch contract carries "redispatch": {"cycle_id": ...,
# "attempt": N, "of": M} on a Step 7 re-dispatch and "redispatch": null on a
# first dispatch; that marker is how a re-dispatch is told from a new task.
REDISPATCH_RE = re.compile(
    r"""["']?redispatch["']?\s*[:=]\s*\{[^{}]*?["']?cycle_id["']?\s*[:=]\s*["']?([^"',}\s]+)""",
    re.IGNORECASE,
)


def on_launch(ctx):
    """Record the dispatch (prompt fingerprint, parent, re-dispatch marker).

    SubagentStart carries no prompt, so this is the only place the task's
    identity is visible; on_start pairs the child's start with it.
    """
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    prompt = str(ctx.tool_input.get("prompt") or "")
    marker = REDISPATCH_RE.search(prompt)
    common.append(ctx, "dispatch.jsonl", {
        "ev": "launch", "tool_use_id": ctx.tool_use_id, "subagent_type": target,
        "parent_agent_id": common.scope_of(ctx),
        "prompt_sha": common.sha(common.normalise_prompt(prompt)),
        "redispatch": marker.group(1) if marker else None,
    })
    return None


def pair_launch(cfg, agent_type, agent_id, dispatch_rows, now):
    """(launch row or None, "unique" | "guess" | None) for a new start.

    A start can only follow its own launch, so when exactly one unconsumed
    launch of this agent type is pending (and no start of the same burst
    was guessed) the pairing is certain. Several pending launches (a
    parallel fan-out) leave it a FIFO guess, which is never used to hand one
    run's output to another.
    """
    if any(r.get("ev") == "start" and r.get("agent_id") == agent_id for r in dispatch_rows):
        return None, None  # a resumed subagent: no new launch belongs to it
    consumed = {r.get("tool_use_id") for r in dispatch_rows if r.get("ev") == "start" and r.get("tool_use_id")}
    floor = now - float(cfg["launch_window_s"])
    pending = [r for r in dispatch_rows
               if r.get("ev") == "launch" and r.get("subagent_type") == agent_type
               and (r.get("t") or 0) >= floor and r.get("tool_use_id") not in consumed]
    if not pending:
        return None, None
    # an earlier guess in the same burst may have taken this start's launch,
    # so the last launch left over is no more certain than the guesses were
    guessed = any(r.get("ev") == "start" and r.get("agent_type") == agent_type and r.get("pair") == "guess"
                  and (r.get("t") or 0) >= floor for r in dispatch_rows)
    return pending[0], ("unique" if len(pending) == 1 and not guessed else "guess")


# ---- SubagentStart ----------------------------------------------------------
def on_start(ctx):
    agent_type = ctx.agent_type
    if not ctx.is_tantra_agent(agent_type):
        return None
    cfg = common.settings(ctx, "scribe", DEFAULTS)
    tier = ctx.tier(agent_type)
    dispatch_rows = common.rows(ctx, "dispatch.jsonl")
    launch, pair = pair_launch(cfg, agent_type, ctx.agent_id, dispatch_rows, time.time())
    row = {"ev": "start", "agent_id": ctx.agent_id, "agent_type": agent_type, "tier": tier}
    if launch:
        row.update({
            "tool_use_id": launch.get("tool_use_id"), "pair": pair,
            "parent_agent_id": launch.get("parent_agent_id"), "prompt_sha": launch.get("prompt_sha"),
            "redispatch": launch.get("redispatch"),
        })
    row = common.append(ctx, "dispatch.jsonl", row)
    results = [run_brief(ctx, cfg, agent_type, dispatch_rows, row), depth_note(ctx, cfg, agent_type)]
    return [r for r in results if r is not None]


def prior_runs(ctx, agent_type, dispatch_rows, exclude_agent_id=None):
    """Finished runs of this agent type with a saved output, oldest first:
    [(stop row, start row or {}, output path)]."""
    starts = {}
    for r in dispatch_rows:
        if r.get("ev") == "start" and r.get("agent_id") and r["agent_id"] not in starts:
            starts[r["agent_id"]] = r
    runs = []
    for aid, stop in common.latest_stop_by_agent(dispatch_rows).items():
        if aid == exclude_agent_id or stop.get("agent_type") != agent_type:
            continue
        path = stop.get("output_path") or common.output_path(ctx, agent_type, aid)
        if path and os.path.isfile(path):
            runs.append((stop, starts.get(aid, {}), path))
    return sorted(runs, key=lambda run: run[0].get("t") or 0)


def select_prior(runs, start_row):
    """The earlier run this start re-dispatches, and why; (None, None) when unrelated.

    Only two signals identify a re-dispatch: the identical normalised prompt,
    or the orchestrators' redispatch marker. With a marker the prior run is
    the parent's only earlier run of this agent type, or its latest run in
    the same cycle; anything more ambiguous (a fan-out over several targets)
    gets no brief, because another target's output would mislead this run.
    """
    if start_row.get("pair") != "unique":
        return None, None
    same_prompt = [run for run in runs if run[1].get("prompt_sha") and run[1].get("prompt_sha") == start_row.get("prompt_sha")]
    if same_prompt:
        return same_prompt[-1], "identical dispatch prompt"
    cycle = start_row.get("redispatch")
    if not cycle:
        return None, None
    same_parent = [run for run in runs if run[1].get("parent_agent_id") == start_row.get("parent_agent_id")]
    same_cycle = [run for run in same_parent if run[1].get("redispatch") == cycle]
    if same_cycle:
        return same_cycle[-1], f"re-dispatch cycle {cycle}"
    if len(same_parent) == 1:
        return same_parent[0], f"re-dispatch cycle {cycle} (first attempt)"
    return None, None


def run_brief(ctx, cfg, agent_type, dispatch_rows, start_row):
    runs = prior_runs(ctx, agent_type, dispatch_rows, exclude_agent_id=ctx.agent_id)
    if not runs:
        return None
    chosen, basis = select_prior(runs, start_row)
    if not chosen:
        return None
    stop, _, latest = chosen
    text = common.read_text(latest)
    if not text.strip():
        return None
    ended = stop.get("t") or common.mtime(latest) or time.time()
    missing = stop.get("contract_missing") or []
    excerpt = common.head_tail(text.strip(), int(cfg["brief_chars"]))
    body = (
        f"Tantra Run Brief: this dispatch re-runs an earlier {agent_type} run in this session (matched by "
        f"{basis}; that run ended {common.fmt_duration(time.time() - ended)} ago). Its final response is "
        f"summarised below so this run can continue from it instead of repeating completed steps. "
        f"Missing contract fields last time: {', '.join(missing) if missing else 'none'}.\n"
        f"Saved output: {latest}\n"
        f"--- previous final response ({len(text):,} chars; head and tail) ---\n"
        f"{excerpt}\n"
        f"--- end of previous response ---"
    )
    prior_tokens = (stop.get("tokens") or {}).get("output") or common.estimate_tokens(len(text))
    return common.outcome(
        ctx, "scribe", cfg["mode"], "run_brief", context=body, cap=int(cfg["brief_chars"]) + 800,
        est_tokens_avoided=prior_tokens, target=agent_type, prior_runs=len(runs), basis=basis,
        prior_agent_id=stop.get("agent_id"),
    )


def spawn_depth(ctx):
    meta = state.read_json(common.agent_file(ctx.transcript_path, ctx.agent_id, ".meta.json") or "", default=None)
    if not isinstance(meta, dict):
        return None
    try:
        return int(meta.get("spawnDepth"))
    except (TypeError, ValueError):
        return None


def depth_note(ctx, cfg, agent_type):
    info = ctx.agent_info(agent_type) or {}
    if info.get("has_agent_tool") is False:
        return None
    depth = spawn_depth(ctx)
    try:
        limit = int(os.environ.get("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH") or cfg["depth_limit"])
    except ValueError:
        limit = int(DEFAULTS["depth_limit"])
    if depth is None or depth < limit:
        return None
    text = (
        f"This agent runs at spawn depth {depth}; Claude Code withholds the Agent tool at the default depth "
        f"limit of {limit}, so dispatches from here will fail. Returning findings to the parent is the "
        f"route that works at this depth."
    )
    return common.outcome(ctx, "scribe", cfg["mode"], "depth_note", context=text, target=agent_type, depth=depth)


# ---- PostToolUse / PostToolUseFailure on Agent (parent side) ----------------
def on_returned(ctx):
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    resp = ctx.tool_response if isinstance(ctx.tool_response, dict) else {}
    status = "error" if ctx.event == "PostToolUseFailure" else (resp.get("status") or "unknown")
    common.append(ctx, "dispatch.jsonl", {
        "ev": "returned",
        "tool_use_id": ctx.tool_use_id,
        "subagent_type": target,
        "status": status,
        "agent_id": resp.get("agentId"),
        "total_duration_ms": resp.get("totalDurationMs"),
        "total_tool_use_count": resp.get("totalToolUseCount"),
        "parent": ctx.agent_type or "main",
        "parent_agent_id": ctx.agent_id or "main",
        "prompt_sha": common.sha(common.normalise_prompt(ctx.tool_input.get("prompt"))),
        "description": common.shorten(ctx.tool_input.get("description") or "", 80),
    })
    return None


# ---- PostToolUse(SubagentHandback), inside the subagent ----------------------
def on_handback(ctx):
    """Keep a report delivered through SubagentHandback for this agent's stop.

    On Claude Code v2.1.271+ (auto mode) that tool's message IS the report and
    last_assistant_message is only closing text; contract and the saved
    output must see the report.
    """
    if not ctx.agent_id or not ctx.is_tantra_agent(ctx.agent_type):
        return None
    message = ctx.tool_input.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    cfg = common.settings(ctx, "scribe", DEFAULTS)
    try:
        common.write_text(common.handback_path(ctx, ctx.agent_id), message[: int(cfg["output_cap"])])
    except OSError as exc:
        ctx.log_error("scribe.handback", exc)
    return None


# ---- SubagentStop (called by the router after meter + contract) -------------
def record_stop(ctx, measured, verdict, blocked=False):
    cfg = common.settings(ctx, "scribe", DEFAULTS)
    message, handback = common.final_report(ctx)
    if handback and not blocked:
        # consumed: a later resume of this agent must not reuse this report.
        # Kept while contract blocks, so the fixed stop still sees it.
        try:
            os.remove(handback)
        except OSError:
            pass
    out_path = None
    if message.strip():
        out_path = common.output_path(ctx, ctx.agent_type, ctx.agent_id)
        try:
            common.write_text(out_path, message[: int(cfg["output_cap"])])
        except OSError as exc:
            ctx.log_error("scribe.output", exc)
            out_path = None
    measured = measured or {}
    verdict = verdict or {}
    return common.append(ctx, "dispatch.jsonl", {
        "ev": "stop",
        "agent_id": ctx.agent_id,
        "agent_type": ctx.agent_type,
        "tier": ctx.tier(ctx.agent_type),
        "duration_s": measured.get("duration_s"),
        "output_chars": len(message),
        "contract_ok": verdict.get("ok", True),
        "contract_missing": verdict.get("missing", []),
        "tokens": measured.get("tokens"),
        "over_budget": measured.get("over_budget", False),
        "output_path": out_path,
        "handback": bool(handback),
    })


# ---- SessionStart (compact | resume) ---------------------------------------
def on_session_start(ctx):
    source = ctx.payload.get("source") or ""
    if source not in ("compact", "resume"):
        return None
    if source == "compact":
        # echo's read history resets for whichever scope compacted, a
        # subagent included (its earlier results left its context too)
        common.append(ctx, "reads.jsonl", {"kind": "compact", "scope": common.scope_of(ctx)})
    if ctx.agent_id:
        return None
    cfg = common.settings(ctx, "scribe", DEFAULTS)
    body = compaction_brief(ctx, source, int(cfg["compaction_brief_chars"]))
    if not body:
        return None
    return common.outcome(ctx, "scribe", cfg["mode"], "compaction_brief", context=body,
                          cap=int(cfg["compaction_brief_chars"]), source_event=source)


def _dispatch_lines(dispatch_rows):
    stops = common.latest_stop_by_agent(dispatch_rows)
    returned = {r.get("agent_id"): r for r in dispatch_rows if r.get("ev") == "returned" and r.get("agent_id")}
    lines, running = [], []
    for r in dispatch_rows:
        aid = r.get("agent_id")
        if r.get("ev") == "start" and aid and aid not in stops and aid not in running:
            running.append(aid)
            lines.append(f"- {r.get('agent_type')} ({aid}): started {common.fmt_ts(r.get('t'))}, no stop recorded yet")
    for aid, stop in stops.items():
        status = (returned.get(aid) or {}).get("status") or "completed"
        tokens = (stop.get("tokens") or {}).get("output")
        extra = f", {tokens:,} output tokens" if isinstance(tokens, int) else ""
        flag = "" if stop.get("contract_ok", True) else f" [missing {', '.join(stop.get('contract_missing') or [])}]"
        lines.append(f"- {stop.get('agent_type')} ({aid}): {status}, {common.fmt_duration(stop.get('duration_s'))}{extra}{flag}")
    return lines, running


def compaction_brief(ctx, source, limit):
    dispatch_rows = common.rows(ctx, "dispatch.jsonl")
    lines, _ = _dispatch_lines(dispatch_rows)
    parts = []
    if lines:
        parts.append(f"Dispatches so far ({len(lines)}):\n" + "\n".join(lines[-15:]))
    ws = ctx.workspace_dir
    if ws:
        latest = state.read_json(os.path.join(ws, "memory", "latest.json"), default={}) or {}
        gates = latest.get("pending_approval_gates") if isinstance(latest, dict) else None
        if isinstance(gates, list) and gates:
            gate_lines = [
                f"- {g.get('gate_id')} ({g.get('stakes_class', '?')}): {common.shorten(g.get('summary') or '', 110)}"
                for g in gates[:8] if isinstance(g, dict)
            ]
            parts.append("Pending approval gates (memory/latest.json):\n" + "\n".join(gate_lines))
        checkpoints = state.read_jsonl(os.path.join(ws, "memory", "checkpoints.jsonl"), tail=1)
        if checkpoints:
            cp = checkpoints[-1]
            parts.append(
                f"Last checkpoint ({cp.get('timestamp', '?')}): {common.shorten(cp.get('request_summary') or '', 220)}; "
                f"dispatched_to: {', '.join(cp.get('dispatched_to') or []) or 'none'}"
            )
    saved = []
    outputs_root = os.path.join(ctx.session_dir, "outputs")
    try:
        for agent in sorted(os.listdir(outputs_root)):
            count = len([n for n in os.listdir(os.path.join(outputs_root, agent)) if n.endswith(".txt")])
            if count:
                saved.append(f"{agent} ({count})")
    except OSError:
        pass
    if saved:
        parts.append(
            "Saved final responses available for re-dispatch (a Tantra Run Brief hands the matching one to a "
            f"re-dispatch that repeats its prompt or carries the redispatch marker): {', '.join(saved)}; "
            f"folder {outputs_root}"
        )
    if not parts:
        return None
    header = f"Tantra session state after {source} (recorded by Tantra hooks, so the history does not need re-reading):"
    return common.clip(header + "\n" + "\n".join(parts), limit)


# ---- Stop (workspace scope) -> memory/sentinel_runs.jsonl -------------------
def on_stop(ctx):
    ws = ctx.workspace_dir
    if not ws or ctx.agent_id:
        return None
    cfg = common.settings(ctx, "scribe", DEFAULTS)
    dispatch_rows = common.rows(ctx, "dispatch.jsonl")
    sentinel_rows = common.rows(ctx, "sentinel.jsonl")
    note_rows = common.rows(ctx, "notes.jsonl")
    marks = common.rows(ctx, "summaries.jsonl")
    last = marks[-1] if marks else {}
    d0, s0, n0 = last.get("dispatch_lines", 0), last.get("sentinel_lines", 0), last.get("note_lines", 0)
    new_dispatch, new_sentinel, new_notes = dispatch_rows[d0:], sentinel_rows[s0:], note_rows[n0:]
    interventions = [r for r in new_sentinel if r.get("action") in common.INTERVENTIONS]
    if not new_dispatch and not interventions:
        return None
    summary = build_summary(ctx, new_dispatch, interventions, new_notes, int(cfg["summary_dispatch_list_cap"]))
    try:
        state.append_jsonl(os.path.join(ws, "memory", "sentinel_runs.jsonl"), summary)
    except OSError as exc:
        ctx.log_error("scribe.summary", exc)
        return None
    common.append(ctx, "summaries.jsonl", {
        "dispatch_lines": len(dispatch_rows), "sentinel_lines": len(sentinel_rows), "note_lines": len(note_rows),
    })
    return None


def percentile(values, pct):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    rank = max(1, -(-len(values) * pct // 100))
    return values[int(rank) - 1]


def build_summary(ctx, dispatch_rows, interventions, notes, list_cap):
    stops = [r for r in dispatch_rows if r.get("ev") == "stop"]
    durations = [r.get("duration_s") for r in stops if isinstance(r.get("duration_s"), (int, float))]
    by_tier = Counter(r.get("tier") or "unknown" for r in stops)
    dispatch_list = [
        {
            "agent_type": r.get("agent_type"), "tier": r.get("tier"), "duration_s": r.get("duration_s"),
            "output_tokens": (r.get("tokens") or {}).get("output"), "total_tokens": (r.get("tokens") or {}).get("total"),
            "contract_ok": r.get("contract_ok", True),
        }
        for r in stops
    ][:list_cap]
    actions = Counter(r.get("action") for r in interventions if r.get("applied", True))
    denials = Counter(r.get("source") for r in interventions if r.get("action") in ("echo_deny", "lens_deny", "boundary_deny") and r.get("applied", True))
    stalls = [
        {"agent_type": r.get("target"), "agent_id": r.get("stalled_agent_id"), "reason": r.get("reason"),
         "idle_s": r.get("idle_s"), "elapsed_s": r.get("elapsed_s")}
        for r in interventions if r.get("action") == "stall"
    ]
    repeated = defaultdict(int)
    for r in interventions:
        if r.get("action") in ("echo_note", "echo_deny") and r.get("desc"):
            repeated[r["desc"]] = max(repeated[r["desc"]], int(r.get("prior_calls") or 0) + 1)
    hotspots = [
        {"agent_type": n.get("agent_type"), "agent_id": n.get("agent_id"), "output_tokens": n.get("output_tokens"),
         "duration_s": n.get("duration_s")}
        for n in notes if n.get("ev") == "note" and n.get("kind") == "meter"
    ]
    return {
        "schema": "tantra-sentinel-run/1",
        "ts": state.now_iso(),
        "session_id": ctx.session_id,
        "dispatches": len(stops),
        "starts": len([r for r in dispatch_rows if r.get("ev") == "start"]),
        "by_tier": dict(by_tier),
        "duration_s": {"p50": percentile(durations, 50), "p90": percentile(durations, 90),
                       "max": max(durations) if durations else None},
        "output_tokens_total": sum((r.get("tokens") or {}).get("output") or 0 for r in stops),
        "dispatch_list": dispatch_list,
        "stalls": stalls,
        "interventions": dict(actions),
        "denials": dict(denials),
        "contract_blocks": actions.get("contract_block", 0),
        "run_briefs": actions.get("run_brief", 0),
        "repeated_reads": [{"desc": d, "calls": n} for d, n in sorted(repeated.items(), key=lambda kv: -kv[1])[:10]],
        "hotspots": hotspots[:10],
        "est_tokens_avoided": sum(int(r.get("est_tokens_avoided") or 0) for r in interventions),
        "est_basis": "ESTIMATE: chars/4 of avoided reads, transcript usage of avoided re-dispatches",
    }
