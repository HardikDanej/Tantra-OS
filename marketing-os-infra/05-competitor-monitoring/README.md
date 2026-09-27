# Workflow 05: Continuous Competitor Monitoring

**Surfaces used:** Claude Code (daily cron, no LLM) · Claude Chat (weekly scheduled prompt, LLM-driven)
**Cadence:** Daily site-diff (deterministic) + weekly ad-library re-audit (LLM-driven)
**Setup time:** ~20 minutes
**Best for:** Anyone already running the Website Development Agent or the Ads Agent's public competitive-intelligence track who wants those checks repeated automatically instead of re-requesting them by hand

---

## What this workflow does, and why it's two different mechanisms

This is the highest-risk workflow in this project to get wrong, for one specific reason: it's the only one designed to run **unattended and recurring**, with nobody watching each individual run. Every other workflow here is either a human-initiated dispatch or a human-reviewed draft. A silent hallucination in a one-off request gets caught because a human is right there reading the output. A silent hallucination in the 47th unattended weekly run of something nobody's actively watching can sit in a feed for months.

So this workflow deliberately keeps the LLM out of the loop everywhere that's actually possible, and only brings it in where the task structurally requires it — and where it does, wires in this project's existing reliability layer (`evidence_log.py` + `citation_guard.py`, referred to elsewhere in this repo as "Group 1") as a hard requirement, not a suggestion.

1. **`site_snapshot.py` (daily, deterministic, no LLM):** fetches a configured list of competitor URLs via a real browser (`browser_render.py`), extracts visible text, hashes it, and diffs against yesterday's snapshot. A change is a mechanical fact — a hash either matches or it doesn't — so there is no hallucination surface here at all. Writes an alert only when something genuinely changed.

2. **`scheduled_prompt.md` (weekly, LLM-driven, via Scheduling):** re-runs the Ads Agent's existing public competitive-intelligence track (Meta Ad Library / Google Ads Transparency Center / TikTok Commercial Content Library) for each configured competitor — these have no plain REST API to hash-diff against, so this path genuinely needs `WebFetch`/`WebSearch`. This is the one place in this workflow an LLM does the finding, and it's required to log evidence and pass `citation_guard.py` before anything gets written to the alert ledger.

Both paths write to the same `alerts.jsonl` — a human reviews it in one place regardless of which mechanism found something.

**What this workflow never does: post anywhere on its own.** No Slack, no email, no webhook. An unattended process auto-posting to an external channel is "sending a message on someone's behalf" with nobody in the loop to catch it going wrong — that's out of scope here regardless of how low-stakes the content seems. The alert ledger is the deliverable; a human (or the Chief Orchestrator, at the start of an interactive session) reads it.

---

## Architecture

```
   Daily cron                              Weekly Scheduling
   site_snapshot.py                        scheduled_prompt.md
   (no LLM)                                (Ads Agent public track)
        │                                          │
        ▼                                          ▼
   browser_render.py                    WebFetch/WebSearch + evidence_log.py
   fetch + hash + diff                  + citation_guard.py (mandatory)
        │                                          │
        └──────────────────┬───────────────────────┘
                            ▼
                    alerts.jsonl
              (append-only, source-tagged)
                            │
                            ▼ (next interactive session)
              Chief Orchestrator surfaces unreviewed
              alerts, same pattern as pending HITL gates
```

---

## Files in this workflow

| File | Purpose | Where it runs |
|------|---------|---------------|
| `config.json` | Which competitors/URLs to monitor | Read by `site_snapshot.py` |
| `site_snapshot.py` | Daily deterministic fetch/hash/diff, alert ledger CLI | Claude Code (your machine), cron |
| `snapshots/` | Last-known text content + hash per URL (created on first run) | Read/written by `site_snapshot.py` |
| `scheduled_prompt.md` | Weekly LLM-driven ad-library re-audit prompt | Pasted into Scheduling UI |
| `ad_library_snapshots/` | Last week's observed-creative summary per competitor (created on first run) | Read/written by the scheduled prompt |
| `alerts.jsonl` | Append-only alert ledger, both mechanisms write here | Read via `site_snapshot.py list-alerts` |

---

## Setup (~20 min)

### 1. Configure competitors (5 min)

Edit `config.json` — replace the placeholder entry with real competitor names and 2-3 high-signal URLs each (homepage, pricing, a product page). Monitoring every page on a competitor's site produces mostly noise for the same review effort.

### 2. Dependencies (5 min)

```bash
pip install playwright beautifulsoup4
python -m playwright install chromium   # skip if already installed for the Website Development Agent
```

### 3. Test the deterministic path (5 min)

```bash
cd ~/marketing-os/05-competitor-monitoring
python3 site_snapshot.py run --dry-run
```
First real run establishes the baseline (every URL reports "no baseline yet" — that's expected, not a failure). Run it again and it should report "unchanged." Nothing is an alert until the SECOND real run after a baseline exists and something actually differs.

### 4. Cron job for the daily check (5 min)

```bash
crontab -e
```
Add:
```
0 6 * * * cd ~/marketing-os/05-competitor-monitoring && /path/to/.venv/bin/python3 site_snapshot.py >> output/cron.log 2>&1
```

### 5. Weekly scheduled prompt for the ad-library re-audit (5 min)

In Claude Chat: Scheduling → New schedule → Weekly → paste `scheduled_prompt.md`'s contents. This one needs a real Claude session (WebFetch/WebSearch), so it goes through Scheduling, not cron.

---

## Reviewing alerts

```bash
python3 site_snapshot.py list-alerts                       # everything, newest first
python3 site_snapshot.py list-alerts --status detected      # unreviewed only
python3 site_snapshot.py mark-reviewed --alert-id <id> --note "..."
```

An alert with `[source: site_diff]` includes a mechanical unified-diff snippet in the ledger line — that's a real, verifiable change, not a summary of one. An alert with `[source: ad_library_reaudit]` carries its own `citation_check` field; treat a `FAIL` there with real skepticism regardless of how confident the surrounding text sounds — that's exactly the number this whole workflow's design exists to keep honest.

---

## Troubleshooting

**Every URL says "blocked" instead of "changed"/"unchanged."**
→ A real bot-challenge, not a tool bug — see `browser_render.py`'s own docstring. This script does not attempt to solve or evade it, by design. If a specific competitor's site consistently blocks headless Chromium, that page just can't be monitored this way; drop it from `config.json` rather than expecting a workaround.

**`site_snapshot.py` reports "changed" every single day for the same page.**
→ Likely a volatile element leaking into the hashed text (a rotating testimonial, a "X people viewing this" counter, a client-side-rendered timestamp). The script hashes extracted visible text specifically to avoid the worse version of this problem (raw HTML hashing, which flags on every analytics-ID rotation) — but a sufficiently dynamic page can still trip it. Check the diff snippet in the alert; if it's the same cosmetic element every time, that URL isn't a good monitoring target.

**Weekly ad-library re-audit produces no alerts, ever.**
→ Could genuinely mean nothing new ran that week — check `ad_library_snapshots/<competitor>.json`'s `checked_at` to confirm the schedule is actually firing, not just that nothing changed. If the file isn't updating, the Scheduling job itself likely isn't running; check Scheduling UI status before assuming a quiet week.
