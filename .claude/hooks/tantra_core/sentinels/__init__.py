"""
sentinels -- Tantra's watcher bots, behind one router.

Why one router: the dispatcher (tantra_hook.py) imports a single module per
event, and several bots care about the same event (a SubagentStop is
measured by meter, checked by contract and recorded by scribe, in that
order, because scribe's ledger line carries both of the others' findings).
The router decides which bots see which event and isolates them: one bot
raising never stops the others and never reaches the dispatcher.

Bots (each in its own module, each with a DEFAULTS dict and a mode):
  scribe    step ledger, Run Brief on re-dispatch, depth note, compaction brief
  pulse     stall watchdog (only in the asyncRewake "watchdog" process)
  echo      repeated identical reads / fetches / dispatches
  lens      full reads of knowledge bases and raw state logs
  contract  output-contract fields on domain/sub agents' final responses
  meter     token and time budgets, heaviest steps, session totals
  boundary  dispatches that skip Tantra's chain of command
  scope     domain agents outside the scope the user's request named

Contract: handle(ctx) -> Result | list[Result] | None. Never raises.
"""
from . import boundary, common, contract, echo, lens, meter, pulse, scope, scribe

READ_TOOLS = {"Read", "WebFetch", "Grep", "Glob"}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
# Tools that can change files without a Write/Edit marker (echo invalidates
# earlier Grep/Glob results when one runs).
EXEC_TOOLS = {"Bash", "PowerShell"}
HANDBACK_TOOL = "SubagentHandback"


def is_exec_tool(name):
    return name in EXEC_TOOLS or str(name or "").startswith("mcp__")


def handle(ctx):
    if ctx.mode == "watchdog":
        return _run(ctx, "pulse", pulse.watch)
    route = ROUTES.get(ctx.event)
    if route is None:
        return None
    return route(ctx) or None


def _run(ctx, name, fn, *args):
    try:
        return fn(ctx, *args)
    except Exception as exc:  # noqa: BLE001 - one bot failing must not silence the rest
        ctx.log_error("sentinels." + name, exc)
        return None


def _collect(ctx, steps):
    results = []
    for name, fn in steps:
        out = _run(ctx, name, fn)
        if isinstance(out, list):
            results.extend(r for r in out if r is not None)
        elif out is not None:
            results.append(out)
    return results


def _pre_tool(ctx):
    if ctx.tool_name == "Agent":
        return _collect(ctx, [("scribe", scribe.on_launch), ("echo", echo.on_pre_agent),
                              ("boundary", boundary.on_pre_agent), ("scope", scope.on_pre_agent)])
    if is_exec_tool(ctx.tool_name):
        return _collect(ctx, [("echo", echo.on_exec)])
    if ctx.tool_name not in READ_TOOLS:
        return None
    lens_results = _collect(ctx, [("lens", lens.on_pre_read)]) if ctx.tool_name == "Read" else []
    if any(r.deny for r in lens_results):
        return lens_results
    return lens_results + _collect(ctx, [("echo", echo.on_pre)])


def _post_tool(ctx):
    if ctx.tool_name == HANDBACK_TOOL:
        return _collect(ctx, [("scribe", scribe.on_handback)])
    if ctx.tool_name == "Agent":
        return _collect(ctx, [("scribe", scribe.on_returned), ("meter", meter.on_returned)])
    if ctx.tool_name in READ_TOOLS:
        return _collect(ctx, [("echo", echo.on_post)])
    if ctx.tool_name in WRITE_TOOLS:
        return _collect(ctx, [("echo", echo.on_write)])
    return None


def _post_tool_failure(ctx):
    if ctx.tool_name == "Agent":
        return _collect(ctx, [("scribe", scribe.on_returned)])
    return None


def _subagent_stop(ctx):
    if not ctx.is_tantra_agent(ctx.agent_type) or not ctx.agent_id:
        return None
    measured = _run(ctx, "meter", meter.measure) or {}
    checked = _run(ctx, "contract", contract.check, measured) or ({}, None)
    verdict, contract_result = checked
    blocked = bool(contract_result is not None and contract_result.block)
    stop_row = _run(ctx, "scribe", scribe.record_stop, measured, verdict, blocked)
    meter_results = _run(ctx, "meter", meter.after_stop, measured, stop_row) or []
    return [r for r in [contract_result, *meter_results] if r is not None]


ROUTES = {
    "UserPromptSubmit": lambda ctx: _collect(ctx, [("scope", scope.on_prompt)]),
    "PreToolUse": _pre_tool,
    "PostToolUse": _post_tool,
    "PostToolUseFailure": _post_tool_failure,
    "SubagentStart": lambda ctx: _collect(ctx, [("scribe", scribe.on_start)]),
    "SubagentStop": _subagent_stop,
    "SessionStart": lambda ctx: _collect(ctx, [("scribe", scribe.on_session_start)]),
    "PreCompact": lambda ctx: _collect(ctx, [("echo", echo.on_compact)]),
    "Stop": lambda ctx: _collect(ctx, [("scribe", scribe.on_stop)]),
}

__all__ = ["handle", "common"]
