"""
press_wire_connector.py
========================
Draft/pending-review-only submission of a press release to a wire
distribution service. Tool-layer connector for the PR & Corporate
Communications system's `media-relations-earned-editorial-agent` —
specifically `press-release-wire-embargo-subagent`'s structural brief,
finally given a real (if gated) submission path instead of ending at "a
human executes this."

Wire services (PR Newswire, Business Wire, GlobeNewswire) don't publish a
uniform public REST API the way Instagram or Typeform do — most require a
sales-negotiated contract and issue vendor-specific credentials/endpoints.
`submit_wire_draft` below is written against a generic, documented REST
shape (method/path/payload keys named for what they mean, not tied to one
vendor's exact schema) — the `config["endpoint_base"]` and
`config["submit_path"]` fields let a real deployment point this at whichever
vendor's actual API the company has a contract with, without changing this
module's enforcement logic. Get the exact field names from your vendor's own
API documentation before using this for real; what's fixed here is the
SAFETY SHAPE, not the vendor-specific payload keys.

**Draft/pending-only is enforced in code, not by convention** — exactly the
`cms_connector.py` pattern: `submit_wire_draft` does not accept a
"publish now" / "release immediately" parameter. Every submission's status
field is hard-coded to a non-live state (`"draft"` if the vendor supports a
true draft state, `"pending_review"` otherwise — never `"released"` /
`"live"` / `"distributed"`). A future need to actually trigger live
distribution is a separate, explicit capability decision requiring its own
sign-off — add a distinctly-named function for it, don't parameterize status
on this one.

This module does NOT decide whether it's safe to call — that's
`press_release_submit.py`'s job (the CLI), which refuses to call anything
here unless a Human-In-The-Loop `approval_gate.py` gate for this specific
release is recorded as "approved". A real wire submission, even in a
pending/draft state, is a real object at the vendor visible to their review
team and tied to the company's real account — treat every successful call
here as "submitted something real that a human must confirm," not a
harmless no-op.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("press_wire_connector")


class WireSubmitError(BaseModel):
    reason: str
    detail: str | None = None


class WireSubmitResult(BaseModel):
    """
    The result of ONE attempt to submit ONE release to ONE wire service.
    `is_live` is always False here — there is no code path in this module
    that produces True. Kept explicit, same reasoning as
    `cms_connector.PublishResult.is_draft`: a downstream reader should never
    have to assume draft/pending-only held, the result says so.
    """
    platform: str
    status: Literal["ok", "error"]
    is_live: bool = False
    submission_state: str | None = None  # e.g. "draft" or "pending_review" -- never "released"/"live"
    submission_id: str | None = None
    review_url: str | None = None
    attempted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: WireSubmitError | None = None

    def ok(self) -> bool:
        return self.status == "ok"


def _fail(platform: str, reason: str, detail: str | None = None) -> WireSubmitResult:
    logger.error("[%s] wire submission failed: %s (%s)", platform, reason, detail)
    return WireSubmitResult(platform=platform, status="error", error=WireSubmitError(reason=reason, detail=detail))


def submit_wire_draft(
    config: dict[str, Any],
    *,
    headline: str,
    body: str,
    dateline: str,
    boilerplate: str,
    media_contact: dict[str, str],
    embargo_at: str | None = None,
    timeout: int = 30,
) -> WireSubmitResult:
    """
    Submit a release for pending review / draft on the configured wire
    service. Every field here is required except `embargo_at` — a release
    with no dateline, no boilerplate, or no named media contact is not
    ready for a real wire, and this function refuses before making the
    call rather than submitting an incomplete release.

    `config` is the wire-service block from config.json: requires
    `platform_name` (a label for logging/results only), `endpoint_base`,
    `submit_path`, `api_key`, and `write_access_confirmed: true` (a
    separate, explicit opt-in — same reasoning as `ads_connector.py`'s
    `write_access_confirmed` fields, since this reaches a real vendor
    account even in a draft/pending state).
    """
    platform = config.get("platform_name", "generic_wire")

    missing = [name for name, value in {
        "headline": headline, "body": body, "dateline": dateline,
        "boilerplate": boilerplate,
    }.items() if not value or not value.strip()]
    if not media_contact or not media_contact.get("name") or not media_contact.get("email"):
        missing.append("media_contact.name/email")
    if missing:
        return _fail(platform, "incomplete_release", f"missing required field(s): {', '.join(missing)}")

    if not config.get("write_access_confirmed"):
        return _fail(
            platform, "write_access_not_confirmed",
            "write_access_confirmed is not true in config.json — this is a separate, explicit "
            "opt-in from having valid credentials configured, by design.",
        )

    api_key = config.get("api_key", "")
    endpoint_base = config.get("endpoint_base", "")
    submit_path = config.get("submit_path", "")
    if not api_key or str(api_key).startswith("REPLACE_WITH"):
        return _fail(platform, "config_missing", f"{platform}.api_key is not configured")
    if not endpoint_base or str(endpoint_base).startswith("REPLACE_WITH"):
        return _fail(platform, "config_missing", f"{platform}.endpoint_base is not configured — set it to your "
                     f"wire vendor's real API base URL from their own documentation")

    payload: dict[str, Any] = {
        "headline": headline,
        "body": body,
        "dateline": dateline,
        "boilerplate": boilerplate,
        "media_contact": media_contact,
        # Hard-coded, never a parameter -- see module docstring.
        "status": "draft",
    }
    if embargo_at:
        payload["embargo_at"] = embargo_at

    try:
        r = requests.post(
            f"{endpoint_base.rstrip('/')}/{submit_path.lstrip('/')}",
            json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout,
        )
    except requests.RequestException as e:
        return _fail(platform, "request_failed", str(e)[:500])

    if r.status_code not in (200, 201, 202):
        detail = r.text[:500]
        try:
            detail = r.json().get("message", detail)
        except ValueError:
            pass
        return _fail(platform, f"http_{r.status_code}", detail)

    try:
        body_json = r.json()
    except ValueError as e:
        return _fail(platform, "invalid_response_json", str(e)[:500])

    return WireSubmitResult(
        platform=platform,
        status="ok",
        is_live=False,
        submission_state=body_json.get("status", "pending_review"),
        submission_id=body_json.get("id") or body_json.get("submission_id"),
        review_url=body_json.get("review_url") or body_json.get("preview_url"),
    )
