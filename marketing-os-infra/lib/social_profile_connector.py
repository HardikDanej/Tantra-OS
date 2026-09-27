"""
social_profile_connector.py
============================
Read-only pull of a real, OWNED social profile's public metrics (follower
count, post count, recent post engagement). Tool-layer connector for the
Brand & Creative Marketing system's `organic-social-community-building-
agent` — specifically `organic-social-channel-management-subagent`'s
cross-platform presence-consistency audits, which previously had no real
data source and relied entirely on WebFetch/WebSearch approximation.

**Owned profiles only.** This connector authenticates as the brand's own
account (Instagram/LinkedIn) and reads that account's own data — it is not,
and must never become, a way to scrape a competitor's or any other party's
social presence. A competitor's public metrics stay exactly what they
already were: a WebSearch/WebFetch-sourced, citation-checked claim, subject
to `citation_guard.py`, never a connector pull.

Read-only: no posting/publishing function exists here. This connector never
posts, schedules, or modifies anything on the account — it only reads
metrics the account already has.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_router import PullResult, SocialProfileSnapshotRow, validate_rows  # noqa: E402


def pull_instagram_profile(config: dict[str, Any], *, ig_user_id: str, timeout: int = 30) -> PullResult:
    """
    `config` is the `instagram` block from config.json: requires
    `access_token` (a Page access token with `instagram_basic` +
    `instagram_manage_insights` scopes for the linked Business/Creator
    account — read-only scopes, never request publish scopes for this
    connector). https://developers.facebook.com/docs/instagram-api/reference/ig-user
    """
    result = PullResult(platform="instagram", accounts_attempted=[ig_user_id])
    token = config.get("access_token", "")
    if not token or str(token).startswith("REPLACE_WITH"):
        result.record_failure(ig_user_id, RuntimeError("instagram.access_token is not configured"))
        return result.finalize()

    url = f"https://graph.facebook.com/v19.0/{ig_user_id}"
    try:
        r = requests.get(url, params={
            "fields": "username,followers_count,follows_count,media_count",
            "access_token": token,
        }, timeout=timeout)
        r.raise_for_status()
        body = r.json()
    except requests.RequestException as e:
        result.record_failure(ig_user_id, e)
        return result.finalize()

    raw_rows = [{
        "platform": "instagram",
        "handle": body.get("username", ig_user_id),
        "followers_count": body.get("followers_count", 0),
        "following_count": body.get("follows_count", 0),
        "post_count": body.get("media_count", 0),
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }]
    good, bad = validate_rows(raw_rows, schema=SocialProfileSnapshotRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


def pull_linkedin_org_profile(config: dict[str, Any], *, org_urn: str, timeout: int = 30) -> PullResult:
    """
    `config` is the `linkedin` block from config.json: requires
    `access_token` (an OAuth token for the LinkedIn Marketing API with
    `r_organization_social` + `rw_organization_admin`'s read portion —
    request read scopes only for this connector) and the organization's
    URN (e.g. `urn:li:organization:12345`).
    https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/organization-lookup-api
    """
    result = PullResult(platform="linkedin", accounts_attempted=[org_urn])
    token = config.get("access_token", "")
    if not token or str(token).startswith("REPLACE_WITH"):
        result.record_failure(org_urn, RuntimeError("linkedin.access_token is not configured"))
        return result.finalize()

    headers = {"Authorization": f"Bearer {token}", "LinkedIn-Version": "202401"}
    try:
        follower_r = requests.get(
            "https://api.linkedin.com/v2/networkSizes/" + org_urn,
            headers=headers, params={"edgeType": "CompanyFollowedByMember"}, timeout=timeout,
        )
        follower_r.raise_for_status()
        follower_count = follower_r.json().get("firstDegreeSize", 0)

        org_r = requests.get(f"https://api.linkedin.com/v2/organizations/{org_urn.split(':')[-1]}",
                              headers=headers, timeout=timeout)
        org_r.raise_for_status()
        org_body = org_r.json()
    except requests.RequestException as e:
        result.record_failure(org_urn, e)
        return result.finalize()

    raw_rows = [{
        "platform": "linkedin",
        "handle": org_body.get("localizedName", org_urn),
        "followers_count": follower_count,
        "following_count": 0,  # LinkedIn organization pages don't expose a "following" concept
        "post_count": 0,  # requires a separate paginated posts call; left to a dedicated posts pull if needed
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }]
    good, bad = validate_rows(raw_rows, schema=SocialProfileSnapshotRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


PLATFORM_PULLERS = {"instagram": pull_instagram_profile, "linkedin": pull_linkedin_org_profile}


def pull(platform: str, config: dict[str, Any], **kwargs: Any) -> PullResult:
    """Dispatch to the right connector by platform name. See social_profile_pull.py for the CLI."""
    if platform not in PLATFORM_PULLERS:
        result = PullResult(platform=platform, accounts_attempted=["?"])
        result.record_failure("config", RuntimeError(f"no connector for platform {platform!r}"))
        return result.finalize()
    return PLATFORM_PULLERS[platform](config, **kwargs)
