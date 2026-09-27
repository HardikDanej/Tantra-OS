# Product Marketing & Go-to-Market Knowledge Base

Dedicated knowledge base for the Product Marketing & Go-to-Market agentic system (`go-to-market-launch-strategy-agent`, `commercial-assets-sales-enablement-agent`, `pricing-packaging-customer-adoption-agent`, and their thirty sub-agents). Closes the standing "no dedicated KB section" disclosure most of those sub-agents carried. Sliced via `kb_slice.py outline` / `section "<heading>"` — never read in full.

## 1. CORE TIER — Go-to-Market Strategy

### 1.1 GTM Motion Selection Matrix

Three canonical motions, and the real signals that should drive the choice (`gtm-motion-selection-subagent`'s working tool):

| Signal | Product-Led (PLG) | Sales-Led (SLG) | Community-Led (CLG) |
|---|---|---|---|
| ACV (annual contract value) | Low ($0–$10K) | High ($25K+) | Varies, often low-to-mid |
| Sales cycle | Days-weeks (self-serve) | Months (multi-stakeholder) | Weeks-months, trust-mediated |
| Buyer | Individual/small team, low-risk decision | Buying committee, budget owner, procurement | Individual, but decision is peer-influenced |
| Time-to-value | Must be minutes-to-hours | Can tolerate a longer onboarding | Value partly *is* the community itself |
| Product complexity | Must be simple enough to self-serve | Can be genuinely complex | Varies |

**Hybrid motions are the norm, not the exception** at scale — a PLG entry motion with an SLG expansion motion once usage crosses a threshold is the most common real-world pattern, not a hedge. The refusal this sub-agent carries — never recommend a motion off deal size or ACV assumptions alone — exists because motion fit is really about *buying behavior*, and ACV is only a proxy for that, not the thing itself.

### 1.2 Launch Tiering Framework

Adapted from Product Marketing Alliance's tiering convention — classifies how much organizational effort a launch deserves, which `product-tiered-launch-management-subagent` uses to right-size a rollout plan:

| Tier | Scope | Cross-functional involvement | Example |
|---|---|---|---|
| **Tier 1** | Major new product, new market, or material revenue driver | Full company: Sales enablement, PR, executive comms, paid launch campaign | A new product line |
| **Tier 2** | Significant feature, meaningful expansion of an existing product | Sales enablement + marketing content + limited PR | A major feature within an existing product |
| **Tier 3** | Minor feature, iterative improvement | Release notes, in-app messaging, no dedicated campaign | A UI improvement or small feature addition |

Under-tiering (treating a Tier 1 launch like a Tier 3) is the single most common real-world launch failure this framework exists to prevent — `cross-functional-launch-readiness-subagent`'s checklist should scale with the tier, not run the same shallow pass regardless of stakes.

### 1.3 Pricing Model Taxonomy & Value-Metric Selection

The **value metric** is what a customer pays *per* — the single highest-leverage decision in pricing, since it determines whether price scales naturally with the value delivered:

| Value metric | Fits when | Risk |
|---|---|---|
| Per-seat | Value scales with number of users | Discourages adoption breadth (fewer seats to save money) |
| Usage-based (API calls, GB, events) | Value scales with consumption, highly variable usage patterns | Unpredictable customer bills, harder to forecast revenue |
| Flat/per-account | Value doesn't scale cleanly with any single unit | Leaves money on the table with high-usage accounts |
| Outcome-based | Value is a measurable business result (revenue, leads) | Hardest to instrument and attribute cleanly |
| Feature-gated tiers | Willingness-to-pay segments by capability need, not usage volume | Requires real packaging discipline to avoid "everything in every tier" pressure |

`pricing-tier-design-value-metric-subagent`'s refusal to assert a price without real evidence maps directly onto three named research methods worth citing by name rather than gesturing at "pricing research" generically: **Van Westendorp Price Sensitivity Meter** (four price-perception questions: too cheap / cheap / expensive / too expensive), **Gabor-Granger** (sequential willingness-to-pay at specific price points), and **conjoint analysis / choice modeling** (trade-off analysis across price + feature bundles simultaneously — the most rigorous, and the most expensive to run).

### 1.4 Packaging & Bundling Patterns

- **Good-Better-Best** — three tiers, each a strict superset of the one below; the most common SaaS pattern because it's the easiest for a buyer to self-select.
- **À la carte / modular add-ons** — a base plan plus independently-priced modules; fits when customer needs genuinely diverge (not every customer wants every module).
- **Land-and-expand** — deliberately under-price or under-scope the initial sale to minimize adoption friction, with a designed expansion path (more seats, more usage, more modules) as the real revenue driver. This pattern is *why* `expansion-upsell-cross-sell-strategy-subagent` and `contract-renewal-retention-marketing-subagent` exist as dedicated disciplines rather than afterthoughts — in a land-and-expand model, the initial sale is intentionally not where most lifetime revenue is designed to come from.

## 2. REFERENCE TIER — Sales Enablement & Adoption

### 2.1 Sales Enablement Asset Anatomy

**Sales deck narrative arc** (`sales-pitch-deck-solution-overview-subagent`'s structural spec) — Situation → Complication → Resolution, a variant of the classic consulting narrative:
```
Situation (the buyer's current state, in their own language)
  → Complication (the specific cost/risk of staying there — quantified where possible)
    → Resolution (the product as the answer to the complication specifically, not a generic feature tour)
```
A deck that opens with the product instead of the buyer's situation inverts this arc and reads as a features list, not a sales narrative.

**Battlecard anatomy** (`competitive-battlecard-objection-handling-subagent`) — four sections, in order of what a rep needs mid-conversation: (1) positioning summary (one line, how we're different), (2) landmine questions (what to ask that surfaces the competitor's real weakness), (3) objection responses (verbatim-ready, not just talking points), (4) proof points (named customers/data, never asserted without a source).

**One-pager anatomy** (`one-pager-solution-brief-subagent`) — headline (the outcome, not the feature) → 3 supporting proof points → a single clear CTA. Self-serve collateral fails when it tries to say everything; it should say the one thing that gets the reader to the next conversation.

### 2.2 Product-Market Fit Measurement

**Sean Ellis Test** (`product-market-fit-validation-subagent`'s core instrument) — the single survey question "How would you feel if you could no longer use this product?" (Very disappointed / Somewhat disappointed / Not disappointed), with **40% "very disappointed" as the commonly cited threshold** for a credible PMF signal. This is a *stated-preference* measure — it must be triangulated against real retention-cohort behavior (an *observed-behavior* measure), never reported alone as proof of fit.

**Retention curve shapes** — the three qualitative patterns that matter more than any single retention percentage: a curve that **flattens** (converges to a stable non-zero retained percentage) signals real product-market fit for the retained segment; a curve that **continues declining toward zero** signals no durable value delivery; a curve that **initially dips then recovers** (the "smile curve") often signals a genuine but narrower product-market fit than the total user base suggests.

### 2.3 Adoption & Activation Frameworks

- **"Aha moment"** — the specific in-product action correlated with long-term retention (Slack's famous 2,000-messages-sent threshold is the canonical example) — `user-onboarding-activation-flow-subagent`'s job is to identify this moment from *real usage data*, never assume a generic "first login" counts.
- **Time-to-value (TTV)** — the elapsed time between signup and the Aha moment; shortening real TTV (not just perceived TTV) is the central lever of onboarding-flow design.
- **Product-Qualified Lead (PQL)** — a usage-behavior-based lead score (as opposed to a demographic/firmographic MQL) — the mechanism `feature-adoption-in-app-discovery-subagent` and `freemium-self-serve-conversion-subagent` both feed into when a self-serve motion needs a sales handoff trigger.

### 2.4 Churn Taxonomy

| Churn type | Definition | Primary owner |
|---|---|---|
| Voluntary churn | Customer actively cancels | `churn-root-cause-winback-offer-modeling-subagent` (why), Revenue/CRM's `churn-prediction-winback-subagent` (who's at risk, sibling system) |
| Involuntary churn | Payment failure, expired card, no active cancellation decision | Often the larger and more fixable share of total churn — a dunning/billing-retry fix can out-perform any win-back offer |
| Logo churn | Losing the whole account | Standard cited metric |
| Revenue/net churn | Net revenue change including expansion within retained accounts | Can be negative (net revenue retention > 100%) even with nonzero logo churn — the two metrics answer different questions and shouldn't be conflated in one framing |

### 2.5 Customer Advisory Board (CAB) Facilitation

`customer-advisory-board-facilitation-subagent`'s structural frame for an ongoing strategic customer-input body — distinct from a one-off focus group (Market Research system) or a reference-call program (`customer-testimonial-reference-program-subagent`, same domain): a CAB is a standing, named group with continuity across meetings, not a recruited-per-question panel.

**Composition principle:** 8-15 members is the commonly-cited functional range — small enough for genuine discussion, large enough to represent segment diversity. Select for a deliberate mix of tenure (new-enough customers to remember onboarding friction, long-tenured customers who've seen the roadmap evolve), segment/use-case diversity, and a demonstrated willingness to give candid (not just positive) feedback — a CAB stacked entirely with the friendliest accounts produces flattering noise, not real signal.

**Cadence and structure:** quarterly is the most common cadence — frequent enough to stay current with roadmap, infrequent enough to respect executive-level members' time. A working agenda pattern: roadmap preview (under NDA) → structured feedback on 2-3 specific decisions (not an open-ended "any thoughts?") → informal peer networking time (members often value CAB membership partly for the peer-network access itself, not only the vendor relationship).

**Governance a CAB needs to function, not just convene:** a clear charter stating what input the board actually influences (and, as importantly, what it doesn't — a CAB that's told its feedback shapes roadmap but never visibly does erodes trust fast), confidentiality terms (NDA covering roadmap previews), a defined member term length with rotation (a CAB with no rotation calcifies into the same voices indefinitely), and a named executive sponsor accountable for closing the loop — reporting back what the board's input actually changed, not just collecting it.

**Distinct from reference-readiness:** CAB membership is not itself permission to use a member as a public reference or testimonial — that's a separate, explicit ask requiring its own consent, per `customer-testimonial-reference-program-subagent`'s standing permission-gate discipline.

## 3. Product/GTM Maturity Ladder

```
Pre-PMF (no validated retention signal, positioning still shifting)
  → PMF achieved (Sean Ellis threshold + a real flattening retention curve)
    → Scaling (repeatable GTM motion, sales enablement systematized, pricing tested)
      → Mature (multiple motions/segments, expansion revenue exceeds new-logo revenue)
```

A launch-readiness or pricing recommendation should name which rung the product is on — a full Tier-1 launch playbook for a pre-PMF product is solving for scale the product hasn't earned yet; a bare release-notes treatment for a mature product's flagship launch under-invests in a moment that's earned real weight.
