---
name: series-bible-architect
description: Activate when the user is creating or running an episodic content series — podcast, newsletter, video series, content campaign, social series, course module sequence — and needs a "bible" that documents the format, structural beats, recurring elements, voice, and editorial rules so contributors can stay consistent. Produces a working bible document that scales the show across writers, editors, producers, and AI assistants. Refuses to create a bible for a one-off piece or for a series that hasn't yet shipped 3+ episodes — the bible is extracted from working format, not invented before format exists. Treats bible-as-living-document; not a launch artifact, but an evolving operations manual.
---

# Series Bible Architect

A series bible answers: *what makes this show this show?* It's the document a new contributor reads to write episode 47 in voice, structure, and pacing without phoning the founder. Without it, every episode after the original creator's involvement drifts. With it, drift is a deliberate choice, not accidental decay.

## Core principle

**Extract, don't invent.** A series bible documents what's already working — patterns visible in episodes 1–N — and codifies them so episodes N+1 through N+∞ can repeat them. Inventing a bible before the show has run is wishful thinking; the format that actually works is rarely the one initially planned.

## When to use

| Situation | Activate? |
|---|---|
| 3+ episodes / issues live; team is growing | Yes — perfect timing |
| Series being handed off to new lead | Yes |
| Multi-author / multi-host series with drift | Yes |
| Adding AI writing assistance to existing series | Yes — bible becomes the prompt scaffolding |
| New series, hasn't launched yet | Reconsider — start with format pilot, not bible; revisit at episode 5 |
| Series creator wants to leave the work intact | Yes — the bible is the succession plan |
| One-off piece | No — wrong tool |

## What's in a series bible

Different formats need different sections. Below is the master template; subset for your format.

### Section 1: Show identity (every format)

- **One-line definition** — what the show is, in 15 words or fewer
- **Why it exists** — the editorial mission, the gap it fills
- **Audience** — who's reading/watching/listening, what they want from the show
- **Tone** — the voice in 2–3 sentences (link to brand-voice-extractor output if it exists)
- **The promise** — what every episode delivers; the consistent payoff

### Section 2: Format structure

For a **podcast**:
- Cold open (yes/no, length, what kind)
- Theme music in/out
- Host intro (script template)
- Segment structure (1 segment / multi-segment)
- Sponsor placement (pre-roll / mid-roll / post-roll)
- Outro (script template)
- Episode length range (e.g., 22–38 min)

For a **newsletter**:
- Subject line conventions
- Above-the-fold structure (preview, lead, hook)
- Section sequence with names
- Length range (word count)
- Visuals / images convention
- CTA placement and type
- Sign-off ritual

For a **video series**:
- Cold open formula
- Title card
- Segment count and pacing
- B-roll conventions
- Lower thirds / overlays
- Outro and CTA
- Length range

For a **social series**:
- Hook formula (first frame / first sentence)
- Pacing beats per duration
- Caption structure
- CTA / engagement prompt
- Hashtag convention (if any)

### Section 3: Editorial rules

- **In scope**: topic / treatment / format we cover
- **Out of scope**: explicitly what we don't do (and why)
- **Stance**: do we take positions or stay neutral? On what?
- **Sources**: what do we cite, how do we cite, what's allowed (anonymous? off-the-record?)
- **Sensitive topics**: list with treatment guidance (politics, current events, competitors, controversy)
- **Sponsor / brand integration**: rules for sponsored episodes vs editorial firewall

### Section 4: Recurring elements

The show's ingredients that distinguish it:
- Recurring segments (e.g., "Fact of the week", "Listener question")
- Catchphrases / calls-and-responses
- Running jokes or themes
- Visual / audio motifs
- Guest framework (who, why, what kind of conversation)

### Section 5: Production workflow

