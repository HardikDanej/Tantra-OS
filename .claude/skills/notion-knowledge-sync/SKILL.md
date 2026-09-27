---
name: notion-knowledge-sync
description: Activate when the user is architecting, cleaning up, or scaling a Notion workspace as a team knowledge base, marketing wiki, content hub, project workspace, or client-facing portal — including database design, page hierarchy, sync patterns between databases, permissions, templates, and integrations. Produces structures the team actually maintains, not aspirational architectures that decay in three months. Refuses to recommend the maximalist "everything in Notion" pattern that creates more problems than it solves. Treats Notion as a tool whose value compounds with discipline (one source of truth per concept, named conventions, archived clutter) and decays with neglect.
---

# Notion Knowledge Sync

The architect's deliverable is a workspace the team actually uses six months from now. Most Notion workspaces start ambitious and fail quietly: pages multiply, no one knows where the current version lives, search returns 14 stale results. The fix is fewer databases, clearer ownership, and rituals that keep the workspace alive.

## Core principle

**One source of truth per concept; everything else links to it.** If the same information lives in three pages, two of them are wrong. The architecture's job is to ensure each concept (a project, a client, a campaign, a piece of content, a process) has exactly one home, and everything that references it links there instead of duplicating.

## When to use

| Situation | Activate? |
|---|---|
| Setting up Notion for a growing team | Yes |
| Cleaning up a workspace that's become unmanageable | Yes |
| Migrating from another tool (Confluence, Coda, GDocs) | Yes |
| Designing client-facing portal | Yes |
| Building marketing content hub / editorial calendar | Yes |
| Building knowledge base for AI / RAG ingestion | Yes — schema matters more |
| Personal note-taking system | Reconsider — different problem |
| One-off "how do I make a database" question | No — too small |

## Workflow

### Step 1: Establish the workspace's job

Before designing structure, ask:

1. **Who uses this?** (Internal only / clients / public; team size)
2. **What decisions does it support?** (Project status / campaign tracking / content production / handbook reference)
3. **What's the team's discipline level?** (Will they archive? Will they tag? Will they fill required fields?)
4. **What integrates?** (Slack, calendar, Figma, Google Drive, GitHub, CRM)
5. **Does it feed AI / RAG?** (Different schema needs)
6. **Lifespan?** (Project workspace ≠ permanent handbook)

The answer to #3 is the most important. A team with low Notion discipline needs a simpler structure with stronger automation and fewer required fields. A team with high discipline can sustain richer schemas.

### Step 2: Identify the entities

What are the things in your workspace? Most teams have 5–10 core entities:

| Entity | Examples |
|---|---|
| Projects | Active engagements, deliverables |
| Clients | Customer accounts |
| People | Team members, contacts |
| Tasks | Action items |
| Documents | Drafts, deliverables, briefs |
| Meetings | Notes, decisions |
| Campaigns | Marketing efforts |
| Content | Articles, videos, posts |
| Resources | Links, files, references |
| Processes | SOPs, playbooks |

Each entity becomes (typically) one database. Relations between entities replace duplication.

### Step 3: Database schema

For each database, define:

