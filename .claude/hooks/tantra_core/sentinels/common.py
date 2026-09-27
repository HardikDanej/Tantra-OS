"""
common.py -- shared plumbing for the Tantra sentinel bots.

Why a shared module: every bot reads the same per-session ledgers, walks the
same Claude Code transcripts and has to shape its intervention to the same
four modes. Keeping that in one place keeps each bot file about its own rule
and nothing else, and guarantees they all log interventions the same way,
which is what lets sentinel_report.py total them.

Modes (every bot has one in its DEFAULTS, overridable in ~/.tantra/config.json):
  off      the bot does nothing at all
  observe  the bot evaluates and logs what it WOULD have done, emits nothing
  assist   context notes only; a deny/block is downgraded to a factual note
  enforce  the bot may deny a tool call or block a subagent stop

Per-session state (under TANTRA_HOME/state/<session_id>/):
  dispatch.jsonl   start / stop / returned / contract_block lines (scribe, meter)
  reads.jsonl      echo's index of read-type tool calls, write + compact markers
  claims.jsonl     pulse watchdogs' claim on a dispatch (first claim wins)
  notes.jsonl      notes queued for a parent's next Agent result (meter, contract)
  summaries.jsonl  how far the workspace run summary has been written (scribe)
  outputs/<agent_type>/<agent_id>.txt   each Tantra agent's final response
  handbacks/<agent_id>.txt  a report delivered through the SubagentHandback
                   tool (auto mode), held until that agent's SubagentStop

Token figures are ESTIMATES: chars/4 for text, or the usage the transcript
recorded. Nothing here calls a model.
"""
import hashlib
import json
import os
import time
from collections import Counter
from datetime import datetime

from .. import state
from ..result import Result

MODES = ("off", "observe", "assist", "enforce")
CONTEXT_CAP = 2500
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

# Action names that count as sentinel interventions in reports (the dispatcher
# separately logs generic "context"/"deny" rows for every emitted Result).
INTERVENTIONS = {
    "run_brief", "depth_note", "compaction_brief", "stall",
    "echo_note", "echo_deny", "echo_cross_scope", "echo_dispatch_note",
    "lens_deny", "contract_block", "contract_note",
    "meter_hotspot", "meter_note", "meter_session_budget",
    "boundary_note", "boundary_deny",
}
ESTIMATE_ON_NOTE = {"run_brief"}


# ---- configuration and modes ------------------------------------------------
def settings(ctx, name, defaults):
    cfg = ctx.cfg(name, defaults)
    mode = str(cfg.get("mode") or "").strip().lower()
    cfg["mode"] = mode if mode in MODES else defaults.get("mode", "assist")
    return cfg


def per_tier(value, tier, fallback):
    """Threshold lookup that accepts either one number or a {tier: number} map."""
    if isinstance(value, dict):
        value = value.get(tier, value.get("default"))
        if value is None and isinstance(fallback, dict):
            value = fallback.get(tier, fallback.get("default"))
    if value is None:
        value = fallback.get(tier) if isinstance(fallback, dict) else fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def outcome(ctx, source, mode, action, deny=None, block=None, context=None, system_message=None,
            rewake=None, est_tokens_avoided=0, cap=CONTEXT_CAP, **fields):
    """Log one intervention and shape it to the bot's mode. Returns a Result or None.

    Only an enforced deny/block (or a Run Brief, whose whole purpose is the
    saving) carries its token estimate into the log; a note that the model is
    free to ignore is logged with est_tokens_avoided=0 so totals stay honest.
    """
    if mode == "off":
        return None
    enforced = bool(deny or block)
    if mode == "assist" and enforced:
        context = "\n".join(t for t in (context, deny or block) if t)
        deny = block = None
        enforced = False
    applied = mode != "observe"
    if ctx.agent_id and "agent_id" not in fields:
        fields["agent_id"] = ctx.agent_id
    est = int(est_tokens_avoided or 0) if applied and (enforced or action in ESTIMATE_ON_NOTE) else 0
    ctx.log_sentinel(source, action, mode=mode, applied=applied, est_tokens_avoided=est, **fields)
    if not applied:
        return None
    return Result(
        source,
        deny=clip(deny) if deny else None,
        block=clip(block) if block else None,
        context=clip(context, cap) if context else None,
        system_message=system_message,
        rewake=rewake,
    )


