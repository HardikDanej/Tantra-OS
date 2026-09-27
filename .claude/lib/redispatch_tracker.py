"""
redispatch_tracker.py
======================
Systemic loop-detection / infinite-delegation cap for the Chief Marketing
Orchestrator's re-dispatch cycles.

The SEO Agent already has one local instance of this pattern hard-coded
into its own file: two `fails_quality_bar` E-E-A-T verdicts on the same
piece escalate to the Orchestrator rather than cycling a third revision
blind. That rule only protects one specific loop (SEO <-> Writing, on
quality-bar failures). Every other bounce-back in this system — a creative
brief sent back for revision, a brand-voice draft rejected twice, a
strategy option the Orchestrator keeps asking an agent to redo — has no
equivalent backstop, and relies entirely on the Orchestrator "remembering"
to count and stop itself. That's the same "asked nicely" failure mode the
citation and tool-routing guardrails exist to close elsewhere in this
system: nothing stops a re-dispatch chain from running forever except the
model's own judgment in the moment.

This script is the generalized, structural version: a persisted, append-
only counter per re-dispatch cycle. The Orchestrator is required to call
`check` before issuing ANY re-dispatch of work already dispatched once for
the same objective — not just the SEO E-E-A-T case. The cap is enforced by
this script's exit code and verdict, not by the Orchestrator's own count-
in-its-head.

Cycle identity: the caller supplies a `--cycle-id` naming the loop (e.g.
"seo_eeat:article-042", "ads_brief_revision:ad_71", "strategist_voice").
No brand segment is needed in the id -- the ledger itself already lives
inside one brand's workspace (see below), so the workspace is already
the namespace. This script does not try to infer what counts as "the same
loop" — the Orchestrator, which sees the actual dispatch contracts, is
better positioned to name that consistently than a string-matching
heuristic would be. What this script guarantees is that once a cycle_id
is named consistently, its attempt count is real, persisted, and the cap
is enforced in code — not in the model's memory of how many times it's
already tried.

Usage (the ledger path is relative to the workspace root -- the company
directory this session is running in; one workspace = one brand):
    # Before issuing a re-dispatch for a cycle already attempted at least
    # once, record this attempt and check the cap in one call:
    python redispatch_tracker.py memory/redispatch_log.jsonl check \\
        --cycle-id "seo_eeat:article-042" \\
        --from-agent seo-agent --to-agent writing-content-production-agent \\
        --reason "fails_quality_bar" [--max-attempts 2]

    # Read-only: how many attempts has this cycle had, without recording one
    python redispatch_tracker.py <ledger> status --cycle-id "..."

    # Print full history for a cycle (use this to build the escalation
    # message shown to the user — what was tried, in what order, why it
    # failed each time)
    python redispatch_tracker.py <ledger> history --cycle-id "..."

    # Mark a cycle resolved (it succeeded, or the user explicitly approved
    # restarting it) — attempts before this point no longer count toward
    # the cap if the same cycle_id is reused for a genuinely new attempt
    python redispatch_tracker.py <ledger> resolve --cycle-id "..." --note "..."

Exit codes for `check`: 0 = ALLOW (proceed with the re-dispatch), 1 =
ESCALATE (cap exceeded — do not dispatch again; surface to the user with
the cycle's history instead).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_MAX_ATTEMPTS = 2  # matches the existing SEO E-E-A-T pattern: 2 failures allowed, 3rd attempt escalates

EventType = Literal["attempt", "resolved"]


class RedispatchEvent(BaseModel):
    event: EventType
    cycle_id: str
    from_agent: str | None = None
    to_agent: str | None = None
    reason: str = ""
    note: str = ""
    logged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def read_events(ledger_path: Path) -> list[dict]:
    if not ledger_path.exists():
        return []
    events = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def append_event(ledger_path: Path, event: RedispatchEvent) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")


def attempts_since_last_resolve(events: list[dict], cycle_id: str) -> list[dict]:
    """Attempts for this cycle_id since the most recent 'resolved' marker (or all, if never resolved)."""
    relevant = [e for e in events if e.get("cycle_id") == cycle_id]
    last_resolve_idx = -1
    for i, e in enumerate(relevant):
        if e.get("event") == "resolved":
            last_resolve_idx = i
    since_resolve = relevant[last_resolve_idx + 1:]
    return [e for e in since_resolve if e.get("event") == "attempt"]


def cmd_check(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    events = read_events(ledger_path)
    prior_attempts = attempts_since_last_resolve(events, args.cycle_id)

    # Record this attempt first — the count that matters is "attempts including this one."
    event = RedispatchEvent(
        event="attempt",
        cycle_id=args.cycle_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        reason=args.reason or "",
    )
    append_event(ledger_path, event)

    attempt_number = len(prior_attempts) + 1
    max_attempts = args.max_attempts

    if attempt_number > max_attempts:
        print(f"ESCALATE: cycle '{args.cycle_id}' has now run {attempt_number} times "
              f"(cap: {max_attempts}). Do not dispatch again — surface this to the user "
              f"with the cycle's history (run the `history` command) instead of trying once more.")
        return 1

    remaining = max_attempts - attempt_number
    print(f"ALLOW: cycle '{args.cycle_id}', attempt {attempt_number} of {max_attempts} "
          f"({remaining} remaining before forced escalation).")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    events = read_events(Path(args.ledger))
    prior_attempts = attempts_since_last_resolve(events, args.cycle_id)
    print(f"cycle '{args.cycle_id}': {len(prior_attempts)} attempt(s) recorded since last resolve.")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    events = [e for e in read_events(Path(args.ledger)) if e.get("cycle_id") == args.cycle_id]
    if not events:
        print(f"No history for cycle '{args.cycle_id}'.")
        return 0
    for e in events:
        if e["event"] == "attempt":
            print(f"[{e['logged_at']}] ATTEMPT  {e.get('from_agent', '?')} -> {e.get('to_agent', '?')}"
                  f"  reason: {e.get('reason', '')}")
        else:
            print(f"[{e['logged_at']}] RESOLVED  note: {e.get('note', '')}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    event = RedispatchEvent(event="resolved", cycle_id=args.cycle_id, note=args.note or "")
    append_event(Path(args.ledger), event)
    print(f"Resolved cycle '{args.cycle_id}'. Future attempts under this id start a fresh count.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ledger", help="Path to the redispatch ledger, e.g. memory/redispatch_log.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Record this re-dispatch attempt and check it against the cap")
    p_check.add_argument("--cycle-id", required=True, help="Stable id naming this specific loop")
    p_check.add_argument("--from-agent", default=None)
    p_check.add_argument("--to-agent", default=None)
    p_check.add_argument("--reason", default=None, help="Why this re-dispatch is happening (e.g. 'fails_quality_bar')")
    p_check.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS,
                          help=f"Attempts allowed before escalation (default {DEFAULT_MAX_ATTEMPTS}, "
                               f"matching the existing SEO E-E-A-T pattern)")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", help="Report the current attempt count without recording one")
    p_status.add_argument("--cycle-id", required=True)
    p_status.set_defaults(func=cmd_status)

    p_history = sub.add_parser("history", help="Print full history for a cycle_id")
    p_history.add_argument("--cycle-id", required=True)
    p_history.set_defaults(func=cmd_history)

    p_resolve = sub.add_parser("resolve", help="Mark a cycle resolved; future attempts start a fresh count")
    p_resolve.add_argument("--cycle-id", required=True)
    p_resolve.add_argument("--note", default=None)
    p_resolve.set_defaults(func=cmd_resolve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
