"""
cms_connector.py
================
Draft-only CMS publishing for the SEO Content Factory (workflow 02).

This is the piece the workflow docs have described since the first commit
("WordPress draft published via MCP") but that never actually existed as
code — the agents could produce a finished, audited article and then had
nowhere real to send it. This module is that missing wire: a WordPress
connector (REST API + Application Passwords) and a Webflow connector (CMS
API v2), both of which can only ever create a DRAFT.

Draft-only is enforced in code, not by convention or a config flag:
- `publish_wordpress_draft` does not accept a `status` argument. The POST
  body always sets `"status": "draft"`.
- `publish_webflow_draft` does not accept an `is_draft` argument. The POST
  body always sets `"isDraft": True`.

If a future caller needs to actually go live, that is a deliberate,
separate capability decision — add a new, clearly-named function for it
(e.g. `publish_wordpress_live`) rather than parameterizing draft/live on
these two. Do not add a `status`/`is_draft` parameter here as a shortcut;
that would silently turn a draft-only connector into a live-publish one
for every existing caller.

Every call returns a `PublishResult` — never raises past its own
boundary, never returns a bare dict, never pretends success. A failed
call always carries `.error.reason` / `.error.detail`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("cms_connector")

CmsPlatform = Literal["wordpress", "webflow"]


class PublishError(BaseModel):
    """Why a publish attempt failed. Always populated when status == "error"."""
    reason: str
    detail: str | None = None


class PublishResult(BaseModel):
    """
    The result of ONE attempt to create ONE draft on ONE platform.
    `is_draft` is always True on this model — there is no code path in
    this module that produces False. It's kept as an explicit field
    (rather than left implicit) so a downstream reader — human or agent —
    never has to assume draft-only held; the result says so.
    """
    platform: CmsPlatform
    status: Literal["ok", "error"]
    is_draft: bool = True
    post_id: str | None = None
    draft_url: str | None = None
    title: str | None = None
    attempted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: PublishError | None = None

    def ok(self) -> bool:
        return self.status == "ok"


def _fail(platform: CmsPlatform, title: str, reason: str, detail: str | None = None) -> PublishResult:
    logger.error("[%s] publish failed for %r: %s (%s)", platform, title, reason, detail)
    return PublishResult(
        platform=platform,
        status="error",
        is_draft=True,
        title=title,
        error=PublishError(reason=reason, detail=detail),
    )


# ---------------------------------------------------------------------------
# WordPress — REST API, Application Passwords
# https://developer.wordpress.org/rest-api/reference/posts/#create-a-post
# ---------------------------------------------------------------------------

def publish_wordpress_draft(
    config: dict[str, Any],
    *,
    title: str,
    content_html: str,
    slug: str = "",
    excerpt: str = "",
    categories: list[int] | None = None,
    tags: list[int] | None = None,
    timeout: int = 30,
) -> PublishResult:
    """
    Create a WordPress draft post. Always `status: "draft"` — see module
    docstring for why that is not a parameter.

    `config` is the `wordpress` block from config.json: requires
    `site_url`, `username`, `app_password`. `categories`/`tags` are
    numeric term IDs (look them up via `/wp-json/wp/v2/categories` —
    WordPress does not accept category *names* on this endpoint).

    Native WordPress has no first-class "meta description" field; if the
    site's config sets `wordpress.yoast_meta_field` (e.g.
    `"_yoast_wpseo_metadesc"`), the excerpt is also written there via the
    `meta` object. Otherwise the SEO meta description belongs in `excerpt`
    only, and the editor sets the on-page SEO field by hand — this is a
    known gap, not a silent failure; see the workflow README.
    """
    site_url = str(config.get("site_url", "")).rstrip("/")
    username = config.get("username", "")
    app_password = config.get("app_password", "")

    if not site_url or site_url.startswith("https://REPLACE_WITH"):
        return _fail("wordpress", title, "config_missing", "wordpress.site_url is not configured")
    if not username or not app_password or str(app_password).startswith("REPLACE_WITH"):
        return _fail("wordpress", title, "config_missing", "wordpress.username / app_password not configured")

    payload: dict[str, Any] = {
        "title": title,
        "content": content_html,
        "status": "draft",  # never anything else — see module docstring
    }
    if slug:
        payload["slug"] = slug
    if excerpt:
        payload["excerpt"] = excerpt
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags

    yoast_field = config.get("yoast_meta_field")
    if yoast_field and excerpt:
        payload["meta"] = {yoast_field: excerpt}

    try:
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(username, app_password),
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        return _fail("wordpress", title, "request_failed", str(e)[:500])

    if r.status_code not in (200, 201):
        detail = r.text[:500]
        try:
            body = r.json()
            detail = body.get("message", detail)
        except ValueError:
            pass
        return _fail("wordpress", title, f"http_{r.status_code}", detail)

    try:
        body = r.json()
    except ValueError as e:
        return _fail("wordpress", title, "invalid_response_json", str(e)[:500])

    post_id = str(body.get("id", ""))
    edit_url = f"{site_url}/wp-admin/post.php?post={post_id}&action=edit" if post_id else None

    return PublishResult(
        platform="wordpress",
        status="ok",
        is_draft=True,
        post_id=post_id or None,
        draft_url=edit_url,
        title=title,
    )


# ---------------------------------------------------------------------------
# Webflow — CMS API v2
# https://developers.webflow.com/data/reference/cms/collection-items/create-item
# ---------------------------------------------------------------------------

def publish_webflow_draft(
    config: dict[str, Any],
    *,
    title: str,
    content_html: str,
    slug: str = "",
    excerpt: str = "",
    timeout: int = 30,
) -> PublishResult:
    """
    Create a Webflow CMS item. Always `"isDraft": True` — see module
    docstring for why that is not a parameter.

    `config` is the `webflow` block from config.json: requires
    `api_token`, `collection_id`, and `field_map` (this script's fields ->
    the collection's actual field slugs, which vary per site/template —
    Webflow does not use fixed field names across collections).
    """
    api_token = config.get("api_token", "")
    collection_id = config.get("collection_id", "")
    field_map = config.get("field_map", {}) or {}

    if not api_token or str(api_token).startswith("REPLACE_WITH"):
        return _fail("webflow", title, "config_missing", "webflow.api_token is not configured")
    if not collection_id or str(collection_id).startswith("REPLACE_WITH"):
        return _fail("webflow", title, "config_missing", "webflow.collection_id is not configured")

    field_data: dict[str, Any] = {
        field_map.get("title_field", "name"): title,
    }
    if slug:
        field_data[field_map.get("slug_field", "slug")] = slug
    body_field = field_map.get("body_field", "post-body")
    field_data[body_field] = content_html
    if excerpt and field_map.get("meta_description_field"):
        field_data[field_map["meta_description_field"]] = excerpt

    payload = {
        "isArchived": False,
        "isDraft": True,  # never anything else — see module docstring
        "fieldData": field_data,
    }

    try:
        r = requests.post(
            f"https://api.webflow.com/v2/collections/{collection_id}/items",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "accept": "application/json",
            },
            data=json.dumps(payload),
            timeout=timeout,
        )
    except requests.RequestException as e:
        return _fail("webflow", title, "request_failed", str(e)[:500])

    if r.status_code not in (200, 201, 202):
        detail = r.text[:500]
        try:
            body = r.json()
            detail = body.get("message", detail)
        except ValueError:
            pass
        return _fail("webflow", title, f"http_{r.status_code}", detail)

    try:
        body = r.json()
    except ValueError as e:
        return _fail("webflow", title, "invalid_response_json", str(e)[:500])

    item_id = str(body.get("id", ""))
    site_id = config.get("site_id", "")
    # Webflow has no stable public deep-link formula to one CMS item across
    # all site/template configurations. Point to the collection list view
    # (reliable) rather than guess at an item URL (fragile) — the item is
    # findable there by the title/slug just written.
    dashboard_url = (
        f"https://webflow.com/dashboard/sites/{site_id}/cms" if site_id else None
    )

    return PublishResult(
        platform="webflow",
        status="ok",
        is_draft=True,
        post_id=item_id or None,
        draft_url=dashboard_url,
        title=title,
    )


def publish_draft(platform: CmsPlatform, config: dict[str, Any], **kwargs: Any) -> PublishResult:
    """Dispatch to the right connector by platform name. See cms_publish.py for the CLI."""
    if platform == "wordpress":
        return publish_wordpress_draft(config, **kwargs)
    if platform == "webflow":
        return publish_webflow_draft(config, **kwargs)
    return _fail(platform, kwargs.get("title", ""), "unknown_platform", f"no connector for {platform!r}")