# ---- text helpers -----------------------------------------------------------
def clip(text, limit=CONTEXT_CAP):
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 32].rstrip() + "\n[... trimmed by Tantra]"


def head_tail(text, limit):
    if len(text) <= limit:
        return text
    marker = "\n[... middle of the previous response omitted by Tantra ...]\n"
    head = int((limit - len(marker)) * 0.6)
    tail = limit - len(marker) - head
    return text[:head].rstrip() + marker + text[-tail:].lstrip()


def shorten(text, limit=90):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def fmt_duration(seconds):
    seconds = max(0, int(round(seconds or 0)))
    if seconds < 60:
        return f"{seconds} s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {sec} s" if minutes < 10 and sec else f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"


def fmt_ts(epoch):
    return state.now_iso(epoch)[:19] + "Z" if epoch else "unknown time"


def estimate_tokens(chars):
    return int(chars or 0) // 4


def sha(text, n=16):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:n]


def normalise_prompt(text):
    return " ".join(str(text or "").split()).casefold()


# ---- agents -----------------------------------------------------------------
def target_agent(ctx):
    ti = ctx.tool_input
    name = ti.get("subagent_type") or ti.get("agent_type") or ti.get("agent") or ""
    return str(name).split(":")[-1].strip() or None


def scope_of(ctx):
    return ctx.agent_id or "main"


# ---- session ledgers --------------------------------------------------------
def append(ctx, name, row):
    row = dict(row)
    now = time.time()
    row.setdefault("ts", state.now_iso(now))
    row.setdefault("t", round(now, 3))
    try:
        state.append_jsonl(ctx.session_file(name), row)
    except OSError as exc:
        ctx.log_error("sentinels." + name, exc)
    return row


def rows(ctx, name):
    return state.read_jsonl(ctx.session_file(name))


def output_dir(ctx, agent_type):
    return os.path.join(ctx.session_dir, "outputs", state.safe_name(agent_type))


def output_path(ctx, agent_type, agent_id):
    return os.path.join(output_dir(ctx, agent_type), state.safe_name(agent_id) + ".txt")


def handback_path(ctx, agent_id):
    return os.path.join(ctx.session_dir, "handbacks", state.safe_name(agent_id) + ".txt")


def final_report(ctx):
    """(report text, handback file or None) for the stopping subagent.

    Why: on Claude Code v2.1.271+ a subagent in auto mode delivers its report
    through the SubagentHandback tool, and last_assistant_message then holds
    only the closing text. Scribe records that tool's message (PostToolUse);
    the report is that message plus any closing text that adds to it.
    """
    closing = ctx.payload.get("last_assistant_message") or ""
    if not ctx.agent_id:
        return closing, None
    path = handback_path(ctx, ctx.agent_id)
    handed = read_text(path) if os.path.isfile(path) else ""
    if not handed.strip():
        return closing, None
    if closing.strip() and closing.strip() not in handed:
        handed = handed.rstrip() + "\n\n" + closing.strip()
    return handed, path


