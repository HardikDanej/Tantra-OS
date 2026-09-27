"""
gsc_keyword_pull.py
====================
Nightly Google Search Console pull. Identifies keyword gaps and updates topic_queue.csv.

Three gap types are surfaced:
1. STRIKING_DISTANCE — queries you rank #8–#20 for. High leverage: small ranking
   improvements yield disproportionate traffic gains.
2. LOW_CTR_OPPORTUNITY — queries with strong impressions but CTR below the position-
   adjusted benchmark. The page is appearing but not earning the click; usually a
   title/meta issue, sometimes an intent mismatch.
3. RISING_QUERY — queries with sharp impression growth in the last 7 days vs. prior
   21 days. These are emerging topics worth catching the wave on.

Each candidate gets a composite priority score. The script appends new topics to
topic_queue.csv (deduped against existing entries and the published log) and
re-prioritizes existing queue entries based on fresh data.

Run via cron nightly:
    0 23 * * * cd ~/marketing-os/02-seo-content-factory && \\
        /path/to/.venv/bin/python3 gsc_keyword_pull.py >> output/cron.log 2>&1

API docs: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from tool_router import GSCRow, PullResult, validate_rows, write_source_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
TOKEN_PATH = CONFIG_DIR / "token.json"
TOPIC_QUEUE = ROOT / "topic_queue.csv"
PUBLISHED_LOG = ROOT / "published_log.csv"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ============================================================
# DEFAULT SETTINGS — override in config/settings.json
# ============================================================
DEFAULT_SETTINGS = {
    "site_url": "https://yourbrand.com",
    "lookback_days": 28,
    "min_impressions": 100,
    "score_threshold": 30,  # composite score below this is filtered out
    "striking_distance_position_min": 8,
    "striking_distance_position_max": 20,
    "rising_query_growth_min": 0.5,  # 50% impression growth threshold
    "ctr_benchmark_position_1": 0.30,
    "ctr_benchmark_position_5": 0.07,
    "ctr_benchmark_position_10": 0.025,
    "exclude_branded_terms": ["yourbrand", "your brand"],
    "max_queue_size": 200,
}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH) as f:
            user_settings = json.load(f)
        return {**DEFAULT_SETTINGS, **user_settings}
    return DEFAULT_SETTINGS


def get_gsc_service(settings: dict):
    """Authenticate and return Search Console API service."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                sys.exit(f"FATAL: {CLIENT_SECRET} missing. Download OAuth client_secret.json from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("searchconsole", "v1", credentials=creds)


def query_gsc(service, site_url: str, start_date: str, end_date: str,
              label: str, row_limit: int = 25000) -> PullResult:
    """
    Pull query-level performance data for a date range.
    Returns a PullResult — a raised API error mid-pagination used to crash
    the whole script with no trace; now it's caught, whatever rows were
    already fetched are kept, and the failure is recorded so the caller
    (and the manifest) can see exactly what happened instead of a silent
    cron failure or a stale topic_queue.csv with no explanation.
    """
    result = PullResult(platform=label, status="ok", accounts_attempted=[site_url])
    rows: list[dict] = []
    start_row = 0
    page_size = 5000

    try:
        while True:
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": page_size,
                "startRow": start_row,
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            batch = response.get("rows", [])
            for row in batch:
                rows.append({
                    "query": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": row.get("ctr", 0),
                    "position": row.get("position", 0),
                })
            if len(batch) < page_size or len(rows) >= row_limit:
                break
            start_row += page_size
    except Exception as e:
        result.record_failure(site_url, e)

    good_rows, bad_count = validate_rows(rows, GSCRow)
    result.rows = good_rows
    result.validation_errors = bad_count
    result.finalize()
    return result


def expected_ctr(position: float, settings: dict) -> float:
    """Linear interpolation between position-1 / position-5 / position-10 CTR benchmarks."""
    p1 = settings["ctr_benchmark_position_1"]
    p5 = settings["ctr_benchmark_position_5"]
    p10 = settings["ctr_benchmark_position_10"]
    if position <= 1:
        return p1
    elif position <= 5:
        return p1 + (p5 - p1) * ((position - 1) / 4)
    elif position <= 10:
        return p5 + (p10 - p5) * ((position - 5) / 5)
    else:
        return max(p10 * (10 / position), 0.005)


