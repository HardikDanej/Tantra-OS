"""
activation.py -- the wake word. Decides whether Tantra is switched on for a
session, and keeps Tantra agents from being dispatched while it is off.

Why a wake word at all: Tantra's 238 agents are installed at user level, so
their descriptions are visible in every Claude Code session on the machine,
and Claude Code auto-delegates on descriptions. Without an explicit switch
the OS activates on anything that sounds like marketing, in any project.
The owner's rule: "Tantra" stays the product name but never activates
anything; the OS turns on only when the user says "mk" or "MK agent".

Matching (see match_wake):
  * Text the user did not type as an instruction never counts: pasted
    content blocks, fenced code (LF or CRLF), inline code spans and
    blockquote lines are removed first. Leading "[Image #N]" / "[Pasted
    text ...]" placeholders, @file mentions and thinking keywords
    ("ultrathink") are skipped so the user's real first word is seen.
  * ON  -- "mk agent" / "mk-agent" anywhere, any case, not glued to a
           preceding word, path or file name; the glued forms "mkagent" /
           "mk_agent" only as the first word (mid-sentence they are usually
           code identifiers);
        -- the FIRST word is "mk" in any case, optionally "@mk" or "/mk",
           followed by the end, whitespace or , : ; ! ? . or an em dash
           ("mk audit ...", "MK, ...", "mk: ...");
        -- a lowercase mid-sentence vocative "mk," / "mk:" after whitespace
           ("ok mk, run the audit"), except inside a list of 2-3 letter
           language codes ("en, de, mk, sq") or after a label ("Supported: mk:").
  * OFF -- the whole message is "[please] mk [agent] off|stop|exit|sleep|
           deactivate|turn off" with optional politeness ("please", "now",
           "thanks", "for today") and punctuation, or it contains "exit mk" /
           "stop mk" / "quit mk" / "turn off mk" (with or without "agent")
           that is not negated ("don't stop mk agent"). OFF wins over ON. An
           OFF phrase in a session that was not on is silent.
  Known, accepted false positive: a message whose first word is the
  abbreviation "MK"/"Mk" in another sense ("MK Dons ...").

State is sticky per session: activation.jsonl in the session's state dir
gets one line per change ({"ts","event":"on"|"off","by","match"}), never one
per prompt. TANTRA_ACTIVE=1 in the environment forces the OS on for
unattended/cron runs that cannot type the wake word (context.py honours it).

Output rules: silent (zero tokens) when Tantra is off and no wake word was
used; everything added to context is phrased as facts, never as imperative
"system" instructions, which Claude Code's docs warn can trip prompt-
injection defenses.

Hard gate: on PreToolUse(Agent) from the main thread or from a non-Tantra
subagent, a dispatch to one of Tantra's own agents while the OS is off is
denied. Dispatches made inside a Tantra agent and non-Tantra agents (another
plugin's "other:seo-agent" included) are never gated. A missing/empty
registry, or a state dir that cannot be written (so the wake word could not
have been recorded), means no gate (fail open).
"""
import os
import re

from . import state
from .context import own_agent_name
from .result import Result

SOURCE = "activation"

DEFAULTS = {
    "remind_each_prompt": True,
    "hard_gate": True,
}

ROUTES = (
    ("Digital Marketing & Growth (SEO, paid media, website, social, writing, revenue/CRM, growth/CRO)",
     "chief-marketing-orchestrator"),
    ("Brand & Creative", "brand-creative-orchestrator"),
    ("Product Marketing & GTM", "product-marketing-gtm-orchestrator"),
    ("Market Research & Insights", "market-research-insights-orchestrator"),
    ("PR & Corporate Communications", "pr-corporate-communications-orchestrator"),
    ("Holistic or company-wide ask with no single owning system", "enterprise-marketing-orchestrator"),
)

ACTIVATION_BRIEF = (
    "Tantra marketing OS is active in this session because the user's message used the wake word "
    "('mk' or 'MK agent'). The product name 'Tantra' on its own is not a wake word.\n"
    "Tantra routing, one entry point per request:\n"
    + "".join(f"- {area} -> {agent}\n" for area, agent in ROUTES)
    + "Cross-system work goes through that single orchestrator, which uses cross-system-dispatch-bridge. "
    "The wake word itself ('mk', 'MK agent') is not part of the task. "
    "Connecting an app, CRM or ERP to Tantra uses the tantra-connect skill and needs the user's explicit approval. "
    "The user can say 'mk off' to deactivate Tantra for this session."
)
REPEAT_BRIEF = (
    "Tantra marketing OS is active in this session (the wake word was used again). Routing is unchanged: "
    "one entry-point orchestrator per request, and the wake word itself is not part of the task."
)
REMINDER = (
    "Tantra marketing OS remains active in this session; the user can say 'mk off' to deactivate."
)
OFF_CONTEXT = (
    "Tantra marketing OS is now inactive for this session (the user switched it off with 'mk off')."
)
GATE_REASON = (
    "Tantra marketing OS is not active in this session, so Tantra agents are not dispatched. "
    "The user activates it by starting a message with 'mk' or by saying 'MK agent'."
)

