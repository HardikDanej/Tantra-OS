# AI Tells Catalog (Extended)

A working reference for recognizing and removing the patterns that mark text as LLM-generated. Updated as the patterns evolve.

---

## Cadence patterns

### 1. The "It's not just X — it's Y" construction
**Variants**: "isn't merely / isn't simply / not only X but also / X transcends Y to become Z"

**Why it shows up**: LLMs reach for false-elevation phrasing when transitioning from concrete to abstract.

**Fix**: drop the elevation; state the concrete thing. Or commit to one register, not the bridge.

---

### 2. The triplet of abstractions
"X, Y, and Z" with three abstract nouns where one specific would do.

**Examples**:
- "faster, smarter, more intuitive"
- "engagement, alignment, and momentum"
- "passion, curiosity, and resilience"

**Fix**: pick one. If three are needed, vary at least one to be specific or concrete.

---

### 3. The portentous opener

Variants that all signal the moment as world-historic:
- "In today's fast-paced digital landscape..."
- "In an era of unprecedented change..."
- "In a world where..."
- "We live in a time when..."
- "Now more than ever..."

**Fix**: just start with the point.

---

### 4. The hedging conclusion

- "Ultimately, success depends on a balanced approach..."
- "There's no one-size-fits-all answer."
- "The right choice depends on your unique needs."
- "Your mileage may vary."

**Fix**: commit to a take. If the genuine answer is "depends," explain the deciding factors specifically.

---

### 5. Symmetric paragraph rhythm

All paragraphs roughly 3–4 sentences, all medium length, all internally similar.

**Fix**: vary deliberately. Some paragraphs should be one sentence. Others should be long enough to develop a thought across a turn. The variation is itself a signal of human composition.

---

### 6. Em-dash mannerism

Frequency: real writers use em dashes occasionally. LLMs use them per paragraph, often per sentence.

**Examples (overdone)**:
> "Marketing has evolved — and continues to evolve — in ways that — even five years ago — would have seemed unlikely."

**Fix**: cap em dashes at ~1 per 200 words. The rest become commas, periods, or full sentences.

---

### 7. Bullet reflex

Every concept becomes a 3-item bulleted list, each with a bold lead.

**Fix**: prose where prose works. Lists for genuinely list-like content (steps, options, criteria). Mix forms across the piece.

---

### 8. Conclusion-as-recap

LLMs reflexively close with "In conclusion, we've explored X, Y, and Z..."

**Fix**: cut the recap. End on the previous paragraph's turn, or close with a single line that earns the ending.

---

## Vocabulary tells

### "Delve / leverage / unlock / navigate / unleash / harness"

The "LLM verb register." Real writers use "look at / use / open / find / let loose / use." LLMs reach for the elevated form.

### "Tapestry / landscape / realm / journey / ecosystem / fabric"

The "LLM metaphor register." Abstract domains framed as physical / textile / geographic.

### "Empower / elevate / amplify / illuminate / catalyze"

The "LLM verb register, marketing variant." Aspirational verbs that don't describe the actual action.

### "Holistic / nuanced / multifaceted / robust / cutting-edge"

The "LLM hedge adjective." Qualifiers that signal sophistication without specifying.

### "Furthermore / Moreover / Additionally / In addition"

Connecting words LLMs use when "and," "also," or simple paragraph break would do.

### "It's worth noting that..." / "It's important to remember that..."

Throat-clearing meta-commentary. Real writers just make the statement.

### "In essence / At its core / Fundamentally"

Distillation language used when the writer doesn't actually know what's essential.

---

## Structural tells

### 9. The suspicious "for example"

Examples that are abstract / hypothetical / generic:
> "For example, a company might choose to..."
> "Imagine a marketer who..."

Real examples are specific, named, dated, concrete. If the example doesn't ground out in someone or something specific, it's filler.

### 10. The bracketed "(which is" definition

> "We're seeing a rise in PLG (which is product-led growth) — a model that..."

Real writers either incorporate the definition in flow, or assume the audience.

### 11. Heading patterns

LLMs default to capitalized abstract noun phrases:
- "The Power of Personalization"
- "Understanding Customer Behavior"
- "Unlocking Growth Through X"

