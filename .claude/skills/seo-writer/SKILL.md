---
name: seo-writer
version: 1.0
description: "Elite search-optimized content skill. Combines an Adaptive Routing Engine that classifies query intent and SERP mechanics before a word is written, a Variable Phonetic Engine that rotates sound-texture patterns to defeat cadence-based AI detection, and Dynamic Epistemic Tuning that calibrates confidence language claim-by-claim against E-E-A-T and YMYL risk. Activates for blog posts, pillar pages, product/category copy, comparison content, and any deliverable meant to rank and hold position on Google or another search engine."
---

## What This Skill Is

Ranking content and readable content are not the same target, and writing toward only one of them produces mediocre output on both axes. This skill runs three engines in sequence, silently, before and during writing: classify what the page must do (routing), decide how it must sound to survive detection and hold attention (phonetics), and decide how confidently each claim can be stated without lying or hedging like a machine (epistemics). Nothing below is a checklist to consult — it is the decision logic that should already be running by the time the first sentence is drafted.

---

## Engine 1 — Adaptive Routing Engine (Logic Classifier)

Before writing, classify the request against four axes. The combination determines structure, not just tone. Do this silently; never show the classification to the reader unless asked.

**Axis A — Search Intent**
- *Informational*: reader wants to understand something. Route to explanation-first structure, definition anchored early, depth over persuasion.
- *Navigational*: reader wants a specific destination (brand, tool, page). Route to short, unambiguous confirmation content — do not pad.
- *Commercial investigation*: reader is comparing options before deciding. Route to comparison structure — criteria stated up front, trade-offs named honestly, no single option flattered without reason.
- *Transactional*: reader is ready to act. Route to friction-minimized structure — answer, proof, action, in that order. Cut anything that delays the CTA.

**Axis B — SERP Feature Target**
Identify what result type the piece is actually competing for, because each demands a different on-page shape:
- Featured snippet (paragraph): the target answer must live in one self-contained 40–60 word block, answerable without reading anything above it.
- Featured snippet (list/table): the answer must already exist as a clean, parallel list or table in the source markup, not prose that could be listified.
- People Also Ask: anticipate 3–5 adjacent questions and answer each as its own short, standalone unit — PAA rewards modularity, not narrative flow.
- Standard blue link only: structure can be looser, but the opening 100 words still carry the primary keyword's intent explicitly.

**Axis C — Funnel Stage**
TOFU (awareness) → depth and trust-building, minimal selling. MOFU (consideration) → comparison and proof. BOFU (decision) → urgency, specificity, friction removal. Never write BOFU tone into a TOFU piece; it reads as bait.

**Axis D — Competitive Density**
Thin SERP (weak or outdated top results): a solid, well-structured answer wins — do not over-engineer. Saturated SERP (established authorities, deep content already ranking): the piece needs a genuine differentiator — an angle, a dataset, a synthesis, or a specificity the top results lack. Writing the same structure as page-one competitors in a saturated SERP guarantees page two.

**Routing output:** state internally (not to the reader) which cell of this matrix the brief falls into, then let that cell dictate opening structure, section order, and where the snippet-target answer sits on the page.

---

## Engine 2 — Variable Phonetic Engine (Ditching the AI Cadence)

Sentence-length variation alone is not enough — detectors and readers both register *phonetic* smoothness: the way words sound and stress when subvocalized or read aloud (increasingly relevant as voice search and screen readers consume this same copy). AI text tends toward phonetically frictionless language — even stress, high proportion of Latinate polysyllables, absence of plosive or percussive sound. This engine rotates between phonetic modes so the pattern itself never becomes the fingerprint.

**Mode 1 — Percussive.** Short, hard, consonant-forward words: *cut, click, drop, stop, fix, gap*. Use for urgency, action steps, and section openers that need to land like a foot coming down.

**Mode 2 — Legato.** Longer, liquid, sibilant-flowing words and clauses: words with soft consonants (l, m, n, s, w) that carry a reader through explanation without jolting them. Use for context-setting and nuance.

**Mode 3 — Spoken-natural.** Contractions, trailing clauses, the shape of a sentence someone would actually say out loud, including the occasional sentence that starts with "And" or "But." Use to break up stretches of either Mode 1 or Mode 2 so no single texture runs for more than two paragraphs.

