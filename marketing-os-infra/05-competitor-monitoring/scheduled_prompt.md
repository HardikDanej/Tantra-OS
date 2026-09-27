# Scheduled prompt — Competitor Ad-Library Re-Audit

**Cadence:** Weekly (this path is more expensive per run than `site_snapshot.py` — it's a real LLM dispatch, not a hash comparison — so it doesn't need daily cadence to be useful).

**Why this is a separate path from `site_snapshot.py`:** that script is deterministic — no LLM involved, so there's no hallucination surface for it to have. Meta Ad Library and Google Ads Transparency Center have no plain REST API to hash-diff against; reading them requires `WebFetch`/`WebSearch`, which only exist inside a Claude session. That means this path genuinely needs an LLM in the loop, and an unattended LLM run with nobody watching is exactly the scenario `evidence_log.py`/`citation_guard.py` exist for. **Do not skip the citation-guard step below "because it's just a routine check" — routine-with-nobody-watching is the highest-risk case, not the lowest.**

Paste into Scheduling as the prompt for a weekly scheduled chat task.

**Activation:** the prompt text below starts with `mk ` (Tantra's wake word) because Tantra's agents are only dispatched once Tantra is active in the session — keep it when pasting. A scheduled or headless run may alternatively set `TANTRA_ACTIVE=1` in its environment.

---

mk you are running the scheduled weekly competitor ad-library re-audit. For each competitor configured in `marketing-os-infra/05-competitor-monitoring/config.json`:

1. **Dispatch via the Chief Marketing Orchestrator to the Ads/Paid-Media Agent's public competitive-intelligence track** (see `ads-paid-media-agent.md`) for that competitor's name, checking Meta Ad Library, Google Ads Transparency Center, and TikTok Commercial Content Library. This is the exact same track that agent already runs for an on-demand competitor check — nothing new is being asked of it, only that it's running on a schedule instead of in response to a live request.

2. **The Ads Agent's own existing rules still apply in full, unweakened by this being a scheduled run:**
   - Log every WebFetch/WebSearch result to the evidence ledger (`evidence_log.py add --source-type webfetch|websearch ...`) before drafting any output.
   - Run `citation_guard.py` against the draft before treating anything in it as fact.
   - State the track's hard ceiling explicitly: observed creative only, never spend/ROAS/CTR/performance.
   - **If `citation_guard.py` returns FAIL for a competitor this run, do not write that competitor's findings to the alert ledger as confirmed.** Either cut the unverified claims and write only what's left, or — if nothing survives — skip that competitor for this run and note it in the session's own summary as "ad-library check degraded this week, citation guard failed N claims," not as silence.

3. **Compare against last week's stored snapshot** at `marketing-os-infra/05-competitor-monitoring/ad_library_snapshots/<competitor_slug>.json` (create the directory/file if this is the first run for that competitor). The snapshot is a plain JSON object: `{"competitor": "...", "checked_at": "...", "observations": [{"platform": "meta|google|tiktok", "ad_summary": "one line, format + angle + destination", "first_seen_estimate": "..."}]}`. Read the previous file (if it exists) and identify which observations in THIS run's results are genuinely new — same platform, no reasonably-matching prior observation — versus which were already seen last time. **Only genuinely new observations become alerts.** An unchanged, already-seen ad running for another week is not news and should not generate a new alert entry every run — that's exactly the kind of noise that trains a human to stop reading the alert feed.
   - Write this run's full observation set back to the snapshot file (whether or not anything was new), so next week's comparison has a real baseline.

4. **For each genuinely new observation, append one line to `marketing-os-infra/05-competitor-monitoring/alerts.jsonl`** in the same shape `site_snapshot.py` uses, so `python site_snapshot.py list-alerts` surfaces both kinds of alert together:
   ```json
   {"alert_id": "alert_<short hash of competitor+platform+checked_at>", "event": "detected", "source": "ad_library_reaudit", "competitor": "<name>", "url": "<the ad library URL checked>", "detected_at": "<ISO timestamp>", "ad_summary": "<the one-line summary>", "citation_check": "PASS|FAIL (N verified, M unverified)"}
   ```
   Carry `citation_check` on every alert line — a human scanning the alert feed should be able to see at a glance which findings passed the mechanical check and which didn't, not have to go find the session transcript to know.

5. **Do not draft creative in response to what's observed here.** This is a monitoring run, not a briefing dispatch — if something observed looks like it warrants a creative-brief response, name that as a follow-up recommendation in the session's own summary, and let a human (or a separate, explicit dispatch) decide whether to act on it. Scope creep from "monitor" to "also draft a response" inside an unattended scheduled run is exactly the kind of expanding-autonomy failure mode this whole task exists to avoid.

6. **This prompt never posts anywhere.** No Slack, no email — the alert ledger is the deliverable. A human reviews it via `python site_snapshot.py list-alerts --status detected` the next time they're in an interactive session, the same way pending HITL approval gates get surfaced.

## End-of-run summary (what this scheduled session should leave behind)

```
COMPETITORS CHECKED: [list]
NEW ALERTS THIS RUN: [count, or "none"]
CITATION CHECK: [PASS/FAIL per competitor — never omit a FAIL to keep this section clean]
DEGRADED: [any competitor whose check didn't complete or failed citation-guard, and why]
```
