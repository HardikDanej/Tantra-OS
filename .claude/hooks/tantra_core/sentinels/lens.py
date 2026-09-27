"""
lens.py -- Tantra Lens: context discipline for the two biggest file families.

Why it exists: Tantra's orchestrators already document the rule (Step 6,
context discipline): knowledge bases are sliced with kb_slice.py, never read
whole, and a raw .jsonl state log is never passed as an input; it is
digested with context_budget.py. A written rule is advice the model can
forget mid-run; a PreToolUse hook is applied every time. Lens turns those
two documented rules into a deny with the exact replacement command, so the
correction costs one short tool call instead of 20-27k tokens.

What counts as a full read: no `limit`, or a `limit` above full_read_limit
(400 lines). A read with a small limit (with or without offset) is exactly
the narrow read the rule asks for, so it always passes.

Files covered:
  * any knowledge-bases/*.md (under the framework root or a workspace copy)
    larger than kb_max_chars;
  * <workspace>/memory/{checkpoints,outcomes,redispatch_log}.jsonl and
    Tantra's own state/<session>/dispatch.jsonl step ledger larger than
    state_max_chars.
Size is the file's byte size (an upper bound on its characters for UTF-8).
Default mode is "enforce"; "assist" turns the deny into a note.
"""
import os

from . import common

DEFAULTS = {
    "mode": "enforce",
    "kb_max_chars": 12000,
    "state_max_chars": 20000,
    "full_read_limit": 400,
}
STATE_KINDS = {"checkpoints.jsonl": "checkpoints", "outcomes.jsonl": "outcomes", "redispatch_log.jsonl": "redispatch"}


def on_pre_read(ctx):
    cfg = common.settings(ctx, "lens", DEFAULTS)
    if cfg["mode"] == "off":
        return None
    raw = ctx.tool_input.get("file_path")
    if not isinstance(raw, str) or not raw.strip() or not _is_full_read(ctx.tool_input, cfg):
        return None
    path = os.path.normpath(os.path.join(ctx.cwd or "", os.path.expanduser(raw.strip())))
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    kb_rule = _kb_rule(ctx, cfg, path, size)
    return kb_rule if kb_rule is not None else _state_rule(ctx, cfg, path, size)


def _is_full_read(tool_input, cfg):
    limit = tool_input.get("limit")
    try:
        return limit is None or int(limit) > int(cfg["full_read_limit"])
    except (TypeError, ValueError):
        return True


def _kb_rule(ctx, cfg, path, size):
    if not path.lower().endswith(".md") or os.path.basename(os.path.dirname(path)).lower() != "knowledge-bases":
        return None
    if size <= int(cfg["kb_max_chars"]):
        return None
    script = os.path.join(ctx.root, ".claude", "lib", "kb_slice.py")
    reason = (
        f"Tantra Lens: {path} is {size:,} characters (about {common.estimate_tokens(size):,} tokens). Tantra "
        f"knowledge bases run ~20-27k tokens each, and the orchestrators' context discipline (Step 6) is to "
        f"slice them rather than read them whole. The slicing commands are:\n"
        f'  python "{script}" "{path}" outline\n'
        f'  python "{script}" "{path}" search "<term>"\n'
        f'  python "{script}" "{path}" section "<heading>"\n'
        f"A Read with a limit of {int(cfg['full_read_limit'])} lines or fewer also passes."
    )
    return common.outcome(ctx, "lens", cfg["mode"], "lens_deny", deny=reason,
                          est_tokens_avoided=common.estimate_tokens(size), desc=f"Read {path}", rule="kb_slice")


def _state_rule(ctx, cfg, path, size):
    kind = _state_kind(ctx, path)
    if kind is None or size <= int(cfg["state_max_chars"]):
        return None
    script = os.path.join(ctx.root, ".claude", "lib", "context_budget.py")
    reason = (
        f"Tantra Lens: {path} is a raw append-only state log of {size:,} characters (about "
        f"{common.estimate_tokens(size):,} tokens). Tantra's orchestrator rule is to never include a raw "
        f".jsonl state file as an inputs entry; the bounded digest (recent entries verbatim plus a rollup) is:\n"
        f'  python "{script}" "{path}" --kind {kind}\n'
        f"A Read with a limit of {int(cfg['full_read_limit'])} lines or fewer also passes."
    )
    return common.outcome(ctx, "lens", cfg["mode"], "lens_deny", deny=reason,
                          est_tokens_avoided=common.estimate_tokens(size), desc=f"Read {path}", rule=f"digest:{kind}")


def _state_kind(ctx, path):
    name = os.path.basename(path).lower()
    parent = os.path.basename(os.path.dirname(path)).lower()
    if parent == "memory" and name in STATE_KINDS:
        return STATE_KINDS[name]
    home_state = os.path.normcase(os.path.join(ctx.home, "state"))
    grandparent = os.path.normcase(os.path.dirname(os.path.dirname(path)))
    if name == "dispatch.jsonl" and grandparent == home_state:
        return "steps"
    return None
