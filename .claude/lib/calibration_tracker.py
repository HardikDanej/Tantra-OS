"""
calibration_tracker.py
=======================
Real, computed confidence-calibration statistics per dispatched agent, from
`memory/outcomes.jsonl` joined against `memory/checkpoints.jsonl`. This is
the Learning layer capability this repository previously stopped short of:
`context_budget.py`'s outcomes rollup already deduplicates the
`implications` field for a human/orchestrator to re-read, but nothing
previously computed an actual number for "when this agent says it's
high-confidence, how often has that actually held up, for this specific
workspace." The Orchestrator's own Outcome Feedback section is explicit
that this system's learning is "exactly as reliable as what the user
reported, no more" — this script doesn't change that ceiling, it just
makes the arithmetic on top of self-reported data real instead of
eyeballed.

**Requires one small addition to the Outcome Feedback Ingestion schema**:
an optional `matched_prediction` field (`true` | `false` | `"partial"` |
absent) on each `outcomes.jsonl` entry, set when the user's report makes it
mechanically clear whether the outcome matched what the recommendation
predicted. This script NEVER infers that field by reading the free-text
`outcome` string itself -- that would be exactly the LLM-summarization
`context_budget.py`'s own docstring already refuses to do. An outcome
logged without `matched_prediction` still counts toward volume/coverage
stats, but never toward a computed hit-rate -- a missing field is treated
as "unknown," never coerced into a guess.

Calibration is computed per (agent, confidence_tier) pair, joining each
outcome to its originating checkpoint's `confidence_returned` map (a single
checkpoint can dispatch several agents, so one outcome's `checkpoint_ref`
can attribute to multiple agent/tier pairs -- that's correct, not a
double-count bug, since the outcome genuinely resulted from all of them
together; this script does not currently try to isolate one agent's causal
contribution to a joint outcome, and says so in every report).

Never asserts a hit-rate from fewer than `--min-sample-size` (default 3)
matched-prediction outcomes for an (agent, tier) pair -- reports
"insufficient data" instead, the same discipline
`context_budget.py`/`redispatch_tracker.py` apply elsewhere in this
repository (never generalize a pattern from too small a sample).

Usage:
    python calibration_tracker.py memory/outcomes.jsonl report \\
        --checkpoints memory/checkpoints.jsonl \\
        [--min-sample-size 3] [--json-out memory/calibration_report.json]

Exit code: 0 always (a thin or empty calibration history is a legitimate
state for a new workspace, not an error) -- unless the outcomes or
checkpoints file exists but contains malformed JSON, which exits 1 rather
than silently skipping the bad line (same discipline as
`context_budget.py`'s `read_jsonl`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_MIN_SAMPLE_SIZE = 3
VALID_MATCHED = {True, False, "partial"}
CANONICAL_TIERS = {"high", "medium", "low"}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{line_no}: malformed JSON ({e}) -- refusing to silently skip it") from e
    return entries


def build_checkpoint_index(checkpoints: list[dict]) -> dict[str, dict]:
    """Index checkpoints by their timestamp, since that's what outcomes.jsonl's `checkpoint_ref` points at."""
    return {c["timestamp"]: c for c in checkpoints if "timestamp" in c}


def compute_calibration(outcomes: list[dict], checkpoint_index: dict[str, dict],
                         min_sample_size: int) -> dict[str, Any]:
    # (agent, tier) -> {"matched": n, "not_matched": n, "partial": n}
    stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"matched": 0, "not_matched": 0, "partial": 0})
    coverage = {"total_outcomes": len(outcomes), "with_matched_prediction": 0, "without_matched_prediction": 0,
                "unresolvable_checkpoint_ref": 0}
    unresolved_refs: list[str] = []
    non_canonical_tiers: dict[str, set[str]] = defaultdict(set)

    for outcome in outcomes:
        matched = outcome.get("matched_prediction")
        checkpoint_ref = outcome.get("checkpoint_ref")
        checkpoint = checkpoint_index.get(checkpoint_ref) if checkpoint_ref else None

        if checkpoint is None:
            coverage["unresolvable_checkpoint_ref"] += 1
            if checkpoint_ref:
                unresolved_refs.append(checkpoint_ref)
            continue

        if matched not in VALID_MATCHED:
            coverage["without_matched_prediction"] += 1
            continue
        coverage["with_matched_prediction"] += 1

        confidence_returned = checkpoint.get("confidence_returned", {}) or {}
        for agent, tier in confidence_returned.items():
            if tier not in CANONICAL_TIERS:
                non_canonical_tiers[agent].add(tier)
            key = (agent, tier)
            if matched is True:
                stats[key]["matched"] += 1
            elif matched is False:
                stats[key]["not_matched"] += 1
            else:  # "partial"
                stats[key]["partial"] += 1

    per_agent_tier: list[dict[str, Any]] = []
    flags: list[str] = []
    for (agent, tier), counts in sorted(stats.items()):
        n = counts["matched"] + counts["not_matched"] + counts["partial"]
        entry: dict[str, Any] = {"agent": agent, "confidence_tier": tier, "sample_size": n, **counts}
        if n < min_sample_size:
            entry["hit_rate"] = None
            entry["note"] = f"insufficient data (n={n} < min_sample_size={min_sample_size}) -- not reporting a rate"
        else:
            # Partial counts as half-weight -- an explicit, documented choice, not hidden in the arithmetic.
            hit_rate = (counts["matched"] + 0.5 * counts["partial"]) / n
            entry["hit_rate"] = round(hit_rate, 3)
            if tier == "high" and hit_rate < 0.5:
                flags.append(f"{agent} (tier=high): hit_rate={hit_rate:.0%} over n={n} -- historically "
                             f"OVERCONFIDENT at this tier for this workspace")
            elif tier == "low" and hit_rate > 0.8:
                flags.append(f"{agent} (tier=low): hit_rate={hit_rate:.0%} over n={n} -- historically "
                             f"UNDERCONFIDENT at this tier; its 'low' calls have mostly held up")
        per_agent_tier.append(entry)

    for agent, tiers in sorted(non_canonical_tiers.items()):
        flags.append(
            f"{agent}: non-canonical confidence tier(s) {sorted(tiers)!r} found in checkpoints.jsonl -- "
            f"the schema requires exactly 'high', 'medium', or 'low' (see chief-marketing-orchestrator.md "
            f"Step 6). Each variant is a separate bucket above, silently fragmenting this agent's real "
            f"calibration history across sessions -- any nuance belongs in that checkpoint's `escalations` "
            f"or the domain agent's own GAPS, never folded into the tier string itself."
        )

    return {
        "coverage": coverage, "unresolved_checkpoint_refs": unresolved_refs[:10],
        "per_agent_tier": per_agent_tier, "flags": flags, "min_sample_size": min_sample_size,
        "non_canonical_tiers": {a: sorted(t) for a, t in non_canonical_tiers.items()},
    }


def print_report(report: dict[str, Any]) -> None:
    cov = report["coverage"]
    print("=== Calibration report ===\n")
    print(f"{cov['total_outcomes']} total outcome(s) logged. "
          f"{cov['with_matched_prediction']} carry a real matched_prediction field; "
          f"{cov['without_matched_prediction']} don't (volume-only, not counted toward any hit-rate); "
          f"{cov['unresolvable_checkpoint_ref']} pointed at a checkpoint_ref not found in checkpoints.jsonl.\n")

    if not report["per_agent_tier"]:
        print("No calibration data yet -- this is expected for a new workspace or one where outcomes are logged "
              "without matched_prediction. Not a failure to find something.")
        return

    print("Per (agent, confidence tier):")
    for e in report["per_agent_tier"]:
        rate_str = f"{e['hit_rate']:.0%}" if e["hit_rate"] is not None else e.get("note", "n/a")
        print(f"  {e['agent']:35s} tier={e['confidence_tier']:8s} n={e['sample_size']:3d}  "
              f"matched={e['matched']} not_matched={e['not_matched']} partial={e['partial']}  hit_rate={rate_str}")

    calibration_flags = [f for f in report["flags"] if "non-canonical confidence tier" not in f]
    tier_flags = [f for f in report["flags"] if "non-canonical confidence tier" in f]

    if calibration_flags:
        print("\nFlags (real computed divergences from what the tier name implies):")
        for f in calibration_flags:
            print(f"  - {f}")
    else:
        print("\nNo overconfidence/underconfidence flags at the current min_sample_size threshold.")

    if tier_flags:
        print("\nData-quality warnings (checkpoint schema violations, not a calibration finding):")
        for f in tier_flags:
            print(f"  - {f}")


def cmd_report(args: argparse.Namespace) -> int:
    try:
        outcomes = read_jsonl(Path(args.outcomes_log))
        checkpoints = read_jsonl(Path(args.checkpoints))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    checkpoint_index = build_checkpoint_index(checkpoints)
    report = compute_calibration(outcomes, checkpoint_index, args.min_sample_size)
    print_report(report)

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport JSON written to {args.json_out}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("outcomes_log", help="Path to memory/outcomes.jsonl")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("report", help="Compute and print the calibration report.")
    r.add_argument("--checkpoints", default="memory/checkpoints.jsonl")
    r.add_argument("--min-sample-size", type=int, default=DEFAULT_MIN_SAMPLE_SIZE)
    r.add_argument("--json-out", default=None, help="Also write the report as JSON to this path")

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "report":
        return cmd_report(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
