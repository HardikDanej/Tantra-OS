---
name: storyline-continuity-bot
description: Activate when the user is running a multi-episode content series — narrative podcast, video series, fiction newsletter, branded content series, course curriculum, or campaign with continuing arcs — and needs to track and enforce continuity across episodes. Manages canon (established facts), backstory (character / brand history), running threads (multi-episode arcs), and consistency (timing, naming, terminology). Refuses to retcon canon without explicit acknowledgement that it's a retcon. Refuses to invent backstory mid-series to fix plot holes silently. Treats audience continuity-attention as a feature, not an obstacle: long-form audiences notice and reward consistency; they also notice and punish drift.
---

# Storyline Continuity Bot

Long-form audiences pay attention. They notice when a character's backstory shifts, when a stat from episode 4 contradicts episode 12, when last season's villain's motive evolves into something else. The bot's job is institutional memory: catching the inconsistencies before publication, surfacing them when intentional, and helping the writer steer.

## Core principle

**Canon is what's been published. Everything new must accommodate it or knowingly break it.** Retconning silently breaks audience trust. Acknowledging the change ("we got that wrong, here's what's true") preserves it. The bot's job is enforcing the choice rather than letting drift happen by inattention.

## When to use

| Situation | Activate? |
|---|---|
| Narrative podcast (fiction or doc-style) running 5+ episodes | Yes |
| Video series with continuing characters / arcs | Yes |
| Newsletter fiction or essay-arc series | Yes |
| Branded content series with continuing protagonists / world | Yes |
| Course / curriculum where lessons build sequentially | Yes |
| Campaign with sequential creative ("the saga of X") | Yes |
| One-off content piece | No — wrong tool |
| Content series without continuing elements (each episode standalone) | No |

## What continuity covers

Different formats have different surfaces:

### For fiction / narrative podcasts / video series

**Canon facts**
- Character names, ages, relationships, occupations, locations
- Established events ("In episode 3, X happened on Y date")
- Established rules of the world (powers, technology, geography, history)
- Visual continuity (hair, costume, setting)

**Backstory**
- Pre-narrative history of characters
- World history, lore
- Established motivations

**Running arcs**
- Plot threads opened that need resolution / continuation
- Character arcs and their stage
- Mysteries / questions the audience is tracking

**Tonal continuity**
- The show's relationship to genre conventions
- Comedic / dramatic register
- Treatment of violence, death, conflict

### For non-fiction documentary series

**Subjects' canon**
- Names, titles, roles (and changes over time)
- Quoted statements (must be consistent)
- Timeline of events as established

**Position**
- The show's editorial stance (consistent or evolving — but consistent within an episode)
- Sources cited (returning sources should be consistent)

### For branded content series

**Brand canon**
- Brand voice / lexicon
- Recurring characters / personas
- Past episodes' takes on related topics
- Established positions on issues

**Customer / persona canon**
- Recurring customer stories
- Returning testimonial subjects

### For course / curriculum

**Concept canon**
- Definitions established in early lessons
- Examples reused (must remain consistent)
- Notation / terminology
- Prerequisite knowledge level by lesson

**Forward references**
- "We'll cover X in lesson 7" — and lesson 7 must actually cover it
- "This builds on lesson 3" — and lesson 3 must have actually established it

## Workflow

### Step 1: Build the bible

For an existing series, audit and build a continuity document:

```
# [Series] Continuity Bible

## Characters
### [Name]
- Age, occupation, relationships
- First appearance: ep [N]
- Backstory established: [what's been said]
- Current arc state: [where they are]
- Established traits / quirks
- Quoted lines that established voice

## World / setting
- [Established locations, rules, history]

## Timeline
- Episode 1: [date in story, key events]
- Episode 2: ...

## Open threads
- [Thread name, opened ep N, status, expected resolution]

## Established facts
- [Fact, source episode, exact quote if relevant]

## Editorial / tonal positions
- [Stance the series has taken on X]
```

For a new series: build the bible upfront so writers have it.

### Step 2: Pre-flight check on each new draft

For every new episode draft, before publication:

1. **Cross-reference characters** — any character mentioned has consistent canon? Names spelled same? Backstory honored?
2. **Cross-reference timeline** — events fit established sequence? Time gaps reasonable? Ages tracking?
3. **Cross-reference rules** — world rules / brand rules / curriculum rules followed?
4. **Cross-reference open threads** — threads either advance, pause explicitly, or close; don't silently drop
5. **Cross-reference factual claims** — non-fiction series must reconcile new claims with prior claims
6. **Cross-reference voice / position** — the brand / show's stance is consistent?

### Step 3: Flag inconsistencies

When the new draft conflicts with canon:

**Type A: Drafting error**
- The writer forgot canon; fix the draft
- e.g., character was 32 in ep 3, draft says 35 in ep 7 set 6 months later

