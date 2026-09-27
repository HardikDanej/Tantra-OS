"""
meter.py -- Tantra Meter: time and token budgets per dispatch and per session.

Why it exists: the parent of a dispatch sees one number at most (the final
request's tokens) and nothing about which steps were expensive, so an
orchestrator keeps re-dispatching an agent the same way even when one huge
tool result is where the budget went. The subagent's transcript already
records every request's usage; SubagentStop hands its path to the hook.

What it does:
  * measure(): sums usage from the agent's own transcript, deduplicated by
    message id (streaming repeats one message across several lines), and
    the run's duration (from scribe's start line). Scribe writes the result
    into the same "stop" ledger line.
  * after_stop(): over the tier's budget -> a hotspot note is queued in
    notes.jsonl, plus the three heaviest tool results from the transcript.
    Session output tokens crossing session_output_budget -> one
    system_message to the user per crossed session_step (100k) band.
  * on_returned(): on the parent's next PostToolUse(Agent) for that dispatch
    (or any later Agent result in the same parent scope, for background
    dispatches that returned "async_launched" long before they finished),
    the queued note is delivered as context, once.

Figures are ESTIMATES in the sense that they are whatever the transcript
recorded; meter never claims a saving itself (est 0).
"""
import time

from . import common

DEFAULTS = {
    "mode": "assist",
    "output_budget": {"sub": 20000, "domain": 50000, "entry": 100000, "bridge": 100000},
    "duration_min": {"sub": 15, "domain": 30, "entry": 50, "bridge": 50},
    "session_output_budget": 400000,
    "session_step": 100000,
    "top_steps": 3,
    "max_transcript_mb": 60,
}


def _transcript(ctx):
    return ctx.payload.get("agent_transcript_path") or common.agent_file(ctx.transcript_path, ctx.agent_id)


def measure(ctx):
    cfg = common.settings(ctx, "meter", DEFAULTS)
    tier = ctx.tier(ctx.agent_type) or "sub"
    path = _transcript(ctx)
    facts = None
    if path and common.mtime(path):
        facts = common.analyse_transcript(path, top=int(cfg["top_steps"]),
                                          max_bytes=int(float(cfg["max_transcript_mb"]) * 1_000_000))
    starts = common.starts_for(ctx, ctx.agent_id)
    now = time.time()
    if starts and starts[0].get("t"):
        duration = now - starts[0]["t"]
    elif facts and facts.get("first_t"):
        duration = (facts.get("last_t") or now) - facts["first_t"]
    else:
        duration = None
    tokens = facts["tokens"] if facts and facts.get("messages") else None
    budget_tokens = common.per_tier(cfg["output_budget"], tier, DEFAULTS["output_budget"])
    budget_s = common.per_tier(cfg["duration_min"], tier, DEFAULTS["duration_min"]) * 60
    over = bool((tokens and tokens["output"] > budget_tokens) or (duration is not None and duration > budget_s))
    return {
        "tokens": tokens,
        "duration_s": round(duration, 1) if duration is not None else None,
        "over_budget": over,
        "heaviest": (facts or {}).get("heaviest") or [],
        "tool_counts": (facts or {}).get("tool_counts") or {},
        "budget_tokens": int(budget_tokens),
        "budget_min": budget_s / 60,
        "tier": tier,
    }


def after_stop(ctx, measured, stop_row):
    cfg = common.settings(ctx, "meter", DEFAULTS)
    if cfg["mode"] == "off" or not measured:
        return []
    results = []
    if measured.get("over_budget"):
        _queue_hotspot(ctx, cfg, measured)
    budget_msg = _session_budget(ctx, cfg)
    if budget_msg is not None:
        results.append(budget_msg)
    return results