def classify_gap(row, prior_row, settings) -> tuple[str, float]:
    """
    Classify the gap type and return composite priority score.
    Score formula prioritizes: high impression volume, easy ranking improvement,
    and rising trends.
    """
    pos = row["position"]
    impressions = row["impressions"]
    ctr = row["ctr"]
    score = 0.0
    gap_type = "none"

    # Type 1: Striking distance
    if settings["striking_distance_position_min"] <= pos <= settings["striking_distance_position_max"]:
        gap_type = "striking_distance"
        # Volume × (proximity to top 10) — closer to position 8 scores higher
        proximity_bonus = max(0, 21 - pos) / 13
        score = (impressions ** 0.6) * proximity_bonus * 1.5

    # Type 2: Low CTR opportunity
    elif pos <= settings["striking_distance_position_min"] - 1:
        expected = expected_ctr(pos, settings)
        if ctr < expected * 0.7 and impressions >= settings["min_impressions"] * 2:
            gap_type = "low_ctr_opportunity"
            ctr_gap = (expected - ctr) / expected
            score = (impressions ** 0.6) * ctr_gap * 1.2

    # Type 3: Rising query
    if prior_row is not None and prior_row["impressions"] > 0:
        growth = (impressions - prior_row["impressions"]) / prior_row["impressions"]
        if growth >= settings["rising_query_growth_min"] and impressions >= settings["min_impressions"]:
            if gap_type == "none":
                gap_type = "rising_query"
            score = max(score, (impressions ** 0.6) * growth * 0.9)

    return gap_type, round(score, 2)


def is_branded(query: str, branded_terms: list[str]) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in branded_terms)


def load_existing_queue() -> set[str]:
    if not TOPIC_QUEUE.exists():
        return set()
    df = pd.read_csv(TOPIC_QUEUE)
    return set(df["query"].str.lower().tolist())


