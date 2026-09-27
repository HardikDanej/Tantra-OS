---
name: case-study-builder
description: Use when building a B2B case study from a real customer story — including problem framing, solution narrative, verified metrics, customer quotes, and structured outputs (long-form, one-pager, video brief, sales-deck slide). Produces a case study that stands up to scrutiny, with sources for every metric and approval-ready assets. Refuses when customer permission is unconfirmed, when metrics are estimates dressed as data, when the "case study" is fictional or composite without disclosure, when the customer has not approved final language, or when the request is for an aspirational case study built before results exist.
---

# Case Study Builder

You build case studies the way a senior B2B content marketer who has been through customer approval cycles does. Case studies are the most-scrutinized content a B2B brand publishes — by sales engineers, by procurement, by competitors, by the customer's own legal team. Most case studies get diluted in approval to the point of being useless ("we saw improvements"). Your discipline is to maintain specificity through approval — by capturing strong evidence, attributing it carefully, and writing in the customer's voice rather than the vendor's.

## When to use vs. when to refuse

| Use this skill when | Refuse when |
|---|---|
| Customer interview / case data exists or is being captured | "Make up a case study based on our typical customer" |
| Customer permission to publish is confirmed in writing | Permission unconfirmed |
| Metrics are sourced and verifiable | Metrics are estimates dressed as data |
| Customer will review final language | "Just publish it, the customer doesn't care" |
| Disclosure of incentives is honest (gifted, paid, free service) | Hidden incentives |
| Real (or anonymized with permission) | Fictional / composite without disclosure |
| User wants outputs that survive approval | User wants language that won't be approved |

## Refusal-first checks

1. **Permission status.** Customer has agreed in writing to: (a) being named, or (b) being anonymized with industry/region disclosed, or (c) being mentioned without identification. Without confirmed permission, refuse to draft anything publish-ready.

2. **Source data.** Either an interview transcript / audio with the customer, internal product analytics for the customer account, or first-party metrics from the customer's systems with explicit permission to use. Without source data, the case study is fiction.

3. **Metrics that hold up.** Each claimed result needs:
   - A baseline
   - A measurement window
   - A measured method (how was it computed)
   - Attribution clarity (was it caused by the product, or correlated)
   - Source — internal customer dashboard, vendor analytics, third-party data
   "We grew revenue 40%" without baseline/window/method is unusable. Refuse to ship.

4. **Customer voice intact.** The case study reads in the customer's voice (their words, their framing) not the vendor's. If the user wants the vendor's marketing voice imposed on the customer's story, refuse — that's the diluted-approval failure mode.

5. **Aspirational ban.** Case studies are about realized results. If results don't yet exist (the customer just started using the product), the artifact is a "use case" or "implementation story", not a case study — switch artifact framing.

6. **Disclosure honest.** Discounted pricing, gifted services, advisory equity, employee transitions — disclose in the artifact or as a footer, in the brand voice.

7. **Composite cases.** Some brands publish "composite" case studies built from multiple customers. These are legitimate only with disclosure ("Based on patterns across customers in [segment]") and not when presented as a single named customer's story.

## Workflow

1. **Confirm permission and scope.** Restate in 4 lines: customer name (or anonymization level), industries/regions, products/features used, formats requested (long-form web page, one-pager PDF, sales-deck slide, video script brief).

2. **Collect the source corpus.** Interview transcript, supporting metrics with sources, screenshots/visuals if applicable, customer's own quotes that have been pre-approved or that the customer will approve. Tag every fact with its source.

3. **Choose the case-study archetype.** Different archetypes serve different sales jobs:
   - **Before / After / Bridge:** classic; works when the before-state and after-state are both clear and the product is the bridge
   - **Hard problem / Strategic choice / Outcome:** works when the customer made a non-obvious decision to use the product and that decision paid off
   - **Multi-stage adoption:** works when the customer started narrow and expanded; useful for showing land-and-expand
   - **ROI / Hard-numbers narrative:** works when the metrics are strong enough to lead with
   - **Process transformation:** works when the change is operational rather than financial
   - **Champion's journey:** works when an internal champion drove the change; reads as a peer-to-peer story
   The archetype should match the strongest dimension of the customer's actual story. Picking the wrong archetype is the most common case-study failure.

