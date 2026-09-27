# Observability & Operations

The OS blueprint's Section 23 ("Observability & Operations") as a real
computed rollup — `.claude/lib/observability_report.py` — instead of
workflow success rate, escalation frequency, and human-approval rate
living only as raw `.jsonl` lines a human reads one at a time.

## Why this doesn't have a committed data file like `taxonomy/` and `data-model/`

Those two are about *this framework repo's own* 238 agents and 17 core
objects — there's one true answer, so it's generated once and committed.
Observability is different: every number here is **per-workspace** (each
client's own `memory/*.jsonl` history), and this framework repo itself
never holds a live workspace — a workspace is always a separate directory
the framework is linked into, per `INSTALL.md`. So there's nothing
framework-level to commit — the deliverable
is the script itself, proven correct against a labeled synthetic fixture
in `examples/`.

## What it computes, and from what

| Metric | Real source |
|---|---|
| Workflow run volume, dispatch volume by agent, dispatch-kind mix | `memory/checkpoints.jsonl` |
| Output quality (proxy for "workflow success/failure rate" + "agent reliability") | `memory/evaluations.jsonl` (`output_evaluator.py`'s own PASS/PASS_WITH_FLAGS/FAIL verdicts) |
| Retry frequency, escalation frequency | `memory/redispatch_log.jsonl` (`redispatch_tracker.py`) |
| Human approval rate, by stakes class | `memory/approval_gates.jsonl` (`approval_gate.py`) |
| Trigger fire frequency, dangling unacknowledged fires | `memory/triggers.jsonl` (`trigger_registry.py`) |
| Confidence vs. actual outcome | `memory/outcomes.jsonl` + `memory/checkpoints.jsonl`, via `calibration_tracker.py`'s real `compute_calibration()` — **imported and reused, not reimplemented** |

## What it honestly can't compute yet

Six blueprint metrics have no real source anywhere in this repo today —
agent/model/tool **latency**, token/model/tool **cost**, **KPI movement**
after an intervention, and **agent/workflow ROI**. Every report includes a
`not_computable` list naming each one, why it can't be computed, and
exactly what instrumentation would need to exist first. This mirrors the
`data-model/` gap's `defined_not_yet_produced` status — named plainly
rather than faked with a placeholder number or silently dropped.

## Using it

```bash
python .claude/lib/observability_report.py report --workspace <path-to-a-real-workspace>
python .claude/lib/observability_report.py report --workspace . --json-out memory/observability_report.json
```

Run from (or point `--workspace` at) any real company workspace directory
that has a `memory/` folder — the same directory `new_workspace.py`
scaffolds and every orchestrator already reads/writes.

## Verified against a labeled synthetic fixture

`examples/sample_workspace/memory/*.jsonl` is synthetic test data (4
checkpoints, 4 evaluations, 2 redispatch cycles — one escalated, one
resolved — 3 approval gates in three different terminal states, 2
outcomes, 2 triggers), **not real business history**. `expected_report.json`
is this script's real output against it, hand-verified line by line:
4 workflow runs, 0.75 overall output-quality pass rate, one escalated
retry cycle out of two (escalation_rate 0.5), one pending approval gate
out of three (approval_rate_of_decided 0.5 on the two decided), one
dangling unacknowledged trigger fire out of two. Re-run the command below
against the fixture any time this script changes, to confirm the numbers
still match:

```bash
python .claude/lib/observability_report.py report --workspace observability/examples/sample_workspace
```
