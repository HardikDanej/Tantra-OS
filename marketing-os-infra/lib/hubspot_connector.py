"""
hubspot_connector.py
=====================
Creates ONE HubSpot task or note — the first write capability against a
live CRM in this project. The original HubSpot Revenue Agent workflow
design explicitly said "read access is sufficient — no write permissions
needed"; this exists only because building it was explicitly signed off
on as a new, narrowly-scoped capability, not because the original design
called for it.

Scope, deliberately narrow: **task and note creation only.** No email
sends, no workflow/sequence enrollment, no deal-stage changes, no contact/
company property writes, and — unlike the CMS and ad-platform connectors,
which have PAUSED/draft states to fall back on — this module doesn't
create anything that could later "go live" on its own. A task is a to-do
item for a human; a note is a log entry. Neither can send anything or
trigger further automation by existing. That's the point: this is the
actual safe analog to a CMS draft or a PAUSED campaign for a CRM, not an
approximation of one.

Explicitly OUT of scope, and not something to "helpfully" add later
without a fresh, separate sign-off:
- Enrolling a contact/deal in a HubSpot Workflow (marketing/sales
  automation). Once enrolled, whatever that workflow is configured to do —
  including live email sends — fires automatically and outside this
  module's visibility or control. There is no way to make that "draft."
- Sending an email, SMS, or any outbound communication directly.
- Changing `dealstage`, `amount`, or any other CRM record property.

Every mutable status field this module DOES touch is hard-coded:
- A task is always created with `hs_task_status: "NOT_STARTED"` — never
  "COMPLETED" (that would be a fabricated record of work never done) or
  any other status.
- Neither function accepts a status/completion parameter. If a future
  need shows up to mark tasks complete or do anything else, that's a
  separate, explicitly-named function and a separate decision — don't
  parameterize status on these two.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("hubspot_connector")

CrmActionType = Literal["task", "note"]


class CrmWriteError(BaseModel):
    reason: str
    detail: str | None = None


class CrmWriteResult(BaseModel):
    """
    The result of ONE attempt to create ONE task or note, optionally
    associated to ONE contact and/or ONE deal. This module creates nothing
    that can send, enroll, or activate on its own — there is no `is_draft`-
    style field here the way cms_connector/ads_connector have one, because
    there is no more-active state this object could be silently upgraded
    to. It just exists, for a human to see and act on.
    """
    action_type: str  # not the Literal, same reasoning as ads_connector.CampaignDraftResult.platform
    status: Literal["ok", "error"]
    object_id: str | None = None
    portal_url: str | None = None
    attempted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: CrmWriteError | None = None

    def ok(self) -> bool:
        return self.status == "ok"


def _fail(action_type: str, reason: str, detail: str | None = None) -> CrmWriteResult:
    logger.error("[%s] CRM write failed: %s (%s)", action_type, reason, detail)
    return CrmWriteResult(action_type=action_type, status="error", error=CrmWriteError(reason=reason, detail=detail))


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


def _associate_default(base: str, headers: dict[str, str], object_type: str, object_id: str,
                        contact_id: str | None, deal_id: str | None, timeout: int) -> CrmWriteError | None:
    """
    Associate the just-created task/note to a contact and/or deal using
    HubSpot's v4 "default association" endpoint — it picks the correct
    association type automatically, so this doesn't need to hard-code a
    numeric associationTypeId that could silently be wrong or change.
    An association failure here does NOT roll back the already-created
    object (HubSpot has no multi-object transaction for this); it's
    surfaced as a partial-success error so the caller knows to check the
    portal rather than assuming a clean association happened.
    """
    for to_type, to_id in (("contacts", contact_id), ("deals", deal_id)):
        if not to_id:
            continue
        url = f"{base}/crm/v4/objects/{object_type}/{object_id}/associations/default/{to_type}/{to_id}"
        try:
            r = requests.put(url, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            return CrmWriteError(
                reason="association_request_failed",
                detail=f"{object_type} {object_id} was created but associating to {to_type}/{to_id} failed: {e}"[:500],
            )
        if r.status_code not in (200, 201, 204):
            return CrmWriteError(
                reason=f"association_http_{r.status_code}",
                detail=f"{object_type} {object_id} was created but associating to {to_type}/{to_id} "
                       f"returned {r.status_code}: {r.text[:300]}",
            )
    return None


def create_hubspot_task(
    config: dict[str, Any],
    *,
    subject: str,
    body: str,
    contact_id: str | None = None,
    deal_id: str | None = None,
    owner_id: str | None = None,
    due_date_iso: str | None = None,
    timeout: int = 30,
) -> CrmWriteResult:
    """
    Create a single HubSpot task, status always NOT_STARTED. `config` is
    the write-scoped block (see the CLI for where this comes from — env
    vars for this workflow, matching hubspot_historical.py's convention,
    not a config.json): requires `access_token` (needs the
    `crm.objects.tasks.write` scope) and `write_access_confirmed: true`,
    a separate, explicit opt-in from the read-only puller's token/scope.

    Requires at least one of `contact_id`/`deal_id` — a task associated
    with nothing is orphaned and effectively invisible to the rep it's
    meant for.
    """
    if not config.get("write_access_confirmed"):
        return _fail(
            "task", "write_access_not_confirmed",
            "HUBSPOT_WRITE_ACCESS_CONFIRMED is not true — this is a separate, explicit opt-in "
            "from the read-only puller's token/scope, by design.",
        )
    if not contact_id and not deal_id:
        return _fail("task", "no_association_target", "at least one of contact_id/deal_id is required")

    access_token = config.get("access_token", "")
    if not access_token or str(access_token).startswith("REPLACE_WITH"):
        return _fail("task", "config_missing", "HUBSPOT_WRITE_TOKEN is not configured")

    base = "https://api.hubapi.com"
    headers = _headers(access_token)

    properties: dict[str, Any] = {
        "hs_task_subject": subject,
        "hs_task_body": body,
        "hs_task_status": "NOT_STARTED",  # never anything else — see module docstring
        "hs_task_type": "TODO",
    }
    if owner_id:
        properties["hubspot_owner_id"] = owner_id
    if due_date_iso:
        try:
            due_ms = int(datetime.fromisoformat(due_date_iso.replace("Z", "+00:00")).timestamp() * 1000)
            properties["hs_timestamp"] = str(due_ms)
        except ValueError:
            return _fail("task", "invalid_due_date", f"due_date_iso={due_date_iso!r} is not a valid ISO-8601 timestamp")

    try:
        r = requests.post(f"{base}/crm/v3/objects/tasks", headers=headers, json={"properties": properties}, timeout=timeout)
    except requests.RequestException as e:
        return _fail("task", "request_failed", str(e)[:500])
    if r.status_code not in (200, 201):
        detail = r.text[:500]
        try:
            detail = r.json().get("message", detail)
        except ValueError:
            pass
        return _fail("task", f"http_{r.status_code}", detail)
    try:
        task_id = r.json()["id"]
    except (ValueError, KeyError) as e:
        return _fail("task", "invalid_response", str(e)[:500])

    assoc_error = _associate_default(base, headers, "tasks", task_id, contact_id, deal_id, timeout)
    if assoc_error:
        return CrmWriteResult(action_type="task", status="error", object_id=task_id, error=assoc_error)

    return CrmWriteResult(
        action_type="task",
        status="ok",
        object_id=task_id,
        portal_url=f"https://app.hubspot.com/tasks/{config.get('portal_id', '')}/view/all",
    )


def create_hubspot_note(
    config: dict[str, Any],
    *,
    body: str,
    contact_id: str | None = None,
    deal_id: str | None = None,
    timeout: int = 30,
) -> CrmWriteResult:
    """
    Log a single HubSpot note. `config` — same shape as create_hubspot_task
    (requires `crm.objects.notes.write` scope on the same write-scoped
    token). Requires at least one of `contact_id`/`deal_id`, same reasoning
    as the task function.
    """
    if not config.get("write_access_confirmed"):
        return _fail(
            "note", "write_access_not_confirmed",
            "HUBSPOT_WRITE_ACCESS_CONFIRMED is not true — this is a separate, explicit opt-in "
            "from the read-only puller's token/scope, by design.",
        )
    if not contact_id and not deal_id:
        return _fail("note", "no_association_target", "at least one of contact_id/deal_id is required")

    access_token = config.get("access_token", "")
    if not access_token or str(access_token).startswith("REPLACE_WITH"):
        return _fail("note", "config_missing", "HUBSPOT_WRITE_TOKEN is not configured")

    base = "https://api.hubapi.com"
    headers = _headers(access_token)

    properties = {
        "hs_note_body": body,
        "hs_timestamp": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
    }

    try:
        r = requests.post(f"{base}/crm/v3/objects/notes", headers=headers, json={"properties": properties}, timeout=timeout)
    except requests.RequestException as e:
        return _fail("note", "request_failed", str(e)[:500])
    if r.status_code not in (200, 201):
        detail = r.text[:500]
        try:
            detail = r.json().get("message", detail)
        except ValueError:
            pass
        return _fail("note", f"http_{r.status_code}", detail)
    try:
        note_id = r.json()["id"]
    except (ValueError, KeyError) as e:
        return _fail("note", "invalid_response", str(e)[:500])

    assoc_error = _associate_default(base, headers, "notes", note_id, contact_id, deal_id, timeout)
    if assoc_error:
        return CrmWriteResult(action_type="note", status="error", object_id=note_id, error=assoc_error)

    return CrmWriteResult(
        action_type="note",
        status="ok",
        object_id=note_id,
        portal_url=f"https://app.hubspot.com/contacts/{config.get('portal_id', '')}/record/0-1/{contact_id}"
                   if contact_id else f"https://app.hubspot.com/notes/{config.get('portal_id', '')}",
    )


def create_crm_write(action_type: str, config: dict[str, Any], **kwargs: Any) -> CrmWriteResult:
    """Dispatch to the right function by action_type. See hubspot_task_create.py for the CLI."""
    if action_type == "task":
        return create_hubspot_task(config, **kwargs)
    if action_type == "note":
        return create_hubspot_note(config, **kwargs)
    return _fail(action_type, "unknown_action_type", f"no handler for {action_type!r} — only 'task' and 'note' exist")
