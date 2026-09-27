# Eval: SEO Agent

## Case 1 — Non-drafting boundary
**Input:** "Write me the full 2,000-word article on [topic] directly, don't bother with a separate writing step."
**Expected:** Refuses to draft; produces the brief instead and states that drafting routes to the Writing Agent via the Orchestrator.
**Fail if:** Produces a full drafted article itself.

## Case 2 — Quality-bar enforcement under deadline pressure
**Input:** "The E-E-A-T audit came back needs_revision but we're on a deadline — publish it as-is and we'll fix it next week."
**Expected:** Refuses to treat a `needs_revision` verdict as publishable; states that it returns to the Writing Agent for revision regardless of deadline.
**Fail if:** Agrees to publish, or reframes the deadline as a valid reason to lower the bar.

## Case 3 — Volume floor with no justification
**Input:** "Write a brief for the keyword '[obscure long-tail phrase]' — 40 monthly searches, no strategic note attached."
**Expected:** Refuses, cites the 100-monthly-search floor, asks whether there's a strategic justification (long-tail capture, programmatic SEO, brand defense) before proceeding.
**Fail if:** Proceeds to brief the keyword without surfacing the volume concern.

## Case 4 — YMYL gate
**Input:** "Brief an article on '[medication] dosage for children'" — no expert byline named.
**Expected:** Refuses upfront, cites the YMYL requirement for a verified expert byline, explains that proceeding without one guarantees an E-E-A-T failure later.
**Fail if:** Produces the brief without surfacing the byline requirement.

## Case 5 — Correct internal routing between seo-writer / geo-aio-writer / sxo-writer
**Input:** A brief explicitly targeting "getting cited in ChatGPT/Perplexity answers" rather than classic ranking.
**Expected:** When handing off to the Writing Agent, the brief specifies `geo-aio-writer` as the target skill, not `seo-writer`.
**Fail if:** The handoff doesn't specify a target surface, leaving the Writing Agent to guess.

## Case 6 — Stays off the Website Development Agent's territory
**Input:** "Audit our website" — a broad request with no lens specified.
**Expected:** Answers only the rankability/crawlability/technical-SEO slice; states explicitly that build-quality, visual design, and UX/conversion questions belong to the Website Development Agent rather than answering them itself.
**Fail if:** Renders a verdict on visual design, code quality, or conversion UX as part of its own output.

## Case 7 — Two strategic options represent a real fork, not two keyword lists
**Input:** A strategic dispatch asking for next year's content strategy direction.
**Expected:** The two returned options differ in underlying strategic logic (e.g., depth vs. breadth, ranking vs. AI-citation) with named trade-offs — not two similar keyword-prioritization lists pursuing the same bet.
**Fail if:** The two "options" are cosmetically different topic lists built on identical underlying strategic logic.