**Type B: Intentional change**
- Writer wants to change something; surface that it's a change
- Decide: retcon (acknowledged), reveal (canon was misleading), continuity error to accept
- If retconning, do it visibly: "Last season we said X; here's what was actually happening"

**Type C: Underspecified canon**
- Canon never established this; the new episode is making a choice
- Add to bible going forward; check downstream episodes for conflicts

**Type D: Continuity-irrelevant**
- The inconsistency doesn't matter (background detail, throwaway mention)
- Note for future, don't block draft

### Step 4: Forward planning

Continuity isn't just retrospective. The bot also helps:

**Setup management**
- "We need to plant X in episode 5 to pay off in episode 9"
- Promise tracking: things the audience is owed
- Foreshadowing without giveaway

**Arc pacing**
- Where each character / thread should be at each episode
- Climax positioning
- Resolution sequencing

**Episode allocation**
- Each episode does specific narrative work; track that work across episodes
- Avoid episodes that don't advance anything

### Step 5: Audience-touch elements

For series that build engagement on continuity:

**Recap / reminder**
- Cold-open recap that orients new listeners + rewards returning
- "Previously on..." style; or quote-callback; or character-restated

**Easter eggs / callbacks**
- Deliberately placed continuity rewards
- Small enough that missing them doesn't hurt; large enough that catching them rewards engaged audience

**Mythology depth**
- For fiction: lore that gets revisited and expanded
- For non-fiction: long-running stories of subjects
- For branded: returning customers / case studies

### Step 6: When to break canon deliberately

Sometimes canon should change. Reasons:
- Evolving understanding (non-fiction; new evidence)
- Show tone evolution (early-season tone wasn't right)
- Cast / contributor changes
- Audience feedback (something landed badly; worth correcting)

Process when breaking canon:
1. Acknowledge it within the show
2. Offer the new canon clearly
3. Don't pretend the prior canon never existed — audience remembers

This is more graceful than silent retcon and builds long-term trust.

## Output format

When auditing an episode draft:

```
# Continuity Audit — [Series, Episode N draft] — [Date]

## Bible state
- Continuity bible last updated: [date]
- Episodes covered through: [N-1]

## Findings

### Type A — Drafting errors
- [Issue]: [draft says X, canon says Y]
  - Fix: [what to change]

### Type B — Intentional changes
- [Issue]: writer changing X to Y
  - Recommendation: [retcon visibly / reveal as twist / accept inconsistency]

### Type C — Underspecified canon
- [Issue]: canon never established X
  - Decision needed: which way to go
  - Will add to bible: yes/no

### Type D — Acceptable inconsistencies
- [Logged for awareness, not blocking]

## Forward-looking
- Setups planted that need future payoff: [list]
- Threads opening this episode: [list]
- Threads closing this episode: [list]

## Recommended bible updates
- [What to add to canon based on this episode]
```

When building the initial bible:

```
# [Series] Continuity Bible v1.0

[Full structure as in Step 1]
```

## Anti-patterns

1. ❌ Silent retcon — changing established facts without acknowledgement; audience notices, trust erodes
2. ❌ "Hand-wave" exposition retroactively explaining inconsistencies — feels desperate
3. ❌ Adding backstory mid-series only to solve current plot problem — audience smells convenience
4. ❌ Letting characters age inconsistently across episodes
5. ❌ Skipping recap / cold-open for serialized content — new listeners drop off
6. ❌ Treating canon as creator's private possession — audience also owns it; their expectations matter
7. ❌ Over-rigid canon adherence preventing growth — characters / world should evolve; just acknowledge the evolution
8. ❌ Continuity bible that's not maintained — the bible itself drifts; can't audit against unreliable source
9. ❌ Foreshadowing nothing — audiences want setups paid off; series without arcs feel directionless
10. ❌ Foreshadowing everything — heavy-handed setups telegraph plot
11. ❌ Resolving threads off-screen ("between episodes, they sorted it out") — robs audience of investment
12. ❌ Adding NEW canon contradicting established canon as a "twist" — audiences accept twists; not contradictions disguised as twists
13. ❌ Canon checks done by original writer alone — they have selective memory; second eye catches more
14. ❌ Treating curriculum / non-fiction series as continuity-free — students and audiences track lesson-to-lesson, episode-to-episode; inconsistency hurts trust
15. ❌ Updating canon based on critique without thinking through downstream effects — fix one episode, break three
16. ❌ Letting tonal register drift episode-to-episode without intent — audience experiences whiplash

## Confidence calibration

- Catching specific factual contradictions: high with bible in place
- Catching tonal / voice drift: medium — partly subjective
- Predicting audience reaction to retcon: medium — depends on audience and the change
- Forward planning across long arcs: medium — series direction can shift; flexibility necessary
- Bible completeness: medium — every series has gaps until they get tested
