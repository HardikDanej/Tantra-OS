"""
tool_router.py
===============
Deterministic tool-call routing for marketing-os-infra data pullers.

Problem this solves: every puller (ad_data_pull.py, gsc_keyword_pull.py,
asset_ingestion.py, hubspot_historical.py) hits an external API per
platform/account and used to swallow failures with a bare `except Exception:
continue`. That means a downstream agent reading the output CSV has no way
to tell "TikTok had $0 spend this week" apart from "the TikTok pull crashed
and returned nothing." A confident-looking file with silently missing rows
is exactly how an agent ends up reporting a hallucinated account audit as
fact.

This module gives every puller two things:

1. `PullResult` — a Pydantic-validated, typed result for one platform/source
   pull. Every pull function returns one of these instead of a bare
   DataFrame. Status is always one of "ok" / "partial" / "error", and
   "error"/"partial" always carry a human-readable reason. There is no path
   that produces silence.
2. `AdRow` (and friends) — a Pydantic schema for one output row. Every row
   is validated before being written to the unified CSV. A row that fails
   validation is dropped and counted, never silently coerced into looking
   like a well-formed row.
3. `write_source_manifest()` — writes the `<output>.sources.json` manifest
   next to every output CSV, recording per-source status/row-count/error so
   a consuming agent can check freshness and completeness BEFORE treating
   the CSV as ground truth, instead of assuming a CSV that exists is a CSV
   that's complete.

Any agent (human-authored script or Claude-driven Bash call) that talks to
an external tool/API in this project should follow this same shape:
catch at the narrowest point that has enough context to explain the
failure, never wider, and never turn "it failed" into "return nothing."
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger("tool_router")

PullStatus = Literal["ok", "partial", "error"]


# ---------------------------------------------------------------------------
# Per-source pull result
# ---------------------------------------------------------------------------

class SourceError(BaseModel):
    """One failure encountered while pulling from a single source/account."""
    source_id: str
    reason: str
    detail: str | None = None


class PullResult(BaseModel):
    """
    The result of attempting to pull data from ONE platform (or one
    account within a platform run). Never construct this by hand for a
    successful call and silently drop errors elsewhere — every failure
    that happens during the pull must show up in `errors`.
    """
    platform: str
    status: PullStatus
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    accounts_attempted: list[str] = Field(default_factory=list)
    accounts_failed: list[str] = Field(default_factory=list)
    errors: list[SourceError] = Field(default_factory=list)
    validation_errors: int = 0
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("status")
    @classmethod
    def status_must_match_errors(cls, v: str, info) -> str:
        return v

    def finalize(self) -> "PullResult":
        """Recompute status/row_count from accumulated state. Call once at the end of a pull."""
        self.row_count = len(self.rows)
        if not self.accounts_attempted:
            self.status = "ok" if not self.errors else "error"
        elif self.accounts_failed and len(self.accounts_failed) == len(self.accounts_attempted):
            self.status = "error"
        elif self.accounts_failed:
            self.status = "partial"
        else:
            self.status = "ok" if self.rows or not self.accounts_attempted else "partial"
        return self

    def record_failure(self, source_id: str, exc: Exception) -> None:
        """Call this from inside a pull function's except block — never a bare `continue`."""
        self.accounts_failed.append(source_id)
        self.errors.append(SourceError(
            source_id=source_id,
            reason=type(exc).__name__,
            detail=str(exc)[:500],
        ))
        logger.error("[%s] pull failed for %s: %s", self.platform, source_id, exc)


# ---------------------------------------------------------------------------
# Output row schema (ad performance — extend/copy this pattern for
# GSC keyword rows, HubSpot deal rows, etc.)
# ---------------------------------------------------------------------------

