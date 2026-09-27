---
name: brand-voice-extractor
description: Activate when the user wants to extract, document, or operationalize a brand's voice from existing content — site copy, blog posts, social, customer support, founder writing, podcast transcripts, video scripts. Produces a structured voice guide with concrete linguistic markers (sentence patterns, vocabulary tendencies, rhythm, what's said and not said), exemplar phrases, and an operational rubric for evaluating future content. Refuses to invent a voice from a logo or moodboard alone — voice is a property of language and requires language samples to extract. Refuses to produce vague "warm but professional" descriptors that any team could write; insists on the specifics that distinguish this brand from its category.
---

# Brand Voice Extractor

A useful voice document is one a writer can hold next to a draft and instantly tell if the draft sounds like the brand. Vague descriptors fail this test. Specific linguistic patterns pass it.

## Core principle

**Voice lives in the words, not the adjectives about the words.** "Confident, warm, witty" describes thousands of brands. The voice extractor's job is to find what's specific: which sentence shapes, which vocabulary, which rhythms, which tonal moves recur. The output is a guide a copywriter can imitate, not a mood the team can argue about.

## When to use

| Situation | Activate? |
|---|---|
| Established brand wants voice documented for new team / agency / AI use | Yes |
| Founder wrote everything and now needs to scale via others | Yes |
| Brand voice exists implicitly but writers are off-tone | Yes |
| Multi-brand house wants distinct voice per sub-brand | Yes |
| New brand without any content yet | No — extract requires samples; suggest building voice via founder interviews + iterative drafts |
| User just wants "make it sound friendlier" | Reconsider — that's editing, not voice extraction |
| Logo + brand colors but no copy samples provided | Refuse — request samples |

## Workflow

### Step 1: Gather corpus

Need a meaningful sample. Minimum useful corpus:
- 5–10 pages of site copy (homepage, about, key product pages)
- 5+ long-form pieces (blog posts, case studies)
- 10+ social posts in the brand's primary platform
- 5+ customer-facing emails
- 1+ founder/exec long-form (essay, podcast transcript)

If the corpus is small (<2K words), flag the limitation; voice extraction from thin data is unreliable.

If the brand has multiple authors, mark which is which. Founder voice and team voice diverge; pick whose voice is the brand or note the blend explicitly.

### Step 2: Multi-pass read

**Pass 1: Tone**
- Formal vs casual? Where on the spectrum (1–5)?
- Earnest vs ironic? Where?
- High vs low intensity? (Calm and considered vs energetic and bold)
- Authority posture: peer / expert / mentor / fellow-traveler?

**Pass 2: Sentence-level patterns**
- Sentence length: short (≤10), medium (10–20), long (20+) — what's the mix?
- Rhythm: declarative / fragments / questions / lists / parenthetical asides?
- Opens: how do paragraphs / sections start? Hooky? Setup-then-pivot? Direct?
- Closes: how do they end? Punch line? Soft fade? Call to action? Open question?

