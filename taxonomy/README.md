# Marketing Taxonomy

The OS blueprint's "Marketing Taxonomy Foundation" as a real, versioned,
queryable registry — not free text, not invented content.

## What this is

`marketing_taxonomy.json` classifies every one of this repo's 237
`.claude/agents/*.md` files into a 3-level tree:

```
Domain (7, from the blueprint)
  └── Subdomain (21 domain agents — the mid-tier orchestrators, e.g. ads-paid-media-agent)
        └── Discipline (210 specialist sub-agents, 10 per domain agent)
```

Plus a 4th bucket, `system_infra` (6 nodes: the 5 top-level orchestrators
and the cross-system-dispatch-bridge) — these route work, they don't own a
marketing discipline, so they sit outside the 7-domain tree by design.

The 7 domains are exactly the blueprint's Section 3 list:

| Key | Name |
|---|---|
| `strategy_management` | Marketing Strategy & Management |
| `brand_communications` | Brand & Communications |
| `digital_performance` | Digital & Performance Marketing |
| `content_social` | Content & Social Media Marketing |
| `customer_relationship` | Customer & Relationship Marketing |
| `product_growth_revenue` | Product, Growth & Revenue Marketing |
| `martech_data_ai` | Marketing Technology, Data & AI |

## How it was built (and why it's trustworthy)

Every field in every node is derived from data that already exists in this
repo — nothing here is invented to fill out a taxonomy shape:

- **id / name / definition / tools** — pulled directly from each agent
  file's own YAML frontmatter.
- **Sub-agent → domain-agent parent link** — extracted by regex from the
  sentence every sub-agent file already carries verbatim: *"Only accepts
  dispatches from the X Agent..."* This is not a guess; it's the same
  boundary sentence that governs real dispatch behavior, read back out of
  the file.
- **Domain-agent → 1-of-7-domain classification** — the one place human
  judgment enters. It's a single 21-entry table (`DOMAIN_MAP` in
  `.claude/lib/taxonomy_registry.py`), each entry checked against that
  domain agent's own stated real scope (its frontmatter description),
  not against a generic template.

**Deliberately NOT included:** per-node objectives, strategies, tactics,
or KPIs. The blueprint's Section 3 asks for these on every taxonomy node,
but writing them for 231 nodes would mean fabricating plausible-sounding
content for most of them — exactly the failure mode this repo's own
agents are built to refuse. A node's real objectives/KPIs come from the
relevant `knowledge-bases/*.md` file and the live dispatch contract at run
time (see `objective-kpi-framework-subagent`), never from a static
taxonomy entry pretending to already know them.

## Versioning

`marketing_taxonomy.json` carries a `taxonomy_version` field
(currently `1.0.0`) and is fully regenerable — it is not hand-edited.
Any change to an agent's frontmatter, a new agent file, or a `DOMAIN_MAP`/
alias-table edit in `taxonomy_registry.py` is picked up by re-running
`build`. See `CHANGELOG.md` for what changed at each version bump.

**When to bump the version:**
- New agent file added anywhere in `.claude/agents/` → re-run `build`,
  bump the patch version, add a `CHANGELOG.md` line.
- A domain agent's real scope changes enough that its `DOMAIN_MAP` entry
  is no longer accurate → edit the table, re-run `build`, bump the minor
  version, note the reclassification and why in `CHANGELOG.md`.
- The 7-domain list itself changes (adding an 8th domain, splitting one)
  → bump the major version — every consumer that hard-codes the 7 keys
  needs to be checked.

## Using it

```bash
python .claude/lib/taxonomy_registry.py build              # regenerate from current agent files
python .claude/lib/taxonomy_registry.py validate            # 0 unresolved / 0 orphans, or it says exactly what's wrong
python .claude/lib/taxonomy_registry.py outline             # the 7-domain tree with counts
python .claude/lib/taxonomy_registry.py node <agent-id>      # full detail on one node (definition, parent, children, tools)
python .claude/lib/taxonomy_registry.py search <term>        # substring search over id + definition
```

An orchestrator deciding which system/domain a novel or ambiguous request
belongs to can run `search` against the request's key terms to find the
real agent(s) that already own that ground, instead of guessing from the
request text alone. (Wiring that lookup into the 5 orchestrators'
DISPATCH steps is a natural next pass — not done in this build, kept
separate so it can be reviewed on its own.)

## Current shape (v1.0.0)

- 237 total agent files
- 7 domains, 21 subdomains (domain agents), 210 disciplines (sub-agents) — an exact 10-per-domain-agent split
- 6 system-infra nodes (5 orchestrators + the cross-system bridge)
- 0 out-of-scope-infra nodes today (the exclusion list exists for engineering/
  data-science/session-tooling agent types like `pea-*`/`dsi-*`/`Explore` —
  none of those happen to be defined as files inside this repo's own
  `.claude/agents/`, so the bucket is empty; it stays in the script so a
  future addition doesn't silently get misclassified as a marketing
  discipline)
- 0 unresolved parent links, 0 orphans (verified via `validate`)
