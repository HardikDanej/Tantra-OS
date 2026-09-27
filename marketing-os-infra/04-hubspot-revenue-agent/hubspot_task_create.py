"""
hubspot_task_create.py
========================
Creates ONE HubSpot task or note from a spec, but ONLY if a specific
Human-In-The-Loop approval_gate.py gate for this exact action is recorded
as "approved". This is the one script in this workflow that writes to a
live CRM — the original workflow design was read-only ("no write
permissions needed"); see marketing-os-infra/lib/hubspot_connector.py's
module docstring for the full reasoning on scope (task/note only — no
sends, no workflow enrollment, no property writes) and why that's the
actual safe analog to a CMS draft or PAUSED ad campaign here.

**This script is Orchestrator-invoked only.** The Revenue/CRM Agent itself
never calls this — its own definition (.claude/agents/revenue-crm-agent.md)
states "never accept a dispatch that would modify CRM data" as an
absolute, and that stays true and unchanged. The Revenue/CRM Agent
produces a re-engagement targeting spec (which deal, which contact, what
to reference, what objection); the Chief Marketing Orchestrator opens a
Step 4.6 HITL approval gate (`stakes_class: crm_write`) on the specific
plan to create tasks/notes from that spec, presents it to the user, waits
for an unambiguous approval, and only then calls this script.

Two independent layers have to agree before anything is created:
1. **Gate approved.** Same mechanism as ads_campaign_draft.py — checked
   here via `approval_gate.get_current_status`, not assumed from the
   caller's say-so.
2. **Write access explicitly confirmed.** `HUBSPOT_WRITE_ACCESS_CONFIRMED`
   must be `"true"` in `.env` — a separate opt-in from `HUBSPOT_TOKEN`
   (the read-only puller's credential), using a distinct
   `HUBSPOT_WRITE_TOKEN` so a broader-scoped token never gets used for
   writes just because it happens to also carry write scope.

There's no PAUSED-style third layer here the way ads_connector.py has a
budget ceiling — a task/note has no dial like that to cap. The action
itself is already the ceiling: it's an inert to-do or log entry, not
something that can spend money or send anything on its own.

Spec JSON shape:
    {
      "action_type": "task",  // or "note"
      "subject": "Follow up with Jane re: pricing objection",  // task only
      "body": "Last touch was the pricing call on 3/12. Reference the ROI calc she asked for.",
      "contact_id": "12345", "deal_id": "67890",  // at least one required
      "owner_id": "999",  // task only, optional — who it's assigned to
      "due_date_iso": "2026-09-08T09:00:00Z"  // task only, optional
    }

Usage:
    python3 hubspot_task_create.py --spec spec.json \\
        --gate-id crm_write_stalled_deals_batch1 --dry-run

    python3 hubspot_task_create.py --spec spec.json \\
        --gate-id crm_write_stalled_deals_batch1 \\
        --gates-ledger memory/approval_gates.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude" / "lib"))
from hubspot_connector import CrmWriteResult, create_crm_write  # noqa: E402
from approval_gate import get_current_status  # noqa: E402

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
WRITES_LOG_PATH = ROOT / "crm_writes_log.csv"
LOG_FIELDS = ["created_at", "gate_id", "action_type", "status", "object_id", "portal_url", "contact_id", "deal_id", "spec_path"]

REQUIRED_SPEC_FIELDS = {
    "task": ["subject", "body"],
    "note": ["body"],
}


class SpecError(Exception):
    pass


def load_write_config() -> dict[str, Any]:
    """
    Loads the write-scoped HubSpot credential from .env, same manual-parse
    convention hubspot_historical.py already uses (no external dependency).
    Deliberately separate variable names from the read-only puller's
    HUBSPOT_TOKEN — see module docstring.
    """
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    return {
        "access_token": os.environ.get("HUBSPOT_WRITE_TOKEN", "REPLACE_WITH_HUBSPOT_WRITE_SCOPED_PRIVATE_APP_TOKEN"),
        "write_access_confirmed": os.environ.get("HUBSPOT_WRITE_ACCESS_CONFIRMED", "false").lower() == "true",
        "portal_id": os.environ.get("HUBSPOT_PORTAL_ID", ""),
    }


def load_spec(path: Path, action_type: str) -> dict[str, Any]:
    if not path.exists():
        raise SpecError(f"spec file not found: {path}")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpecError(f"spec is not valid JSON: {e}") from e
    if not isinstance(spec, dict):
        raise SpecError("spec must be a JSON object")

    missing = [f for f in REQUIRED_SPEC_FIELDS[action_type] if not spec.get(f)]
    if missing:
        raise SpecError(f"spec is missing required field(s) for {action_type}: {', '.join(missing)}")
    if not spec.get("contact_id") and not spec.get("deal_id"):
        raise SpecError("spec must include at least one of contact_id/deal_id")
    return spec


def append_writes_log(row: dict[str, Any]) -> None:
    is_new = not WRITES_LOG_PATH.exists()
    with open(WRITES_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--action-type", choices=["task", "note"], default="task")
    parser.add_argument("--spec", required=True, type=Path, help="Path to the spec JSON file")
    parser.add_argument("--gate-id", required=True,
                         help="The approval_gate.py gate_id for this exact action. Must be 'approved' "
                              "in the ledger, unless --dry-run.")
    parser.add_argument("--gates-ledger", type=Path, default=Path("memory/approval_gates.jsonl"),
                         help="Path to the approval_gates.jsonl ledger (default: memory/approval_gates.jsonl "
                              "relative to cwd — the workspace root, same convention as approval_gate.py itself)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Validate config + spec + gate status; do not call the HubSpot API")
    args = parser.parse_args()

    config = load_write_config()

    try:
        spec = load_spec(args.spec, args.action_type)
    except SpecError as e:
        sys.exit(f"FATAL: could not load spec {args.spec}: {e}")

    print(f"\n{'='*60}")
    print(f"HubSpot {args.action_type} creation")
    print(f"{'='*60}")
    print(f"Contact/Deal:  {spec.get('contact_id', '(none)')} / {spec.get('deal_id', '(none)')}")
    print(f"Body:          {spec['body'][:80]}")
    print(f"Gate:          {args.gate_id}")

    gate_status = get_current_status(args.gates_ledger, args.gate_id) if args.gates_ledger.exists() else None
    print(f"Gate status:   {gate_status or '(not found)'}")

    if not args.dry_run and gate_status != "approved":
        sys.exit(
            f"FATAL: gate {args.gate_id!r} is {gate_status or 'UNKNOWN (never created)'}, not 'approved'. "
            f"Refusing to write to a live CRM without an approved Human-In-The-Loop gate. "
            f"This is not a permissions bug to work around — open or resolve the gate via "
            f"approval_gate.py first (see chief-marketing-orchestrator.md, Step 4.6)."
        )

    if not config["write_access_confirmed"] and not args.dry_run:
        sys.exit(
            "FATAL: HUBSPOT_WRITE_ACCESS_CONFIRMED is not 'true' in .env. This is a separate, "
            "explicit opt-in from the read-only puller's HUBSPOT_TOKEN — set it only once a "
            "real write-scoped token (HUBSPOT_WRITE_TOKEN) is actually in place."
        )

    if args.dry_run:
        print("\n--dry-run: config + spec + gate-status checked, no API call made.")
        print(f"Would create a {args.action_type} in HubSpot "
              f"(gate would need to be 'approved' and HUBSPOT_WRITE_ACCESS_CONFIRMED=true for a real run).")
        return

    result: CrmWriteResult = create_crm_write(
        args.action_type, config,
        body=spec["body"],
        contact_id=spec.get("contact_id"),
        deal_id=spec.get("deal_id"),
        **({"subject": spec["subject"], "owner_id": spec.get("owner_id"), "due_date_iso": spec.get("due_date_iso")}
           if args.action_type == "task" else {}),
    )

    if result.ok():
        append_writes_log({
            "created_at": result.attempted_at,
            "gate_id": args.gate_id,
            "action_type": result.action_type,
            "status": result.status,
            "object_id": result.object_id or "",
            "portal_url": result.portal_url or "",
            "contact_id": spec.get("contact_id", ""),
            "deal_id": spec.get("deal_id", ""),
            "spec_path": str(args.spec),
        })
        print(f"\nOK: {args.action_type} created in HubSpot.")
        print(f"  object_id:  {result.object_id}")
        print(f"  portal_url: {result.portal_url}")
        print(f"\nLogged to {WRITES_LOG_PATH}")
    else:
        print(f"\nERROR: {args.action_type} NOT fully created in HubSpot.")
        print(f"  reason: {result.error.reason}")
        print(f"  detail: {result.error.detail}")
        if result.object_id:
            print(f"  NOTE: the {args.action_type} itself (id={result.object_id}) WAS created — only "
                  f"its association failed. Check the portal; it may need manual association.")
        sys.exit(1)


if __name__ == "__main__":
    main()
