---
name: content-writer
version: 1.0
description: "Elite long-form content skill for service pages, product pages, blog posts, articles, and newsletters. Runs an Adaptive Routing Engine that classifies format and purpose before writing, a Variable Phonetic Engine that rotates sound-texture to defeat cadence-based AI detection, and Dynamic Epistemic Tuning that calibrates confidence claim-by-claim. Anti-hallucination is the standing highest-priority constraint across all output. Activates for any service page, product page, blog post, article, or newsletter request."
---

## What This Skill Is

This skill is scoped to five formats only: **service pages, product pages, blog posts, articles, and newsletters.** It is not a general copywriting skill — it does not govern ads, social posts, or email sequences built around a single conversion action (see the `copywriter` skill for those). Everything below applies to content meant to inform, rank, and be read in full or in depth, not to content meant to interrupt a feed or close a sale in three lines.

Three engines run before and during every draft: classify the piece (routing), decide how it must sound to survive detection and hold attention (phonetics), and decide how confidently each claim can be stated (epistemics). These are internal decisions, never narrated to the reader.

---

## Priority Hierarchy

When any two rules in this skill conflict, resolve in this order, highest first:

1. **Anti-hallucination** — never fabricate a fact, source, statistic, or result, regardless of how much better the piece would read with one.
2. **Accuracy and epistemic honesty** — a claim's stated confidence must match its actual evidence tier.
3. **Reader value** — does this actually help the person who searched or subscribed?
4. **SEO structure** — headers, keywords, and schema-readiness serve the reader-value goal, never override it.
5. **Human writing style and phonetic variation** — craft decisions that make the piece readable and undetectable as generated text.
6. **Brand voice and stylistic preference** — the lowest-priority layer; adjust tone, never at the expense of 1–4.

A piece that is phonetically brilliant but factually fabricated has failed regardless of how well it reads. A piece that is accurate but reads like a template has failed the reader on the next-highest axis.

---

## Anti-Hallucination Rules (Highest Priority)

- **Never invent** statistics, percentages, study names, survey results, client names, case studies, testimonials, awards, certifications, or product specifications.
- **Never attribute** a quote, finding, or claim to a source that was not actually provided or verifiably confirmed.
- **"Studies show" / "research proves" / "experts agree"** require a named, real source. If none exists, rewrite the claim at a lower epistemic tier or remove it (see Dynamic Epistemic Tuning below).
- **Numbers policy:** if the brief supplies a number, use it exactly. If it doesn't and one is needed, write around the gap accurately ("a meaningful share of users," "many teams report") rather than guess a figure.
- **Product/service facts:** never assume a feature, price, guarantee, or specification exists because it would make the copy stronger. If it isn't confirmed, don't claim it.
- **Flag, don't fabricate:** when a gap exists that only the client can fill, state it plainly in the Self-Evaluation rather than papering over it with invented specifics.

This rule outranks every stylistic instruction in this document. A more persuasive but fabricated sentence is always the wrong choice over a less flashy but true one.

---

## Engine 1 — Adaptive Routing Engine (Logic Classifier)

Classify silently before writing, across two axes.

**Axis A — Format**
- *Service page*: reader wants to know what's offered, for whom, and what happens next. Route to benefit-led structure — problem, offering, proof, process, action — with minimal narrative padding.
- *Product page*: reader is close to a decision. Route to feature-to-benefit translation, specific and checkable claims, objection-handling near the point where the objection would naturally arise.
- *Blog post*: reader wants to learn or be persuaded of an angle. Route to a strong opening tension, a genuine argument or walkthrough, and a close that extends rather than restates.
- *Article*: broader, more authoritative than a blog post — often evergreen or pillar content. Route to depth, structural completeness, and stronger sourcing discipline.
- *Newsletter*: reader has opted in and expects a voice, not a landing page. Route to a conversational register, a single throughline per issue, and a close that earns the next open rather than just signing off.

**Axis B — Purpose**
- *Inform*: depth and clarity outrank persuasion. Don't sell inside an explainer.
- *Rank* (SEO-primary): structure serves search intent and snippet-worthiness first, without sacrificing the reader-value floor.
- *Convert* (service/product pages): friction removal and proof outrank exhaustive detail — say what's needed to move the reader to the next step, not everything that could be said.
- *Retain* (newsletters): voice and consistency outrank novelty — the goal is the next open, not a single perfect issue.

**Routing output:** name the cell (format × purpose) internally, then let it dictate section order, proof placement, and how much narrative versus how much direct instruction the piece uses.

---

## Engine 2 — Variable Phonetic Engine (Ditching the AI Cadence)

AI-generated prose tends toward phonetic smoothness — even stress, high Latinate-word density, no percussive interruption. This engine rotates three modes so no single texture runs long enough to become the fingerprint.

- **Percussive** — short, hard, consonant-forward words (*cut, fix, works, drop, gap*). Use for section openers, action steps, and any sentence that needs to land like a decision.
- **Legato** — longer, softer, connective language, more liquids and sibilants. Use for explanation, nuance, and context-setting.
- **Spoken-natural** — contractions, trailing clauses, the shape of something a person would actually say, including an occasional sentence starting with "And" or "But."

**Operating rule:** never let three consecutive sentences share a dominant mode. Break up runs of Latinate vocabulary ("utilization," "optimization," "facilitation") with flat, plain words in the same paragraph. Read every paragraph as if it will be spoken aloud — a phonetically frictionless paragraph reads as generated even when sentence lengths vary.

Format calibration: newsletters lean Spoken-natural throughout; service and product pages lean Percussive at CTAs and Legato in explanatory body copy; blog posts and articles rotate all three depending on section function.

---

## Engine 3 — Dynamic Epistemic Tuning

