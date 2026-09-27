"""
echo.py -- Tantra Echo: repetition of identical reads, fetches and dispatches.

Why it exists: long Tantra runs re-read the same brand file, re-run the same
Grep or re-fetch the same URL because the model lost track of what it
already has, and orchestrators re-dispatch an identical contract after a
stall or a compaction. Each repeat costs the full result again. Echo keeps
an index of what each scope (a subagent id, or "main") already read and
says so, with facts, before the repeat happens.

Index: state/<sid>/reads.jsonl, written on PostToolUse (one "call" line per
Read / WebFetch / Grep / Glob), plus "write" markers (any Write/Edit, which
can change Grep/Glob results), "exec" markers (PreToolUse of Bash,
PowerShell or an MCP tool, which can create or change files without a
Write/Edit, so earlier Grep/Glob results stop counting) and "compact"
markers (PreCompact, or SessionStart after compaction, in any scope: the
earlier results are no longer in context, so they stop counting).

On PreToolUse, with n = earlier identical calls in the same scope that are
still valid (same key; for Read the file's mtime (ns) and size are unchanged):
  n == 1           -> factual note (the result is already in this context)
  n >= deny_after  -> deny (enforce) naming the earlier calls
A WebFetch of a URL another scope already fetched gets a cross-scope note
naming that agent, and any workspace evidence file that contains the URL.
PreToolUse(Agent) with the same agent type and the same normalised prompt as
a dispatch that already completed this session gets a note pointing at the
saved output (scribe keeps it), since a targeted follow-up is cheaper.

est_tokens_avoided for a denied call = the earlier result's chars/4 (or the
file size/4 for a Read); notes are logged with 0 so totals stay honest.
"""
import json
import os

from . import common

DEFAULTS = {
    "mode": "enforce",
    "deny_after": 2,
    "evidence_scan_files": 200,
    "evidence_scan_bytes": 2_000_000,
}
READ_KEYS = {
    "Read": ("file_path", "offset", "limit"),
    "WebFetch": ("url", "prompt"),
    "Grep": ("pattern", "path", "glob", "output_mode", "-i", "type"),
    "Glob": ("pattern", "path"),
}
PATH_FIELDS = {"file_path", "path"}


# ---- keys -------------------------------------------------------------------
def _norm_path(value, cwd):
    if not isinstance(value, str) or not value.strip():
        return value
    path = os.path.expanduser(value.strip())
    if not os.path.isabs(path):
        path = os.path.join(cwd or "", path)
    return os.path.normcase(os.path.normpath(path))


def call_key(ctx):
    fields = READ_KEYS.get(ctx.tool_name)
    if not fields:
        return None
    parts = {}
    for name in fields:
        value = ctx.tool_input.get(name)
        parts[name] = _norm_path(value, ctx.cwd) if name in PATH_FIELDS else value
    return common.sha(ctx.tool_name + json.dumps(parts, sort_keys=True, default=str), 24), parts


def file_stat(ctx):
    if ctx.tool_name != "Read":
        return None
    try:
        st = os.stat(_norm_path(ctx.tool_input.get("file_path"), ctx.cwd))
    except (OSError, TypeError):
        return None
    return [st.st_mtime_ns, st.st_size]


def describe(tool, parts):
    main = parts.get("file_path") or parts.get("url") or parts.get("pattern") or ""
    extra = ""
    if tool == "Read" and (parts.get("offset") or parts.get("limit")):
        extra = f" (offset {parts.get('offset')}, limit {parts.get('limit')})"
    return common.shorten(f"{tool} {main}{extra}", 160)


# ---- PostToolUse: index -------------------------------------------------------
def on_post(ctx):
    keyed = call_key(ctx)
    if not keyed:
        return None
    key, parts = keyed
    row = {
        "kind": "call", "key": key, "scope": common.scope_of(ctx), "agent_type": ctx.agent_type or "main",
        "tool": ctx.tool_name, "desc": describe(ctx.tool_name, parts), "stat": file_stat(ctx),
        "chars": common.content_chars(ctx.tool_response),
    }
    if ctx.tool_name == "WebFetch":
        row["url"] = parts.get("url")
    common.append(ctx, "reads.jsonl", row)
    return None


def on_write(ctx):
    target = ctx.tool_input.get("file_path") or ctx.tool_input.get("notebook_path")
    common.append(ctx, "reads.jsonl", {"kind": "write", "scope": common.scope_of(ctx),
                                       "path": _norm_path(target, ctx.cwd)})
    return None


def on_exec(ctx):
    common.append(ctx, "reads.jsonl", {"kind": "exec", "scope": common.scope_of(ctx), "tool": ctx.tool_name})
    return None


def on_compact(ctx):
    common.append(ctx, "reads.jsonl", {"kind": "compact", "scope": common.scope_of(ctx)})
    return None


# ---- PreToolUse: repeats --------------------------------------------------------
def valid_priors(index, key, scope, tool, stat):
    floor = 0.0
    for row in index:
        kind = row.get("kind")
        if kind == "compact" and row.get("scope") == scope:
            floor = max(floor, row.get("t") or 0)
        elif kind in ("write", "exec") and tool in ("Grep", "Glob"):
            floor = max(floor, row.get("t") or 0)
    priors = []
    for row in index:
        if row.get("kind") != "call" or row.get("key") != key or row.get("scope") != scope:
            continue
        if (row.get("t") or 0) <= floor:
            continue
        if tool == "Read" and row.get("stat") != stat:
            continue
        priors.append(row)
    return priors


