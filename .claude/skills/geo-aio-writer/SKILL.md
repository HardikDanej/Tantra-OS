---
name: geo-aio-writer
version: 1.0
description: "Elite Generative Engine Optimization (GEO) and AI Overview (AIO) writing skill. Combines an Adaptive Routing Engine that classifies query type and target answer-engine before writing, a Variable Phonetic Engine tuned for text that survives being read aloud by voice assistants and extracted verbatim by LLMs, and Dynamic Epistemic Tuning that preserves a claim's true confidence level even when a model quotes it out of context. Activates whenever content is meant to be surfaced, cited, or synthesized by Google AI Overviews, Perplexity, ChatGPT search, Claude, or any other answer engine, rather than only clicked as a blue link."
---

## What This Skill Is

Ranking for a click and being selected as source material for a generated answer are different problems. An answer engine doesn't send a reader to the page — it extracts a fragment, strips the surrounding context, and re-serves that fragment as fact to someone who will never see the source. That changes the unit of writing from "page" to "extractable, self-contained claim." This skill routes each piece by query type and engine, writes every extractable unit in a phonetic register that survives both silent reading and text-to-speech, and locks each claim's epistemic status into the sentence itself so it can't be laundered into overconfidence once lifted out of context.

---

## Engine 1 — Adaptive Routing Engine (Logic Classifier)

Classify silently before writing, across three axes, because each combination demands a different extractable shape.

**Axis A — Query Type**
- *Fact lookup* ("what is," "how many," "when did"): the answer is a single, bounded fact. Route to a one-sentence declarative answer, stated first, with no pronoun or "this" that depends on prior sentences to resolve.
- *How-to / process*: route to a numbered sequence where each step is independently actionable — an engine should be able to extract step 3 alone and have it still make sense.
- *Comparison*: route to a structure where each entity's claim is paired with its own qualifier in the same sentence or adjacent cell, so extraction of one side doesn't misrepresent the other.
- *Opinion synthesis / "best X"*: route to attributed, plural framing ("multiple sources cite Y as strong for Z") rather than a single unattributed verdict, since these get extracted as if Claude itself endorsed the pick.

**Axis B — Target Engine Behavior**
- Google AI Overview favors short, schema-friendly, directly-answering passages near the top of the page — mirrors featured-snippet mechanics but with tighter self-containment.
- Perplexity and ChatGPT search weight recency, named sourcing, and clear entity attribution more heavily — unsourced claims are more likely to be skipped in favor of a competitor's cited one.
- Claude and similar assistants weight internal consistency and hedge-accuracy — a page that contradicts itself between sections is less likely to be trusted as a synthesis source.
Write for whichever engine the brief targets; if unspecified, default to the strictest common denominator: self-contained, sourced, internally consistent.

**Axis C — Extraction Unit**
Before writing a section, decide what the atomic extractable unit is: a sentence, a table row, a list item, a Q&A pair. Then make sure that unit, alone, with zero surrounding context, is complete, accurate, and not misleading. This is the single highest-leverage GEO decision — most GEO failures are units that only make sense inside their paragraph.

---

## Engine 2 — Variable Phonetic Engine (Ditching the AI Cadence)

Answer-engine content gets read twice over: once by a crawler/embedding model scoring it for retrieval, and increasingly a second time out loud by a voice assistant relaying the answer to a user with no screen. Both punish the same flatness — evenly-stressed, frictionless, all-Latinate phrasing — but for different reasons: retrieval models score it as generic (low information density per token), and voice synthesis renders it as a monotone that listeners disengage from.

**Rotate three modes across a piece:**
- **Percussive** — short, plosive, concrete words for the core answer sentence itself. A voice assistant reading "Replace the filter every 90 days" lands cleanly; "It is generally recommended that filter replacement occur at approximately ninety-day intervals" does not.
- **Legato** — softer, connective language for the explanation that follows the core answer, where nuance actually belongs.
- **Spoken-natural** — the shape of how someone would actually answer if asked out loud. This matters more here than in ordinary web copy, because voice answer engines are quite literally converting the text to speech.

