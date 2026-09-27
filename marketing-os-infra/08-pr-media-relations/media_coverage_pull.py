"""
media_coverage_pull.py
=======================
Pull real, published news coverage matching a query, for the PR & Corporate
Communications system's `editorial-media-monitoring-clipping-subagent`.
Read-only — see `media_coverage_connector.py`.

Run on demand, or via cron for a rolling weekly digest:
    0 7 * * 1 cd ~/marketing-os/08-pr-media-relations && \\
        /path/to/.venv/bin/python3 media_coverage_pull.py --query "YourBrand" \\
        --from-date $(date -d '7 days ago' +%Y-%m-%d) >> output/cron.log 2>&1
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from media_coverage_connector import pull as pull_coverage  # noqa: E402
from tool_router import write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FIELDNAMES = ["source", "title", "url", "published_at", "snippet", "query"]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--query", required=True, help='e.g. "YourBrand" or "YourBrand OR \\"Your Product\\""')
    parser.add_argument("--from-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--to-date", default=None, help="YYYY-MM-DD")
    args = parser.parse_args()

    config = load_config().get("newsapi", {})
    result = pull_coverage("newsapi", config, query=args.query, from_date=args.from_date, to_date=args.to_date)

    safe_query = "".join(c if c.isalnum() else "_" for c in args.query)[:40]
    output_csv = OUTPUT_DIR / f"coverage_{safe_query}.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in result.rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    manifest_path = write_source_manifest(output_csv, [result])
    print(f"[newsapi] status={result.status} rows={result.row_count} errors={[e.reason for e in result.errors]}")
    print(f"Wrote {output_csv}")
    print(f"Source manifest: {manifest_path} — a FAIL or 'error' status here means treat this as an "
          f"incomplete coverage picture, not a confirmed zero-coverage week.")
    if result.status == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
