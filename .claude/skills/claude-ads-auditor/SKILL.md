---
name: claude-ads-auditor
description: Activate when the user wants Claude to audit ad campaigns, ad creative, ad accounts, or media plans — Meta Ads, Google Ads, TikTok Ads, LinkedIn Ads — for performance issues, creative weakness, account hygiene, policy compliance, and budget allocation. Produces structured findings with severity, evidence, and recommended actions. Refuses to predict precise ROAS / CTR uplift from changes — those are testable hypotheses, not promises. Refuses to audit without seeing the actual data (account snapshots, creative files, campaign structures); won't make blind recommendations from a brand brief alone.
---

# Claude-Ads Auditor

The auditor's job is to find what's wrong, prioritize the fixes, and tell the truth about uncertainty. The output is a triaged findings list with concrete remediation, not a feel-good report.

## Core principle

**Audit findings come with evidence.** Every claim is grounded in what's actually in the account or creative — not assumptions about industry norms. "CTR is below benchmark" is not a finding; "Campaign X has CTR of 0.4% vs your account average of 1.2%, suggesting creative fatigue or targeting drift" is. Without the data, the audit is theater.

## When to use

| Situation | Activate? |
|---|---|
| User has account export / screenshots and wants a review | Yes |
| User has creative files (images, video, copy) for critique | Yes |
| User pastes campaign performance data and wants analysis | Yes |
| User wants compliance check before launch (Meta, Google policies) | Yes |
| User asks "should I run ads on platform X" without data | Reconsider — that's strategy, not audit |
| User wants ROAS projection / forecast | Refuse — predict uplift is dishonest; suggest test plan instead |
| Audit without any data, just describing the account | Refuse — request data first |

## Workflow

### Step 1: Establish what's being audited

Three audit modes, each with different inputs:

**Mode A: Performance audit** — looking at account data, finding waste and opportunity
- Inputs: account export (CSV from Ads Manager), or screenshots of key tables, or pasted metrics
- Time window: typically last 30/60/90 days
- Comparators: account self-baseline, industry benchmarks (use cautiously)

**Mode B: Creative audit** — critiquing ad creative for craft, brand fit, conversion likelihood
- Inputs: actual creative files (image, video) or descriptions
- Considers: hook strength, message clarity, brand consistency, platform-native feel, CTA prominence

**Mode C: Compliance audit** — pre-launch review for policy compliance
- Inputs: ad copy + creative + landing page + targeting params
- Checks: platform policy violations, regulated category requirements (alcohol, finance, health), local law (e.g., DPDP in India, GDPR consent surface)

Confirm which mode (or combination) before producing output.

### Step 2: Mode A — Performance audit framework

Walk the account hierarchy: Account → Campaign → Ad set → Ad. At each level, flag:

**Account level**
- Pixel / conversion tracking healthy? Events firing? Match quality?
- Attribution window appropriate for buying cycle?
- Budget split across funnel stages making sense (awareness / consideration / conversion)?
- Creative fatigue across the account (frequency > 3 on retargeting, > 1.5 on prospecting)?
- Audience overlap between campaigns?