**Operating rule specific to GEO/AIO:** the core extractable answer sentence should always sit in Percussive or Spoken-natural mode — short, direct, stress-clear — never in dense Legato phrasing, because that sentence is the one most likely to be lifted whole and spoken aloud. Save Legato for supporting material that won't be extracted standalone.

---

## Engine 3 — Dynamic Epistemic Tuning

This is the highest-stakes engine in this skill, because an answer engine will typically strip the surrounding hedge and present the extracted sentence with the engine's own default confidence — usually flatter and more certain than the source intended. The fix is to build the epistemic status *into the extractable unit itself*, not into surrounding context that might not travel with it.

| Tier | Evidence basis | Self-contained phrasing |
|---|---|---|
| 1 — Established | Broad, stable consensus | State flatly — this is the one tier where extraction without a hedge is safe. |
| 2 — Strong but contextual | True generally, varies by case | Build the qualifier into the same clause: "Most X require Y," not "X requires Y" with "most" only implied earlier. |
| 3 — Emerging/single-source | One study, one practitioner, unverified vendor claim | Name the source inside the sentence itself: "According to [named source], X." Never rely on a citation living in a separate paragraph — assume the extractor takes the sentence alone. |
| 4 — Inference/opinion | Reasoned judgment, no direct evidence | Frame the inference inline: "A likely explanation is X," never stated as settled fact. |

**Rule of self-containment:** every sentence at Tier 2 or below must carry its own hedge or attribution *inside that sentence* — assume zero surrounding context survives extraction. This is the core difference from ordinary SEO epistemic tuning, where hedges can live at the paragraph level.

**Never invent** statistics, studies, or named sources to satisfy Tier 3 phrasing — a fabricated source that gets extracted and repeated by an answer engine propagates the fabrication at scale, which is a materially worse failure mode here than in a single web page.

---

## Structural Mechanics for Extractability

- Put the direct answer to the implied query in the first sentence of the relevant section — not the second, not after a rhetorical setup.
- Use genuine lists and tables in markup (not prose dressed as a list) wherever the content is naturally enumerable — engines parse structured data far more reliably than narrative.
- Give each FAQ-style question its own complete, standalone answer — no "as mentioned above."
- Name entities explicitly rather than using pronouns across sentence boundaries ("the 2024 model" not "it," two sentences after the model was introduced).
- Keep one definitive, quotable definition of any key term the piece owns — engines favor a single crisp definition they can attribute consistently over several slightly different phrasings scattered through the page.

---

## Forbidden Patterns

- Core answer sentences that depend on a prior sentence to resolve a pronoun or "this"
- Hedges or citations that live outside the sentence they modify
- Fabricated sources, studies, or statistics at any tier
- Dense Legato phrasing in the primary extractable answer sentence
- Unattributed superlatives ("the best," "the top choice") without inline sourcing

---

## Self-Evaluation (Append After Every Piece)

| Dimension | Check |
|---|---|
| Routing accuracy | Does the extraction unit match the query type (fact/how-to/comparison/opinion)? |
| Self-containment | Does every Tier 2+ sentence carry its own hedge or source with zero external context? |
| Extractability | Could each core answer sentence stand alone, accurately, if lifted with nothing else? |
| Phonetic fit for voice | Does the core answer sentence read cleanly aloud in one natural breath? |
| Entity clarity | Are entities named explicitly rather than carried by pronoun across sentences? |
| Sourcing integrity | Are all named sources real and verifiable? |
| Structural parseability | Are naturally list-like or tabular facts actually marked up as lists/tables? |

Flag: any sentence that only makes sense with surrounding context, any unverified statistic, and one structural change that would most improve extraction accuracy.
