---
name: de-ai-ify
description: Activate when the user wants to take AI-generated text (or text that reads as AI-generated) and revise it to feel like it was written by a thoughtful human — removing tells, restoring voice, eliminating AI cadence patterns. Produces revised text plus a diagnostic of which AI tells were present and how each was fixed. Refuses to "humanize" content for the purpose of bypassing AI-detection in academic / contractual contexts where authorship attribution matters; that's a different request with different ethics. Treats the goal as honest improvement of writing — readers feel served by writing that sounds like a person thought it through, regardless of how it was drafted. The skill also refuses to add fabricated personal anecdotes or invented credentials to fake humanness.
---

# De-AI-ify (Humanizer)

LLMs draft in patterns. The patterns aren't bad on their own — they're well-formed, grammatical, structured — they're just *recognizable*. After enough exposure, readers feel the rhythm and disengage. De-AI-ifying is voice restoration: same content, less obvious origin, more reader trust.

## Core principle

**Specificity, restraint, and rhythm variation are the three repairs.** AI text tends toward generic specificity (numbers without sources), abundance (saying three things when one would do), and rhythmic uniformity (similar sentence shapes back-to-back). The fix is rarely a single edit; it's a pattern of edits that together restore the texture of considered writing.

## When to use

| Situation | Activate? |
|---|---|
| Marketing copy drafted by Claude / GPT, deploying to brand surfaces | Yes |
| Long-form content (blog, newsletter) drafted by AI, needs editorial polish | Yes |
| Email / outreach drafted by AI, needs human-from-the-team feel | Yes |
| Speech / presentation script needing oral cadence | Yes |
| Academic submission / contractually-attributed authorship | Refuse — different problem; user should write it |
| Bypassing AI-detection for adversarial purposes | Refuse |
| Text already has a strong human voice; user just wants edit | Reconsider — that's editing, not de-AI-ifying |

## The AI tells

Recognize the tells before treating them. The most common in current LLM output:

### 1. The "It's not just X, it's Y" construction
Variants: "isn't merely / isn't just / not only X, but also / also Y." Often paired with abstract pairings.

> ❌ "This isn't just a tool — it's a transformation in how teams collaborate."
> ✅ "Teams using it answer each other's questions in 4 minutes instead of 4 days." (specific, no faux-portent)

### 2. The "delve / navigate / unlock / leverage / unleash" register
Verbs LLMs reach for that real writers reach for less. Plus "tapestry," "landscape," "realm," "journey," "elevate," "empower."

> ❌ "Let's delve into the landscape of modern customer engagement."
> ✅ "Most companies email customers about three things. Here's why." (replace abstract verb-noun with concrete claim)

### 3. The triplet
"X, Y, and Z" three-part lists everywhere, especially with abstract nouns. Real writing uses pairs, fours, or single words too.

> ❌ "Faster, smarter, and more efficient than ever."
> ✅ "Faster than the old way. Sometimes 4× faster." (one specific beats three vague)

### 4. The portentous opener
"In today's fast-paced digital landscape..." / "In an era of..." / "In a world where..." LLMs love framing the present moment as historic.

> ❌ "In today's competitive marketing environment, brand differentiation has never been more important."
> ✅ Just start with the point. The reader knows it's now.

### 5. The hedging conclusion
"Ultimately, success depends on a balanced approach that considers multiple factors..." Conclusions that don't conclude.

> ❌ "Ultimately, the right CRM depends on your team's unique needs."
> ✅ "Pick HubSpot for marketing-led teams, Salesforce for enterprise complexity, Pipedrive for tight sales cycles." (commit)

### 6. Symmetric paragraph rhythm
Paragraphs that are all 3–4 sentences, all medium length, all with similar internal structure.

Fix: vary. One-sentence paragraphs. Long paragraph then a short one. Sentences of 4 words next to sentences of 27.

### 7. Generic statistics
"Studies show..." "Research has demonstrated..." without source, often with suspiciously round numbers (60%, 70%, 80%).

Fix: cite specifics or remove. "A 2024 Edelman survey of 1,200 marketers found..." or just don't claim it.

### 8. Em dashes everywhere
LLMs over-use em dashes for parenthetical asides. Real writers use em dashes — but not three per paragraph.

> ❌ "Marketing has evolved — and continues to evolve — in ways that — even five years ago — would have seemed unlikely."
> ✅ "Marketing has changed. Five years ago, this approach would have seemed unlikely."

### 9. The bulleted-list reflex
Every concept becomes a bulleted list of 3 items, each starting with a bold phrase. Useful sometimes, mannerism when constant.

Fix: prose where prose works. Lists for genuinely list-like content (steps, options, criteria).

### 10. "It's worth noting" / "It's important to remember"
Throat-clearing meta-commentary about the importance of upcoming statements. Real writers just make the statement.

> ❌ "It's worth noting that timing matters significantly here."
> ✅ "Timing matters here."

### 11. The suspicious "for example"
Examples that are abstract, hypothetical, or generic ("a company might choose to..." "imagine a marketer who..."). Real examples are specific (named, dated, concrete).

### 12. Conclusion paragraph that summarizes the post
"In conclusion, we've explored X, Y, and Z. By implementing these strategies..." Real writers either don't summarize, or end on a turn rather than a recap.