**Pass 3: Vocabulary**
- Specific recurring words / phrases the brand uses (and the obvious synonyms it doesn't)
- Jargon density and which jargon (insider terms vs accessible)
- Metaphors and what they're drawn from (sports? craft? nature? engineering?)
- Capitalization conventions (Title Case rituals, ALL CAPS for emphasis)
- Punctuation tics (em dashes, ellipses, parentheticals, exclamation points)

**Pass 4: Tonal moves**
- Humor: deadpan, self-deprecating, observational, absurd, none?
- Vulnerability: does the brand admit hard things, fail-forward stories, behind-the-scenes mess?
- Stance: takes positions, or stays neutral?
- Customer address: "you" frequency, "we" frequency, addressing customer as peer / expert / etc.
- Treatment of competitors: named, unnamed, ignored, mocked?

**Pass 5: What's NOT said**
- Industry clichés the brand avoids ("synergy", "leverage", "unlock value")
- Topics the brand stays away from
- Tonal registers absent (e.g., never angry, never urgent, never overly excited)
- Formats avoided (e.g., never lists, never one-liners, never dense paragraphs)

### Step 3: Codify into a voice guide

Structure the output for use, not display:

```
# [Brand] Voice Guide

## Voice in 30 seconds
[A two-sentence positioning that captures the distinctive feel — should NOT use "warm" "authentic" "premium" etc.]

## Voice spectrum
| Axis | Scale | Where we sit |
|---|---|---|
| Formal ←→ Casual | 1–5 | 2.5 — "professional but loose" |
| Earnest ←→ Ironic | 1–5 | 1.5 — mostly earnest, occasional dry aside |
| Calm ←→ High-energy | 1–5 | 2 — measured |
| Concise ←→ Expansive | 1–5 | 4 — we explain, with care |

## Sentence DNA
- Average sentence length: 14 words
- Mix: ~60% medium, 25% short for emphasis, 15% long for nuance
- Open with a concrete claim or observation; rarely with throat-clearing
- Use em dashes — like this — for asides
- One-sentence paragraphs allowed for emphasis. Use sparingly.

## Vocabulary
**We say**
- "[characteristic word/phrase 1]" — used in [context]
- "[characteristic phrase 2]"
- ...

**We don't say**
- "[cliché 1]" — too [reason]
- "[corporate phrase 2]"

## Tonal moves we make
- [Move 1]: [example]
- [Move 2]: [example]

## Tonal moves we don't make
- [Avoidance 1] — because [reason]

## Address
- We say "you" when [...]
- We say "we" when [...]
- We don't address customer as [...]

## Examples
- ✅ On-voice: [3-5 actual or close-paraphrase examples from corpus]
- ❌ Off-voice: [2-3 examples of common drift; flag what's wrong]

## Quick reference for writers
- Open with [pattern]
- Avoid [list]
- When uncertain, [decision rule]
```

### Step 4: Build an evaluation rubric

Voice guides are useless without a way to evaluate drafts. Provide a checklist a writer / AI can run on a draft:

```
Voice check rubric
- [ ] Does the open feel like us (not throat-clearing, not generic hook)?
- [ ] Sentence rhythm varies (not all medium, not all short)?
- [ ] Did we use any of our vocabulary tells?
- [ ] Did we avoid the cliché list?
- [ ] Tonal moves present and not over-used?
- [ ] Reads aloud naturally in our voice (do the read-aloud test)?
```

For AI-generated content (Claude / GPT writing as the brand), provide a system prompt template that encodes the rubric.

### Step 5: Stress-test on new contexts

Before declaring the guide done, draft a few hypothetical pieces in voice across formats the brand hasn't covered yet:
- Press release announcing a hard thing (layoffs, product sunset)
- Apology / acknowledgment of a mistake
- Technical explainer outside main category
- Founder LinkedIn post

If the guide doesn't help write these convincingly, it's underspecified.

## Output format

The voice guide itself is the output (see Step 3 template). Length: 1500–3000 words. Longer becomes unread; shorter becomes vague.

Supplementary deliverables when useful:
- A one-page cheat sheet (the rubric + 10 vocab tells + 5 examples)
- A Claude / GPT system prompt that encodes the voice for AI writing assistance
- An anti-pattern catalog for review (what off-voice drift commonly looks like for this brand)

## Anti-patterns

1. ❌ Reaching for adjectives ("warm", "authentic", "human") without grounding them in linguistic specifics — the test: could this descriptor apply to 100 other brands?
2. ❌ Over-codifying every paragraph shape the corpus contains — voice has variety; capture tendencies, not rules
3. ❌ Conflating tone (mood-of-the-moment, varies) with voice (consistent across moods) — angry-voice and celebratory-voice can both exist within one brand voice
4. ❌ Extracting from a corpus of varied authors without flagging — produces a Frankenstein voice that's no individual writer's
5. ❌ Building a voice from inspiration brands ("we want to sound like Mailchimp") instead of from the brand's own samples — no extraction, no real voice
6. ❌ Producing a guide longer than 3000 words — won't be re-read, won't be applied
7. ❌ Vocabulary lists that are too obvious ("we say 'simple' a lot") — surface-level, not distinguishing
8. ❌ Skipping the "what's NOT said" section — half of voice is restraint
9. ❌ Treating brand voice as a static document — it should evolve; recommend annual re-extraction
10. ❌ Voice guide that's pitched at marketing only — voice applies to product copy, error messages, support replies, hiring pages; the guide should cover all of it
11. ❌ Producing a guide that's enthusiastic about voice but doesn't include actual examples from the corpus — examples are the load-bearing element
12. ❌ Inventing voice prescriptions the corpus doesn't actually evidence — audit recommendations against the corpus
13. ❌ Failing to flag corpus weakness (small, single-format, single-author) — gives false confidence
14. ❌ Voice guide that doesn't address how to write hard messages (apologies, bad news, complex topics) — those are exactly when teams need it most

## Reference files

- `references/voice-frameworks.md` — established frameworks (Nielsen Norman tone dimensions, Brand Voice Quadrants from various agencies); use as reference, not as default output structure

## Confidence calibration

- Patterns extracted from substantial corpus: high
- Patterns from <2K words: low — flag the limit
- Predicting what the brand "should" sound like: refuse — extract what it does sound like
- Whether a draft is on-voice: medium — borderline cases are subjective; recommend voice committee review for high-stakes copy
- Voice guides aging well: medium — recommend annual re-extraction as brand evolves
