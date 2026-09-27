"""
site_snapshot.py
=================
Deterministic (no LLM) competitor page-change monitor. Fetches configured
competitor URLs via a real browser (`.claude/lib/browser_render.py`),
extracts visible text, and diffs it against last run's stored snapshot.
An alert is "this page's text content changed since <date>, here's the
mechanical diff" — never a narrative claim about WHY it changed. That's a
deliberate scope limit, not a missing feature.

Why deterministic hashing/diffing instead of an LLM describing the change:
this script runs unattended via cron, with no human watching each run. An
LLM asked to summarize "what changed" can hallucinate details that aren't
actually in the diff — and with nobody watching, a hallucinated summary
would sit in the alert feed looking exactly as credible as a real one.
A text-diff either shows a real removed/added line or it doesn't. This is
Group 1's reliability principle (evidence_log.py / citation_guard.py)
applied at the cheapest possible layer: don't even create a hallucination
surface for the routine 95% of runs where nothing happened.

The one place an LLM is genuinely needed — synthesizing "what does this
change probably mean," or re-checking a competitor's public ad presence
(Meta Ad Library / Google Ads Transparency Center have no plain REST API
to hash-diff against; they need `WebFetch`/`WebSearch`, which only a
Claude session has) — is intentionally a SEPARATE path: `scheduled_prompt.md`
in this directory, dispatched as a scheduled chat run, and it is REQUIRED
to go through `evidence_log.py` + `citation_guard.py` before anything it
finds is written to the alert ledger. Read that file before wiring it up.

This script never sends anything anywhere — no Slack, no email, no
webhook. It writes to `alerts.jsonl`, a local, append-only, human-reviewed
ledger, same reasoning as `approval_gate.py`: a cron job auto-posting to
an external channel with nobody watching is "sending a message on the
user's behalf" autonomously, which stays out of scope regardless of how
low-stakes the content is. The Chief Orchestrator surfaces unreviewed
alerts the next time an interactive session starts, the same pattern
already used for `pending_approval_gates`.

Run via cron, e.g. daily 6am:
    0 6 * * * cd ~/marketing-os/05-competitor-monitoring && \\
        /path/to/.venv/bin/python3 site_snapshot.py >> output/cron.log 2>&1

Usage:
    python3 site_snapshot.py                          # real run: fetch, diff, alert, update snapshots
    python3 site_snapshot.py --dry-run                 # fetch + diff, write nothing to disk
    python3 site_snapshot.py list-alerts [--status unreviewed|reviewed]
    python3 site_snapshot.py mark-reviewed --alert-id <id> [--note "..."]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude" / "lib"))
from browser_render import render_page  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SNAPSHOTS_DIR = ROOT / "snapshots"
ALERTS_LEDGER_PATH = ROOT / "alerts.jsonl"


class PageCheckResult(BaseModel):
    competitor: str
    url: str
    fetch_status: Literal["ok", "blocked", "error"]
    changed: bool | None = None  # None = no prior snapshot to compare against (first-ever check)
    blocked_reason: str | None = None
    error_detail: str | None = None
    alert_id: str | None = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"FATAL: {CONFIG_PATH} not found.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _safe_filename(url: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")[:150]


def extract_visible_text(html: str) -> str:
    """
    Full visible text, not just browser_render.py's 500-char excerpt — a
    change deep in the page must not be missed. Text (not raw HTML) is
    hashed/diffed on purpose: it's stable against the analytics IDs,
    cache-busting query strings, and inline script noise that make raw-HTML
    hashing false-positive on nearly every real page.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _read_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_snapshot(path: Path, content_hash: str, text_content: str, fetched_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "content_hash": content_hash,
        "text_content": text_content,
        "fetched_at": fetched_at,
    }, indent=2), encoding="utf-8")


def _append_alert(record: dict[str, Any]) -> None:
    ALERTS_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _read_alerts() -> list[dict[str, Any]]:
    if not ALERTS_LEDGER_PATH.exists():
        return []
    events = []
    for line in ALERTS_LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _latest_alert_status(events: list[dict[str, Any]], alert_id: str) -> dict[str, Any] | None:
    matches = [e for e in events if e.get("alert_id") == alert_id]
    return matches[-1] if matches else None


