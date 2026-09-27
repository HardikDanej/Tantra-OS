Synthetic test ledger for `workflow_state.py` — not a real client's
workflow history. `workflow_instances.example.jsonl` contains two real
lifecycle paths, both hand-verified:

- `02-seo-content-factory__run_2026-09-08` — the full happy path,
  including a real APPROVAL detour (`DRAFT -> QUEUED -> RUNNING ->
  APPROVAL -> RUNNING -> COMPLETED`), linked to a synthetic
  `approval_gate_id` and `checkpoint_ref`.
- `01-campaign-intelligence__run_2026-09-08-monday` — a failure path
  (`DRAFT -> QUEUED -> RUNNING -> FAILED`), simulating a stale-data
  gatekeeper refusal.

Also verified but NOT in this ledger (they were refused before anything
was written, which is the correct behavior): registering the same
idempotency key twice does not create a duplicate instance; registering
against an unregistered `workflow_id` is refused; transitioning
`COMPLETED -> RUNNING` and `DRAFT -> RUNNING` (skipping `QUEUED`) are both
refused with exit code 1.

Reproduce:
```bash
python .claude/lib/workflow_state.py --ledger workflow-registry/examples/workflow_instances.example.jsonl status --instance-id 02-seo-content-factory__run_2026-09-08
python .claude/lib/workflow_state.py --ledger workflow-registry/examples/workflow_instances.example.jsonl list
```
