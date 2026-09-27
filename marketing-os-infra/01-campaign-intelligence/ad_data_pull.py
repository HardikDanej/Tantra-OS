"""
ad_data_pull.py
================
Weekly ad performance puller for Meta, Google Ads, and TikTok.
Outputs a unified CSV that the Campaign Intelligence workflow consumes.

Run via cron Sunday 11pm:
    0 23 * * 0 cd ~/marketing-os/01-campaign-intelligence && \\
        /path/to/.venv/bin/python3 scripts/ad_data_pull.py >> output/cron.log 2>&1

Manual test:
    python3 scripts/ad_data_pull.py --test --verbose

Design notes:
- Each platform pull is wrapped in try/except so one failure doesn't kill the whole run.
- 14-day window (not 7) so the analysis can compute week-over-week deltas.
- Output schema is unified across platforms — `platform`, `ad_id`, `ad_name`, `spend`,
  `impressions`, `clicks`, `conversions`, `revenue`, `frequency`, `date`. Everything
  else is platform-specific and lives in a JSON column.
- TikTok exports default to UTF-16; we force UTF-8 here. Meta sometimes returns
  placement-level rows that we aggregate to ad-level. Google returns CSVs with
  hidden header rows that we skip.

Auth tokens live in config/config.json (gitignored). NEVER commit real tokens.
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from tool_router import AdRow, PullResult, assert_not_silently_empty, validate_rows, write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "config.json"
ACCOUNTS_PATH = ROOT / "config" / "accounts.csv"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

UNIFIED_SCHEMA = [
    "platform", "account_id", "ad_id", "ad_name", "campaign_name",
    "adset_name", "date", "spend", "impressions", "clicks",
    "conversions", "revenue", "frequency", "ctr", "cpm", "platform_meta_json",
]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found. Copy config.json.example and fill in credentials.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_accounts() -> pd.DataFrame:
    if not ACCOUNTS_PATH.exists():
        sys.exit(f"FATAL: {ACCOUNTS_PATH} not found.")
    return pd.read_csv(ACCOUNTS_PATH)


def date_window(days: int = 14) -> tuple[str, str]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


# ============================================================
# META MARKETING API
# ============================================================

def pull_meta(access_token: str, account_ids: list[str], start: str, end: str,
              verbose: bool = False) -> PullResult:
    """
    Pull ad-level insights from Meta Marketing API.
    Returns a PullResult — status is "ok" only if every account succeeded,
    "partial" if some did, "error" if none did. Never returns silence.

    API docs: https://developers.facebook.com/docs/marketing-api/insights
    """
    result = PullResult(platform="meta", status="ok", accounts_attempted=list(account_ids))
    rows: list[dict] = []
    for account_id in account_ids:
        url = f"https://graph.facebook.com/v18.0/act_{account_id}/insights"
        params = {
            "access_token": access_token,
            "level": "ad",
            "fields": ",".join([
                "ad_id", "ad_name", "campaign_name", "adset_name",
                "spend", "impressions", "clicks", "frequency", "ctr", "cpm",
                "actions", "action_values", "date_start",
            ]),
            "time_range": json.dumps({"since": start, "until": end}),
            "time_increment": 1,  # daily breakdown
            "limit": 500,
        }

        try:
            while url:
                r = requests.get(url, params=params if "graph.facebook.com" in url and "access_token" not in url else None, timeout=60)
                r.raise_for_status()
                data = r.json()

                for row in data.get("data", []):
                    # Conversions and revenue come from `actions` and `action_values` arrays.
                    # We pull the `purchase` action type by default — adjust to match your event setup.
                    conversions = 0.0
                    revenue = 0.0
                    for a in row.get("actions", []) or []:
                        if a.get("action_type") == "purchase":
                            conversions = float(a.get("value", 0))
                    for a in row.get("action_values", []) or []:
                        if a.get("action_type") == "purchase":
                            revenue = float(a.get("value", 0))

                    rows.append({
                        "platform": "meta",
                        "account_id": account_id,
                        "ad_id": row.get("ad_id"),
                        "ad_name": row.get("ad_name"),
                        "campaign_name": row.get("campaign_name"),
                        "adset_name": row.get("adset_name"),
                        "date": row.get("date_start"),
                        "spend": float(row.get("spend", 0)),
                        "impressions": int(row.get("impressions", 0)),
                        "clicks": int(row.get("clicks", 0)),
                        "conversions": conversions,
                        "revenue": revenue,
                        "frequency": float(row.get("frequency", 0)),
                        "ctr": float(row.get("ctr", 0)),
                        "cpm": float(row.get("cpm", 0)),
                        "platform_meta_json": json.dumps({}),
                    })

                # Pagination — Meta returns next URL with token already embedded
                url = data.get("paging", {}).get("next")
                params = None
        except Exception as e:
            result.record_failure(account_id, e)
            if verbose:
                logging.exception(e)
            continue

    good_rows, bad_count = validate_rows(rows, AdRow)
    result.rows = good_rows
    result.validation_errors = bad_count
    result.finalize()
    if verbose and good_rows:
        df = pd.DataFrame(good_rows)
        print(f"[Meta] Pulled {df['ad_id'].nunique()} ads, "
              f"{df['date'].nunique()} days, ${df['spend'].sum():,.0f} spend "
              f"({bad_count} rows dropped on validation)")
    return result


# ============================================================
# GOOGLE ADS API
# ============================================================

def pull_google(config: dict, customer_ids: list[str], start: str, end: str,
                verbose: bool = False) -> PullResult:
    """
    Pull ad-level performance from Google Ads API via google-ads python client.

    API docs: https://developers.google.com/google-ads/api/docs/reporting/overview

    Note: Google Ads' "ad" concept is the responsive search ad / image ad / etc.
    We aggregate impression/click/cost at the ad_group_ad level.
    """
    result = PullResult(platform="google", status="ok", accounts_attempted=list(customer_ids))
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as e:
        for cid in customer_ids:
            result.record_failure(cid, e)
        result.finalize()
        logging.error("google-ads not installed. Run: pip install google-ads")
        return result

    rows: list[dict] = []
    google_config = {
        "developer_token": config["developer_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "login_customer_id": config.get("login_customer_id", ""),
        "use_proto_plus": True,
    }

    try:
        client = GoogleAdsClient.load_from_dict(google_config)
        ga_service = client.get_service("GoogleAdsService")
    except Exception as e:
        for cid in customer_ids:
            result.record_failure(cid, e)
        result.finalize()
        return result

    query = f"""
        SELECT
          customer.id,
          campaign.name,
          ad_group.name,
          ad_group_ad.ad.id,
          ad_group_ad.ad.name,
          segments.date,
          metrics.cost_micros,
          metrics.impressions,
          metrics.clicks,
          metrics.conversions,
          metrics.conversions_value,
          metrics.ctr,
          metrics.average_cpm
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{start}' AND '{end}'
          AND ad_group_ad.status != 'REMOVED'
    """

    for customer_id in customer_ids:
        try:
            stream = ga_service.search_stream(customer_id=customer_id, query=query)
            for batch in stream:
                for row in batch.results:
                    rows.append({
                        "platform": "google",
                        "account_id": str(customer_id),
                        "ad_id": str(row.ad_group_ad.ad.id),
                        "ad_name": row.ad_group_ad.ad.name or f"ad_{row.ad_group_ad.ad.id}",
                        "campaign_name": row.campaign.name,
                        "adset_name": row.ad_group.name,
                        "date": row.segments.date,
                        "spend": row.metrics.cost_micros / 1_000_000,
                        "impressions": int(row.metrics.impressions),
                        "clicks": int(row.metrics.clicks),
                        "conversions": float(row.metrics.conversions),
                        "revenue": float(row.metrics.conversions_value),
                        "frequency": 0.0,  # Google doesn't expose frequency the same way
                        "ctr": float(row.metrics.ctr),
                        "cpm": float(row.metrics.average_cpm) / 1_000_000,
                        "platform_meta_json": json.dumps({}),
                    })
        except Exception as e:
            result.record_failure(customer_id, e)
            if verbose:
                logging.exception(e)
            continue

    good_rows, bad_count = validate_rows(rows, AdRow)
    result.rows = good_rows
    result.validation_errors = bad_count
    result.finalize()
    if verbose and good_rows:
        df = pd.DataFrame(good_rows)
        print(f"[Google] Pulled {df['ad_id'].nunique()} ads, "
              f"{df['date'].nunique()} days, ${df['spend'].sum():,.0f} spend "
              f"({bad_count} rows dropped on validation)")
    return result


# ============================================================
# TIKTOK MARKETING API
# ============================================================

def pull_tiktok(access_token: str, advertiser_ids: list[str], start: str, end: str,
                verbose: bool = False) -> PullResult:
    """
    Pull ad-level reports from TikTok Marketing API.

    API docs: https://business-api.tiktok.com/portal/docs?id=1740302848100353
    """
    result = PullResult(platform="tiktok", status="ok", accounts_attempted=list(advertiser_ids))
    rows: list[dict] = []
    base_url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
    headers = {"Access-Token": access_token, "Content-Type": "application/json"}

    for advertiser_id in advertiser_ids:
        page = 1
        while True:
            params = {
                "advertiser_id": advertiser_id,
                "report_type": "BASIC",
                "data_level": "AUCTION_AD",
                "dimensions": json.dumps(["ad_id", "stat_time_day"]),
                "metrics": json.dumps([
                    "ad_name", "campaign_name", "adgroup_name",
                    "spend", "impressions", "clicks", "ctr", "cpm",
                    "frequency", "conversion", "total_purchase_value",
                ]),
                "start_date": start,
                "end_date": end,
                "page": page,
                "page_size": 1000,
            }
            try:
                r = requests.get(base_url, headers=headers, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 0:
                    result.record_failure(
                        advertiser_id,
                        RuntimeError(f"TikTok API error code {data.get('code')}: {data.get('message')}"),
                    )
                    break

                for row in data.get("data", {}).get("list", []):
                    dims = row.get("dimensions", {})
                    metrics = row.get("metrics", {})
                    rows.append({
                        "platform": "tiktok",
                        "account_id": str(advertiser_id),
                        "ad_id": str(dims.get("ad_id")),
                        "ad_name": metrics.get("ad_name"),
                        "campaign_name": metrics.get("campaign_name"),
                        "adset_name": metrics.get("adgroup_name"),
                        "date": dims.get("stat_time_day", "").split(" ")[0],
                        "spend": float(metrics.get("spend", 0)),
                        "impressions": int(float(metrics.get("impressions", 0))),
                        "clicks": int(float(metrics.get("clicks", 0))),
                        "conversions": float(metrics.get("conversion", 0)),
                        "revenue": float(metrics.get("total_purchase_value", 0)),
                        "frequency": float(metrics.get("frequency", 0)),
                        "ctr": float(metrics.get("ctr", 0)),
                        "cpm": float(metrics.get("cpm", 0)),
                        "platform_meta_json": json.dumps({}),
                    })

                # Pagination
                page_info = data.get("data", {}).get("page_info", {})
                if page >= page_info.get("total_page", 1):
                    break
                page += 1
            except Exception as e:
                result.record_failure(advertiser_id, e)
                if verbose:
                    logging.exception(e)
                break

    good_rows, bad_count = validate_rows(rows, AdRow)
    result.rows = good_rows
    result.validation_errors = bad_count
    result.finalize()
    if verbose and good_rows:
        df = pd.DataFrame(good_rows)
        print(f"[TikTok] Pulled {df['ad_id'].nunique()} ads, "
              f"{df['date'].nunique()} days, ${df['spend'].sum():,.0f} spend "
              f"({bad_count} rows dropped on validation)")
    return result


# ============================================================
# ORCHESTRATION
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Test mode — pulls 3 days only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--days", type=int, default=14, help="Days to pull (default 14)")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    config = load_config()
    accounts = load_accounts()
    days = 3 if args.test else args.days
    start, end = date_window(days)

    print(f"\n{'='*60}")
    print(f"Ad data pull — {start} to {end}")
    print(f"{'='*60}\n")

    results: list[PullResult] = []

    # Meta
    if config.get("meta", {}).get("enabled"):
        meta_accounts = accounts[accounts["platform"] == "meta"]["account_id"].astype(str).tolist()
        if meta_accounts:
            results.append(pull_meta(config["meta"]["access_token"], meta_accounts, start, end, args.verbose))

    # Google
    if config.get("google_ads", {}).get("enabled"):
        google_accounts = accounts[accounts["platform"] == "google"]["account_id"].astype(str).tolist()
        if google_accounts:
            results.append(pull_google(config["google_ads"], google_accounts, start, end, args.verbose))

    # TikTok
    if config.get("tiktok", {}).get("enabled"):
        tiktok_accounts = accounts[accounts["platform"] == "tiktok"]["account_id"].astype(str).tolist()
        if tiktok_accounts:
            results.append(pull_tiktok(config["tiktok"]["access_token"], tiktok_accounts, start, end, args.verbose))

    if not results:
        print("\nFATAL: no platform is enabled in config.json / has accounts in accounts.csv.")
        sys.exit(1)

    # Refuse to write a CSV that would look like a legitimate quiet week when
    # every source actually failed — this is the deterministic backstop that
    # replaces the old silent-empty-DataFrame path.
    assert_not_silently_empty(results)

    output_path = OUTPUT_DIR / "weekly_unified.csv"
    meta_path = OUTPUT_DIR / "weekly_unified.meta.json"

    all_rows = [row for r in results if r.rows for row in r.rows]
    if all_rows:
        unified = pd.DataFrame(all_rows)[UNIFIED_SCHEMA]
        unified.to_csv(output_path, index=False)
    else:
        # Every source errored/partial with zero usable rows — still write an
        # empty CSV with headers so downstream tooling doesn't crash on a
        # missing file, but the manifest below is what makes this visible
        # as "no trustworthy data," not "zero spend week."
        pd.DataFrame(columns=UNIFIED_SCHEMA).to_csv(output_path, index=False)

    manifest_path = write_source_manifest(
        output_path, results,
        extra={"date_range": {"start": start, "end": end}, "row_count": len(all_rows)},
    )

    # Legacy metadata file kept for existing consumers, now sourced from
    # validated results rather than a bare DataFrame that could be silently
    # missing rows.
    with open(meta_path, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "date_range": {"start": start, "end": end},
            "row_count": len(all_rows),
            "platforms": sorted({r.platform for r in results if r.status != "error"}),
            "total_spend": float(sum(row["spend"] for row in all_rows)),
            "overall_status": json.loads(manifest_path.read_text())["overall_status"],
        }, f, indent=2)

    print(f"\n{'PARTIAL' if any(r.status != 'ok' for r in results) else 'OK'}: "
          f"wrote {output_path} ({len(all_rows):,} rows)")
    print(f"✓ Wrote {manifest_path} — CHECK THIS before treating the CSV as complete")
    print(f"✓ Wrote {meta_path}")
    for r in results:
        status_flag = {"ok": "OK", "partial": "PARTIAL", "error": "ERROR"}[r.status]
        print(f"  [{status_flag}] {r.platform}: {r.row_count} rows, "
              f"{len(r.accounts_failed)}/{len(r.accounts_attempted)} accounts failed, "
              f"{r.validation_errors} rows dropped on validation")
        for err in r.errors:
            print(f"      - {err.source_id}: {err.reason}: {err.detail}")
    print(f"\nTotal spend across platforms: ${sum(row['spend'] for row in all_rows):,.0f}")


if __name__ == "__main__":
    main()
