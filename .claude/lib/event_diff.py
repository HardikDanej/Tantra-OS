"""
event_diff.py
===============
The OS blueprint's Section 12 "Event" trigger type (lead.created;
campaign.launched; opportunity.stage_changed) made real for a system that
has no live webhook receiver and, by deliberate design (see the top-level
README's "zero external cost, clone-and-run" architecture), never will.

Honest mechanism: this system already pulls real data on a schedule (the
existing marketing-os-infra pullers -- ad_data_pull.py writes
`01-campaign-intelligence/weekly_unified.csv`, hubspot_historical.py
writes an aggregate report). This script does NOT call any live API
itself -- it only ever diffs a puller's already-written output file
against the last snapshot IT cached, and reports what changed. Detecting
that something changed since the last pull is not the same as receiving a
live push event the instant it happens, and this file is explicit about
that difference rather than implying real-time delivery it can't provide.

Two real event types are wired end-to-end:
  - campaign_launched         -- a new (ad_id) appears in weekly_unified.csv
                                  that wasn't in the last snapshot.
  - opportunity_created /
    opportunity_stage_changed -- a new deal_id appears, or an existing
                                  deal's dealstage differs, in
                                  historical_deals_snapshot.json (see
                                  hubspot_historical.py's additive change,
                                  gap #6, which now writes this file
                                  alongside its existing aggregate report
                                  -- no existing behavior changed).

NOT built, named plainly rather than faked: "lead.created". No connector
in this repo persists individual HubSpot CONTACT records anywhere (see
data-model/core_data_model.json's `customer_contact` entry -- "no
dedicated Pydantic row class exists yet for contacts specifically").
There is nothing real to diff against for that event type yet.

Usage:
    python event_diff.py check --current <path to a puller's real output> \\
        --snapshot <this script's own cache path> --id-field ad_id \\
        [--watch-field campaign_name ...] [--update-snapshot]

Exit codes: 0 if nothing new/changed, 1 if something fired -- so a caller
(or trigger_registry.py's new "event" trigger kind) can treat this like
any other condition check.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_records(path: Path, id_field: str) -> dict[str, dict[str, Any]]:
    """Reads either a .csv or a .json file of records into {id_field value: record}.
    A .json file may be a bare list of records, or a dict with a 'rows'/'deals' key
    holding that list -- both real shapes this repo's own pullers actually produce."""
    if not path.exists():
        return {}
    if path.suffix == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("rows") or data.get("deals") or data.get("records") or []
        else:
            rows = []
    return {str(r[id_field]): r for r in rows if id_field in r and r[id_field]}


def diff_records(previous: dict[str, dict], current: dict[str, dict],
                  watch_fields: list[str]) -> dict[str, Any]:
    new_ids = sorted(set(current) - set(previous))
    removed_ids = sorted(set(previous) - set(current))
    changed = []
    for rid in sorted(set(current) & set(previous)):
        for field in watch_fields:
            old_val = previous[rid].get(field)
            new_val = current[rid].get(field)
            if old_val != new_val:
                changed.append({"id": rid, "field": field, "old": old_val, "new": new_val})
    return {"new_ids": new_ids, "removed_ids": removed_ids, "changed": changed}


def cmd_check(args: argparse.Namespace) -> int:
    current_path = Path(args.current)
    snapshot_path = Path(args.snapshot)

    if not current_path.exists():
        print(f"No current data at {args.current} -- nothing to diff. "
              f"Run the real puller that writes this file first.")
        return 0

    current = load_records(current_path, args.id_field)
    previous = load_records(snapshot_path, args.id_field)
    result = diff_records(previous, current, args.watch_field or [])

    fired = bool(result["new_ids"] or result["changed"])
    if not previous and current:
        print(f"First-ever snapshot for {args.snapshot} -- {len(current)} record(s) baselined, "
              f"nothing reported as 'new' this run (there's no prior state to compare against).")
        fired = False
    else:
        if result["new_ids"]:
            print(f"NEW: {len(result['new_ids'])} record(s) not in the last snapshot: "
                  f"{', '.join(result['new_ids'][:10])}" + (" ..." if len(result['new_ids']) > 10 else ""))
        if result["changed"]:
            print(f"CHANGED: {len(result['changed'])} field-change(s):")
            for c in result["changed"][:10]:
                print(f"  - {c['id']}: {c['field']} {c['old']!r} -> {c['new']!r}")
        if result["removed_ids"]:
            print(f"(informational, not fired) REMOVED from current pull: {len(result['removed_ids'])} record(s) "
                  f"no longer present -- could mean deleted, or just outside this pull's window.")
        if not fired:
            print("No new records, no watched-field changes.")

    if args.update_snapshot:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(list(current.values()), indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nSnapshot updated: {snapshot_path} ({len(current)} record(s)).")

    return 1 if fired else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="Diff a puller's current output against the last cached snapshot.")
    c.add_argument("--current", required=True, help="Path to a real puller's output file (csv or json)")
    c.add_argument("--snapshot", required=True, help="Path where this script caches the last-seen state")
    c.add_argument("--id-field", required=True)
    c.add_argument("--watch-field", action="append", default=[],
                    help="Field to watch for value changes on an already-known id (repeatable)")
    c.add_argument("--update-snapshot", action="store_true",
                    help="After reporting, overwrite the snapshot with the current state "
                         "so the next check diffs from here, not the original baseline")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "check":
        return cmd_check(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
