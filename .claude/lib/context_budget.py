"""
context_budget.py
==================
Bounded, deterministic digest of a brand's growing JSONL state logs --
checkpoints.jsonl, outcomes.jsonl, redispatch_log.jsonl -- for use in a
dispatch contract's INPUTS field, instead of the raw file.

The problem this solves: the Orchestrator's own Step 5 says a dispatch
contract's INPUTS should include "relevant history from outcomes.jsonl if
any exists for this brand." That's fine on entry 3. On entry 300 (a year
of weekly runs), "include the relevant history" either means someone
manually decides what's relevant every single time (inconsistent, easy
to skip under time pressure), or the whole file gets pasted in and the
contract's token cost grows linearly with the brand's age forever, most
of it irrelevant to the specific thing being dispatched right now.

This script is not an LLM summarizer -- these logs are structured JSON
(the Orchestrator's own defined schema, not free prose), so a real
aggregation over the fields is possible without spending a model call:

- The most recent N entries are kept VERBATIM (raw JSON) -- these are
  the ones actually likely to matter for "what happened last time."
- Everything older is compacted into a ROLLUP: counts, distributions,
  and (for outcomes specifically) the deduplicated list of "implications"
  strings -- the actual load-bearing text for the kind of pattern
  statement the Orchestrator's Outcome Feedback section describes
  ("the last three content-led growth pushes underperformed..."),
  without carrying every full outcome record just to get there.

This bounds token cost at O(keep_recent + rollup_size) regardless of how
large the underlying file grows -- the digest for a 300-entry file and a
30-entry file differ only in the rollup's counts, not in linear length.

Usage (paths are relative to the workspace root -- the company directory
this session is running in; one workspace = one brand, no slug needed):
    python context_budget.py memory/checkpoints.jsonl --kind checkpoints
    python context_budget.py memory/outcomes.jsonl --kind outcomes
    python context_budget.py memory/redispatch_log.jsonl --kind redispatch
    python context_budget.py memory/outcomes.jsonl --kind outcomes --keep-recent 8 --json-out digest.json
    python context_budget.py ~/.tantra/state/<session_id>/dispatch.jsonl --kind steps

The `steps` kind digests the step ledger Tantra's hooks write per session
(the scribe sentinel's dispatch.jsonl): which agents ran, how long, how
many output tokens, which ones missed contract fields. An orchestrator that
needs "what has this session already dispatched" reads this digest instead
of re-reading its own history.

Prints a human-readable digest to stdout, ready to paste into a dispatch
contract's INPUTS field. Exit code 1 if the file exists but a line fails
to parse (never silently drop a malformed entry and present a clean-
looking digest as if the file were fully readable; the hook-written
`steps` ledger is the one exception: a torn line there is skipped and the
digest names how many were skipped and where) or if --kind doesn't
match a recognized log shape; exit 0 (with an explicit "no history yet"
digest) if the file doesn't exist yet -- that is a legitimate state for a
new brand, not an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_KEEP_RECENT = 5


def estimate_tokens(text: str) -> int:
    """Rough heuristic (chars / 4), not an exact tokenizer -- good enough to compare orders of magnitude."""
    return len(text) // 4


def read_jsonl(path: Path, skipped: list | None = None) -> list[dict]:
    """Parse every line. A malformed line raises, unless `skipped` is given:
    then its line number is recorded there (and reported by the caller) so
    the digest still says how much of the file it could not read."""
    entries = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            if skipped is None:
                raise ValueError(f"{path}:{line_no}: malformed JSON ({e}) -- refusing to silently skip it") from e
            skipped.append(line_no)
    return entries


# Kinds whose file is written by Tantra's hooks from many concurrent
# processes (not by an orchestrator step): a torn line there is a known,
# bounded hazard, so it is skipped and COUNTED in the digest, never hidden.
TOLERANT_KINDS = {"steps"}


# ---------------------------------------------------------------------------
# Kind-specific rollups
# ---------------------------------------------------------------------------

def rollup_checkpoints(older: list[dict]) -> dict:
    dispatched_to = Counter()
    confidence = Counter()
    artifacts = set()
    escalations = []
    for e in older:
        for agent in e.get("dispatched_to", []) or []:
            dispatched_to[agent] += 1
        for tier in (e.get("confidence_returned") or {}).values():
            confidence[tier] += 1
        for a in e.get("artifacts_updated", []) or []:
            artifacts.add(a)
        for esc in e.get("escalations", []) or []:
            if esc and esc not in escalations:
                escalations.append(esc)
    return {
        "older_entry_count": len(older),
        "dispatched_to_frequency": dict(dispatched_to.most_common()),
        "confidence_distribution": dict(confidence),
        "artifacts_ever_updated": sorted(artifacts),
        "distinct_escalations": escalations[:10],
        "escalations_truncated": len(escalations) > 10,
    }


def rollup_outcomes(older: list[dict]) -> dict:
    action_taken = Counter()
    outcome_confidence = Counter()
    implications = []
    for e in older:
        if e.get("action_taken"):
            action_taken[e["action_taken"]] += 1
        if e.get("outcome_confidence"):
            outcome_confidence[e["outcome_confidence"]] += 1
        impl = (e.get("implications") or "").strip()
        if impl and impl not in implications:
            implications.append(impl)
    return {
        "older_entry_count": len(older),
        "action_taken_distribution": dict(action_taken),
        "outcome_confidence_distribution": dict(outcome_confidence),
        "distinct_implications": implications[:10],
        "implications_truncated": len(implications) > 10,
    }


def rollup_redispatch(older: list[dict]) -> dict:
    cycles: dict[str, dict] = {}
    for e in older:
        cid = e.get("cycle_id")
        if not cid:
            continue
        c = cycles.setdefault(cid, {"attempts": 0, "resolved": False, "reasons": []})
        if e.get("event") == "attempt":
            c["attempts"] += 1
            reason = e.get("reason") or ""
            if reason and reason not in c["reasons"]:
                c["reasons"].append(reason)
        elif e.get("event") == "resolved":
            c["resolved"] = True
    ever_hit_cap = [cid for cid, c in cycles.items() if c["attempts"] >= 2]
    return {
        "older_entry_count": len(older),
        "distinct_cycles": len(cycles),
        "cycles_that_reached_the_cap": ever_hit_cap[:10],
        "unresolved_cycles": [cid for cid, c in cycles.items() if not c["resolved"] and c["attempts"] > 0][:10],
    }


def rollup_steps(older: list[dict]) -> dict:
    """Tantra's hook-written step ledger (~/.tantra/state/<session>/dispatch.jsonl).

    One line per start / stop / returned / contract_block event, written by
    the scribe sentinel. A resumed or contract-fixed agent stops more than
    once, so the latest stop per agent_id is the one that counts.
    """
    events = Counter(e.get("ev") or "unknown" for e in older)
    stops: dict[str, dict] = {}
    for e in older:
        if e.get("ev") == "stop" and e.get("agent_id"):
            stops[e["agent_id"]] = e
    by_agent = Counter(s.get("agent_type") or "unknown" for s in stops.values())
    by_tier = Counter(s.get("tier") or "unknown" for s in stops.values())
    durations = sorted(s["duration_s"] for s in stops.values() if isinstance(s.get("duration_s"), (int, float)))
    output_tokens = sum(((s.get("tokens") or {}).get("output") or 0) for s in stops.values())
    contract_misses = sorted({s.get("agent_type") for s in stops.values() if s.get("contract_ok") is False} - {None})
    statuses = Counter(e.get("status") or "unknown" for e in older if e.get("ev") == "returned")
    started = {e.get("agent_id") for e in older if e.get("ev") == "start" and e.get("agent_id")}
    return {
        "older_entry_count": len(older),
        "event_counts": dict(events),
        "completed_dispatches_by_agent": dict(by_agent.most_common()),
        "completed_dispatches_by_tier": dict(by_tier),
        "duration_s_median": durations[len(durations) // 2] if durations else None,
        "duration_s_max": durations[-1] if durations else None,
        "output_tokens_total": output_tokens,
        "agents_missing_contract_fields": contract_misses[:10],
        "returned_status_distribution": dict(statuses),
        "started_without_recorded_stop": len(started - set(stops)),
    }


ROLLUP_FUNCS = {
    "checkpoints": rollup_checkpoints,
    "outcomes": rollup_outcomes,
    "redispatch": rollup_redispatch,
    "steps": rollup_steps,
}


# ---------------------------------------------------------------------------
# Digest assembly
# ---------------------------------------------------------------------------

def build_digest(path: Path, kind: str, keep_recent: int) -> dict:
    if not path.exists():
        return {
            "kind": kind,
            "file": str(path),
            "exists": False,
            "recent": [],
            "rollup": None,
            "estimated_tokens_full_file": 0,
            "estimated_tokens_digest": 0,
        }

    skipped: list | None = [] if kind in TOLERANT_KINDS else None
    entries = read_jsonl(path, skipped)
    recent = entries[-keep_recent:] if keep_recent > 0 else []
    older = entries[: max(0, len(entries) - keep_recent)]
    rollup = ROLLUP_FUNCS[kind](older) if older else None

    full_text = path.read_text(encoding="utf-8")
    digest_obj = {"recent": recent, "rollup": rollup}
    digest_text = json.dumps(digest_obj)

    return {
        "kind": kind,
        "file": str(path),
        "exists": True,
        "total_entries": len(entries),
        "recent_count": len(recent),
        "recent": recent,
        "rollup": rollup,
        "estimated_tokens_full_file": estimate_tokens(full_text),
        "estimated_tokens_digest": estimate_tokens(digest_text),
        "malformed_lines_skipped": skipped or [],
    }


def print_digest(d: dict) -> None:
    print(f"=== Context budget: {d['kind']} ({d['file']}) ===\n")

    if not d["exists"]:
        print("No history yet for this brand/kind -- this is a legitimate empty state, "
              "not a failure to find the file.")
        return

    print(f"{d['total_entries']} total entries. Showing {d['recent_count']} most recent verbatim; "
          f"{d['rollup']['older_entry_count'] if d['rollup'] else 0} older entries rolled up below.\n")
    bad = d.get("malformed_lines_skipped") or []
    if bad:
        print(f"NOTE: {len(bad)} malformed (torn) line(s) could not be parsed and are NOT in this digest: "
              f"line(s) {', '.join(str(n) for n in bad[:20])}{' ...' if len(bad) > 20 else ''}.\n")

    print("RECENT (verbatim):")
    for e in d["recent"]:
        print(f"  {json.dumps(e)}")

    if d["rollup"]:
        print(f"\nOLDER-HISTORY ROLLUP ({d['rollup']['older_entry_count']} entries):")
        for k, v in d["rollup"].items():
            if k == "older_entry_count":
                continue
            print(f"  {k}: {v}")

    saved_pct = 0.0
    if d["estimated_tokens_full_file"]:
        saved_pct = 100 * (1 - d["estimated_tokens_digest"] / d["estimated_tokens_full_file"])
    print(f"\nEstimated tokens if the FULL raw file were included: ~{d['estimated_tokens_full_file']:,}")
    print(f"Estimated tokens for this digest instead: ~{d['estimated_tokens_digest']:,}")
    print(f"Estimated savings: ~{saved_pct:.0f}%")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("state_file", help="Path to a *.jsonl state log, e.g. memory/checkpoints.jsonl")
    parser.add_argument("--kind", required=True, choices=list(ROLLUP_FUNCS.keys()))
    parser.add_argument("--keep-recent", type=int, default=DEFAULT_KEEP_RECENT)
    parser.add_argument("--json-out", default=None, help="Also write the digest as JSON to this path")
    args = parser.parse_args()

    try:
        digest = build_digest(Path(args.state_file).expanduser(), args.kind, args.keep_recent)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print_digest(digest)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(digest, indent=2), encoding="utf-8")
        print(f"\nDigest JSON written to {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
