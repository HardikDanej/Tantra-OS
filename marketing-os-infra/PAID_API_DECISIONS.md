# Paid API Provisioning Decisions

This file exists because "free before paid" has been the standing design principle across every workflow in this repo, web research runs on free tools (direct fetch, PageSpeed Insights, the ad-transparency centers) until real credentials justify paying for more, and a principle that's never actually tested against a concrete adopt/skip decision is just a slogan. This is that test, for three categories: SERP APIs, scraping-as-a-service, and social/ad intelligence (Apify). Recorded here so the reasoning survives past the chat session that produced it, the same way every other capability decision in this project got written into a README or agent file instead of staying only in a conversation.

**Scope:** this is a recommendation and a decision record, not a provisioning action. Nothing here signs up for anything, enters a payment method, or commits spend — that stays the user's own action, on their own account, same boundary as every other financial/account-creation action in this project.

Pricing cited below was pulled live (2026), not recalled from training data, and is cited with sources — the same discipline `citation_guard.py` enforces on every agent's live-research claims in this repo applies here too. Pricing changes; verify at signup regardless of what's written here.

---

## 1. SERP API (SerpApi / Tavily) — **Skip for now**

**What it would add:** structured, reliable SERP snapshots (ranking position, SERP features) and precise search-volume numbers, at a frequency/scale free `WebSearch` can't reliably sustain.

**What already covers the load-bearing need for free:** the SEO Content Factory workflow's actual keyword-prioritization engine (`gsc_keyword_pull.py`) runs on real Google Search Console data — impressions, CTR, position — for the user's own site. That's the data the topic-scoring algorithm is built on, and it's free by definition (it's the user's own property). `ahrefs-seo-machine` already exists as an optional, BYO-subscription skill for anyone who separately has Ahrefs, and Ahrefs covers keyword volume + rank tracking + backlink/authority data in one tool — a strictly larger feature set than SerpApi/Tavily for the same use case.

