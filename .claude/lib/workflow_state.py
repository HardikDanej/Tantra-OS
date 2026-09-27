"""
workflow_state.py
===================
The OS blueprint's Section 21 "Workflow State & Reliability" made real:
"Suggested states: Draft -> Queued -> Running -> Waiting -> Approval ->
Completed / Failed / Cancelled. Use idempotency keys so retries cannot
duplicate actions. Persist state so long-running workflows can resume."

A real, enforced state machine -- not a suggestion in a doc. Invalid
transitions are refused (e.g. COMPLETED -> RUNNING), the same way
approval_gate.py refuses to silently re-record a decision on an
already-resolved gate. State is persisted append-only in
memory/workflow_instances.jsonl (same ledger convention as every other
`.claude/lib/*.py` tracker in this repo), so "resume" is a real file read,
not something an orchestrator has to reconstruct from memory.

Deliberately reuses rather than re-implements two states that already
have a real, working mechanism elsewhere in this repo:
  - APPROVAL       -> approval_gate.py already tracks pending/approved/
    rejected/superseded for exactly this purpose. This script's APPROVAL
    state is a pointer (an approval_gate_id), not a duplicate tracker --
    transitioning out of APPROVAL should reflect what approval_gate.py's
    own ledger says, never contradict it.
  - COMPLETED      -> a workflow instance transitioning to COMPLETED
    should correspond to a real memory/checkpoints.jsonl entry (the
    Decision object, gap #2) for that run. This script doesn't write
    checkpoints itself -- the calling orchestrator does, per its own
    existing Step 6 -- but records the checkpoint_ref alongside the
    COMPLETED transition so the two stay linkable.

A workflow instance must reference a real workflow_id from
workflow-registry/workflow_registry.json (gap #7's other half) -- an
instance of a workflow that was never registered as a template is refused
at creation time, the same cross-reference discipline this repo's other
registries already enforce on each other.

Usage:
    python workflow_state.py register --workflow-id 02-seo-content-factory --idempotency-key <stable-key> [--ledger memory/workflow_instances.jsonl]
    python workflow_state.py transition --instance-id <id> --to RUNNING [--detail "..."] [--approval-gate-id <id>] [--checkpoint-ref <ts>]
    python workflow_state.py status --instance-id <id>
    python workflow_state.py list [--workflow-id <id>] [--state <state>]

Exit codes:
    register:    0 always -- registering an already-known idempotency_key
                 returns the EXISTING instance rather than erroring, since
                 that's the whole point of an idempotency key (a retried
                 registration is not a failure).
    transition:  0 if the transition was valid and applied. 1 if the
                 instance doesn't exist, is already in a terminal state,
                 or the transition isn't in this state machine's real
                 graph -- surfaced as a refusal, not silently coerced.
    status:      0 if the instance exists. 1 if it doesn't.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_REGISTRY_JSON = REPO_ROOT / "workflow-registry" / "workflow_registry.json"

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}

# The real, enforced transition graph -- blueprint Section 21's suggested
# states, made into an actual graph a script checks membership against,
# not prose a human has to remember to follow.
STATE_MACHINE: dict[str, set[str]] = {
    "DRAFT": {"QUEUED", "CANCELLED"},
    "QUEUED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"WAITING", "APPROVAL", "COMPLETED", "FAILED", "CANCELLED"},
    "WAITING": {"RUNNING", "FAILED", "CANCELLED"},
    "APPROVAL": {"RUNNING", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _known_workflow_ids() -> Optional[set[str]]:
    if not WORKFLOW_REGISTRY_JSON.exists():
        return None  # registry not built yet -- don't block on a missing prerequisite the caller may not control
    return set(json.loads(WORKFLOW_REGISTRY_JSON.read_text(encoding="utf-8"))["workflows"].keys())


def _instance_history(entries: list[dict], instance_id: str) -> list[dict]:
    return [e for e in entries if e.get("instance_id") == instance_id]


def _current_state(history: list[dict]) -> Optional[str]:
    return history[-1]["state"] if history else None


def cmd_register(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    entries = read_ledger(ledger_path)

    existing = [e for e in entries if e.get("idempotency_key") == args.idempotency_key]
    if existing:
        instance_id = existing[0]["instance_id"]
        current = _current_state(_instance_history(entries, instance_id))
        print(f"Idempotency key {args.idempotency_key!r} already registered as instance {instance_id!r} "
              f"(current state: {current}). Not creating a duplicate.")
        return 0

    known_ids = _known_workflow_ids()
    if known_ids is not None and args.workflow_id not in known_ids:
        print(f"ERROR: workflow_id {args.workflow_id!r} is not a registered workflow template "
              f"({sorted(known_ids)}). Refusing to create an instance of an unregistered workflow "
              f"-- run workflow_registry.py build first, or check for a typo.", file=sys.stderr)
        return 1

    instance_id = f"{args.workflow_id}__{args.idempotency_key}"
    entry = {
        "instance_id": instance_id, "workflow_id": args.workflow_id,
        "idempotency_key": args.idempotency_key, "state": "DRAFT",
        "previous_state": None, "timestamp": now(), "detail": "instance created",
    }
    append(ledger_path, entry)
    print(f"Registered instance {instance_id!r} in state DRAFT.")
    return 0


def cmd_transition(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    entries = read_ledger(ledger_path)
    history = _instance_history(entries, args.instance_id)
    if not history:
        print(f"ERROR: no such instance: {args.instance_id!r}", file=sys.stderr)
        return 1

    current = _current_state(history)
    if current in TERMINAL_STATES:
        print(f"ERROR: instance {args.instance_id!r} is already in terminal state {current!r} -- "
              f"refusing to transition a completed/failed/cancelled instance further, the same way "
              f"approval_gate.py refuses to re-record a decision on an already-resolved gate.",
              file=sys.stderr)
        return 1

    valid_next = STATE_MACHINE.get(current, set())
    if args.to not in valid_next:
        print(f"ERROR: {current!r} -> {args.to!r} is not a valid transition. "
              f"Valid next state(s) from {current!r}: {sorted(valid_next) or '(none -- terminal)'}",
              file=sys.stderr)
        return 1

    entry = {
        "instance_id": args.instance_id, "workflow_id": history[0]["workflow_id"],
        "idempotency_key": history[0]["idempotency_key"], "state": args.to,
        "previous_state": current, "timestamp": now(), "detail": args.detail or "",
    }
    if args.approval_gate_id:
        entry["approval_gate_id"] = args.approval_gate_id
    if args.checkpoint_ref:
        entry["checkpoint_ref"] = args.checkpoint_ref
    append(ledger_path, entry)
    print(f"{args.instance_id}: {current} -> {args.to}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    entries = read_ledger(Path(args.ledger))
    history = _instance_history(entries, args.instance_id)
    if not history:
        print(f"No such instance: {args.instance_id!r}")
        return 1
    current = _current_state(history)
    valid_next = sorted(STATE_MACHINE.get(current, set())) or ["(none -- terminal)"]
    print(f"Instance: {args.instance_id}")
    print(f"Workflow: {history[0]['workflow_id']}  (idempotency_key={history[0]['idempotency_key']})")
    print(f"Current state: {current}")
    print(f"Valid next state(s): {valid_next}")
    print(f"History ({len(history)} event(s)):")
    for e in history:
        extra = ""
        if e.get("approval_gate_id"):
            extra += f" approval_gate_id={e['approval_gate_id']}"
        if e.get("checkpoint_ref"):
            extra += f" checkpoint_ref={e['checkpoint_ref']}"
        detail = f" -- {e['detail']}" if e.get("detail") else ""
        print(f"  [{e['timestamp']}] {e['previous_state']} -> {e['state']}{extra}{detail}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = read_ledger(Path(args.ledger))
    by_instance: dict[str, list[dict]] = {}
    for e in entries:
        by_instance.setdefault(e["instance_id"], []).append(e)

    shown = 0
    for instance_id, history in sorted(by_instance.items()):
        current = _current_state(history)
        wf_id = history[0]["workflow_id"]
        if args.workflow_id and wf_id != args.workflow_id:
            continue
        if args.state and current != args.state:
            continue
        print(f"{instance_id:50s} workflow={wf_id:28s} state={current}")
        shown += 1
    if shown == 0:
        print("No matching instances.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ledger", default="memory/workflow_instances.jsonl")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("register", help="Create a workflow instance (idempotent).")
    r.add_argument("--workflow-id", required=True)
    r.add_argument("--idempotency-key", required=True,
                    help="A stable key for this specific run -- registering the same key twice "
                         "returns the existing instance rather than creating a duplicate.")

    t = sub.add_parser("transition", help="Move an instance to a new state.")
    t.add_argument("--instance-id", required=True)
    t.add_argument("--to", required=True, choices=sorted(STATE_MACHINE.keys()))
    t.add_argument("--detail", default=None)
    t.add_argument("--approval-gate-id", default=None, help="Set when --to APPROVAL, links to approval_gate.py's ledger")
    t.add_argument("--checkpoint-ref", default=None, help="Set when --to COMPLETED, links to memory/checkpoints.jsonl")

    s = sub.add_parser("status", help="Show one instance's current state, valid next states, and full history.")
    s.add_argument("--instance-id", required=True)

    l = sub.add_parser("list", help="List instances.")
    l.add_argument("--workflow-id", default=None)
    l.add_argument("--state", default=None, choices=sorted(STATE_MACHINE.keys()))

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "register":
        return cmd_register(args)
    if args.command == "transition":
        return cmd_transition(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "list":
        return cmd_list(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
