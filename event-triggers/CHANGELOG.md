# Event Triggers Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "live event-type triggers" gap identified
against the OS blueprint (`Marketing OS.md` §12's Event trigger type:
lead.created, campaign.launched, opportunity.stage_changed).

- New: `.claude/lib/event_diff.py` — a generic, real snapshot-diff engine
  (CSV or JSON input) that detects new records and watched-field changes
  against a locally cached snapshot. No live API call happens inside it —
  it only ever diffs a real puller's already-written output.
- `.claude/lib/trigger_registry.py` extended with a new `"event"` trigger
  kind (alongside the existing `cron`/`scheduled_prompt`/`condition`),
  backed by two real event kinds: `campaign_launched` and
  `opportunity_created_or_stage_changed`. Reuses the existing registered-
  trigger/ledger/acknowledge machinery rather than building a parallel
  system. Verified no regression: the pre-existing `pending_gate_age`
  condition kind still fires correctly on a real stale-gate scenario
  after this change.
- Additive change to `marketing-os-infra/04-hubspot-revenue-agent/hubspot_historical.py`:
  now also writes `historical_deals_snapshot.json` (flattened raw per-deal
  records) alongside its existing aggregate report — nothing existing was
  changed, confirmed via `py_compile` and a `git diff` review. This is
  what makes `opportunity_created_or_stage_changed` possible; before this,
  no file anywhere persisted individual deal records.
- `lead.created` explicitly NOT built — no contact-level connector or
  snapshot exists anywhere in this repo (named in gap #2's Tool/Data
  Model registry). Stated plainly rather than faked.
- Verified end-to-end with labeled synthetic fixtures
  (`examples/campaign_launched/`, `examples/opportunity_events/`): first
  snapshot baselines silently; a real new record and a real field change
  both fire correctly; re-running against unchanged data does not
  re-fire.
