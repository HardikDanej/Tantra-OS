# Cost & Model Routing Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "Cost & Model Routing" gap identified against
the OS blueprint (`Marketing OS.md` §24).

**Model routing:**
- Verified first (via the `claude-code-guide` agent, not assumed) that
  Claude Code subagent frontmatter supports a real `model` field with
  documented fallback behavior (unset -> inherit parent session's model).
- New: `.claude/lib/model_routing.py`. Applied 12 real overrides across
  237 agent files — 6 `haiku` (Website Development Agent's markup/
  pattern-detection sub-agents), 6 `opus` (highest legal/financial/
  regulatory exposure + cross-cutting adversarial/multi-system synthesis
  roles). Every override cites specific language already in that agent's
  own file.
- Verified: `apply` run for real, `validate` reports 0 mismatches,
  `taxonomy_registry.py` re-run clean (237/237, 0 unresolved) after the
  frontmatter edits.

**Tool usage / budget tracking:**
- New: `.claude/lib/tool_usage_ledger.py` + `budget_config.template.json`.
  Tracks call volume (and, only when a real figure is supplied, dollar
  cost) for the paid/rate-limited connectors in `marketing-os-infra/lib/`.
- Deliberately did NOT build a token/model-cost tracker for the Claude
  Code side — no script in this repo has access to that data (confirmed
  during gap #3's observability build); a fabricated number would be
  worse than none.
- Verified end-to-end against a synthetic ledger: `report` correctly
  summed calls/errors/cost per tool; `check-budget` against a
  deliberately low ceiling correctly failed with exit 1 and named the
  exact overage, while a separate tool's higher ceiling correctly passed.
- Not yet wired into any orchestrator/connector call site — a named,
  separate follow-on, same precedent as gap #1's deferred taxonomy-search
  wiring.
