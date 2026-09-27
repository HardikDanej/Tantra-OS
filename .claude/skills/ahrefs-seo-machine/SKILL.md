---
name: ahrefs-seo-machine
description: Activate when the user is doing SEO work using Ahrefs — keyword research, content gap analysis, backlink analysis, rank tracking, competitor audits, technical site audits, internal linking strategy. Produces specific Ahrefs workflows (which reports to run, which filters, what to look for) rather than generic SEO advice. Refuses to recommend tactics that violate Google's spam policies (PBNs, link buying networks, mass-AI content, doorway pages). Refuses to forecast specific traffic outcomes from work — outcomes are testable, not promised. Treats Ahrefs as a research tool whose value is the analysis it enables, not the data it shows; the deliverable is decisions, not screenshots.
---

# Ahrefs SEO Machine

The skill's deliverable is what to do, grounded in what Ahrefs shows. Most Ahrefs reports become wall art — pulled, screenshotted, never acted on. The discipline is using each report to answer a specific question and turning the answer into a content / link / technical decision.

## Core principle

**Reports answer questions; questions drive decisions.** Don't pull Ahrefs reports without a question in mind, and don't end an Ahrefs session without a decision logged. The data is plentiful; the bottleneck is connecting it to action.

## When to use

| Situation | Activate? |
|---|---|
| Keyword research for content strategy | Yes |
| Content gap analysis vs competitors | Yes |
| Backlink audit / link building strategy | Yes |
| Rank tracking setup and analysis | Yes |
| Technical SEO audit (Site Audit module) | Yes |
| Topical authority / cluster planning | Yes |
| Competitor SEO benchmarking | Yes |
| Identifying underperforming pages for refresh | Yes |
| One-off "what's the search volume for X" | Reconsider — use the tool directly |
| Link buying / PBN strategy | Refuse |

## Workflow by question

### Q1: What keywords should we target?

**Steps**
1. **Seed list** — start with 5–15 seed terms drawn from the user's category, product, customer language
2. **Keywords Explorer** for each seed → expand via:
   - **Matching terms** (broad)
   - **Related terms** (semantic)
   - **Search suggestions** (autocomplete)
   - **Questions** (intent-rich)
3. **Filter** to a workable set:
   - Volume: depends on niche; 100–10,000 typical for content; lower for niche B2B
   - Keyword Difficulty (KD): start with KD < domain's typical achievable level (rough rule: half the site's Domain Rating)
   - Intent: filter for informational + commercial; deprioritize navigational + branded-other
   - SERP features present: featured snippet / People Also Ask = opportunity
4. **Cluster** by topic:
   - Manual: similar pages = same cluster
   - Or use Ahrefs' Parent Topic to group
5. **Prioritize**:
   - High volume × achievable KD × commercial intent = priority 1
   - Mid volume × low KD × commercial intent = priority 2 (quick wins)
   - High volume × high KD = long-game; build supporting cluster first

**Output: keyword priority list + topical clusters**

### Q2: What content gaps exist vs competitors?

**Steps**
1. Identify 3–5 direct competitors (organic SERP overlap, not just brand competitors)
2. **Content Gap** report: your domain vs theirs
3. Filter to:
   - Keywords where ≥2 competitors rank in top 10 and you don't
   - Volume threshold above the noise floor
   - Intent matches your content strategy
4. Cull keywords that don't fit your audience even if competitors rank
5. Group remaining gaps into content briefs

**Output: content gap list with priority and brief direction**

### Q3: What's our backlink situation?

**Steps**
1. **Site Explorer** → Backlinks
   - Filter to dofollow, English (or relevant language), not subdomain spam
2. **Anchor texts**:
   - Branded vs non-branded ratio (≥60% branded healthy for most sites)
   - Over-optimized exact-match anchor on commercial pages = risk
3. **Linking domains** (referring domains) growth over time:
   - Steady growth = healthy; sudden spikes need explanation (PR / link buying / negative SEO?)
4. **Domain Rating distribution** of inbound links:
   - Pyramid shape healthy (many low DR, few high DR)
   - Inverted (only high-DR links, suspicious) or all low-DR (low-quality acquisition) both problematic
5. **Lost backlinks** report:
   - Recent losses worth recovery outreach if from authoritative sources

**Output: backlink health summary + recovery / new link priorities**

### Q4: Where are we losing rankings?

**Steps**
1. **Rank Tracker** with priority keywords loaded
2. Filter for keywords that:
   - Lost positions in last 30/90 days
   - Were on page 1, now page 2–3 (recoverable)
   - Have meaningful volume
3. For each, **Site Explorer → Top Pages**:
   - When did the page last get updated?
   - What's the current SERP look like — new competitor? Featured snippet they took? Algorithm change?
4. **Content Explorer** for the keyword:
   - Top-ranking pages — what they have that yours doesn't (length, schema, freshness, multimedia, depth)

**Output: refresh / update priority list with specific gap-to-close per page**

### Q5: What backlinks should we pursue?

**Steps**
1. **Site Explorer** on top 3 competitors → Backlinks
2. **Best Pages by links** — which of their pages attract the most links?
3. For each high-link page, ask: do we have an equivalent (or better)?
   - Yes → outreach to sites linking to theirs, propose ours as alternative / addition
   - No → consider creating equivalent content (resource, study, calculator, list)