_TRUTHY = {"1", "true", "yes", "on"}

_PASTED = re.compile(r"<pasted_content\b[^>]*>.*?(?:</pasted_content\b[^>]*>|\Z)", re.S | re.I)
_FENCE = re.compile(r"^[ \t]*(?P<f>`{3,}|~{3,})[^\n]*\n?.*?(?:^[ \t]*(?P=f)[`~]*[ \t]*$|\Z)", re.S | re.M)
_INLINE_CODE = re.compile(r"(?P<t>`+)(?!`).+?(?<!`)(?P=t)(?!`)")
_BLOCKQUOTE = re.compile(r"^[ \t]*>.*$", re.M)

_NOT_AFTER = r"(?<![\w./\-])"
_NOT_GLUED = r"(?!\w)(?![./\-]\w)"
_MK_NAME = r"mk(?:(?:[ \t]{1,3}|[-_])?agent)?"
# Mid-sentence only the spaced/hyphenated form counts; "mk_agent" / "mkAgent"
# there are usually code identifiers, so the glued forms need the first word.
_MK_AGENT = re.compile(_NOT_AFTER + r"mk(?:[ \t]{1,3}|-)agent" + _NOT_GLUED, re.I)
_MK_AGENT_LEAD = re.compile(r"\A[@/]?mk_?agent" + _NOT_GLUED, re.I)
_FIRST_WORD = re.compile(r"\A[@/]?mk(?=\Z|\s|[,:;!?—]|\.(?!\w))", re.I)
_VOCATIVE = re.compile(r"(?:(?<=\s)|\A)mk(?=[,:])")
_OFF_VERB = r"(?:off|stop|exit|sleep|deactivate|turn[ \t]+off|switch[ \t]+off)\b"
_OFF_TAIL = (r"(?:(?:[ \t]*,[ \t]*|[ \t]+)(?:please|pls|now|thanks|thank[ \t]+you|for[ \t]+now|for[ \t]+today"
             r"|for[ \t]+this[ \t]+session|for[ \t]+the[ \t]+session)\b)*")
_OFF_WHOLE = re.compile(
    r"\A(?:(?:please|ok|okay|hey)[ \t]*,?[ \t]+)?[@/]?" + _MK_NAME + r"[ \t]*[,:—-]?[ \t]+" + _OFF_VERB
    + _OFF_TAIL + r"[ \t]*[.!?]*\Z", re.I
)
_OFF_PHRASE = re.compile(
    r"(?<!not )(?<!n't )(?<!n’t )(?<!never )" + _NOT_AFTER
    + r"(?:exit|stop|quit|deactivate|turn[ \t]+off|switch[ \t]+off)[ \t]+" + _MK_NAME + _NOT_GLUED, re.I
)
# Leading prompt decorations that are not the user's first word: pasted-image
# / pasted-text placeholders, @file mentions (but not "@mk") and thinking keywords.
_LEAD_NOISE = re.compile(
    r"\A(?:\s+|\[(?:Image|Pasted text)\b[^\]\n]*\]"
    r"|@(?!" + _MK_NAME + r"(?![\w./\-]))\S+"
    r"|(?:ultrathink|megathink|think[ \t]+harder|think[ \t]+hard)\b[,:]?)+",
    re.I,
)
_SHORT_CODES_BEFORE = re.compile(r"(?:\b[A-Za-z]{2,3}[ \t]*[,;/][ \t]*)+\Z")
_SHORT_CODES_AFTER = re.compile(r"(?:[ \t]*[,;/][ \t]*[A-Za-z]{2,3}\b(?![ \t]*[A-Za-z]))+")
_LABEL_BEFORE = re.compile(r"\w[ \t]*:[ \t]*\Z")


def _is_vocative(text, m):
    """A lowercase "mk," / "mk:" that addresses the OS, not a language code in
    a list ("en, de, mk, sq") or a value after a label ("Supported: mk: ...")."""
    before, after = text[:m.start()], text[m.end():]
    if _LABEL_BEFORE.search(before):
        return False
    b = _SHORT_CODES_BEFORE.search(before)
    a = _SHORT_CODES_AFTER.match(after)
    codes = (len(re.findall(r"[A-Za-z]{2,3}", b.group())) if b else 0) + \
        (len(re.findall(r"[A-Za-z]{2,3}", a.group())) if a else 0)
    return codes < 2


