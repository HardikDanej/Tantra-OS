"""
pulse.py -- Tantra Pulse: the stall watchdog.

Why it exists: the known Tantra stall is a background-dispatched child that
never returns. The parent keeps waiting (or keeps working without the
result), nobody notices for many minutes, and the eventual recovery is a
full re-run that repeats everything the child already finished. No hook
fires while a subagent is silently stuck, so the only way to notice is a
process that is already running when the dispatch starts.

How: Claude Code starts this module in a separate asyncRewake hook process
on every PreToolUse(Agent) ("watchdog" mode). It polls the session ledger
that scribe writes, identifies the subagent this dispatch started, and uses
transcript file mtimes as a heartbeat: the subagent's own, and those of
every descendant it dispatched (a parent waiting on a healthy synchronous
child writes nothing itself). While the subagent's last tool call has no
result yet (a foreground child, a long Bash or MCP call) its silence is not
counted as idle; only max_min applies. When the heartbeat has been still
for idle_min[tier], or the run exceeds max_min[tier], it returns one rewake
report (exit 2 -> Claude is woken with it as a system reminder) and exits.
It exits silently as soon as the dispatch finishes.

A foreground (synchronous) dispatch returns "completed"; a background one
returns "async_launched" immediately, so only a non-async "returned" line,
or the child's own stop line, ends the watch.

Matching a start to this dispatch, most certain first:
  1. the returned line's agentId for this tool_use_id (always wins, even
     over an earlier guess, which is then released to its real owner);
  2. a start line scribe paired with this tool_use_id when exactly one
     launch of that agent type was pending (pair "unique");
  3. a guess: the first unclaimed start of the agent type that began after
     the watchdog itself (minus a grace period). The guess is recorded in
     claims.jsonl; the first claim line for an agent_id wins, a "sure" claim
     (1 or 2) beats any guess, and a watchdog whose guess was taken over
     drops it and claims again on its next poll.

Pulse is a latency bot: it never claims a token saving (est 0). The report
is factual and cites Tantra's stall protocol so the model can act on it.
Always returns before deadline_s (the installer's timeout is 3600 s).
"""
import time

from . import common

DEFAULTS = {
    "mode": "assist",
    "poll_s": 30,
    "idle_min": {"sub": 6, "domain": 10, "entry": 15, "bridge": 15},
    "max_min": {"sub": 20, "domain": 35, "entry": 55, "bridge": 55},
    "start_grace_s": 5,
    "find_start_s": 180,
    "deadline_s": 3500,
    "report_chars": 2000,
}
HARD_DEADLINE_S = 3500