**Operating rule:** read every section aloud (internally). If a paragraph is phonetically smooth from first word to last — no percussive interruption, no mixed syllable weight — it will sound like it was generated, regardless of sentence-length variety. Deliberately break up runs of Latinate vocabulary ("utilization," "optimization," "implementation") with flat Anglo-Saxon words ("use," "fix," "run") in the same paragraph. Never let three consecutive sentences share the same dominant phonetic mode — rotate before the pattern sets.

Watch specifically for the "text-to-speech tell": a sentence that a voice assistant would read in one unbroken, evenly-stressed breath. Real speech has stress, a stumble point, an emphasis. Write toward that.

---

## Engine 3 — Dynamic Epistemic Tuning

Every claim in SEO content carries a confidence level, and stating all claims at the same confidence — whether that's uniform overclaiming or uniform hedging — is itself a flattening pattern that damages both trust and detection resistance. This engine assigns a tier to each claim and matches the language to it.

| Tier | Evidence basis | Language |
|---|---|---|
| 1 — Established | Broad consensus, verifiable, low volatility (e.g., how HTTP works) | Flat declarative. No hedge. |
| 2 — Strong but contextual | True in most cases, varies by situation (e.g., typical page-speed thresholds) | Light qualifier: "typically," "in most cases," "for most sites." |
| 3 — Emerging or single-source | Recent study, one practitioner's data, a Google statement not independently verified | Explicit attribution: "According to [named source]," "Early data suggests." |
| 4 — Inference or opinion | No direct evidence, reasoned judgment | Framed as perspective: "The likely reason is," "This tends to work because." |

**YMYL override:** for health, finance, legal, or safety-adjacent topics, shift every claim one tier more cautious than the evidence alone would justify, and never state a Tier 1 claim on a YMYL topic without it actually being medical/legal/financial consensus. E-E-A-T signals are earned by calibration, not by confidence.

**Anti-pattern to avoid:** do not hedge everything uniformly ("results may vary," "it depends on your situation" appended to every claim) — that flat, blanket caution is as detectable and as untrustworthy as blanket overclaiming. Confidence should visibly track evidence quality, sentence by sentence, not sit at one setting for the whole piece.

**Never invent:** statistics, study names, percentages, or client results. If a number is needed and unavailable, write around it accurately at Tier 4 rather than fabricate a Tier 1 statement.

---

## On-Page SEO Mechanics (Apply After the Three Engines)

- Primary keyword or its natural variant appears in the H1, the first 100 words, one H2, and the meta description — never forced into a sentence that reads unnaturally as a result.
- Title tag: front-load the primary term where possible, keep under ~60 characters, make it a reason to click, not a keyword stuffing exercise.
- Meta description: written as a Tier-appropriate promise of what's inside, under ~155 characters, never copy-pasted from the H1.
- Header hierarchy (H1 → H2 → H3) mirrors the actual argument structure, not a symmetrical template — a section that needs three subpoints gets three H3s, one that needs none gets none.
- Internal links: only where genuinely useful to the next step in the reader's task, anchor text descriptive of the destination, never generic ("click here").
- Image alt text: literal and specific, describing what's actually in the image, keyword-relevant only when honestly so.
- Schema-ready structure: FAQ-style questions get self-contained answers (see Engine 1, Axis B) so they can be marked up as FAQPage schema without editing.

---

## Forbidden Patterns

- "In today's fast-paced digital world," "unlock the power of," "game-changer," "seamless," "leverage synergies"
- "In conclusion" / "To summarize" as a closing crutch — extend the piece instead, don't restate it
- Keyword stuffing that breaks natural phonetic or grammatical flow
- Uniform hedge language applied to every claim regardless of evidence tier
- Symmetrical section lengths that signal a template rather than a genuine argument

---

## Self-Evaluation (Append After Every Piece)

| Dimension | Check |
|---|---|
| Routing accuracy | Does the structure match the actual intent/SERP-feature/funnel-stage cell identified? |
| Snippet readiness | Is there a self-contained 40–60 word answer block where a featured snippet is being targeted? |
| Phonetic variation | Do at least two phonetic modes appear across the piece, with no mode running more than two paragraphs? |
| Epistemic calibration | Does confidence language visibly shift with evidence tier, claim by claim? |
| YMYL caution | If applicable, is every claim shifted one tier more cautious than the raw evidence alone justifies? |
| On-page mechanics | Title, meta, headers, alt text, internal links all present and natural? |
| Differentiation | Does the piece contain something the current top-ranking pages do not? |

Flag: unconfirmed statistics, any claim needing a client-supplied source, and one structural change worth testing before publishing.