def on_pre(ctx):
    keyed = call_key(ctx)
    if not keyed:
        return None
    cfg = common.settings(ctx, "echo", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    key, parts = keyed
    scope = common.scope_of(ctx)
    index = common.rows(ctx, "reads.jsonl")
    stat = file_stat(ctx)
    priors = valid_priors(index, key, scope, ctx.tool_name, stat)
    desc = describe(ctx.tool_name, parts)
    if priors:
        return _repeat(ctx, cfg, priors, desc, stat)
    if ctx.tool_name == "WebFetch":
        return _cross_scope(ctx, cfg, index, parts.get("url"), scope)
    return None


def _repeat(ctx, cfg, priors, desc, stat):
    n = len(priors)
    where = "in this agent" if ctx.agent_id else "in the main thread"
    times = ", ".join(common.fmt_ts(p.get("t")) for p in priors[-3:])
    unchanged = " and the file is unchanged since (same mtime and size)" if stat else ""
    if n >= int(cfg["deny_after"]):
        chars = max(int(p.get("chars") or 0) for p in priors) or (stat[1] if stat else 0)
        narrower = (
            " If that content was lost to compaction, a narrower Read with offset/limit covering only the "
            "needed lines is the cheaper route." if ctx.tool_name == "Read" else ""
        )
        reason = (
            f"Tantra Echo: this identical call ({desc}) already ran {n} time(s) {where} "
            f"(at {times}){unchanged}; the earlier results are still in this context. Tantra's repetition "
            f"rule allows a call to be repeated {int(cfg['deny_after']) - 1} time(s) per agent.{narrower}"
        )
        return common.outcome(ctx, "echo", cfg["mode"], "echo_deny", deny=reason,
                              est_tokens_avoided=common.estimate_tokens(chars), desc=desc, prior_calls=n)
    note = (
        f"Tantra Echo: {desc} already ran {where} at {times}{unchanged}; the earlier result is still in "
        f"context unless it was compacted."
    )
    return common.outcome(ctx, "echo", cfg["mode"], "echo_note", context=note, desc=desc, prior_calls=n)


def _cross_scope(ctx, cfg, index, url, scope):
    if not url:
        return None
    others = [r for r in index if r.get("kind") == "call" and r.get("url") == url and r.get("scope") != scope]
    if not others:
        return None
    other = others[-1]
    who = other.get("agent_type") if other.get("scope") != "main" else "the main thread"
    note = f"Tantra Echo: {url} was already fetched by {who} ({other.get('scope')}) at {common.fmt_ts(other.get('t'))}."
    evidence = _evidence_file(ctx, cfg, url)
    if evidence:
        note += f" The workspace evidence file {evidence} contains this URL."
    return common.outcome(ctx, "echo", cfg["mode"], "echo_cross_scope", context=note,
                          desc=common.shorten(url, 160), other_scope=other.get("scope"))


def _evidence_file(ctx, cfg, url):
    ws = ctx.workspace_dir
    if not ws:
        return None
    folder = os.path.join(ws, "memory", "evidence", "raw")
    try:
        names = sorted(os.listdir(folder))[: int(cfg["evidence_scan_files"])]
    except OSError:
        return None
    for name in names:
        path = os.path.join(folder, name)
        if os.path.isfile(path) and url in common.read_text(path, int(cfg["evidence_scan_bytes"])):
            return path
    return None


# ---- PreToolUse(Agent): identical dispatch -------------------------------------
def on_pre_agent(ctx):
    target = common.target_agent(ctx)
    if not ctx.is_tantra_agent(target):
        return None
    cfg = common.settings(ctx, "echo", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    prompt_sha = common.sha(common.normalise_prompt(ctx.tool_input.get("prompt")))
    dispatch_rows = common.rows(ctx, "dispatch.jsonl")
    stops = common.latest_stop_by_agent(dispatch_rows)
    for row in reversed(dispatch_rows):
        if row.get("ev") != "returned" or row.get("subagent_type") != target or row.get("prompt_sha") != prompt_sha:
            continue
        stop = stops.get(row.get("agent_id"))
        if row.get("status") != "completed" and stop is None:
            continue
        saved = (stop or {}).get("output_path") or _saved_output(ctx, target, row.get("agent_id"))
        where = f"its saved output is at {saved}" if saved else "its result is in this context's earlier Agent tool result"
        note = (
            f"Tantra Echo: an identical dispatch of {target} (same prompt) completed at "
            f"{common.fmt_ts((stop or row).get('t'))}; {where}. A targeted follow-up for the missing piece "
            f"is usually cheaper than a full re-run."
        )
        return common.outcome(ctx, "echo", cfg["mode"], "echo_dispatch_note", context=note,
                              target=target, desc=f"Agent {target}")
    return None


def _saved_output(ctx, agent_type, agent_id):
    if not agent_id:
        return None
    path = common.output_path(ctx, agent_type, agent_id)
    return path if os.path.isfile(path) else None
