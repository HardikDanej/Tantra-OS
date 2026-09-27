"""
output_evaluator.py
====================
Deterministic quality gate on ONE dispatched agent's returned output, run
by whichever orchestrator dispatched it, at Step 1 of SYNTHESIZE ("Collect
and Classify") before the output is trusted enough to synthesize around.

This is the Evaluation layer this repository previously covered only
partially: `citation_guard.py` checks whether cited facts are actually
evidenced, and `evals/*.md` are dev-time smoke tests run by a human before
an agent ships, not a runtime check on a live dispatch's actual output.
Nothing previously checked, at runtime, whether a returned block is even
STRUCTURALLY complete (has the sections the contract's `required_output_shape`
demanded), whether a self-reported CONFIDENCE tier is a real value rather
than a missing or invented one, or whether a strategic dispatch's two
"genuinely distinct options" are actually distinct rather than the same
idea worded twice -- all previously trusted entirely on the receiving
orchestrator's own read, with no computed check behind it.

This script does NOT judge whether an output is factually correct or a
good recommendation -- that's a judgment call the orchestrator's own
Step 2/3 synthesis (Epistemic Uncertainty Mapping, Self-Correction) still
makes, and `citation_guard.py` still owns fact-vs-evidence checking. This
script only catches STRUCTURAL and MECHANICAL failures a human reviewer
would also catch on a careful read -- a missing required section, an
invalid confidence value, GAPS left empty on a low-confidence claim, two
strategic options that are near-duplicates of each other -- the kind of
thing that's easy to miss when reading a long, confidently-worded block of
prose, and cheap to check deterministically instead.

Verdicts:
- PASS -- every structural check passed, nothing to flag.
- PASS_WITH_FLAGS -- no hard failure, but something worth a second look
  (e.g. a low-confidence claim with an empty GAPS list). Proceed, but the
  flags belong in the orchestrator's own Step 2/3 reasoning, not silently
  dropped.
- FAIL -- a required section is missing, CONFIDENCE is missing/invalid, or
  (for a strategic dispatch) the two options are near-duplicates. Send the
  dispatch back per Step 7's re-dispatch/loop-detection discipline rather
  than synthesizing around a structurally broken output.

Usage:
    python output_evaluator.py evaluate \\
        --agent seo-agent --dispatch-kind diagnostic \\
        --required-shape OUTPUT,CONFIDENCE,GAPS,CITATION_CHECK \\
        --output-file /tmp/agent_output.txt \\
        --evaluations-log memory/evaluations.jsonl

    python output_evaluator.py evaluate \\
        --agent marketing-strategist-agent --dispatch-kind strategic \\
        --required-shape "OPTION_A,OPTION_B,GAPS" \\
        --output-file /tmp/agent_output.txt \\
        --evaluations-log memory/evaluations.jsonl

Exit codes: 0 for PASS/PASS_WITH_FLAGS, 1 for FAIL -- a calling orchestrator
that treats a non-zero exit as "do not synthesize this yet, resolve it
first" gets the loop-detection discipline for free rather than having to
remember to check the verdict string itself.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

VALID_CONFIDENCE_TIERS = {"high", "medium", "low"}
NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # difflib ratio above this -> "may not be genuinely distinct"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_section(text: str, label: str) -> str | None:
    """
    Extract the content of a `LABEL: ...` or `LABEL\\n...` section, up to
    the next all-caps section label or end of text. Matches this
    repository's Contract Compliance block convention loosely enough to
    tolerate minor formatting variance (a colon vs. a newline after the
    label, extra whitespace) without being so loose it matches unrelated
    prose that happens to contain the word.
    """
    pattern = rf"^\s*{re.escape(label)}\s*:?\s*\n?(.*?)(?=^\s*[A-Z][A-Z_ ]{{2,}}\s*:|\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else None


def evaluate(agent: str, dispatch_kind: str, required_shape: list[str], output_text: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    flags: list[str] = []
    hard_failures: list[str] = []

    # 1. Structural compliance -- every section in required_output_shape must be present and non-empty.
    sections: dict[str, str | None] = {}
    for label in required_shape:
        clean_label = re.sub(r"\s*\(.*\)$", "", label).strip()  # strip a trailing "(claim, evidence, ...)" hint
        content = _find_section(output_text, clean_label)
        sections[clean_label] = content
        if content is None:
            hard_failures.append(f"required section {clean_label!r} not found in output")
        elif not content.strip():
            hard_failures.append(f"required section {clean_label!r} is present but empty")
    checks.append({"check": "structural_compliance", "required": required_shape,
                   "found": {k: (v is not None and bool(v.strip())) for k, v in sections.items()}})

    # 2. Confidence tier validity.
    confidence_text = sections.get("CONFIDENCE")
    confidence_tier = None
    if confidence_text:
        m = re.search(r"\b(high|medium|low)\b", confidence_text, re.IGNORECASE)
        confidence_tier = m.group(1).lower() if m else None
    if "CONFIDENCE" in [re.sub(r"\s*\(.*\)$", "", l).strip() for l in required_shape]:
        if confidence_text is None:
            pass  # already recorded as a structural hard failure above
        elif confidence_tier is None:
            hard_failures.append(f"CONFIDENCE section present but no recognizable tier "
                                  f"({sorted(VALID_CONFIDENCE_TIERS)}) found in it: {confidence_text[:100]!r}")
    checks.append({"check": "confidence_tier_valid", "tier_found": confidence_tier})

    # 3. GAPS non-emptiness on low/medium confidence -- a hedge with nothing named behind it is suspicious.
    gaps_text = sections.get("GAPS")
    if confidence_tier in ("low", "medium") and gaps_text is not None and not gaps_text.strip():
        flags.append(f"CONFIDENCE is {confidence_tier!r} but GAPS is empty -- an unjustified hedge, "
                      f"or a real gap that went unnamed")
    checks.append({"check": "gaps_present_on_uncertain_confidence", "confidence_tier": confidence_tier,
                   "gaps_empty": bool(gaps_text is not None and not gaps_text.strip())})

    # 4. CITATION_CHECK presence + internal consistency, when required.
    normalized_required = [re.sub(r"\s*\(.*\)$", "", l).strip() for l in required_shape]
    if "CITATION_CHECK" in normalized_required:
        citation_text = sections.get("CITATION_CHECK")
        if citation_text:
            failed = bool(re.search(r"\bFAIL\b", citation_text, re.IGNORECASE))
            output_text_section = sections.get("OUTPUT") or ""
            if failed and re.search(r"\bunverified\b", citation_text, re.IGNORECASE):
                # A FAIL naming an unverified claim should not also appear asserted as plain fact in OUTPUT --
                # this is a heuristic substring check, not a semantic one, so it only ever flags, never hard-fails.
                unverified_terms = re.findall(r'"([^"]{4,60})"', citation_text)
                for term in unverified_terms:
                    if term.lower() in output_text_section.lower():
                        flags.append(f"CITATION_CHECK flags {term!r} as unverified, but it still appears "
                                      f"stated as fact in OUTPUT -- resolve before treating this as complete")
        checks.append({"check": "citation_check_consistency", "present": citation_text is not None})

    # 5. Strategic dispatch: two options must be genuinely distinct, not near-duplicates.
    if dispatch_kind == "strategic":
        option_labels = [l for l in normalized_required if re.match(r"^OPTION_[A-Z0-9]+$", l)]
        option_texts = {l: sections.get(l) for l in option_labels if sections.get(l)}
        if len(option_texts) < 2:
            hard_failures.append(f"dispatch_kind is 'strategic' but fewer than 2 populated OPTION_* "
                                  f"sections were found ({list(option_texts.keys())})")
        else:
            names = list(option_texts.keys())
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = option_texts[names[i]], option_texts[names[j]]
                    ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
                    checks.append({"check": "option_distinctness", "pair": [names[i], names[j]],
                                   "similarity_ratio": round(ratio, 3)})
                    if ratio >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD:
                        hard_failures.append(
                            f"{names[i]} and {names[j]} are {ratio:.0%} textually similar (threshold "
                            f"{NEAR_DUPLICATE_SIMILARITY_THRESHOLD:.0%}) -- likely two flavors of the same idea, "
                            f"not two genuinely distinct options; send back per Step 3's anti-pattern #12"
                        )

    verdict = "FAIL" if hard_failures else ("PASS_WITH_FLAGS" if flags else "PASS")
    return {
        "timestamp": now(), "agent": agent, "dispatch_kind": dispatch_kind,
        "required_shape": required_shape, "verdict": verdict,
        "hard_failures": hard_failures, "flags": flags, "checks": checks,
    }


def cmd_evaluate(args: argparse.Namespace) -> int:
    output_path = Path(args.output_file)
    if not output_path.exists():
        print(f"ERROR: --output-file {output_path} does not exist.", file=sys.stderr)
        return 1
    output_text = output_path.read_text(encoding="utf-8")
    required_shape = [s.strip() for s in args.required_shape.split(",") if s.strip()]

    result = evaluate(args.agent, args.dispatch_kind, required_shape, output_text)

    log_path = Path(args.evaluations_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    print(f"=== output_evaluator: {args.agent} ({args.dispatch_kind}) -> {result['verdict']} ===\n")
    if result["hard_failures"]:
        print("HARD FAILURES (send this dispatch back, do not synthesize around it):")
        for hf in result["hard_failures"]:
            print(f"  - {hf}")
    if result["flags"]:
        print("FLAGS (proceed, but carry these into Step 2/3 of synthesis):")
        for fl in result["flags"]:
            print(f"  - {fl}")
    if result["verdict"] == "PASS":
        print("All structural checks passed.")
    print(f"\nLogged to {log_path}")

    return 1 if result["verdict"] == "FAIL" else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("evaluate", help="Evaluate one dispatched agent's returned output.")
    e.add_argument("--agent", required=True, help="The dispatched agent's id, e.g. seo-agent")
    e.add_argument("--dispatch-kind", required=True, choices=["diagnostic", "strategic"])
    e.add_argument("--required-shape", required=True,
                    help="Comma-separated section labels from the dispatch contract's required_output_shape, "
                         "e.g. 'OUTPUT,CONFIDENCE,GAPS,CITATION_CHECK' or 'OPTION_A,OPTION_B,GAPS'")
    e.add_argument("--output-file", required=True, help="Path to a text file containing the agent's raw returned output")
    e.add_argument("--evaluations-log", default="memory/evaluations.jsonl")

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "evaluate":
        return cmd_evaluate(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