### 13. The "nuanced" hedge
"While there are valid arguments on both sides..." "It depends on a variety of factors..." Real writers commit, or explicitly mark the question as live.

### 14. Brackets / parentheses overuse for "(which is" definitions
Real writers either incorporate the definition or assume the reader knows / doesn't need it.

### 15. Heading patterns: "The Power of X" / "Understanding Y" / "Unlocking Z"
LLMs default to capitalized abstract noun phrases. Specific, declarative headings work better.

> ❌ "The Power of Personalization"
> ✅ "Why generic email opens at 18% and personalized opens at 41%"

## Workflow

### Step 1: Read aloud

Read the AI text aloud. Tells become audible: places where rhythm flattens, where abstract words pile up, where the reader's voice (you) trips over the cadence. Mark those.

### Step 2: Catalog the tells

List what's present. A short post might have 3–4 tells; a long one might have 20. Don't fix yet; map first.

### Step 3: Fix structurally before line-by-line

Some fixes are global:
- If every paragraph is symmetric: rebreak to vary length
- If every section opens with a portentous frame: kill the frames
- If conclusion is a recap: cut or replace with a turn

Then go line-by-line for the local tells.

### Step 4: Inject specificity

Every abstract claim either gets specific or gets cut. Numbers, names, dates, examples that actually happened, particular instances.

> ❌ "Many businesses struggle with onboarding."
> ✅ "Notion's docs say activation takes 4 minutes. Most users we surveyed took 11."

If you don't have specifics, the abstract claim probably isn't load-bearing — cut it.

### Step 5: Restore voice

If the user has a brand voice document or sample, run the revised text against it. Match vocabulary, sentence shapes, restraint conventions, characteristic moves. (See brand-voice-extractor skill.)

If no voice doc: aim for plain, declarative, unadorned. Better to under-style than over-style.

### Step 6: Vary rhythm deliberately

Pass through and vary sentence length. Some short. Some long enough to develop a thought across multiple clauses with a turn at the end. Combinations like that. The key is *deliberate* variation, not just shorter sentences.

### Step 7: Strip the closing recap

In 90% of cases, the AI's closing paragraph is recap. Cut it. End on the previous paragraph's turn, or write a one-line ending that earns its place.

### Step 8: Final read-through

After all edits, read the text again. If any of the original tells survived: fix or accept (some tells are fine in moderation; the goal isn't zero, it's not-saturated).

## Output format

Deliver:
1. **Revised text** — the de-AI-ified version
2. **Diagnostic** — list of tells found, count, fix applied
3. **Optional: side-by-side** for the highest-impact paragraphs (before/after) so the user learns the patterns

```
## Tells found
- "It's not just X, it's Y" — 4 instances → reduced to 0
- Triplet abstractions — 7 instances → kept 2, killed 5
- Portentous opener — 1 instance → cut
- Em-dash overuse — 12 → 4
- Conclusion recap — present → replaced with single-sentence turn
- Generic statistics — 3 → cited 1, removed 2
- ...

## Highest-impact rewrites
[Before/after on 2-3 paragraphs]

## Revised text
[Full text]
```

## Anti-patterns

1. ❌ Substituting one set of mannerisms for another — "elevate" becomes "level up"; "delve" becomes "dive"; pattern remains
2. ❌ Adding fake personal anecdotes ("I remember when I was running my agency..." when there's no agency) — humanness ≠ fabrication
3. ❌ Adding deliberate grammar errors to seem human — readers register that as low-quality, not authentic
4. ❌ Replacing every abstract noun with concrete one — over-correction; some abstraction is fine in moderation
5. ❌ Cutting all em dashes — em dashes are fine sparingly; over-correcting is also a tell
6. ❌ Inserting filler hedges ("I think," "I guess") to seem casual — opposite mannerism, same problem
7. ❌ Optimizing for AI-detector tools' specific signals — they'll change; write for readers, not detectors
8. ❌ Stripping all structure — bullet lists become messy prose, headings become buried — over-corrections that hurt scanability
9. ❌ Replacing competent-sounding content with worse content in the name of voice — readers want both
10. ❌ Treating de-AI-ifying as a one-pass automation — it's editorial work; runs better with a human or a reflective second pass
11. ❌ Failing to consider that the user might want to keep the structured / efficient style — some surfaces (technical docs, FAQ) benefit from AI-cadence; only humanize where humanness pays off
12. ❌ Adding "filler human-ness" (typos, "haha," exclamation overload) instead of fundamental rewriting
13. ❌ Promising the result will pass AI detection tools — those tools have high false positive and false negative rates; the goal is reader trust, not detector evasion
14. ❌ Ignoring genre conventions — a press release should sound like a press release; a Twitter thread can be more idiosyncratic; over-humanizing across-the-board produces format-mismatched copy

## Reference files

- `references/ai-tells-catalog.md` — extended catalog of LLM cadence patterns with examples and fixes

## Confidence calibration

- Pattern recognition (which tells are present): high
- Per-edit improvement (each fix makes the text better): medium — judgment varies
- Whether revised text "passes" as human: low — passes which audience? Reader engagement is the better metric
- Detector tool evasion: refuse to optimize for it; goal is reader trust, not detector games
