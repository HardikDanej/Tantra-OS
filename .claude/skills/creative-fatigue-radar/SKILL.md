---
name: creative-fatigue-radar
description: Activate when the user is monitoring or diagnosing ad creative fatigue across paid social — Meta, TikTok, Google Display, YouTube, LinkedIn — including frequency thresholds, CTR / CPM decay patterns, refresh cadence, and creative volume planning. Produces fatigue assessment with leading indicators (early warning signals before performance crashes) and concrete refresh / rotation plans. Distinguishes true creative fatigue from algorithm shifts, audience saturation, seasonal changes, or budget changes — all of which can mimic fatigue. Refuses to recommend "just produce 10x more creative" without examining whether the existing creative is actually fatigued vs other factors at play.
---

# Creative Fatigue Radar

Creative fatigue is real but routinely misdiagnosed. CPM rose? Maybe fatigue, maybe auction competition, maybe seasonality, maybe iOS attribution hiccup. The radar's job is to separate signal from noise — and prescribe creative refresh only when the data actually says creative.

## Core principle

**Fatigue is a leading-indicator pattern, not a single metric.** Frequency alone isn't fatigue; CTR drop alone isn't fatigue; CPM rise alone isn't fatigue. Fatigue is the pattern across these — and against the right comparators (same audience, same season, same platform mood). The diagnosis precedes the prescription.

## When to use

| Situation | Activate? |
|---|---|
| Ad performance declining; need to diagnose | Yes |
| Planning creative refresh cadence | Yes |
| Building creative production pipeline / volume planning | Yes |
| Always-on campaign needing rotation strategy | Yes |
| Auditing past campaigns for what fatigue looked like | Yes |
| Fresh launch with no creative running yet | No — pre-fatigue; wrong skill |
| User wants creative critique on a single asset | Reconsider — claude-ads-auditor handles that |

## Leading indicators (early warning, before crash)

Watch these in roughly this order — they degrade in this sequence:

### 1. Frequency rising past audience tolerance

Per-platform rough thresholds (these are tendencies, not laws):

| Platform | Audience type | Frequency tolerance |
|---|---|---|
| Meta | Cold prospecting (broad / lookalike) | 1.5–2 per week sustainable; >3 fatigue likely |
| Meta | Retargeting / warm | 3–6 per week sustainable; 7+ fatigue |
| TikTok | Broad audience | Even higher tolerance — TFP variety masks frequency |
| LinkedIn | B2B niche audience | 1–2 / week max |
| YouTube | Pre-roll / display | 4–6 / week tolerated |
| Google Display | Retargeting | 2–4 / week |

These are starting points; observe your specific audience's tolerance curve.

### 2. Engagement rate decay

Specifically:
- **Likes / shares / comments per impression** declining vs the creative's first-week baseline
- **3-second video view rate** dropping (people scrolling past faster)
- **Hover / hold time** declining (engagement time per impression — Meta breakdown)
- **Saves / shares** dropping faster than likes (the strongest signal — engaged response declining first)

Engagement decay precedes click decay; click decay precedes conversion decay.

### 3. CTR (click-through rate) decay

When engagement has been declining and CTR follows, fatigue is well underway. Compare:
- **Same creative, week-over-week** — declining = fatigue likely
- **Same creative across multiple ad sets** — declining everywhere = creative-level fatigue; declining in one = audience-level

### 4. CPM (cost per mille) rising

CPM rise can be:
- **Fatigue** — algorithm sees creative underperforming, reduces auction priority → effectively raises CPM for delivery
- **Auction competition** — more advertisers bidding for the same audience (seasonal: Q4, holiday windows)
- **Seasonality** — natural CPM cycle in your niche
- **Audience saturation** — exhausted the warm audience; cold remainder costs more
- **Algorithm change** — platform shift in delivery model

Don't assume CPM rise = fatigue without checking the alternatives.

### 5. CPA (cost per acquisition) rising

The lagging indicator. By the time CPA has risen visibly, fatigue has been compounding for days/weeks. The radar's job is catching upstream signals before this point.

## Patterns that look like fatigue but aren't

Common misdiagnoses:

**Audience saturation, not creative fatigue**
- New ad creative will help short-term, but audience exhaustion remains
- Solution: expand audience, not just refresh creative

**Seasonality**
- Same campaign performed worse in early January than December
- Solution: don't conclude fatigue from a single seasonal drop; compare year-over-year

**Algorithm change**
- Platform-wide CPM movement, attribution changes (iOS 14, ATT)
- Solution: check competitor / industry signals; if everyone's CPM moved, it's not your creative

**Tracking quality**
- Pixel issue, conversion event misfire, attribution window change
- Solution: validate tracking before declaring fatigue

**Budget / bid changes**
- Increased budget without restarting learning phase = noisy data
- New audience layer added = different audience entirely; not the same creative being fatigued

**Landing page / funnel change**
- Lower CVR from LP changes mimics ad fatigue at the CPA level
- Solution: isolate ad-level metrics from funnel-level

The radar should always ask: *what changed?* before concluding *creative is tired.*

## Workflow

### Step 1: Set up monitoring

For active campaigns, monitor at three levels:

**Account / portfolio level (weekly)**
- Total spend
- Account-wide ROAS / CPA
- Frequency by audience type
- CPM trend

**Campaign / ad-set level (twice weekly)**
- Per-ad-set frequency
- Per-ad-set CTR / CVR / CPA
- Spend pacing

**Ad / creative level (twice weekly during active testing; weekly otherwise)**
- Per-ad CTR, hover/hold, 3s view, completion rate
- Per-ad frequency
- Engagement rate (saves/shares/comments)

### Step 2: Compute fatigue scores

