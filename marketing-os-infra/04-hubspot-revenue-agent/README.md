# Workflow 04: HubSpot CRM Revenue Intelligence Agent

**Surfaces used:** Claude Chat (Projects + Skills) · Scheduling · HubSpot MCP · Slack MCP · Claude Code (weekly only) · Cowork
**Cadence:** Daily 8:30am pipeline digest + weekly Sunday historical trend analysis
**Setup time:** ~90 minutes first time, ~2 minutes/day thereafter
**Best for:** B2B sales orgs running HubSpot with 5–50 reps and $1M–$50M ARR

---

## What this workflow does

This is the most natively executable of the four workflows because both data systems have first-party Claude MCPs already.

1. **Every weekday at 8:30am:** A scheduled chat task fires. It uses the **HubSpot MCP** to pull live pipeline data, runs the 2-skill diagnostic pipeline (hubspot-crm-strategist + psychographic-profiler), drafts re-engagement messages for top stalled deals, and uses the **Slack MCP** to post the daily revenue intelligence digest to `#revenue-ops`. Reps wake up with their priorities.

2. **Every Sunday at 9pm:** Claude Code runs `hubspot_historical.py` on your local machine. It uses the HubSpot Private App token to pull 12+ months of historical deal data — things the daily MCP can't show in a single query: forecast accuracy by quarter, win rate trends by lead source, stage conversion drift, deal velocity decay. Output lands as `historical_trends.json` in the Project files.

3. **Monday morning's 8:30am digest** automatically incorporates the weekly historical trends into the diagnostic, surfacing structural pipeline issues that only show up over a multi-month lens.

4. **Cowork** manages `voice_samples.csv` — when a rep sends a re-engagement draft and gets a positive reply, they can log the win in a shared sheet, and Cowork syncs it back into Project files. The voice samples database grows weekly without manual curation.

---

## Architecture

```
       DAILY (Mon-Fri, 8:30am)                       WEEKLY (Sunday 9pm)
       ───────────────────────                       ─────────────────────

       Scheduled chat fires                          Claude Code (cron)
              │                                            │
              ▼                                            ▼
  ┌─────────────────────────┐                ┌─────────────────────────┐
  │  HubSpot MCP            │                │  hubspot_historical.py  │
  │  • pull live pipeline   │                │  • 12mo deal history    │
  │  • last 30d activity    │                │  • forecast accuracy    │
  │  • contact engagement   │                │  • stage conversion     │
  └────────┬────────────────┘                │  • win rate by source   │
           │                                 └─────────┬───────────────┘
           ▼                                           │
  ┌─────────────────────────┐                          ▼
  │  Skills:                │              ┌─────────────────────────┐
  │  • hubspot-crm-         │              │  historical_trends.json │
  │    strategist           │              │  (Project files)        │
  │  • psychographic-       │              └─────────┬───────────────┘
  │    profiler             │                        │
  └────────┬────────────────┘                        │
           │                                         │
           │  ◄────── reads weekly trends ───────────┘
           ▼
  ┌─────────────────────────┐
  │  Daily diagnostic +     │
  │  re-engagement drafts   │
  └────────┬────────────────┘
           │
           ▼ (Slack MCP)
  ┌─────────────────────────┐
  │  #revenue-ops digest    │
  │  Top 5 actions today    │
  └─────────────────────────┘

       FEEDBACK LOOP (continuous, via Cowork)
       ──────────────────────────────────────

  Rep sends draft → gets reply → logs to shared Google Sheet
                                          │
                                          ▼ (Cowork watches sheet)
                              ┌──────────────────────────┐
                              │  voice_samples.csv       │
                              │  (Project files updated) │
                              └──────────────────────────┘
                                          │
                                          ▼
                          Next day's drafts pattern-match
                          against the new winning sample
```

---

## Files in this workflow

