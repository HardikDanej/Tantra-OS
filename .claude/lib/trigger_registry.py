"""
trigger_registry.py
====================
Deterministic trigger registry and condition-checker, for the Trigger layer
this repository previously had only one narrow instance of: workflow 05's
cron (`site_snapshot.py`, daily, deterministic) + Claude Scheduling
(`scheduled_prompt.md`, weekly, LLM-driven) pair. Everything else in this
~150-agent system only ever ran on a human message or a manual Agent
dispatch — there was no general "condition X in the workspace's own state
-> surface it, or fire a dispatch" mechanism, and no single place recording
which time-based triggers exist across every workflow.

This script gives every one of the five orchestrators (chief-marketing-
orchestrator, brand-creative-orchestrator, product-marketing-gtm-
orchestrator, market-research-insights-orchestrator, pr-corporate-
communications-orchestrator) and the cross-system-dispatch-bridge two
things:

1. A registry (`memory/triggers.jsonl`, append-only, same ledger
   convention as `approval_gate.py`) of every trigger that exists for this
   workspace — both EXTERNAL ones (a real crontab entry, a real Claude
   Scheduling job — this script can't execute those, only document them so
   they're not scattered across a dozen READMEs) and INTERNAL ones (a
   deterministic condition against this workspace's own state files, which
   `check` can actually evaluate right now, no external scheduler needed).

2. A `check` command that evaluates every active `condition`-type trigger
   against the real workspace state (`memory/approval_gates.jsonl`,
   `memory/outcomes.jsonl`, `memory/redispatch_log.jsonl`, and workflow 05's
   `alerts.jsonl` if it exists) and reports which ones actually fired. This
   is meant to run once per orchestrator session, the same place Step 7 of
   `chief-marketing-orchestrator.md` already checked workflow 05's alerts —
   this generalizes that one hand-written check into a real, extensible
   mechanism instead of a special case.

Condition kinds this script knows how to evaluate (add a new one by adding
a function to CONDITION_CHECKERS, same extension pattern as
`context_budget.py`'s ROLLUP_FUNCS):

- `pending_gate_age` — an `approval_gates.jsonl` gate has been `pending`
  longer than `params.max_pending_days`. Catches a HITL gate the user never
  actually responded to, silently sitting there — see `params`: {"max_pending_days": 3}.
- `redispatch_cap_reached` — a `redispatch_log.jsonl` cycle hit its cap
  (ESCALATE) and was never resolved. Catches an escalation that got
  surfaced once but never actually followed up on.
- `outcome_pattern_repeat` — `context_budget.py`'s outcomes rollup shows
  the same `distinct_implications` phrase (or a phrase containing
  `params.contains`) appearing at least `params.min_occurrences` times.
  Catches "we've now seen this same pattern N times, this deserves a
  proactive re-strategize dispatch" instead of waiting for the user to
  notice it themselves.
- `unreviewed_monitoring_alerts` — workflow 05's `alerts.jsonl` has entries
  with `status: "detected"` that haven't been marked reviewed.

Three more read `memory/sentinel_runs.jsonl`, the one-line-per-turn
summary Tantra's sentinel hooks write (scribe, at Stop). They only look at
summaries newer than `params.max_age_days` (default 7) and newer than the
trigger's last `acknowledge`, so a handled finding does not re-fire forever:
- `stalled_dispatch` — at least `params.min_stalls` (1) dispatches were
  reported stalled by the pulse watchdog. Catches a background child that
  keeps never returning, run after run.
- `repeated_read_loop` — the same read/fetch was repeated at least
  `params.min_calls` (3) times in one run, or echo denied at least
  `params.min_denials` (1) calls. Catches an agent stuck re-reading.
- `token_hotspot` — at least `params.min_hotspots` (1) dispatches went over
  their tier's token/time budget (meter), optionally only those with
  `params.min_output_tokens` or more output tokens.

Registry line shape (append-only, one line per lifecycle event — mirrors
`approval_gate.py`'s pattern exactly):
{
  "trigger_id": "stable slug",
  "event": "registered | fired | acknowledged | disabled",
  "timestamp": "ISO-8601",
  "kind": "cron | scheduled_prompt | condition",
  "condition_kind": "pending_gate_age | redispatch_cap_reached | outcome_pattern_repeat | unreviewed_monitoring_alerts | stalled_dispatch | repeated_read_loop | token_hotspot | null (for cron/scheduled_prompt)",
  "params": {...},
  "target": "what fires -- a script path, an orchestrator id, or 'surface to user'",
  "description": "one line, what this trigger is for",
  "cadence": "a crontab expression or 'weekly'/'daily' -- only meaningful for cron/scheduled_prompt kinds",
  "detail": "present on 'fired' events -- what was actually found"
}

Usage:
    python trigger_registry.py memory/triggers.jsonl register \\
        --trigger-id stale_gate_watch --kind condition \\
        --condition-kind pending_gate_age --params '{"max_pending_days": 3}' \\
        --target "surface to user" --description "Flag a HITL gate nobody responded to"

    python trigger_registry.py memory/triggers.jsonl register \\
        --trigger-id competitor_ad_reaudit --kind scheduled_prompt \\
        --target "marketing-os-infra/05-competitor-monitoring/scheduled_prompt.md" \\
        --cadence weekly --description "Weekly ad-library re-audit (see workflow 05)"

    python trigger_registry.py memory/triggers.jsonl check \\
        --workspace-root . --gates-ledger memory/approval_gates.jsonl \\
        --outcomes-log memory/outcomes.jsonl --redispatch-log memory/redispatch_log.jsonl

    `--workspace-root DIR` resolves the relative ledger and workspace state
    paths (triggers, gates, outcomes, redispatch, sentinel runs) against DIR
    instead of the current directory; `--alerts-log` stays as given, since
    it points into the framework repo, not the workspace.

    python trigger_registry.py memory/triggers.jsonl list [--kind condition] [--status active]
    python trigger_registry.py memory/triggers.jsonl acknowledge --trigger-id stale_gate_watch
    python trigger_registry.py memory/triggers.jsonl disable --trigger-id stale_gate_watch

Exit codes: `check` returns 0 always (firing is informational, not a
failure) but prints a summary a calling orchestrator should surface, not
swallow. `register`/`disable`/`acknowledge` return 1 on a bad trigger_id or
malformed params.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

VALID_KINDS = {"cron", "scheduled_prompt", "condition", "event"}
VALID_CONDITION_KINDS = {"pending_gate_age", "redispatch_cap_reached", "outcome_pattern_repeat", "unreviewed_monitoring_alerts",
                         "stalled_dispatch", "repeated_read_loop", "token_hotspot"}
# "event" kind (gap #6): the OS blueprint's Section 12 Event trigger type (lead.created;
# campaign.launched; opportunity.stage_changed), built as a real pull-then-diff mechanism via
# event_diff.py -- see that module's docstring for why this system detects rather than receives
# these, and why "lead.created" isn't included (no contact-level snapshot exists anywhere yet).
VALID_EVENT_KINDS = {"campaign_launched", "opportunity_created_or_stage_changed"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{line_no}: malformed JSON ({e})") from e
    return entries


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _latest_per_trigger(entries: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for e in entries:
        tid = e.get("trigger_id")
        if tid:
            latest[tid] = e  # later lines overwrite -- last event wins, same as approval_gate.py
    return latest


def _read_jsonl_safe(path: Path) -> list[dict]:
    """Same shape as context_budget.py's read_jsonl, tolerant of a missing file (that's a legitimate state)."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a check-time scan tolerates a bad line; approval_gate.py/context_budget.py are the strict readers
    return entries


