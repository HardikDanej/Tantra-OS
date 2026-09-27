# Workflow 04: HubSpot Revenue Agent — Agent-Orchestrated Edition

**Change from the original marketing-os version:** the original system prompt had `psychographic-profiler` both score ICP fit AND draft re-engagement copy in the same pass. That's now split: the **Revenue/CRM Agent** scores and targets, the **Writing Agent** drafts. Neither agent can send anything — that boundary was already correct in the original ("humans send") and carries forward unchanged, now enforced as one of the Chief Orchestrator's hard deterministic constraints rather than a single line in a skills list.

## What triggers this workflow

Same as before: scheduled task fires weekday mornings at 8:30am using the HubSpot MCP (live pull), plus a separate Sunday 9pm Claude Code cron job (`hubspot_historical.py`) for trend data the MCP can't aggregate efficiently.

**Activation:** Tantra's agents are only dispatched once Tantra is active, so the scheduled prompt that fires this workflow starts with the wake word `mk ` (e.g. "mk run the daily revenue intelligence pass"); a scheduled or headless run may alternatively set `TANTRA_ACTIVE=1` in its environment.

## The dispatch sequence

```
Scheduled trigger (weekday 8:30am)
        │
        ▼
CHIEF ORCHESTRATOR — DISPATCH mode
  Step 1 (Gatekeeper): if icp_definition.md is missing, contains placeholder
    language, or the Marketing Strategist Agent has never run for this brand,
    surface this BEFORE dispatching — this is the one dependency the original
    workflow called a "no-go" condition, so catch it at the gate, not three
    steps into a run that will produce fabricated-looking scores.
  Step 2 (Decomposition): two workstreams, sequential — Revenue/CRM Agent
    (diagnosis + targeting) must complete before Writing Agent (drafting).
  Step 3 (Contract #1):
    AGENT: Revenue/CRM Agent
    OBJECTIVE: pipeline pull, health diagnosis, ICP-fit scoring, re-engagement
      targeting spec for qualifying stalled deals
    INPUTS: live HubSpot data (read-only), icp_definition.md,
      historical_trends.json (Sundays only, or most recent if mid-week)
    CONSTRAINTS: refuse if pipeline under 30 active deals; refuse forecast
      calls under 10 deals at a stage; verify "stalled" against activity logs,
      not stage duration alone; exclude any "do not contact" deals
    REQUIRED OUTPUT SHAPE: per Revenue/CRM Agent's own contract format
    CONFIDENCE REPORTING: required, per finding
        │
        ▼
REVENUE / CRM AGENT (pipeline pull → health diagnosis via hubspot-crm-strategist
  → ICP scoring via psychographic-profiler → re-engagement targeting spec —
  see revenue-crm-agent.md; produces a spec, not drafted copy)
        │
        ▼
CHIEF ORCHESTRATOR — dispatches targeting spec to Writing Agent
  Step 4 (Contract #2):
    AGENT: Writing Agent
    OBJECTIVE: draft re-engagement messages for the targeted stalled+high-fit
      deals
    INPUTS: the targeting spec (last interaction, value lever, likely
      objection, per deal), voice_samples.csv
    CONSTRAINTS: max 80 words per message; one clear low-friction CTA; must
      reference specific deal context — no generic re-engagement; flag as
      voice-uncalibrated if the specific rep has no samples in the file
    REQUIRED OUTPUT SHAPE: per Writing Agent's own contract format
    CONFIDENCE REPORTING: required
        │
        ▼
WRITING AGENT (drafts against the spec — does not have HubSpot access,
  does not decide which deals qualify, only executes the brief it's handed)
        │
        ▼
CHIEF ORCHESTRATOR — SYNTHESIZE mode
  Step 2 (Epistemic Uncertainty Mapping): ICP scores clustering around the
    middle (e.g., mostly 3/5) is itself a signal worth surfacing — the
    Revenue/CRM Agent's own logic already flags this, but the Orchestrator's
    synthesis layer is the backstop if that self-check gets skipped under
    time pressure on an automated run
  Step 3 (Self-Correction Pass): cross-check that no drafted message exists
    for a deal the Revenue/CRM Agent excluded for "do not contact" or
    rep-handling reasons — this is a boundary violation that must never reach
    a rep's inbox even as a suggestion, so verify it explicitly rather than
    trusting the upstream exclusion silently propagated correctly
  Step 4 (Progressive Disclosure): the Slack digest gets the compressed
    top-5-actions view; the full chat thread gets the complete pipeline
    snapshot, ICP scoring table, and ready-to-send drafts
  Step 5 (Checkpoint): log which deals were flagged, what confidence, what
    was excluded and why — this is what lets someone audit next week why a
    given deal did or didn't get flagged
```

## Slack digest format (unchanged from the original — proven, keep it)

```
🎯 *Daily Revenue Intelligence — [date]*

*Pipeline:* $[X]M open, [N]x coverage vs. [quarter] target ($[Y]M)
*Status:* [N] stalled (>$[X]), [N] ghosted in last 14d, [N] forecast risks

*Top 5 actions today (ranked by revenue impact):*
1. [Action] — [deal name] ($[amount], [context]) — [rep] — [why now]
2. ...

*Weekly trend:* [one specific insight from historical_trends.json]

Full digest + drafts: [chat thread link]
```

## What changed vs. the original marketing-os version, and why it matters

The original system prompt's "what this agent never does" list already correctly banned CRM writes, sending, and fabricated context — those survive unchanged as the Chief Orchestrator's deterministic constraint boundaries, now enforced at the routing layer instead of relying on one role to self-police both scoring and drafting in the same breath. The concrete improvement is the explicit self-correction check in SYNTHESIZE Step 3: the original workflow trusted that a deal excluded for "do not contact" simply wouldn't get a draft, because the same role did both jobs and presumably wouldn't contradict itself. Splitting scoring from drafting means that assumption is no longer safe by default — so the Orchestrator now verifies it, rather than inheriting it.