def load_published() -> set[str]:
    if not PUBLISHED_LOG.exists():
        return set()
    df = pd.read_csv(PUBLISHED_LOG)
    return set(df["query"].str.lower().tolist())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Test mode — pulls 7 days only")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    settings = load_settings()
    lookback = 7 if args.test else settings["lookback_days"]

    end = datetime.utcnow().date()
    start_current = end - timedelta(days=7)
    start_prior = end - timedelta(days=lookback)
    end_prior = end - timedelta(days=8)

    service = get_gsc_service(settings)
    print(f"[GSC] Connected to property: {settings['site_url']}")

    # Pull current 7 days
    current_result = query_gsc(service, settings["site_url"],
                               start_current.isoformat(), end.isoformat(), label="gsc_current_7d")
    # Pull prior 21 days for trend comparison
    prior_result = query_gsc(service, settings["site_url"],
                             start_prior.isoformat(), end_prior.isoformat(), label="gsc_prior_21d")

    if current_result.status != "ok":
        # The current-period pull is load-bearing for every downstream score —
        # a partial/failed fetch here means composite scores would be computed
        # on incomplete impression/CTR data and silently look like real
        # rankings. Refuse rather than write a queue built on that, and leave
        # a manifest explaining exactly why so the SEO Agent doesn't read a
        # missing/stale topic_queue.csv as "no new gaps this week."
        write_source_manifest(
            TOPIC_QUEUE, [current_result, prior_result],
            extra={"date_range": {"start": start_current.isoformat(), "end": end.isoformat()},
                   "refused_reason": "current-period GSC pull failed or was incomplete"},
        )
        sys.exit(
            f"FATAL: current-period GSC pull failed — {current_result.errors[0].detail if current_result.errors else 'unknown error'}. "
            f"topic_queue.csv was NOT updated. See topic_queue.csv.sources.json."
        )

    current = pd.DataFrame(current_result.rows) if current_result.rows else pd.DataFrame(
        columns=["query", "clicks", "impressions", "ctr", "position"])
    prior = pd.DataFrame(prior_result.rows) if prior_result.rows else pd.DataFrame(
        columns=["query", "clicks", "impressions", "ctr", "position"])

    print(f"[GSC] Current period: {len(current):,} queries "
          f"({current_result.validation_errors} rows dropped on validation)")
    print(f"[GSC] Prior period: {len(prior):,} queries, status={prior_result.status} "
          f"({prior_result.validation_errors} rows dropped on validation)")
    if prior_result.status != "ok":
        print("      WARNING: prior-period pull failed/incomplete — rising_query detection "
              "is disabled for this run, not because nothing is trending.")

    # Filter
    current = current[current["impressions"] >= settings["min_impressions"]]
    current = current[~current["query"].apply(
        lambda q: is_branded(q, settings["exclude_branded_terms"]))]

    # Build prior lookup for growth calc
    prior_indexed = prior.set_index("query") if not prior.empty else pd.DataFrame()

    # Classify and score
    classified = []
    for _, row in current.iterrows():
        prior_row = None
        if not prior_indexed.empty and row["query"] in prior_indexed.index:
            prior_row = prior_indexed.loc[row["query"]].to_dict()
        gap_type, score = classify_gap(row, prior_row, settings)
        if gap_type != "none" and score >= settings["score_threshold"]:
            classified.append({
                "query": row["query"],
                "gap_type": gap_type,
                "impressions": int(row["impressions"]),
                "clicks": int(row["clicks"]),
                "ctr": round(row["ctr"], 4),
                "position": round(row["position"], 1),
                "composite_score": score,
                "first_seen_at": datetime.utcnow().isoformat() + "Z",
                "status": "queued",
                "assigned_persona": "",  # populated by scheduled chat
                "notes": "",
            })

    print(f"[Scoring] {len(classified)} keywords passed filter")

    # Dedupe against existing queue and published log
    existing_queue = load_existing_queue()
    published = load_published()
    new_topics = [c for c in classified
                  if c["query"].lower() not in existing_queue
                  and c["query"].lower() not in published]

    # Reload existing queue and update scores for entries that are still relevant
    if TOPIC_QUEUE.exists():
        existing_df = pd.read_csv(TOPIC_QUEUE)
        # Only keep entries still queued (not in_progress, drafted, etc.)
        active_queue = existing_df[existing_df["status"] == "queued"].copy()

        # Re-score existing queued entries with fresh data
        promoted = 0
        for idx, row in active_queue.iterrows():
            match = current[current["query"] == row["query"]]
            if not match.empty:
                m = match.iloc[0]
                prior_row = (prior_indexed.loc[row["query"]].to_dict()
                             if (not prior_indexed.empty and row["query"] in prior_indexed.index)
                             else None)
                _, new_score = classify_gap(m, prior_row, settings)
                if new_score > row["composite_score"] * 1.2:
                    promoted += 1
                active_queue.at[idx, "composite_score"] = new_score
                active_queue.at[idx, "impressions"] = int(m["impressions"])
                active_queue.at[idx, "position"] = round(m["position"], 1)

        # Combine: re-scored existing + new topics
        combined = pd.concat([active_queue, pd.DataFrame(new_topics)], ignore_index=True)

        # Plus the in-flight entries (in_progress, drafted) — preserve them
        in_flight = existing_df[existing_df["status"] != "queued"]
        combined = pd.concat([in_flight, combined], ignore_index=True)
    else:
        combined = pd.DataFrame(new_topics)
        promoted = 0

    # Sort by score (queued only), cap at max queue size
    queued_part = combined[combined["status"] == "queued"].sort_values(
        "composite_score", ascending=False).head(settings["max_queue_size"])
    other_part = combined[combined["status"] != "queued"]
    final = pd.concat([other_part, queued_part], ignore_index=True)

    # Write
    final.to_csv(TOPIC_QUEUE, index=False)

    # Metadata for downstream consumers
    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "queued_count": int((final["status"] == "queued").sum()),
        "in_progress_count": int((final["status"] == "in_progress").sum()),
        "drafted_count": int((final["status"] == "drafted").sum()),
        "new_topics_added": len(new_topics),
        "topics_promoted": promoted,
        "prior_period_status": prior_result.status,
        "rising_query_detection_active": prior_result.status == "ok",
        "top_5_next": final[final["status"] == "queued"]
            .sort_values("composite_score", ascending=False)
            .head(5)[["query", "gap_type", "composite_score"]].to_dict(orient="records"),
    }
    with open(OUTPUT_DIR / "topic_queue.meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    write_source_manifest(
        TOPIC_QUEUE, [current_result, prior_result],
        extra={"date_range": {"start": start_current.isoformat(), "end": end.isoformat()},
               "new_topics_added": len(new_topics), "topics_promoted": promoted},
    )

    print(f"[Output] topic_queue.csv updated")
    print(f"  • {len(new_topics)} new topics added")
    print(f"  • {promoted} existing topics promoted on fresh scoring")
    print(f"  • {meta['queued_count']} total queued, {meta['in_progress_count']} in progress")
    print("\nTop 5 next:")
    for t in meta["top_5_next"]:
        print(f"  - [{t['gap_type']}] {t['query']} (score: {t['composite_score']:.1f})")


if __name__ == "__main__":
    main()