def strip_quoted(text):
    """Remove text the user pasted or quoted rather than typed as an instruction."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # CRLF would hide a closing fence
    text = _PASTED.sub("\n", text)
    text = _FENCE.sub("\n", text)
    text = _INLINE_CODE.sub(" ", text)
    return _BLOCKQUOTE.sub("", text)


def match_wake(prompt):
    """Return ("on" | "off" | None, rule_name | None) for a user prompt."""
    if not isinstance(prompt, str) or "mk" not in prompt.lower():
        return None, None
    text = _LEAD_NOISE.sub("", strip_quoted(prompt)).strip()
    if _OFF_WHOLE.match(text):
        return "off", "off_phrase"
    if _OFF_PHRASE.search(text):
        return "off", "stop_phrase"
    if _MK_AGENT.search(text) or _MK_AGENT_LEAD.match(text):
        return "on", "mk_agent"
    if _FIRST_WORD.match(text):
        return "on", "first_word"
    if any(_is_vocative(text, m) for m in _VOCATIVE.finditer(text)):
        return "on", "vocative"
    return None, None


def handle(ctx):
    if ctx.event == "UserPromptSubmit":
        return _on_prompt(ctx)
    if ctx.event == "PreToolUse" and ctx.tool_name == "Agent":
        return _gate_dispatch(ctx)
    return None


def _env_forced():
    return (os.environ.get("TANTRA_ACTIVE") or "").strip().lower() in _TRUTHY


def _record(ctx, event, by, match):
    try:
        state.append_jsonl(ctx.activation_path, {"ts": state.now_iso(), "event": event, "by": by, "match": match})
    except OSError as exc:
        ctx.log_error(SOURCE, exc)


def _on_prompt(ctx):
    kind, rule = match_wake(ctx.payload.get("prompt"))
    last = state.last_event(ctx.activation_path) if ctx.session_id else None

    if kind == "off":
        was_on = last == "on" or (_env_forced() and last != "off")
        ctx.active = False
        if not was_on:
            # Nothing to switch off: stay silent rather than tell the model the
            # user said "mk off" (the phrase may be "stop mk production").
            return None
        _record(ctx, "off", "wake_word", rule)
        return Result(SOURCE, context=OFF_CONTEXT, system_message="Tantra: off")

    if kind == "on":
        ctx.active = True
        if last == "on":
            return Result(SOURCE, context=REPEAT_BRIEF)
        _record(ctx, "on", "wake_word", rule)
        return Result(SOURCE, context=ACTIVATION_BRIEF, system_message="Tantra: active (wake word detected)")

    if not ctx.active:
        return None
    if _env_forced() and last is None:
        _record(ctx, "on", "env", "TANTRA_ACTIVE")
        return Result(SOURCE, context=ACTIVATION_BRIEF, system_message="Tantra: active (TANTRA_ACTIVE=1)")
    if ctx.cfg("activation", DEFAULTS).get("remind_each_prompt", True):
        return Result(SOURCE, context=REMINDER)
    return None


def dispatch_target(tool_input):
    """The agent name an Agent/Task call targets. Tantra's own "tantra:" plugin
    prefix is dropped; any other namespace is kept, so another plugin's agent
    that shares a short name with a Tantra agent is not mistaken for it."""
    for key in ("subagent_type", "agent_type", "agent"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return own_agent_name(value.strip().lower())
    return None


def _state_writable(ctx):
    """Can this session's activation state be written? If not, a wake word
    could never be recorded, so the gate must fail open instead of denying."""
    try:
        state.ensure_dir(ctx.session_dir)
        with open(ctx.activation_path, "a", encoding="utf-8"):
            pass
        return True
    except OSError as exc:
        ctx.log_error(SOURCE, exc)
        return False


def _gate_dispatch(ctx):
    if not ctx.cfg("activation", DEFAULTS).get("hard_gate", True):
        return None
    # Dispatches from inside a Tantra agent are its own chain of command. A
    # non-Tantra subagent (general-purpose, Explore, ...) is gated like the
    # main thread, or it would be a way around the switch.
    if ctx.agent_id and ctx.is_tantra_agent(ctx.agent_type):
        return None
    target = dispatch_target(ctx.tool_input)
    if not target or ctx.active or not ctx.is_tantra_agent(target):
        return None
    if not _state_writable(ctx):
        return None
    return Result(SOURCE, deny=GATE_REASON)