# ---------------------------------------------------------------------------
# Condition checkers -- each takes (registered trigger dict, workspace paths)
# and returns a `detail` string if the trigger fired, or None if it didn't.
# ---------------------------------------------------------------------------

def check_pending_gate_age(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    max_days = trigger.get("params", {}).get("max_pending_days", 3)
    entries = _read_jsonl_safe(paths["gates"])
    latest_by_gate: dict[str, dict] = {}
    for e in entries:
        gid = e.get("gate_id")
        if gid:
            latest_by_gate[gid] = e
    stale = []
    now_dt = datetime.now(timezone.utc)
    for gid, e in latest_by_gate.items():
        if e.get("event") != "pending":
            continue
        try:
            created = datetime.fromisoformat(e["timestamp"])
        except (KeyError, ValueError):
            continue
        age_days = (now_dt - created).total_seconds() / 86400
        if age_days >= max_days:
            stale.append(f"{gid} (pending {age_days:.1f}d, stakes_class={e.get('stakes_class', '?')})")
    if stale:
        return f"{len(stale)} gate(s) pending >= {max_days}d: " + "; ".join(stale)
    return None


def check_redispatch_cap_reached(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    entries = _read_jsonl_safe(paths["redispatch"])
    cycles: dict[str, dict] = {}
    for e in entries:
        cid = e.get("cycle_id")
        if not cid:
            continue
        c = cycles.setdefault(cid, {"attempts": 0, "resolved": False})
        if e.get("event") == "attempt":
            c["attempts"] += 1
        elif e.get("event") == "resolved":
            c["resolved"] = True
    unresolved_at_cap = [cid for cid, c in cycles.items() if c["attempts"] >= 2 and not c["resolved"]]
    if unresolved_at_cap:
        return f"{len(unresolved_at_cap)} redispatch cycle(s) hit the cap and were never resolved: {', '.join(unresolved_at_cap)}"
    return None


def check_outcome_pattern_repeat(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    params = trigger.get("params", {})
    min_occurrences = params.get("min_occurrences", 3)
    contains = (params.get("contains") or "").lower()
    entries = _read_jsonl_safe(paths["outcomes"])
    implications = [e.get("implications", "") for e in entries if e.get("implications")]
    if contains:
        matches = [i for i in implications if contains in i.lower()]
    else:
        matches = implications
    if len(matches) >= min_occurrences:
        return f"{len(matches)} outcome(s) recorded an implication matching {contains or '(any)'!r} (threshold {min_occurrences}): most recent -- {matches[-1]}"
    return None


def check_unreviewed_monitoring_alerts(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    alerts_path = paths.get("alerts")
    if not alerts_path or not alerts_path.exists():
        return None
    entries = _read_jsonl_safe(alerts_path)
    unreviewed = [e for e in entries if e.get("status") == "detected"]
    if unreviewed:
        return f"{len(unreviewed)} unreviewed competitor-monitoring alert(s) (workflow 05)"
    return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _recent_sentinel_runs(trigger: dict, paths: dict[str, Path]) -> list[dict]:
    """sentinel_runs.jsonl summaries inside the trigger's window and after its last acknowledge."""
    path = paths.get("sentinel_runs")
    if not path or not path.exists():
        return []
    max_age_days = trigger.get("params", {}).get("max_age_days", 7)
    floor = datetime.now(timezone.utc).timestamp() - float(max_age_days) * 86400
    acked = _parse_ts(trigger.get("acknowledged_at"))
    if acked:
        floor = max(floor, acked.timestamp())
    runs = []
    for run in _read_jsonl_safe(path):
        ts = _parse_ts(run.get("ts"))
        if ts and ts.timestamp() > floor:
            runs.append(run)
    return runs


def check_stalled_dispatch(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    min_stalls = trigger.get("params", {}).get("min_stalls", 1)
    stalls = [s for run in _recent_sentinel_runs(trigger, paths) for s in (run.get("stalls") or [])]
    if len(stalls) < min_stalls:
        return None
    agents = Counter(s.get("agent_type") or "?" for s in stalls)
    listed = ", ".join(f"{a} x{n}" for a, n in agents.most_common(8))
    return f"{len(stalls)} Tantra dispatch(es) reported stalled by the pulse watchdog (threshold {min_stalls}): {listed}"


def check_repeated_read_loop(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    params = trigger.get("params", {})
    min_calls = params.get("min_calls", 3)
    min_denials = params.get("min_denials", 1)
    runs = _recent_sentinel_runs(trigger, paths)
    loops = [r for run in runs for r in (run.get("repeated_reads") or []) if (r.get("calls") or 0) >= min_calls]
    denials = sum(int((run.get("denials") or {}).get("echo") or 0) for run in runs)
    if not loops and denials < min_denials:
        return None
    parts = []
    if loops:
        worst = sorted(loops, key=lambda r: -(r.get("calls") or 0))[:5]
        parts.append(f"{len(loops)} repeated read(s) of >= {min_calls} identical calls: "
                     + "; ".join(f"{r.get('desc')} x{r.get('calls')}" for r in worst))
    if denials >= min_denials:
        parts.append(f"{denials} repeated call(s) denied by the echo sentinel")
    return " | ".join(parts)


def check_token_hotspot(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    params = trigger.get("params", {})
    min_hotspots = params.get("min_hotspots", 1)
    min_output = params.get("min_output_tokens", 0)
    hotspots = [h for run in _recent_sentinel_runs(trigger, paths) for h in (run.get("hotspots") or [])
                if (h.get("output_tokens") or 0) >= min_output]
    if len(hotspots) < min_hotspots:
        return None
    worst = sorted(hotspots, key=lambda h: -(h.get("output_tokens") or 0))[:5]
    listed = "; ".join(f"{h.get('agent_type')} {h.get('output_tokens') or 0:,} output tokens" for h in worst)
    return f"{len(hotspots)} Tantra dispatch(es) went over their token/time budget (threshold {min_hotspots}): {listed}"


CONDITION_CHECKERS = {
    "pending_gate_age": check_pending_gate_age,
    "redispatch_cap_reached": check_redispatch_cap_reached,
    "outcome_pattern_repeat": check_outcome_pattern_repeat,
    "unreviewed_monitoring_alerts": check_unreviewed_monitoring_alerts,
    "stalled_dispatch": check_stalled_dispatch,
    "repeated_read_loop": check_repeated_read_loop,
    "token_hotspot": check_token_hotspot,
}


# ---------------------------------------------------------------------------
# Event checkers (gap #6) -- pull-then-diff, never a live API call from
# inside `check` itself. Unlike the condition checkers above (pure read),
# these ADVANCE the snapshot on every check that finds a real change --
# deliberately, like a queue consumer moving its read offset forward, not
# like version_manifest.py's git-like "review before accepting a new
# baseline" model. The next check should count from here, not the
# original baseline, or it would re-fire the same change forever.
# ---------------------------------------------------------------------------

def _run_event_diff(trigger: dict) -> Optional[str]:
    from event_diff import load_records, diff_records  # local import: keeps trigger_registry.py
    params = trigger.get("params", {})                  # importable standalone even without event_diff.py present
    current_path = Path(params["current"])
    snapshot_path = Path(params["snapshot"])
    id_field = params["id_field"]
    watch_fields = params.get("watch_fields", [])

    if not current_path.exists():
        return None  # the real puller that writes this file hasn't run yet -- not a failure, just nothing to check

    current = load_records(current_path, id_field)
    previous = load_records(snapshot_path, id_field)
    result = diff_records(previous, current, watch_fields)

    if not previous and current:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(list(current.values()), indent=2, sort_keys=True), encoding="utf-8")
        return None  # first-ever snapshot: baseline silently, same as event_diff.py's own CLI behavior

    detail_parts = []
    if result["new_ids"]:
        detail_parts.append(f"{len(result['new_ids'])} new record(s): {', '.join(result['new_ids'][:10])}")
    if result["changed"]:
        changes = "; ".join(f"{c['id']}.{c['field']}: {c['old']!r}->{c['new']!r}" for c in result["changed"][:10])
        detail_parts.append(f"{len(result['changed'])} field change(s): {changes}")

    if detail_parts:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(list(current.values()), indent=2, sort_keys=True), encoding="utf-8")
        return "; ".join(detail_parts)
    return None


def check_campaign_launched(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    return _run_event_diff(trigger)


def check_opportunity_created_or_stage_changed(trigger: dict, paths: dict[str, Path]) -> Optional[str]:
    return _run_event_diff(trigger)


EVENT_CHECKERS = {
    "campaign_launched": check_campaign_launched,
    "opportunity_created_or_stage_changed": check_opportunity_created_or_stage_changed,
}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_register(args: argparse.Namespace) -> int:
    if args.kind in ("condition", "event"):
        valid_set = VALID_CONDITION_KINDS if args.kind == "condition" else VALID_EVENT_KINDS
        if not args.condition_kind or args.condition_kind not in valid_set:
            print(f"ERROR: --condition-kind is required and must be one of {sorted(valid_set)} "
                  f"when --kind {args.kind}", file=sys.stderr)
            return 1
        try:
            params = json.loads(args.params) if args.params else {}
        except json.JSONDecodeError as e:
            print(f"ERROR: --params is not valid JSON: {e}", file=sys.stderr)
            return 1
        if args.kind == "event":
            missing = [k for k in ("current", "snapshot", "id_field") if k not in params]
            if missing:
                print(f"ERROR: --params for an event trigger must include {missing} "
                      f"(e.g. '{{\"current\": \"...\", \"snapshot\": \"...\", \"id_field\": \"ad_id\", "
                      f"\"watch_fields\": [\"campaign_name\"]}}')", file=sys.stderr)
                return 1
    else:
        params = {}

    entry = {
        "trigger_id": args.trigger_id, "event": "registered", "timestamp": now(),
        "kind": args.kind, "condition_kind": args.condition_kind, "params": params,
        "target": args.target, "description": args.description, "cadence": args.cadence,
    }
    _append(Path(args.ledger), entry)
    print(f"Registered trigger {args.trigger_id!r} (kind={args.kind}"
          + (f", condition_kind={args.condition_kind}" if args.condition_kind else "") + ")")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    entries = _read_ledger(Path(args.ledger))
    latest = _latest_per_trigger(entries)
    if args.trigger_id not in latest:
        print(f"ERROR: trigger_id {args.trigger_id!r} was never registered.", file=sys.stderr)
        return 1
    _append(Path(args.ledger), {**latest[args.trigger_id], "event": "disabled", "timestamp": now()})
    print(f"Disabled trigger {args.trigger_id!r}.")
    return 0


def cmd_acknowledge(args: argparse.Namespace) -> int:
    entries = _read_ledger(Path(args.ledger))
    latest = _latest_per_trigger(entries)
    if args.trigger_id not in latest:
        print(f"ERROR: trigger_id {args.trigger_id!r} was never registered.", file=sys.stderr)
        return 1
    base = dict(latest[args.trigger_id])
    base.pop("detail", None)
    stamp = now()
    _append(Path(args.ledger), {**base, "event": "acknowledged", "timestamp": stamp, "acknowledged_at": stamp})
    print(f"Acknowledged trigger {args.trigger_id!r} — its condition can fire again on a future check.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = _read_ledger(Path(args.ledger))
    latest = _latest_per_trigger(entries)
    for tid, e in sorted(latest.items()):
        status = "disabled" if e["event"] == "disabled" else "active"
        if args.status and status != args.status:
            continue
        if args.kind and e.get("kind") != args.kind:
            continue
        print(f"{tid:30s} [{status:8s}] kind={e.get('kind'):16s} "
              f"target={e.get('target')!r:40s} last_event={e['event']} at {e['timestamp']}")
        if e.get("description"):
            print(f"   {e['description']}")
    if not latest:
        print("No triggers registered yet for this workspace.")
    return 0


def _under_root(root: Optional[str], value: str) -> Path:
    path = Path(value).expanduser()
    return path if root is None or path.is_absolute() else Path(root).expanduser() / path


def cmd_check(args: argparse.Namespace) -> int:
    root = args.workspace_root
    ledger = _under_root(root, args.ledger)
    entries = _read_ledger(ledger)
    latest = _latest_per_trigger(entries)
    paths = {
        "gates": _under_root(root, args.gates_ledger), "outcomes": _under_root(root, args.outcomes_log),
        "redispatch": _under_root(root, args.redispatch_log),
        "sentinel_runs": _under_root(root, args.sentinel_runs),
        "alerts": Path(args.alerts_log) if args.alerts_log else None,
    }

    fired = []
    for tid, trigger in sorted(latest.items()):
        if trigger["event"] == "disabled":
            continue
        if trigger.get("kind") not in ("condition", "event"):
            continue  # cron/scheduled_prompt triggers are external -- nothing for this process to evaluate
        checker = CONDITION_CHECKERS.get(trigger.get("condition_kind")) or EVENT_CHECKERS.get(trigger.get("condition_kind"))
        if not checker:
            continue
        detail = checker(trigger, paths)
        if detail:
            fired.append((tid, trigger, detail))
            _append(ledger, {**trigger, "event": "fired", "timestamp": now(), "detail": detail})

    if not fired:
        print("Trigger check: nothing fired.")
        return 0

    print(f"Trigger check: {len(fired)} condition(s) fired —\n")
    for tid, trigger, detail in fired:
        print(f"  [{tid}] target={trigger.get('target')!r}")
        print(f"    {detail}")
    print("\nSurface these to the user (or route to the named target) — do not silently swallow a fired trigger. "
          "Run `acknowledge --trigger-id <id>` once handled so it doesn't re-fire identically next check.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ledger", help="Path to memory/triggers.jsonl (append-only).")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("register", help="Register a new trigger (cron/scheduled_prompt/condition/event).")
    r.add_argument("--trigger-id", required=True)
    r.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    r.add_argument("--condition-kind", default=None, choices=sorted(VALID_CONDITION_KINDS | VALID_EVENT_KINDS),
                    help="The specific condition (--kind condition) or event (--kind event) type.")
    r.add_argument("--params", default=None,
                    help="JSON object of condition/event-specific params. For --kind event: "
                         '{"current": "<real puller output path>", "snapshot": "<this trigger\'s cache path>", '
                         '"id_field": "ad_id", "watch_fields": ["campaign_name"]}')
    r.add_argument("--target", required=True, help="What fires -- a script path, an orchestrator id, or 'surface to user'")
    r.add_argument("--description", required=True)
    r.add_argument("--cadence", default=None, help="Crontab expression or 'daily'/'weekly' -- cron/scheduled_prompt only")

    d = sub.add_parser("disable", help="Disable a registered trigger.")
    d.add_argument("--trigger-id", required=True)

    a = sub.add_parser("acknowledge", help="Clear a fired condition trigger so it can fire again later.")
    a.add_argument("--trigger-id", required=True)

    l = sub.add_parser("list", help="List registered triggers.")
    l.add_argument("--kind", default=None, choices=sorted(VALID_KINDS))
    l.add_argument("--status", default=None, choices=["active", "disabled"])

    c = sub.add_parser("check", help="Evaluate every active condition-type trigger against real workspace state.")
    c.add_argument("--workspace-root", default=None,
                   help="Resolve the relative ledger and workspace state paths against this directory "
                        "(default: the current directory).")
    c.add_argument("--sentinel-runs", default="memory/sentinel_runs.jsonl",
                   help="Per-turn summaries written by Tantra's sentinel hooks.")
    c.add_argument("--gates-ledger", default="memory/approval_gates.jsonl")
    c.add_argument("--outcomes-log", default="memory/outcomes.jsonl")
    c.add_argument("--redispatch-log", default="memory/redispatch_log.jsonl")
    c.add_argument("--alerts-log", default="marketing-os-infra/05-competitor-monitoring/alerts.jsonl")

    return p


def main() -> int:
    args = build_parser().parse_args()
    handlers = {
        "register": cmd_register, "disable": cmd_disable, "acknowledge": cmd_acknowledge,
        "list": cmd_list, "check": cmd_check,
    }
    try:
        return handlers[args.command](args)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