class AdRow(BaseModel):
    platform: str
    account_id: str
    ad_id: str
    ad_name: str | None = None
    campaign_name: str | None = None
    adset_name: str | None = None
    date: str
    spend: float = Field(ge=0)
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    conversions: float = Field(ge=0)
    revenue: float = Field(ge=0)
    frequency: float = Field(ge=0)
    ctr: float = Field(ge=0)
    cpm: float = Field(ge=0)
    platform_meta_json: str = "{}"

    @field_validator("date")
    @classmethod
    def date_must_be_iso(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d")  # raises ValueError -> pydantic ValidationError
        return v


class GSCRow(BaseModel):
    """One Search Console query-level performance row."""
    query: str = Field(min_length=1)
    clicks: int = Field(ge=0)
    impressions: int = Field(ge=0)
    ctr: float = Field(ge=0, le=1.0)
    position: float = Field(ge=1.0)


# ---------------------------------------------------------------------------
# Row schemas for the Tool-layer connectors added for the four systems that
# previously had zero live data access (Brand & Creative, Product Marketing
# & GTM via Market Research's shared analytics, Market Research & Consumer
# Insights, PR & Corporate Communications). Same discipline as AdRow/GSCRow
# above: every row is validated before a connector includes it, a row that
# fails validation is dropped and counted, never silently coerced.
# ---------------------------------------------------------------------------

class SurveyResponseRow(BaseModel):
    """One respondent's answer to one question, from a real fielded survey. READ-ONLY data —
    see survey_platform_connector.py's module docstring for why this schema has no counterpart
    write/field function anywhere in this project."""
    platform: str
    survey_id: str = Field(min_length=1)
    respondent_id: str = Field(min_length=1)
    question_id: str
    question_text: str | None = None
    answer: str
    submitted_at: str

    @field_validator("submitted_at")
    @classmethod
    def submitted_at_must_be_iso(cls, v: str) -> str:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class ProductEventRow(BaseModel):
    """One product-usage event (a page view, a feature action, a cohort membership signal) from
    a real product analytics platform. Feeds the Market Research system's
    product-analytics-cohort-retention-subagent — the canonical cohort-computation source other
    sub-agents (GTM's product-market-fit-validation-subagent, Revenue/CRM's rfm-segmentation-
    subagent) should consume rather than re-deriving their own retention math."""
    platform: str
    user_id: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    event_time: str
    properties_json: str = "{}"

    @field_validator("event_time")
    @classmethod
    def event_time_must_be_iso(cls, v: str) -> str:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class MediaCoverageRow(BaseModel):
    """One real, cited piece of earned-media coverage. Feeds
    editorial-media-monitoring-clipping-subagent (PR & Corporate Communications) — never a
    substitute for citation_guard.py's evidence-logging discipline on any figure pulled from it."""
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    published_at: str
    snippet: str | None = None
    query: str

    @field_validator("published_at")
    @classmethod
    def published_at_must_be_iso(cls, v: str) -> str:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class SocialProfileSnapshotRow(BaseModel):
    """One point-in-time snapshot of a real, owned social profile's public metrics. Feeds
    organic-social-channel-management-subagent's cross-platform presence-consistency audits
    (Brand & Creative Marketing) — never a substitute for a competitor's data, which stays a
    WebSearch/WebFetch-sourced, citation-checked claim, not a connector pull."""
    platform: str
    handle: str = Field(min_length=1)
    followers_count: int = Field(ge=0)
    following_count: int = Field(ge=0)
    post_count: int = Field(ge=0)
    snapshot_at: str

    @field_validator("snapshot_at")
    @classmethod
    def snapshot_at_must_be_iso(cls, v: str) -> str:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


def validate_rows(raw_rows: list[dict[str, Any]], schema: type[BaseModel] = AdRow
                   ) -> tuple[list[dict[str, Any]], int]:
    """
    Validate every raw row against `schema`. Returns (good_rows, bad_row_count).
    A row that fails validation is DROPPED, never included half-typed —
    downstream code must never see a row that only pretends to match the schema.
    """
    good: list[dict[str, Any]] = []
    bad = 0
    for row in raw_rows:
        try:
            validated = schema(**row)
            good.append(validated.model_dump())
        except ValidationError as e:
            bad += 1
            logger.warning("dropped invalid row (%s): %s", row.get("ad_id", "?"), e.errors()[:2])
    return good, bad


# ---------------------------------------------------------------------------
# Source manifest — the file a consuming agent MUST read before trusting
# the accompanying CSV.
# ---------------------------------------------------------------------------

def write_source_manifest(output_csv_path: Path, results: list[PullResult],
                           extra: dict[str, Any] | None = None) -> Path:
    """
    Writes `<output_csv>.sources.json` next to the CSV. This is the
    deterministic signal a downstream agent checks instead of inferring
    completeness from row counts alone.
    """
    manifest_path = output_csv_path.with_suffix(output_csv_path.suffix + ".sources.json")
    overall_status: PullStatus
    statuses = [r.status for r in results]
    if not statuses or all(s == "error" for s in statuses):
        overall_status = "error"
    elif any(s in ("error", "partial") for s in statuses):
        overall_status = "partial"
    else:
        overall_status = "ok"

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "sources": [json.loads(r.model_dump_json()) for r in results],
        **(extra or {}),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


def assert_not_silently_empty(results: list[PullResult]) -> None:
    """
    Hard stop: if every enabled source errored out, refuse to let the
    caller proceed as if it just had a quiet week. Raise, don't `sys.exit`
    quietly with an easy-to-miss warning print.
    """
    if results and all(r.status == "error" for r in results):
        failing = ", ".join(f"{r.platform} ({r.errors[0].reason if r.errors else 'no data'})" for r in results)
        raise RuntimeError(
            f"All enabled sources failed — refusing to write a CSV that would look like a "
            f"legitimate zero-activity week. Failing sources: {failing}"
        )
