---
name: core-eeat-benchmark
description: Activate when the user wants to audit content (page, site, or specific articles) against Google's E-E-A-T framework — Experience, Expertise, Authoritativeness, Trustworthiness — for SEO quality assessment, especially for YMYL (Your Money or Your Life) topics where E-E-A-T weights heavily. Produces a per-page benchmark with concrete signals checked, gaps flagged, and remediation prioritized. Refuses to treat E-E-A-T as a single ranking factor or to recommend "stuff E-E-A-T signals" as a tactic — it's a quality framework Google uses in human evaluation that informs algorithmic signals; the path to better E-E-A-T is genuinely more authoritative content, not signal-mimicry.
---

# CORE-EEAT Benchmark

E-E-A-T is Google's framework for human raters to evaluate content quality, especially in YMYL areas (medical, financial, legal, safety). The framework feeds back into algorithmic signals — there isn't one "E-E-A-T score." The audit's job is to identify whether content credibly demonstrates Experience, Expertise, Authoritativeness, and Trustworthiness, then close gaps where it doesn't.

## Core principle

**E-E-A-T is earned, not asserted.** A bio claiming "20 years of expertise" doesn't move E-E-A-T; verifiable credentials, original work, citations from authoritative peers, and demonstrated experience do. The audit checks for evidence, not claims.

## When to use

| Situation | Activate? |
|---|---|
| Health / medical content site | Yes — high YMYL weighting |
| Financial advice / investment / insurance content | Yes — high YMYL weighting |
| Legal information | Yes — YMYL |
| Parenting / safety / nutrition | Yes — YMYL-adjacent |
| News / current events | Yes |
| Reviews / recommendations site | Yes — Experience matters specifically |
| E-commerce product descriptions | Lower priority — but still helpful |
| Pure entertainment / opinion | Lower priority |
| Internal tool docs | No — different use case |

## The four dimensions

### Experience (the recently-added E)
First-hand experience with the topic. Has the writer used the product, visited the place, lived through the situation? For reviews, this dimension is most important.

**Signals**:
- Original photography (not stock) of the product / place / event
- Specific details only first-hand experience produces (the surprising thing, the friction, the unexpected)
- Date of experience documented
- Repeated engagement signals (multiple visits, long-term use, follow-up updates)
- Writer's relationship to the topic disclosed

**Anti-signals**:
- Stock images
- Generic descriptions matching marketing copy
- No specific details that distinguish from competitor reviews
- "The product is great. It has features X, Y, Z." (lifted from product page)

### Expertise
Knowledge / skill / training in the subject. Most relevant for technical, medical, financial, legal content.

**Signals**:
- Author bio with relevant credentials, training, role
- Linked author page with publication history
- Education / certifications listed (with verifiable institutions)
- Body of work in the topic (other articles, books, talks)
- Industry recognition (awards, board positions, affiliations)
- Domain-specific accuracy (correct terminology, current consensus, nuance)

**Anti-signals**:
- No author byline
- Generic "Editorial Team" byline with no individuals
- Bio that asserts expertise without specifics ("decades of experience")
- Errors / outdated information
- Surface-level treatment lacking nuance an expert would include

### Authoritativeness
Recognition by others as a go-to source. Institutional and graph-based, more than individual.

**Signals**:
- Inbound links from other authoritative sources in the topic
- Cited by Wikipedia / news / industry publications
- Author quoted / cited in third-party articles
- Site appears in topical knowledge graphs
- Media mentions ("As featured in X")
- Original research that gets cited

**Anti-signals**:
- Thin backlink profile, especially from low-authority sources
- Site / author not referenced anywhere outside their own properties
- No news / press / industry mentions

