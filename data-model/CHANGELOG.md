# Core Data Model Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "Core Data Model" gap identified against the OS
blueprint (`Marketing OS.md` §5): the 17 named objects (Organization,
Brand, Customer/Contact, Account, Product, Campaign, Audience, Content
Asset, Opportunity, Experiment, Agent, Workflow, Task, Tool, Event,
Decision, Learning) as typed Pydantic schemas plus a queryable registry,
rather than each existing only as an informal file convention.

- 13/17 objects marked `active` (real producer already exists in this
  repo); 4/17 (`account`, `product`, `content_asset`, `experiment`) marked
  `defined_not_yet_produced` — schema exists, no script writes one yet.
- `agent` and `event`/`campaign`-performance are pointers to
  `taxonomy/marketing_taxonomy.json` and `tool_router.py`'s row schemas
  respectively, not re-declared.
- New Tool Registry: 9 real connector entries from
  `marketing-os-infra/lib/`, each with real capability/gating/paid-API
  status — the first time these were catalogued together as structured
  data rather than left as separate module docstrings.
- `validate` command tested end-to-end against synthetic fixtures
  (`examples/task.example.jsonl` passes 2/2, `examples/task.example.bad.jsonl`
  correctly fails both deliberately-broken lines) — a missing required
  field and an invalid enum value are both caught with the right exit code.
