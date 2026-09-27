"""
approval_gate.py
=================
Deterministic tracker for Human-In-The-Loop sign-off gates on high-stakes,
finalized plans (an annual/multi-quarter budget commitment, final creative
going to print/production/paid launch, a pricing change, a brand
reposition/relaunch). This is the formal version of what the Orchestrator's
Escalation rules already did implicitly ("surface to the user") -- it exists
because implicit escalation has no persisted state: nothing stops the same
plan from being silently re-presented as done, or a vague "looks good"
reply from being read as authorization for something the user never
actually looked at closely enough to approve.

This script does not decide what counts as high-stakes -- that's the
calling orchestrator's own classification (originally chief-marketing-
orchestrator.md, Step 4.6 -- now shared, one ledger, by all five top-level
orchestrators in this repository: chief-marketing-orchestrator, brand-
creative-orchestrator, product-marketing-gtm-orchestrator, market-research-
insights-orchestrator, and pr-corporate-communications-orchestrator -- plus
the cross-system-dispatch-bridge for a plan that spans more than one of
them). It only tracks the lifecycle of a gate once a calling orchestrator has
decided one is needed: pending -> approved | rejected | superseded, plus
staleness via `expires_note` (informational only -- staleness NEVER means
implicit approval; see `check`).

Data model, one JSON object per line in the ledger (append-only, one line
per lifecycle event -- a gate accumulates multiple lines over its life:
one `pending`, then exactly one terminal `approved`/`rejected`/`superseded`):

{
  "gate_id": "stable slug, e.g. annual_budget_fy27 or final_creative_launch_q1",
  "event": "pending | approved | rejected | superseded",
  "timestamp": "ISO-8601",
  "stakes_class": "annual_budget | final_creative | pricing_change | brand_relaunch | ad_platform_write | crm_write | product_launch_go | research_fielding_commitment | investor_disclosure | crisis_response_go | labor_relations_action | government_relations_action | cross_system_high_stakes | mcp_connection | mcp_write_connection | other_high_stakes",
  "binding": "optional, pending events only -- the exact configuration this approval is bound to (e.g. an MCP connector's config_hash from mcp_connector_registry.py); see binding_matches()",
  "summary": "one-line, what this plan actually is",
  "what_if_approved": "what happens / what becomes authorized once approved",
  "what_if_rejected": "what happens instead -- revert, revise, or drop",
  "red_team_verdict": "HOLDS | HOLDS WITH CHANGES | VULNERABLE | N/A",
  "irreversibility_note": "why this is expensive or hard to walk back",
  "checkpoint_ref": "timestamp of the synthesis checkpoint this gate belongs to",
  "note": "present on approved/rejected/superseded events -- the user's actual words or the reason superseded"
}

A companion file, `memory/latest.json`, keeps a `pending_approval_gates`
array of full gate objects (the most recent `pending` state for each gate
not yet resolved) so the Orchestrator can answer "what's still awaiting
sign-off" with a file read instead of re-scanning the whole ledger every
time. This script keeps both files in sync -- the calling agent never
hand-edits `pending_approval_gates` directly.

Why `--binding` exists (added with the MCP connector method): a plain gate
authorizes whatever the calling agent later says it meant. For a connector,
"approved" must mean "approved for exactly this server, transport, scope and
tool list" -- so the gate stores the connector's config hash on its pending
event, and binding_matches() only answers True when the gate is approved AND
the hash the caller holds now is the hash the user approved. Any change to the
connector's configuration produces a new hash and therefore needs a new gate.
Gates created without --binding behave exactly as before.

Stakes classes `mcp_connection` (read-only MCP connector) and
`mcp_write_connection` (an MCP connector with any tool that writes to a live
system) are opened by the tantra-connect skill via mcp_connector_registry.py.

Usage:
    python approval_gate.py <ledger.jsonl> create \
        --gate-id annual_budget_fy27 --stakes-class annual_budget \
        --summary "..." --what-if-approved "..." --what-if-rejected "..." \
        --red-team-verdict HOLDS --irreversibility-note "..." \
        --checkpoint-ref "2026-09-04T12:00:00Z" [--latest-json memory/latest.json] \
        [--binding <config_hash>]

    python approval_gate.py <ledger.jsonl> respond --gate-id annual_budget_fy27 \
        --decision approved --note "verbatim or paraphrased user reply" \
        [--latest-json memory/latest.json]

    python approval_gate.py <ledger.jsonl> list [--status pending]

    python approval_gate.py <ledger.jsonl> check --gate-id annual_budget_fy27

Exit codes:
    create:  0 always (unless arguments are invalid) -- creating a gate is
             never itself a failure condition.
    respond: 0 if the gate was pending and is now recorded as
             approved/rejected. 1 if the gate_id doesn't exist, or already
             has a terminal event -- the calling agent must not silently
             re-record a decision on an already-resolved gate; surface the
             conflict (e.g. "this was already approved on <date> -- are you
             re-confirming, or is this a new request?") instead of treating
             the second response as if it were the first.
    list:    0 always.
    check:   0 if the gate exists (any status). 1 if the gate_id is
             unknown -- the calling agent asked about a gate that was never
             created, which is itself worth surfacing rather than treating
             as "not yet approved."
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VALID_DECISIONS = {"approved", "rejected"}
TERMINAL_EVENTS = {"approved", "rejected", "superseded"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _append_ledger(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _latest_status(events: list[dict], gate_id: str) -> Optional[dict]:
    """Return the most recent event for gate_id, or None if it never existed."""
    matches = [e for e in events if e.get("gate_id") == gate_id]
    if not matches:
        return None
    return matches[-1]


def get_current_status(ledger_path: Path, gate_id: str) -> Optional[str]:
    """
    Public helper for OTHER scripts (not just this CLI) to check whether a
    gate is approved before doing something irreversible on its authority —
    e.g. ads_campaign_draft.py refuses to write to a live ad account unless
    this returns "approved" for the gate_id it was given. Returns None if
    the gate_id was never created; never guess "not yet approved" apart
    from "doesn't exist" the way `check`'s exit code does, since the two
    mean different things to a caller deciding whether to proceed.
    """
    events = _read_ledger(ledger_path)
    latest = _latest_status(events, gate_id)
    return latest["event"] if latest else None


def gate_state(ledger_path, gate_id: str) -> Optional[dict]:
    """
    Current lifecycle of one gate for callers that need more than the status:
    {"status", "stakes_class", "binding", "opened_at", "decided_at", "note"},
    taken from the gate's MOST RECENT pending event (a gate_id can be reused
    after a terminal event, and the older lifecycle must not leak into the new
    one). Returns None if the gate_id was never created.
    """
    events = [e for e in _read_ledger(Path(ledger_path)) if e.get("gate_id") == gate_id]
    if not events:
        return None
    pending = next((e for e in reversed(events) if e.get("event") == "pending"), {})
    latest = events[-1]
    return {
        "status": latest.get("event"),
        "stakes_class": pending.get("stakes_class"),
        "binding": pending.get("binding"),
        "opened_at": pending.get("timestamp"),
        "decided_at": latest.get("timestamp") if latest.get("event") in TERMINAL_EVENTS else None,
        "note": latest.get("note"),
    }


def binding_matches(ledger_path, gate_id: str, binding: str) -> bool:
    """
    True only when gate_id is currently `approved` AND the pending event the
    user approved carried exactly this binding. A missing ledger, unknown
    gate, unapproved gate, gate created without --binding, or any other
    binding is False -- the caller treats every one of those as "not
    authorized" and should use gate_state() to say which it was.
    """
    if not binding:
        return False
    try:
        state = gate_state(ledger_path, gate_id)
    except (OSError, ValueError):
        return False
    return bool(state and state["status"] == "approved" and state["binding"] == binding)


def _sync_latest_json(ledger_events: list[dict], latest_json_path: Optional[str]) -> None:
    if not latest_json_path:
        return
    path = Path(latest_json_path)
    latest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    # Recompute pending gates from the ledger's actual current state -- never
    # trust incremental patching here, the ledger is the source of truth.
    by_gate: dict[str, dict] = {}
    for e in ledger_events:
        by_gate.setdefault(e["gate_id"], []).append(e)

    pending = []
    for gate_id, evts in by_gate.items():
        last = evts[-1]
        if last["event"] == "pending":
            pending.append(last)

    latest["pending_approval_gates"] = pending
    path.write_text(json.dumps(latest, indent=2), encoding="utf-8")


def cmd_create(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    events = _read_ledger(ledger_path)

    existing = _latest_status(events, args.gate_id)
    if existing is not None and existing["event"] not in TERMINAL_EVENTS:
        # A gate with this id is already pending -- creating "again" would
        # silently duplicate it in pending_approval_gates. Refuse; the
        # calling agent should either respond to the existing one or choose
        # a distinct gate_id for a genuinely different plan.
        print(json.dumps({
            "error": f"gate_id '{args.gate_id}' already has a pending event from {existing['timestamp']} -- "
                     f"respond to it or supersede it explicitly before creating a new gate under the same id"
        }, indent=2), file=sys.stderr)
        return 1

    event = {
        "gate_id": args.gate_id,
        "event": "pending",
        "timestamp": _now_iso(),
        "stakes_class": args.stakes_class,
        "summary": args.summary,
        "what_if_approved": args.what_if_approved,
        "what_if_rejected": args.what_if_rejected,
        "red_team_verdict": args.red_team_verdict,
        "irreversibility_note": args.irreversibility_note,
        "checkpoint_ref": args.checkpoint_ref,
    }
    if args.binding:
        event["binding"] = args.binding
    _append_ledger(ledger_path, event)
    events.append(event)
    _sync_latest_json(events, args.latest_json)

    print(json.dumps({"created": event}, indent=2))
    return 0


def cmd_respond(args: argparse.Namespace) -> int:
    if args.decision not in VALID_DECISIONS:
        print(json.dumps({"error": f"--decision must be one of {sorted(VALID_DECISIONS)}"}, indent=2), file=sys.stderr)
        return 1

    ledger_path = Path(args.ledger)
    events = _read_ledger(ledger_path)
    existing = _latest_status(events, args.gate_id)

    if existing is None:
        print(json.dumps({"error": f"gate_id '{args.gate_id}' was never created -- nothing to respond to"}, indent=2), file=sys.stderr)
        return 1
    if existing["event"] in TERMINAL_EVENTS:
        print(json.dumps({
            "error": f"gate_id '{args.gate_id}' already has a terminal event ('{existing['event']}' at {existing['timestamp']}) -- "
                     f"do not silently re-record; surface this to the user as a re-confirmation or a new request",
            "existing_event": existing,
        }, indent=2), file=sys.stderr)
        return 1

    event = {
        "gate_id": args.gate_id,
        "event": args.decision,
        "timestamp": _now_iso(),
        "note": args.note or "",
    }
    _append_ledger(ledger_path, event)
    events.append(event)
    _sync_latest_json(events, args.latest_json)

    print(json.dumps({"recorded": event}, indent=2))
    return 0


def cmd_supersede(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    events = _read_ledger(ledger_path)
    existing = _latest_status(events, args.gate_id)

    if existing is None:
        print(json.dumps({"error": f"gate_id '{args.gate_id}' was never created"}, indent=2), file=sys.stderr)
        return 1
    if existing["event"] in TERMINAL_EVENTS:
        print(json.dumps({"error": f"gate_id '{args.gate_id}' is already terminal ('{existing['event']}') -- nothing to supersede"}, indent=2), file=sys.stderr)
        return 1

    event = {
        "gate_id": args.gate_id,
        "event": "superseded",
        "timestamp": _now_iso(),
        "note": args.note or "plan materially changed since this gate was opened -- a new gate is required",
    }
    _append_ledger(ledger_path, event)
    events.append(event)
    _sync_latest_json(events, args.latest_json)

    print(json.dumps({"recorded": event}, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    events = _read_ledger(ledger_path)

    by_gate: dict[str, list[dict]] = {}
    for e in events:
        by_gate.setdefault(e["gate_id"], []).append(e)

    rows = []
    for gate_id, evts in by_gate.items():
        last = evts[-1]
        rows.append(last)

    if args.status:
        rows = [r for r in rows if r["event"] == args.status]

    print(json.dumps({"gates": rows}, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    events = _read_ledger(ledger_path)
    matches = [e for e in events if e.get("gate_id") == args.gate_id]

    if not matches:
        print(json.dumps({"error": f"gate_id '{args.gate_id}' unknown -- never created, not just unapproved"}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps({"gate_id": args.gate_id, "history": matches, "current_status": matches[-1]["event"]}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic HITL approval-gate tracker for high-stakes finalized plans.")
    p.add_argument("ledger", help="Path to the approval_gates.jsonl ledger (append-only).")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create", help="Open a new pending approval gate.")
    c.add_argument("--gate-id", required=True, help="Stable slug -- reuse the same id if you mean the same plan, choose a new one for a genuinely different plan.")
    c.add_argument("--stakes-class", required=True, choices=[
        "annual_budget", "final_creative", "pricing_change", "brand_relaunch", "ad_platform_write", "crm_write",
        "product_launch_go", "research_fielding_commitment", "investor_disclosure", "crisis_response_go",
        "labor_relations_action", "government_relations_action", "cross_system_high_stakes",
        "mcp_connection", "mcp_write_connection", "other_high_stakes",
    ])
    c.add_argument("--summary", required=True)
    c.add_argument("--what-if-approved", required=True)
    c.add_argument("--what-if-rejected", required=True)
    c.add_argument("--red-team-verdict", required=True, choices=["HOLDS", "HOLDS WITH CHANGES", "VULNERABLE", "N/A"])
    c.add_argument("--irreversibility-note", required=True, help="Why this is expensive or hard to walk back -- the reason it needs a formal gate at all.")
    c.add_argument("--checkpoint-ref", default=None, help="Timestamp of the synthesis checkpoint this gate belongs to.")
    c.add_argument("--latest-json", default=None, help="Path to memory/latest.json -- if given, its pending_approval_gates array is kept in sync.")
    c.add_argument("--binding", default=None, help="Optional exact-configuration binding (e.g. an MCP connector's config_hash). Stored on the pending event; binding_matches() only accepts this exact value.")

    r = sub.add_parser("respond", help="Record approved/rejected against a pending gate.")
    r.add_argument("--gate-id", required=True)
    r.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS))
    r.add_argument("--note", default=None, help="The user's actual words or a faithful paraphrase -- not a restatement of the plan.")
    r.add_argument("--latest-json", default=None)

    s = sub.add_parser("supersede", help="Mark a pending gate superseded because the underlying plan materially changed before it was resolved.")
    s.add_argument("--gate-id", required=True)
    s.add_argument("--note", default=None)
    s.add_argument("--latest-json", default=None)

    l = sub.add_parser("list", help="List gates, optionally filtered by current status.")
    l.add_argument("--status", default=None, choices=["pending", "approved", "rejected", "superseded"])

    ck = sub.add_parser("check", help="Get the full history and current status of one gate.")
    ck.add_argument("--gate-id", required=True)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create":
        return cmd_create(args)
    elif args.command == "respond":
        return cmd_respond(args)
    elif args.command == "supersede":
        return cmd_supersede(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "check":
        return cmd_check(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