**The actual remaining gap:** automated *competitor* rank tracking (not the user's own site) and precise search-volume numbers independent of GSC's impression-based proxy. Real, but not currently blocking anything built — no agent in this repo has a stop condition that requires it the way, say, the Website Development Agent requires a real PageSpeed score.

**Current pricing (2026):**
- SerpApi: $25/mo (1,000 searches) up to $275/mo (30,000 searches); no pay-as-you-go, unused searches don't roll over. ([SerpApi Pricing Explained](https://apiserpent.com/blog/serpapi-pricing-explained))
- Tavily: free tier (1,000 credits/mo), then $30–$500/mo tiers or $0.008/credit pay-as-you-go. ([Tavily Pricing 2026](https://coldiq.com/blog/tavily-pricing))

**Call:** don't adopt either yet. Revisit only if a specific, named need shows up — "track our rank against these N named competitors weekly" — that GSC's own-site data and an existing Ahrefs subscription (if the user has one) genuinely can't answer. If that need appears and Ahrefs isn't already in the picture, Tavily's pay-as-you-go model is the lower-commitment starting point of the two.

---

## 2. Scraping-as-a-service (Firecrawl / ScraperAPI / Bright Data) — **Skip**

**What it would add:** managed infrastructure for JS rendering plus (for ScraperAPI/Bright Data specifically) residential proxy rotation and anti-bot-detection handling for sites that block even a real headless browser.

**What already covers the legitimate part of this gap for free:** `.claude/lib/browser_render.py`, built earlier in this same sequence — self-hosted Playwright, real Chromium, correctly clears basic JS "checking your browser" interstitials as a side effect of being a real browser, honestly reports a genuine bot-challenge/CAPTCHA as a stop condition.

**The actual remaining gap, and why it's not worth paying for here:** what's left after `browser_render.py` is specifically *serious* anti-bot infrastructure (Akamai, PerimeterX, Cloudflare Enterprise/Turnstile) — and that's precisely what these services sell: Bright Data's core products are residential/ISP proxy rotation ($8/GB residential, $500+/mo committed plans) and a Web Scraper API explicitly priced around getting past that kind of protection ([Bright Data Pricing 2026](https://dupple.com/pricing/bright-data)); ScraperAPI's own pricing notes that "JavaScript rendering, premium proxies, and advanced targets" consume extra credits ([ScraperAPI Pricing](https://scrapegraphai.com/blog/scraperapi-pricing)) — i.e., the harder-to-block the target, the more it costs, because the product is the evasion. That's a materially different thing from "render JS honestly," and it's the exact capability `browser_render.py`'s own docstring deliberately refuses to build, for a stated reason: this project's actual usage (occasional competitor/site diagnostic checks, not high-volume production scraping) rarely hits a target that needs it, and paying for evasion infrastructure to route around a boundary set on purpose isn't a cost/benefit call, it's undoing a decision.

Firecrawl is the softer case of the three here — its pricing/positioning ([Firecrawl Pricing 2026](https://www.eesel.ai/blog/firecrawl-pricing): Free 1,000 credits/mo, $16/mo Hobby, up to $599+/mo) reads more like "outsourced Playwright infrastructure" than "buy your way past a specific target's defense." Even so, it's redundant with something already built and already working for this project's actual volume — paying to not maintain a working thing isn't nothing, but it's not this project's problem yet either.

**Call:** don't adopt any of the three. If a specific, real site someone actually needs to monitor turns out to be blocked even by `browser_render.py` — not hypothetically, a concrete named case — that's a one-off decision to revisit with that case in hand, not a standing subscription to provision speculatively now.

---

## 3. Social/ad intelligence (Apify) — **Adopt, scoped narrowly**

**What it would add:** structured scraping of public social profiles/posts — organic engagement data, follower/audience signals — for platforms (Instagram, TikTok, LinkedIn) that have no free public API for third-party read access the way Meta Ad Library or Google Ads Transparency Center exist for *ads*.

**Why this is the one real gap of the three, already admitted in the agents' own files, not hypothetical:**
- `social-media-agent.md`'s influencer-vetting track already states its own limitation in writing: *"If those checks fail rather than return real signal, refuse to vet on follower count alone as a fallback — say the authenticity check couldn't be completed."* That's not a hedge, it's an agent whose current tools (`WebFetch`/`WebSearch`) sometimes structurally cannot get the data the task needs.
- `comment-sentiment-monitor` requires "an existing comment stream" as input today — meaning a human has to manually export/paste social comments before this agent can do anything. There's no live pull at all.
- Neither gap is served by anything already built in this sequence (workflow 05's `site_snapshot.py` monitors *websites*; nothing here touches organic social).

**Risk/ethics profile, and why it's meaningfully different from category 2:** scraping public profile pages/posts for competitive intelligence and creator vetting is well short of "solve CAPTCHAs to get past a defense actively trying to stop automated access" — most public social profiles aren't behind that kind of protection, and this is the same posture Meta Ad Library/Google Transparency Center already establish as acceptable for ads, just extended to organic content. The same boundary still applies: read public data only, never automate engagement/follows, never evade a login wall.

**Current pricing (2026):** free tier ($5/mo compute credit), then pay-as-you-go compute units on top of a plan starting ~$29/mo — usage-proportional, not a flat commitment. A typical light actor run (2GB RAM, 30 min) costs about $0.20 on the Starter plan; proxy usage (needed for the harder-to-reach platforms) bills separately on top. ([Apify Pricing 2026](https://use-apify.com/docs/what-is-apify/apify-free-plan))

**Call:** adopt, starting on the free tier ($5/mo credit, no commitment) to validate against the two named use cases above before upgrading — influencer-authenticity vetting first (already a stated, recurring refusal point), competitor organic-social monitoring second (extends workflow 05's pattern, not urgent). **This decision does not itself wire anything up** — building the actual connector (which specific Apify actors, how results feed `influencer-matchmaker`/`social-media-agent`, evidence-logging and citation-guard integration the same way every other live-research path in this repo already has) is separate follow-up work, to be scoped and signed off on the same way the ad-platform and CRM connectors were, once there's a live Apify account to build against.

---

## Summary

| Category | Call | Why |
|---|---|---|
| SERP API (SerpApi/Tavily) | Skip | Load-bearing need already covered free (GSC); remaining gap isn't blocking anything built |
| Scraping-as-a-service (Firecrawl/ScraperAPI/Bright Data) | Skip | Legitimate gap already closed free (`browser_render.py`); remaining gap is evasion infrastructure this project deliberately doesn't do |
| Social/ad intelligence (Apify) | Adopt, free tier first | Real, already-admitted gap in two agents' own files; usage-based pricing keeps initial commitment near zero |
