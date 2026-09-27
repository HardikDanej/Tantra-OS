"""
connectors_guard -- enforces the tantra-connect approvals on every MCP tool
call made inside a Tantra client workspace, and meters those calls.

Why a hook and not just agent instructions: an approval that the model is
merely asked to respect is not a boundary. Claude Code loads MCP servers
without asking in non-interactive runs, many vendor servers bundle write tools
with read tools under one OAuth grant, and the user has claude.ai connectors
attached to every session. The approval record in
`<workspace>/memory/mcp_connections.jsonl` (written only by
.claude/lib/mcp_connector_registry.py after a bound, approved gate) is the
single source of truth, and this module applies it at the moment of the call.

Decision matrix (PreToolUse on mcp__<server>__<tool>, Tantra active, inside a
workspace -- outside a workspace there is no record to enforce, so no opinion):

  server/tool not approved + any subagent     -> deny (enforce; a Tantra agent
                                                 could otherwise launder the call
                                                 through a general-purpose one)
  server/tool not approved + main thread      -> context note, once per server
                                                 per session (assist: the user
                                                 may be using their own tools)
  approved write tool, write gate not approved
  or bound to a different config              -> deny, wherever it is called
  approved read tool, or valid write tool     -> no opinion

The approval chain itself is human-attested: propose -> the user's yes
(approval_gate.py respond) -> the user runs `claude mcp add` -> record-connect.
None of those steps may be taken by a sub-agent, where a prompt injection in
tool or web output could reach a Bash-capable agent and self-approve a
server. So in any sub-agent, a Bash/PowerShell command that records a
connection, answers or opens an mcp_* approval gate, runs `claude mcp
add/remove`, or writes the ledgers, and a Write/Edit aimed at either ledger,
is denied. This is a tripwire for the plain forms, not a sandbox: shell text
can always be obfuscated, which is why tool_decision() also re-checks the
bound gate on every call.

PostToolUse (and PostToolUseFailure, should the dispatcher route it here)
appends one line to `<workspace>/memory/tool_usage_log.jsonl` in
tool_usage_ledger.py's schema: tool="mcp:<server>", calls=1, status, and the
tool name as the note. Tool arguments and results are never logged; they can
carry customer data and credentials.

claude.ai connectors have UUID-like server names; they parse and are handled
exactly like any other server.
"""
import os
import re
import sys

from . import state
from .result import Result

SOURCE = "connectors_guard"

DEFAULTS = {
    "enforce_subagents": True,
    "assist_main_thread": True,
    "log_usage": True,
    "protect_approvals": True,
}

SHELL_TOOLS = {"Bash", "PowerShell"}
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
LEDGER_FILES = {"mcp_connections.jsonl", "approval_gates.jsonl"}
ATTESTED_SHELL = (
    (re.compile(r"mcp_connector_registry[\s\S]*\brecord-connect\b", re.I), "record an MCP connection"),
    (re.compile(r"approval_gate[\s\S]*\b(?:respond|create|supersede)\b[\s\S]*mcp_|"
                r"approval_gate[\s\S]*mcp_[\s\S]*\b(?:respond|create|supersede)\b", re.I),
     "open or answer an MCP connection approval gate"),
    (re.compile(r"\bclaude(?:\.exe)?\s+mcp\s+(?:add|add-json|add-from-claude-desktop|remove)\b", re.I),
     "add or remove an MCP server in Claude Code"),
    (re.compile(r"mcp_connections\.jsonl", re.I), "touch the MCP connection ledger"),
    (re.compile(r"(?:>|\btee\b|add-content|out-file|set-content|sed\s+-i|\bopen\s*\(|\.write)[\s\S]*"
                r"approval_gates\.jsonl|approval_gates\.jsonl[\s\S]*(?:\.write|\bopen\s*\(.*['\"]a)", re.I),
     "write the approval gate ledger"),
)
ATTESTED_REASON = ("Tantra connector approval: a sub-agent may not {what}. Connecting an MCP server is a "
                   "human-attested chain (propose, the user's explicit yes, the user's own `claude mcp add`, "
                   "record-connect) that runs only in the main thread through the tantra-connect skill. Report "
                   "the need to the main thread instead.")

USAGE_LOG_REL = os.path.join("memory", "tool_usage_log.jsonl")
NOTES_FILE = "connectors_notes.jsonl"
HOW_TO_CONNECT = ("Connections are approved per workspace through the tantra-connect skill "
                  "(say \"mk connect <app>\"), which records an approval bound to the exact server "
                  "config and tool list.")


