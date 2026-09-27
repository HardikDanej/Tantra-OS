# Workflow 02: SEO Content Factory

**Surfaces used:** Claude Code · Cowork · Claude Chat (Projects + Skills) · Scheduling · `cms_publish.py` (WordPress REST API or Webflow CMS API v2, draft-only) · Slack MCP
**Cadence:** Daily (nightly keyword pull → daily morning article production)
**Setup time:** ~2 hours first time, ~5 minutes/day thereafter
**Best for:** Brands publishing 5+ long-form articles per week with E-E-A-T quality bar

---

## What this workflow does

1. **Every night at 11pm:** Claude Code runs `gsc_keyword_pull.py`. It hits Google Search Console for the last 28 days of query performance, identifies keyword gaps (high impressions but low CTR, or queries you're ranking 8–20 for), scores them, and updates `topic_queue.csv` with the prioritized backlog.

2. **Every weekday at 6am:** A scheduled chat task fires. It picks the top unworked topic from `topic_queue.csv`, runs the 5-skill production pipeline (reddit-insights-bot → content-brief-generator → long-form-article-architect → core-eeat-benchmark → de-ai-ify), and calls `python3 cms_publish.py --article <finished draft>` to create the draft on the configured CMS.

3. **By 9am:** You have a draft article in WordPress or Webflow (never live — see "Publishing the draft" below), marked in `published_log.csv`, ready for editorial review and scheduling.

4. **Cowork** maintains the inventory: marks topics as "in_progress" → "drafted" → "published" as articles move through the pipeline. Surfaces the next 5 topics to a watched dashboard view.

---

## Architecture

```
                ┌─────────────────────────────┐
                │  Daily 11pm (cron)           │
                │  gsc_keyword_pull.py         │
                │  via Claude Code             │
                └────────────┬─────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │  topic_queue.csv (updated)   │
                └────────────┬─────────────────┘
                              │
                              ▼ (Cowork syncs to Project)
                ┌──────────────────────────────┐
                │  Claude Project Files        │
                └────────────┬─────────────────┘
                              │
                              ▼ (Scheduled prompt fires Mon-Fri 6am)
                ┌──────────────────────────────┐
                │  Skills pipeline:             │
                │  • reddit-insights-bot        │
                │  • content-brief-generator    │
                │  • long-form-article-architect│
                │  • core-eeat-benchmark        │
                │  • de-ai-ify                  │
                └────────────┬─────────────────┘
                              │
                              ▼ (cms_publish.py — WordPress REST API or Webflow CMS API v2)
                ┌──────────────────────────────┐
                │  CMS draft created (never    │
                │  live — draft-only in code)  │
                │  published_log.csv updated   │
                └──────────────────────────────┘
```

**A note on "via MCP":** the original design for this workflow assumed a chat-UI WordPress.com connector. This agentic-OS edition runs through Claude Code subagents, which call out via Bash, not chat-level MCP connectors — so the actual publish step is `cms_publish.py`, a small script that hits the WordPress REST API (Application Passwords) or the Webflow CMS API v2 directly. Functionally the same deliverable (a CMS draft), different transport.

---

## Files in this workflow

| File | Purpose | Where it runs |
|------|---------|---------------|
| `gsc_keyword_pull.py` | Nightly Search Console pull, keyword gap scoring | Claude Code (your machine) |
| `cms_publish.py` | Creates the finished article as a draft on WordPress or Webflow (draft-only, enforced in `../lib/cms_connector.py`) | Claude Code (your machine), called by the Orchestrator's synthesis step |
| `config.json` | CMS credentials (site URL, Application Password / API token) — ships with `REPLACE_WITH_*` placeholders | Read by `cms_publish.py` |
| `published_log.csv` | Append-only record of successful drafts (`query,platform,status,post_id,draft_url,article_path,...`) — generated on first successful publish | Written by `cms_publish.py`, read by `gsc_keyword_pull.py` to avoid re-queuing published topics |
| `topic_queue.csv` | Prioritized keyword backlog with scoring | Updated by script, read by scheduled chat |
| `eeat_evidence.json` | Reusable citation library (case studies, original research, expert quotes) | Read by long-form-article-architect during drafting |
| `system_prompt.md` | Project system prompt | Pasted into Project settings |
| `scheduled_prompt.md` | Daily 6am article production prompt | Pasted into Scheduling UI |

---

## Setup (2 hours, one time)

### 1. Local environment (15 min)

```bash
cd ~/marketing-os/02-seo-content-factory
python3 -m venv .venv
source .venv/bin/activate
pip install google-api-python-client google-auth-oauthlib pandas
```

### 2. Google Search Console OAuth (45 min)

This is the one painful part. You only do it once.

- Google Cloud Console → Create project → Enable Search Console API
- Credentials → Create OAuth 2.0 Client ID → Desktop app
- Download `client_secret.json`, place in `config/`
- First script run will open a browser for OAuth; the resulting `token.json` is saved for subsequent runs

### 3. CMS connector — WordPress or Webflow (10 min)

```bash
pip install markdown pyyaml requests
```

Pick one:

- **WordPress:** WP Admin → Users → Your Profile → Application Passwords → Add New Application Password. Copy the generated password (shown once) into `config.json`'s `wordpress.app_password`, along with `site_url` and `username`. The account needs at least the Author role.
- **Webflow:** Webflow → Site settings → Apps & Integrations → API access → generate a v2 Site API token (scope: CMS read+write). Set `webflow.api_token`, `webflow.site_id`, and `webflow.collection_id` (find the collection ID via `GET https://api.webflow.com/v2/sites/{site_id}/collections`) in `config.json`, and set `cms.platform` to `"webflow"`.

Either way: creating a draft is all this connector can do. `publish_wordpress_draft`/`publish_webflow_draft` in `../lib/cms_connector.py` hard-code `status: "draft"` / `isDraft: true` in the request body — there's no parameter that flips that, by design. Taking a draft live is a manual step you take in the CMS admin.

Test the wiring without touching the real site:
```bash
python3 cms_publish.py --article path/to/any/draft.md --dry-run
```

### 4. Test the pull manually (10 min)

```bash
cd ~/marketing-os/02-seo-content-factory
source .venv/bin/activate
python3 gsc_keyword_pull.py --test
```

Expected output:
```
[GSC] Connected to property: https://yourbrand.com
[GSC] Pulled 1,847 queries (last 28 days)
[Scoring] 312 keywords passed filter (impressions >= 100)
[Output] topic_queue.csv updated — 47 new topics added, 18 promoted in priority
```

### 5. Cron job (5 min)

```bash
crontab -e
```

Add:
```
0 23 * * * cd ~/marketing-os/02-seo-content-factory && /path/to/.venv/bin/python3 gsc_keyword_pull.py >> output/cron.log 2>&1
```

### 6. Claude Project setup (15 min)

- Create Project: "SEO Content Factory"
- Upload skills: `reddit-insights-bot.md`, `content-brief-generator.md`, `long-form-article-architect.md`, `core-eeat-benchmark.md`, `de-ai-ify.md` (and optionally `brand-voice-extractor.md` for voice consistency)
- Upload `eeat_evidence.json` to Project files
- Upload your brand voice document (output from Workflow 03 if you have it)
- Paste `system_prompt.md` into Project custom instructions
- If running the agent-dispatched edition instead (see `../../workflows/02-seo-content-factory/orchestration.md`), skip this step — the CMS connector is `cms_publish.py` (step 3 above), not a project-level connector

### 7. Schedule the daily run (10 min)

In Claude Chat:
- Open SEO Content Factory project
- Scheduling → New schedule:
  - **Cadence:** Daily at 06:00 (your timezone), Mon–Fri only
  - **Prompt:** paste `scheduled_prompt.md` contents
  - **Delivery:** new chat thread

### 8. First-week monitoring (ongoing)

Check the first 5 days of output manually. The E-E-A-T audit should fail roughly 30–40% of articles on first pass — that's healthy calibration. If 100% pass, the audit skill is too lenient. If 100% fail, your evidence library is too thin.

---

## What you'll see by 9am each weekday

In WordPress drafts:
- One article (2,000–4,000 words), formatted, with meta description, focus keyword, suggested URL slug, and 3 headline variants in the post excerpt for editor selection
- Status: draft (not published — you review before scheduling)

In `topic_queue.csv`:
- The published topic moved to `published_log.csv` with publication timestamp
- Next 5 topics ranked and ready for tomorrow's runs

In the chat thread (for diagnostic review):
- The audience research dossier (with verbatim Reddit quotes — these are reusable for future articles on related topics)
- The editorial brief (archived for future reference)
- The E-E-A-T audit scorecard (this is your quality control signal — patterns over time tell you where the system is drifting)
- The de-ai-ify diff log (shows what cadence patterns were stripped)

---

## Calibration over time

The compounding value of this workflow shows up in week 4, not week 1. Each daily run:
- Adds to your audience research dossier library (Reddit quotes from related topics accumulate)
- Strengthens your evidence library if you're feeding case studies/research back in
- Reveals patterns in what topics consistently fail E-E-A-T audits (probably YMYL topics in your niche — flag those for human-only writing)

By week 8, the system knows your topical territory better than most freelance writers do.

---

## Refusal patterns

The system will refuse to produce articles for:
- Keywords with under 100 monthly searches and no strategic justification
- YMYL topics (medical, legal, financial advice) without verified expert byline
- Topics where the audience research dossier comes back empty (too niche or too B2B for Reddit signal)
- Articles where the E-E-A-T audit verdict is `fails_quality_bar` (returned to architect for revision, not published)

If the system refuses 5 days in a row, your topic queue is upstream-broken. Open `topic_queue.csv`, review the top 20, and manually deprioritize anything that shouldn't be in the queue.

---

## Troubleshooting

**Cron runs but topic_queue.csv isn't updated.**
→ Check cron.log. GSC OAuth tokens expire after extended inactivity. Rerun manually to refresh `token.json`.

**Scheduled run finishes but no CMS draft appears.**
→ Run `python3 cms_publish.py --article <the finished draft> --dry-run` manually to isolate the failure — it prints the parsed frontmatter without calling the API. If that passes, drop `--dry-run` and check the printed `reason`/`detail`: `config_missing` means `config.json` still has a `REPLACE_WITH_*` placeholder; an `http_401`/`http_403` means the WordPress Application Password or Webflow API token expired or was revoked — regenerate it. The article output should still be on disk / in the chat thread for manual posting either way.

**Every article fails E-E-A-T audit.**
→ Evidence library is empty or too generic. Populate `eeat_evidence.json` with actual case studies, original research findings, expert quotes the brand can cite.

**Articles read as fluent but generic.**
→ Brand voice document missing from Project files, or the de-ai-ify pass is over-correcting. Audit the diff logs to see what's getting stripped.

**Topic queue has 800 entries and grows daily.**
→ The score threshold in `gsc_keyword_pull.py` is too lenient. Raise the minimum composite score in the script's `SCORE_THRESHOLD` constant. Quality > quantity.
