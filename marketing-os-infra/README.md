# Marketing OS — Multi-Surface Orchestration (v2 — canonical)

> This is the current, canonical edition. If you'd rather not set up local scripts, API credentials, and cron jobs, every workflow here also runs manually: hand the agents a CSV export instead of a scheduled pull (see `SETUP.md`, Tier 1).

Four production marketing workflows, each architected across four Claude surfaces: **Claude Code**, **Claude Chat (Projects + Skills + Connectors)**, **Cowork**, and **Scheduling**. Each surface does what it's actually best at, instead of forcing one to do everything. (A fifth, `05-competitor-monitoring/`, was added later for continuous unattended monitoring specifically — it doesn't follow this same four-surface spine, since its whole point is running without Cowork/connector involvement; see that workflow's own README.)

**Paid-API adoption decisions** (SERP APIs, scraping-as-a-service, social/ad intelligence) are recorded separately in [`PAID_API_DECISIONS.md`](PAID_API_DECISIONS.md) — none of the workflows below require a paid third-party key to run as documented.

This is a master-level upgrade of the original four workflows. The earlier version ran inside a chat window with manual CSV uploads. This version runs *itself* — data pulls happen on your machine via Claude Code, files move via Cowork, analysis runs on a schedule, and output is pushed to Slack/WordPress/HubSpot before you sit down at your desk.

---

## The four-surface architecture

| Surface | Role | What it's good at | What it's bad at |
|---------|------|-------------------|------------------|
| **Claude Code** | The engineer | Long-running scripts, API authentication, multi-file ops, CRON scheduling, anything that requires a terminal | Conversational decision-making; doesn't have your skills loaded |
| **Claude Chat + Projects** | The strategist | Skill-based analysis, multi-turn reasoning, connector-mediated actions (Slack/HubSpot/WordPress posting) | Heavy data preprocessing; rate-limited for huge file ops |
| **Cowork** | The operator | Watching folders, moving files between Code outputs and Project inputs, low-friction human checkpoints | Anything requiring intelligence or judgment |
| **Scheduling** | The timekeeper | Running recurring prompts without human kickoff; pushing output via connectors | One-off work; ad-hoc analysis |

The pattern: **Code pulls → Cowork moves → Schedule runs → Connector pushes.** Each workflow follows this spine; the differences are in skills, data sources, and output destinations.

---

## Workflow inventory

### 01 — Campaign Intelligence
Weekly pipeline that audits paid media performance across Meta, Google, and TikTok. **Claude Code** runs the API pulls Sunday night. **Cowork** lands the unified CSV in your Project. **Scheduling** kicks off the diagnostic at 8am Monday. Output lands in **Slack** before standup.

### 02 — SEO Content Factory
Daily pipeline that mines keyword gaps, drafts an article, audits E-E-A-T, scrubs AI cadence, and publishes to WordPress. **Claude Code** pulls Search Console data nightly. **Scheduling** picks the next topic at 6am. **WordPress connector** publishes the draft. By 9am, you have a draft article ready to review.

### 03 — Brand Launch Suite
One-time multi-stage engagement to build a brand foundation. **Claude Code** ingests and normalizes brand assets (PDFs, transcripts, web copy). **Chat + skills** runs the six-stage strategy workflow. **Cowork** manages stage-gate approvals. Output is a brand playbook plus structured JSON files that the other three workflows consume as upstream input.

### 04 — HubSpot Revenue Agent
Daily pipeline intelligence delivered to Slack at 8:30am. **HubSpot MCP** pulls live data. **Skills** diagnose pipeline health and draft re-engagement. **Slack MCP** posts the digest. **Claude Code** runs a weekly historical pull on Sundays for trend analysis the live data can't show.

---

## Deterministic tool routing (`lib/tool_router.py`)

Every puller in this repo (`ad_data_pull.py`, `gsc_keyword_pull.py`, `asset_ingestion.py`, `hubspot_historical.py`) hits an external API per platform/account. The old pattern was `try/except: continue` — a failed pull just vanished, and the output CSV looked identical whether a platform had a quiet week or its credentials expired. A downstream agent reading that CSV has no way to tell the difference, and will confidently report on data that was never actually fetched.