| File | Purpose | Where it runs |
|------|---------|---------------|
| `hubspot_historical.py` | Weekly historical trend pull beyond MCP scope | Claude Code (your machine), Sunday 9pm |
| `hubspot_task_create.py` | Creates ONE HubSpot task or note from a spec — agentic-OS edition only, human-gated, task/note only (no sends, no workflow enrollment), see below | Claude Code (your machine), called only by the Chief Orchestrator after an approved HITL gate |
| `crm_writes_log.csv` | Append-only record of successful task/note creations | Written by `hubspot_task_create.py` |
| `icp_definition.md` | Documented ICP — required input for deal scoring | Project files (read by skills) |
| `voice_samples.csv` | Re-engagement voice training data | Project files (read by drafting step) |
| `system_prompt.md` | Project system prompt for revenue ops analyst role | Pasted into Project settings |
| `scheduled_prompt.md` | The daily 8:30am scheduled prompt | Pasted into Scheduling UI |

---

## Task/note creation (agentic-OS edition only, human-gated — read this before touching it)

Everything above is read-only. `hubspot_task_create.py` is different — it's the one script in this workflow that writes to a live CRM, and it exists only because that was explicitly scoped and signed off on as a narrow capability, not implied by anything above. It creates exactly one of two things, always inert until a human acts on it:
- **A task**, always `hs_task_status: NOT_STARTED` (hard-coded in `marketing-os-infra/lib/hubspot_connector.py` — not a setting).
- **A note**, a log entry on a contact/deal.

Neither can send anything, and this script deliberately does **not** support enrolling a contact in a HubSpot Workflow — unlike a task/note, an active workflow enrollment can trigger automated actions (including live email sends) outside this script's control the moment it happens, so there's no safe "draft" version of that to build here.

Two independent layers have to agree before anything is created:
1. **A Human-In-The-Loop approval gate for this exact action is `approved`.** The Chief Orchestrator opens a `stakes_class: crm_write` gate (`.claude/lib/approval_gate.py`) and presents it to you first — see `chief-marketing-orchestrator.md`, Step 4.6. The script re-checks the gate's live status itself.
2. **`HUBSPOT_WRITE_ACCESS_CONFIRMED=true` is set by hand** in `.env` — deliberately separate from `HUBSPOT_TOKEN` above. A second, distinct token variable, `HUBSPOT_WRITE_TOKEN`, holds the write-scoped credential, so the read-only token used for the weekly pull is never silently reused for writes.

Setup, once you've decided you actually want this:

In HubSpot: Settings → Integrations → Private Apps → Create a **separate** private app (don't reuse the read-only one above). Grant scopes:
- `crm.objects.tasks.write`, `crm.objects.tasks.read`
- `crm.objects.notes.write`, `crm.objects.notes.read`
- `crm.objects.contacts.read`, `crm.objects.deals.read` (needed to associate the task/note)

```bash
# ~/marketing-os/04-hubspot-revenue-agent/.env — add these alongside HUBSPOT_TOKEN
HUBSPOT_WRITE_TOKEN=pat-na1-xxxxxxxxxxxxxxxxxxxxx
HUBSPOT_WRITE_ACCESS_CONFIRMED=true
HUBSPOT_PORTAL_ID=12345678
```

Test the wiring without touching the live CRM:
```bash
python3 hubspot_task_create.py --spec drafts/example_spec.json --gate-id anything --dry-run
```
A successful real run creates a real task or note that a rep will see the next time they open the record — that's the deliverable, not a side effect to minimize.

---

## Why split MCP and Code

The HubSpot MCP is excellent at live, current-state queries: *"Show me deals over $50k in stages 3-5 with no activity in 14 days."* That's exactly what the daily digest needs.

The MCP is bad at historical trend analysis at scale. Asking it *"Show me forecast accuracy by rep across the last 6 quarters"* requires pulling and aggregating thousands of deal records across time — this is slow, hits rate limits, and the analytical heavy lifting doesn't belong in a chat session anyway.

So: **MCP for daily current state, Code for weekly historical aggregation, chat for synthesis of both.** The split reflects what each surface is genuinely good at, not what's theoretically possible.

---

## Setup (90 min, one time)

### 1. Documents you must produce first (60 min)

This workflow is a no-go without `icp_definition.md` and `voice_samples.csv` populated. The skills will refuse to run if these are missing or generic.

**`icp_definition.md`** — a real ICP, not a marketing template. The included file is a structured template; spend an hour with your VP Sales filling it in honestly. Specifically:
- What firmographic criteria predict success vs. churn?
- What technographic signals indicate buying readiness?
- What disqualifiers do you wish you'd caught earlier?

**`voice_samples.csv`** — 5–10 real re-engagement messages from your reps that previously got positive replies. Real voice, real outcomes. The skill pattern-matches against these to draft new messages in your team's voice.

If you skip this step, the daily digest will produce ICP scores that are statistical noise and re-engagement drafts that read as generic AI templates. The skills will still run, but the output won't be trustworthy.

### 2. HubSpot MCP authorization (5 min)

Settings → Connectors → HubSpot → Authorize. Read access is sufficient for this workflow's original scope (the daily digest and weekly historical pull) — no write permissions needed here. The OAuth flow walks you through scope selection. (A separate, optional write capability — task/note creation only, human-gated — exists in the agentic-OS edition; see the section below. It's not part of this MCP-based setup.)

