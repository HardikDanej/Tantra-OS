---
name: cite-domain-scorer
description: Activate when the user is evaluating sources to cite in marketing content, articles, research reports, or AI-generated content — deciding which domains carry credibility, which are weak, which to avoid, and how to weight competing sources. Produces a CITE score (Credibility, Independence, Transparency, Evidence) per source with reasoning. Refuses to recommend citing low-quality sources to pad references; refuses to launder weak claims through chained citations. Treats citation as the writer's commitment to defend the source if challenged — if you wouldn't defend it, don't cite it.
---

# CITE Domain Scorer

A citation isn't a footnote; it's a vote. The writer is saying: *I trust this source enough to put my credibility behind it.* The scorer's job is helping the user separate sources worth that vote from sources that pad references and reduce the reader's trust.

## Core principle

**Cite sources you'd defend.** If the source is challenged, can the writer explain why it's reliable? If not, the citation is decorative and the credibility cost exceeds the value. Default to fewer citations from stronger sources rather than many from mixed ones.

## When to use

| Situation | Activate? |
|---|---|
| Building a research report / whitepaper | Yes |
| Long-form content with factual claims | Yes |
| AI-generated content where the AI cited sources | Yes — verify everything |
| YMYL content (medical, financial, legal) | Yes — high stakes |
| Auditing existing content for citation quality | Yes |
| Choosing sources for client-facing recommendations | Yes |
| Marketing copy with no factual claims | No — different problem |
| Internal opinion piece without claims to defend | No |

## The CITE framework

Score each candidate source on four axes (1–5 scale):

### C — Credibility
Is the source recognized as authoritative on this topic by people who know the topic?

| Score | Profile |
|---|---|
| 5 | Peer-reviewed journal, major government statistical agency, Nobel-tier researcher's primary work |
| 4 | Established trade publication, recognized industry analyst (Gartner, Forrester for B2B), major newspaper of record |
| 3 | Reputable secondary source, well-known industry blog by recognized expert |
| 2 | Marketing blog from a known company; LinkedIn thought-leadership |
| 1 | Anonymous content farm, low-authority aggregator, AI-generated spam |

### I — Independence
Does the source have a financial / political incentive that aligns with the claim?

| Score | Profile |
|---|---|
| 5 | Independent academic / non-profit; no obvious conflict; topic outside their funder's interest |
| 4 | Mainstream journalism with editorial firewall; analyst with disclosed methodology |
| 3 | Industry publication; some advertiser influence but evidence-based |
| 2 | Vendor-published research about their own category (white papers, "the state of X" reports) |
| 1 | Sponsored content, native advertising, AI-generated SEO content for affiliate links |

A vendor's white paper claiming the vendor's category is growing isn't disqualifying — but the score takes 2 hits and you need to triangulate with independent sources.

### T — Transparency
Does the source show its work? Methodology, sample sizes, dates, raw data?

| Score | Profile |
|---|---|
| 5 | Full methodology, dataset accessible, replication possible |
| 4 | Clear methodology, sample size, time period, definitions |
| 3 | Partial methodology — some details, some opacity |
| 2 | Conclusions only, no method ("we surveyed marketers and found...") |
| 1 | Vague claims, no source, no date, "research shows" with no anchor |

### E — Evidence
Is the claim itself well-supported within the source, or is the source making leaps?

| Score | Profile |
|---|---|
| 5 | Primary data, clearly observed, conclusions match the data |
| 4 | Solid analysis of primary data; reasonable inferences |
| 3 | Synthesis of others' work, mostly accurate |
| 2 | Claim is the source's hot take or thinly-supported opinion |
| 1 | Claim contradicts more authoritative sources, or source itself flags uncertainty as fact |

### Combined score
Sum: 4–20. Rough interpretation:
- **18–20**: cite freely; load-bearing
- **15–17**: cite when relevant; corroborate when central
- **12–14**: cite cautiously; flag the source's nature
- **8–11**: usually don't cite; if used, attribute carefully and note context
- **4–7**: don't cite; if cited, reader will notice and discount

## Workflow

### Step 1: Gather candidate sources

For a given claim, list every source that supports / contradicts / qualifies it. Don't pre-filter — the audit is in the scoring.

### Step 2: Score each on CITE

For each source:
- Note URL, title, author, publisher, date
- Score C, I, T, E with one-line reasoning each
- Combined score
- Classification: cite freely / cite cautiously / don't cite

### Step 3: Triangulate

For load-bearing claims, look for 2–3 independent high-CITE sources that converge. If only one source supports the claim — and it's mid-CITE — note the dependency in the writing or hold the claim weaker than the source asserted.

### Step 4: Recency check

Even high-CITE sources age. For each source ask:
- Is the data current enough for the claim?
- Has more recent work updated or contradicted it?
- For fast-moving fields (AI, regulation, market sizing), 2-year-old data is often stale

### Step 5: Bias check

For each high-influence source on a contested claim:
- Funder / publisher's interests
- Author's known stance / prior work
- Methodology choices that may bias toward outcome

This isn't ad hominem — it's transparency. Note bias; don't necessarily exclude.

