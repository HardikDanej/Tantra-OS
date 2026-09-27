# Event Triggers

The OS blueprint's Section 12 "Event" trigger type — `lead.created`,
`campaign.launched`, `opportunity.stage_changed` — made real for a system
that has no live webhook receiver and, by deliberate design (see the
top-level README's "zero external cost, clone-and-run" architecture),
never will.

## The honest mechanism: detect, don't receive

This system already pulls real data on a schedule — `ad_data_pull.py`
writes `01-campaign-intelligence/output/weekly_unified.csv`,
`hubspot_historical.py` writes a weekly aggregate report. Nothing here
calls a live API itself. `.claude/lib/event_diff.py` only ever diffs a
puller's already-written output file against the last snapshot it
cached, and reports what changed since then. **Detecting that something
changed since the last pull is not the same as receiving a live push
event the instant it happens** — this is stated plainly rather than
implied away, because "our event triggers work" would be a materially
overclaimed capability if it quietly meant "eventually, next time the
weekly cron runs."

Two real event types are wired end-to-end, both through
`.claude/lib/trigger_registry.py`'s existing registered-trigger/ledger/
acknowledge machinery (a new `"event"` trigger kind, alongside the
existing `cron`/`scheduled_prompt`/`condition`) — not a parallel system:

- **`campaign_launched`** — diffs `weekly_unified.csv` (real, already
  produced) against a cached snapshot on `ad_id`, watching `campaign_name`.
  A new `ad_id` or a changed `campaign_name` fires.
- **`opportunity_created_or_stage_changed`** — diffs a real per-deal
  snapshot against a cached copy on `id`, watching `dealstage`.

## A real gap this closed in an existing script, additively

`hubspot_historical.py` previously only ever wrote an **aggregate**
report (`historical_trends.json` — forecast accuracy, win rate, stage-
conversion drift) — the raw per-deal records it pulls (`deals`, with
`dealname`/`amount`/`dealstage`/`pipeline` per deal) lived only in a local
variable during that one run and were never persisted anywhere.
There was nothing real to diff for an individual deal's stage change.

Fixed with a small, purely additive change: right after a successful deal
pull, it now also writes `historical_deals_snapshot.json` — the same raw
deals, flattened (HubSpot's real API response nests properties under a
`properties` key; this flattens `id` + `properties` into one dict per
deal). **No existing output, variable, or analysis was touched** — this
is a new file write alongside the existing ones, verified with
`py_compile` and a `git diff` review before trusting it.

## What's NOT built, named rather than faked

**`lead.created`** — no connector in this repo persists individual
HubSpot **contact** records anywhere (see `data-model/core_data_model.json`'s
`customer_contact` entry: "no dedicated Pydantic row class exists yet for
contacts specifically" — a gap named back in gap #2). There is nothing
real to diff against for this event type yet. Building it would need the
same additive-snapshot treatment `hubspot_historical.py`'s deal pull just
got, applied to a contact pull that doesn't exist in this repo today.

## Using it

Register an event trigger the same way any other trigger gets registered:

```bash
python .claude/lib/trigger_registry.py memory/triggers.jsonl register \
  --trigger-id ads_campaign_watch --kind event --condition-kind campaign_launched \
  --params '{"current": "marketing-os-infra/01-campaign-intelligence/output/weekly_unified.csv", \
             "snapshot": "memory/.snapshots/campaign_launched.json", \
             "id_field": "ad_id", "watch_fields": ["campaign_name"]}' \
  --target chief-marketing-orchestrator --description "detect newly launched ad campaigns"

python .claude/lib/trigger_registry.py memory/triggers.jsonl check \
  --gates-ledger memory/approval_gates.jsonl --outcomes-log memory/outcomes.jsonl \
  --redispatch-log memory/redispatch_log.jsonl
```

`check` runs every registered event trigger alongside the existing
condition triggers, in one pass. A fired event is logged into
`memory/triggers.jsonl` exactly like a fired condition — `acknowledge`
still works the same way.

**One real design difference from the condition triggers, stated
explicitly:** an event trigger's snapshot auto-advances on every check
that finds a real change (like a queue consumer moving its read offset
forward) — the next check should count from *now*, not the original
baseline, or it would re-fire the identical diff forever. This is
deliberately different from `version_manifest.py`'s git-like "review,
then explicitly accept a new baseline" model (gap #5) — the two
mechanisms answer different questions ("did anything change, ever, that
I haven't reviewed yet" vs. "did a new business event happen since I last
looked"), and conflating their semantics would make one or the other
behave wrong.

## Verified, not just built

`examples/campaign_launched/` and `examples/opportunity_events/` are
labeled synthetic fixtures (a `week1`/`week2` pair each), not real
business data. Re-run these to reproduce the exact behavior described
above:

```bash
# campaign_launched: week1 already baselined into snapshot.json; week2 should fire
python .claude/lib/event_diff.py check --current event-triggers/examples/campaign_launched/week2.csv \
  --snapshot event-triggers/examples/campaign_launched/snapshot.json --id-field ad_id --watch-field campaign_name

# opportunity_events: week1 already baselined; week2 should fire
python .claude/lib/event_diff.py check --current event-triggers/examples/opportunity_events/week2.json \
  --snapshot event-triggers/examples/opportunity_events/snapshot.json --id-field id --watch-field dealstage
```

Both were also verified for the failure mode that matters most for a
diff-based trigger: **re-running against unchanged data does not
re-fire** (confirmed against a scratch copy before committing the
examples above), and the very first snapshot for a workspace baselines
silently rather than reporting every pre-existing record as "new."