Real headings are declarative, specific, often longer:
- "Why personalization at scale fails for most brands"
- "What customers actually do, vs what they tell you"
- "How [Company] doubled growth in 90 days — and why it didn't last"

### 12. Generic statistics

> "Studies show that 80% of..."
> "Research suggests that customers..."

Round numbers, no source, no date. Real writing cites or doesn't claim.

### 13. False symmetries

LLMs love structural parallels:
> "If you build it for engineers, you lose marketers. If you build it for marketers, you lose engineers."

Sometimes this works. Often it's a fake symmetry covering a thin idea.

### 14. The "nuanced" hedge

> "While there are valid arguments on both sides..."
> "It depends on a variety of factors..."

The writer didn't commit. Real writing either commits or marks the question as live and explains why.

---

## Voice tells

### 15. Excessive "we" or "you"

LLMs swing between authoritative-we ("we've seen...") and friendly-you ("you might be wondering..."). Real writers commit to a register.

### 16. "Dear reader" affect

Self-aware addresses to the reader: "you might be thinking..." "as you read this..." "imagine yourself..."

Sparingly fine; over-used = LLM tell.

### 17. Formulaic transitions

- "But here's the thing:"
- "Here's the truth:"
- "Here's what most people miss:"
- "But there's a catch:"

These are fine occasionally. LLMs use them to mask weak transitions.

### 18. Ambiguous time markers

"In recent years..." / "Lately..." / "More and more..."

When? Specifically? Real writing either dates ("Since 2024...") or omits.

---

## What humans actually write that LLMs don't

The inverse signals — patterns that LLMs underuse:

### Specific names and dates
Real writing names: people, companies, products, projects, dates. LLMs tend toward generics ("a major SaaS company," "in recent years").

### Memorable wrong notes
A phrase that's slightly off, distinctive, memorable. LLMs file these down to averageness.

### Sentence fragments
Just sometimes. For emphasis. LLMs avoid them.

### Genre breaks
A sudden change of register — formal to colloquial, technical to plain — when it earns the moment. LLMs maintain register consistency.

### One-line paragraphs.

That land.

### Footnote-style asides
(In parens, sometimes too long, like a real tangent.) LLMs use parens lightly.

### Numbers that aren't round
"63%" not "60%." "2,847" not "thousands." Real data has texture.

### Things noticed but not central
Observations slightly off the main thread, the texture that signals the writer was actually there.

---

## Diagnostic process

When evaluating AI-feeling text:

1. **Read the first sentence**. If it's a portentous opener or the framing is doing work the body should be doing, mark it.

2. **Scan for vocabulary tells**. Count "delve," "leverage," "unlock," "tapestry," "landscape." 2+ per 500 words = signal.

3. **Check paragraph rhythm**. Are they all the same length? Symmetric internally?

4. **Check the conclusion**. Recap of previous sections? Hedged finish?

5. **Check specificity**. Are claims grounded in named things, dated, sourced? Or floating?

6. **Read aloud**. Where you stumble, the cadence is off. Where you're bored, you're scanning past LLM-cadence.

---

## Process for fixing

1. **Don't fix line-by-line first**. Do structural fixes (open, close, paragraph breaks, sectioning) before line edits.

2. **Inject specificity**. Every abstract claim either gets specific or gets cut.

3. **Vary rhythm deliberately**. Mix sentence lengths.

4. **Cut throat-clearing**. "It's worth noting" / "It's important to remember" — gone.

5. **Replace LLM verb register with plain verbs**. "Delve into" → "look at." "Leverage" → "use."

6. **Read aloud once more**. Any place the rhythm flattens, fix.

7. **Accept some persistence**. The goal isn't zero LLM tells; it's not-saturated. A piece can have 1–2 minor tells and read as human; with 8 it reads as machine.

---

## What this catalog isn't

- Not a way to evade AI detectors. Detectors update; the goal is reader trust, not detector games.
- Not exhaustive. New LLM mannerisms emerge with each model update; the catalog needs refreshing.
- Not absolute. A skilled writer might use any of these patterns deliberately and well. The tells are problematic when they accumulate, not in isolation.
