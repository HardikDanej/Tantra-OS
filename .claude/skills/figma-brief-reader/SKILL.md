---
name: figma-brief-reader
description: Activate when the user wants to interpret a Figma file as a design brief — extracting copy, visual system, component inventory, layout intent, interaction patterns, and constraints — to inform marketing content, ad creative, presentations, or downstream design work. Produces structured briefs that translate visual design into actionable instructions for writers, AI image generation, copy variants, presentation builds, and dev handoff. Refuses to fabricate design intent the file doesn't actually express; flags ambiguity rather than guessing. Distinguishes between what's documented in the file (decided) and what's implied (interpretive). Treats Figma as one input — not a complete brief; recommends asking the designer when intent is ambiguous.
---

# Figma Brief Reader

The reader's output is a brief that someone who hasn't opened the Figma can act on — a writer can write to it, a video editor can build to it, a deck-maker can match it. It captures decisions visible in the file and flags decisions the file doesn't make.

## Core principle

**Read what's there, mark what isn't.** Figma files often contain finished decisions (final color tokens, locked components, named layouts) and unfinished decisions (frames labeled "TBD," placeholder lorem ipsum, multiple variants without a chosen one). A good brief separates these — actioning the decided, flagging the undecided — instead of inventing intent.

## When to use

| Situation | Activate? |
|---|---|
| Marketing team needs to write copy to a designed layout | Yes |
| AI image generation needs visual reference and style direction | Yes |
| Building a presentation that should match Figma source | Yes |
| Dev handoff brief for engineers | Yes (though Figma's Dev Mode is the primary source) |
| Producing ad creative variants matching Figma master | Yes |
| Auditing brand consistency across multiple Figma files | Yes |
| User wants Figma-to-code conversion | No — different tool / different problem |
| User has just a description, no actual Figma access | Reconsider — extraction needs file access |

## Workflow

### Step 1: Inventory the file

Walk the file structure and document:

**Pages** — Figma files commonly have multiple pages (Cover, Assets, Components, Pages, Archive). Note which contain finished work vs WIP vs reference.

**Frames per page** — what each frame represents (homepage hero, ad variant 3, modal state, etc.). Frame names matter; designers often encode intent there.

**Components / variants** — what's been componentized (buttons, cards, navs)? Variants per component (size, state, theme)?

**Style tokens** — color styles, text styles, effect styles. These are decisions; capture them precisely (hex codes, font/size/weight/line-height, shadow specs).

**Comments** — designer's notes-to-self, open questions, decision rationales.

### Step 2: Distinguish brief content from production content

Within the file, classify content:

- **Final** — frame labeled "Final," recently updated, no comments / open issues
- **Approved** — has stakeholder sign-off comment ("approved by X on date")
- **In review** — has open comments
- **WIP** — frame labeled WIP, lorem ipsum placeholder, "TBD"
- **Reference** — moodboards, competitor screenshots, inspiration boards

The brief should distinguish: "this is what was decided" vs "this is exploration."

### Step 3: Extract the visual system

Document the design system the file expresses:

**Color**
- Primary palette (with hex)
- Secondary / accent
- Neutrals (gray scale, with hex)
- Semantic colors (success, error, warning, info)
- Background treatments (gradients, textures, photography overlays)

**Typography**
- Type families (display, body, mono)
- Type scale (named: Heading 1, Heading 2, ..., Body, Caption)
- Sizes / weights / line-heights
- Letter-spacing on display sizes
- Special treatments (uppercase headers, italic emphasis patterns)

**Spacing**
- Base unit (typical 4 or 8 px)
- Spacing scale (4, 8, 12, 16, 24, 32, 48, 64...)
- Section padding conventions
- Component internal spacing

**Components and their behavior**
- Button styles, sizes, states (default, hover, active, disabled)
- Form inputs
- Cards, modals, navigation
- Loading / empty / error states

**Imagery**
- Photography style (saturated / desaturated, golden hour / studio, candid / posed, people / objects / abstract)
- Illustration style (if any)
- Icon style (line / fill, rounded / sharp, weight)
- Aspect ratios used (1:1, 16:9, 4:5, 9:16)

**Motion**
- If prototype includes motion: timing, easing, transition types

### Step 4: Extract layout intent

For each frame / screen / artboard:
- **Purpose** — what this layout is for
- **Hierarchy** — primary message, secondary, tertiary
- **Read order** — Z-pattern? F-pattern? Visual flow designed?
- **Negative space** — used as breathing or filled?
- **Density** — high information vs spacious

### Step 5: Extract copy

If the file contains real copy (not lorem ipsum), pull it. Note:
- **Voice clues** — sentence length, vocabulary, formal/casual
- **Hierarchy** — H1 is "X," subhead is "Y"
- **CTAs verbatim**
- **Microcopy** — error messages, empty states, helper text

If lorem ipsum: flag, ask for real copy or note that copy is open.

### Step 6: Extract interaction / interactivity

Prototype mode shows intended flows. Document:
- Entry point
- Tap / click targets and what they trigger
- State transitions
- Modal / overlay behaviors
- Conditional logic (if any — Figma supports basic conditional flows)

### Step 7: Identify ambiguities

Where the file doesn't decide:
- Multiple variants without a chosen primary
- Placeholder content (lorem, "Headline goes here," gray boxes)
- "TBD" labels
- Open comments
- Inconsistencies between similar frames (e.g., different button styles in different sections)

These are the questions to bring back to the designer or product owner.

## Output format

```
# Figma Brief — [File Name] — [Date]

## File overview
- Source: [link / file ID]
- Last updated: [date / by whom]
- Status: [Final / In review / WIP]
- Designer: [name]
- Stakeholders: [from comments]

## Frames in scope
| Frame | Purpose | Status | Notes |
|---|---|---|---|

## Visual system
### Colors
| Name | Hex | Use |

### Typography
| Style | Family / size / weight / LH | Use |

### Spacing
- Base: [unit]
- Scale: [values]

### Components
- [Component name]: [variants, states, behavior]

### Imagery direction
[Style description with examples or moodboard link]

## Per-frame breakdown

### [Frame name]
**Purpose**: [what this is for]
**Hierarchy**: [primary, secondary, tertiary message]
**Layout**: [structure]
**Copy** (if real): [verbatim]
**Interactions** (if any): [from prototype]
**Open questions**: [ambiguities]

## Open decisions (the file doesn't yet decide)
1. [Specific question]
2. ...

## Ready-to-action
- [What downstream teams can start on now]

## Blocked-pending-decision
- [What needs designer / PM / stakeholder input first]
```

For specific downstream uses, summarize:

**For copywriter**:
- Voice expressed in the file
- Word counts per slot
- Headline vs subhead vs body distinction
- CTA conventions

**For AI image generation**:
- Style descriptors (color palette, lighting, composition)
- Subject conventions
- Reference images
- Aspect ratios

**For presentation builder**:
- Slide layouts to match
- Font / color / spacing
- Image treatment

**For dev handoff**:
- Use Figma Dev Mode primarily
- This brief flags business / content questions, not implementation specs

## Anti-patterns

1. ❌ Treating placeholder content as final — lorem ipsum is not copy; gray box is not an image; flag, don't fabricate
2. ❌ Inventing rationale the designer didn't express — don't say "this layout is designed for scannable F-pattern reading" unless that's documented
3. ❌ Skipping the comments — designer notes often contain the most useful intent
4. ❌ Extracting one frame as if it's the whole file — note its place in the larger system
5. ❌ Ignoring component variants — "Button" is not one thing if there are 12 variants
6. ❌ Reporting hex codes without resolved opacity / blends — what looks like #4A5568 might be #1A202C @ 70% opacity
7. ❌ Pulling copy from comments / annotations as if it's intended user-facing text
8. ❌ Missing the file's auto-layout / responsive behavior — layouts encode breakpoint logic
9. ❌ Brief that's longer than the Figma file — distill, don't transcribe
10. ❌ Assuming a single Figma file is the complete brand system — there are usually parallel files (logo lockup, illustration library, brand book) the marketing team also draws from
11. ❌ Reading "Page 2 / Archive" frames as current — recently-renamed-out-of-the-way doesn't mean current
12. ❌ Producing a brief without flagging "this file has not been touched in 6 months" if true — staleness matters
13. ❌ Not noting prototype interactions — the static screens don't show the full intent
14. ❌ Quoting copy from the file as the brand's voice without checking against brand voice guide — designers sometimes use placeholder voice that doesn't match brand

## Confidence calibration

- Visible style values (hex, fonts, sizes): high
- Layout intent and hierarchy: medium — interpretive
- Designer's reasoning when not documented in comments: low — flag and ask
- Whether file content is final: medium — go by labels, comments, and recency together
- Cross-file brand consistency: low without the brand system file as comparison
