# Setup

Tantra runs in two tiers. Tier 1 is everything that works inside Claude Code today, with no accounts, keys or spend. Tier 2 is the scheduled, unattended workflows, which need real credentials. Start with Tier 1. Only pay for Tier 2 once Tier 1 has earned it.

Install first: [`INSTALL.md`](INSTALL.md).

---

## Tier 1: runs today, inside Claude Code, for free

### What you get

- **238 agents** in `.claude/agents/`: six top-level entry points (five system orchestrators plus `enterprise-marketing-orchestrator` for company-wide asks), the `cross-system-dispatch-bridge`, 21 domain agents, and 210 specialists.
- **62 skills** in `.claude/skills/`, the tools the agents call to do the work.
- **7 knowledge bases** in `knowledge-bases/`, read in slices with `kb_slice.py`, never whole.
- **27 deterministic scripts** in `.claude/lib/`. These cover approval gates, scope routing, site checks, context budgets, calibration, redispatch caps, provenance and more. They're plain Python, and none of them calls a model.
- **Hooks**: the `mk` wake word, eight sentinels (Scribe, Pulse, Echo, Lens, Contract, Meter, Boundary, Scope), the MCP connector guard and the Tantra Seal.

### Waking it up

```
mk audit example.com's SEO and tell me what to fix first
```

A message starting with `mk`, or containing "MK agent", turns Tantra on for the session. `mk off` turns it off. Without the wake word, Claude Code refuses to dispatch Tantra agents. Unattended runs set `TANTRA_ACTIVE=1`. Details: `.claude/hooks/README.md`.

### Works end to end with no accounts

- **Brand foundation**: personas, voice system, ICP, from real brand assets you provide.
- **SEO audit, strategy and drafting**: `site_checks.py` measures the page in plain Python. Agents spend tokens only on what the numbers mean.
- **Paid media diagnosis and briefing**: from a CSV export of your ad data.
- **Brand, GTM, research and PR work** across the other four systems.
- **Any drafting task** through the Writing/Content Production Agent.

### Optional, still free

| Add | What it does | How |
|---|---|---|
| Laya | Fast local cross-check on every approval-gate decision | `pip install -r .claude/lib/laya_requirements.txt` (~2.7GB model downloads once) |
| PageSpeed key | Reliable Core Web Vitals in `site_checks.py` (keyless calls often hit quota) | Free key from Google Cloud, set `PAGESPEED_API_KEY` |
| MCP connectors | Read access to your CRM, analytics, docs | `mk connect <app>`, approval-gated, read-only by default. See `connectors/README.md` |

### Seeing what it cost

```bash
python .claude/lib/sentinel_report.py report
```

This shows dispatches, output tokens per agent, time, stalls and output-format repairs for the latest session. It's measured from the hooks' own ledgers, not estimated by a model.

---

## Tier 2: scheduled, unattended workflows

These live in `marketing-os-infra/`. Each workflow's `orchestration.md` (in `workflows/`) is the standing contract its scheduled prompt dispatches through the orchestrator. The scripts pull data, and the agents reason over it.

| Workflow | Needs |
|---|---|
| 01 Campaign Intelligence | Meta / Google Ads / TikTok API tokens, Slack connector, `ad_data_pull.py` on cron |
| 02 SEO Content Factory | Search Console OAuth, WordPress or Webflow connector (drafts only, never publishes live), `gsc_keyword_pull.py` on cron |
| 03 Brand Launch Suite | Nothing external; `asset_ingestion.py` once per engagement |
| 04 HubSpot Revenue Agent | HubSpot MCP + private-app token, Slack connector, `hubspot_historical.py` on cron |
| 05–08 Competitor monitoring, brand/social audit, research data, PR & media | See each folder's README |

Rules that don't change at this tier:
- Credentials go in gitignored `.env` files. Committed `config.json` files hold `REPLACE_WITH_*` placeholders only.
- Nothing publishes, sends, or spends on its own. CMS writes are drafts. Ad-platform and CRM writes need an approved HITL gate, and the script re-checks that gate itself.
- `marketing-os-infra/PAID_API_DECISIONS.md` records why no workflow needs a paid third-party data API.

---

## In order

1. Install (`INSTALL.md`), then run `python tools/check_install.py` until it says PASS.
2. Run one real Tier 1 task. Read the output and the token report.
3. Fix what that run surfaces. Agents are markdown, so iteration is cheap.
4. Only then wire up Tier 2 for the one workflow you'd actually run every week.