def _registry(ctx):
    lib = os.path.join(ctx.root, ".claude", "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    import mcp_connector_registry  # noqa: E402 - stdlib-only, lives outside the hooks package

    return mcp_connector_registry


def handle(ctx):
    if ctx.event == "PreToolUse" and ctx.agent_id and ctx.tool_name in SHELL_TOOLS | FILE_TOOLS:
        return _guard_attested_steps(ctx)
    if not ctx.tool_name.startswith("mcp__") or not ctx.workspace_dir:
        return None
    settings = ctx.cfg("connectors", DEFAULTS)
    if ctx.event == "PreToolUse":
        return _pre(ctx, settings)
    if ctx.event in ("PostToolUse", "PostToolUseFailure") and settings.get("log_usage", True):
        _log_usage(ctx)
    return None


def _in_subagent(ctx):
    return bool(ctx.agent_id)


def _attested_violation(ctx):
    if ctx.tool_name in SHELL_TOOLS:
        command = ctx.tool_input.get("command")
        if not isinstance(command, str):
            return None
        return next((what for pattern, what in ATTESTED_SHELL if pattern.search(command)), None)
    target = ctx.tool_input.get("file_path") or ctx.tool_input.get("notebook_path") or ""
    if isinstance(target, str) and os.path.basename(target.replace("\\", "/")).lower() in LEDGER_FILES:
        return f"edit {os.path.basename(target)} directly"
    return None


def _guard_attested_steps(ctx):
    if not ctx.cfg("connectors", DEFAULTS).get("protect_approvals", True):
        return None
    what = _attested_violation(ctx)
    if not what:
        return None
    ctx.log_sentinel(SOURCE, "decision", outcome="attested_step_denied", tool_kind=ctx.tool_name)
    return Result(SOURCE, deny=ATTESTED_REASON.format(what=what))


def _pre(ctx, settings):
    reg = _registry(ctx)
    workspace = ctx.workspace_dir
    connections = reg.load_state(workspace)
    decision, reason = reg.tool_decision(workspace, connections, ctx.tool_name)
    if decision in ("read", "write"):
        return None
    kind, _record = reg.classify_tool(connections, ctx.tool_name)
    server, _tool = reg.split_tool_name(ctx.tool_name)
    ctx.log_sentinel(SOURCE, "decision", server=reg.redact(server), outcome="not_approved", kind=kind)
    if kind == "write":
        return Result(SOURCE, deny=f"Tantra connector approval: {reason}. Write tools run only under an approved "
                                   f"mcp_write_connection gate bound to the current config. {HOW_TO_CONNECT}")
    if _in_subagent(ctx):
        if not settings.get("enforce_subagents", True):
            return None
        return Result(SOURCE, deny=f"Tantra connector approval: {reason}. Tantra agents may only call MCP tools "
                                   f"approved for this workspace. {HOW_TO_CONNECT}")
    if not settings.get("assist_main_thread", True) or _already_noted(ctx, server):
        return None
    return Result(SOURCE, context=f"Tantra connector note: {reason}. This call is outside Tantra's approved "
                                  f"connections, so its output is not covered by a Tantra approval. "
                                  f"{HOW_TO_CONNECT}")


def _already_noted(ctx, server):
    path = ctx.session_file(NOTES_FILE)
    if any(row.get("server") == server for row in state.read_jsonl(path)):
        return True
    try:
        state.append_jsonl(path, {"ts": state.now_iso(), "server": server})
    except OSError:
        pass
    return False


def _response_failed(ctx):
    if ctx.event == "PostToolUseFailure":
        return True
    resp = ctx.tool_response
    if isinstance(resp, dict):
        return bool(resp.get("isError") or resp.get("is_error") or resp.get("error"))
    return False


def _log_usage(ctx):
    reg = _registry(ctx)
    server, tool = reg.split_tool_name(ctx.tool_name)
    row = {
        "tool": "mcp:" + reg.redact(server or "unknown"),
        "timestamp": state.now_iso(),
        "calls": 1,
        "status": "error" if _response_failed(ctx) else "ok",
        "cost_usd": None,
        "note": reg.redact(tool or ""),
    }
    try:
        state.append_jsonl(os.path.join(ctx.workspace_dir, USAGE_LOG_REL), row)
    except OSError as exc:
        ctx.log_error(SOURCE, exc)
