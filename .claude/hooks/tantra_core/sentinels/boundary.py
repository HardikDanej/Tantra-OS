"""
boundary.py -- Tantra Boundary: dispatches that skip the chain of command.

Why it exists: Tantra is a hierarchy (entry orchestrators -> bridge ->
domain agents -> sub-agents), and each level's dispatch contract carries
context the level below relies on (brand memory, approval gates, the
parent's synthesis). A domain agent dispatching another system's sub-agent
directly bypasses the parent that owns that context, which is how the same
research gets done twice under two owners. The registry already records
every agent's parents and children, so the check is a lookup.

Rule: when a Tantra agent (the hook fires inside it) dispatches a Tantra
agent, the dispatch is in bounds if the target is one of the caller's
registered children or the caller is one of the target's registered
parents. Otherwise: "assist" (default) adds a factual note naming the
registered parent(s); "enforce" denies. Main-thread dispatches are the
activation gate's concern, not boundary's.
"""
from . import common

DEFAULTS = {"mode": "assist"}


def on_pre_agent(ctx):
    caller = ctx.agent_type
    if not ctx.agent_id or not ctx.is_tantra_agent(caller):
        return None
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    cfg = common.settings(ctx, "boundary", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    caller_info = ctx.agent_info(caller) or {}
    target_info = ctx.agent_info(target) or {}
    parents = [p for p in (target_info.get("parents") or []) if p]
    if target in (caller_info.get("children") or []) or caller in parents:
        return None
    named = [p for p in parents if p != "main"] or parents or ["(none registered)"]
    text = (
        f"Tantra hierarchy note: {caller} is dispatching {target}, whose registered parent(s) are "
        f"{', '.join(named)}; Tantra's chain of command routes this through {named[0]}."
    )
    return common.outcome(ctx, "boundary", cfg["mode"],
                          "boundary_deny" if cfg["mode"] == "enforce" else "boundary_note",
                          deny=text if cfg["mode"] == "enforce" else None,
                          context=None if cfg["mode"] == "enforce" else text,
                          target=target, caller=caller)