### Step 6: Citation strategy

Decide how to use surviving sources:

**Direct citation**: "According to [Source, Year], X."
- Use for primary claims; reader knows where it comes from
- Hyperlink to specific page / paper

**Synthesis citation**: "Multiple analyses ([A], [B], [C]) find X."
- Use when claim is widely agreed; signals robustness
- Each in-text link to the underlying source

**Counter citation**: "While X claims Y, [Source] argues Z."
- Use when there's a meaningful counterargument worth surfacing
- Avoid manufactured controversy where the field has consensus

**Footnote citation**: "...X.[1]"
- Use for technical / academic content where flow matters
- Less effective for SEO and AI-citation surfaces

### Step 7: Anti-laundering check

Watch for citation chains:
- Claim → cited source → which cites → which cites → original (often weaker than the chain implies)
- Trace back to primary; if primary is weak, the chain doesn't strengthen it
- Common pattern: marketing post cites another marketing post that cites an industry survey by a vendor

### Step 8: Document the decisions

For high-stakes content:

```
Source: [URL]
- C: 4 (established trade publication)
- I: 3 (publisher accepts industry sponsorship)
- T: 4 (clear methodology, sample N=500, date Q3 2025)
- E: 4 (primary data, reasonable conclusions)
- Total: 15 — cite, optionally note industry context

Used to support claim: [claim]
Triangulated by: [other sources]
```

Even if the user doesn't publish the documentation, building it sharpens citation quality.

## Source-type reference

| Source type | Typical CITE | Notes |
|---|---|---|
| Peer-reviewed journal article | 17–20 | Highest tier; check for methodology issues, retractions |
| Government statistical agency | 17–19 | High tier; check for political pressure on agencies |
| Major NGO research (Pew, Brookings, etc.) | 16–18 | Reputation varies by NGO; check funding |
| Wall Street Journal, FT, NYT, Reuters | 14–17 | Strong; varies by section (news vs opinion) |
| Trade press (e.g., MarketingWeek, AdAge) | 12–15 | Useful for industry-specific claims; vendor influence varies |
| Major analyst firms (Gartner, Forrester, IDC) | 13–16 | Strong methodology; commercial incentives matter |
| Vendor-published research (whitepapers, "state of") | 7–11 | Use for self-reported data about themselves; not for industry truth |
| Industry blog by recognized expert | 10–14 | Depends on author; check track record |
| Wikipedia | 8–12 | Useful as starting point; cite the underlying source it cites |
| Reddit / forum threads | 5–9 | Useful as voice-of-customer; not a source for factual claims |
| LinkedIn posts / Twitter threads | 4–10 | Author-dependent; usually weaker than equivalent published work |
| AI-generated content | 1–6 | Don't cite as primary source; verify everything |
| Anonymous content farms / SEO blogs | 1–4 | Don't cite |

## Output format

```
# Citation Audit — [Topic / Article] — [Date]

## Claims and sources
| Claim | Source | C | I | T | E | Total | Recommendation |
|---|---|---|---|---|---|---|---|

## Strong sources (cite freely)
- [Source]: [why]

## Conditional sources (cite with framing)
- [Source]: [framing recommendation]

## Sources to drop
- [Source]: [why dropping]

## Triangulation gaps
- [Claim] depends on a single source; suggest finding corroboration

## Recency concerns
- [Source] from [date]; consider updating

## Bias notes
- [Source] has [interest]; note in framing

## Recommended citation strategy
- [Direct / synthesis / counter / footnote per major claim]
```

## Anti-patterns

1. ❌ Padding references with low-CITE sources to seem researched — readers / engines / experts notice
2. ❌ Citing AI-generated articles as if they're primary research
3. ❌ "According to studies..." with no specific citation — empty appeal to authority
4. ❌ Round-numbered statistics without source — almost always fabricated or laundered
5. ❌ Citing your own marketing as if it's neutral evidence
6. ❌ One source carrying load-bearing claim with no triangulation
7. ❌ Burying source-bias on contested claims — disclosure builds trust
8. ❌ Trusting the citation chain without tracing to primary
9. ❌ Citing outdated work in fast-moving fields
10. ❌ Selectively citing sources that agree, ignoring authoritative dissent — confirmation citation
11. ❌ Citing "global average" stats from sources that surveyed only one region — geography matters
12. ❌ Citing experimental / preliminary findings as established fact
13. ❌ Hyperlinking to homepage instead of specific source page — looks shifty
14. ❌ Citing Twitter / LinkedIn thought-leadership as if it's primary research
15. ❌ Removing dates / versions from cited URLs — sources change; reader can't verify
16. ❌ Treating prestigious-sounding domain names as proxy for credibility ("ResearchHub.io" with one paid contributor)

## Confidence calibration

- Source-level CITE scoring: high — patterns are well-established
- Specific score for a given URL: medium — judgment varies; document reasoning
- Whether a claim is well-supported: medium — depends on field consensus
- Future reliability of sources: low — institutions evolve; trusted in 2024 may be questionable in 2026
- Recommendations for niche / non-English sources: lower — corpus knowledge thinner
