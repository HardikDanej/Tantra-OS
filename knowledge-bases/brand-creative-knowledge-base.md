# Brand & Creative Marketing Knowledge Base

Dedicated knowledge base for the Brand & Creative Marketing agentic system (`brand-strategy-architecture-agent`, `content-marketing-editorial-strategy-agent`, `organic-social-community-building-agent`, and their thirty sub-agents). Closes the "no dedicated KB backing" disclosure most of those sub-agents carried before this file existed — `marketing-knowledge-base.md` remains the shared cross-system reference for general marketing taxonomy; this file goes deeper on the structural/governance and content/community disciplines specific to this system. Sliced the same way as every other KB in this repo: `kb_slice.py outline` first, then `section "<heading>"` — never read in full.

## 1. CORE TIER — Brand Strategy & Architecture

### 1.1 Brand Architecture Models

The four canonical structures (Aaker & Joachimsthaler's spectrum), ordered by parent-brand visibility:

| Model | Parent visibility | Sub-brand independence | Example pattern | When it fits |
|---|---|---|---|---|
| **Branded House** | Full — one master brand across everything | None — sub-brands are descriptors, not brands (e.g. "FedEx Ground") | Google, FedEx, Virgin | Single coherent audience, shared trust transfers cleanly, low reputational-contagion risk across lines |
| **Sub-brands (endorsed-lite)** | Full — master brand drives, sub-brand adds flavor | Low-moderate | Courtyard by Marriott, Google Pixel | Distinct product lines need their own identity but should still borrow master-brand equity |
| **Endorsed brands** | Partial — sub-brand leads, parent endorses in smaller type | Moderate-high | "A Kraft Company," Nabisco's cookie sub-brands | Sub-brand needs its own market position but parent's credibility is still a genuine asset |
| **House of Brands** | Minimal-to-invisible to the end consumer | Full — each brand competes independently, sometimes against each other | P&G (Tide vs. Gain), Yum! Brands | Portfolio spans genuinely different audiences/price points/reputational risk profiles; contagion between brands would be a net negative |

**Decision heuristic, in order:** (1) Do the audiences overlap enough that one brand promise serves both? If no → lean House of Brands. (2) Does a reputational event in one line meaningfully damage another? If yes and the audiences don't overlap → separate the brands. (3) Is the parent's equity strong enough to be a genuine asset for a new line, or would inheriting it actually constrain the new line's positioning? Weak/constraining → sub-brand or house-of-brands; strong/enabling → branded house or endorsed.

**Refusal-relevant fact:** a single-product company has nothing to architect yet — a Branded-House recommendation for a company with one product isn't an architecture decision, it's just the absence of one. Don't manufacture a framework application where there's no real multi-brand question.

### 1.2 Brand Equity Measurement Frameworks

Two canonical models, complementary rather than competing:

**Aaker's Five Assets** (David Aaker, *Managing Brand Equity*, 1991) — equity is the sum of:
1. Brand loyalty (the hardest to build, the most defensible once built)
2. Brand awareness (aided vs. unaided vs. top-of-mind — three different numbers, never conflate them)
3. Perceived quality (a belief, distinct from actual measured quality)
4. Brand associations (beyond perceived quality — lifestyle, values, imagery)
5. Other proprietary assets (patents, trademarks, channel relationships)

**Keller's Customer-Based Brand Equity (CBBE) Pyramid** (Kevin Lane Keller) — four ascending stages, each a prerequisite for the next:
```
Salience (do they know you exist / recall you in-category?)
  → Performance + Imagery (functional attributes / how it makes them feel & who uses it)
    → Judgments + Feelings (quality/credibility/superiority beliefs / emotional response)
      → Resonance (the peak: active loyalty, attachment, community, engagement)
```

A brand-health read that reports "resonance" metrics (advocacy, community engagement) while salience is still unestablished is measuring the wrong rung — always confirm the foundation before trusting the peak. Never invent a numeric score for any rung without real survey/behavioral data behind it; a framework is a lens for organizing real evidence, not a source of evidence itself.

### 1.3 Positioning Frameworks (structural layer — see `marketing-knowledge-base.md` for the general positioning discipline this extends)

- **Value Proposition Canvas** (Osterwalder) — map Customer Jobs/Pains/Gains against Products & Services/Pain Relievers/Gain Creators; a positioning claim with no named pain reliever or gain creator behind it is aspiration, not positioning.
- **Perceptual Mapping** — two-axis competitive map (commonly price/quality, or a category-specific pair) plotting the client and named competitors; the value of this map is entirely in the two chosen axes being the ones the *buyer* actually decides on, not the ones easiest to plot.
- **Category Membership vs. Point of Difference** (Keller) — a positioning claim needs both: what group does this belong to (so a buyer knows how to evaluate it at all), and what makes it different within that group. A claim with only one of the two either confuses the buyer about what they're even looking at, or gives them no reason to choose this one over the category norm.

### 1.4 Verbal Identity & Brand Voice Systems

**Tone-by-context matrix** — the operational unit `brand-verbal-identity-subagent` governs: voice stays constant, *tone* shifts by context (a support ticket, a product launch, a crisis statement, a job posting each need a different tone from the same underlying voice). A voice system with no context matrix is a voice description, not a governance document.

**Brand archetype reference** (Jung-derived, popularized by Mark & Pearson) — twelve archetypes (Innocent, Sage, Explorer, Outlaw, Magician, Hero, Lover, Jester, Everyman, Caregiver, Ruler, Creator) as a *starting vocabulary* for a voice's underlying character, never a substitute for real extraction from actual founder/exec-authored material — `brand-voice-extraction-subagent`'s own rule (no aspirational voice, ever) governs here too: an archetype label applied without real evidence it matches observed voice is exactly the kind of confident-sounding fabrication this whole system exists to refuse.

### 1.5 Co-Branding & Strategic Partnership Fit Assessment

`co-branding-partnerships-subagent`'s working framework for evaluating a proposed brand-to-brand alliance, joint product, or strategic partnership:

**Fit-assessment axes, checked in order:**
1. **Audience overlap direction** — does the partnership introduce each brand to a genuinely new, relevant audience segment, or just double-serve the same people? Meaningful co-branding usually trades on *asymmetric* audience access, not redundant reach.
2. **Equity transfer risk** — co-branding transfers perception in both directions, not just the intended one. A premium brand partnering with a discount brand risks importing "discount" associations back onto itself just as much as it exports "premium" outward — this is the single most common co-branding mistake, treating equity transfer as one-directional when it never is.
3. **Values/quality-tier compatibility** — a values or quality-tier mismatch (ethical-sourcing brand + a partner with an unresolved labor controversy; luxury brand + mass-discount partner) is a harder blocker than a mere aesthetic mismatch and should be weighted accordingly.
4. **Exit clarity** — what does unwinding the partnership look like if it underperforms or reputational risk emerges from the partner's side later? A co-brand with no defined sunset/exit mechanism is a standing reputational-contagion exposure with no circuit breaker.

**Common structures:** ingredient branding (component brand visible within a host product, e.g. a named-technology partnership), composite/joint-product branding (a genuinely new offering under both names), and promotional/campaign-level co-branding (temporary, campaign-bound, lowest commitment and lowest risk). Match the structure's commitment level to the actual confidence in the fit assessment — a campaign-level co-brand is the correct instrument for testing a partnership hypothesis before a deeper structural commitment.

## 2. REFERENCE TIER — Content, Community & Governance

### 2.1 Content Format Strategy Layer

Content Marketing & Editorial Strategy's ten sub-agents split along format lines; the underlying decision framework for *which* format fits *which* objective:

| Objective | Best-fit formats | Why |
|---|---|---|
| Build category authority over time | Long-form editorial, thought leadership | Depth signals expertise; compounds via search/backlinks |
| Demonstrate proof/credibility | Case studies, testimonials | Third-party validation beats self-assertion |
| Explain a complex product | Video, interactive tools (calculators/quizzes) | Show > tell for anything with real complexity |
| Reach a passive/ambient audience | Audio/podcast, social-native short-form | Fits into existing behavior rather than demanding a visit |
| Convert an already-warm visitor | Interactive content, visual assets on-page | Engagement mechanisms outperform static text at the decision moment |

### 2.2 Editorial Workflow Governance — RACI Pattern

`editorial-workflow-governance-subagent` designs the approval pipeline a piece of content moves through. The canonical structure to specify, not skip:

```
Draft → Fact/Legal Review (if claims-bearing) → Style/Brand-Voice Review → Editorial Sign-off → Publish → Post-publish Distribution
```

Each stage needs a named **R**esponsible (does the work), **A**ccountable (owns the sign-off — exactly one person per stage), **C**onsulted (Legal/Product/Support as relevant), **I**nformed (stakeholders who see the outcome but don't gate it). A workflow with no named Accountable at a stage isn't a workflow, it's a hope that someone will catch problems.

### 2.3 Community & Social Operating Models

**Community management maturity ladder** (the frame `organic-social-channel-management-subagent` and `private-community-operations-subagent` should locate a brand on before recommending a next step):
```
Ad hoc (reactive replies, no policy) → Policy-governed (response tiers, escalation paths exist)
  → Programmatic (ambassador/advocate structures, systematic UGC solicitation)
    → Owned ecosystem (a private community is the primary relationship surface, not a supplement to public channels)
```

**UGC/creator rights taxonomy** (`ugc-strategy-rights-management-subagent`, `creator-economy-licensing-subagent`) — four distinct rights bundles that get conflated in practice and shouldn't be:
1. **Repost right** — sharing the content on the brand's own channel, attributed
2. **Whitelisting/paid-amplification right** — running the content as paid media from the creator's handle
3. **Usage-beyond-platform right** — reuse in owned assets (website, email, print) outside the original platform
4. **Derivative-work right** — editing, remixing, or repurposing the content into something new

A single "yes, you can use my photo" consent does not automatically grant all four — `ugc-strategy-rights-management-subagent`'s refusal to assume unscoped consent maps directly onto this taxonomy.

### 2.3a Video Strategy & Production-Complexity Tiering

`video-strategy-production-subagent`'s format-to-objective mapping, one level deeper than the Content Format table in §2.1:

| Format | Best objective fit | Typical production-complexity tier |
|---|---|---|
| Explainer (animated or live-action) | Onboarding, landing-page comprehension of a complex product | Low-moderate (scriptable, often single-location or fully animated) |
| Testimonial/case-study video | Mid-funnel trust-building | Moderate (requires real customer coordination, on-location or remote interview) |
| Product demo | Bottom-funnel, sales-enablement | Low-moderate (talking-head + screen-capture, minimal location need) |
| Short-form social (Reels/Shorts/TikTok-native) | Top-of-funnel discovery, algorithmic reach | Low (fast-turnaround, vertical-native, often talent + phone-camera sufficient) |
| Long-form (YouTube, on-site depth content) | Category authority, search/on-site depth | High (heavier scripting, editing, and often multi-location needs) |

**Channel-format mismatch is the most common failure this sub-agent flags:** a format built for vertical, sound-off, fast-scroll social consumption (short-form) does not survive unedited on a horizontal landing page, and vice versa — re-editing for the destination channel is not optional polish, it's a structural requirement. **Complexity-tier honesty matters more than the tier itself:** understating a multi-location shoot as "simple" to make a recommendation look more feasible is the specific failure mode to guard against, since it sets a production team up to blow the timeline/budget on a plan that was never actually low-complexity.

### 2.3b Audio Strategy & Podcasting

`audio-strategy-podcasting-subagent`'s format-selection frame:

**Show-format archetypes:** interview (lowest production overhead, scales with guest access, strongest for building industry-relationship equity), solo/host-led (highest voice/authority control, most demanding on a single host's ongoing bandwidth), narrative/serialized (highest production cost and editorial complexity, strongest listener-retention mechanic once it lands, worst fit for infrequent or resource-constrained teams). Match the format to actual sustainable production cadence, not aspirational ambition — a narrative-serialized show a team can't sustain past episode 4 is worse than a simpler interview format run consistently for a year.

**Audio-ad placement taxonomy:** host-read (highest trust-transfer, inherits the audience's existing relationship with the host — the single strongest-performing ad unit in audio, and the reason programmatic audio can't fully substitute for it), dynamically-inserted programmatic spot (scalable, no trust-transfer, cheapest per-impression), and full-episode sponsorship (highest cost, highest exclusivity, works best when the show's audience and the sponsor's ICP are near-identical). Never recommend host-read placement without factoring the host's own credibility risk — an ill-fitting sponsor read damages the host-audience trust relationship the format's entire value depends on.

**Distribution reality:** a podcast is only as discoverable as its RSS-feed metadata (title, show/episode description, category tags) and its presence across the handful of directories (Apple Podcasts, Spotify, YouTube Music) that actually drive the bulk of discovery — treat directory-listing optimization with the same rigor as ASO metadata, not as an afterthought once the audio is recorded.

### 2.3c Live-Streaming & Real-Time Broadcasting

`live-streaming-broadcasting-subagent`'s platform-fit frame:

| Platform | Best-fit use case | Real-time engagement mechanic |
|---|---|---|
| Twitch | Gaming/hobbyist communities, long-session ambient viewership | Chat-driven, sub/bits economy |
| YouTube Live | Product launches, AMAs, evergreen-afterlife content (the VOD persists and keeps ranking) | Comment stream, Super Chat |
| Instagram/TikTok Live | Behind-the-scenes, ephemeral audience-building, algorithm-boosted discovery window | Real-time reaction/comment overlay |
| LinkedIn Live | B2B thought-leadership, executive visibility | Professional-audience Q&A |

**The irreducible logistics layer**, regardless of platform: a named moderator distinct from the on-camera talent (talent cannot simultaneously perform and moderate a live chat without quality degrading on one side), a tested-in-advance technical setup (stream software, connection redundancy, backup recording), and a pre-committed content runsheet even for a nominally "unscripted" AMA-style format — live formats fail more often from missing logistics than from weak content ideas.

### 2.3d Private/Owned Community Operations

`private-community-operations-subagent`'s platform-selection and moderation frame, extending the maturity ladder in §2.3:

**Platform fit:** Discord (real-time chat culture, strongest for younger/gaming-adjacent or highly active daily-engagement communities), Slack (professional/B2B communities, async-friendly, weaker for large-scale public discovery), Circle/Mighty Networks (owned, brandable, best when the community itself is a paid or gated product), a self-hosted forum (best long-term SEO/searchability for evergreen Q&A content, weakest real-time engagement). Match the platform to where the *audience already has social capital invested*, not to whichever platform is easiest to set up — migrating an established community to a new platform is a genuine retention risk, not a neutral technical decision.

**Moderation-policy floor, non-negotiable regardless of platform:** a written code of conduct, a named escalation path to a real human for policy violations, and defined consequences by severity tier (warning → temporary mute/timeout → removal) — an owned community with no written moderation policy is a liability the moment it has enough members for a real conflict to occur, not a "nice to have" for later.

**Member-lifecycle stages worth designing for explicitly:** onboarding (the single highest-leverage moment — an unwelcomed new member who never posts in the first week rarely becomes active later), core-contributor identification (a small percentage of members typically generate most content/value — name and specifically nurture this group rather than treating all members identically), and graceful offboarding/re-engagement (a dormant-member win-back cadence, distinct from the Revenue/CRM Agent's churn-winback work, which operates on customers, not community members).

### 2.4 Trademark & IP Governance Basics (non-legal-advice reference only)

Three distinct marks, commonly confused:
- **™** — an unregistered trademark claim; asserts use, confers no registered federal protection
- **®** — a registered trademark; legal protection exists, but only in the jurisdiction(s) and classes actually registered
- **©** — copyright, automatic upon creation of an original work, a completely different right from a trademark

`trademark-ip-governance-subagent` can name this distinction and flag an obvious mismatch (e.g., a company using ® on a mark it hasn't actually registered) — it can never declare a mark "clear," "protected," or "registered" as a legal conclusion; that always requires real counsel and a real clearance search.

## 3. Brand Maturity Ladder

The frame for calibrating how much a brand-strategy recommendation should assume already exists:

```
Undefined (no documented positioning/voice/identity)
  → Asserted (positioning exists on paper, untested against real competitive/customer evidence)
    → Validated (positioning has survived real competitive-axis stress-testing and customer language checks)
      → Owned (the market associates the claim with this brand specifically, not just the category)
        → Defended (the brand actively protects and extends the position against competitive erosion)
```

A `brand-relaunch` or `final_creative` recommendation should name which rung the brand is actually on — recommending "defend the position" work for a brand that's still at "asserted" is solving the wrong problem.
