"""
product_analytics_pull.py
==========================
Pull real product-usage events (Amplitude, Mixpanel) for the Market
Research & Consumer Insights system's `product-analytics-cohort-retention-
subagent` — the canonical cohort-computation source other sub-agents
(GTM's `product-market-fit-validation-subagent`, Revenue/CRM's
`rfm-segmentation-subagent`) should consume rather than re-deriving their
own retention math (see `cross-system-dispatch-bridge.md`'s file-contract
table).

Read-only. See `product_analytics_connector.py` — no event-tracking/write
function exists.

Run on demand or via cron for a rolling window:
    python3 product_analytics_pull.py --platform amplitude --start 20260801 --end 20260901
    python3 product_analytics_pull.py --platform mixpanel --from-date 2026-08-01 --to-date 2026-09-01
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from product_analytics_connector import pull as pull_analytics  # noqa: E402
from tool_router import write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FIELDNAMES = ["platform", "user_id", "event_name", "event_time", "properties_json"]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--platform", required=True, choices=["amplitude", "mixpanel"])
    parser.add_argument("--start", help="Amplitude: YYYYMMDD")
    parser.add_argument("--end", help="Amplitude: YYYYMMDD")
    parser.add_argument("--from-date", help="Mixpanel: YYYY-MM-DD")
    parser.add_argument("--to-date", help="Mixpanel: YYYY-MM-DD")
    parser.add_argument("--event-names", nargs="*", default=None, help="Optional filter to specific event names")
    args = parser.parse_args()

    config = load_config().get(args.platform, {})
    if args.platform == "amplitude":
        if not args.start or not args.end:
            sys.exit("FATAL: --start and --end are required for --platform amplitude")
        result = pull_analytics("amplitude", config, start=args.start, end=args.end, event_names=args.event_names)
        window = f"{args.start}_{args.end}"
    else:
        if not args.from_date or not args.to_date:
            sys.exit("FATAL: --from-date and --to-date are required for --platform mixpanel")
        result = pull_analytics("mixpanel", config, from_date=args.from_date, to_date=args.to_date,
                                 event_names=args.event_names)
        window = f"{args.from_date}_{args.to_date}"

    output_csv = OUTPUT_DIR / f"product_events_{args.platform}_{window}.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in result.rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    manifest_path = write_source_manifest(output_csv, [result])
    print(f"[{args.platform}] status={result.status} rows={result.row_count} "
          f"errors={[e.reason for e in result.errors]}")
    print(f"Wrote {output_csv}")
    print(f"Source manifest: {manifest_path} — read before computing cohort/retention math against this file.")
    if result.status == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