A simple per-ad fatigue score:

```
Fatigue indicators (count how many are present):
[ ] Frequency >2× audience tolerance threshold
[ ] CTR declined >25% from week-1 baseline
[ ] CPM rose >25% from week-1 baseline
[ ] Saves/shares per impression declined >30%
[ ] 3s view rate declined >20% (video)
[ ] CPA rose >40% from week-1 baseline
[ ] Other ads in same set with similar audience perform better

Score:
0–1 indicators: not fatigued
2–3 indicators: early fatigue; refresh planning
4+ indicators: fatigued; rotate or refresh now
```

### Step 3: Diagnose root cause

Before prescribing refresh, ask:

1. Is this isolated to one ad, or pattern across creatives?
2. Did anything else change (audience expansion, budget, landing page)?
3. Is the platform / industry experiencing similar shift?
4. Is tracking healthy?
5. Is seasonality at play?

Only after ruling out alternatives, conclude creative fatigue.

### Step 4: Refresh strategy

If creative fatigue is real, refresh options:

**Variation refresh** (cheapest, fast)
- Same concept, different execution
- New angle, new hook, new visual treatment
- Example: same UGC creator, different opening line and pacing
- Lifespan: extends the concept by ~2–4 weeks typical

**Concept refresh** (mid effort)
- New creative idea entirely
- Different value prop, different format, different testimonial
- Best for: cold prospecting where audience needs novel pattern interrupt
- Lifespan: 4–8 weeks typical

**Creative system refresh** (high effort, lasting)
- New brand creative direction; multiple concepts under a new system
- Production planning for the next quarter
- Best for: scaling brands that need creative volume

**Audience refresh, not creative refresh**
- If diagnosis showed audience saturation: expand the audience, keep working creative
- New lookalike sources, new demographic / interest targeting, new geography

### Step 5: Production volume planning

For sustained programs, budget creative volume:

| Spend tier | Cold prospecting volume | Retargeting volume |
|---|---|---|
| Small ($1K–10K/mo) | 2–4 fresh concepts/mo | 1–2 fresh concepts/mo |
| Mid ($10K–100K/mo) | 6–12 concepts/mo with variants | 3–6 concepts/mo |
| Large ($100K+/mo) | 20+ concepts/mo systematized | 10+/mo |

Volume isn't the answer alone — quality first. But chronically under-producing creates predictable fatigue.

### Step 6: Rotation strategy

For always-on campaigns:
- Maintain 4–6 active creatives per ad set; let algorithm distribute
- Prune underperformers weekly
- Add 1–2 new creatives weekly (cold prospecting)
- Sunset creatives after individual fatigue threshold or after they've underperformed for 7+ days
- Don't over-launch (10 new creatives per week stays in learning forever)

## Output format

```
# Creative Fatigue Audit — [Campaign / Account] — [Date]

## Health summary
- Account fatigue level: [None / Early / Active]
- Specific campaigns / ad sets in fatigue: [list]

## Per-ad fatigue scoring
| Ad | Frequency | CTR trend | CPM trend | Engagement trend | Score | Recommendation |

## Root cause analysis
- Creative fatigue: [evidence]
- Audience saturation: [check]
- Seasonal / industry: [check]
- Tracking / measurement: [check]
- Funnel change: [check]

## Refresh prescription
- Immediate (next 1–2 weeks):
  - [Ad] → [variation / concept / sunset]
- Near-term (this month):
  - [Concept refresh queue]
- System (this quarter):
  - [Production plan]

## Audience action (if relevant)
- [Expansion / new sources / new layers]

## Production volume plan
- [Cadence + budget for fresh creative]

## Monitoring setup
- KPIs to watch
- Alert thresholds
- Review cadence
```

## Anti-patterns

1. ❌ Concluding fatigue from one metric alone — pattern across indicators; otherwise misdiagnosis
2. ❌ Refreshing creative when audience is saturated — wastes production; fix targeting instead
3. ❌ "Just make more creative" without quality direction — volume without quality produces fatigued-from-day-one ads
4. ❌ Sunsetting top performer because frequency hit a threshold — frequency is signal, not law; if performance holds, keep
5. ❌ Adding 20 new creatives at once — keeps ad sets in learning phase indefinitely
6. ❌ Refreshing without change — same concept with new caption; algorithm and audience both notice
7. ❌ Ignoring leading indicators until CPA spikes — fatigue is several weeks compounded by then
8. ❌ Using industry-average frequency thresholds without measuring your audience's specific tolerance
9. ❌ Treating fatigue thresholds the same across cold and warm audiences
10. ❌ Killing video creative based on declining 3s views without checking 50% / 75% / completion rates — sometimes early-views drop while engaged-views hold; the right audience self-selects
11. ❌ Refreshing one platform's creative with content from another (TikTok-style on LinkedIn, vice versa) — platform-mismatched creative fatigues fastest
12. ❌ Production schedules that bunch refreshes (all new in week 1, none for 8 weeks) — uneven fatigue cycle; aim for steady cadence
13. ❌ Outsourcing fatigue management to platform algorithms ("Advantage+ will handle it") — algorithms optimize delivery, not creative production
14. ❌ Ignoring user research / qualitative — fatigued audiences sometimes literally tell you ("I see this ad everywhere"); listen
15. ❌ Treating fatigue as a creative-only problem when it's also a media-mix problem — running same audience too hard regardless of creative

## Confidence calibration

- Pattern recognition (fatigue vs alternatives): high
- Specific frequency thresholds: medium — vary by audience, niche, season
- Refresh recommendations: high when diagnosis is solid
- Predicted lift from refresh: low — test, don't promise
- Production volume sufficient for spend: medium — depends on creative quality, not just count
