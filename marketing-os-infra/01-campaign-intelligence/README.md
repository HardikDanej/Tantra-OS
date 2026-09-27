# Workflow 01: Full-Funnel Campaign Intelligence

**Surfaces used:** Claude Code · Cowork · Claude Chat (Projects + Skills) · Scheduling · Slack MCP
**Cadence:** Weekly (Sunday night data pull → Monday 8am report)
**Setup time:** ~3 hours first time, ~5 minutes/week thereafter
**Best for:** Brands spending $50k+/month on paid acquisition

---

## What this workflow does

1. **Sunday 11pm:** Claude Code runs `ad_data_pull.py` on your local machine via cron. It hits the Meta Marketing API, Google Ads API, and TikTok Marketing API for the last 14 days of ad-level performance data, normalizes everything into a unified schema, and writes a single CSV to `~/marketing-os/01-campaign-intelligence/output/weekly_unified.csv`.

2. **Sunday 11:30pm:** Cowork is configured to watch that output folder. When the CSV appears, Cowork moves it into the Claude Project files for "Campaign Intelligence."

3. **Monday 8am:** A scheduled chat task fires. Claude reads the CSV, runs the 5-skill diagnostic pipeline (creative-fatigue-radar → claude-ads-auditor → psychographic-profiler → viral-hook-generator + brand-voice-extractor), and assembles the weekly intelligence report.

4. **Monday 8:15am:** The scheduled task uses the Slack connector to post the executive summary to `#growth-weekly` and DMs the full report to whoever owns the channel.

5. **You** sit down at 9am with the weekly audit done, creative briefs queued, and the prioritized action list waiting in Slack.

---

## Architecture

```
                  ┌──────────────────────────┐
                  │  Sunday 11pm (cron)      │
                  │  ad_data_pull.py         │
                  │  via Claude Code         │
                  └────────────┬─────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │  ~/marketing-os/01-.../      │
                │  output/weekly_unified.csv   │
                └────────────┬─────────────────┘
                               │
                               ▼ (Cowork watches folder)
                ┌──────────────────────────────┐
                │  Claude Project Files        │
                │  Campaign Intelligence       │
                └────────────┬─────────────────┘
                               │
                               ▼ (Scheduled prompt fires Mon 8am)
                ┌──────────────────────────────┐
                │  Skills pipeline:            │
                │  • creative-fatigue-radar    │
                │  • claude-ads-auditor        │
                │  • psychographic-profiler    │
                │  • viral-hook-generator      │
                │  • brand-voice-extractor     │
                └────────────┬─────────────────┘
                               │
                               ▼ (Slack MCP)
                ┌──────────────────────────────┐
                │  #growth-weekly              │
                │  Executive summary + DM      │
                └──────────────────────────────┘
```

---

## Files in this workflow

| File | Purpose | Where it runs |
|------|---------|---------------|
| `ad_data_pull.py` | Multi-platform API pull, unified CSV output | Claude Code (your machine) |
| `config.json` | API credentials and feature flags — also holds the separate `google_ads_write`/`meta_write`/`safety` blocks for draft campaign creation, see below | Read by `ad_data_pull.py` and `ads_campaign_draft.py` |
| `accounts.csv` | Which ad accounts to pull each week | Read by `ad_data_pull.py` |
| `ads_campaign_draft.py` | Creates ONE PAUSED draft campaign on Google Ads or Meta from a brief — agentic-OS edition only, human-gated, see below | Claude Code (your machine), called only by the Chief Orchestrator after an approved HITL gate |
| `campaign_drafts_log.csv` | Append-only record of successful draft creations | Written by `ads_campaign_draft.py` |
| `system_prompt.md` | Project system prompt for the strategist role | Pasted into Project settings |
| `scheduled_prompt.md` | The exact prompt the scheduler runs each Monday | Pasted into Scheduling UI |

---

## Draft campaign creation (agentic-OS edition only, human-gated — read this before touching it)

