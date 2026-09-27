"""
contract.py -- Tantra Contract: the output contract on domain and sub agents.

Why it exists: every Tantra domain agent and sub-agent ends its answer with
labelled fields (CONFIDENCE, GAPS and, for most, CITATION_CHECK) that the
orchestrator's synthesis and the evaluator depend on. When one is missing,
the orchestrator's Step 7 re-dispatches the whole agent, which redoes all
of its research for one missing line. SubagentStop lets a hook keep the
subagent running with an instruction, so the fix happens inside the same
run and costs a few output tokens instead of a full re-dispatch.

Rules:
  * only tiers domain and sub are checked; entry and bridge agents answer
    the user, so their format is never blocked;
  * required fields = the registry's contract_fields for that agent
    (fallback CONFIDENCE, GAPS when the registry lists none);
  * a field counts when a line starts with it followed by ':' (markdown
    emphasis, a bullet or a heading marker in front is tolerated);
  * a response shorter than min_chars is treated as incomplete too;
  * the response is the SubagentHandback report when the agent delivered
    one (auto mode, Claude Code v2.1.271+), plus any closing text; only
    without a hand-back is it last_assistant_message alone;
  * at most max_blocks_per_agent blocks per agent id, and never while
    stop_hook_active is set, so a model that cannot comply is let go (Claude
    Code itself overrides after 8 consecutive blocks).

est_tokens_avoided = the agent's total tokens so far from meter (the cost of
the re-dispatch this avoids); without a transcript, output chars/4 x 3 as a
labelled rough estimate.
"""
import re

from . import common

DEFAULTS = {
    "mode": "enforce",
    "max_blocks_per_agent": 1,
    "min_chars": 200,
    "fallback_fields": ["CONFIDENCE", "GAPS"],
}
CHECKED_TIERS = {"domain", "sub"}
EXAMPLES = {
    "CONFIDENCE": "'CONFIDENCE: high|medium|low -- reason'",
    "CITATION_CHECK": "'CITATION_CHECK: pass|flagged -- which claims carry sources'",
    "GAPS": "'GAPS: what could not be verified or was out of scope'",
}


def field_present(message, field):
    pattern = r"^\s*(?:[#>*\-]+\s*)?[*_`]*" + re.escape(field) + r"[*_`]*\s*:"
    return re.search(pattern, message, re.MULTILINE | re.IGNORECASE) is not None


def required_fields(ctx, cfg):
    info = ctx.agent_info(ctx.agent_type) or {}
    fields = info.get("contract_fields")
    return list(fields) if fields else list(cfg["fallback_fields"])


def check(ctx, measured):
    """Return (verdict, Result|None); verdict = {"ok", "missing", "short"}."""
    tier = ctx.tier(ctx.agent_type)
    if tier not in CHECKED_TIERS:
        return {"ok": True, "missing": []}, None
    cfg = common.settings(ctx, "contract", DEFAULTS)
    message, _ = common.final_report(ctx)
    missing = [f for f in required_fields(ctx, cfg) if not field_present(message, f)]
    short = len(message.strip()) < int(cfg["min_chars"])
    verdict = {"ok": not missing and not short, "missing": missing, "short": short}
    if verdict["ok"] or cfg["mode"] == "off":
        return verdict, None
    if ctx.payload.get("stop_hook_active") or _blocks_so_far(ctx) >= int(cfg["max_blocks_per_agent"]):
        common.outcome(ctx, "contract", "observe", "contract_let_go", missing=missing, short=short)
        return verdict, None
    result = common.outcome(
        ctx, "contract", cfg["mode"], "contract_block" if cfg["mode"] == "enforce" else "contract_note",
        block=_instruction(message, missing, short), est_tokens_avoided=_avoided(measured, message),
        target=ctx.agent_type, missing=missing, short=short,
    )
    if result is not None and result.block:
        common.append(ctx, "dispatch.jsonl", {"ev": "contract_block", "agent_id": ctx.agent_id,
                                              "agent_type": ctx.agent_type, "missing": missing, "short": short})
    return verdict, result


def _blocks_so_far(ctx):
    return sum(1 for r in common.rows(ctx, "dispatch.jsonl")
               if r.get("ev") == "contract_block" and r.get("agent_id") == ctx.agent_id)


def _instruction(message, missing, short):
    if missing:
        names = ", ".join(missing)
        formats = "; ".join(EXAMPLES.get(f, f"'{f}: ...'") for f in missing)
        text = (
            f"Tantra contract check: the final response is missing {names}. Add only the missing {names} "
            f"line(s) in the required format (e.g. {formats}); the analysis above stands and does not need "
            f"to be redone."
        )
    else:
        text = "Tantra contract check: the final response has all contract fields."
    if short:
        text += (
            f" The final response is also only {len(message.strip())} characters, which is too short to carry "
            f"the findings the parent asked for; restating the findings already gathered completes it without "
            f"new research."
        )
    return text


def _avoided(measured, message):
    total = ((measured or {}).get("tokens") or {}).get("total")
    if isinstance(total, int) and total > 0:
        return total
    return common.estimate_tokens(len(message)) * 3
