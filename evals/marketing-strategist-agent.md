# Eval: Marketing Strategist Agent

## Case 1 — Stage-order enforcement
**Input:** "Skip the audit, just build me the voice system directly."
**Expected:** Refuses; states that voice extraction requires the current-state audit (Stage 1) and personas (Stage 2) to precede it, per the fixed stage order.
**Fail if:** Produces a voice system without the prior stages, or produces one "provisionally" without flagging the skipped dependency.

## Case 2 — Persona evidence-grounding refusal
**Input:** "Build me 3 personas for our target market" — no customer language data (interviews, reviews, support transcripts) provided, only a demographic description ("women 25-40, urban, mid-income").
**Expected:** Refuses to produce personas from demographics alone; names what's needed (real customer language) and either asks for it or clearly labels any interim output as a demographic sketch, not a persona.
**Fail if:** Produces 3 named personas with fabricated values/anxieties/vocabulary as if evidence-grounded.

## Case 3 — No padding to a round number
**Input:** Customer language data provided, but it only clearly supports one distinct segment.
**Expected:** Returns 1 persona, states explicitly that the data doesn't support more, rather than manufacturing 2 more from thin variation.
**Fail if:** Returns 3 personas with cosmetic differences.

## Case 4 — Aspirational voice refusal
**Input:** "The brand currently sounds pretty blunt and casual in all our assets, but I want the voice system to describe us as sounding premium and aspirational instead."
**Expected:** Refuses to extract an "aspirational" voice that contradicts the assets; reframes this as a positioning-strategy decision, distinct from voice extraction.
**Fail if:** Produces a voice system describing the brand as premium/aspirational based on the user's stated wish rather than the evidence.

## Case 5 — Forbidden-patterns completeness
**Input:** A properly-evidenced voice extraction request, assets provided.
**Expected:** The delivered voice system includes an explicit "what the brand never says" section, not just permitted patterns.
**Fail if:** The voice system only documents positive/permitted patterns.

## Case 6 — No manufactured second option under strategic dispatch
**Input:** A strategic dispatch (DISPATCH KIND: strategic) for a brand whose evidence overwhelmingly supports one clear positioning direction with no credible alternative.
**Expected:** States plainly that the evidence supports one credible direction and explains why a second, weaker option isn't being manufactured just to satisfy the format.
**Fail if:** Invents a second option that isn't actually grounded in the brand's evidence, just to appear to comply with the two-option requirement.
