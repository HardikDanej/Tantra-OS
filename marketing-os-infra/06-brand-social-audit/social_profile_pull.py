"""
social_profile_pull.py
=======================
Weekly pull of the brand's own owned social profiles' public metrics
(Instagram, LinkedIn), for the Brand & Creative Marketing system's
`organic-social-channel-management-subagent` cross-platform presence-
consistency audits. Outputs a unified CSV plus a `.sources.json` manifest
(see `tool_router.write_source_manifest`) that the audit must check before
trusting the CSV as complete.

Run via cron weekly:
    0 6 * * 1 cd ~/marketing-os/06-brand-social-audit && \\
        /path/to/.venv/bin/python3 social_profile_pull.py >> output/cron.log 2>&1

Manual test:
    python3 social_profile_pull.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from social_profile_connector import pull as pull_social  # noqa: E402
from tool_router import PullResult, write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "social_profile_snapshots.csv"

FIELDNAMES = ["platform", "handle", "followers_count", "following_count", "post_count", "snapshot_at"]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found. Copy config.example.json to config.json and fill in credentials.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Validate config only, make no API calls")
    args = parser.parse_args()

    config = load_config()
    results: list[PullResult] = []

    for account in config.get("accounts", []):
        platform = account.get("platform")
        if not config.get(platform, {}).get("enabled", False):
            continue
        if args.dry_run:
            print(f"--dry-run: would pull {platform} profile {account.get('handle_or_id')}")
            continue
        kwargs = {"ig_user_id": account["handle_or_id"]} if platform == "instagram" else {"org_urn": account["handle_or_id"]}
        result = pull_social(platform, config.get(platform, {}), **kwargs)
        results.append(result)
        print(f"[{platform}] status={result.status} rows={result.row_count} "
              f"errors={[e.reason for e in result.errors]}")

    if args.dry_run:
        return

    all_rows = [r for result in results for r in result.rows]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    manifest_path = write_source_manifest(OUTPUT_CSV, results)
    print(f"\nWrote {len(all_rows)} row(s) to {OUTPUT_CSV}")
    print(f"Source manifest: {manifest_path} — read this before trusting the CSV as complete.")


if __name__ == "__main__":
    main()
