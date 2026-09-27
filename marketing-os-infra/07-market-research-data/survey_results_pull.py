"""
survey_results_pull.py
=======================
Pull real, already-collected survey responses (Typeform, SurveyMonkey) for
the Market Research & Consumer Insights system's `quantitative-survey-
design-sampling-subagent` and `nps-csat-audit-subagent`.

**Read-only, structurally.** See `survey_platform_connector.py`'s module
docstring: there is no write/field function anywhere in that connector, by
design — this system never fields a live study itself.

Run on demand (no fixed cadence — surveys close asynchronously, not weekly):
    python3 survey_results_pull.py --platform typeform --form-id abc123
    python3 survey_results_pull.py --platform surveymonkey --survey-id 456789
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from survey_platform_connector import pull as pull_survey  # noqa: E402
from tool_router import write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FIELDNAMES = ["platform", "survey_id", "respondent_id", "question_id", "question_text", "answer", "submitted_at"]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--platform", required=True, choices=["typeform", "surveymonkey"])
    parser.add_argument("--form-id", help="Typeform form id")
    parser.add_argument("--survey-id", help="SurveyMonkey survey id")
    args = parser.parse_args()

    if args.platform == "typeform" and not args.form_id:
        sys.exit("FATAL: --form-id is required for --platform typeform")
    if args.platform == "surveymonkey" and not args.survey_id:
        sys.exit("FATAL: --survey-id is required for --platform surveymonkey")

    config = load_config().get(args.platform, {})
    kwargs = {"form_id": args.form_id} if args.platform == "typeform" else {"survey_id": args.survey_id}
    result = pull_survey(args.platform, config, **kwargs)

    survey_id = args.form_id or args.survey_id
    output_csv = OUTPUT_DIR / f"survey_{args.platform}_{survey_id}.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in result.rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    manifest_path = write_source_manifest(output_csv, [result])
    print(f"[{args.platform}] status={result.status} rows={result.row_count} "
          f"errors={[e.reason for e in result.errors]}")
    print(f"Wrote {output_csv}")
    print(f"Source manifest: {manifest_path} — read before treating this as a complete response set.")
    if result.status == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