def _queue_hotspot(ctx, cfg, measured):
    notes = common.rows(ctx, "notes.jsonl")
    if any(n.get("ev") == "note" and n.get("kind") == "meter" and n.get("agent_id") == ctx.agent_id for n in notes):
        return
    tokens = measured.get("tokens") or {}
    parent = next((r.get("parent_agent_id") for r in common.rows(ctx, "dispatch.jsonl")
                   if r.get("ev") == "returned" and r.get("agent_id") == ctx.agent_id), None)
    common.outcome(ctx, "meter", "observe" if cfg["mode"] == "observe" else "assist", "meter_hotspot",
                   target=ctx.agent_type, output_tokens=tokens.get("output"), duration_s=measured.get("duration_s"))
    if cfg["mode"] == "observe":
        return
    common.append(ctx, "notes.jsonl", {
        "ev": "note", "kind": "meter", "agent_id": ctx.agent_id, "agent_type": ctx.agent_type,
        "parent_agent_id": parent, "output_tokens": tokens.get("output"), "total_tokens": tokens.get("total"),
        "duration_s": measured.get("duration_s"), "budget_tokens": measured.get("budget_tokens"),
        "budget_min": measured.get("budget_min"), "heaviest": measured.get("heaviest"),
    })


def session_output_tokens(dispatch_rows):
    return sum(((r.get("tokens") or {}).get("output") or 0)
               for r in common.latest_stop_by_agent(dispatch_rows).values())


def _session_budget(ctx, cfg):
    budget = int(cfg["session_output_budget"])
    step = max(1, int(cfg["session_step"]))
    total = session_output_tokens(common.rows(ctx, "dispatch.jsonl"))
    if budget <= 0 or total < budget:
        return None
    band = int((total - budget) // step)
    notes = common.rows(ctx, "notes.jsonl")
    if any(n.get("ev") == "session_budget" and n.get("band") == band for n in notes):
        return None
    common.append(ctx, "notes.jsonl", {"ev": "session_budget", "band": band, "total": total})
    message = (
        f"Tantra Meter: Tantra agents in this session have used about {total:,} output tokens so far "
        f"(session budget {budget:,}; figure from the subagents' own transcripts). "
        f"`python .claude/lib/sentinel_report.py report` shows where they went."
    )
    return common.outcome(ctx, "meter", cfg["mode"], "meter_session_budget", system_message=message,
                          total_output_tokens=total, band=band)


def on_returned(ctx):
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    cfg = common.settings(ctx, "meter", DEFAULTS)
    if cfg["mode"] in ("off", "observe"):
        return None
    resp = ctx.tool_response if isinstance(ctx.tool_response, dict) else {}
    agent_id = resp.get("agentId")
    scope = common.scope_of(ctx)
    notes = common.rows(ctx, "notes.jsonl")
    delivered = {n.get("agent_id") for n in notes if n.get("ev") == "delivered"}
    pending = [
        n for n in notes
        if n.get("ev") == "note" and n.get("kind") == "meter" and n.get("agent_id") not in delivered
        and (n.get("agent_id") == agent_id or n.get("parent_agent_id") == scope)
    ]
    if not pending:
        return None
    for n in pending:
        common.append(ctx, "notes.jsonl", {"ev": "delivered", "agent_id": n.get("agent_id")})
    text = "\n".join(_note_text(n) for n in pending[:4])
    return common.outcome(ctx, "meter", cfg["mode"], "meter_note", context=text,
                          targets=[n.get("agent_type") for n in pending])


def _note_text(note):
    heavy = "; ".join(
        f"{h.get('tool')} {h.get('target') or ''} ({h.get('chars', 0):,} chars)".replace("  ", " ")
        for h in (note.get("heaviest") or [])[:3]
    ) or "no tool results recorded"
    out = note.get("output_tokens")
    used = f"{out:,} output tokens" if isinstance(out, int) else "an unknown number of output tokens"
    return (
        f"Tantra Meter: {note.get('agent_type')} ({note.get('agent_id')}) used {used} / "
        f"{common.fmt_duration(note.get('duration_s'))} (budget {int(note.get('budget_tokens') or 0):,} output tokens / "
        f"{common.fmt_duration((note.get('budget_min') or 0) * 60)}). Heaviest steps: {heavy}."
    )