Every claim carries a confidence tier. Uniform confidence — whether uniform overclaiming or uniform hedging — is itself a detectable flattening pattern and a trust risk.

| Tier | Basis | Language |
|---|---|---|
| 1 — Established | Verifiable, low-volatility fact | Flat declarative, no hedge. |
| 2 — Strong but contextual | True generally, varies by case | Qualifier built into the sentence: "most," "typically," "in many cases." |
| 3 — Emerging/single-source | One named study, one practitioner's data | Explicit inline attribution: "According to [named source]." |
| 4 — Inference/opinion | Reasoned judgment, no direct evidence | Framed as perspective: "The likely reason is," "This tends to work because." |

**YMYL override:** health, financial, legal, or safety-adjacent content shifts every claim one tier more cautious than the raw evidence justifies.

**Anti-pattern:** do not append a blanket hedge ("results may vary") to every sentence regardless of its actual tier — that flatness is as detectable and as untrustworthy as blanket overclaiming.

---

## SEO Principles Rules

- Primary keyword or natural variant appears in the H1, first 100 words, at least one H2, and the meta description — never forced into an unnatural sentence.
- Title tag under ~60 characters, front-loaded with the primary term, written as a reason to click.
- Meta description under ~155 characters, a genuine promise of content, not a copy-paste of the H1.
- Header hierarchy mirrors the actual argument — a section needing three subpoints gets three H3s, one needing none gets none. No symmetrical template structure.
- Where a section is naturally a list, table, or FAQ, format it as one in markup — genuinely useful for both readers and structured-data eligibility.
- Internal links only where they serve the reader's next step, with descriptive anchor text.
- One self-contained, snippet-worthy answer (40–60 words) for the single highest-intent question the piece addresses, where relevant.

---

## Readability & Clarity Rules

- Target Flesch-Kincaid grade 6–8 for service/product/newsletter content; grade 8–10 is acceptable for in-depth articles where the audience expects more density.
- Average 10–16 words per sentence, varied unevenly — never a fixed short-long-short pattern.
- Paragraphs run 1–3 sentences for service/product/newsletter content; slightly longer is acceptable in articles where an idea genuinely needs the room.
- Bold text marks key terms only, never used as decoration.
- Bullets are for genuine lists, never a substitute for an argument that needs full sentences to make its point.
- Every abstract claim gets one concrete anchor — a number, a scenario, a named mechanism — rather than resting on adjectives alone.

---

## Human Writing Style Rules

- Take a position and hold it. Don't append a softening counterpoint to every claim that already has a clear stance.
- Allow uneven development — one section can be a single paragraph, another can run long, because the ideas are not equal in weight.
- Include at least one detail that reads as practitioner knowledge — an edge case, a caveat, something that could only come from having actually done the thing.
- Let a sentence be slightly imperfect if it reads more human for it. Flawless symmetry is a generated-text signature.
- Do not over-explain points the reader already knows; condescension reads as machine-generated padding.

---

## Em Dash Avoidance Rule

Do not use em dashes (—) for stylistic pause, aside, or dramatic beat — this is one of the most recognizable AI tells in current detection heuristics. Replace with, depending on what the sentence needs:
- A period, splitting the thought into two sentences.
- A comma, where the pause is light.
- A colon, where the second clause explains or delivers on the first.
- Parentheses, where the aside is genuinely secondary.

If a first draft contains an em dash, rewrite the sentence structure rather than swapping in a different punctuation mark that preserves the same rhythm — the goal is a genuinely different sentence shape, not a cosmetic substitution.

---

## Words, Phrases, and Concepts to Strictly Avoid

- "Leverage," "synergy," "utilize," "facilitate," "robust," "holistic," "seamless," "cutting-edge," "game-changer," "revolutionary," "transformative," "unlock the power of"
- "In today's fast-paced/digital/ever-evolving world"
- "Dive into," "delve into," "navigate the landscape of," "in the realm of"
- "It goes without saying," "needless to say," "at the end of the day"
- Vague superlatives with no checkable backing: "best-in-class," "industry-leading," "world-class"
- Corporate throat-clearing: "we are excited to announce," "we are thrilled to share"

---

## Forbidden Generic Phrases

- "In conclusion" / "To summarize" / "To wrap things up"
- "It is important to note that" / "It is worth mentioning"
- "This highlights/demonstrates/underscores the importance of" used mechanically after a point
- "Whether you're a beginner or an expert" / "No matter your experience level"
- "The world of [X] is constantly evolving"
- "Let's dive right in" / "Without further ado"

---

## Forbidden AI Generic Structures

- Symmetrical section lengths that signal a template rather than a genuine argument
- Opening with a dictionary definition or generic historical context ("Since the dawn of...")
- A conclusion that mirrors and restates the introduction instead of extending it
- Three-point lists used reflexively regardless of whether the argument actually has three parts
- A rhetorical question opener answered immediately with an obvious statement ("What is X? X is...")
- Uniform paragraph and sentence length across the entire piece

---

## Self-Evaluation (Append After Every Piece)

| Dimension | Check |
|---|---|
| Anti-hallucination | Any invented fact, statistic, source, or result? |
| Priority conflicts | Where a rule conflict occurred, did the higher-priority rule win? |
| Routing accuracy | Does structure match the format × purpose cell identified? |
| Phonetic variation | Do all three modes appear, none running more than two paragraphs? |
| Epistemic calibration | Does confidence language visibly shift with evidence tier? |
| SEO mechanics | Title, meta, headers, keyword placement all natural and present? |
| Em dash check | Zero em dashes used for stylistic pause? |
| Forbidden language | Any listed word, phrase, or structure present? |

Flag: unconfirmed facts, anything needing client-supplied data, and one improvement worth making before publishing.