Verify in HubSpot admin: an "Anthropic" application appears in connected apps with read access to Deals, Contacts, Companies, and Engagements.

### 3. Slack MCP authorization (5 min)

Settings → Connectors → Slack → Authorize. The bot needs permission to post in `#revenue-ops` (or whatever channel you designate). Make sure the channel exists before scheduling.

### 4. HubSpot Private App for the weekly script (10 min)

The weekly historical script doesn't go through the MCP — it uses HubSpot's REST API directly for bulk historical pulls.

In HubSpot: Settings → Integrations → Private Apps → Create private app. Name it "Marketing OS Historical Pull." Grant scopes:
- `crm.objects.deals.read`
- `crm.objects.contacts.read`
- `crm.objects.companies.read`
- `crm.schemas.deals.read`

Copy the access token. It goes into a local `.env` file (never committed to git):

```bash
# ~/marketing-os/04-hubspot-revenue-agent/.env
HUBSPOT_TOKEN=pat-na1-xxxxxxxxxxxxxxxxxxxxx
```

### 5. Claude Project setup (10 min)

- Create Project: "Revenue Intelligence Agent"
- Upload skills: `hubspot-crm-strategist.md`, `psychographic-profiler.md`
- Upload `icp_definition.md` and `voice_samples.csv` to Project files
- Paste `system_prompt.md` into Project custom instructions
- Verify HubSpot and Slack connectors are visible at the project level

### 6. Cron job for weekly historical pull (5 min)

```bash
crontab -e
```

Add:
```
0 21 * * 0 cd ~/marketing-os/04-hubspot-revenue-agent && /path/to/.venv/bin/python3 hubspot_historical.py >> output/cron.log 2>&1
```

Sunday 9pm runs the historical pull. Output writes to `historical_trends.json`. Cowork picks it up and syncs to Project files (or do it manually the first few times until you trust the cron).

### 7. Schedule the daily digest (5 min)

In Claude Chat:
- Open Revenue Intelligence Agent project
- Scheduling → New schedule
- **Cadence:** Daily at 08:30 (your timezone), Mon–Fri only
- **Prompt:** paste `scheduled_prompt.md` contents
- **Delivery:** new chat thread + Slack push (handled in prompt)

### 8. Smoke test before relying on it

Run the schedule manually once:
- Verify HubSpot data pulls successfully
- Verify ICP scores show variance (not all 3s)
- Verify Slack post lands in `#revenue-ops`
- Verify drafts reference specific deal context, not generic templates

