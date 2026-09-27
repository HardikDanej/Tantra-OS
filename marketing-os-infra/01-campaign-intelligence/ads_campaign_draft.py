"""
ads_campaign_draft.py
======================
Creates ONE paused draft campaign (Google Ads or Meta) from a brief, but
ONLY if a specific Human-In-The-Loop approval_gate.py gate for this exact
action is recorded as "approved". This is the one script in this project
that reaches into a real, live ad account — see
marketing-os-infra/lib/ads_connector.py's module docstring for the full
reasoning on why that's a materially bigger deal than the CMS/rendering
connectors, and why PAUSED-only is enforced in code, not by convention.

**This script is Orchestrator-invoked only.** The Ads/Paid-Media Agent
itself never calls this — its own definition (.claude/agents/
ads-paid-media-agent.md) states "you do not touch the ad platforms" as an
absolute, and that stays true and unchanged. The Ads Agent produces a
creative brief; the Chief Marketing Orchestrator opens a Step 4.6 HITL
approval gate (`stakes_class: ad_platform_write`) on the specific plan to
create that campaign, presents it to the user, waits for an unambiguous
approval, and only then calls this script with that gate's id. If some
other caller runs this script without an approved gate, it refuses — see
below.

Three independent layers have to agree before anything is created:
1. **Gate approved.** `approval_gate.py`'s ledger must show `event:
   "approved"` for `--gate-id`. Missing, pending, rejected, or superseded
   all refuse — this is checked here, not just assumed from the caller's
   say-so, precisely so no dispatch phrasing can skip it.
2. **Write access explicitly confirmed in config.** `google_ads_write.
   write_access_confirmed` / `meta_write.write_access_confirmed` must be
   `true` — a separate opt-in from the read-only puller's `enabled` flag.
3. **PAUSED-only, hard-coded.** Enforced in `ads_connector.py`, not here —
   there is no flag anywhere in this call chain that produces a live
   campaign.

Brief JSON shape (platform-specific fields; see --platform):
    {
      "campaign_name": "...", "daily_budget_usd": 10,
      // google_ads:
      "ad_group_name": "...", "final_url": "https://...",
      "headlines": ["...", "..."], "descriptions": ["...", "..."],
      // meta:
      "adset_name": "...", "objective": "OUTCOME_TRAFFIC",
      "optimization_goal": "LINK_CLICKS", "billing_event": "IMPRESSIONS",
      "link": "https://...", "message": "...", "headline": "...",
      "description": "..."
    }

Usage:
    python3 ads_campaign_draft.py --platform google_ads --brief brief.json \\
        --gate-id ad_platform_write_campaignX --dry-run

    python3 ads_campaign_draft.py --platform meta --brief brief.json \\
        --gate-id ad_platform_write_campaignX \\
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
from ads_connector import CampaignDraftResult, create_draft_campaign  # noqa: E402
from approval_gate import get_current_status  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
DRAFTS_LOG_PATH = ROOT / "campaign_drafts_log.csv"
LOG_FIELDS = ["created_at", "gate_id", "platform", "status", "campaign_id", "ad_group_id", "ad_id", "manage_url", "brief_path"]

REQUIRED_BRIEF_FIELDS = {
    "google_ads": ["campaign_name", "daily_budget_usd", "ad_group_name", "final_url", "headlines", "descriptions"],
    "meta": ["campaign_name", "daily_budget_usd", "adset_name", "objective", "optimization_goal",
             "billing_event", "link", "message", "headline"],
}


class BriefError(Exception):
    pass


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_brief(path: Path, platform: str) -> dict[str, Any]:
    if not path.exists():
        raise BriefError(f"brief file not found: {path}")
    try:
        brief = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BriefError(f"brief is not valid JSON: {e}") from e
    if not isinstance(brief, dict):
        raise BriefError("brief must be a JSON object")

    missing = [f for f in REQUIRED_BRIEF_FIELDS[platform] if not brief.get(f)]
    if missing:
        raise BriefError(f"brief is missing required field(s) for {platform}: {', '.join(missing)}")
    return brief


def append_drafts_log(row: dict[str, Any]) -> None:
    is_new = not DRAFTS_LOG_PATH.exists()
    with open(DRAFTS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True, choices=["google_ads", "meta"])
    parser.add_argument("--brief", required=True, type=Path, help="Path to the brief JSON file")
    parser.add_argument("--gate-id", required=True,
                         help="The approval_gate.py gate_id for this exact action. Must be 'approved' "
                              "in the ledger, unless --dry-run.")
    parser.add_argument("--gates-ledger", type=Path, default=Path("memory/approval_gates.jsonl"),
                         help="Path to the approval_gates.jsonl ledger (default: memory/approval_gates.jsonl "
                              "relative to cwd — the workspace root, same convention as approval_gate.py itself)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Validate config + brief + gate status; do not call the ad platform API")
    args = parser.parse_args()

    config = load_config()
    platform_config = config.get(f"{args.platform}_write", {})

    try:
        brief = load_brief(args.brief, args.platform)
    except BriefError as e:
        sys.exit(f"FATAL: could not load brief {args.brief}: {e}")

    print(f"\n{'='*60}")
    print(f"Ad platform draft campaign — {args.platform}")
    print(f"{'='*60}")
    print(f"Campaign:      {brief['campaign_name']}")
    print(f"Daily budget:  ${brief['daily_budget_usd']}")
    print(f"Gate:          {args.gate_id}")

    gate_status = get_current_status(args.gates_ledger, args.gate_id) if args.gates_ledger.exists() else None
    print(f"Gate status:   {gate_status or '(not found)'}")

    if not args.dry_run and gate_status != "approved":
        sys.exit(
            f"FATAL: gate {args.gate_id!r} is {gate_status or 'UNKNOWN (never created)'}, not 'approved'. "
            f"Refusing to write to a live ad account without an approved Human-In-The-Loop gate. "
            f"This is not a permissions bug to work around — open or resolve the gate via "
            f"approval_gate.py first (see chief-marketing-orchestrator.md, Step 4.6)."
        )

    if not platform_config.get("write_access_confirmed") and not args.dry_run:
        sys.exit(
            f"FATAL: {args.platform}_write.write_access_confirmed is not true in config.json. "
            f"This is a separate, explicit opt-in from the read-only puller's config — set it to "
            f"true only once real write-scoped credentials are actually in place."
        )

    if args.dry_run:
        print("\n--dry-run: config + brief + gate-status checked, no API call made.")
        print(f"Would create a PAUSED campaign on {args.platform} "
              f"(gate would need to be 'approved' and write_access_confirmed=true for a real run).")
        return

    result: CampaignDraftResult = create_draft_campaign(args.platform, platform_config, **brief)

    if result.ok():
        append_drafts_log({
            "created_at": result.attempted_at,
            "gate_id": args.gate_id,
            "platform": result.platform,
            "status": result.status,
            "campaign_id": result.campaign_id or "",
            "ad_group_id": result.ad_group_id or "",
            "ad_id": result.ad_id or "",
            "manage_url": result.manage_url or "",
            "brief_path": str(args.brief),
        })
        print(f"\nOK: PAUSED draft campaign created on {args.platform}.")
        print(f"  campaign_id: {result.campaign_id}")
        print(f"  ad_group/adset_id: {result.ad_group_id}")
        print(f"  ad_id: {result.ad_id}")
        print(f"  manage_url: {result.manage_url}")
        print(f"  (is_paused={result.is_paused} — nothing will spend until a human reviews and "
              f"manually enables it in the platform's own UI)")
        print(f"\nLogged to {DRAFTS_LOG_PATH}")
    else:
        print(f"\nERROR: draft campaign NOT created on {args.platform}.")
        print(f"  reason: {result.error.reason}")
        print(f"  detail: {result.error.detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