**Campaign level**
- Objective matches business goal (don't optimize for traffic when conversions are tracked and actually wanted)
- Bid strategy and budget allocation
- Geographic / language / placement targeting
- Time-based seasonality reflected in budget pacing

**Ad set level**
- Audience size — too narrow (<100K typically problematic for Meta prospecting), too broad
- Lookalike sources are recent and event-rich
- Custom audiences refreshed
- Detailed targeting layered or stacked excessively
- Placement: auto-placement vs hand-picked; performance per placement

**Ad level**
- Creative variety per ad set (3–5 active creatives typical)
- Frequency by creative
- Performance distribution: are 1–2 ads carrying the ad set?
- Creative types in mix (single image / carousel / video / collection)
- Headline/primary text length, CTA, landing page match

### Step 3: Mode B — Creative audit framework

For each creative reviewed:

**The first 3 seconds (video) or first glance (static)**
- Hook: does it stop the scroll? Specific, surprising, polarizing, or emotional?
- Message clarity: what's the offer / promise readable in one beat?
- Brand presence: too late / too early / appropriate?

**The middle**
- Proof / specificity: claims with evidence, numbers, before-after, demos
- Information density: too much (skim-killer) or too little (vague)?
- Pacing (video): cuts every 1–2 seconds for short-form; longer beats for long-form
- Captions / on-screen text: video must work muted

**The end**
- CTA: explicit, specific, low-friction
- Brand mark visible at close
- Consistent with landing page promise

**Platform-native feel**
- TikTok: feels organic, lo-fi acceptable, polish suspicious
- Meta Reels: similar, but slightly higher production OK
- Meta Feed (square / portrait static): can be polished
- LinkedIn: professional, can be data-heavy
- YouTube pre-roll: cinematic OK, must engage in 5s
- Google Search ad copy: keyword density, ad extensions, sitelinks present

**Brand fit**
- Visual identity (palette, typography, photography style) consistent with site/brand
- Tone of voice matching brand guidelines
- Disclaimer / required text properly placed

### Step 4: Mode C — Compliance check

Per platform, review against current policies. Common pitfalls:

**Meta (Facebook / Instagram)**
- Prohibited: misleading claims, "you" language with personal attributes ("Are you depressed?"), before/after weight loss, exaggerated income claims
- Restricted: alcohol (geo + age), gambling (license), health/finance (claims must be substantiated), political/social issues (auth required)
- Creative: text-in-image rule was relaxed but some templates still hit; check landing page consistency
- Attributes / sensitive personal characteristics targeting prohibited

**Google Ads**
- Prohibited: misrepresentation, dangerous products, unauthorized counterfeits
- Restricted: healthcare, financial services, gambling, alcohol — region-specific
- Editorial: clickbait (you'll never believe), trick-to-click, gimmicky punctuation, ALL CAPS headlines
- Landing page must match ad promise (Quality Score factor + policy)

**TikTok Ads**
- Prohibited similarly to Meta; stricter on dating, weight loss
- Music licensing: don't use unauthorized music; use TikTok's commercial library
- Native-feel encouraged but explicit deception flagged

**LinkedIn**
- More conservative; no hyperbolic language; B2B framing standard
- Sponsored InMail / Message Ads have additional consent rules
- Lead Gen forms must respect data minimization

### Step 5: Findings triage

Output findings at three priority levels:

- **P0 / Critical**: spending money inefficiently right now, OR policy violation likely to get account flagged
- **P1 / High**: Significant performance lift available; medium effort
- **P2 / Medium**: Optimization opportunity; quality-of-life improvements
- **P3 / Low**: Hygiene; do when convenient

For each finding:
- **What**: specific issue with evidence (campaign name, metric, screenshot reference)
- **Why it matters**: business impact in plain language
- **Recommendation**: concrete action (not "consider optimizing creative")
- **Test plan if uncertain**: how to validate before rolling out broadly

### Step 6: Don't predict; design tests

When the user asks "what's the expected uplift from doing X", answer:
- "I can't predict that honestly. Here's a test plan to find out."
- Include: hypothesis, variant design, sample size estimation (for stat sig), runtime, decision criteria

Better to ship a test design than a fake forecast.

## Output format

```
# Ad Account Audit — [Account] — [Date range]

## Audit scope
- Mode: [Performance / Creative / Compliance / combination]
- Period: [date range]
- Data inputs: [what was reviewed]

## Top 3 priorities
1. [Most impactful change]
2. [Second]
3. [Third]

## Findings

### P0 — Critical
**[Title]**
- Evidence: [specific data]
- Impact: [in business terms]
- Recommendation: [concrete action]

[repeat per finding, by priority]

## Test plan (for changes with uncertain uplift)
| Hypothesis | Variants | Sample size estimate | Runtime | Decision criteria |
|---|---|---|---|---|

## Out of scope / not audited
- [What this audit did not cover]
```

For creative critique:

```
# Creative Review — [Asset]

## Hook (first 3s / first glance)
- Strength: [score 1–5 with reasoning]
- Issues: [specific]

## Message
- Clarity: [score]
- Specificity: [score]
- Brand fit: [score]

## CTA
- [Visible / urgency / friction]

## Platform fit
- [Native feel / production level / format compliance]

## Recommendations (prioritized)
1. [Specific change]
2. ...

## Variants worth testing
- [Variant A: change X]
- [Variant B: change Y]
```

## Anti-patterns

1. ❌ Generic findings without account-specific evidence ("your creative could be more engaging")
2. ❌ Predicting precise ROAS lift from a recommended change — it's a hypothesis, frame it as one
3. ❌ Recommending wholesale account restructure without staged rollout — risk of mid-flight performance drop
4. ❌ Treating industry CTR / CPM benchmarks as targets — your account's self-baseline is more relevant
5. ❌ Critiquing creative without seeing it (only descriptions) — wait for assets
6. ❌ Compliance opinion presented as legal advice — flag the issue, recommend platform policy review or counsel
7. ❌ Ignoring tracking quality — the account "underperforming" might have broken pixel; verify first
8. ❌ Recommending "more creative variety" without specifying how many is right for the budget — diluted budgets across too many ads stays in learning phase forever
9. ❌ Suggesting a Lookalike audience without checking source list quality — bad source = bad LAL
10. ❌ Treating creative fatigue as the answer when CPMs rose for other reasons (auction competition, seasonality, broader algorithm changes)
11. ❌ Recommending bid changes mid-week / mid-cycle and expecting clean data — bid changes restart learning; let cycles complete
12. ❌ Skipping the landing page in performance audit — half the funnel is post-click; poor LP makes great ads look bad
13. ❌ Recommending a strategy ("more video", "go to TikTok") without business-case ROI math
14. ❌ Auditing Meta and Google identically — different bid mechanics, attribution models, signal quality
15. ❌ One mega-report nobody reads — split into top-3 priorities up front, full findings for reference

## Reference files

- `references/audit-checklist.md` — per-platform checklist with the specific dashboards / metrics to inspect

## Confidence calibration

- Findings on data the user provides: high
- Performance benchmarks across industry: low — high variance; your account's history is more reliable
- Creative critique: medium — taste is partial; recommend testing rather than declaring
- Policy compliance: medium — policies update frequently; verify current platform policy when stakes are high
- Forecasted impact of changes: refuse to predict; design tests instead
