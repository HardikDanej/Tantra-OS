"""
press_release_submit.py
========================
Submits ONE press release as a draft/pending-review object to a wire
service, but ONLY if a specific Human-In-The-Loop `approval_gate.py` gate
for this exact release is recorded as "approved". Mirrors
`ads_campaign_draft.py`'s gate-checking pattern exactly — same three
independent layers have to agree before anything is submitted:

1. **Gate approved.** `approval_gate.py`'s ledger must show `event:
   "approved"` for `--gate-id`. Missing, pending, rejected, or superseded
   all refuse — checked here, not just assumed from the caller's say-so.
2. **Write access explicitly confirmed in config.** `write_access_confirmed`
   must be `true` in the wire-service config block — a separate opt-in from
   having credentials configured at all.
3. **Draft/pending-only, hard-coded.** Enforced in `press_wire_connector.py`,
   not here — there is no flag anywhere in this call chain that produces a
   live-distributed release.

**This script is orchestrator-invoked only.** `media-relations-earned-
editorial-agent` and its sub-agents never call this — they structure and
brief a release, never submit it. The `pr-corporate-communications-
orchestrator` opens a HITL gate on the specific release (stakes_class
depends on content — `investor_disclosure` for anything market-moving,
`crisis_response_go` for a crisis statement, `other_high_stakes` otherwise),
presents it to the user, waits for an unambiguous approval, and only then
calls this script with that gate's id.

Release JSON shape:
    {
      "headline": "...", "body": "...", "dateline": "CITY, State, Month Day, Year --",
      "boilerplate": "...", "media_contact": {"name": "...", "email": "...", "phone": "..."},
      "embargo_at": "2026-09-10T09:00:00Z"  // optional
    }

Usage:
    python3 press_release_submit.py --release release.json \\
        --gate-id investor_disclosure_q3_departure --dry-run

    python3 press_release_submit.py --release release.json \\
        --gate-id investor_disclosure_q3_departure \\
        --gates-ledger memory/approval_gates.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude" / "lib"))
from press_wire_connector import WireSubmitResult, submit_wire_draft  # noqa: E402
from approval_gate import get_current_status  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SUBMISSIONS_LOG_PATH = ROOT / "wire_submissions_log.csv"
LOG_FIELDS = ["submitted_at", "gate_id", "platform", "status", "submission_state", "submission_id", "review_url", "release_path"]

REQUIRED_RELEASE_FIELDS = ["headline", "body", "dateline", "boilerplate", "media_contact"]


class ReleaseError(Exception):
    pass


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_release(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ReleaseError(f"release file not found: {path}")
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ReleaseError(f"release is not valid JSON: {e}") from e
    missing = [f for f in REQUIRED_RELEASE_FIELDS if not release.get(f)]
    if missing:
        raise ReleaseError(f"release is missing required field(s): {', '.join(missing)}")
    return release


def append_submissions_log(row: dict[str, Any]) -> None:
    is_new = not SUBMISSIONS_LOG_PATH.exists()
    with open(SUBMISSIONS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True, type=Path, help="Path to the release JSON file")
    parser.add_argument("--gate-id", required=True,
                         help="The approval_gate.py gate_id for this exact release. Must be 'approved' "
                              "in the ledger, unless --dry-run.")
    parser.add_argument("--gates-ledger", type=Path, default=Path("memory/approval_gates.jsonl"),
                         help="Path to approval_gates.jsonl (default: memory/approval_gates.jsonl relative "
                              "to cwd — the workspace root, same convention as approval_gate.py itself)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Validate config + release + gate status; do not submit to the wire service")
    args = parser.parse_args()

    config = load_config()

    try:
        release = load_release(args.release)
    except ReleaseError as e:
        sys.exit(f"FATAL: could not load release {args.release}: {e}")

    print(f"\n{'='*60}")
    print("Press wire draft submission")
    print(f"{'='*60}")
    print(f"Headline: {release['headline']}")
    print(f"Gate:     {args.gate_id}")

    gate_status = get_current_status(args.gates_ledger, args.gate_id) if args.gates_ledger.exists() else None
    print(f"Gate status: {gate_status or '(not found)'}")

    if not args.dry_run and gate_status != "approved":
        sys.exit(
            f"FATAL: gate {args.gate_id!r} is {gate_status or 'UNKNOWN (never created)'}, not 'approved'. "
            f"Refusing to submit to a real wire service without an approved Human-In-The-Loop gate. "
            f"Open or resolve the gate via approval_gate.py first (see pr-corporate-communications-"
            f"orchestrator.md's HITL Approval Gate section)."
        )

    if not config.get("write_access_confirmed") and not args.dry_run:
        sys.exit(
            "FATAL: write_access_confirmed is not true in config.json. This is a separate, explicit "
            "opt-in from having credentials configured — set it to true only once real submission-scoped "
            "credentials are actually in place and the vendor relationship is confirmed."
        )

    if args.dry_run:
        print("\n--dry-run: config + release + gate-status checked, no submission made.")
        print("Would submit a draft/pending-review release (gate would need to be 'approved' and "
              "write_access_confirmed=true for a real run).")
        return

    result: WireSubmitResult = submit_wire_draft(config, **release)

    if result.ok():
        append_submissions_log({
            "submitted_at": result.attempted_at, "gate_id": args.gate_id, "platform": result.platform,
            "status": result.status, "submission_state": result.submission_state or "",
            "submission_id": result.submission_id or "", "review_url": result.review_url or "",
            "release_path": str(args.release),
        })
        print(f"\nOK: draft/pending-review release submitted to {result.platform}.")
        print(f"  submission_state: {result.submission_state} (is_live={result.is_live} — nothing distributes "
              f"until a human reviews and confirms in the vendor's own portal)")
        print(f"  submission_id: {result.submission_id}")
        print(f"  review_url: {result.review_url}")
        print(f"\nLogged to {SUBMISSIONS_LOG_PATH}")
    else:
        print("\nERROR: release NOT submitted.")
        print(f"  reason: {result.error.reason}")
        print(f"  detail: {result.error.detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