def check_one_url(competitor: str, url: str, dry_run: bool) -> PageCheckResult:
    result = render_page(url, wait_until="networkidle", timeout_ms=30_000)

    if result.status == "blocked":
        return PageCheckResult(competitor=competitor, url=url, fetch_status="blocked",
                                blocked_reason=result.blocked_reason)
    if result.status == "error":
        return PageCheckResult(competitor=competitor, url=url, fetch_status="error",
                                error_detail=f"{result.error.reason}: {result.error.detail}" if result.error else "unknown")

    html = Path(result.html_path).read_text(encoding="utf-8")
    text_content = extract_visible_text(html)
    content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()

    snapshot_path = SNAPSHOTS_DIR / f"{_safe_filename(url)}.json"
    previous = _read_snapshot(snapshot_path)

    if previous is None:
        if not dry_run:
            _write_snapshot(snapshot_path, content_hash, text_content, result.fetched_at)
        return PageCheckResult(competitor=competitor, url=url, fetch_status="ok", changed=None)

    changed = previous["content_hash"] != content_hash
    check = PageCheckResult(competitor=competitor, url=url, fetch_status="ok", changed=changed)

    if changed:
        diff_lines = list(difflib.unified_diff(
            previous["text_content"].splitlines(), text_content.splitlines(),
            fromfile=f"{url} (previous, {previous['fetched_at']})",
            tofile=f"{url} (current, {result.fetched_at})",
            lineterm="", n=1,
        ))[:60]  # cap: this is a pointer for a human to go look, not the full page
        alert_id = f"alert_{hashlib.sha256(f'{url}{result.fetched_at}'.encode()).hexdigest()[:12]}"
        _append_alert({
            "alert_id": alert_id,
            "event": "detected",
            "source": "site_diff",  # vs. "ad_library_reaudit" — see scheduled_prompt.md; same ledger, same CLI
            "competitor": competitor,
            "url": url,
            "detected_at": result.fetched_at,
            "previous_hash": previous["content_hash"],
            "current_hash": content_hash,
            "diff_snippet": diff_lines,
        })
        check.alert_id = alert_id

    if not dry_run:
        _write_snapshot(snapshot_path, content_hash, text_content, result.fetched_at)

    return check


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config()
    competitors = config.get("competitors", [])
    if not competitors:
        sys.exit("FATAL: config.json has no competitors configured — nothing to monitor.")

    print(f"\n{'='*60}")
    print(f"Competitor site monitoring — {len(competitors)} competitor(s)")
    print(f"{'='*60}\n")

    results: list[PageCheckResult] = []
    for comp in competitors:
        name = comp["name"]
        for url in comp.get("urls", []):
            r = check_one_url(name, url, args.dry_run)
            results.append(r)
            flag = {"ok": "OK", "blocked": "BLOCKED", "error": "ERROR"}[r.fetch_status]
            change_note = (
                " (no baseline yet)" if r.changed is None and r.fetch_status == "ok" else
                " — CHANGED, alert logged" if r.changed else
                " — unchanged" if r.fetch_status == "ok" else ""
            )
            print(f"  [{flag}] {name}: {url}{change_note}")
            if r.fetch_status == "blocked":
                print(f"        blocked_reason={r.blocked_reason} — a real bot-challenge, not a tool failure; "
                      f"not treated as 'no change', reported as unmeasured for this run")
            if r.fetch_status == "error":
                print(f"        {r.error_detail}")

    ok_count = sum(1 for r in results if r.fetch_status == "ok")
    changed_count = sum(1 for r in results if r.changed)
    blocked_count = sum(1 for r in results if r.fetch_status == "blocked")
    error_count = sum(1 for r in results if r.fetch_status == "error")

    print(f"\n{ok_count} checked OK, {changed_count} changed (alerts logged), "
          f"{blocked_count} blocked, {error_count} errored")
    if args.dry_run:
        print("(--dry-run: no snapshots or alerts were written to disk)")
    else:
        print(f"Alerts ledger: {ALERTS_LEDGER_PATH}")
    return 0


def cmd_list_alerts(args: argparse.Namespace) -> int:
    """
    Lists one row per alert_id: the original "detected" event's fields
    (competitor, url, detected_at, diff_snippet) merged with the latest
    lifecycle event's status — a "reviewed" event only carries alert_id/
    timestamp/note, so displaying it alone would silently drop the very
    context (which competitor, which URL) a human needs to make sense of
    the listing.
    """
    events = _read_alerts()
    by_id: dict[str, list[dict]] = {}
    for e in events:
        by_id.setdefault(e["alert_id"], []).append(e)

    rows = []
    for evts in by_id.values():
        detected = next((e for e in evts if e["event"] == "detected"), evts[0])
        latest = evts[-1]
        rows.append({**detected, "event": latest["event"], "review_note": latest.get("note", "")})

    if args.status:
        rows = [r for r in rows if r["event"] == args.status]
    rows.sort(key=lambda r: r.get("detected_at", ""), reverse=True)

    if not rows:
        print(f"No alerts{' with status ' + args.status if args.status else ''}.")
        return 0
    for r in rows:
        note_part = f" — note: {r['review_note']}" if r.get("review_note") else ""
        source_part = f" [{r['source']}]" if r.get("source") else ""
        print(f"[{r['event']}]{source_part} {r['alert_id']} — {r.get('competitor', '?')}: {r.get('url', '?')} "
              f"(detected {r.get('detected_at', '?')}){note_part}")
    return 0


def cmd_mark_reviewed(args: argparse.Namespace) -> int:
    events = _read_alerts()
    latest = _latest_alert_status(events, args.alert_id)
    if latest is None:
        print(f"ERROR: alert_id {args.alert_id!r} not found.", file=sys.stderr)
        return 1
    if latest["event"] == "reviewed":
        print(f"NOTE: {args.alert_id} is already marked reviewed (at {latest.get('timestamp', '?')}). "
              f"Recording this as a re-confirmation, not a duplicate.")
    _append_alert({
        "alert_id": args.alert_id,
        "event": "reviewed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": args.note or "",
    })
    print(f"Marked {args.alert_id} reviewed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="(only applies to the default run) Fetch + diff, write nothing to disk")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Fetch, diff, alert, update snapshots (default if no subcommand given)")
    run_p.add_argument("--dry-run", action="store_true", help="Fetch + diff, write nothing to disk")
    run_p.set_defaults(func=cmd_run)

    list_p = sub.add_parser("list-alerts", help="List alerts, optionally filtered by status")
    list_p.add_argument("--status", choices=["detected", "reviewed"], default=None)
    list_p.set_defaults(func=cmd_list_alerts)

    review_p = sub.add_parser("mark-reviewed", help="Mark one alert as reviewed")
    review_p.add_argument("--alert-id", required=True)
    review_p.add_argument("--note", default=None)
    review_p.set_defaults(func=cmd_mark_reviewed)

    args = parser.parse_args()
    if args.command is None:
        # No subcommand given -> default to `run` (so cron's plain
        # `python3 site_snapshot.py [--dry-run]` still works unchanged).
        args.func = cmd_run

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
