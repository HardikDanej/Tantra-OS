#!/usr/bin/env python3
"""
tantra_hook.py
==============
Single entry point for every Claude Code hook Tantra installs.

Installed (by tools/install_hooks.py) in exec form, for example:

    "command": "C:\\Python314\\python.exe",
    "args": ["-I", "-S", "<repo>/.claude/hooks/tantra_hook.py", "pre"]

The trailing mode argument only matters for the stall watchdog ("watchdog"),
which is a separate asyncRewake hook entry on the same PreToolUse event.
Every other mode is informational; the real event comes from the payload's
`hook_event_name`.

Contract with Claude Code (https://code.claude.com/docs/en/hooks):
  * the event JSON arrives on stdin;
  * exit 0 + a JSON object on stdout is a structured decision;
  * exit 0 + no stdout means "no opinion";
  * exit 2 + stderr is used only by the watchdog (asyncRewake) to wake Claude.

Design rules, all load-bearing:
  * Stdlib only, run with -I -S: this runs on every matching event in every
    project on the machine, so start-up cost and import surface stay minimal.
  * Fail open. Any exception anywhere -> exit 0 with no output, and the error
    goes to ~/.tantra/logs/hook_errors.log. A crashing hook must never block
    unrelated work.
  * Silent when Tantra is not active. Only the activation module runs for an
    inactive session, and it prints nothing unless the wake word was used or a
    Tantra agent is about to be dispatched.

Module order per event is fixed in PLAN below. Each module exposes
`handle(ctx) -> Result | list[Result] | None` (see tantra_core/result.py).
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Which modules run for which event, in order. "activation" always runs first
# because every other module checks ctx.active, which activation may change.
PLAN = {
    "UserPromptSubmit": ["activation", "sentinels"],
    "PreToolUse": ["activation", "sentinels", "connectors_guard"],
    "PostToolUse": ["sentinels", "connectors_guard", "seal_guard"],
    "PostToolUseFailure": ["sentinels", "connectors_guard"],
    "SubagentStart": ["sentinels"],
    "SubagentStop": ["sentinels"],
    "SessionStart": ["sentinels"],
    "PreCompact": ["sentinels"],
    "Stop": ["sentinels"],
}


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0

    from tantra_core.context import Context
    from tantra_core.result import emit

    ctx = Context(payload, mode=mode, hooks_dir=HERE)
    # The watchdog is a second, asyncRewake process on the same PreToolUse
    # event as the synchronous "pre" hook. It must only run the stall watch;
    # anything else would duplicate the synchronous hook's work.
    modules = ["sentinels"] if mode == "watchdog" else PLAN.get(ctx.event, [])
    results = []
    for name in modules:
        if name != "activation" and not ctx.active:
            continue
        try:
            mod = importlib.import_module("tantra_core." + name)
            out = mod.handle(ctx)
        except Exception as exc:  # noqa: BLE001 - fail open, always
            ctx.log_error(name, exc)
            continue
        if out is None:
            continue
        if isinstance(out, list):
            results.extend(r for r in out if r is not None)
        else:
            results.append(out)
    return emit(ctx, results)


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception as exc:  # noqa: BLE001 - fail open, always
        try:
            from tantra_core.context import log_error_standalone
            log_error_standalone("tantra_hook", exc)
        except Exception:  # noqa: BLE001
            pass
        code = 0
    sys.exit(code)
