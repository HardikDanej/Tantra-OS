"""
scope.py -- Tantra Scope: enforce the scope router's lock on dispatches.

Why it exists: chief-marketing-orchestrator's instructions say to run
.claude/lib/scope_router.py before decomposing, and to dispatch only the
domain agents the request names. In a measured run the orchestrator loaded
that instruction, never ran the script, and dispatched a domain agent the
user hadn't asked for. A prompt instruction is a request; this makes it a
rule, at zero tokens.

Rule:
  * UserPromptSubmit (Tantra active): run scope_router.route() on the text
    the user typed (pasted/quoted text removed, same as the wake word) and
    save the result as the session's scope.json. A request that names no
    domain ("help us grow") clears the lock, so this never blocks a request
    the router can't read.
  * PreToolUse Agent from chief-marketing-orchestrator: if the lock is
    "high" and the target is one of that system's domain agents but not in
    the lock, deny (mode "enforce", default) or note (mode "assist").
    A dispatch whose prompt carries a `scope_dependency:` line is allowed:
    that is how the orchestrator declares a real dependency, such as the
    Marketing Strategist brand-foundation rule.
"""
import importlib.util
import json
import os

from .. import state
from ..activation import strip_quoted
from . import common

DEFAULTS = {"mode": "enforce"}
LOCKED_CALLERS = {"chief-marketing-orchestrator"}
DEP_MARKER = "scope_dependency:"
SCOPE_FILE = "scope.json"

_ROUTER = None


def _router(ctx):
    global _ROUTER
    if _ROUTER is None:
        path = os.path.join(ctx.root, ".claude", "lib", "scope_router.py")
        spec = importlib.util.spec_from_file_location("tantra_scope_router", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ROUTER = mod
    return _ROUTER


def on_prompt(ctx):
    if common.settings(ctx, "scope", DEFAULTS)["mode"] == "off":
        return None
    prompt = ctx.payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    route = _router(ctx).route(strip_quoted(prompt))
    row = {
        "ts": state.now_iso(),
        "confidence": route["confidence"],
        "domain_agents": route["domain_agents"],
        "other_systems": route["other_systems"],
        "prompt_sha": common.sha(prompt),
    }
    state.ensure_dir(ctx.session_dir)
    with open(ctx.session_file(SCOPE_FILE), "w", encoding="utf-8") as f:
        json.dump(row, f)
    ctx.log_sentinel("scope", "scope_set", mode="record", applied=True, est_tokens_avoided=0,
                     confidence=row["confidence"], domain_agents=row["domain_agents"])
    return None


def on_pre_agent(ctx):
    caller = ctx.agent_type
    if caller not in LOCKED_CALLERS or not ctx.agent_id:
        return None
    cfg = common.settings(ctx, "scope", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    lock = state.read_json(ctx.session_file(SCOPE_FILE), default=None)
    if not isinstance(lock, dict) or lock.get("confidence") != "high":
        return None
    target = common.target_agent(ctx)
    allowed = lock.get("domain_agents") or []
    if target not in _router(ctx).DOMAIN_AGENTS or target in allowed:
        return None
    if DEP_MARKER in str(ctx.tool_input.get("prompt") or ""):
        ctx.log_sentinel("scope", "scope_dependency_allowed", mode=cfg["mode"], applied=True,
                         est_tokens_avoided=0, target=target, caller=caller)
        return None
    text = (
        f"Tantra scope lock: the user's request names {', '.join(allowed)} "
        f"(scope_router.py, run by the hook on their message), and {target} is outside it. "
        f"Don't dispatch it. If it's a real dependency this orchestrator's rules require "
        f"(e.g. the Marketing Strategist brand-foundation rule), re-dispatch with a line "
        f"`{DEP_MARKER} <reason>` in the contract and name it to the user as a dependency. "
        f"Otherwise offer it under \"Flagged for you\" instead of dispatching it."
    )
    enforce = cfg["mode"] == "enforce"
    return common.outcome(ctx, "scope", cfg["mode"], "scope_deny" if enforce else "scope_note",
                          deny=text if enforce else None, context=None if enforce else text,
                          target=target, caller=caller, lock=allowed)