If any of these fail, fix before relying on tomorrow morning's automated run.

---

## What you'll see at 8:30am each weekday

In `#revenue-ops`:

> 🎯 **Daily Revenue Intelligence — Mon Mar 4**
>
> **Pipeline:** $4.2M open, 3.4x coverage vs. Q2 target ($1.2M)
> **Status:** 12 stalled (>$1.4M), 4 ghosted in the last 14 days, 3 forecast risks
>
> **Top 5 actions today (ranked by revenue impact):**
> 1. Re-engage Acme Corp ($340k, stalled 18d) — Sarah K — DM has new role per LinkedIn
> 2. Forecast risk: Globex ($210k Q2 commit, velocity inconsistent) — David L — 1:1 today
> 3. ICP mismatch flagged: Initech ($180k) — score 2/5, recommend disqualify or downgrade — Sarah K
> 4. Drafts ready: 7 re-engagement messages for Stage 3 stalled — see thread
> 5. Source-mix risk: 78% of new pipeline this week from 1 channel — Marketing review
>
> **Weekly trend (from Sunday's pull):** Stage 3 → Stage 4 conversion dropped from 64% to 51% over Q1. Likely cause: pricing change in Feb. Worth investigating.
>
> Full digest + drafts: [link to chat thread]

The full chat thread has the diagnostic, ICP scoring table, and 5–10 ready-to-send re-engagement drafts (each rep grabs theirs).

---

## Refusal patterns (correct behavior)

The system will refuse to:
- Run without `icp_definition.md` in Project files (scores would be fabricated)
- Run pipeline diagnostics with under 30 active deals (sample too thin)
- Generate forecast predictions with under 10 deals at the relevant stage
- Flag a deal as "stalled" without checking activity logs (a deal with active engagement is not stalled, even if the stage hasn't moved)
- Draft re-engagement for deals where notes say "do not contact" or rep is handling personally
- Generate "all deals" re-engagement at scale (generic outreach damages brand)

Three days of refusals in a row usually means HubSpot data hygiene problems upstream — fix the CRM, the digest will follow.

---

## Troubleshooting

**Daily digest doesn't appear in Slack at 8:30am.**
→ Check the chat thread the schedule created. Most common cause: HubSpot MCP OAuth expired (re-auth at Settings → Connectors). Second most common: Slack connector lost permission to post in channel.

**ICP scores all cluster around 3.**
→ ICP doc is too vague. Tighten with specific firmographic + technographic thresholds. Real scoring shows variance — if everything is a 3, the system is hedging because it can't differentiate.

**Re-engagement drafts read generic.**
→ Voice samples are too thin or too uniform. Add 5–10 more varied samples (different reps, different objection types, different deal sizes).

**Sunday's `hubspot_historical.py` fails.**
→ Check `output/cron.log`. Usually the Private App token expired or scopes are insufficient. Regenerate, update `.env`, manual-run once.

**Daily digest flags the same 5 deals every day.**
→ Either reps aren't acting on recommendations (execution bottleneck, not workflow problem), or the recommendations are misfit. Audit by asking the next day's chat: "Why did these 5 deals not move yesterday despite being flagged?"

**Pipeline coverage looks healthy but bookings miss target.**
→ Pipeline is over-stuffed with low-fit deals. The high-amount/low-ICP table in the daily digest is your false-positive forecast — that's where bookings leak.

---

## Compounding value

By week 4 of running this daily, the system knows:
- Which reps consistently win which deal profiles (from Sunday's win rate analysis)
- Which lead sources actually convert (not just generate volume)
- Which ICP attributes are predictive vs. correlative
- Which voice patterns drive replies vs. silence

That feedback loop is what makes this workflow harder to outsource than the obvious daily cost displacement suggests. An external sales ops analyst can produce one excellent monthly report. This produces a calibrated daily one and improves on its own as the data layer thickens.