def watch(ctx, clock=time.time, sleep=time.sleep):
    if ctx.tool_name != "Agent" or not ctx.active:
        return None
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    cfg = common.settings(ctx, "pulse", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    tier = ctx.tier(target) or "sub"
    limits = {
        "idle": common.per_tier(cfg["idle_min"], tier, DEFAULTS["idle_min"]) * 60,
        "max": common.per_tier(cfg["max_min"], tier, DEFAULTS["max_min"]) * 60,
    }
    started = clock()
    deadline = started + min(float(cfg["deadline_s"]), HARD_DEADLINE_S)
    poll = max(0.05, float(cfg["poll_s"]))
    watch_state = {"agent_id": None, "start_t": None, "sure": False}
    while True:
        now = clock()
        verdict = _tick(ctx, cfg, target, tier, limits, started, now, watch_state)
        if verdict == "done":
            return None
        if verdict is not None:
            return verdict
        if now + poll >= deadline:
            return None
        sleep(poll)


def _tick(ctx, cfg, target, tier, limits, started, now, ws):
    dispatch_rows = common.rows(ctx, "dispatch.jsonl")
    returned = [r for r in dispatch_rows if r.get("ev") == "returned" and r.get("tool_use_id") == ctx.tool_use_id]
    for r in returned:
        if r.get("status") != "async_launched":
            return "done"
        if r.get("agent_id"):
            _adopt(ctx, ws, r["agent_id"])
    if not ws["agent_id"]:
        paired = [r for r in dispatch_rows if r.get("ev") == "start" and r.get("pair") == "unique"
                  and r.get("tool_use_id") == ctx.tool_use_id and r.get("agent_id")]
        if paired:
            _adopt(ctx, ws, paired[0]["agent_id"])
    elif not ws.get("sure") and _owner(ctx, ws["agent_id"]) not in (None, ctx.tool_use_id):
        ws.update(agent_id=None, start_t=None)  # a sure claim took this child over: guess again
    if not ws["agent_id"]:
        ws["agent_id"] = _claim_start(ctx, cfg, target, started, dispatch_rows)
        if not ws["agent_id"]:
            return "done" if now - started > float(cfg["find_start_s"]) else None
    agent_id = ws["agent_id"]
    if any(r.get("ev") == "stop" and r.get("agent_id") == agent_id for r in dispatch_rows):
        return "done"
    if ws["start_t"] is None:
        starts = common.starts_for(ctx, agent_id, dispatch_rows)
        ws["start_t"] = starts[0].get("t") if starts else started
    heartbeat = _heartbeat(ctx, agent_id, dispatch_rows)
    last_activity = max(t for t in (ws["start_t"], heartbeat, started) if t)
    idle, elapsed = now - last_activity, now - ws["start_t"]
    if idle >= limits["idle"] and not common.pending_tool_call(common.agent_file(ctx.transcript_path, agent_id)):
        reason = "idle"
    elif elapsed >= limits["max"]:
        reason = "max_duration"
    else:
        return None
    report = _report(ctx, cfg, target, tier, agent_id, reason, idle, elapsed, limits)
    return common.outcome(
        ctx, "pulse", cfg["mode"], "stall", rewake=report, cap=int(cfg["report_chars"]),
        target=target, stalled_agent_id=agent_id, reason=reason, tier=tier,
        idle_s=round(idle, 1), elapsed_s=round(elapsed, 1), tool_use_id=ctx.tool_use_id,
    ) or "done"


def _adopt(ctx, ws, agent_id):
    """Watch agent_id for certain (returned line or unique pairing)."""
    if ws.get("agent_id") == agent_id and ws.get("sure"):
        return
    if ws.get("agent_id") != agent_id:
        ws["start_t"] = None
    ws.update(agent_id=agent_id, sure=True)
    common.append(ctx, "claims.jsonl", {"agent_id": agent_id, "tool_use_id": ctx.tool_use_id, "sure": True})


def _claim_start(ctx, cfg, target, started, dispatch_rows):
    floor = started - float(cfg["start_grace_s"])
    taken = {r.get("agent_id") for r in dispatch_rows
             if r.get("ev") == "stop" or (r.get("ev") == "returned" and r.get("tool_use_id") != ctx.tool_use_id)
             or (r.get("ev") == "start" and r.get("pair") == "unique" and r.get("tool_use_id") != ctx.tool_use_id)}
    for row in dispatch_rows:
        if row.get("ev") != "start" or row.get("agent_type") != target or not row.get("agent_id"):
            continue
        if (row.get("t") or 0) < floor or row["agent_id"] in taken:
            continue
        owner = _owner(ctx, row["agent_id"])
        if owner is None:
            common.append(ctx, "claims.jsonl", {"agent_id": row["agent_id"], "tool_use_id": ctx.tool_use_id})
            owner = _owner(ctx, row["agent_id"])
        if owner == ctx.tool_use_id:
            return row["agent_id"]
    return None


def _owner(ctx, agent_id):
    """First sure claim for agent_id, else its first guess claim."""
    first = None
    for claim in common.rows(ctx, "claims.jsonl"):
        if claim.get("agent_id") != agent_id:
            continue
        if claim.get("sure"):
            return claim.get("tool_use_id")
        if first is None:
            first = claim.get("tool_use_id")
    return first


def descendants(agent_id, dispatch_rows, limit=50):
    """Agent ids dispatched (transitively) by agent_id, from scribe's start lines."""
    children = {}
    for r in dispatch_rows:
        if r.get("ev") == "start" and r.get("agent_id") and r.get("parent_agent_id"):
            children.setdefault(r["parent_agent_id"], []).append(r["agent_id"])
    found, queue = [], [agent_id]
    while queue and len(found) < limit:
        for child in children.get(queue.pop(0), []):
            if child not in found and child != agent_id:
                found.append(child)
                queue.append(child)
    return found


def _heartbeat(ctx, agent_id, dispatch_rows):
    beats = [common.mtime(common.agent_file(ctx.transcript_path, aid))
             for aid in [agent_id, *descendants(agent_id, dispatch_rows)]]
    beats = [b for b in beats if b]
    if beats:
        return max(beats)
    ledger = [r.get("t") for r in dispatch_rows if r.get("agent_id") == agent_id and r.get("t")]
    for r in common.rows(ctx, "sentinel.jsonl"):
        if r.get("agent_id") == agent_id:
            ledger.append(common.parse_iso(r.get("ts")))
    ledger.extend(r.get("t") for r in common.rows(ctx, "reads.jsonl") if r.get("scope") == agent_id)
    ledger = [t for t in ledger if t]
    return max(ledger) if ledger else None


def _report(ctx, cfg, target, tier, agent_id, reason, idle, elapsed, limits):
    path = common.agent_file(ctx.transcript_path, agent_id)
    facts = common.analyse_transcript(path, max_bytes=20_000_000) if common.mtime(path) else None
    trigger = (
        f"no transcript activity for {common.fmt_duration(idle)} (idle limit for tier {tier}: "
        f"{common.fmt_duration(limits['idle'])})"
        if reason == "idle"
        else f"running for {common.fmt_duration(elapsed)} (limit for tier {tier}: {common.fmt_duration(limits['max'])})"
    )
    lines = [
        f"Tantra Pulse stall report: the dispatch of {target} (tier {tier}, agent id {agent_id}, "
        f"tool_use_id {ctx.tool_use_id or 'unknown'}) has {trigger}. Elapsed since start: {common.fmt_duration(elapsed)}.",
    ]
    if facts and facts.get("last_tool"):
        last = facts["last_tool"]
        lines.append(f"Last recorded activity: {last['tool']} {last['target']}".rstrip() + ".")
    else:
        lines.append("Last recorded activity: no readable subagent transcript for this agent.")
    if facts and facts.get("tool_counts"):
        counts = ", ".join(f"{name} x{n}" for name, n in list(facts["tool_counts"].items())[:8])
        lines.append(f"Completed tool calls so far: {counts}.")
    lines.append(
        "Tantra stall protocol: a known Tantra stall is a background-dispatched child that never returns. "
        "The recovery is to re-dispatch only the unfinished part, synchronously. Completed work is preserved: "
        "the child's transcript stays on disk, and the Tantra Run Brief hands an earlier run's saved final "
        "output to a re-dispatch that repeats its prompt or carries the redispatch marker."
    )
    return common.clip("\n".join(lines), int(cfg["report_chars"]))