**Properties to include**
- Title (always)
- Status (always — defines current state)
- Owner / assigned (who's accountable)
- Date(s) — created, due, published
- Type / category — short enum, not free text
- Relations to other databases — the load-bearing connectors
- Tags — sparingly; tag explosion is real

**Properties NOT to include** (default no, opt-in only)
- Sub-tags within tags (multi-level tagging gets unmaintainable)
- Properties that exist for a single page (those go in the page body, not the schema)
- "Notes" fields where any free-text would do — page body handles this
- Auto-calculated fields the team doesn't actually consume

**Status values**
- Force enum (not free text)
- 3–6 statuses max — every additional status is a transition the team has to think about
- Common: Backlog → Active → In Review → Done → Archived
- For content: Idea → Draft → Editing → Scheduled → Published → Archived

**Required fields**
- Mark fields required only when essential
- Required-creep kills adoption; pages get half-filled

### Step 4: Database views

Views are how the team interacts with the database. Default views per database:

- **Active** (default) — filtered to current items
- **By owner** — grouped by person, for accountability
- **Calendar** — for time-bound entities
- **Board** — for status-based workflow (kanban)
- **Archive** — done / cancelled, out of the way

For each view:
- Filter logic explicit
- Sort order purposeful
- Visible properties limited to the 4–7 the user actually scans

Avoid:
- 20 views per database — most aren't used; clutter
- Views that filter to one user only (private to one person, but sitting in shared db)
- Views without filters (showing everything is signal of unstructured database)

### Step 5: Page templates

For pages within a database, templates lock structure. Examples:

**Project page template**
```
- Status / Owner / Dates (database properties)
- ## Goals (heading + bullets)
- ## Scope
- ## Stakeholders
- ## Decisions log (datestamped)
- ## Open questions
- ## Tasks (linked task database, filtered to this project)
- ## Documents (linked document database)
```

**Meeting note template**
```
- Date / Attendees / Topic (properties)
- ## Agenda
- ## Discussion (free-form)
- ## Decisions
- ## Action items (synced to task database)
```

**Content piece template**
```
- Title / Status / Author / Channel / Publish date (properties)
- ## Brief / Why this piece
- ## Outline
- ## Draft
- ## Notes / Feedback
- ## Final
```

Templates make consistent structure cheap and missing structure visible.

### Step 6: Sync patterns

Notion's relational model means the same data can be expressed in multiple places without duplication. Use it.

**Linked databases**
- One database, multiple views in different contexts
- E.g., Tasks database linked into project pages (filtered to project), into person pages (filtered to assignee), into a "this week" view

**Synced blocks**
- Same content rendered in multiple pages, edited in any
- For shared sections (announcements, current sprint goals)

**Relations + rollups**
- Relate Tasks to Projects; rollup task counts and statuses up to the project
- Relate Content to Campaigns; rollup performance metrics

**Avoid**
- Copy-pasting page content between pages (drift starts immediately)
- Manually maintaining cross-references (link, don't list)

### Step 7: Permissions and sharing

For each section of the workspace:
- **Workspace-shared**: everyone in the workspace (default for team handbook, processes, public projects)
- **Group-shared**: specific teams (sales, marketing, engineering)
- **Private to user**: personal scratchpad
- **Guest-shared**: external clients with limited access (usually full read on specific pages, comment access)

Watch out for:
- Inheritance surprises: parent page permissions cascade unless overridden
- Guest counts: guests cost separately on most plans
- Public web pages: explicit, conscious decision; not the default

### Step 8: Integrations

**Workspace-level**
- Slack: page mentions, status updates → channel posts
- Google Calendar: meeting pages auto-created from calendar events
- GitHub: PRs / issues mirrored to project pages
- Figma: embedded designs in project / brief pages

**For marketing teams specifically**
- Calendar database → social scheduling tools (via Zapier / Make / Buffer)
- Editorial calendar → publishing workflows
- Form responses (Tally / Typeform) → CRM-adjacent database in Notion

**For AI / RAG**
- Notion is decent as a content source for RAG when schema is clean
- Use the official Notion API / connector
- Keep machine-readable structure (consistent property names, clean status enums)
- Avoid heavy formatting that loses semantics in extraction (tables of nested toggles)

### Step 9: Maintenance rituals

Without rituals, workspaces decay:

- **Weekly**: archive completed projects, kill empty pages, check status accuracy
- **Monthly**: cull templates that aren't used, retire databases that haven't been written to in 90 days, audit access for departed teammates
- **Quarterly**: review schema — are there properties no one fills? Statuses no one uses? Relations no one queries? Cull.
- **Annually**: full architecture review — is the workspace serving the team or accumulating debt?

Build the rituals into the team's calendar; otherwise they don't happen.

## Output format

```
# Notion Workspace Design — [Team / Project] — [Date]

## Workspace job
- Users: [internal / external]
- Discipline level: [low / medium / high — drives complexity]
- Lifespan: [permanent / project / temporary]

## Top-level structure
- [Section A] — [purpose, who has access]
- [Section B] — ...

## Databases
| Database | Purpose | Key properties | Relations |
|---|---|---|---|

## Per-database details
### [Database name]
- Properties: [list with types and rationale]
- Status enum: [values]
- Default views: [list]
- Templates: [list]
- Required fields: [list, justified]

## Sync / relation map
- [Diagram or list of cross-database relations]

## Page hierarchy
- [Top-level pages and their nesting]

## Permissions
- [Per section]

## Integrations
- [Per integration: scope, direction, gotchas]

## Templates provided
- [Page templates with body structure]

## Maintenance rituals
- Weekly: [list]
- Monthly: [list]
- Quarterly: [list]
- Annually: [list]
```

## Anti-patterns

1. ❌ Database for every entity even when count is small (database with 4 entries is just a page list)
2. ❌ Multi-level nesting beyond 3 levels — users don't drill that deep
3. ❌ 20 properties per database — most blank; cull aggressively
4. ❌ Free-text status fields — drift, no view filters work properly
5. ❌ Ten different views nobody uses except the original creator
6. ❌ Same information in three places — pick one home, link from others
7. ❌ Workspace-wide tags that mean different things in different databases — namespace tags by db
8. ❌ Required fields the team can't fill at moment of creation — friction kills entry
9. ❌ Templates that nobody uses because they're too rigid or too long — observe + iterate
10. ❌ Permissions as afterthought — guest accidentally seeing private project, or team member missing edit access
11. ❌ "Master database" containing every entity ever — performance + cognitive load
12. ❌ Heavy use of toggles for content the team needs to scan — collapsed by default = invisible
13. ❌ Notion as primary task tracker for engineering teams — usually wrong tool; engineering ticketing should be in Linear / Jira
14. ❌ Notion as CRM — workable for very small teams; breaks at scale; recommend HubSpot / etc. when it's outgrown
15. ❌ Migrating wholesale from another tool without re-thinking schema — porting bad structure makes new tool feel bad
16. ❌ No archive strategy — done items pile up, search degrades, performance suffers
17. ❌ Sync to AI / RAG without auditing what's in there — confidential / outdated content flows into model contexts

## Confidence calibration

- Schema and structure recommendations: high
- Whether team will adopt the structure: medium — depends on culture more than design
- Notion-specific feature behavior: medium — Notion ships changes monthly; verify feature availability when building
- AI / RAG quality from Notion content: medium — schema discipline matters more than tool choice
- Workspace longevity without maintenance: low — decay is the default
