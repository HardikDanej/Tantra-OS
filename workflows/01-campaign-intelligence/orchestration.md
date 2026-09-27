# Workflow 01: Campaign Intelligence — Agent-Orchestrated Edition

**Change from the original marketing-os version:** this Project no longer holds five skills directly wired to a single system prompt. It now dispatches through the **Chief Marketing Orchestrator**, which routes the diagnostic work to the **Ads/Paid-Media Agent** and any drafting need to the **Writing/Content Production Agent**. The underlying skills (`creative-fatigue-radar`, `claude-ads-auditor`, `psychographic-profiler`, `viral-hook-generator`, `brand-voice-extractor`) haven't moved — they now live inside the Ads Agent's toolkit, called by that agent, not by this Project's system prompt directly.

## What triggers this workflow

Same as before: `ad_data_pull.py` runs Sunday 11pm via cron, Cowork lands `weekly_unified.csv` in Project files, a scheduled task fires Monday 8am.

**Activation:** Tantra's agents are only dispatched once Tantra is active, so the scheduled prompt that fires this workflow starts with the wake word `mk ` (e.g. "mk run the weekly campaign intelligence diagnostic"); a scheduled or headless run may alternatively set `TANTRA_ACTIVE=1` in its environment.

## The dispatch sequence

```
Scheduled trigger (Monday 8am)
        │
        ▼
CHIEF ORCHESTRATOR — DISPATCH mode
  Step 1 (Gatekeeper): check weekly_unified.csv freshness. If older than 36 hours,
    do not dispatch — post directly to #growth-weekly: "⚠️ stale data detected,
    check cron.log" and stop. This is a data-integrity gate, not a clarifying
    question — it fires automatically, no consolidated question needed.
  Step 2 (Decomposition): one workstream — full diagnostic — dispatched to Ads Agent.
    No dependency on Marketing Strategist Agent's brand-foundation outputs is
    hard-required here, but if voice_system.json exists from a prior Brand Launch
    Suite run, attach it as an input; if not, proceed and let the Ads Agent's own
    GAPS report flag briefs as voice-ungrounded.
  Step 3 (Contract): 
    AGENT: Ads/Paid-Media Agent
    OBJECTIVE: full weekly diagnostic — data validation, fatigue verdict, account
      audit, persona refresh, creative briefs for fatigued ads
    INPUTS: weekly_unified.csv, voice_system.json (if available)
    CONSTRAINTS: fatigue verdict requires 2+ corroborating signals; refuse audit
      findings not directly evidenced in the data; refuse briefs for non-fatigued ads
    REQUIRED OUTPUT SHAPE: per the Ads Agent's own contract format
    CONFIDENCE REPORTING: required, per finding
        │
        ▼
ADS / PAID-MEDIA AGENT (runs its own 5-step internal sequence:
  data validation → fatigue diagnosis → account audit → persona refresh →
  creative briefing — see ads-agent.md for the full logic)
        │
        ▼
CHIEF ORCHESTRATOR — SYNTHESIZE mode
  Step 1: collect Ads Agent output + confidence tiers
  Step 2 (Epistemic Uncertainty Mapping): if fatigue verdicts are majority
    low-confidence, or if >40% of ads returned true_fatigue (a known
    miscalibration signal), escalate rather than present the report as final —
    post a review-needed message instead of the full report
  Step 3 (Self-Correction Pass): check that no brief was generated for a
    non-fatigued ad, and that the account-audit findings don't contradict the
    fatigue verdicts (e.g., an audit finding recommending more spend on an ad
    the fatigue step flagged true_fatigue)
  Step 4 (Progressive Disclosure): assemble the report in the structure below;
    Slack gets the compressed executive summary, the full chat thread gets
    everything
  Step 5 (Checkpoint): log what ran, what confidence came back, what (if
    anything) was escalated — so next Monday's run can reference this week's
    baseline
```

## Report structure (unchanged from the original — this format is proven, keep it)

```
# Weekly Campaign Intelligence — [date]

## Executive Summary
[5 bullets max, ranked by revenue impact, each with the owner role in brackets]

## Account Health Snapshot
[spend, ROAS, week-over-week deltas, by platform]

## Creative Fatigue Verdict
[table: ad_name | platform | spend | verdict | signals | confidence]

## Account Audit Findings
[5–15 findings, ranked by impact, each: issue / evidence / fix / confidence]

## Audience Persona Refresh
[top 3 converting segments with values, vocabulary, share of conversions]

## Creative Briefs
[5 briefs per fatigued ad, each with hook variants, angle, format, target persona]

## Prioritized Action List
[top 5 actions ranked by revenue impact, each with owner role]
```

Slack push = Executive Summary + Prioritized Action List only, Slack-formatted, no markdown headers.

## Refusal / escalation conditions (now enforced across two layers, not one)

| Condition | Who catches it | Action |
|---|---|---|
| Data file older than 36 hours | Chief Orchestrator, DISPATCH Step 1 | Abort before dispatch, post stale-data message |
| Under 7 days of data / spend under $5k/week / campaign-level-only data | Ads Agent's own refusal checks | Ads Agent refuses the relevant sub-step, reports the gap |
| >40% of ads flagged true_fatigue | Chief Orchestrator, SYNTHESIZE Step 2 | Escalate instead of presenting as final — this is exactly the kind of aggregate pattern a single agent working in isolation might not flag about its own output, which is why the Orchestrator's synthesis-layer check matters |
| Brief generated for a non-fatigued ad | Chief Orchestrator, SYNTHESIZE Step 3 (self-correction) | Strip the brief, flag the Ads Agent's own violation of its refusal rule before it reaches Slack |

## What changed vs. the original marketing-os version, and why it matters

The original system prompt made one agent responsible for diagnosis, auditing, persona work, AND creative ideation, with no independent check on its own output before it shipped to Slack. The new version keeps the exact same diagnostic logic (nothing about *how* fatigue is diagnosed changed) but adds a synthesis-layer review that specifically catches the failure mode the original workflow's own troubleshooting section warned about ("Claude flags every ad as fatigued") — now that's an automatic escalation instead of something you discover by reading a bad report Monday morning.
