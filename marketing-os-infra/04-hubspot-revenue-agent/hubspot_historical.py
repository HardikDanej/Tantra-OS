"""
hubspot_historical.py
======================
Weekly historical trend pull from HubSpot. Produces analyses the daily MCP can't
practically deliver: forecast accuracy by quarter, win rate by source over time,
stage conversion drift, deal velocity decay.

Why this exists separately from the daily MCP-driven digest:
- The MCP is great for live current-state queries. It struggles with bulk
  historical aggregation across thousands of deal records.
- Pulling 12 months of deal history through chat would consume serious rate
  limits and tie up a session for minutes per query.
- Trend analysis is a once-a-week need, not a daily one. The daily digest reads
  the cached output of this script rather than recomputing trends every morning.

Run via cron Sunday 9pm:
    0 21 * * 0 cd ~/marketing-os/04-hubspot-revenue-agent && \\
        /path/to/.venv/bin/python3 hubspot_historical.py >> output/cron.log 2>&1

API docs:
- Deals: https://developers.hubspot.com/docs/api/crm/deals
- Pipelines: https://developers.hubspot.com/docs/api/crm/pipelines

Auth: HubSpot Private App token in .env file (NEVER committed to git).
Required scopes: crm.objects.deals.read, crm.objects.contacts.read,
                 crm.objects.companies.read, crm.schemas.deals.read
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from tool_router import PullResult, write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Load .env without external dependency
ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

HUBSPOT_TOKEN = os.environ.get("HUBSPOT_TOKEN")
if not HUBSPOT_TOKEN:
    sys.exit("FATAL: HUBSPOT_TOKEN not set. Add to .env file (see README).")

API_BASE = "https://api.hubapi.com"
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json",
}


# ============================================================
# DATA PULL
# ============================================================

def get_pipelines() -> PullResult:
    """
    Pull all deal pipelines and their stage definitions.
    Previously this raised straight out of main() on any failure — a token
    expiry or a transient 500 crashed the cron job with no trace file for
    the daily digest to check. Now the failure is caught and reported.
    """
    result = PullResult(platform="hubspot_pipelines", status="ok", accounts_attempted=["deals"])
    url = f"{API_BASE}/crm/v3/pipelines/deals"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        result.rows = r.json().get("results", [])
    except Exception as e:
        result.record_failure("deals", e)
    result.finalize()
    return result


def search_deals(filter_groups: list[dict], properties: list[str],
                 limit_per_page: int = 100, max_results: int = 10000) -> list[dict]:
    """
    Pull deals matching filter criteria. Handles pagination automatically.

    HubSpot's search endpoint caps at 10,000 results per query. For larger
    pulls, we'd need to paginate by date range — but 10k deals/quarter is
    sufficient for nearly all orgs in this workflow's target range.
    """
    url = f"{API_BASE}/crm/v3/objects/deals/search"
    results: list[dict] = []
    after = None

    while True:
        body = {
            "filterGroups": filter_groups,
            "properties": properties,
            "limit": limit_per_page,
        }
        if after:
            body["after"] = after

        r = requests.post(url, headers=HEADERS, json=body, timeout=60)
        if r.status_code == 429:
            logging.warning("Rate limited, sleeping 10s")
            import time
            time.sleep(10)
            continue
        r.raise_for_status()
        data = r.json()

        results.extend(data.get("results", []))
        if len(results) >= max_results:
            break

        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after") if paging.get("next") else None
        if not after:
            break

    return results


def pull_closed_deals(days_back: int = 365) -> PullResult:
    """
    Pull all closed deals (won or lost) from the last N days.
    Returns a PullResult — `search_deals` used to raise straight through
    on any non-429 HTTP error, crashing the whole weekly run with nothing
    written for the digest to notice. Now the failure (and whatever deals
    were already paginated in before it happened) is captured explicitly.
    """
    result = PullResult(platform="hubspot_closed_deals", status="ok", accounts_attempted=["deals"])
    cutoff_ms = int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)
    filter_groups = [{
        "filters": [
            {"propertyName": "closedate", "operator": "GTE", "value": str(cutoff_ms)},
            {"propertyName": "dealstage", "operator": "HAS_PROPERTY"},
        ]
    }]
    properties = [
        "dealname", "amount", "dealstage", "pipeline",
        "closedate", "createdate", "hs_forecast_amount",
        "hs_forecast_probability", "hubspot_owner_id",
        "hs_deal_stage_probability", "hs_lead_source",
        "dealtype", "hs_acv", "hs_arr", "hs_is_closed_won",
    ]
    try:
        result.rows = search_deals(filter_groups, properties, max_results=10000)
    except Exception as e:
        result.record_failure("deals", e)
    result.finalize()
    return result


def pull_deal_stage_history(deal_ids: list[str]) -> tuple[dict[str, list[dict]], PullResult]:
    """
    Pull stage transition history for each deal. Used for stage conversion
    and velocity analysis. Note: this is property history, accessed per-deal,
    so we sample rather than pulling all to stay within rate limits.

    Returns (history, PullResult). Previously a per-deal failure was a bare
    `except: continue` logged only at DEBUG — indistinguishable from a deal
    that legitimately has no stage-history property. That mattered:
    `analyze_stage_conversion`'s sample sizes silently shrink either way,
    and a systematic failure (an expired token, a permissions scope missing
    `crm.objects.deals.read` history) would produce a thin-looking but
    plausible stage_conversion_drift_90d report with no signal that
    anything had gone wrong.
    """
    sampled = deal_ids[:500]  # cap to avoid hammering the API
    history: dict[str, list[dict]] = {}
    result = PullResult(platform="hubspot_stage_history", status="ok", accounts_attempted=list(sampled))

    for deal_id in sampled:
        url = f"{API_BASE}/crm/v3/objects/deals/{deal_id}"
        params = {"propertiesWithHistory": "dealstage"}
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 429:
                import time
                time.sleep(5)
                continue
            r.raise_for_status()
            data = r.json()
            stage_history = data.get("propertiesWithHistory", {}).get("dealstage", [])
            history[deal_id] = stage_history
        except Exception as e:
            result.record_failure(deal_id, e)
            continue

    result.rows = []  # history payload isn't row-shaped; kept out of the manifest, error list is what matters here
    result.finalize()
    return history, result


# ============================================================
# ANALYSES
# ============================================================

def quarter_of(ts_ms: int) -> str:
    dt = datetime.utcfromtimestamp(int(ts_ms) / 1000)
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{q}"


def analyze_forecast_accuracy(deals: list[dict]) -> dict:
    """
    Compare forecasted amount (at deal creation or stage entry) vs. actual
    closed amount. Aggregate by quarter to surface drift over time.
    """
    by_quarter: dict[str, dict] = defaultdict(
        lambda: {"forecast_total": 0.0, "actual_total": 0.0, "deal_count": 0,
                 "won_count": 0, "lost_count": 0}
    )

    for deal in deals:
        props = deal.get("properties", {})
        close_date = props.get("closedate")
        if not close_date:
            continue

        try:
            close_ms = int(datetime.fromisoformat(close_date.replace("Z", "+00:00")).timestamp() * 1000)
        except (ValueError, TypeError):
            continue

        q = quarter_of(close_ms)
        amount = float(props.get("amount") or 0)
        forecast = float(props.get("hs_forecast_amount") or amount)
        is_won = (props.get("hs_is_closed_won") == "true")

        by_quarter[q]["forecast_total"] += forecast
        by_quarter[q]["deal_count"] += 1
        if is_won:
            by_quarter[q]["actual_total"] += amount
            by_quarter[q]["won_count"] += 1
        else:
            by_quarter[q]["lost_count"] += 1

    # Compute accuracy ratio
    output = {}
    for q, agg in sorted(by_quarter.items()):
        if agg["forecast_total"] > 0:
            accuracy = agg["actual_total"] / agg["forecast_total"]
        else:
            accuracy = 0
        win_rate = (agg["won_count"] / agg["deal_count"]) if agg["deal_count"] > 0 else 0
        output[q] = {
            "forecast_total": round(agg["forecast_total"], 0),
            "actual_won": round(agg["actual_total"], 0),
            "accuracy_ratio": round(accuracy, 3),
            "deal_count": agg["deal_count"],
            "win_rate": round(win_rate, 3),
        }
    return output


def analyze_win_rate_by_source(deals: list[dict]) -> dict:
    """Win rate broken down by lead source, with sample sizes."""
    by_source: dict[str, dict] = defaultdict(
        lambda: {"won": 0, "lost": 0, "total_won_amount": 0.0}
    )

    for deal in deals:
        props = deal.get("properties", {})
        source = props.get("hs_lead_source") or "unknown"
        is_won = (props.get("hs_is_closed_won") == "true")
        amount = float(props.get("amount") or 0)

        if is_won:
            by_source[source]["won"] += 1
            by_source[source]["total_won_amount"] += amount
        else:
            by_source[source]["lost"] += 1

    output = {}
    for source, agg in by_source.items():
        total = agg["won"] + agg["lost"]
        if total < 5:
            continue  # below sample size threshold, suppress
        win_rate = agg["won"] / total
        avg_won_acv = (agg["total_won_amount"] / agg["won"]) if agg["won"] > 0 else 0
        output[source] = {
            "deals_total": total,
            "deals_won": agg["won"],
            "win_rate": round(win_rate, 3),
            "avg_won_acv": round(avg_won_acv, 0),
            "total_won_revenue": round(agg["total_won_amount"], 0),
        }
    return output


def analyze_stage_conversion(deals: list[dict], stage_history: dict[str, list[dict]],
                              pipelines: list[dict]) -> dict:
    """
    For each pipeline stage, what % of deals advanced past it?
    Compares last 90 days vs. prior 90 days to surface conversion drift.
    """
    # Map stage IDs to readable names
    stage_label: dict[str, str] = {}
    for p in pipelines:
        for s in p.get("stages", []):
            stage_label[s["id"]] = s["label"]

    now = datetime.utcnow()
    cutoff_recent = now - timedelta(days=90)
    cutoff_prior = now - timedelta(days=180)

    # For each deal, what's the furthest stage it reached?
    def categorize(deal_id: str, history: list[dict]) -> tuple[str | None, datetime | None]:
        if not history:
            return None, None
        # History is reverse chronological; last entry is earliest
        try:
            entry_dates = [datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00"))
                          for h in history]
            earliest = min(entry_dates)
            stages_visited = [h["value"] for h in history]
            return stages_visited[0], earliest  # most recent stage
        except (KeyError, ValueError):
            return None, None

    recent_counts: dict[str, int] = defaultdict(int)
    prior_counts: dict[str, int] = defaultdict(int)

    for deal in deals:
        deal_id = deal.get("id")
        if not deal_id or deal_id not in stage_history:
            continue
        final_stage, first_seen = categorize(deal_id, stage_history[deal_id])
        if not final_stage or not first_seen:
            continue
        # Make first_seen naive for comparison
        first_seen_naive = first_seen.replace(tzinfo=None)
        if first_seen_naive >= cutoff_recent:
            recent_counts[final_stage] += 1
        elif first_seen_naive >= cutoff_prior:
            prior_counts[final_stage] += 1

    output = {}
    all_stages = set(recent_counts.keys()) | set(prior_counts.keys())
    for stage in all_stages:
        recent = recent_counts.get(stage, 0)
        prior = prior_counts.get(stage, 0)
        if prior < 3:
            continue  # insufficient sample
        delta = (recent - prior) / prior if prior > 0 else 0
        output[stage_label.get(stage, stage)] = {
            "recent_90d_deals": recent,
            "prior_90d_deals": prior,
            "delta_pct": round(delta * 100, 1),
        }
    return output


def analyze_deal_velocity(deals: list[dict]) -> dict:
    """Median days from create to close, by quarter, won deals only."""
    by_quarter: dict[str, list[float]] = defaultdict(list)

    for deal in deals:
        props = deal.get("properties", {})
        if props.get("hs_is_closed_won") != "true":
            continue
        create_date = props.get("createdate")
        close_date = props.get("closedate")
        if not (create_date and close_date):
            continue
        try:
            created = datetime.fromisoformat(create_date.replace("Z", "+00:00"))
            closed = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
            days = (closed - created).days
            if 0 < days < 730:  # filter outliers
                close_ms = int(closed.timestamp() * 1000)
                by_quarter[quarter_of(close_ms)].append(days)
        except ValueError:
            continue

    output = {}
    for q, days_list in sorted(by_quarter.items()):
        if len(days_list) < 5:
            continue
        days_list.sort()
        n = len(days_list)
        median = days_list[n // 2]
        p75 = days_list[int(n * 0.75)]
        p25 = days_list[int(n * 0.25)]
        output[q] = {
            "won_deals": n,
            "median_days_to_close": median,
            "p25_days": p25,
            "p75_days": p75,
        }
    return output


# ============================================================
# ORCHESTRATION
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=365,
                        help="Lookback window for deal history (default 365)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    print(f"\n{'='*60}")
    print(f"HubSpot historical trend analysis")
    print(f"Lookback: {args.days_back} days")
    print(f"{'='*60}\n")

    output_path = ROOT / "historical_trends.json"

    print("[1/5] Fetching pipelines...")
    pipelines_result = get_pipelines()
    pipelines = pipelines_result.rows
    print(f"      Found {len(pipelines)} pipelines, status={pipelines_result.status}")

    print("[2/5] Fetching closed deals...")
    deals_result = pull_closed_deals(days_back=args.days_back)
    deals = deals_result.rows
    print(f"      Pulled {len(deals)} deals, status={deals_result.status}")

    if pipelines_result.status == "error" or deals_result.status == "error":
        # Both are load-bearing for every analysis below — writing
        # historical_trends.json from an empty/failed pull would look like
        # a legitimately quiet quarter to the daily digest reading it
        # tomorrow morning. Refuse, and leave a manifest naming exactly
        # what failed instead of a silent cron failure or a stale file
        # with no signal that this run didn't actually happen.
        write_source_manifest(
            output_path, [pipelines_result, deals_result],
            extra={"refused_reason": "pipelines and/or closed-deals pull failed"},
        )
        sys.exit(
            "FATAL: pipelines and/or closed-deals pull failed. historical_trends.json was NOT "
            "updated — the daily digest will keep reading last week's file. "
            "See historical_trends.json.sources.json."
        )

    if len(deals) < 30:
        print("\n⚠️  Fewer than 30 closed deals in the lookback window.")
        print("    Trend analysis requires more data to be reliable.")
        print("    Output will be produced but flagged as low confidence.")

    # Additive only -- does not change historical_trends.json or any existing
    # analysis. A flattened (id + properties merged) per-deal snapshot, so
    # .claude/lib/event_diff.py can diff this week's deals against last
    # week's to detect real opportunity_created / opportunity_stage_changed
    # events -- something no file in this pipeline persisted before, since
    # `deals` (raw HubSpot search results, one dict per deal) only ever lived
    # in this function's local variable and fed the aggregate analyses above.
    deals_snapshot_path = ROOT / "historical_deals_snapshot.json"
    flattened_deals = [{"id": d.get("id"), **(d.get("properties") or {})} for d in deals]
    with open(deals_snapshot_path, "w") as f:
        json.dump(flattened_deals, f, indent=2)
    print(f"      (additive) {deals_snapshot_path} written -- {len(flattened_deals)} deal record(s) "
          f"for event_diff.py to compare against next run.")

    print("[3/5] Fetching stage history (sampled)...")
    deal_ids = [d["id"] for d in deals]
    stage_history, stage_history_result = pull_deal_stage_history(deal_ids)
    print(f"      Got history for {len(stage_history)} deals, "
          f"{len(stage_history_result.accounts_failed)}/{len(stage_history_result.accounts_attempted)} deal lookups failed")

    print("[4/5] Running analyses...")
    forecast_accuracy = analyze_forecast_accuracy(deals)
    win_rate_by_source = analyze_win_rate_by_source(deals)
    stage_conversion = analyze_stage_conversion(deals, stage_history, pipelines)
    deal_velocity = analyze_deal_velocity(deals)

    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "lookback_days": args.days_back,
        "deal_count_analyzed": len(deals),
        "stage_history_sample_size": len(stage_history),
        "stage_history_lookup_failures": len(stage_history_result.accounts_failed),
        "confidence": "high" if len(deals) >= 100 else ("medium" if len(deals) >= 30 else "low"),
        "analyses": {
            "forecast_accuracy_by_quarter": forecast_accuracy,
            "win_rate_by_source": win_rate_by_source,
            "stage_conversion_drift_90d": stage_conversion,
            "deal_velocity_by_quarter": deal_velocity,
        },
    }

    print("[5/5] Writing output...")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    manifest_path = write_source_manifest(
        output_path, [pipelines_result, deals_result, stage_history_result],
        extra={"lookback_days": args.days_back, "deal_count_analyzed": len(deals)},
    )

    print(f"\n✓ {output_path} written")
    print(f"✓ {manifest_path} written — CHECK THIS before treating stage_conversion_drift_90d "
          f"as a clean signal rather than one degraded by lookup failures")
    print(f"\nSummary:")
    print(f"  Deals analyzed: {len(deals)}")
    print(f"  Confidence: {output['confidence']}")
    print(f"  Stage-history lookup failures: {len(stage_history_result.accounts_failed)}/{len(stage_history_result.accounts_attempted)}")
    print(f"  Quarters with forecast data: {len(forecast_accuracy)}")
    print(f"  Sources with sufficient sample: {len(win_rate_by_source)}")
    print(f"  Stages with conversion data: {len(stage_conversion)}")


if __name__ == "__main__":
    main()
