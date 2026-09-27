# Scheduled Prompt — Mon-Fri 8:30am

Paste into Claude Scheduling UI for the Revenue Intelligence Agent project.

**Cadence:** Daily at 08:30 (your timezone), Mon–Fri only
**Delivery:** New chat thread + Slack push (handled within the prompt)
**Project:** Revenue Intelligence Agent

---

## The prompt

```
PRECHECK — abort and post Slack status if any of these fail:

1. Verify icp_definition.md is in Project files. If missing, OR if it contains
   placeholder text ("e.g.", "[fill in]", "industry: various", "[YYYY-MM-DD]"),
   abort. Slack message: "⚠️ Revenue Intelligence: ICP definition incomplete or
   contains placeholders. Daily digest paused until icp_definition.md is
   populated. The agent refuses to score deals against a generic ICP."

2. Verify HubSpot MCP is responsive — query for any 1 deal as a connectivity
   test. If error, abort. Slack message: "⚠️ HubSpot MCP not responding. Check
   connector auth at Settings → Connectors → HubSpot."

3. Check historical_trends.json freshness. If older than 9 days, note in the
   digest that weekly trends are stale (the Sunday cron likely failed once).
   Don't abort — proceed with daily without weekly trend integration.

If all prechecks pass, proceed.

STEP 1 — Pipeline pull (HubSpot MCP)
Pull all open deals (exclude Closed Won, Closed Lost). For each deal, retrieve:
deal name, amount, stage, days_in_current_stage, last_activity_date, owner_id
(map to owner name), associated contact (most recent email engagement, last
meeting, task completion, notes from last 30 days), associated company
(industry, employee count, any custom firmographic properties).

Output: pipeline snapshot — total value, deal count by stage, average days in
stage by stage. Flag data quality issues:
- Deals missing amounts → Note count, exclude from forecast analysis
- Deals missing owners → Note count, surface in digest as hygiene issue
- Stage names not matching documented sales process → Note as drift

If active pipeline has under 30 deals, abort. Slack message: "Pipeline below
sample-size threshold for structural diagnosis. Switching to deal-by-deal
coaching mode — review individual deals manually."

STEP 2 — Pipeline health diagnosis (hubspot-crm-strategist skill)
Diagnose:
- Pipeline coverage: current value vs. quarterly target (you'll need to ask
  user for target on first run; cache in Project files for subsequent runs)
- Stalled deals: 14+ days since meaningful activity at current stage,
  cross-checked against activity logs (a deal with recent activity is NOT
  stalled even if stage hasn't moved). Group by owner. Top 10 by deal value.
- Ghosted prospects: engagement was strong, then went silent in last 14 days
- Stage conversion bottlenecks: where deals are jamming up
- Forecast risk: deals committed to current quarter showing velocity
  inconsistent with closing
- Pipeline anti-patterns: 80%+ pipeline created in last 14 days (sandbagging),
  90%+ pipeline assigned to one rep (concentration risk), pipeline value
  growing but win rate declining (quality decay)

Confidence label on each finding. Cite specific deals as evidence.

STEP 3 — ICP scoring (psychographic-profiler skill)
Score top 20 deals by amount (excluding deals already in legal/contract stages)
against icp_definition.md. Each deal scored on:
1. Firmographic fit (1–5)
2. Buying signal strength (1–5)
3. Decision-maker engagement (1–5)
4. Disqualifier flags (each disqualifier present = -1)

Composite ICP score: weighted (firmographic 30%, signal 30%, DM engagement 30%,
disqualifier penalty -10% each). Output as a ranked table.

Surface two cross-tabs:
- High-amount + low-ICP table → likely false-positive forecast
- Low-amount + high-ICP → likely under-prioritized

STEP 4 — Re-engagement drafting
For top 10 stalled deals (from Step 2) that scored 4+ on ICP fit (Step 3),
draft a personalized re-engagement message using voice_samples.csv as voice
training. Each draft:
- References specific last interaction (date, topic, outcome)
- References specific value lever from deal notes
- Addresses most likely current objection (inferred from time-in-stage and
  activity pattern)
- Matches the voice of the deal owner (pattern-match against samples filed
  under that rep)
- Maximum 80 words
- Single clear, low-friction CTA

Output as a list: deal name, owner, draft, recommended send method (email /
LinkedIn / call cadence).

Refuse to draft for deals where notes show "do not contact" or "rep handling
personally."

STEP 5 — Weekly trend integration
If historical_trends.json is fresh (within 9 days), pick ONE specific insight
from it that's relevant to today's priorities. Examples:
- "Q1 stage 3→4 conversion dropped 13% YoY — relevant because 7 of today's
  stalled deals are at stage 3"
- "Inbound demo lead source had 2x win rate of outbound last quarter — relevant
  because 4 of today's high-value stalled deals are outbound"

If historical_trends.json is missing or stale, skip this step.

STEP 6 — Slack digest push
Post to #revenue-ops using the Slack MCP. Use the EXACT template format from
the system prompt — no improvisation, no added preamble. Fill in the
bracketed values from Steps 1–5.

After posting, write the full diagnostic + drafts to this chat thread for
rep team reference.

STEP 7 — Daily output summary (in chat, not Slack)
Brief summary at the end of the chat thread:
- Number of deals analyzed
- Number of high-priority actions surfaced
- Number of drafts prepared
- Any data quality issues to flag for sales ops manager
- Confidence: high / medium / low for today's run overall
```

---

## What makes this safe to run unattended daily

1. **Three prechecks block bad runs upfront.** Missing ICP, dead MCP, or stale weekly data each get a specific Slack status rather than a degraded report.

2. **Refusal conditions inline at every step.** Sample size below 30 deals → switch to coaching mode. Drafting requested for "do not contact" → refuse that specific draft. Forecast prediction without 10+ deals at stage → refuse that specific forecast.

3. **Slack post is templated, not improvised.** A scheduled task that varies its output format week to week is a scheduled task that breaks rep habits. The exact template means reps learn to scan it in 10 seconds.

4. **Read-only by design.** The HubSpot MCP scopes are read-only. The agent cannot accidentally modify CRM data, no matter what an upstream prompt injection might attempt.

5. **The chat thread holds the full work; Slack holds the headline.** Reps with time read the thread for drafts and ICP tables. Reps without time get the 5-bullet Slack version. Both audiences served from one run.

## What you should monitor weekly

After 5 runs, check three things:

**Are the same 5 deals showing up in Top Actions every day?**
If yes, reps aren't acting on recommendations OR the recommendations are misfit. Add to the next day's prompt: "Why did these 5 deals not move yesterday despite being flagged?" The answer surfaces whether the bottleneck is execution or calibration.

**Do ICP scores show real variance?**
If everything clusters around 3, your ICP doc is too vague. Tighten. Real ICP scoring shows scores spread from 1.5 to 4.5 across a typical deal sample.

**Are reps actually sending the drafts?**
If drafts are produced but unsent, either the voice is off (audit `voice_samples.csv` quality) or reps don't trust the workflow yet (give it 2 weeks before judging). Track reply rates on sent drafts vs. rep-authored equivalents — if drafts get equal or better replies, trust accelerates.