def read_text(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read() if limit is None else fh.read(limit)
    except OSError:
        return ""


def write_text(path, text):
    state.ensure_dir(os.path.dirname(path))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


# ---- Claude Code transcripts ------------------------------------------------
def subagents_dir(transcript_path):
    """<proj>/<session>.jsonl -> <proj>/<session>/subagents (or the dir itself)."""
    if not transcript_path:
        return None
    path = os.path.expanduser(transcript_path)
    parent = os.path.dirname(path)
    if os.path.basename(parent) == "subagents":
        return parent
    stem = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(parent, stem, "subagents")


def agent_file(transcript_path, agent_id, suffix=".jsonl"):
    folder = subagents_dir(transcript_path)
    if not folder or not agent_id:
        return None
    name = agent_id if str(agent_id).startswith("agent-") else "agent-" + str(agent_id)
    return os.path.join(folder, name + suffix)


def iter_jsonl(path, max_bytes=None, tail_bytes=None):
    try:
        size = os.path.getsize(path)
        fh = open(path, "rb")
    except OSError:
        return
    with fh:
        if tail_bytes and size > tail_bytes:
            fh.seek(size - tail_bytes)
            fh.readline()
        read = 0
        for raw in fh:
            read += len(raw)
            if max_bytes and read > max_bytes:
                break
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj


def parse_iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def tool_target(tool_input):
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "notebook_path", "path", "url", "pattern", "query", "skill",
                "subagent_type", "command", "description", "prompt"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return shorten(value, 90)
    return ""


def content_chars(content):
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                if isinstance(block.get("text"), str):
                    total += len(block["text"])
                elif isinstance(block.get("content"), (str, list)):
                    total += content_chars(block["content"])
            elif isinstance(block, str):
                total += len(block)
        return total
    if isinstance(content, dict):
        return sum(content_chars(v) for v in content.values() if isinstance(v, (str, list, dict)))
    return 0


def analyse_transcript(path, top=3, max_bytes=60_000_000, tail_bytes=None):
    """Usage totals (deduped by message id), tool-call counts, heaviest tool results."""
    usage_by_msg = {}
    tools = {}
    results = []
    first_ts = last_ts = None
    last_tool = None
    for obj in iter_jsonl(path, max_bytes=max_bytes, tail_bytes=tail_bytes):
        ts = parse_iso(obj.get("timestamp"))
        if ts:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if isinstance(usage, dict):
            key = msg.get("id") or obj.get("uuid") or obj.get("requestId") or len(usage_by_msg)
            merged = usage_by_msg.setdefault(key, dict.fromkeys(USAGE_KEYS, 0))
            for k in USAGE_KEYS:
                value = usage.get(k)
                if isinstance(value, (int, float)) and value > merged[k]:
                    merged[k] = int(value)
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name") or "?"
                target = tool_target(block.get("input"))
                tools[block.get("id")] = (name, target)
                last_tool = {"tool": name, "target": target, "t": ts}
            elif block.get("type") == "tool_result":
                results.append((block.get("tool_use_id"), content_chars(block.get("content"))))
    totals = dict.fromkeys(USAGE_KEYS, 0)
    for usage in usage_by_msg.values():
        for k in USAGE_KEYS:
            totals[k] += usage[k]
    tokens = {
        "input": totals["input_tokens"],
        "output": totals["output_tokens"],
        "cache_read": totals["cache_read_input_tokens"],
        "cache_creation": totals["cache_creation_input_tokens"],
    }
    tokens["total"] = sum(tokens.values())
    counts = Counter(tools[tid][0] for tid, _ in results if tid in tools)
    heaviest = []
    for tid, size in sorted(results, key=lambda r: r[1], reverse=True)[:top]:
        name, target = tools.get(tid, ("?", ""))
        heaviest.append({"tool": name, "target": target, "chars": size})
    return {
        "tokens": tokens,
        "messages": len(usage_by_msg),
        "tool_counts": dict(counts.most_common()),
        "heaviest": heaviest,
        "first_t": first_ts,
        "last_t": last_ts,
        "last_tool": last_tool,
    }


def pending_tool_call(path, tail_bytes=262_144):
    """The last tool_use in a transcript's tail that has no tool_result yet, or None.

    A subagent inside one long tool call (a foreground child dispatch, a slow
    Bash or MCP call) writes nothing to its own transcript until it returns,
    so its silence is not a stall.
    """
    last = None
    answered = set()
    for obj in iter_jsonl(path, tail_bytes=tail_bytes) if path else ():
        msg = obj.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("id"):
                last = {"id": block["id"], "tool": block.get("name") or "?", "target": tool_target(block.get("input"))}
            elif block.get("type") == "tool_result":
                answered.add(block.get("tool_use_id"))
    return last if last and last["id"] not in answered else None


def mtime(path):
    try:
        return os.path.getmtime(path) if path else None
    except OSError:
        return None


# ---- small shared lookups ---------------------------------------------------
def starts_for(ctx, agent_id, dispatch_rows=None):
    return [r for r in (dispatch_rows if dispatch_rows is not None else rows(ctx, "dispatch.jsonl"))
            if r.get("ev") == "start" and r.get("agent_id") == agent_id]


def latest_stop_by_agent(dispatch_rows):
    """Last stop line per agent_id (a resumed subagent stops more than once)."""
    out = {}
    for r in dispatch_rows:
        if r.get("ev") == "stop" and r.get("agent_id"):
            out[r["agent_id"]] = r
    return out
