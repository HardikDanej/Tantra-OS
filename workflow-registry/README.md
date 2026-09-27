# Workflow Registry & State Machine

The OS blueprint's Section 29 ("Master Workflow Record") and Section 21
("Workflow State & Reliability") made real, as two deliberately separate
halves: a **template catalog** (what a workflow IS) and a **state
machine** (what state one RUN of it is currently in).

## Part A — Workflow Registry (the template catalog)

`.claude/lib/workflow_registry.py` catalogs this repo's 4 real workflows,
populated from what each `workflows/*/orchestration.md` file already
says — real trigger cadence, real agent involvement, real gatekeeper
checks — not invented template text.

**Reuses, doesn't duplicate:**
- Agent identity → `taxonomy/marketing_taxonomy.json` (gap #1). Every
  `primary_agents` entry is cross-checked against it at build time — a
  typo or a renamed agent fails the build loudly instead of silently
  drifting.
- Workflow file version → `version-manifest/manifest.json`'s
  `workflow_versions` (gap #5) — read directly, not recomputed.
- Tool permissions → `data-model/core_data_model.json`'s `tool_registry`
  (gap #2).

**Deliberately excluded:** Confidence, Outcome, Cost, Evidence, Learning
— blueprint §29 lists these on the same table, but they vary *per run*,
not per template. They already have a real home:
`memory/checkpoints.jsonl` (Decision) and `memory/outcomes.jsonl`
(Learning), both from gap #2. Stuffing per-run fields into a template
registry would misrepresent one specific past run's numbers as if they
described the workflow in general.

```bash
python .claude/lib/workflow_registry.py build       # regenerate workflow-registry/workflow_registry.json
python .claude/lib/workflow_registry.py validate     # confirm every named agent is real, every version resolves
python .claude/lib/workflow_registry.py show 02-seo-content-factory
```

**Verified:** `build` cross-referenced all 4 workflows' agent lists
against the real 237-node taxonomy and all 4 content versions against the
real version manifest — 0 problems on the first run.

## Part B — Workflow instance state machine

`.claude/lib/workflow_state.py` implements blueprint §21's suggested
states as a **real, enforced graph** — not prose a human has to remember
to follow:

```
DRAFT -> QUEUED -> RUNNING -> {WAITING, APPROVAL} -> RUNNING -> COMPLETED
  |         |          |                                          |
  v         v          v                                          v
CANCELLED CANCELLED  FAILED/CANCELLED                    (COMPLETED/FAILED/CANCELLED are terminal)
```

- **Idempotency keys, for real**: registering the same
  `--idempotency-key` twice returns the *existing* instance rather than
  creating a duplicate — verified directly, not just asserted.
- **Persisted, resumable state**: every transition is an append-only line
  in `memory/workflow_instances.jsonl` (same ledger convention as
  `approval_gate.py`/`redispatch_tracker.py`). `status --instance-id`
  reads the full history back and states the current state plus every
  *valid* next state — that's what makes "a long-running workflow can
  resume" a real file read instead of something an orchestrator has to
  reconstruct from memory.
- **Invalid transitions are refused, not coerced**: `DRAFT -> RUNNING`
  (skipping `QUEUED`) and any transition out of a terminal state
  (`COMPLETED -> RUNNING`) both fail with exit code 1 and a clear reason
  — verified directly, mirroring `approval_gate.py`'s own refusal to
  silently re-record a decision on an already-resolved gate.
- **Cross-registry enforcement**: registering an instance against a
  `workflow_id` that isn't in `workflow-registry/workflow_registry.json`
  is refused — verified directly against a fake workflow id.
- **Links to the two states that already have a real mechanism
  elsewhere**, rather than re-tracking them: an `APPROVAL` transition
  carries an `--approval-gate-id` pointing at `approval_gate.py`'s own
  ledger; a `COMPLETED` transition carries a `--checkpoint-ref` pointing
  at the real `memory/checkpoints.jsonl` entry for that run.

```bash
python .claude/lib/workflow_state.py register --workflow-id 02-seo-content-factory --idempotency-key run_2026-09-08
python .claude/lib/workflow_state.py transition --instance-id 02-seo-content-factory__run_2026-09-08 --to QUEUED
python .claude/lib/workflow_state.py status --instance-id 02-seo-content-factory__run_2026-09-08
python .claude/lib/workflow_state.py list
```

**Verified end-to-end** (see `examples/README.md` for the full
reproducible trace): a complete happy path through every state including
a real `APPROVAL` detour, a complete failure path, and three real refusal
cases (duplicate idempotency key, unregistered workflow id, an invalid
state skip, and a transition attempted out of a terminal state) — all
confirmed with the actual exit codes and error text, not just described.

## Not yet wired

Neither script is currently called automatically by any of the 5
orchestrators — same precedent as every other gap's deferred-wiring step
(gaps #1, #4, #5, #6). An orchestrator's own Step 5/6 dispatch logic would
need to call `workflow_state.py register`/`transition` around a real
dispatch to make a workflow's lifecycle state actually tracked during a
live run, rather than only reconstructable after the fact from
`memory/checkpoints.jsonl`.

## Versioning

`workflow_registry.json` carries `workflow_registry_version` (currently
`1.0.0`). Bump it when a workflow's real trigger cadence, agent
involvement, or approval policy changes enough that the hand-curated
`WORKFLOW_TEMPLATES` table in `workflow_registry.py` needs an edit — the
same discipline every other registry in this repo already follows.