Everything above this section is read-only: pulling performance data. `ads_campaign_draft.py` is different — it's the one script in this project that reaches into a real, live ad account and creates something. It only ever creates a **PAUSED** campaign (hard-coded in `marketing-os-infra/lib/ads_connector.py`, not a setting you can flip), and three independent things all have to be true before it will do even that:

1. **A Human-In-The-Loop approval gate for this exact action is `approved`.** The Chief Orchestrator opens a `stakes_class: ad_platform_write` gate (`.claude/lib/approval_gate.py`) and presents it to you before anything is created — see `chief-marketing-orchestrator.md`, Step 4.6. The script re-checks the gate's live status itself; it does not trust the caller.
2. **`write_access_confirmed: true` is set by hand** in `config.json`'s `google_ads_write` / `meta_write` block — deliberately separate from the read-only puller's `enabled` flag above, so setting up weekly reporting never silently also authorizes writes.
3. **The brief's daily budget is under `safety.max_daily_budget_usd`** (default $20) — a backstop against a malformed brief, on top of PAUSED-only.

Setup, once you've decided you actually want this:
```bash
pip install google-ads requests  # if not already installed for ad_data_pull.py
```
- **Google Ads:** the write-scoped credentials go in `google_ads_write` — same OAuth dance as the read-only `google_ads` block above, but the token/account needs write access, and `customer_id` is the account that gets written to. Double-check it before flipping `write_access_confirmed`.
- **Meta:** `meta_write` needs an access token with the `ads_management` permission (the read-only block above only needs `ads_read`), `ad_account_id`, and `page_id` (Meta ad creatives require a Page).

Test the wiring without touching a live account:
```bash
python3 ads_campaign_draft.py --platform google_ads --brief drafts/example_brief.json --gate-id anything --dry-run
```
A successful real run creates a real, PAUSED object in the account — nothing spends until a human reviews it and manually enables it in the platform's own UI. That's a feature, not a gap: this connector's whole job is producing something for a human to look at, not shipping a live campaign.

---

## Setup (3 hours, one time)

### 1. Local environment (45 min)

```bash
cd ~/
mkdir -p marketing-os/01-campaign-intelligence/{scripts,config,output}
cd marketing-os/01-campaign-intelligence

# Drop ad_data_pull.py into scripts/
# Drop config.json and accounts.csv into config/

python3 -m venv .venv
source .venv/bin/activate
pip install requests google-ads facebook-business pandas python-dotenv
```

### 2. API credentials (90 min)

This is the most painful step. Each platform has its own dance.

**Meta Marketing API:**
- developers.facebook.com → My Apps → Create App → Business
- Add Marketing API product
- Generate System User access token with `ads_read` permission
- Token goes into `config.json` → `meta.access_token`

**Google Ads API:**
- Apply for Developer Token (24-hour approval typical)
- developers.google.com/google-ads/api → enable API
- OAuth2 client credentials in Google Cloud Console
- Generate refresh token via OAuth playground
- All four values go into `config.json` → `google_ads`

**TikTok Marketing API:**
- ads.tiktok.com/marketing_api → Create App
- Generate access token (long-lived, 1 year)
- Token goes into `config.json` → `tiktok.access_token`

Skip any platform you don't run. The script handles missing platforms gracefully.

### 3. Test the pull manually (15 min)

```bash
cd ~/marketing-os/01-campaign-intelligence
source .venv/bin/activate
python3 scripts/ad_data_pull.py --test
```

You should see a summary like:
```
[Meta] Pulled 47 ads, 14 days, $84,200 spend
[Google] Pulled 32 ads, 14 days, $61,400 spend
[TikTok] Pulled 18 ads, 14 days, $22,100 spend
✓ Wrote output/weekly_unified.csv (97 rows)
```

If a platform fails, the error message tells you what credential is missing. Fix and re-run.

### 4. Cron job (5 min)

```bash
crontab -e
```

Add this line:
```
0 23 * * 0 cd ~/marketing-os/01-campaign-intelligence && /path/to/.venv/bin/python3 scripts/ad_data_pull.py >> output/cron.log 2>&1
```