- Who does what (writer, editor, producer, host, designer)
- Pipeline stages with timing (research → outline → draft → edit → review → publish)
- Tools (CMS, project management, asset library)
- Calendar / cadence
- Lead time per episode
- Backup / contingency (what if a guest cancels, what's evergreen)

### Section 6: Style sheet

- Hyphenation, capitalization, formatting conventions
- Numbers (spelled vs digits)
- Names / titles convention
- Statistics / sourcing format
- Image / chart treatment
- Length conventions per element

### Section 7: Examples (the most important section)

The bible is mostly inert text without examples. Pull 2–3 episodes that exemplify the format at its best, annotate them inline:

> **Episode 14: [Title]**
>
> *Cold open*: 38 seconds. Anecdote-led, tied to thesis. (See: cold-open formula, p.4)
>
> *Hook*: the line "Most fundraising advice is wrong about timing." Direct, polarizing, specific. Note: not 'fundraising is changing' — too vague.
>
> ...

Annotated examples teach in ways prescriptions don't.

### Section 8: Anti-pattern gallery

Examples of episodes / pieces that drifted off-format and what went wrong. Equally instructive.

> **Episode 9 (we did not do this again)**: Cold open ran 2:40. The structure dragged. Lesson: cold open caps at 60s. Add to bible.

This is where the bible learns over time.

## Workflow for building the bible

### Step 1: Audit the existing run

Pick 5–8 representative episodes. Read/listen/watch them with structural notes:
- Length of each section
- What worked, what dragged
- Recurring devices the show uses
- Words / phrases the host(s) use repeatedly
- Guest treatment patterns
- Where the audience laughs / shares / engages most

### Step 2: Identify the format spine

The non-negotiable pattern. For most shows, this is 3–5 structural beats. If you can't articulate the spine in 30 seconds, it's not yet a format — it's a collection of episodes.

### Step 3: Codify the recurring elements

Move from "we sometimes do this" to "we always do this" or "we never do this." Force decisions. Optional elements proliferate; decided elements compound.

### Step 4: Capture the implicit rules

The hardest part: editorial decisions made on instinct that team members don't realize they're making. Examples:
- "We never have two guests in one episode"
- "We always end on a note of hope, even with grim subjects"
- "We don't promote sponsors who haven't used our product"
- "We avoid current-week news; topics need a 7-day lookback"

These rules live in the founder's head. Surfacing them is the bible's primary job.

### Step 5: Specify the workflow

Document the pipeline. Who hands off to whom. What "done" means at each stage. What tools. What templates.

### Step 6: Write it for use, not display

The bible should be 15–30 pages, structured for reference (not narrative), with table of contents and cross-links. Long enough to cover real cases, short enough to actually re-read.

### Step 7: Pilot with a contributor

The test of a bible is: hand it to a new writer, have them produce episode N+1 without other guidance, see if it feels like the show. The first attempt will reveal gaps. Iterate.

## Output format

Deliver as a single working document (Notion, Google Doc, Markdown) with:
- Linked TOC
- Section headers with anchor links
- Annotated examples (linked or embedded)
- Living change log at the end ("Last updated: X — change Y for reason Z")

For shows using AI assistance:
- A condensed Claude / GPT system prompt derived from the bible (maybe 1500 words) that encodes voice, format spine, editorial rules
- Episode-template files contributors can fill in

## Anti-patterns

1. ❌ Building a bible before the show has format — wishful prescription, not extracted documentation
2. ❌ Bible that's a marketing brief in disguise — full of audience-personas and value-pillars, light on operating reality
3. ❌ 80-page bible nobody re-reads — bibles must be re-read; size for that
4. ❌ Bible that lists rules without examples — abstract; misapplied
5. ❌ Bible that inventories everything but commits to nothing — "we sometimes do X, sometimes don't" is not a rule
6. ❌ Bible written by the founder for the founder's eyes only — must be written for the next person
7. ❌ Bible that doesn't cover the workflow / handoffs — episodes still depend on tribal knowledge
8. ❌ Skipping the anti-pattern section — failures are the most instructive examples
9. ❌ Treating the bible as launch-and-forget — it's a living document; cadence for review (quarterly typical)
10. ❌ Voice / tone section that copies brand voice without specifying show-specific adaptation — series within a brand can have their own voice variation
11. ❌ No length / pacing prescriptions — pacing is half of format; without it, drafts run long
12. ❌ Bible covers content but not commercial — sponsor integration, product placement, paid promotion rules need to be in the same doc
13. ❌ Style sheet inherited from corporate without adapting to the medium (audio vs video vs text have different conventions)
14. ❌ Bible not version-controlled — episodes diverge from each other; readers can't tell which version applied when
15. ❌ AI-prompt version of the bible drifts from the human-readable bible — keep them aligned; one source of truth

## Reference files

- `references/format-templates.md` — example section structures for podcast, newsletter, video, social series

## Confidence calibration

- Bible quality from solid corpus (5+ exemplar episodes): high
- Bible from sparse corpus: low — recommend pilot more before bibling
- Generalization across mediums: medium — patterns transfer but specifics differ
- Bible's effective shelf life: 6–18 months before substantial revision needed; format evolves