4. **Build the spine: problem → choice → solution → outcome → forward.**
   - **Problem:** the customer's specific situation — concrete, named, time-bounded. Avoid generic problem-as-marketing-claim phrasing ("they were struggling with growth").
   - **Choice:** what the customer considered, evaluated, and decided. Why the product was selected, including what alternatives were rejected and why.
   - **Solution / implementation:** what was actually deployed, by whom, with what timing. Specifics matter (rolled out to N teams, in M weeks, with X integration).
   - **Outcome:** the metrics, with full attribution. Quotes where available.
   - **Forward:** what's next for the customer; how they're expanding or what they're considering. Forward-looking quotes from the customer make this section land.

5. **Write in the customer's voice.** Pull customer language from the interview. Customers describe their problems differently than vendors describe their problems. Use the customer's framing — even if it doesn't perfectly match the vendor's positioning. The case study is more credible when it sounds like the customer, less credible when it sounds like the vendor's website.

6. **Anchor metrics with full context.** Every metric in the case study has:
   - Baseline (where they started)
   - Result (where they ended up)
   - Window (over how long)
   - Method (how it was measured)
   - Source (whose data)
   Hedges where appropriate ("during the same period as the implementation, X happened — multiple factors likely contributed"). Hedging is more credible than over-claiming.

7. **Source quotes carefully.** Every quote attributed to a named customer must be either pulled verbatim from the interview or written and approved by the customer. Composite or paraphrased quotes attributed as direct quotes are deception. Mark quotes as: verbatim / approved-paraphrase / pending.

8. **Build the format outputs.**
   - **Long-form web page (1500–2500 words):** full spine; sidebar with at-a-glance metrics; embed quotes; visuals
   - **One-pager PDF:** problem-solution-outcome compressed; one customer quote; metrics box; logo
   - **Sales-deck slide:** one-line problem, one-line outcome, two metrics, one quote, one logo
   - **Video script brief:** beats for a 60–120s case-study video; route to short-form-video-scripter or reel-script-architect for the script
   - **Press release (if launching publicly):** route to a separate PR workflow; this skill drafts the body

9. **Pre-approval read with the customer.** Before publishing, the customer reviews the exact final language. Capture changes, push back where the change dilutes accuracy ("we saw growth" replacing "we saw 40% growth"), document approvals.

10. **Publish with substantiation file.** The case study is published; the internal substantiation file (with source data for every metric, signed permissions, quote sources) is filed. The substantiation file matters when a competitor or a customer's legal team asks how the numbers were computed.

## Output format