`lib/tool_router.py` is the shared fix, wired into all four pullers:

- **`PullResult`** — every pull function returns one of these instead of a bare DataFrame/list. Status is always `ok` / `partial` / `error`, computed from what actually happened, never asserted by the caller.
- **`AdRow` / `GSCRow`** (Pydantic) — output rows are validated before being written. A row that fails validation is dropped and counted in `validation_errors`, never silently included half-typed.
- **`SourceError`** — a typed per-item failure record (used directly for asset-ingestion file failures and HubSpot per-deal history lookups, since those aren't row-shaped pulls).
- **`write_source_manifest()`** — writes `<output>.sources.json` next to the output file: per-source status, row counts, and the exact error for anything that failed. **Any agent consuming a puller's output must read this manifest before treating the file as complete** — a file that exists is not the same claim as a file that's complete.
- **`assert_not_silently_empty()`** — if every enabled source failed, the script raises instead of writing an empty-looking-legitimate output.

Where each script uses it:

| Script | What's wrapped | Manifest |
|---|---|---|
| `01-campaign-intelligence/ad_data_pull.py` | Meta/Google/TikTok pulls, per-account | `weekly_unified.csv.sources.json` |
| `02-seo-content-factory/gsc_keyword_pull.py` | Current + prior-period GSC pulls; refuses to update the queue if the current period failed | `topic_queue.csv.sources.json`, plus `rising_query_detection_active` in `topic_queue.meta.json` |
| `03-brand-launch-suite/asset_ingestion.py` | Per-file extraction failures, missing-dependency extractors, empty/tiny-content skips | `brand_inputs.errors.json` |
| `04-hubspot-revenue-agent/hubspot_historical.py` | Pipelines pull, closed-deals pull (refuses to write if either fails), per-deal stage-history lookups | `historical_trends.json.sources.json` |

The consuming domain agents (SEO, Marketing Strategist, Revenue/CRM, Ads/Paid-Media) are instructed to check the relevant manifest before treating their input file as trustworthy — see each agent's `.claude/agents/*.md`.

---

## How the workflows compose

Workflow 03 (Brand Launch) produces three structured outputs that the other workflows consume:

```
03-brand-launch-suite/outputs/
├── personas.json         → consumed by 01 (audience refresh) and 02 (article persona targeting)
├── voice_system.json     → consumed by 01 (creative briefs) and 02 (article voice)
└── icp_definition.md     → consumed by 04 (deal qualification scoring)
```

Run 03 first if you don't already have a brand foundation. Run 01, 02, and 04 in any order — they're independent once the brand foundation exists.

---

## Setup prerequisites

### Claude account
- **Pro** or **Max** subscription
- Projects, Skills, Connectors, Code Interpreter all included

### Local machine (for Claude Code)
- macOS or Linux (Windows via WSL works)
- Node.js 18+ (for Claude Code CLI)
- Python 3.10+ (for the data pull scripts)
- A folder structure you commit to (the scripts assume `~/marketing-os/`)
- Cron access (or Windows Task Scheduler equivalent) for unattended runs

### Cowork (beta)
- Desktop app installed
- Folder watching configured per workflow (each workflow's README specifies)

### Connectors to enable in Claude
- HubSpot (Workflow 04)
- Slack (Workflows 01 and 04)
- WordPress.com (Workflow 02)
- Google Drive (optional — Workflows 02 and 03 benefit)

### API credentials you'll need to gather
- Meta Marketing API access token (Workflow 01)
- Google Ads Developer Token + OAuth (Workflow 01)
- TikTok Marketing API access token (Workflow 01)
- Google Search Console OAuth (Workflow 02)
- HubSpot Private App token (Workflow 04 — only for the historical script; the MCP handles daily access)

Each workflow's `config.json` shows exactly where credentials go. Never commit real credentials to git.

---

## Repository structure

```
marketing-os/
├── README.md (this file)
├── 01-campaign-intelligence/
│   ├── README.md                  → architecture + setup
│   ├── ad_data_pull.py            → Claude Code: weekly multi-platform API pull
│   ├── config.json                → API credentials and account IDs (template)
│   ├── accounts.csv               → which ad accounts to pull each week
│   ├── system_prompt.md           → Project system prompt
│   └── scheduled_prompt.md        → the prompt the scheduler runs Mondays 8am
│
├── 02-seo-content-factory/
│   ├── README.md
│   ├── gsc_keyword_pull.py        → Claude Code: nightly Search Console pull
│   ├── topic_queue.csv            → prioritized keyword backlog
│   ├── eeat_evidence.json         → reusable citation library
│   ├── system_prompt.md
│   └── scheduled_prompt.md        → daily 6am article production
│
├── 03-brand-launch-suite/
│   ├── README.md
│   ├── asset_ingestion.py         → Claude Code: normalize brand assets folder
│   ├── input_schema.json          → schema for normalized brand inputs
│   ├── system_prompt.md
│   └── stage_orchestration.md     → six-stage prompt sequence
│
└── 04-hubspot-revenue-agent/
    ├── README.md
    ├── hubspot_historical.py      → Claude Code: weekly trend analysis pull
    ├── icp_definition.md          → ICP template (you fill this in)
    ├── voice_samples.csv          → re-engagement voice training data
    ├── system_prompt.md
    └── scheduled_prompt.md        → daily 8:30am pipeline digest
```

---

## Operating cadence (combined)

A typical week running all four workflows:

| Day | Time | Surface | Workflow | What happens |
|-----|------|---------|----------|--------------|
| Sun | 11pm | Claude Code (cron) | 01 | Ad data pulled from Meta/Google/TikTok APIs into local CSVs |
| Sun | 11:30pm | Cowork | 01 | Watches folder, moves CSVs to Project files |
| Sun | 11:45pm | Claude Code (cron) | 04 | Weekly HubSpot historical pull for trend analysis |
| Mon | 6am | Scheduled chat | 02 | Daily article production runs against topic queue |
| Mon | 8am | Scheduled chat | 01 | Weekly campaign intelligence diagnostic runs, posts to Slack |
| Mon | 8:30am | Scheduled chat | 04 | Daily revenue intelligence digest posts to Slack |
| Mon | 9am | You | All | Standup; team has digests waiting |
| Daily | 6am | Scheduled chat | 02 | Article production continues |
| Daily | 8:30am | Scheduled chat | 04 | Pipeline digest |
| Daily | 11pm | Claude Code (cron) | 02 | GSC keyword pull updates topic queue |

You sit down to work at 9am Monday with: weekly ad audit done, today's article drafted and ready for E-E-A-T review, pipeline digest in Slack with top 5 actions ranked. That's the goal.

---

## A note on the trade-offs

This architecture is materially more powerful than the chat-only version, but it carries costs:

1. **Setup is real.** Plan a day to wire everything up the first time. API credentials, OAuth flows, cron jobs, connector authorizations — they all need to work before any of it runs unattended.

2. **Failures fail silently.** When a cron job breaks at 11pm Sunday, you find out at 8:30am Monday when the digest doesn't show up. Each workflow's README has a monitoring section for this reason.

3. **Cowork is beta.** Folder watching works but expect occasional friction. The workflows are designed to fail safe — if Cowork misses a file, the next scheduled chat run will say "no new data" rather than analyze stale data.

4. **The scheduled chat tasks consume rate limits.** A daily article run on Pro is fine; running all four workflows daily on Pro will eventually hit limits. Plan for Max if you're committing to all four daily.

If you're running just one or two of these, you don't need the full architecture. Start with one workflow, get it stable, add the next.

---

## Where to start

**If you're a marketer with a small team:** Start with Workflow 04 (HubSpot Revenue Agent). It uses native MCPs only, no Claude Code setup needed for the daily run, and it produces value the next morning. Add Workflow 02 once 04 is stable.

**If you're a growth lead at an ecommerce brand:** Start with Workflow 01 (Campaign Intelligence). The weekly cadence is forgiving for first-time setup, and the output replaces the most expensive line item (paid media agency).

**If you're launching or relaunching a brand:** Start with Workflow 03 (Brand Launch Suite). Run it once, then plug its outputs into 01, 02, and 04.

**If you're a content team:** Start with Workflow 02 (SEO Content Factory). It's the most self-contained and produces visible output (published articles) faster than any of the others.

Each workflow's README has a "first run" section that walks you through the very first execution end-to-end before automating it.
