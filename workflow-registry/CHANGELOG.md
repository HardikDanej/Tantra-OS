# Workflow Registry & State Machine Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "Formal Workflow Registry / state machine" gap
identified against the OS blueprint (`Marketing OS.md` §21 Workflow State
& Reliability, §29 Master Workflow Record).

**Workflow Registry:**
- New: `.claude/lib/workflow_registry.py`. Catalogs all 4 real workflows
  from `workflows/*/orchestration.md`'s own real text (trigger cadence,
  agent involvement, gatekeeper checks). Cross-references
  `taxonomy/marketing_taxonomy.json` (agents) and
  `version-manifest/manifest.json` (content version) rather than
  duplicating either. 0 build problems on first run — all agent
  references and version lookups resolved cleanly.
- Confidence/Outcome/Cost/Evidence/Learning deliberately excluded from
  the template registry — those are per-run fields already tracked in
  `memory/checkpoints.jsonl`/`memory/outcomes.jsonl` (gap #2).

**Workflow instance state machine:**
- New: `.claude/lib/workflow_state.py`. A real, enforced state graph
  (`DRAFT -> QUEUED -> RUNNING -> {WAITING, APPROVAL} -> COMPLETED /
  FAILED / CANCELLED`) persisted to `memory/workflow_instances.jsonl`.
- Verified end-to-end: a full happy-path lifecycle including a real
  `APPROVAL` detour linked to a synthetic `approval_gate_id`, and a
  failure path. Verified refusals: a duplicate idempotency key returns
  the existing instance rather than duplicating it; an unregistered
  `workflow_id` is refused at registration; an invalid state skip
  (`DRAFT -> RUNNING`) and a transition attempted out of a terminal state
  (`COMPLETED -> RUNNING`) are both refused with exit code 1 and a clear
  reason.
- Links `APPROVAL` and `COMPLETED` transitions to `approval_gate.py`'s
  ledger and `memory/checkpoints.jsonl` respectively via optional
  `--approval-gate-id`/`--checkpoint-ref` fields, rather than
  re-implementing either mechanism.
- Not yet wired into any of the 5 orchestrators' actual dispatch logic —
  a named, separate follow-on, same precedent as gaps #1, #4, #5, #6.
