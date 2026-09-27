# Cost & Model Routing

The OS blueprint's Section 24 ("Cost & Model Routing") as two real,
working mechanisms, both scoped honestly to what's actually true about
this system:

1. **Model routing** — `.claude/lib/model_routing.py` + `model_routing.json`
2. **Tool usage / budget tracking** — `.claude/lib/tool_usage_ledger.py` + `budget_config.template.json`

## 1. Model routing — 12 overrides, not 237

Claude Code subagent frontmatter has a real, documented `model` field
(`haiku` / `sonnet` / `opus` / `fable` / a full model ID / `inherit`) that
genuinely changes which model a specific agent runs on — this isn't a
paper policy, it's the actual mechanism.

**Why only 12 of 238 agents get an explicit override**, not a blanket
per-tier assignment: this system's genuinely mechanical work already runs
as deterministic Python (`kb_slice.py`, `citation_guard.py`,
`output_evaluator.py`, and everything else in `.claude/lib/`), never as an
LLM call — so the blueprint's "use lightweight models for classification/
extraction" principle is already substantially satisfied by the existing
architecture, before this pass even started. Nearly every remaining LLM
dispatch in this repo is inherently a marketing judgment call (diagnose,
brief, recommend, weigh trade-offs) — downgrading the model for those is
a real quality risk, not a free cost saving, and would contradict this
repo's own "honest confidence, no shortcuts" discipline. So:

- **6 `haiku` overrides** — all Website Development Agent sub-agents whose
  real job is markup/structural **pattern detection**, not judgment:
  `broken-link-dead-page-scanning-subagent`, `mobile-responsive-behavior-subagent`,
  `tech-stack-fingerprinting-subagent`, `security-posture-auditing-subagent`,
  `accessibility-wcag-auditing-subagent`, `js-rendering-dynamic-verification-subagent`.
- **6 `opus` overrides** — the highest real legal/financial/regulatory
  exposure in this repository, or a genuinely cross-cutting adversarial/
  multi-system synthesis role: `investor-relations-earnings-release-subagent`,
  `labor-relations-union-workplace-comms-subagent`, `ma-due-diligence-intelligence-subagent`,
  `government-relations-public-policy-subagent`, `competitor-red-team-agent`,
  `cross-system-dispatch-bridge`.
- **The other 225** — no override, left to inherit the parent session's
  model. That's the documented Claude Code fallback, not a gap.

Every override's rationale quotes real language already in that agent's
own file (e.g. "the highest-stakes sub-agent in this entire roster") —
none of the 12 were picked by a generic rubric.

```bash
python .claude/lib/model_routing.py build       # regenerate model-routing/model_routing.json from the policy tables
python .claude/lib/model_routing.py apply        # write/update the model: line in each of the 12 real agent files
python .claude/lib/model_routing.py validate     # confirm every agent file matches the policy exactly, 0 drift
```

**Verified:** `apply` was run for real against this repo's 12 target
files (not a dry run) — each file's frontmatter now has a `model:` line,
confirmed by re-reading one file and by `model_routing.py validate`
reporting 0 mismatches. `taxonomy_registry.py build`/`validate` were
re-run afterward and still report 237/237 nodes, 0 unresolved — the
frontmatter edits didn't break anything the taxonomy layer depends on.

## 2. Tool usage & budget tracking — call volume, not fabricated dollars

**Deliberately NOT built:** a token/model-cost tracker for the Claude Code
side of this system. Confirmed while building the observability layer
(gap #3): no script in this repo has access to per-dispatch token counts
or model spend. Inventing a dollar figure there would be exactly the kind
of fabricated-precise number this repo's agents are built to refuse.

**What IS real and tracked:** calls to the paid/rate-limited external
connectors in `marketing-os-infra/lib/` (the Tool Registry from
`data-model/core_data_model.json`, gap #2). Every one of those is billed
as a platform subscription or a rate-limited free tier, not a metered
per-call charge — so **call volume**, not a fabricated per-call dollar
figure, is the number that actually matters operationally ("are we about
to blow through this month's request quota"). `cost_usd` stays optional
and null unless a real, cited figure is supplied — never guessed.

```bash
python .claude/lib/tool_usage_ledger.py --ledger memory/tool_usage_log.jsonl log --tool hubspot_connector --status ok
python .claude/lib/tool_usage_ledger.py --ledger memory/tool_usage_log.jsonl report --period-days 30
python .claude/lib/tool_usage_ledger.py --ledger memory/tool_usage_log.jsonl check-budget --config memory/budget_config.json
```

Copy `budget_config.template.json` to a real workspace's
`memory/budget_config.json` and fill in real `max_calls` ceilings (and
`max_cost_usd`, only if you have a real figure) for the connectors you
actually use — the template ships with `REPLACE_WITH_YOUR_LIMIT`
placeholders, the same convention `marketing-os-infra/*/config.json`
already uses for credentials.

**Verified end-to-end** against a synthetic ledger: 3 `hubspot_connector`
calls (1 logged as an error) + 5 `media_coverage_connector` calls with a
real `$0.00` cost figure. `report` correctly summed both. `check-budget`
against a deliberately low ceiling (`max_calls: 2` for `hubspot_connector`,
which had 3) correctly failed with exit code 1 and named the exact
overage, while `media_coverage_connector`'s separate, higher ceiling
correctly passed — proving the check discriminates per-tool rather than
failing or passing everything at once.

**Not yet wired:** no orchestrator or connector currently calls `log`
automatically — exactly like `approval_gate.py` and `redispatch_tracker.py`,
this is an explicit CLI an agent's own instructions would need to invoke
after a real connector call. Wiring that invocation into the relevant
agent `.md` files (revenue-crm-agent for `hubspot_connector`, the PR
system for `press_wire_connector`, etc.) is a natural next pass, kept
separate here so it can be reviewed on its own — same precedent as gap
#1's deferred orchestrator-wiring step.

## Versioning

`model_routing.json` carries `model_routing_version` (currently `1.0.0`).
Bump it and add a note here when an override is added, removed, or its
target tier changes — each change should cite the same kind of real,
specific evidence (a quoted line from the agent's own file, not a vibe)
the initial 12 did.
