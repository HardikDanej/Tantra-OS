"""
product_analytics_connector.py
===============================
Read-only pull of real product-usage events from Amplitude and Mixpanel.
Tool-layer connector for the Market Research & Consumer Insights system's
`marketing-analytics-attribution-modeling-agent` — specifically
`product-analytics-cohort-retention-subagent`, whose real output
(`analytics/cohort_retention.md`) is the canonical cohort-computation source
the Product Marketing & GTM system's `product-market-fit-validation-subagent`
and Digital Marketing & Growth's Revenue/CRM `rfm-segmentation-subagent`
should consume rather than each re-deriving their own retention math (see
`cross-system-dispatch-bridge.md`'s file-contract table).

Read-only: no event-tracking/write function exists here. This connector
pulls what already happened; it never sends an event, never modifies a
cohort definition inside the platform, never writes back to it.

Every call returns a `PullResult` (see `tool_router.py`) — cohort/retention
math itself is computed by `product-analytics-cohort-retention-subagent` via
Bash from these real rows, never estimated by this connector or by the
calling agent.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_router import ProductEventRow, PullResult, validate_rows  # noqa: E402


def pull_amplitude_events(config: dict[str, Any], *, start: str, end: str,
                           event_names: list[str] | None = None, timeout: int = 60) -> PullResult:
    """
    `config` is the `amplitude` block from config.json: requires `api_key`
    and `secret_key` (project keys from Amplitude → Settings → Projects —
    read-scoped; Amplitude's Export API is read-only by nature, no separate
    write scope exists to accidentally over-grant).
    `start`/`end` are `YYYYMMDD` strings (Amplitude Export API convention).
    https://amplitude.com/docs/apis/analytics/export
    """
    result = PullResult(platform="amplitude", accounts_attempted=[f"{start}-{end}"])
    api_key = config.get("api_key", "")
    secret_key = config.get("secret_key", "")
    if not api_key or str(api_key).startswith("REPLACE_WITH") or not secret_key or str(secret_key).startswith("REPLACE_WITH"):
        result.record_failure(f"{start}-{end}", RuntimeError("amplitude.api_key / secret_key not configured"))
        return result.finalize()

    url = "https://amplitude.com/api/2/export"
    raw_rows: list[dict[str, Any]] = []
    try:
        # Amplitude's export endpoint returns a zipped set of gzipped JSON-lines files.
        import gzip
        import io
        import json
        import zipfile

        r = requests.get(url, params={"start": start, "end": end}, auth=(api_key, secret_key), timeout=timeout)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for name in zf.namelist():
                with zf.open(name) as f, gzip.GzipFile(fileobj=f) as gz:
                    for line in gz.read().decode("utf-8").splitlines():
                        if not line.strip():
                            continue
                        event = json.loads(line)
                        event_type = event.get("event_type", "")
                        if event_names and event_type not in event_names:
                            continue
                        raw_rows.append({
                            "platform": "amplitude",
                            "user_id": event.get("user_id") or event.get("device_id", "unknown"),
                            "event_name": event_type,
                            "event_time": event.get("event_time") or event.get("client_event_time")
                                          or datetime.now(timezone.utc).isoformat(),
                            "properties_json": json.dumps(event.get("event_properties", {}) or {}),
                        })
    except requests.RequestException as e:
        result.record_failure(f"{start}-{end}", e)
        return result.finalize()
    except Exception as e:  # zip/gzip parsing — a genuinely malformed export shouldn't crash the caller
        result.record_failure(f"{start}-{end}", e)
        return result.finalize()

    good, bad = validate_rows(raw_rows, schema=ProductEventRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


def pull_mixpanel_events(config: dict[str, Any], *, from_date: str, to_date: str,
                          event_names: list[str] | None = None, timeout: int = 60) -> PullResult:
    """
    `config` is the `mixpanel` block from config.json: requires
    `service_account_username` and `service_account_secret` (a Mixpanel
    Service Account scoped to this project — Project Settings → Service
    Accounts) and `project_id`. `from_date`/`to_date` are `YYYY-MM-DD`.
    https://developer.mixpanel.com/reference/raw-event-export
    """
    result = PullResult(platform="mixpanel", accounts_attempted=[f"{from_date}-{to_date}"])
    user = config.get("service_account_username", "")
    secret = config.get("service_account_secret", "")
    project_id = config.get("project_id", "")
    if not user or str(user).startswith("REPLACE_WITH") or not secret or str(secret).startswith("REPLACE_WITH"):
        result.record_failure(f"{from_date}-{to_date}", RuntimeError("mixpanel service-account credentials not configured"))
        return result.finalize()

    url = "https://data.mixpanel.com/api/2.0/export"
    params: dict[str, Any] = {"from_date": from_date, "to_date": to_date, "project_id": project_id}
    if event_names:
        import json as _json
        params["event"] = _json.dumps(event_names)

    raw_rows: list[dict[str, Any]] = []
    try:
        import json

        r = requests.get(url, params=params, auth=(user, secret), timeout=timeout, stream=True)
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            props = event.get("properties", {}) or {}
            raw_rows.append({
                "platform": "mixpanel",
                "user_id": props.get("distinct_id", "unknown"),
                "event_name": event.get("event", ""),
                "event_time": datetime.fromtimestamp(props.get("time", 0), tz=timezone.utc).isoformat()
                              if props.get("time") else datetime.now(timezone.utc).isoformat(),
                "properties_json": json.dumps({k: v for k, v in props.items() if not k.startswith("$") and k != "time"}),
            })
    except requests.RequestException as e:
        result.record_failure(f"{from_date}-{to_date}", e)
        return result.finalize()
    except Exception as e:
        result.record_failure(f"{from_date}-{to_date}", e)
        return result.finalize()

    good, bad = validate_rows(raw_rows, schema=ProductEventRow)
    result.rows = good
    result.validation_errors = bad
    return result.finalize()


PLATFORM_PULLERS = {"amplitude": pull_amplitude_events, "mixpanel": pull_mixpanel_events}


def pull(platform: str, config: dict[str, Any], **kwargs: Any) -> PullResult:
    """Dispatch to the right connector by platform name. See product_analytics_pull.py for the CLI."""
    if platform not in PLATFORM_PULLERS:
        result = PullResult(platform=platform, accounts_attempted=["?"])
        result.record_failure("config", RuntimeError(f"no connector for platform {platform!r}"))
        return result.finalize()
    return PLATFORM_PULLERS[platform](config, **kwargs)
