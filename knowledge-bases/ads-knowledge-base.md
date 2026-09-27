# Ads / Paid-Media Knowledge Base

> **Temporal Currency Note:** the taxonomy, buying-mechanics, and measurement-principle structure here is stable and ages slowly. Platform-specific specifics do not — auction mechanics, targeting options, and creative-format availability change per-platform frequently and often without notice. Never state a current bid strategy, current targeting option, or current platform policy from this file alone; verify against the platform's own current documentation first.
>
> **Last reviewed:** 2026-08-30. **Refresh cadence:** the 11-dimension taxonomy and governing principles are stable, review yearly. Per-channel platform mechanics (auction types, targeting options, format availability) should be spot-checked every 6 months — these are exactly the specifics platforms change without announcement.

**What this is:** Reference knowledge for an Ads/Paid-Media Agent operating in a multi-agent marketing system. It is background context to be loaded and consulted — not a workflow, skill, or set of steps to execute. Use it to: (1) correctly classify an ad request against the master taxonomy, (2) look up a channel's format vocabulary, buying mechanics, and measurement stack before recommending a plan, and (3) calibrate how sophisticated an ad-idea-generation prompt/system should be using the maturity ladder.

**How to use it:**
- Need to place a request within the overall advertising landscape → **Core Tier → Master Taxonomy**.
- Need channel-specific facts (formats, how it's bought, what to measure, rules of the road) → **Reference Tier**, one entry per channel.
- Need to decide how sophisticated an ideation/personalization system should be → **Ideation Maturity Ladder**.
- Generic marketing advice (audience research, brand voice, creative testing discipline) belongs in the separate Marketing KB, not here — this file stays advertising-specific.

---

## 1. CORE TIER

### 1.1 Master Taxonomy

Advertising is not a flat list of formats — it's a **combinatorial system** across orthogonal dimensions. Any single ad can be described as a configuration across all of them simultaneously:

```
AD = Medium × Channel × Environment × Placement × Format × Creative × Interaction × Objective × Audience × Delivery × Timing
```

**The 7-level structural hierarchy:**
`Advertising → Medium → Channel → Environment → Placement → Format → Variant`

**The 11 orthogonal classification dimensions** (every ad sits somewhere on each axis independently):

| Dimension | Values |
|---|---|
| Medium | Text, Image, Video, Audio, Interactive, Physical, Immersive |
| Channel | Search, Social, Web, App, TV, Audio, Retail, OOH, Messaging |
| Environment | Editorial, Commerce, Entertainment, Utility, Community, Physical |
| Placement | Feed, Search results, Product page, Content, Video player, Homepage, Checkout, Physical location |
| Format | Banner, Video, Native, Carousel, Sponsored listing, etc. |
| Creative structure | Static, Dynamic, Personalized, Interactive, UGC, Creator, AI-generated |
| Interaction | View, Click, Swipe, Play, Engage, Message, Install, Purchase |
| Objective | Awareness, Consideration, Traffic, Lead, Install, Sale, Retention |
| Audience | Contextual, Demographic, Behavioral, Interest, Intent, First-party, Lookalike |
| Delivery mechanism | Direct, Auction, Programmatic, Sponsorship, Affiliate, Creator |
| Measurement | Impression, View, Click, Engagement, Lead, Install, Purchase, LTV |

**Important non-formats** — these are transaction/strategy layers that can wrap *any* format, not formats themselves:
- **Programmatic** = an auction/delivery mechanism (RTB, PMP, programmatic guaranteed, preferred deals, open auction) that can deliver display, video, audio, native, CTV, DOOH, mobile, or retail media.
- **Retargeting/re-engagement** = an audience/delivery strategy, manifesting as retargeting display, video, search, social, email, app, or CTV.
- **Dynamic advertising** = a construction method (data/feed-driven creative) layered onto any format.
- **Affiliate/performance** = a commercial (payout) model, not a creative format.

**The 38 major advertising format families** (top-level taxonomy; each has its own sub-format tree covered per-channel in the Reference Tier below): Digital Display, Search, Social Media, Video, Connected TV/OTT/Streaming, Audio, Mobile & In-App, Native, E-Commerce & Retail Media, Programmatic, Email, Messaging, Influencer & Creator, Out-of-Home (OOH), Digital OOH, Print, Direct Mail, Gaming, Virtual/Immersive, Experiential, Sponsorship, Product Placement, Branded Content, Affiliate/Performance, Lead-Generation, Conversational/AI, Search-Assistant/Generative, Ambient, Packaging, Vehicle, Point-of-Sale, Retargeting/Re-engagement, Dynamic, Interactive, Shoppable, Promotional, Classified/Listing, Political/PSA/Cause.

**The feedback loop underlying all paid media** (the mental model to apply to any channel):
```
Advertiser → Creative → Audience/Targeting → Auction/Distribution → User → Response → Data → Optimization → New Creative/Distribution
```

**The Advertising Intelligence layer** above format — 17 sub-disciplines that increasingly define modern ad ops (useful as a checklist when auditing a channel strategy): Audience, Intent, Context, Creative, Targeting, Bidding, Budget-allocation, Auction, Personalization, Experimentation, Attribution, Conversion, Prediction, Optimization, Competitive, Fraud/quality, and Measurement intelligence.

### 1.2 Cross-Channel Governing Principles (deduped digest)

These are patterns that recur across most/all channel files but are genuinely worth stating once at the Core level (channel-specific rules that don't generalize live in each Reference Tier entry instead):

- **Format ≠ mechanism ≠ strategy.** Always separate "what the ad looks like" (format) from "how it's bought" (auction/direct/programmatic) from "who sees it and why" (targeting/audience strategy). Conflating these is the most common classification error across the corpus (explicit in Programmatic, Retargeting, Dynamic, Affiliate entries).
- **Attribution degrades as the funnel moves off-platform or offline.** Every channel with a walled garden (social, search, retail media, CTV) pushes its own attribution model; every offline/ambient channel (OOH, print, experiential, sponsorship) relies on proxy/lift measurement (surveys, geo-lift, brand lift, promo-code/QR bridges) rather than direct click attribution. Treat "last click" metrics as directionally useful only for owned/closed-loop channels (search, retail media, email/SMS) and as one input among several elsewhere.
- **Auction dynamics reward relevance, not just bid.** Nearly every auction-based channel (search, social, programmatic display, DOOH) uses some ad-rank/quality-score composite (bid × relevance/CTR × format contribution), so creative quality directly lowers effective CPMs — this is a mechanic, not just advice.
- **First-party and identity signals are the scarce resource.** Cookie/IDFA deprecation has pushed contextual, cohort-based (e.g., interest/topic clustering), clean-room, and first-party CRM matching to the center of targeting across display, video, CTV, and social — channel files converge on this as the defining shift of the current era.
- **Creative and placement fatigue is format-specific, not universal.** Skippable video, social feed, and messaging formats decay fast (days); OOH, sponsorship, and branded content decay slow (weeks-months) — plan refresh cadence per channel, not on one global rule.
- **Frequency and intrusiveness trade off against brand trust asymmetrically by channel.** Messaging (SMS/push) and direct mail carry the highest per-impression trust cost of overuse (regulatory + relationship risk); display and DOOH carry the lowest (ambient, low personal-data footprint).
- **Every closed commerce environment (retail media, social commerce, e-commerce) converts channel logic into an internal auction on top of a marketplace's own product graph** — meaning keyword/placement bidding there behaves more like search advertising than like traditional display, regardless of the visual format.
- **The "highest bid wins" mental model is wrong everywhere an ad-rank/quality composite governs the auction.** Search, social, native, and retail media all compute something like `Bid × P(action) × Quality/Relevance`, so a lower bid with better-predicted performance can outrank a higher bid — this is stated as an explicit mechanic (not a tip) in the Search, Social, Native, and Retail Media source material alike.
- **Attributed conversions and incremental conversions are two different numbers, and the gap is the single most repeated correction across every channel file.** "This sale happened after the ad" (attribution) is not "this sale happened because of the ad" (incrementality); every channel with enough scale eventually needs a holdout/geo-experiment layer to close that gap, not just a better attribution model.
- **Format and unit and placement are three separate axes that a flat taxonomy collapses at everyone's peril.** A "video ad" is a format; "300×250 skyscraper" or "6-second bumper" is a unit; "pre-roll on a YouTube watch page" is a placement — the same format can sit in a dozen placements with materially different economics and behavior, and channel files (Video, Display, Native, Mobile) each call this out as a recurring analytical error to avoid.
- **Creative decisioning is increasingly a search/ranking problem, not a design problem.** Once an advertiser supplies N headlines × M images × K CTAs, the system (not a human) is choosing the shown combination per impression — responsive search ads, DCO in display/email/retail-media, and dynamic creative in social/native/mobile all reduce to the same underlying `argmax expected-value` selection problem over a combinatorial asset library.
- **Retargeting and lifecycle-stage targeting should be modeled as a state machine, not a single audience.** Viewer → cart → checkout → purchaser → repeat-customer each warrant a different message (reminder → objection-handling → urgency → cross-sell → loyalty); this pattern repeats near-identically across Display, Social, Video, Email, and Retail Media and is a stronger mental model than "retarget site visitors" as one undifferentiated bucket.
- **Suppression is a targeting decision, not a courtesy.** Email, Messaging, and Direct Mail all treat "who NOT to contact" (recent purchasers, complainers, the already-converted, the fatigued) as equally important as "who to contact" — audience = eligible − suppressed, and skipping this step measurably degrades deliverability/response and inflates fatigue-driven unsubscribes.

---

## 2. REFERENCE TIER

One compact entry per channel (24 channels).

### Affiliate & Partner Marketing
- **What it is:** A commission-based distribution model — a publisher/partner drives an attributable action (click, lead, or sale) and is paid only on that outcome, not on impressions. Distinct from influencer/creator spend, which typically blends a flat fee with performance incentives; affiliate is performance-first by construction.
- **Key format distinctions:**
  - Content/review affiliates (comparison sites, "best of" roundups) vs. coupon/cashback sites vs. loyalty/rewards portals vs. sub-affiliate networks (an affiliate who recruits and pays sub-affiliates)
  - Network-mediated (ShareASale, Impact, CJ, Awin — network handles tracking/payout, takes a cut) vs. direct/in-house program (brand runs its own tracking and terms)
  - Cookie-based vs. server-to-server (S2S) postback tracking — S2S is materially more reliable under browser cookie restrictions and is now the default for serious programs
- **Commission structure decision:** flat CPA (fixed payout per action) vs. percentage-of-sale (scales with basket size, standard for ecommerce) vs. tiered/performance-escalating (higher rate as an affiliate's volume grows, used to reward top performers without overpaying long-tail partners). Attribution window (typically 7-30 days, category-dependent) must be stated in the program terms, not left implicit — an undefined window is a common source of affiliate-brand disputes over who "gets credit" for a sale.
- **Top metrics:** Earnings per click (EPC, the affiliate's own health metric — used to recruit and retain), conversion rate by partner tier, incremental vs. cannibalized revenue (a real risk: coupon/cashback affiliates often intercept a sale that would have converted anyway via a brand-search coupon-code insertion at checkout — this is the single most common affiliate-program measurement failure and must be modeled, not assumed away).
- **Channel-specific principles:**
  - Vet before recruiting — an affiliate with a history of trademark-bidding (bidding on the brand's own name in paid search to intercept branded traffic) or cookie-stuffing violates most programs' terms and actively cannibalizes paid-search spend elsewhere in the stack.
  - Commission changes are a real budget/contract commitment, not a content decision — treat a rate change with the same authorization discipline as a media-buy decision, never as a routine content update.
  - Program terms (cookie window, commission tiers, prohibited tactics, termination clause) need to exist in writing before a partner is onboarded — an undocumented arrangement is where most affiliate-relationship disputes originate.

### Audio Advertising
- **What it is:** Paid communication delivered through audio consumption environments (radio, streaming, podcasts, smart speakers, connected car).
- **Key format distinctions:**
  - Host-read (personal, trust-transfer) vs. produced/baked-in vs. dynamically-inserted spot
  - Pre-roll / mid-roll / post-roll / ad pods
  - Sponsorship (show, segment, playlist, station) vs. impression-based buying
  - Interactive/voice-response audio (smart speakers) and audio companion (visual add-on for CTA)
  - Dynamic/personalized/sequential audio creative
- **Buying mechanism:** Direct, reserved, sponsorship, programmatic guaranteed, preferred deal, PMP, open auction (OpenRTB extends to audio).
- **Top metrics:** Reach, frequency distribution, completion rate, listening/attention (distinct from completion), brand lift, incrementality lift (exposed vs. control).
- **Channel-specific principles:**
  - No visual canvas — creative must build mental imagery through voice/music/sound design; sonic branding (sonic logo) is the audio equivalent of a visual identity.
  - Completion ≠ attention — playback continuing doesn't mean the listener is engaged; audio is frequently consumed while multitasking.
  - Host trust is a distinct persuasion asset — host-read ads inherit the audience's existing relationship with the host, unlike programmatic audio.

### Branded Content Advertising
- **What it is:** Brand funds/produces/integrates into content designed to inform, entertain, or tell a story rather than function as a conventional ad — the content itself is the ad vehicle.
- **Key format distinctions:**
  - Editorial (sponsored article, advertorial) vs. video/audio/social/interactive content
  - Entertainment content (brand-funded film/series where brand is nearly invisible)
  - Educational/expertise content (builds authority before commercial persuasion)
  - Experiential/event-derived content (event → content → digital distribution)
- **Buying mechanism:** Fixed sponsorship, production fee, media distribution purchase, CPM/CPC/CPA, revenue share, or hybrid (production fee + guaranteed media + performance bonus).
- **Top metrics:** Content performance (watch time, completion, scroll depth, shares/saves), audience quality (qualified engagement vs. raw exposure), brand lift/association/trust, downstream behavioral (site visits, leads).
- **Channel-specific principles:**
  - Brand integration level is a tunable variable — too little means content is remembered but not the brand; too much collapses it into a perceived ad ("audience fit ≠ brand fit").
  - Strongest effects land in the middle result layers (content/brand), not pure reach or pure conversion — judging solely by CPC or reach misreads the format.
  - Content compounds — unlike a media buy, strong content keeps generating value after the paid distribution ends.

### Connected TV / OTT / Streaming
- **What it is:** Advertising ecosystem (not just a format) bridging linear TV and digital RTB across CTV devices, OTT content, and streaming business models.
- **Key format distinctions:**
  - Content models: FAST (free ad-supported), AVOD, SVOD-with-ads, live/vMVPD
  - In-stream: pre/mid/post-roll, ad pods (with pod position, category exclusivity)
  - CTV-native: pause ads, screensaver ads, menu ads, in-scene ads (IAB 2026 portfolio)
  - Interactive/shoppable CTV (TV = discovery, phone = transaction)
- **Buying mechanism:** Direct, reserved, programmatic guaranteed, preferred deal, PMP, open auction (OpenRTB 2.6+ adds CTV-specific pod/channel objects), or sponsorship.
- **Top metrics:** Completion rate, viewability, household reach/frequency, brand lift, incrementality (exposed vs. control), cross-device attribution.
- **Channel-specific principles:**
  - Household, not individual, is the addressable unit — co-viewing means one device impression can equal multiple viewers, requiring panel/survey-based modeling.
  - Attribution is view-through by necessity — viewers rarely click, so search-lift, clean-room matching, and household-to-device graphs replace click attribution.
  - Supply-path quality is a distinct risk — fragmented device/OS environments create device misclassification and fraud that don't exist the same way in web display.

### Digital Display Advertising
- **What it is:** A decision-and-delivery system selecting which visual message shows to which user, where, and when, via websites/apps/exchanges.
- **Key format distinctions:**
  - Static/animated/HTML5 vs. rich media (expandable, interactive) vs. native (in-feed, visually blended)
  - Format (what it looks like) vs. ad unit/dimension (banner, skyscraper, interstitial) — these are separate axes
  - Responsive/dynamic creative optimization (DCO) — combinatorial asset assembly
  - Retargeting (site/product/cart/search) as a distinct strategic layer from format
  - Expandable units: start small (standard banner footprint) and unlock a larger interactive/video experience only after hover/click/tap — reserves scarce screen space until interest is demonstrated, rather than front-loading a large unit on every impression
  - Sequential/state-based display: instead of one ad shown repeatedly, delivery advances the viewer through Ad A → Ad B → Ad C as their engagement state changes, effectively giving the campaign memory rather than treating every impression independently
- **Worked scenario:** An online mattress brand running site retargeting would show a plain product-reminder banner to someone who merely viewed a product page, but switch to a discount-anchored, review-heavy rich-media unit for someone who added to cart and abandoned checkout — same retargeting pool, two different creative treatments keyed to funnel depth.
- **Buying mechanism:** Direct, ad network, programmatic (RTB via DSP/SSP/exchange), private marketplace, programmatic guaranteed; priced via CPM/CPC/CPA/CPV/CPE/vCPM.
- **Top metrics:** Viewability, CTR, conversion rate/CPA/ROAS, invalid traffic/fraud rate, incrementality (treatment vs. control).
- **Channel-specific principles:**
  - Format, placement, targeting, buying, and creative logic are distinct layers that should not be conflated as "ad types" (e.g., RTB and retargeting are not formats).
  - Creative search space grows combinatorially (assets × audiences × devices × placements can reach six figures) — this is why DCO/automation is structurally necessary, not optional.
  - A preceding impression before a purchase does not imply causation — requires geo/holdout experiments to establish incrementality.
  - Contextual targeting infers relevance from what the user is currently consuming (page/article topic) rather than who the user is, meaning it can function without personal identity data — this is why contextual has become the fallback targeting layer as cookie-based identity resolution degrades.
  - Dynamic Creative Optimization (DCO) treats creative selection as a decision-logic problem keyed on live signals (location, device, weather, prior product interest): the same campaign can render "rain-ready shoes" to one user and "20%-off running shoes" to another, with the underlying creative assets and rules identical.
  - Creative testing at scale is combinatorial, not additive — 3 headlines × 4 images × 2 CTAs × 2 offers × 3 layouts already produces 144 combinations before audiences/devices/placements multiply it further, which is the structural reason DCO/automation exists rather than being an optional efficiency layer.

### Digital Out-of-Home
- **What it is:** Digital advertising on physical-environment screens, defined by venue + screen + variable audience exposure + optional programmatic buying, not just "digital on a big screen."
- **Key format distinctions:**
  - Venue hierarchy (transit, retail, outdoor, etc. — OpenOOH's 11 parent / 70 child taxonomy)
  - Ad unit ≠ screen: full-screen, partial-screen, slot, spot, loop position, share-of-voice, takeover
  - Static vs. motion vs. dynamic (data-triggered: weather/traffic/sports) vs. interactive (QR/AR/touch)
  - Placement is a separate axis from venue (e.g., mall = venue, checkout = placement, portrait LED = inventory)
- **Buying mechanism:** Direct (guaranteed, fixed placement, SOV, takeover) or programmatic (open auction, PMP, preferred, programmatic guaranteed) via OpenRTB DOOH-specific fields.
- **Top metrics:** Plays/proof-of-play, impressions (estimated, not 1:1 with plays), reach/frequency/GRP/TRP, dwell/attention, store-visit lift.
- **Channel-specific principles:**
  - One play ≠ one impression — impressions are estimated (audience opportunity × share-of-loop × visibility factor), unlike a discrete web impression.
  - Venue is itself a targeting primitive carrying audience/context meaning (e.g., airport gate = captive + long dwell), not just a location label.
  - Trigger-based (condition → creative-variant) dynamic creative is a defining native capability, not an add-on as in most other channels.

### Direct Mail Advertising
- **What it is:** A physical, addressable outbound channel delivering promotional material to a known mailing address, defined by delivery mechanism and addressability rather than paper format.
- **Key format distinctions:**
  - Postcards (no envelope barrier, high immediate visibility) vs. letters vs. self-mailers
  - Catalogs/magalogs vs. dimensional mail (3D packages/samples — physical-experience channel)
  - Unaddressed mail/door drops — a related but fundamentally different targeting branch
  - Format ≠ unit: a dimensional "package" contains distinct units (letter, coupon, sample, reply card)
- **Buying mechanism:** List acquisition (owned/rented/purchased/modeled) + production/printing + fulfillment + postage; cost structure directly tied to weight/dimensions/presort class, not auction-based.
- **Top metrics:** Response rate, matchback-attributed conversions, incremental lift (mail vs. holdout control), CAC/cost-per-response, revenue per thousand mailed.
- **Channel-specific principles:**
  - Creative and postal economics are coupled — a heavier/larger mailer that raises postage can produce worse economics despite better creative.
  - Suppression (deciding who NOT to mail) is as valuable as targeting who to mail, unlike most digital channels where incremental reach is cheap.
  - Holdout/control-group testing is the primary causal-measurement method, since there's no click to attribute — matchback and promo codes are secondary proxies.

### E-Commerce & Retail Media
- **What it is:** Commerce-linked advertising delivered inside/around retail environments (marketplaces, retailer sites/apps, physical stores) using first-party shopper, product, and transaction data.
- **Key format distinctions:**
  - Sponsored Product (search/category/product-page listing, intent capture)
  - Sponsored Brand (multi-product/storefront, category consideration)
  - Sponsored Display / off-site retail media (audience activation via DSPs off the retailer's own properties)
  - Product recommendation placements ("customers also bought")
  - In-store media (digital shelf, checkout screens, smart carts)
  - Product-graph targeting: instead of targeting a keyword, an advertiser targets a specific competitor, substitute, or complementary product directly on that product's own detail page — a targeting primitive with no equivalent in non-commerce channels
  - Off-site retail media: the retailer activates its own first-party shopper/purchase audiences (category shoppers, lapsed buyers, competitor purchasers) on external display/video/CTV inventory via a DSP, bridging retail media into programmatic rather than staying confined to the retailer's own properties
- **Worked scenario:** A mid-tier headphone brand on a marketplace would bid aggressively on Sponsored Product placements against a competitor's flagship model's own product page (product-graph targeting, capturing comparison-shopping intent at the point of decision) while using off-site retail media to re-engage the retailer's own "electronics category shoppers who haven't purchased in 60 days" audience with a CTV spot — two different retail-media mechanisms serving the same campaign.
- **Buying mechanism:** CPC auction (dominant), plus CPM/CPV, fixed placement/sponsorship, guaranteed deals, and programmatic (DSP/SSP).
- **Top metrics:** ROAS, ACOS/TACOS, new-to-brand %, basket size/AOV, attributed vs. incremental sales.
- **Channel-specific principles:**
  - Ad performance is capped by the underlying product (availability, price, rating) — creative cannot rescue a bad product.
  - Optimize for expected incremental profit (bid × relevance × CVR × margin), not just CTR/ROAS.
  - Attributed sales ≠ incremental sales — requires holdouts/geo experiments to isolate causal lift; over-monetizing inventory can degrade shopper experience/marketplace health.
  - Portfolio-level advertising allocation should weigh margin against conversion rate, not treat all SKUs equally: a high-margin/high-CVR product and a low-margin/high-CVR product warrant different bid ceilings even at identical ROAS, because ROAS measures revenue efficiency while the actual objective is incremental profit.
  - In-store media (digital shelf, checkout screens, smart carts, electronic shelf labels) extends retail media into physical space, meaning "retail media" is not inherently a digital-only category — the same targeting logic (shopper state, category affinity) can drive a screen at a physical endcap.
  - The seven-dimension ad-unit model (format, placement, unit, targeting, buying, creative, optimization) applies cleanly to retail media specifically because every sponsored placement is simultaneously an advertising decision and a merchandising decision — a Sponsored Product ad is scored on `bid × relevance × conversion probability`, identical in shape to a search auction, but its "creative" is catalog-derived rather than advertiser-authored.

### Email Advertising
- **What it is:** Direct-response/native advertising delivered through owned or third-party email inventory to a permissioned audience.
- **Key format distinctions:**
  - Newsletter placement (ad embedded in existing publisher email)
  - Dedicated/full-email takeover (single advertiser owns entire send)
  - Native email (styled as editorial content)
  - Product/recommendation placement (catalog-driven, dynamic)
  - Triggered/transactional email advertising (event-driven, e.g., cart abandonment)
  - Logical placement vs. rendered placement: where the advertiser intended a unit to sit (e.g., "hero position") is a distinct data point from where it actually appears after a given email client renders the HTML — a subtlety with no equivalent in web display
  - Individualized send-time optimization: rather than one blast time for the full list, the system learns P(open|user, time) and P(conversion|user, time) per subscriber and staggers delivery accordingly
- **Worked scenario:** A subscription meal-kit brand sending a win-back campaign to lapsed customers would suppress anyone who converted in the last 14 days, target only subscribers whose engagement state is "at risk" or "dormant," and use a discount-led dynamic offer block — while its dedicated-email newsletter placement to active subscribers stays purely editorial/native in style to avoid training the list to tune out sponsored content.
- **Buying mechanism:** Flat-rate sponsorship, CPM/CPC/CPA/CPL, revenue share, or programmatic email (DSP-matched audience+inventory).
- **Top metrics:** Delivery/deliverability rate, CTOR (click-to-open rate), CPA/CPL, incremental lift (treatment vs. control), LTV.
- **Channel-specific principles:**
  - Deliverability is a gating layer, not just a metric — mailbox providers decide if the ad is even seen (sender/domain reputation, SPF/DKIM/DMARC, spam/complaint rate).
  - Distinguish "logical placement" (intended) from "rendered placement" (actual, varies by email client).
  - Frequency/suppression is a first-class targeting dimension (audience = eligible − suppressed), not an afterthought — over-emailing trains subscribers to disengage.
  - Lifecycle-stage messaging differs by design intent, not just tone: new subscribers warrant discovery-oriented creative, existing customers warrant cross-sell, high-value customers warrant retention/premium offers, and lapsed customers warrant reactivation — sending the same "shop now" creative across all four lifecycle states wastes the channel's biggest structural advantage (first-party behavioral history).
  - Recency decay is measurable and should drive targeting thresholds directly: conversion probability given recency (`P(conversion|recency)`) declines with time since last engagement, so a "purchased <7 days" segment and a "no engagement >90 days" segment are not just different audiences but warrant fundamentally different offers and frequency.
  - Deliverability is a gating layer above creative quality: sender/domain/IP reputation, SPF/DKIM/DMARC authentication, and bounce/complaint rates determine inbox placement before rendering even happens — a perfectly optimized creative that lands in spam has zero value, which is why deliverability engineering sits upstream of subject-line or CTA testing in priority.

### Experiential Advertising
- **What it is:** Advertising where the audience encounters, participates in, or physically/virtually experiences the brand rather than just viewing a message.
- **Key format distinctions:**
  - Brand activations (street/retail/festival — an "experience architecture" rather than one format)
  - Product experience/demonstration (trial, test drive, before/after)
  - Pop-ups and branded environments (temporary scarcity drives urgency/earned media)
  - Stunts/spectacles (built for unexpectedness → attention → sharing)
  - Sponsorship activation (activating the rights, not just holding them)
- **Buying mechanism:** Owned, paid placement/venue rights, sponsorship, partnership/co-branding, production-based, or performance-based (leads/trials) — no universal auction, commercial structure is deal-by-deal.
- **Top metrics:** Approach/engagement/completion rate (funnel: Reach→Notice→Approach→Enter→Engage→Convert), dwell time, cost per participant/lead, earned media value, brand recall/association lift.
- **Channel-specific principles:**
  - Experience memorability ≠ brand memorability — brand integration must be structural, not a bolted-on logo, or people remember "that cool thing" without the brand.
  - Two audiences exist simultaneously: participants (primary) and social/shareable reach (secondary, via UGC/earned media) — don't design solely for the Instagram audience at the expense of the in-person experience.
  - Operational execution (queueing, staffing, throughput) is itself an advertising-effectiveness variable — a brilliant activation with a 45-minute line fails.

### Gaming Advertising
- **What it is:** Advertising delivered inside, around, or through interactive game environments and gamer audiences (including advergaming, esports, and game user-acquisition).
- **Key format distinctions:**
  - Rewarded advertising (player opts in for in-game reward — voluntary attention)
  - Native/integrated advertising (branded objects/skins/quests embedded as game content, not an overlay)
  - Playable ads and interactive video (mini-gameplay inside the ad unit)
  - Advergaming (the game itself is the branded asset, not an ad placed in an existing game)
  - Esports advertising (league/team/player sponsorship, broadcast/in-arena)
- **Buying mechanism:** Direct sponsorship, programmatic/auction, guaranteed, performance (CPI/CPA), or hybrid (fixed sponsorship + performance media).
- **Top metrics:** Viewability/completion rate, CPI → CPA → ROAS → LTV progression, retention/churn, ARPU/ARPPU, brand lift.
- **Channel-specific principles:**
  - The game is both media and product — ad monetization directly trades off against player experience/retention; short-term ad revenue ≠ optimal outcome.
  - The cheapest install is often not the most valuable install — optimization must move beyond CPI to player quality/LTV.
  - Frequency/fatigue management is structural: rewarded formats convert attention into value voluntarily, but overexposure of any format turns monetization into churn.

### Influencer & Creator Advertising
- **What it is:** Personality-, community-, and content-mediated advertising where a creator produces and/or distributes commercial communication, functioning simultaneously as media, creative, endorser, and distribution channel.
- **Key format distinctions:**
  - Sponsored social content (post/Reel/Story/livestream)
  - Creator endorsement/testimonial vs. demonstration (unboxing, tutorial, comparison)
  - UGC production (content-only, no distribution) vs. full creator campaign (audience + content + distribution)
  - Whitelisting/Spark-style paid amplification (creator content run as a paid ad from the creator's handle)
  - Affiliate/commission-based creator commerce
  - Brand-controlled vs. creator-controlled vs. collaborative creative production: brand-controlled has the creator execute a predefined concept (highest consistency, weakest authenticity signal); creator-controlled has the creator develop their own concept and execution (strongest authenticity, least brand control); collaborative sits between the two via brief → creator concept → brand review → execution
  - UGC production without distribution is a distinct deliverable from a full creator campaign: a brand can pay a creator purely to produce an asset (photo/video) it then owns and distributes itself, buying zero audience access or endorsement value — this is a content-production purchase, not an audience/influence purchase
- **Worked scenario:** A protein-powder brand running a creator campaign would treat a 50k-follower fitness micro-influencer's authentic gym-routine integration (creator-controlled, buying audience + influence + distribution) completely differently from a separate UGC-only deal with a non-influencer content creator who simply films a clean product demo the brand then runs as paid social creative (buying content production only, zero audience/distribution value) — conflating the two into one "influencer budget" line item misprices both.
- **Buying mechanism:** Flat fee, performance (CPA/commission/CPL), hybrid (base fee + commission), or non-cash (product seeding/gifting).
- **Top metrics:** Engagement rate (ER), cost per engagement (CPE), audience authenticity %, incremental revenue per creator, promo-code/affiliate-link conversions.
- **Channel-specific principles:**
  - Creator audience value ≠ creator content value ≠ influence — a campaign must specify which of the 5 creator-value types (audience, influence, content, distribution, performance) is actually being purchased.
  - Rights/usage terms are a distinct asset from the content itself — one Reel does not implicitly grant paid-media, cross-channel, or perpetual usage rights.
  - UGC and influencer advertising are not synonyms: UGC is a content-production mechanism (often no audience/distribution attached), influencer advertising is an audience/trust/distribution mechanism.
  - Creator size should not be reduced to a hard follower-count bracket — the more useful definition is audience scale × reach × engagement × niche authority, since a smaller creator with a tightly-matched niche audience can outperform a larger, more diffuse one on the metrics that actually matter for a given campaign.
  - Whitelisting/Spark-style paid amplification is a distinct distribution mode from either pure organic creator posting or pure brand-owned paid media: the brand runs the creator's content as a paid ad from the creator's own handle, buying the creator's perceived authenticity while controlling the media spend and targeting like a normal paid campaign.
  - Rights should be modeled per-asset, per-channel, per-territory, and per-duration rather than assumed: one Reel does not automatically grant paid-media usage, cross-platform usage, perpetual usage, or editing rights — a creator deal without an explicit rights clause routinely produces disputes the moment a brand tries to run organic content as a paid ad.

### Messaging Advertising
- **What it is:** Paid promotion delivered through/into messaging environments (SMS, WhatsApp, Messenger, RCS, etc.) designed to initiate or continue a business-to-user conversation.
- **Key format distinctions:**
  - Click-to-message ad (paid social/display placement that opens a chat — the core acquisition unit)
  - Sponsored/rich message (native inbox placement with cards, carousels, buttons)
  - Conversational ad (the ad itself behaves as a mini dialogue with branching)
  - Catalog/product card messaging (commerce embedded in chat)
  - Conversation-stage-triggered messages (qualification, reactivation, abandoned-cart recovery)
- **Buying mechanism:** CPM/CPC, cost-per-conversation, cost-per-qualified-conversation, CPL/CPA, or value-based/ROAS bidding.
- **Top metrics:** Cost per (qualified) conversation, conversation completion/reply rate, lead/qualification rate, incremental lift (treatment vs. control), LTV.
- **Channel-specific principles:**
  - The conversation itself is a first-party data-generation asset — extracted intent/entities (budget, product, timeline) feed back into targeting and next-best-action, unlike a one-way impression.
  - Progressive qualification beats upfront interrogation — every unnecessary question in the chat flow reduces completion probability.
  - Attribution is especially inflation-prone here: a conversation preceding a purchase doesn't mean it caused it, so incrementality testing is essential; frequency/cooldown discipline matters more than in other channels because messaging is a more intimate, higher-annoyance-risk surface.

### Mobile & In-App Advertising
- **What it is:** Digital advertising delivered across mobile web, native apps, games, and app-store ecosystems, spanning brand exposure through app-install acquisition and in-app commerce.
- **Key format distinctions:** Banner/MREC display; interstitial, rewarded, and app-open video; playable ads (interactive demo of the app itself); native in-feed units; offerwalls/virtual-currency incentives (gaming-specific).
  - Placement-within-app-lifecycle sub-formats specific to gaming: level-transition interstitials, game-over screens, menu placements, and reward screens — each carries a different tolerance for interruption and a different expected engagement state
  - App-install funnel formats are chained, not single-shot: impression → click → store visit → install → first open → registration → activation → purchase → retention, meaning "app install ads" is shorthand for creative/bidding decisions made across the whole chain, not just the initial click unit
- **Worked scenario:** A hyper-casual mobile game acquiring users would bid toward predicted 90-day LTV rather than raw CPI — accepting a higher cost-per-install from a playable-ad placement (which pre-qualifies players who actually enjoy the mechanic) over a cheaper banner-driven install that historically churns within a day, because the mediation layer's cheapest fill is not the same as the advertiser's most valuable user.
- **Buying mechanism:** Direct/sponsorship or programmatic (RTB, PMP, programmatic guaranteed); inside apps, SDK mediation/waterfall (or in-app bidding) lets multiple ad networks compete per impression.
- **Top metrics:** CPI (cost per install) as an intermediate, not final, KPI; SKAN/attribution-based install and first-open tracking; ROAS and predicted LTV; retention curves; incrementality (vs. correlation-only attribution).
- **Channel-specific principles:**
  - Optimize toward predicted 90-day LTV per acquired user, not raw CPI — cheapest install ≠ best user.
  - Rewarded formats work via explicit incentive exchange (user gets value for attention), unlike passive display.
  - Mediation creates real-time internal competition among demand sources for the same impression, distinct from a single-exchange auction.
  - The app-install funnel is chained, not single-shot (impression → click → store visit → install → first open → registration → activation → purchase → retention), so "app install advertising" really names creative and bidding decisions made across the whole chain rather than just the click-to-install step.
  - Expected value for acquisition bidding compounds multiple probabilities — `P(install) × P(activation) × P(purchase) × predicted LTV` — meaning two campaigns with identical CPI can have wildly different economics if their downstream activation/purchase rates diverge.
  - Playable ads (an interactive mini-demo of the app itself, run as the ad unit) pre-qualify installs by letting the user experience core mechanics before installing, which is why their resulting install cohorts often retain better than banner- or video-driven installs even at a higher CPI.

### Native Advertising
- **What it is:** Paid media designed to visually and functionally match the surrounding content/platform experience rather than interrupt it (in-feed, sponsored articles, promoted listings, recommendation widgets).
- **Key format distinctions:** In-feed (mimics feed items); content recommendation (below/beside articles); sponsored/branded editorial articles; social-native (inherits organic post structure); commerce-native (looks like a normal shopping result).
  - Content-first vs. product-first creative structure: content-first leads with problem → information → insight → solution → brand (used where the environment is editorial/trust-driven); product-first leads with product → benefit → proof → CTA (used where the environment is already commerce-intent, e.g., search or marketplace native)
  - Interactive native sub-formats — quizzes, calculators, configurators, product selectors — trade the passive "read the sponsored piece" behavior for an engagement mechanism that itself generates first-party signal (answers, selections) usable for downstream targeting
- **Worked scenario:** A financial-planning app placing a sponsored article in a personal-finance newsletter would use content-first structure ("Why most people underestimate retirement costs") that only introduces the product in the final third, whereas the same brand's commerce-native placement inside a comparison-shopping site would lead immediately with the product card, rating, and CTA — same advertiser, opposite creative sequencing, driven entirely by which environment it's native to.
- **Buying mechanism:** Direct/sponsorship, network buying, or programmatic native (DSP → exchange → publisher), often via auction scored on Bid × P(Action) × Quality.
- **Top metrics:** CTR and dwell/content-consumption time (native-specific engagement proxies); conversion-to-value chain (click → lead → customer → LTV) rather than click alone; incrementality; experience-cost offset (advertiser value + relevance + publisher value − experience cost).
- **Channel-specific principles:**
  - The core tension is unique to this channel: attract attention *without* breaking the surrounding experience — over-optimizing CTR can degrade platform trust.
  - Disclosure/sponsorship transparency is a structural requirement, not optional polish, because the format deliberately mimics editorial content.
  - Ranking blends advertiser bid with a "quality"/experience score, not just economic value, since a bad-fit native ad damages publisher context more than a bad banner does.
  - The conceptual ranking function `Score = Bid × P(Action) × Quality` mirrors search and social auctions almost exactly, reinforcing that native is fundamentally an auction-and-relevance system wearing an editorial costume rather than a separate mechanic.
  - Native creative must solve two problems simultaneously that other formats solve separately: attracting attention (like any ad) while preserving the surrounding experience (unlike most ads) — over-optimizing for CTR alone routinely damages the second objective and, over time, publisher trust and native inventory value with it.
  - Eligibility filtering happens before ranking: campaign status, budget, audience match, context match, geo/device eligibility, creative approval, frequency limits, and brand-safety requirements all gate a candidate ad before it competes on Bid × P(Action) × Quality — a creative can be perfectly targeted and still never enter the auction if it fails an eligibility gate.

### Out-of-Home (OOH) Advertising
- **What it is:** Physical-world advertising attached to a place, object, route, or public environment rather than a personal device (billboards, transit, street furniture, place-based, DOOH).
- **Key format distinctions:** Static large-format (bulletin/poster/wallscape) vs. digital billboard/LED; street furniture (bus shelter, kiosk); transit (bus/train/subway/taxi/airport); place-based (mall, gym, cinema — venue itself is the targeting mechanism); ambient/guerrilla (environment becomes the creative, e.g. building takeovers, projection mapping).
- **Buying mechanism:** Fixed placement, package, network, market, or route buying for traditional OOH; DOOH adds programmatic/PMP/open-exchange/auction and automated reservation, sold by non-standard units (face, panel, slot, loop, showing, GRP) rather than a universal "impression."
- **Top metrics:** GRP (gross rating points) and share of voice; estimated impressions/reach/frequency (modeled, not individual-level); cost per GRP / CPM-equivalent; proof-of-play (plays, play duration) for digital; attribution via geo-lift (exposed vs. control market) since there's no click.
- **Channel-specific principles:**
  - No native impression-level tracking exists — audience is estimated/modeled, so measurement leans on GRP and controlled geo experiments rather than individual attribution.
  - Programmatic DOOH can condition creative on real-world triggers (weather, time of day, traffic, live events) — a targeting axis with no digital-only equivalent.
  - Contextual/venue targeting (gym→fitness, airport→travelers) substitutes for identity targeting, since individuals can't be identified.

### Print Advertising
- **What it is:** Offline advertising reproduced on a physical substrate and distributed via publications, direct mail, retail, or packaging, with predetermined inventory booked in advance.
- **Key format distinctions:** Publication display (full/half/fractional page, spread, gatefold, cover positions); classified; direct mail (postcards, catalogs, personalized/addressable mail); inserts (bound-in, polybag, statement/bill inserts); retail/POS print (shelf talkers, circulars) and packaging print.
- **Buying mechanism:** Space-based (buy physical page/insert size), audience/circulation-based pricing, frequency and geographic buying, or negotiated package deals (often bundled with digital).
- **Top metrics:** Circulation vs. readership vs. opportunity-to-see vs. attention (each a different, non-equivalent number); response mechanisms (QR scans, promo codes, unique phone numbers, coupon redemption) as the primary attribution bridge; incremental ROAS via matched-market/control-market testing.
- **Channel-specific principles:**
  - Circulation ≠ readers ≠ exposures ≠ attention — treating any one as a proxy for another overstates reach.
  - Creative must communicate the full proposition with zero interactivity, since there's no click-through path unless a response mechanism is designed in.
  - Optimization operates on a slow planning→execution→measurement→next-insertion cycle, not real-time bid adjustment — physical production/distribution lead times are a hard constraint on the media itself.

### Product Placement Advertising
- **What it is:** Paid integration of a brand/product into third-party content (film, TV, streaming, gaming, music, creator content) rather than a discrete ad unit.
- **Key format distinctions:** Visual/logo/packaging placement (passive exposure); verbal placement (spoken mention); demonstrative/consumption placement (functional use shown); character/story/plot integration (brand becomes narratively load-bearing); virtual/dynamic placement (digitally inserted, swappable post-production, common in streaming/gaming).
- **Buying mechanism:** Direct deal with production, agency-mediated, product-for-placement (barter), cash+product hybrid, sponsorship-linked, licensing/co-production, or revenue-share; contracts specify exclusivity, duration, and approval rights over script/depiction.
- **Top metrics:** Screen time, size, position and visual prominence (visibility, not just presence); aided/unaided brand and product recall; narrative/character relevance score; earned-media spillover (social mentions, organic posts, press) beyond the original audience; downstream search-lift/purchase-intent.
- **Channel-specific principles:**
  - Three escalating integration levels — exposure (product visible) → integration (participates in scene) → narrative integration (product shapes plot/character identity) — and deeper levels drive disproportionately more brand effect.
  - Optimization must balance prominence against authenticity: maximizing visibility can break narrative believability and backfire on brand perception, unlike a standalone ad unit.
  - Measurement is inherently harder than click-based media — it requires proxies (recall, contextual/narrative relevance) since there's no impression or click event.

### Programmatic Advertising
- **What it is:** Not a format but an automated buying/decisioning layer (marketplace + auction + decision engine + delivery + optimization) that transacts inventory across nearly every other channel (display, video, native, CTV, audio, DOOH).
- **Key format distinctions:** N/A as a format — it's a transaction mechanism; applies across display, native, video, audio, CTV, DOOH inventory.
- **Buying mechanism:** Four core structures — Open Auction/RTB (OpenRTB-standardized, real-time competitive bidding), Private Marketplace/Private Auction (invite-only), Preferred Deal (fixed price, first-look, non-binding), Programmatic Guaranteed (negotiated price/volume/inventory, automated execution — closer to automated direct than RTB); auction packages/curated marketplaces bundle inventory by criteria.
- **Top metrics:** Win rate and supply-path cost/take rate (SPO efficiency); viewability-adjusted expected value (Bid × P(Viewable)); CPA/ROAS at the bid-decision level; incrementality (exposed vs. counterfactual conversions, not just post-exposure conversion); brand-safety/invalid-traffic rate as a gating metric, not just a report.
- **Channel-specific principles:**
  - Auction mechanics matter structurally: first-price vs. second-price scoring changes optimal bid strategy — bidding true value is only safe under second-price rules.
  - Supply-path optimization is essential because the same publisher impression is often reachable through multiple SSPs/resellers at different cost/quality/transparency — buyers must evaluate the path, not just the impression.
  - Supply-chain transparency (ads.txt/app-ads.txt, sellers.json, SupplyChain Object) is a prerequisite for legitimate bid eligibility, not an afterthought — fraud/brand-safety checks belong inside the bid/no-bid decision itself, not as post-hoc reporting.
  - The four commercial structures are not interchangeable labels for the same thing: Open Auction/RTB is fully competitive and impression-level; Private Marketplace restricts participation to selected buyers for better inventory control; Preferred Deal gives first-look access at an agreed price without a purchase obligation; Programmatic Guaranteed pre-negotiates inventory/volume/price/dates and then automates execution — closer to automated direct sales than to an auction at all.
  - Viewability changes expected value independent of CPM: two impressions priced identically can have very different `Bid × P(Viewable)` expected value, so optimizing on CPM alone leaves viewability-adjusted value on the table.
  - Pacing is not `budget ÷ days` — a naive even split ignores time-varying inventory availability, competition, and conversion likelihood, so real systems compute `Spend_t = f(time, opportunity, performance, budget, forecast)` and can intentionally under- or over-spend early relative to a flat pace.
  - Header bidding / in-app bidding lets multiple exchanges compete simultaneously (vs. sequential waterfall), materially changing yield — a mechanism distinct from the auction type itself.
  - Bid/no-bid is a pre-filter, not just a price decision: eligibility, brand-safety, audience-match, and expected-value thresholds reject the large majority of bid requests before a price is even calculated — this filtering-then-pricing sequence is why programmatic can evaluate billions of impressions economically.
  - Curated marketplaces / auction packages bundle open-auction inventory around a criterion (publisher quality, audience, content category) while still competing against open-auction bids under a deal ID — a middle tier between fully open RTB and a negotiated PMP.
- **Worked scenario:** A travel brand's programmatic desk running a always-on prospecting campaign would route bids through supply-path optimization first — checking whether the same publisher impression is cheaper and more transparent via SSP A vs. SSP B — before the DSP even calculates a bid, since paying a lower take-rate for an identical impression is pure margin recovered with zero change to the audience reached.

### Social Media Advertising
- **What it is:** Paid, algorithmically distributed advertising on social platforms that leverages identity, behavior, and social-graph data to predict and deliver relevant ads.
- **Key format distinctions:**
  - Image/single-image and carousel (sequential "mini landing page" logic: hook→problem→solution→proof→CTA)
  - Collection/dynamic product ads (catalog-driven, recommendation-engine-based)
  - Native lead forms (avoids off-platform funnel drop-off)
  - Stories/Reels (full-screen, consumption-stream format vs. feed's "interrupt" format)
  - Messaging ads (turns impression→click into impression→conversation→conversion)
  - Broad/algorithmic targeting: advertiser supplies objective + creative + conversion signal and lets the platform's prediction model find the audience, shifting audience-discovery intelligence from advertiser to platform
  - Sequential/story-state creative: instead of one static ad shown repeatedly, campaigns can advance a viewer through Ad A → Ad B → Ad C as a narrative, functioning as state-based advertising rather than frequency-capped repetition
- **Worked scenario:** A DTC skincare brand running Meta retargeting on cart-abandoners would not show the same ad as its cold-prospecting campaign — the cart-abandoner sees an objection-removal creative (ingredient safety, return policy, a testimonial) at a tighter frequency cap, while cold prospects see a broad awareness/UGC video with algorithmic targeting left open so the platform can discover the audience itself.
- **Buying mechanism:** Real-time auction — bid × predicted action rate × ad quality/relevance = auction value; bid strategies include lowest cost, cost cap, target CPA/ROAS.
- **Top metrics:** CTR, CPM, engagement rate (likes/shares/saves), CPA/CPL, ROAS, view-through vs. click attribution, incrementality/holdout lift.
- **Channel-specific principles:**
  - Broad/algorithmic targeting shifts audience-finding intelligence from advertiser to platform (feed objective+creative+signal, let system find the audience) rather than manual demographic targeting.
  - Retargeting should be modeled as a behavioral state machine (viewer→cart→checkout→purchaser), each state warranting a different creative strategy, not one blanket "retarget visitors" campaign.
  - Dynamic/combinatorial creative (multiple images×headlines×texts×CTAs) requires managing creative fatigue explicitly — frequency has a nonlinear effect where too little underexposes and too much triggers CTR decay/negative sentiment.
  - The campaign hierarchy (Account → Campaign → Ad Set/Ad Group → Ad) assigns different controls at different levels: objective and budget strategy live at the campaign level, audience/placement/schedule/bid strategy live at the ad-set level, and creative variation lives at the ad level — collapsing this hierarchy (e.g., changing audience at the wrong level) is a common operational error.
  - Native lead-generation forms exist specifically to eliminate the off-platform funnel drop-off of Ad → Website → Page → Form → Submit, compressing it to Ad → Native form → Lead; the tradeoff is losing website-side qualification and enrichment that a full landing page would capture.
  - Attribution on social splits into click, view-through, multi-touch, and data-driven models, but the deeper question the channel-specific material stresses is incrementality: holdout and geo experiments answer "what would have happened without this exposure," which no attribution model — however sophisticated — actually answers on its own.
  - Carousel and collection formats function as a sequential mini-funnel inside a single ad unit (hook → problem → solution → proof → offer → CTA across frames), so they should be storyboarded as a narrative rather than treated as "one static ad per frame."

### Sponsorship Advertising
- **What it is:** A relationship/association-based discipline where brands buy rights, access, and exclusivity around a property (sports, entertainment, events, causes, etc.) rather than buying media exposure directly.
- **Key format distinctions:**
  - Relationship tiers: Title, Presenting, Official Sponsor, Category/Official Supplier, Media/Strategic Partner
  - Rights types: naming, branding, content, talent, hospitality, promotional, data
  - Inventory: physical (signage/uniforms), broadcast (mentions/segments), digital, social, experiential (booths/activations)
  - Activation types: brand, product, experiential, content, digital, retail, hospitality
- **Buying mechanism:** Negotiated deals — fixed fee, tiered packages (Platinum/Gold/Silver), revenue share, performance-linked, in-kind, or hybrid; not standardized CPM auctions.
- **Top metrics:** Exposure (logo/broadcast minutes), brand lift/association/preference, engagement/participation, leads, sales/commerce conversion, earned media/share of voice, overall ROI.
- **Channel-specific principles:**
  - Category exclusivity is a core value driver — it can lock competitors out of an entire property/category, unlike standard media buys.
  - "Rights ≠ advertising" — an unactivated sponsorship deal is underutilized; value = Rights × Activation, not Rights alone.
  - Targeting inverts the normal model: instead of finding an audience, you find properties whose existing audience already matches your target (audience-fit-driven property selection, not property-agnostic audience buying).

### Search Advertising
- **What it is:** Paid advertising that competes for exposure at the moment a user expresses explicit intent via a search query.
- **Key format distinctions:**
  - Responsive search ads (multiple headlines/descriptions combinatorially assembled per query context)
  - Shopping/product ads (matched via product feed data, not keywords)
  - Dynamic search ads (site content, not advertiser keywords, generates targets/headlines)
  - Ad extensions/assets (sitelinks, callouts, price, call, location)
  - Broad match has shifted from string-matching toward intent-matching: the engine now uses landing pages, other keywords in the account, location, and search history as signals — meaning a broad-match keyword is closer to "topic eligibility" than a literal phrase match
  - Negative keywords are a distinct targeting layer (target demand = desired demand − undesired demand), not a cleanup afterthought
- **Worked scenario:** A B2B SaaS company selling accounting software bids on "best accounting software for small business" (commercial-investigation intent) very differently from "QuickBooks alternative" (competitive-evaluation intent) or "buy accounting software" (transactional intent) — same product, three different landing pages, three different bid/CPA targets, because the query itself encodes where the searcher sits in the funnel.
- **Buying mechanism:** Real-time keyword/query auction on Ad Rank (bid × quality × context × competition × thresholds); manual CPC or automated bidding (tCPA, tROAS, Maximize Conversions).
- **Top metrics:** Impression share (incl. absolute-top share), CTR, CPC, Quality Score (diagnostic, not an auction input), CVR/CPA, ROAS.
- **Channel-specific principles:**
  - Highest bid does not equal highest position — Ad Rank blends bid with quality/context, so "outbidding" alone doesn't win placement.
  - Negative keywords are as strategically important as positive targeting: target demand = desired demand − undesired demand.
  - Match types have moved from string-matching toward intent-matching (broad match now uses landing pages, other keywords, location, and history as signals) — treat keywords as matching instructions, not literal strings.
  - Query→Ad→Landing Page must form one coherent semantic chain (message match); this continuity itself affects Quality/conversion, not just conversion-page design.
  - Quality Score is diagnostic, not an auction input in itself — the actual auction inputs are its underlying components (expected CTR, ad relevance, landing-page experience). Chasing a "10/10 Quality Score" as a goal is a category error; the real goal is more valuable auction outcomes at acceptable economics.
  - Shopping/product ads use the product feed (title, price, availability, images, attributes) as the matching substrate instead of keywords — meaning feed hygiene (accurate titles, in-stock status, competitive pricing) functions as the keyword-optimization equivalent for this sub-format. A feed with stale prices or out-of-stock items will lose auctions regardless of bid.
  - Dynamic Search Ads reverse the normal workflow: instead of advertiser-defined keywords driving ad creation, the system crawls the website's own content to discover search opportunities and auto-generate headlines/landing-page targets, which means a site's information architecture itself becomes part of the advertising surface.
  - The economic ceiling on any bid is `P(conversion) × conversion value − required margin`; treating a keyword as "worth pursuing" without running this calculation is how search accounts overspend on traffic that never had a viable payback.

### Video Advertising
- **What it is:** Paid distribution of audiovisual creative across in-stream, out-stream, social, CTV/OTT, and app environments to drive a measurable outcome.
- **Key format distinctions:**
  - In-stream (pre/mid/post-roll, pods) vs. out-stream (in-feed/native/interstitial) vs. feed-native (Shorts/Reels-style)
  - Skippable vs. non-skippable vs. bumper (fixed short non-skippable)
  - CTV/OTT-specific: pause ads, ad pods, shoppable/interactive TV
  - Rewarded video (in-app, opt-in exchange for value)
  - CSAI vs. SSAI: client-side ad insertion (player separately requests the ad) vs. server-side ad insertion (server stitches ad into the content stream before it reaches the player) — SSAI smooths CTV playback but complicates independent verification since the ad is no longer a discrete client-called event
  - Temporal creative architecture differs by environment: a 0–2 second pattern-interrupt is critical in skippable in-feed/social video but irrelevant in non-skippable CTV, where the full 15–30 seconds is guaranteed regardless of the opening frame
- **Worked scenario:** A furniture retailer running a 6-second bumper on YouTube in-stream needs a completely different creative cut than the same brand's 30-second CTV spot — the bumper must land the product + offer inside the first 2 seconds because skip is available, while the CTV spot can build a slower narrative arc since completion is guaranteed by the non-skippable pod.
- **Buying mechanism:** Direct/sponsorship, programmatic (open auction, PMP, programmatic guaranteed), or platform auction; priced via CPM, CPV, CPC, CPA, tCPA, vCPM depending on objective.
- **Top metrics:** View-through/completion rate (25/50/75/100%), viewability, watch time, vCPM, CPA/ROAS, view-through vs. click attribution.
- **Channel-specific principles:**
  - Format ≠ placement ≠ environment — the same creative asset performs differently depending on which of these three independent variables changes; don't conflate "YouTube ads" with a single format.
  - CSAI vs. SSAI matters operationally: server-side ad insertion (common in CTV) smooths playback but complicates verification/measurement since ads are stitched server-side rather than called client-side.
  - Completion ≠ persuasion and impression ≠ attention — a fully-watched ad can still produce zero recall, so funnel modeling should chain P(viewable)×P(watch)×P(engage)×P(click)×P(convert) rather than relying on CTR alone.
  - Creative timing should be re-architected per environment (e.g., 0–2sec pattern interrupt is critical in skippable/short-form but irrelevant in non-skippable CTV).
  - Video is a sequential medium where message_t depends on message_(t-1) — information reveals through time, so reordering a demonstration-then-proof structure into proof-then-demonstration is not a neutral edit, it changes what the viewer has been primed to accept at each subsequent second.
  - The video funnel should be modeled as a probability chain — `P(conversion) = P(viewable) × P(watch) × P(engagement|watch) × P(click|engagement) × P(conversion|click)` — rather than read off CTR alone, because a creative can win on any one stage and still lose on the full chain (e.g., high viewability but low watch-through).
  - VAST standardizes the ad-server-to-player handoff (which creative, where the asset lives, tracking events); understanding CSAI vs. SSAI matters operationally because SSAI (common in CTV) smooths playback but complicates independent measurement since the ad is stitched into the stream server-side rather than called by the client.
  - Rewarded video is fundamentally an incentive-exchange format (user opts in for value — extra lives, currency, unlocked content) rather than a passive interruption, which is why its completion rates and sentiment differ structurally from a forced pre-roll even at identical length.

### Virtual / Immersive Advertising
- **What it is:** Experience-based, spatial, interactive advertising delivered through AR/VR/MR/XR and virtual-world environments where users participate rather than passively view.
- **Key format distinctions:**
  - AR (marker/markerless/location-based try-on, filters, packaging activation) vs. VR (360° video, VR stores/events, full inhabited experiences)
  - Spatial/3D product ads (rotate, configure, disassemble) and virtual try-on
  - Sponsored/branded virtual worlds, virtual goods (skins, avatar items), avatar advertising
  - WebXR/3D web ads (browser-based, no headset required — lowers hardware friction)
- **Buying mechanism:** Direct purchase, sponsorship, partnership/custom brand integration with platform or game publisher, and emerging programmatic buying based on audience/environment/context.
- **Top metrics:** Dwell time/gaze duration, interaction rate, experience completion rate, exploration depth, product configuration/add-to-cart, brand lift, incremental revenue.
- **Channel-specific principles:**
  - Spatial inventory has variables ordinary digital ads lack — position, scale, orientation, occlusion, persistence, environmental relevance — meaning "placement" is a 3D/physical problem, not X/Y coordinates.
  - Technical performance directly is advertising performance: latency, frame rate, and motion comfort measurably affect campaign results in a way they don't for banner/video ads.
  - Targeting can be event-driven/environment-triggered (e.g., gaze duration > threshold, or entering a physical zone with an AR-capable device) rather than purely pre-set audience segments — this is "experience-state targeting," unique to immersive.

---

## 3. IDEATION MATURITY LADDER

Source: "Advertisement Idea Intelligence" — a 10-level maturity model for how sophisticated an ad-idea-generation (LLM-driven or human) system is. Use this to calibrate how much reasoning/system architecture a given ideation task actually warrants — don't build a Level 9 pipeline for a Level 1 request, and don't ship Level 1 output when the brief demands Level 6+ segmentation.

**Grouping:** Levels 1-6 = generative intelligence (better concepts). Levels 7-8 = adaptive/predictive intelligence (concepts that change with signals). Levels 9-10 = closed-loop systems (concepts that test, learn, and regenerate themselves).

| Level | Name | Core Logic | What It Does | One-Line Prompt Pattern |
|---|---|---|---|---|
| 1 | Basic | Product → Benefit | Turns a product's primary benefit into a simple, memorable message/concept | "Given product {product}, audience {audience}, benefit {benefit}: generate 10 concepts communicating the benefit clearly." |
| 2 | Audience-aware | Audience → Need → Message | Generates different concepts for different audience segments off the same product | "Identify {audience}'s need, frustration, desired outcome, emotional motivation; generate concepts positioning {product} as the solution." |
| 3 | Problem-solution | Problem → Tension → Solution | Dramatizes a real pain point before introducing the product as relief | "Identify the strongest recurring problem {audience} has that {product} solves; build PROBLEM → ESCALATION → TENSION → PRODUCT → RELIEF." |
| 4 | Context-aware | Context → Message adaptation | Adapts the message to when/where/under-what-conditions it's encountered (time, weather, location) | "Given location, time, weather, situation, audience, product: generate a message that feels naturally relevant to this exact context." |
| 5 | Behavioral | Behavior → Trigger → Response | Infers intent from observed user behavior and designs a message targeting the likely next action | "Given {behavior history}: infer intent, funnel stage, objection, likely next action; create an ad targeting that next action specifically." |
| 6 | Multi-variable | Audience × Intent × Context × Objective × Channel | Combines multiple variables simultaneously into one strategic concept, producing different creative per combination | "Given audience, intent, context, objective, product, channel, funnel stage: determine psychological angle, message, format, hook, CTA, and rationale." |
| 7 | Adaptive | Real-time signals → Dynamic creative | Changes the live advertisement itself as real-world signals shift (weather, traffic, events) | "Monitor {signals}; on meaningful change, identify audience state, select creative format, generate the revised ad, explain the adaptation." |
| 8 | Predictive | Predicted intent → Intervention | Moves from reacting to current state to predicting the likely next action and intervening pre-emptively | "Given historical + current behavior + context + product interaction: predict purchase probability, next action, barrier, optimal intervention point; generate the ad addressing that predicted action." |
| 9 | Autonomous | Observe→Interpret→Segment→Predict→Strategize→Generate→Deploy→Measure→Compare→Learn→Regenerate | The LLM becomes a campaign decision engine: detects anomalies, forms hypotheses, generates and ranks alternatives, defines experiments | "You are an advertising optimization system. Given objective, data, campaign history, current performance: detect anomalies, identify causes/opportunities, generate hypotheses, create and rank alternative ads, define experiments, analyze results, update strategy." |
| 10 | Advertising intelligence system | Sense → Model → Strategize → Generate → Experiment → Learn (full closed loop, continuous) | A standing system that continuously understands markets/people/context/creative/outcomes and regenerates strategy without being re-briefed each time | "You are an autonomous advertising intelligence system. Given market, audience, product, context, behavior, campaign history, business objectives: run the full 14-step reasoning cycle (understand market → identify opportunities → predict behavior → form hypotheses → generate creative → design experiments → evaluate → learn → generate next concepts), optimizing for the stated business objective and long-term brand constraints, not just clicks." |

**One-sentence framing per level** (useful as a quick self-check on which level a request actually needs):
1. What advertisement can we make? 2. What should this audience see? 3. What problem should it solve? 4. What makes sense in this context? 5. What should we show because of what they did? 6. What's the best combination of audience/intent/context/objective/channel? 7. How should the ad change as conditions change? 8. What will they likely do next, and how do we influence it? 9. What should the system create/test/optimize next? 10. Can the whole loop sense, reason, create, experiment, and learn continuously?

**Reusable prompting patterns that recur across levels** (apply independent of level):
- **Transformation:** Input → Analysis → Transformation → Output (e.g., product → benefit → emotional benefit → ad).
- **Segmentation:** Audience → Segment → Need → Motivation → Message.
- **Evaluation:** Generate N concepts → critique each on relevance/originality/memorability/emotional strength/brand fit/audience fit/feasibility → score 1-10 → select top 3. Prefer this over a bare "give me 20 ideas" ask.
- **Adversarial:** Generate a concept, then attack it in-character as a skeptical consumer, a competitor, a creative director, and a brand strategist; redesign based on the identified weaknesses.
- **Multi-agent decomposition:** Split one mega-prompt into role-specific agents — Research → Audience → Strategy → Creative → Critic → Experiment → Optimization — each with a narrow objective, rather than asking one prompt to do everything at once.
- **Closed-loop:** Create → Deploy → Measure → Learn → Create again. At sufficient maturity, ad ideation stops being a copywriting problem and becomes an optimization problem.
