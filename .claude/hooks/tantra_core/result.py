"""
result.py -- what a Tantra hook module returns, and how results become the
JSON Claude Code expects on stdout.

A module returns one Result (or a list, or None). The dispatcher merges every
module's results for the event and emits exactly one JSON object.

Field meanings (only the ones the current event supports are emitted):

  deny            PreToolUse: block the tool call; text goes to Claude as the
                  reason. Precedence over ask.
  ask             PreToolUse: force a permission prompt; text shown to the user.
  block           UserPromptSubmit / PostToolUse / Stop / SubagentStop:
                  top-level decision "block" + reason. On SubagentStop this
                  keeps the subagent running and the reason becomes its next
                  instruction.
  context         Text added to Claude's context (hookSpecificOutput.
                  additionalContext). Phrase it as facts, not commands:
                  Claude Code's docs warn imperative "system" phrasing can
                  trip prompt-injection defenses.
  system_message  Warning shown to the user (not to Claude).
  rewake          Watchdog only: printed to stderr with exit code 2, which an
                  asyncRewake hook uses to wake Claude.
  source          Module name, for the sentinel log.

Every text field is capped so one hook can never flood the context window
(Claude Code's own cap is 10,000 characters per field; we stay under it).
"""
import json
import sys

FIELD_CAP = 9000

EVENTS_WITH_CONTEXT = {
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "SessionStart",
    "Stop",
}
EVENTS_WITH_BLOCK = {"UserPromptSubmit", "PostToolUse", "PostToolUseFailure", "Stop", "SubagentStop", "PreCompact"}


class Result:
    __slots__ = ("source", "deny", "ask", "block", "context", "system_message", "rewake")

    def __init__(self, source, deny=None, ask=None, block=None, context=None, system_message=None, rewake=None):
        self.source = source
        self.deny = deny
        self.ask = ask
        self.block = block
        self.context = context
        self.system_message = system_message
        self.rewake = rewake

    def __repr__(self):
        parts = [f"{k}={getattr(self, k)!r}" for k in self.__slots__ if getattr(self, k)]
        return "Result(" + ", ".join(parts) + ")"


def cap(text, limit=FIELD_CAP):
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 60].rstrip() + "\n[... truncated by Tantra to stay within hook limits]"


def _join(values):
    vals = [v for v in values if v]
    return cap("\n\n".join(vals)) if vals else None


def build_output(event, results):
    """Return (exit_code, stdout_obj_or_None, stderr_text_or_None)."""
    rewake = _join(r.rewake for r in results)
    if rewake:
        return 2, None, rewake

    deny = _join(r.deny for r in results)
    ask = _join(r.ask for r in results)
    block = _join(r.block for r in results)
    context = _join(r.context for r in results)
    system_message = _join(r.system_message for r in results)

    out = {}
    hso = {}
    if event == "PreToolUse":
        if deny:
            hso["permissionDecision"] = "deny"
            hso["permissionDecisionReason"] = deny
        elif ask:
            hso["permissionDecision"] = "ask"
            hso["permissionDecisionReason"] = ask
    elif block and event in EVENTS_WITH_BLOCK:
        out["decision"] = "block"
        out["reason"] = block

    if context and event in EVENTS_WITH_CONTEXT:
        hso["additionalContext"] = context
    if hso:
        hso = {"hookEventName": event, **hso}
        out["hookSpecificOutput"] = hso
    if system_message:
        out["systemMessage"] = system_message
    return 0, (out or None), None


def emit(ctx, results):
    code, obj, err = build_output(ctx.event, results)
    if results:
        ctx.record_actions(results)
    if err:
        sys.stderr.write(err)
        sys.stderr.flush()
        return code
    if obj:
        # ensure_ascii keeps stdout pure ASCII: no Windows codepage surprises.
        sys.stdout.write(json.dumps(obj, ensure_ascii=True))
        sys.stdout.flush()
    return code
