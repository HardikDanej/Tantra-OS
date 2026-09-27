"""
model_routing.py
==================
The OS blueprint's "Cost & Model Routing" (Section 24) model-tier half:
route the small number of agents where a real model-tier override is
defensible, via Claude Code's own real `model:` subagent-frontmatter field
-- not a paper policy that has no effect on what actually runs.

Why so few overrides (12 of 238 agents), not a blanket policy:
this system's genuinely mechanical work already runs as deterministic
Python (kb_slice.py, citation_guard.py, output_evaluator.py, etc.), never
as an LLM call -- so blueprint Section 24's "use lightweight models for
classification/extraction" principle is already substantially satisfied
by the existing architecture. Nearly everything left that IS an LLM
dispatch is inherently a marketing judgment call (diagnose, brief,
recommend), where downgrading the model is a real quality risk, not a
free cost saving. Blanket-assigning a cheap model to sub-agents whose job
is strategic judgment would contradict this repo's own "honest
confidence, no shortcuts" discipline. So this script overrides only:

  - HAIKU: sub-agents whose real job is markup/structural PATTERN
    DETECTION rather than strategic judgment -- all six are Website
    Development Agent sub-agents that check for a signal's presence
    (a viewport meta tag, a response header, a status code), not agents
    that weigh trade-offs.
  - OPUS: the handful of sub-agents/agents carrying either (a) the
    highest real legal/financial/regulatory exposure in this repository,
    or (b) a genuinely cross-cutting adversarial/multi-system synthesis
    role where a shallow pass is the actual failure mode.
  - Everything else: no override. Unset means "inherit the parent
    session's model" (Claude Code's own documented fallback) -- the
    correct default until a SPECIFIC agent earns a different tier with
    real evidence, the same evidentiary bar every other override in this
    repo already has to clear.

Usage:
    python model_routing.py build              # regenerate model-routing/model_routing.json from the tables below
    python model_routing.py apply               # write/update the model: frontmatter line in every overridden agent file
    python model_routing.py validate            # confirm every agent file's frontmatter matches this policy exactly
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
OUT_DIR = REPO_ROOT / "model-routing"
OUT_JSON = OUT_DIR / "model_routing.json"

VERSION = "1.0.0"

HAIKU_OVERRIDES = {
    "broken-link-dead-page-scanning-subagent":
        "Status-code verification across fetched links -- pattern detection, not judgment.",
    "mobile-responsive-behavior-subagent":
        "Viewport meta tag / responsive CSS pattern presence-checking -- pattern detection, not judgment.",
    "tech-stack-fingerprinting-subagent":
        "CMS/framework identification from markup + response headers against known signatures -- pattern matching.",
    "security-posture-auditing-subagent":
        "HTTPS enforcement / security-header presence-checking -- explicitly black-box signal detection, "
        "never a vulnerability judgment call by the sub-agent's own stated boundary.",
    "accessibility-wcag-auditing-subagent":
        "Alt-text / heading-hierarchy / ARIA-landmark presence-checking against markup -- structural detection, "
        "explicitly not a compliance judgment (that's flagged unverifiable by the sub-agent itself).",
    "js-rendering-dynamic-verification-subagent":
        "Confirms a JS element mounts / a toggle responds via a deterministic script (browser_render.py) -- "
        "verification of a binary outcome, not a strategic call.",
}

OPUS_OVERRIDES = {
    "investor-relations-earnings-release-subagent":
        "The sub-agent's own file calls this 'the highest-stakes sub-agent in this entire roster' -- real "
        "securities-law exposure (Regulation FD, MNPI, forward-looking-statement safe harbor).",
    "labor-relations-union-workplace-comms-subagent":
        "The sub-agent's own file calls this 'the strictest legal refusal gate in this entire repository' -- "
        "real labor-law exposure (the TIPS framework).",
    "ma-due-diligence-intelligence-subagent":
        "The sub-agent's own file calls this 'the highest-stakes sub-agent in this roster' for M&A -- real "
        "confidentiality/valuation/fairness-opinion exposure.",
    "government-relations-public-policy-subagent":
        "Active lobbying/policy-engagement strategy -- real compliance exposure, never a substitute for "
        "lobbying-compliance counsel.",
    "competitor-red-team-agent":
        "Adversarial stress-test of a finalized strategic recommendation across the whole system -- a shallow "
        "pass here is the specific failure mode this agent exists to prevent.",
    "cross-system-dispatch-bridge":
        "Cross-system contradiction-check and insight synthesis across up to 5 standalone agentic systems -- "
        "the highest-complexity single reasoning task in this repository.",
}

FRONTMATTER_RE = re.compile(r"^(---\n)(.*?\n)(---\n)", re.DOTALL)
MODEL_LINE_RE = re.compile(r"^model:\s*.*$", re.MULTILINE)


def _target_model_for(agent_id: str) -> str | None:
    if agent_id in HAIKU_OVERRIDES:
        return "haiku"
    if agent_id in OPUS_OVERRIDES:
        return "opus"
    return None


def _rationale_for(agent_id: str) -> str | None:
    return HAIKU_OVERRIDES.get(agent_id) or OPUS_OVERRIDES.get(agent_id)


def build():
    entries = {}
    for agent_id, rationale in HAIKU_OVERRIDES.items():
        entries[agent_id] = {"model": "haiku", "rationale": rationale}
    for agent_id, rationale in OPUS_OVERRIDES.items():
        entries[agent_id] = {"model": "opus", "rationale": rationale}

    doc = {
        "model_routing_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Only agents listed in 'overrides' get an explicit model: frontmatter field. Every other "
            "agent in this repository (225 of 237) is deliberately left unset, which Claude Code resolves "
            "to 'inherit the parent session's model' -- the correct default for judgment-heavy marketing "
            "work, not a gap. See this script's own module docstring for the full reasoning."
        ),
        "total_agents": len(list(AGENTS_DIR.glob("*.md"))),
        "override_count": len(entries),
        "haiku_count": len(HAIKU_OVERRIDES),
        "opus_count": len(OPUS_OVERRIDES),
        "overrides": entries,
    }
    OUT_DIR.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT_JSON} -- {len(entries)} overrides "
          f"({len(HAIKU_OVERRIDES)} haiku, {len(OPUS_OVERRIDES)} opus) out of {doc['total_agents']} agents.")
    return doc


def _apply_to_file(agent_id: str, model: str) -> str:
    """Returns 'added' | 'updated' | 'already_correct' | 'no_frontmatter'."""
    path = AGENTS_DIR / f"{agent_id}.md"
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "no_frontmatter"
    block = m.group(2)
    existing = MODEL_LINE_RE.search(block)
    if existing and existing.group(0).strip() == f"model: {model}":
        return "already_correct"
    if existing:
        new_block = MODEL_LINE_RE.sub(f"model: {model}", block)
        status = "updated"
    else:
        new_block = block.rstrip("\n") + f"\nmodel: {model}\n"
        status = "added"
    new_text = m.group(1) + new_block + m.group(3) + text[m.end():]
    path.write_text(new_text, encoding="utf-8")
    return status


def apply():
    results = {}
    for agent_id in list(HAIKU_OVERRIDES) + list(OPUS_OVERRIDES):
        model = _target_model_for(agent_id)
        status = _apply_to_file(agent_id, model)
        results[agent_id] = status
        print(f"  {agent_id}: model={model} -> {status}")
    counts = {}
    for status in results.values():
        counts[status] = counts.get(status, 0) + 1
    print(f"\n{counts}")
    return results


def validate():
    problems = []
    override_ids = set(HAIKU_OVERRIDES) | set(OPUS_OVERRIDES)
    for path in sorted(AGENTS_DIR.glob("*.md")):
        agent_id = path.stem
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        block = m.group(2) if m else ""
        existing = MODEL_LINE_RE.search(block)
        existing_value = existing.group(0).split(":", 1)[1].strip() if existing else None
        expected = _target_model_for(agent_id)
        if agent_id in override_ids:
            if existing_value != expected:
                problems.append(f"{agent_id}: expected model={expected!r}, file has {existing_value!r}")
        else:
            if existing_value is not None:
                problems.append(f"{agent_id}: not in override policy but file sets model={existing_value!r} "
                                 f"-- either add it to model_routing.py's tables or remove the frontmatter line")

    if not problems:
        print(f"OK -- {len(override_ids)} overrides all match, 0 unexpected model: fields elsewhere.")
        return 0
    print(f"FAIL -- {len(problems)} mismatch(es):")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "apply":
        apply()
    elif cmd == "validate":
        sys.exit(validate())
    else:
        print(__doc__)
        sys.exit(1)
