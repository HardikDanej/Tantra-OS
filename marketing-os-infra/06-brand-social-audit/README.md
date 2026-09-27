# 06 — Brand Social Audit

Read-only Tool-layer connector for the **Brand & Creative Marketing** agentic system — the first live data access `organic-social-community-building-agent` (specifically `organic-social-channel-management-subagent`) has had. Before this workflow existed, every cross-platform presence-consistency audit that domain agent ran was a WebFetch/WebSearch approximation of publicly-visible profile data, with no structured, re-runnable source.

## What this does

`social_profile_pull.py` pulls the brand's own owned Instagram and LinkedIn profile metrics (followers, following, post count) via each platform's official API, validates every row against `tool_router.SocialProfileSnapshotRow`, and writes a unified CSV plus a `.sources.json` manifest the consuming sub-agent should read before trusting the CSV as complete (see `tool_router.py`'s module docstring for why the manifest exists).

## What this does NOT do

- **Does not pull competitor data.** This connects as the brand's own account and reads its own metrics. A competitor's public social metrics stay exactly what they already were — a WebSearch/WebFetch-sourced, citation-checked claim (`citation_guard.py`), never a connector pull. Do not repurpose these credentials to scrape another account.
- **Does not post, schedule, or modify anything.** Purely read-only, same discipline as `gsc_keyword_pull.py`/`ad_data_pull.py` — this pulls what already exists, never writes.

## Setup

1. Fill in `config.json`'s `instagram`/`linkedin` blocks with real credentials (see each block's `_help` field for where to get them) and list the real accounts to audit under `accounts`.
2. Test without making API calls: `python3 social_profile_pull.py --dry-run`
3. Run for real: `python3 social_profile_pull.py`
4. Optionally schedule weekly via cron (see the script's own docstring for the exact line).

## Output

- `output/social_profile_snapshots.csv` — one row per platform per run, unified schema.
- `output/social_profile_snapshots.csv.sources.json` — per-platform pull status (ok/partial/error), so a partial pull (one platform's token expired) never gets silently read as "everything's fine, followers are just flat."
