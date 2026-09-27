# Scheduled Prompt — Mondays 8:00am

Paste this into the Claude Scheduling UI for the Campaign Intelligence project.

**Cadence:** Weekly, Monday 08:00 (your timezone)
**Delivery:** New chat thread + Slack push (handled within the prompt)
**Project:** Campaign Intelligence

---

## The prompt

```
The weekly_unified.csv file in this Project's files contains the last 14 days of ad performance data from Meta, Google Ads, and TikTok, generated automatically by the ad_data_pull.py script Sunday night.

If the file's modification timestamp is older than 36 hours, abort and post to #growth-weekly: "⚠️ Campaign Intelligence: stale data detected. Sunday night cron job likely failed. Check ~/marketing-os/01-campaign-intelligence/output/cron.log on the data pull machine."

Otherwise, proceed with the weekly diagnostic in this exact sequence:

STEP 1 — Validate the data
Use code interpreter to load weekly_unified.csv. Output: row count, date range, total spend by platform, ad count by platform. Flag any data quality issues (rows with spend > 0 and conversions = 0, ads under 1,000 impressions, missing values in required columns). If data quality issues affect more than 10% of spend, abort and post to Slack with details.

STEP 2 — Compute week-over-week deltas
Split the 14-day window into "current week" (last 7 days) and "prior week" (days 8–14). Compute deltas for: spend, impressions, clicks, conversions, revenue, ROAS, frequency, CTR, CPM. Aggregate at platform level and ad level.

STEP 3 — Run creative-fatigue-radar
Apply the skill to every ad with 1,000+ impressions in the current week. Verdict per ad: true_fatigue, ambiguous, not_fatigued, insufficient_data. Require at least two corroborating signals before flagging true_fatigue. Output as a markdown table sorted by spend descending. Confidence on each verdict.

STEP 4 — Run claude-ads-auditor
Audit account structure across all three platforms. Output 5–15 findings ranked by projected impact. Each finding: issue, evidence in the data, recommended fix, confidence. Skip findings you cannot directly verify from the data.

STEP 5 — Run psychographic-profiler
Refresh persona model using current-week conversion data. Output top 3 converting segments with: defining values, vocabulary patterns, share of conversions, week-over-week share change.

STEP 6 — Generate creative briefs
For each ad flagged true_fatigue in Step 3, run viral-hook-generator + brand-voice-extractor in collaboration to produce 5 creative briefs. Each brief: 3 hook variants, angle, format, platform-specific treatment, target persona from Step 5, and the rationale linking the brief to why the original creative fatigued.

STEP 7 — Assemble and push
Assemble the full weekly report in the structure defined in the system prompt. Then use the Slack connector to post the executive summary + prioritized action list to #growth-weekly. The full report stays in this chat thread for reference.

The Slack post format (post this verbatim, fill in the bracketed values):

🎯 **Weekly Campaign Intelligence — [date]**

**Pipeline:** $[total spend] last 7 days, blended ROAS [ratio]x ([+/-X.X] WoW)
**Fatigue verdict:** [N] true fatigue, [N] ambiguous, [N] healthy

**Top 5 actions this week:**
1. [action] — [deal/ad name] — [owner role] — [why now]
2. [action] — [...]
3. [...]
4. [...]
5. [...]

Full report: [paste the URL of this chat thread]

Refusal conditions (abort and post a status message instead of the report):
- Data file older than 36 hours → "stale data" message
- Spend under $5,000 across the 14-day window → "insufficient spend for diagnosis" message
- More than 40% of ads flagged true_fatigue → "fatigue rate suspiciously high — possible measurement artifact, manual review needed" message

Do not produce the report if any refusal condition triggers. Post the status message instead.
```

---

## Why this works on a schedule

Three design choices make this safe to run unattended:

1. **Freshness check first.** If the cron job failed Sunday night, the prompt detects the stale data and posts a clear failure message instead of analyzing 2-week-old numbers and pretending the report is current.

2. **Refusal conditions baked in.** The "more than 40% fatigue" check catches the most common skill miscalibration — when the fatigue radar over-triggers, the prompt notices and asks for human review rather than firing 47 false-positive recommendations into Slack.

3. **Slack post is templated, not improvised.** Schedulers fail when Claude decides to "be helpful" and varies the format week to week. The verbatim template constrains output to a parseable shape your team learns to read in 10 seconds.