This runs every Sunday at 11pm. Replace `/path/to/.venv` with your actual venv path (run `which python3` after activating).

### 5. Cowork folder watcher (10 min)

In Cowork:
- Create a watched folder rule for `~/marketing-os/01-campaign-intelligence/output/`
- Action: when `weekly_unified.csv` appears (modified within last 1 hour), upload it to the Claude Project named "Campaign Intelligence" replacing any file with the same name

If Cowork isn't available, the manual fallback is: drag-drop the CSV into the project Sunday night yourself, or set up the project to read from a connected Google Drive folder where Claude Code uploads the CSV via API.

### 6. Claude Project setup (15 min)

- Create new Project: "Campaign Intelligence"
- Upload skills: `creative-fatigue-radar.md`, `claude-ads-auditor.md`, `psychographic-profiler.md`, `viral-hook-generator.md`, `brand-voice-extractor.md`
- Paste contents of `system_prompt.md` into Project custom instructions
- Enable Slack connector at the account level if not already

### 7. Schedule the Monday run (5 min)

In Claude Chat:
- Open the Campaign Intelligence project
- Open Scheduling (sidebar or settings)
- Create new schedule:
  - **Cadence:** Weekly, Monday 8:00am
  - **Prompt:** paste contents of `scheduled_prompt.md`
  - **Delivery:** new chat thread + Slack push (configured in the prompt itself)

### 8. Smoke test (15 min)

Run the schedule once manually before relying on it:
- Scheduling UI → "Run now"
- Verify the Slack message appears in `#growth-weekly`
- Verify the full chat thread contains all 6 sections (audit, fatigue verdict, persona refresh, briefs, action list)

If anything is missing, troubleshoot before next Monday.

---

## What you'll see Monday morning

In Slack at 8:15am:

> 🎯 **Weekly Campaign Intelligence — Mon Mar 4**
>
> **Pipeline:** $167.7k spend last 7 days, blended ROAS 3.2x (-0.4 WoW)
>
> **Top 5 actions this week:**
> 1. Pause Meta ad `Spring_Hero_v3` (true fatigue, $12k waste projected) — Media Buyer
> 2. Reallocate $8k from Google generic to branded (CPM compression detected) — Media Buyer
> 3. Brief 3 new UGC variants for fatigued TikTok hero — Creative
> 4. Audit conversion event setup on Meta (3 events firing duplicates) — Analytics
> 5. Test value-based bidding on top Google campaign (eligible) — Media Buyer
>
> Full report: [link to chat thread]

The full chat thread contains the audit, persona refresh, and 15–25 individual creative briefs you can hand directly to creators.

---

## Troubleshooting

**`ad_data_pull.py` fails Sunday night, no CSV produced.**
→ Check `output/cron.log` first thing Monday. Auth errors are most common (tokens expire). Refresh credentials, manual-run the script, kick off the schedule manually for this week.

**Cron runs but `weekly_unified.csv` is empty.**
→ All three API calls failed silently. Check `config.json` and run with `--verbose` for detailed error output.

**Cowork doesn't pick up the CSV.**
→ Manual fallback: drag-drop into Project files Sunday night. Cowork tends to miss files when the desktop app has been closed. Keep it running in background.

**Scheduled chat runs but Slack post doesn't appear.**
→ Slack connector OAuth probably expired. Reconnect at Settings → Connectors → Slack. Re-run the schedule manually for this week.

**Reports flag every ad as fatigued.**
→ Skill calibration issue, not infrastructure. See `02-seo-content-factory` calibration guidance — same principle applies. The fatigue radar should require 2+ corroborating signals.

---

## Refusal patterns (these are correct behavior)

The system will refuse to:
- Run a diagnosis on under 7 days of data (sample too thin)
- Flag fatigue with only one signal (CTR decline alone)
- Generate creative briefs for ads not flagged as fatigued
- Comment on bidding strategy with under 14 days of conversion data
- Make recommendations for platforms not in the data

If you see these refusals, the system is working correctly. Don't override.
