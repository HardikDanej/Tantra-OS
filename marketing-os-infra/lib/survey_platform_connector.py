"""
survey_platform_connector.py
=============================
Read-only pull of real, already-collected survey responses from Typeform and
SurveyMonkey. This is the Tool-layer connector for the Market Research &
Consumer Insights system's Primary Research domain — closing that system's
previous zero-live-data-access state for `quantitative-survey-design-
sampling-subagent` and `nps-csat-audit-subagent` specifically.

**This module contains ONLY read functions.** There is no
`create_survey`/`send_survey`/`field_survey` function anywhere in this file,
and there never should be — the Market Research system's own defining
constraint (see `primary-research-customer-discovery-agent.md` and
`market-research-insights-orchestrator.md`) is that it has no live human-
subject contact: it designs the instrument a human fields, it never fields
one itself. That's enforced here structurally, the same way
`cms_connector.py` structurally enforces draft-only by never accepting a
status parameter — except stricter: there is no write capability of any
kind to remove, because none was ever added. If a future, explicit decision
is made to let this system trigger a live survey send, that is a new
capability requiring its own sign-off, not an extension of this module.

Every call returns a `PullResult` (see `tool_router.py`) — never raises past
its own boundary, never returns a bare dict, never silently returns an empty
result on a real failure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_router import PullResult, SurveyResponseRow, validate_rows  # noqa: E402


def pull_typeform_responses(config: dict[str, Any], *, form_id: str, page_size: int = 200,
                             timeout: int = 30) -> PullResult:
    """
    `config` is the `typeform` block from config.json: requires `api_token`
    (a personal access token from Typeform's Developer settings, read-only
    scope `responses:read` is sufficient — never grant more).
    https://www.typeform.com/developers/responses/reference/retrieve-responses/
    """
    result = PullResult(platform="typeform", accounts_attempted=[form_id])
    token = config.get("api_token", "")
    if not token or str(token).startswith("REPLACE_WITH"):
        result.record_failure(form_id, RuntimeError("typeform.api_token is not configured"))
        return result.finalize()

    url = f"https://api.typeform.com/forms/{form_id}/responses"
    headers = {"Authorization": f"Bearer {token}"}
    raw_rows: list[dict[str, Any]] = []
    page_token = None
    try:
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["before"] = page_token
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            r.raise_for_status()
            body = r.json()
            items = body.get("items", [])
            if not items:
                break
            for item in items:
                submitted_at = item.get("submitted_at", "")
                response_id = item.get("response_id") or item.get("token", "")
                for answer in item.get("answers", []) or []:
                    field = answer.get("field", {})
                    value = (
                        answer.get("text") or answer.get("email") or answer.get("phone_number")
                        or (str(answer.get("number")) if "number" in answer else None)
                        or (str(answer.get("boolean")) if "boolean" in answer else None)
                        or (answer.get("choice", {}) or {}).get("label")
                        or ", ".join((answer.get("choices", {}) or {}).get("labels", []) or [])
                        or ""
                    )
                    raw_rows.append({
                        "platform": "typeform", "survey_id": form_id, "respondent_id": response_id,
                        "question_id": field.get("id", ""), "question_text": field.get("ref"),
                        "answer": value, "submitted_at": submitted_at,
                    })
            if len(items) < page_size:
                break
            page_token = items[-1].get("token")
    except requests.RequestException as e:
        result.record_failure(form_id, e)
        return result.finalize()

    good, bad = validate_rows(raw_rows, schema=SurveyResponseRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


def pull_surveymonkey_responses(config: dict[str, Any], *, survey_id: str, per_page: int = 100,
                                 timeout: int = 30) -> PullResult:
    """
    `config` is the `surveymonkey` block from config.json: requires
    `access_token` (OAuth token, `surveys_read` + `responses_read_detail`
    scopes — read-only, never request write scopes for this connector).
    https://developer.surveymonkey.com/api/v3/#surveys-id-responses-bulk
    """
    result = PullResult(platform="surveymonkey", accounts_attempted=[survey_id])
    token = config.get("access_token", "")
    if not token or str(token).startswith("REPLACE_WITH"):
        result.record_failure(survey_id, RuntimeError("surveymonkey.access_token is not configured"))
        return result.finalize()

    url = f"https://api.surveymonkey.com/v3/surveys/{survey_id}/responses/bulk"
    headers = {"Authorization": f"Bearer {token}"}
    raw_rows: list[dict[str, Any]] = []
    page = 1
    try:
        while True:
            r = requests.get(url, headers=headers, params={"page": page, "per_page": per_page}, timeout=timeout)
            r.raise_for_status()
            body = r.json()
            data = body.get("data", [])
            if not data:
                break
            for resp in data:
                respondent_id = resp.get("id", "")
                submitted_at = resp.get("date_modified", "")
                for page_data in resp.get("pages", []) or []:
                    for q in page_data.get("questions", []) or []:
                        q_id = q.get("id", "")
                        for a in q.get("answers", []) or []:
                            value = a.get("text") or a.get("choice_id") or a.get("other_id") or ""
                            raw_rows.append({
                                "platform": "surveymonkey", "survey_id": survey_id, "respondent_id": respondent_id,
                                "question_id": q_id, "question_text": None,
                                "answer": str(value), "submitted_at": submitted_at,
                            })
            if not body.get("links", {}).get("next"):
                break
            page += 1
    except requests.RequestException as e:
        result.record_failure(survey_id, e)
        return result.finalize()

    good, bad = validate_rows(raw_rows, schema=SurveyResponseRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


PLATFORM_PULLERS = {"typeform": pull_typeform_responses, "surveymonkey": pull_surveymonkey_responses}


def pull(platform: str, config: dict[str, Any], **kwargs: Any) -> PullResult:
    """Dispatch to the right connector by platform name. See survey_results_pull.py for the CLI."""
    if platform not in PLATFORM_PULLERS:
        result = PullResult(platform=platform, accounts_attempted=[kwargs.get("form_id") or kwargs.get("survey_id") or "?"])
        result.record_failure("config", RuntimeError(f"no connector for platform {platform!r}"))
        return result.finalize()
    return PLATFORM_PULLERS[platform](config, **kwargs)
