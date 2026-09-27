---
name: geo-aeo-optimizer
description: Activate when the user wants their content (web pages, articles, product pages, documentation) to be cited or referenced by generative answer engines — ChatGPT search, Perplexity, Claude, Google AI Overviews, Bing Copilot, You.com — rather than (or in addition to) ranking in classical Google search. Produces content structures, on-page changes, and measurement frameworks specifically for AI citation surfaces. Distinguishes GEO (Generative Engine Optimization) from classical SEO — overlapping but not identical. Refuses to recommend "stuff content with FAQ schema and pray" as a strategy; refuses prompt-injection-style invisible text targeting LLM crawlers. Treats AI citation as earned by content depth, structural clarity, source authority, and citability — not by tricks.
---

# GEO / AEO Optimizer

GEO (Generative Engine Optimization) and AEO (Answer Engine Optimization) are the discipline of getting your content surfaced as the cited source when someone asks ChatGPT / Perplexity / Claude / Gemini a question your content answers. The output is citation in the answer (with link/attribution), not necessarily a click — though clicks follow when the citation is compelling.

## Core principle

Answer engines synthesize answers from a small set of sources per query — typically 3–8 cited URLs. Being one of them depends on: (a) the engine's crawler / index discovering your page, (b) the page being topically authoritative in the engine's retrieval ranking, (c) the page being **citable** (specific facts, structured, attributable), (d) the source being trusted (domain authority, freshness, alignment with the engine's preference signals). You optimize all four axes; tricks don't work.

## When to use

| Situation | Activate? |
|---|---|
| Brand wants to be cited in ChatGPT / Perplexity answers | Yes |
| Existing content ranking on Google but not in AI Overviews | Yes |
| New content strategy where AI surfaces are explicit goal | Yes |
| B2B SaaS docs that should surface for "how do I" queries | Yes |
| E-commerce product pages targeting "best [thing] for [use case]" | Yes |
| Local SEO (geographic intent) | Reconsider — classical local SEO still dominates for these |
| Pure brand awareness with no informational query intent | No — different tooling |
| Asked to "trick" an AI into citing | Refuse |

## How AI engines actually retrieve

Different engines use different stacks. Approximate model:

| Engine | Retrieval | Signals |
|---|---|---|
| ChatGPT (Search) | Bing index + OpenAI's own crawler | Bing rank, freshness, schema, URL structure |
| Perplexity | Hybrid: Google + Bing + own crawler + curated indices | Source credibility, topical clusters, citation graphs |
| Claude (search-enabled) | Anthropic's web search infrastructure | Topical relevance, source authority |
| Google AI Overviews | Google's main index | Classical SEO + featured-snippet-style signals |
| Bing Copilot | Bing index | Bing rank + freshness |

**Practical implication**: ranking on Bing matters for ChatGPT. Ranking on Google matters for AI Overviews. Most paid SEO tools focus on Google; if AI citation matters, monitor Bing rank too.

## Workflow

### Step 1: Identify citation-worthy queries

Not every page needs GEO. Pages that benefit:
- Definitional queries: "What is X?"
- Comparative: "X vs Y"
- How-to: "How to do X"
- List queries: "Best X for Y"
- Recommendation: "Should I X?"

Pages that don't benefit much:
- Transactional / branded ("buy [exact product name]")
- Navigational ("[brand name] login")
- Real-time data unless you're the source (stock prices, weather)

For each priority query, ask: *what would a useful AI answer look like, and would my page be one of the 3–8 sources cited?* If no, the page needs work or doesn't belong on the GEO list.

### Step 2: Audit current citation surface

For each priority query:
1. Run it in ChatGPT (Search), Perplexity, Claude, Gemini, Bing Copilot
2. Note the cited sources for each engine
3. See if your domain is cited; if not, who is and why
4. Note answer structure — what's the synthesized answer, what specific facts/numbers come from where

This is manual but irreplaceable. Tooling (Profound, AthenaHQ, BrightEdge AI Tracker, etc.) automates monitoring once you know what to track, but the initial audit is hand-driven.

### Step 3: Make pages citable

Citability means the page contains discrete, attributable, factually grounded chunks the engine can lift. Common patterns:

**Original data and statistics**
- "We surveyed 1,200 marketing leaders in Q1 2026" — engines love proprietary data because it's only sourceable from you
- Cite your methodology so the answer can include "according to a 2026 [Brand] survey of 1,200 marketers"

**Definitions in the first 100 words**
- Open with a clear, quotable definition: "X is [concise definition]." Engines often lift the lead sentence as the synthesized answer.
- Avoid burying the definition under brand intro / SEO fluff — the answer engine moves on.

**Specific, falsifiable facts**
- "The average X costs $Y" beats "X can vary in cost"
- "47% of users prefer A over B" beats "many users prefer A"
- Numbers, dates, named entities — these are what the engine extracts

**Structured comparisons**
- Tables for "X vs Y" — engines often re-render these in their answers
- Pro/con lists for evaluative queries
- Decision criteria checklists

**Questions as headings**
- H2/H3 phrased as the actual user query: "How long does X take?" rather than "Timeline considerations"
- Engine retrievers chunk on heading boundaries; matching the query phrasing helps recall

### Step 4: Source authority signals

The engine ranks sources beyond just topical match. Signals:

- **Author bylines with credentials** — "By [Name], [credential / role]" with linked author page
- **Citation density** — your page citing other authoritative sources signals you're embedded in the topical knowledge graph
- **Freshness markers** — explicit "Updated [date]" on the page; reflected in HTTP `Last-Modified`
- **Domain authority for the topic** — historical depth of content in this topic, inbound links from authoritative sources
- **Schema.org markup**: Article, FAQPage, HowTo, Product, with author and dateModified populated

### Step 5: Technical baseline

Don't skip the basics:
- Page indexed by Google AND Bing (check Search Console + Bing Webmaster Tools)
- Crawlable for AI crawlers — don't block GPTBot / ClaudeBot / PerplexityBot in robots.txt unless you've decided to (see Step 7)
- llms.txt at root if you want to provide a curated map for AI crawlers (emerging standard, partial adoption)
- Fast load (LCP < 2.5s) — slow pages get crawled less frequently
- Clean URLs, no infinite-scroll content traps, content in HTML not JS-only

### Step 6: Measurement

Track:
- **Citation rate**: for each priority query, fraction of engines citing your domain (run audits monthly minimum)
- **Citation rank**: when cited, are you 1st, 3rd, 7th in the source list?
- **Click-through from AI answers**: track via UTM-tagged links if engine adds them; track via referrer (`https://chat.openai.com/`, `https://perplexity.ai/`) in analytics
- **Branded query growth**: GEO often increases branded search ("[Brand] [topic]") even without direct AI clicks
- **Conversions from AI-cited content**: long attribution chain; instrument carefully

Tooling that can help (verify current capability when adopting): Profound, AthenaHQ, Otterly, BrightEdge AI Tracker, Peec AI, Goodie. Free path: spreadsheet + monthly manual audit.

### Step 7: The crawler-access decision

Whether to allow AI crawlers (GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended) is a strategic call:

| Stance | Rationale |
|---|---|
| Allow all | You want maximum citation surface; willing to be training data |
| Allow citation crawlers, block training crawlers | GPTBot ≠ OAI-SearchBot; GoogleBot ≠ Google-Extended; you can allow the search-time fetcher and block the training fetcher |
| Block all | You're explicitly opting out of AI surfaces; valid for some publishers |

Recommend allowing search-time crawlers (OAI-SearchBot, ChatGPT-User, PerplexityBot, ClaudeBot's search variant) for most marketing-driven sites — blocking them is opting out of the entire GEO surface.

## Output format

When auditing a page or site:

```
# GEO Audit — [Site/Page] — [Date]

## Priority queries
1. [Query] — currently cited by: [engines] | not cited by: [engines]

## Page-level findings
| Page | Citability score | Issues | Priority fix |
|---|---|---|---|

## Quick wins
- [Specific changes shippable this week]

## Strategic recommendations
- [Content gaps, original research opportunities, schema work]

## Crawler config
- Current: [blocked/allowed bots]
- Recommended: [based on stance]

## Measurement plan
- Tracked queries: [list]
- Cadence: [monthly]
- KPIs: [citation rate, rank, referral CTR]
```

When generating content for GEO:
- Lead with the answer in the first 100 words
- Include 3–5 specific, citable facts in the body (numbers / dates / proper nouns)
- Use question-phrased H2/H3
- Add original data if possible
- Date-stamp updates explicitly

## Anti-patterns

1. ❌ Stuffing FAQ schema with low-quality questions hoping for FAQ rich result reuse — answer engines don't fall for it; users don't click through
2. ❌ Hidden text / white-on-white prompt injection targeting LLM crawlers — quality engines detect and demote; reputational risk if discovered
3. ❌ Treating GEO as a separate strategy from content quality — it's a refinement of quality content, not a parallel track
4. ❌ Optimizing for one engine — citation rates differ wildly across engines; track all major ones
5. ❌ Generating AI content to feed AI search — engines downrank low-original-value content; the citation surface rewards specificity
6. ❌ Ignoring Bing entirely — disproportionate ChatGPT impact comes from Bing index
7. ❌ Skipping the manual audit step — automated tools tell you ranks but not why; the why comes from reading the cited sources
8. ❌ Updating "Updated [date]" without actually updating content — engines that compare content hash to dateModified will demote
9. ❌ Putting key facts only in PDFs / images / video transcripts not surfaced in HTML — engines extract from page HTML primarily
10. ❌ "Best [thing]" listicle with vague descriptions — engines extract specific recommendations; vague entries get filtered out
11. ❌ Removing internal links to "consolidate authority" — internal link graph helps engines understand topical depth
12. ❌ Reporting GEO success purely on rank position without measuring referral traffic and brand lift — answer engines often satisfy without click; the KPI mix needs to reflect that
13. ❌ Building a single hub page for every topic instead of a topical cluster — engines reward depth-of-coverage, which means multiple pages each going deep on subtopics, interlinked
14. ❌ Applying GEO to transactional pages — wrong query intent; users in buying mode are using product search not asking AI
15. ❌ Assuming today's engine behavior is stable — re-audit every quarter; ranking algorithms shift, new engines emerge, citation conventions evolve

## Reference files

- `references/citation-patterns.md` — query types, citation surface examples, scoring rubrics

## Confidence calibration

- General GEO patterns: high — established now across multiple agencies' published findings
- Specific engine ranking signals: low — engines disclose little; signals are reverse-engineered and shift
- Tool recommendations: refresh quarterly — fast-moving category
- "Will this specific change improve citation rate" — measure, don't predict; citation outcomes are noisy