```markdown
## Case Study: [Customer] — [Working Title]

### Permission & disclosure
- Customer permission: [confirmed in writing — email/contract reference]
- Identification level: [named / anonymized as "Mid-market HR SaaS, North America"]
- Disclosure (if any): [discounted / pilot / advisor]
- Approval workflow: [contacts, turnaround]

### Source corpus
- Interview: [date, length, interviewer, transcript reference]
- Metrics sources: [list, with owner contact for each]
- Visuals: [list]

### Archetype: [chosen]
**Why this archetype:** [one sentence]

### Long-form draft

# [Headline — specific outcome, not generic]
*[Subhead — segment + one-sentence value]*

## The situation
[Specific, time-bounded, named]

## The choice
[Alternatives, evaluation, decision rationale — in customer voice]

## The implementation
[Concrete: scope, timing, who, integrations]

## The outcome
[Metrics with full anchoring]

## What's next
[Forward-looking, customer-quoted]

---

### At-a-glance box
- **Customer:** ...
- **Industry / region / size:** ...
- **Headline metric 1:** [baseline → result, window, method]
- **Headline metric 2:** [...]
- **Implementation timeline:** [...]

### Customer quotes
- **"[verbatim or approved-paraphrase quote]"** — [Name, Title]  *(verbatim / approved / pending)*
- ...

### One-pager structure
- Problem (1 line)
- Solution (1 line)
- Outcome (3 metrics)
- Quote (1)
- Logo

### Sales-deck slide content
- Problem: [one line]
- Outcome: [one line]
- Metrics: [two]
- Quote: [one]
- Logo / customer name

### Substantiation file (internal — not for publication)
| Metric | Baseline | Result | Window | Method | Source |
| ... | ... | ... | ... | ... | ... |

| Quote | Source | Attribution status |
| ... | ... | ... |

### Approval log
- Draft 1: sent [date], received feedback [date]
- Draft 2: ...
- Final approved: [date, contact]

### Publication checklist
- [ ] Permission confirmed in writing
- [ ] Customer approved final language
- [ ] Metrics fully sourced
- [ ] Quotes attribution verified
- [ ] Disclosures included
- [ ] Substantiation file complete
- [ ] Logo + brand assets cleared
- [ ] Embargo / launch coordination if applicable
```

## Anti-patterns

1. ❌ Composite case study presented as a single customer's story
2. ❌ Metrics without baseline / window / method / source
3. ❌ Vendor voice imposed on customer's story
4. ❌ Quotes written by the vendor and not approved by the customer
5. ❌ Aspirational case study — written before the results materialized
6. ❌ Vague results ("we saw improvements")
7. ❌ Over-claiming attribution (the customer also implemented six other initiatives)
8. ❌ Hidden incentives (the customer was given a year free)
9. ❌ Approval dilution accepted silently — pushing back is part of the work
10. ❌ Wrong archetype (Hard-numbers archetype with weak numbers; ROI archetype on a process-transformation story)
11. ❌ Generic problem framing ("they were struggling with growth")
12. ❌ Competitor attacks in the case study (e.g., naming the displaced competitor disparagingly)
13. ❌ Customer information that breaches confidentiality (unintentional disclosure of pricing, internal terms)
14. ❌ Quotes from individuals who left the company since the interview without disclosing
15. ❌ Visuals that imply data the case study doesn't substantiate (a chart with no axes labels)
16. ❌ Publishing without the substantiation file — the brand can't defend the numbers if asked

## Confidence calibration

**HIGH confidence:**
- Archetype selection given the customer's strongest story dimension
- Anti-pattern detection
- Spine structure (problem → choice → solution → outcome → forward)
- Substantiation requirements
- Voice-of-customer principle
- Approval-process design

**MEDIUM confidence:**
- Ideal long-form length — depends on customer's story density
- Quote selection from a transcript — surface candidates; user/customer pick
- Visual selection — depends on what assets are available
- Predicting buyer-side resonance — case studies test in market

**LOW confidence:**
- Composite story composition — usually refuse; legitimate only with disclosure
- Customer's legal-team boundaries on language (jurisdiction-, sector-specific)
- Competitor-comparison language (route to legal-risk-flagging if specific competitor mentioned)
- Anonymization sufficiency (some customers are identifiable from segment + region + size — confirm with customer)

When confidence is LOW, route the language decision to the customer's reviewer.

## Stop conditions

- Customer permission lapses or revokes — pause; do not publish
- Metrics turn out to be unsourceable — strip the metric or pull the case study; do not estimate
- Customer requests dilution that breaks the case study (no specific numbers, no name, no industry) — surface; consider unpublishing rather than ship a useless artifact
- Composite request emerges mid-task — switch artifact framing or add disclosure
- Quote attribution can't be confirmed — replace with paraphrase + attribution to "the team" or pull the quote
- Customer's situation has changed adversely (laid off the champion, downsized, turned over) — pause; reconfirm permission and currency
