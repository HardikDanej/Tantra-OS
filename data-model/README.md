# Core Data Model

The OS blueprint's Section 5 ("Core Data Model") as real, typed schemas
plus a queryable registry — the 17 objects (Organization, Brand,
Customer/Contact, Account, Product, Campaign, Audience, Content Asset,
Opportunity, Experiment, Agent, Workflow, Task, Tool, Event, Decision,
Learning), each mapped to whatever *actually already produces that shape*
in this repo today, instead of existing only as an ad hoc file convention
a human has to infer by reading five different agent files.

## How to read `core_data_model.json`

Each of the 17 objects has:
- `purpose` — the blueprint's own one-line definition (Section 5's table),
  reused verbatim since it's the source spec, not invented.
- `status` — `"active"` (a real script/file in this repo produces this
  shape today) or `"defined_not_yet_produced"` (a schema exists, grounded
  in the blueprint's stated purpose, but nothing in this framework writes
  one yet).
- `real_producer` — the actual file/script that writes this shape, or
  `null` if `status` is `defined_not_yet_produced`.
- `schema_class` — the Pydantic model name in `taxonomy_registry.py`'s
  sibling script, `.claude/lib/data_model_registry.py`, if one exists.

**13 of 17 are active, 4 are defined-not-yet-produced** (Account,
Product, Content Asset, Experiment) — see each entry's `show` output for
why. That split is the honest state of this repo, not a target to
immediately force to 17/17: Content Asset and Experiment in particular
are real gaps worth closing later (a workspace has no persisted log of
what's been drafted or what's been tested), but inventing a fake producer
for them today would be worse than naming the gap.

## Two things this deliberately reuses instead of duplicating

- **Agent** — not redefined here. `taxonomy/marketing_taxonomy.json`
  (built by `taxonomy_registry.py`, gap #1) already is the real, live
  Agent Registry: 237 nodes, id/name/definition/tools/parent/children.
  This file's `agent` entry is a pointer to it.
- **Event / Campaign performance** — not redefined here either.
  `marketing-os-infra/lib/tool_router.py`'s row schemas (`AdRow`, `GSCRow`,
  `SurveyResponseRow`, `ProductEventRow`, `MediaCoverageRow`,
  `SocialProfileSnapshotRow`) are imported and referenced by name, not
  re-declared — so the two files can never silently drift apart on what
  an ad-performance row actually contains.

## Tool Registry

`core_data_model.json`'s `tool_registry` array is the blueprint's Tool
object (§5) made real and complete: one entry per external-system
connector that actually exists in `marketing-os-infra/lib/`, each with its
real capability (`read_only` / `draft_write` / `scoped_write` /
`query_utility`), what gates it (an `approval_gate.py` stakes-class, a
`write_access_confirmed` config flag, or nothing), and whether it needs a
paid API key. This is the piece that didn't exist anywhere as structured
data before this pass — the connectors were real, but nothing catalogued
them together with their permissions/limits in one place.

## Using it

```bash
python .claude/lib/data_model_registry.py build                       # regenerate from the schemas in the script
python .claude/lib/data_model_registry.py list                          # all 17 objects + status, one line each
python .claude/lib/data_model_registry.py show <object_id>               # full detail + schema fields
python .claude/lib/data_model_registry.py validate <object_id> <file>     # validate a real file against its schema
```

`validate` gives this real teeth, not just documentation value — see
`examples/README.md` for a worked pass/fail demonstration against the
`Task` (dispatch contract) schema. Point it at a real workspace's
`memory/checkpoints.jsonl` (`decision`), `memory/outcomes.jsonl`
(`learning`), or `brand/company.json` (`organization`) to check a real
workspace's files conform to the shape every agent already assumes they
have.

## Versioning

Mirrors `taxonomy/`'s policy exactly: `data_model_version` in the JSON
(currently `1.0.0`), regenerated via `build`, never hand-edited. Bump the
version and add a `CHANGELOG.md` line when a schema's fields change, a
`defined_not_yet_produced` object gets a real producer for the first time,
or a new Tool Registry entry is added.