### Trustworthiness
The most important of the four (per Google's recent guidance). Whether the content can be trusted on its face.

**Signals**:
- Accuracy of factual claims (verifiable)
- Citations to authoritative primary sources
- Transparency about authorship, ownership, methodology
- Clear distinction between editorial and sponsored content
- Easy contact / ownership info
- Privacy policy, terms, security indicators (HTTPS)
- Updated dates on time-sensitive content
- Corrections policy when wrong

**Anti-signals**:
- Factual errors
- Uncited claims, especially YMYL
- Hidden ownership / no contact info
- Affiliate disclosure missing where relevant
- Publish date but no update date on stale content
- Misleading or clickbait headlines vs body

## Workflow

### Step 1: Establish YMYL classification

Is the content YMYL?
- **Yes** if: medical / health, financial / investment, legal, civic / political, safety, child-related, major life decisions
- **Partial** if: nutrition / fitness, parenting (informational not medical), insurance / consumer protection, news / current events
- **No** if: entertainment, recipes (mostly), travel destinations (mostly), product reviews of low-stakes items

YMYL classification raises the bar — minor E-E-A-T gaps that wouldn't matter on a non-YMYL page can sink a YMYL page.

### Step 2: Audit each dimension per page

For each priority page, check signals systematically. Use the rubric:

| Dimension | Strong signal? | Weak signal? | Anti-signal? |
|---|---|---|---|
| Experience | [list] | [list] | [list] |
| Expertise | | | |
| Authoritativeness | | | |
| Trustworthiness | | | |

Score 0–3 per dimension. Total 0–12 per page.

### Step 3: Site-level signals

Beyond per-page, check site-level:
- About page that discloses team, mission, ownership
- Editorial standards / methodology page (especially for review sites)
- Author pages with bios linking to all their content
- Contact / company info easy to find
- Privacy policy, terms
- HTTPS, valid SSL
- No malware / safe browsing flags
- Reasonable ad load (overwhelming ads is an anti-signal)
- No deceptive layout (ads disguised as content)

### Step 4: Compare to top-ranking peers

For each priority query:
- Search the query on Google
- Look at the top 5 organic results (excluding ads, AI Overviews, knowledge panels)
- Audit each for the same E-E-A-T signals
- Identify what they have that the user's site doesn't

This comparative gap is the most actionable output. Closing it is concrete work.

### Step 5: Triage findings

**P0 — Trust gaps**: missing author info, missing dates, factual errors, misleading content. Highest-priority because trust is the most weighted dimension.

**P1 — Expertise gaps in YMYL content**: medical / financial content without credentialed authors or expert review.

**P2 — Experience gaps in review content**: reviews lacking original photography, specific detail, dates of use.

**P3 — Authoritativeness gaps**: thin backlink profile, lack of media mentions. Slowest to fix; longer game.

### Step 6: Remediation plan

For each gap, concrete action:
- **Add author bios**: with credentials, photo, link to author page, link to other content
- **Add expert review**: medically reviewed by Dr. X (with link to verifiable Dr. X)
- **Add dates**: publish date + last reviewed/updated date
- **Add citations**: link to primary sources, especially for claims
- **Add about / methodology page**: explain how the site evaluates / produces content
- **Add original research / data**: most defensible authoritativeness move
- **Earn media coverage**: PR work; long timeframe

## Output format

```
# E-E-A-T Audit — [Site/Page] — [Date]

## YMYL classification
[Yes / Partial / No, with reasoning]

## Site-level scorecard
| Signal | Status | Priority to fix |
|---|---|---|

## Per-page scorecard
### [Page]
- Experience: [score, evidence]
- Expertise: [score, evidence]
- Authoritativeness: [score, evidence]
- Trustworthiness: [score, evidence]
- Top gaps: [list]
- Top peer (URL): [what they have we don't]

## Top remediation priorities
1. [Specific action]
2. ...

## Long-game work (3–12 month)
- [Authority-building, original research, media earned]

## Out of scope
- [What this audit didn't cover]
```

## Anti-patterns

1. ❌ Treating E-E-A-T as one number / one ranking factor — it's a quality framework, not a metric
2. ❌ Adding fake credentials / borrowed authority signals — explicit Google quality rater anti-pattern; can backfire badly
3. ❌ Generic "Reviewed by our editorial team" without naming individuals — empty signal
4. ❌ Author bios full of buzzwords ("passionate about helping people achieve their best lives") with no verifiable specifics
5. ❌ Adding a "Last updated" date without actually updating — engines compare content hash; demotes for staleness fakery
6. ❌ Citing your own previous content as authority — circular; doesn't count
7. ❌ Citing low-quality sources to seem cited — the inbound graph from low-authority sources doesn't help
8. ❌ Treating affiliate / paid content as editorial without disclosure — trust killer
9. ❌ "Expertise" signaling on YMYL written by non-experts — misleading and risky
10. ❌ Bulk-generating author pages for ghost-written content — pages have no presence elsewhere; thin and detectable
11. ❌ Skipping the peer comparison — without seeing what the top results have, gap analysis is guesswork
12. ❌ Ignoring negative E-E-A-T signals (factual errors, misleading claims, hidden ownership) while adding positive — the negative drag dominates
13. ❌ Trying to fix authoritativeness in 30 days — link earning and media coverage are 6–18 month work; budget accordingly
14. ❌ Conflating user-generated reviews with E-E-A-T — UGC can support trust signals but doesn't substitute for first-party expertise

## Confidence calibration

- Per-page signal audit: high
- Whether specific change will move ranking: low — Google's algorithmic interpretation is opaque; correlate with rank movement, don't predict
- YMYL classification: medium — borderline cases exist; err on the strict side
- Authority gap remediation timeline: low — depends on niche, current authority, opportunity availability
