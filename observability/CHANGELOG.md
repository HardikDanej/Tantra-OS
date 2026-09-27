# Observability Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "Observability & Operations" gap identified
against the OS blueprint (`Marketing OS.md` §23): a real computed rollup
over the logs that already exist (`checkpoints.jsonl`, `evaluations.jsonl`,
`redispatch_log.jsonl`, `approval_gates.jsonl`, `outcomes.jsonl`,
`triggers.jsonl`), instead of those numbers existing only as raw lines.

- New: `.claude/lib/observability_report.py` — workflow/dispatch volume,
  output-quality pass rate (overall + per-agent), retry/escalation rate,
  human-approval rate (by stakes class), trigger fire/acknowledgment rate,
  and confidence calibration (reused from `calibration_tracker.py`, not
  reimplemented).
- Verified end-to-end against a labeled synthetic fixture
  (`examples/sample_workspace/`) — every number hand-checked against the
  fixture's actual contents before being trusted.
- 6 blueprint metrics (agent/model/tool latency, token/model/tool cost,
  KPI movement, agent/workflow ROI) explicitly marked not computable from
  any log this repo currently writes, each with the specific
  instrumentation that would need to exist first — not silently omitted.
