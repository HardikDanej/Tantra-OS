"""
media_coverage_connector.py
============================
Read-only pull of real, published news/media coverage matching a search
query. Tool-layer connector for the PR & Corporate Communications system's
`media-relations-earned-editorial-agent` — specifically
`editorial-media-monitoring-clipping-subagent`'s tracking of the brand's own
real earned-media hits, replacing "verified via real search" (WebSearch,
manual and unstructured) with a structured, re-runnable, validated pull.

This does NOT replace WebSearch/WebFetch for one-off verification — it's for
the recurring "how much real coverage did we get, and what does it say"
question this sub-agent answers repeatedly. Every returned row still needs
the same real-source discipline the sub-agent already applies: a coverage
hit is a real, dated, sourced URL, never a fabricated placement.

Read-only: no submission/pitch function exists here — that stays exactly
what it already was, a human-executed pitch via
`media-pitching-journalist-outreach-subagent`'s strategy. This connector
only reads what already got published.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_router import MediaCoverageRow, PullResult, validate_rows  # noqa: E402


def pull_newsapi_coverage(config: dict[str, Any], *, query: str, from_date: str | None = None,
                           to_date: str | None = None, page_size: int = 100, timeout: int = 30) -> PullResult:
    """
    `config` is the `newsapi` block from config.json: requires `api_key`
    (from newsapi.org — free tier is rate-limited and delayed by 24h on
    some plans; note that limitation in any output built from this).
    `from_date`/`to_date` are `YYYY-MM-DD`, optional (defaults to NewsAPI's
    own lookback window when omitted).
    https://newsapi.org/docs/endpoints/everything
    """
    result = PullResult(platform="newsapi", accounts_attempted=[query])
    api_key = config.get("api_key", "")
    if not api_key or str(api_key).startswith("REPLACE_WITH"):
        result.record_failure(query, RuntimeError("newsapi.api_key is not configured"))
        return result.finalize()

    url = "https://newsapi.org/v2/everything"
    params: dict[str, Any] = {"q": query, "pageSize": min(page_size, 100), "sortBy": "publishedAt", "language": "en"}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    raw_rows: list[dict[str, Any]] = []
    try:
        r = requests.get(url, params=params, headers={"X-Api-Key": api_key}, timeout=timeout)
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "ok":
            result.record_failure(query, RuntimeError(body.get("message", "newsapi returned non-ok status")))
            return result.finalize()
        for article in body.get("articles", []):
            raw_rows.append({
                "source": (article.get("source", {}) or {}).get("name", "unknown"),
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "snippet": article.get("description"),
                "query": query,
            })
    except requests.RequestException as e:
        result.record_failure(query, e)
        return result.finalize()

    good, bad = validate_rows(raw_rows, schema=MediaCoverageRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


PLATFORM_PULLERS = {"newsapi": pull_newsapi_coverage}


def pull(platform: str, config: dict[str, Any], **kwargs: Any) -> PullResult:
    """Dispatch to the right connector by platform name. See media_coverage_pull.py for the CLI."""
    if platform not in PLATFORM_PULLERS:
        result = PullResult(platform=platform, accounts_attempted=[kwargs.get("query", "?")])
        result.record_failure("config", RuntimeError(f"no connector for platform {platform!r}"))
        return result.finalize()
    return PLATFORM_PULLERS[platform](config, **kwargs)