4. **Link Intersect**: domains linking to multiple competitors but not to you = warmest prospect list
5. **Broken Link Building**: Ahrefs' broken backlinks report on competitors — find their dead links pointed at by sites; offer your live page as replacement

**Output: prioritized outreach list with angle per prospect**

### Q6: What technical SEO issues are blocking?

**Steps**
1. **Site Audit** module — full crawl
2. Triage by severity:
   - **Errors** (broken pages, indexability blocks, broken canonicals) → fix immediately
   - **Warnings** (missing meta, slow pages, large CLS) → fix systematically
   - **Notices** (informational) → watch
3. For high-impact issues:
   - Crawl errors / 404s on important pages
   - Indexability problems (noindex on pages that should rank)
   - Canonical issues (self-pointing or pointing to wrong URL)
   - JavaScript rendering — content visible to crawlers?
   - Duplicate content
   - Site speed / Core Web Vitals
4. Track issue resolution over time — Site Audit re-crawls, watch trend

**Output: technical issue list, prioritized by impact, with owner / fix instruction**

### Q7: What's our topical authority?

**Steps**
1. **Site Explorer → Top Pages** — what topics are we already winning?
2. **Site Explorer → Organic Keywords** filtered by parent topic
3. Cluster the keywords / pages we rank for
4. Identify topical strongholds (clusters where we rank multiple top-10 results) vs weak topics (one-off rankings)
5. For strongholds: deepen with new pages around the cluster
6. For weak topics: either commit (build the cluster) or deprioritize (don't keep one-off pages floating)

**Output: topical cluster map with consolidate/expand/cull recommendations**

## Combining the answers into a strategy

These question-driven workflows feed into:

- **Content roadmap**: from Q1, Q2, Q4, Q7
- **Link building plan**: from Q3, Q5
- **Technical roadmap**: from Q6
- **Refresh schedule**: from Q4, Q7

Pull all together monthly; don't try to update everything weekly.

## Output format

```
# SEO Strategy — [Domain] — [Date]

## Domain snapshot (Ahrefs)
- DR: [n]
- Backlinks: [n] from [n] domains
- Organic keywords: [n] ranking, [n] in top 10
- Organic traffic estimate: [n/mo] (Ahrefs estimate; understate)
- Top performing pages: [list with KW]

## Keyword strategy
- Tier 1 (priority targets): [list with volume, KD, intent]
- Tier 2 (quick wins): [list]
- Tier 3 (long-game cluster builders): [list]

## Content gaps vs competitors
| Keyword | Volume | KD | Competitors ranking | Brief direction |

## Backlink position
- Health summary
- Recovery list (lost backlinks worth pursuing)
- Acquisition list (Link Intersect, broken link building)

## Technical issues
- P0: [errors blocking ranking]
- P1: [warnings to address systematically]

## Refresh queue
| Page | Current rank | Issue | Action |

## Reporting cadence
- Weekly: [what to watch]
- Monthly: [what to review]
- Quarterly: [strategy retro]

## Out of scope
- [What this strategy doesn't cover]
```

## Anti-patterns

1. ❌ Forecasting "we'll get X traffic from this" — outcomes are testable, not promised; show ranges or refuse
2. ❌ Targeting keywords with no business connection — high-volume vanity that doesn't convert
3. ❌ Buying links / using PBNs / private link schemes — Google penalty risk; long-term ranking loss
4. ❌ Mass-generating AI articles to "build topical authority" — Helpful Content updates penalize this
5. ❌ Chasing every Ahrefs notice — diminishing returns; triage by impact
6. ❌ Ignoring search intent — ranking #1 for a query whose users don't want what you offer = traffic without conversion
7. ❌ Rebuilding existing pages from scratch when a refresh would do — loses page age, links, equity
8. ❌ Using Domain Rating as a quality proxy in isolation — DR is link-graph based; doesn't measure content quality
9. ❌ Tracking every keyword in Rank Tracker — track strategically; cull noise
10. ❌ Reading SERP features as static — they move; verify current state when targeting
11. ❌ "Skyscraper" tactic without genuine reason for the existing audience to switch — longer ≠ better
12. ❌ Outreach for links from irrelevant sites — low conversion + dilutes link profile if achieved
13. ❌ Ignoring brand strength — high-DR domains can rank thin content; mid-DR domains need more depth to compete
14. ❌ Treating Ahrefs estimates as ground truth — they're estimates from sample; use Search Console + analytics for actual
15. ❌ Optimizing for outdated SERP layouts — AI Overviews, featured snippets, knowledge panels reshape the click economy; volume ≠ traffic the way it used to
16. ❌ One-time SEO project then dropping — SEO is ongoing; budget for sustained work or don't start

## Confidence calibration

- Ahrefs report interpretation: high
- Specific keyword traffic forecast: low — Ahrefs estimates have wide error bars
- Whether a backlink target will convert: low — outreach response rates 5–20% typical
- Whether content refresh will recover ranking: medium — depends on what changed in the SERP
- Algorithmic specifics (which signal carried weight): low — Google doesn't disclose; correlation isn't causation
