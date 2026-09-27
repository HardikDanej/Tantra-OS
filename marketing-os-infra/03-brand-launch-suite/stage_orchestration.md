# Stage Orchestration — Brand Launch Suite

This document contains the six stage prompts you'll execute in sequence inside the Brand Launch Suite project. Each prompt is designed to be copy-pasted as-is.

**Total time:** 4–6 hours, split across two sessions.
**Session 1:** Stages 1–3 (~3 hours)
**Session 2:** Stages 4–6 (~2 hours), in a fresh chat in the same project

---

## Pre-flight check

Before Stage 1, run this in a new chat to verify setup:

```
Verify the project is configured correctly:
1. Confirm brand_inputs.json is in Project files. Report its asset count by category.
2. Confirm input_schema.json is in Project files.
3. List the 6 skills installed in this project.
4. Tell me which stages are ready to run based on input asset coverage:
   - Stage 1 needs 5+ total assets
   - Stage 2 needs 3+ customer assets
   - Stage 3 needs 3+ interview/social founder assets
5. If any stage is blocked by insufficient input, recommend specifically what to gather before proceeding.
```

If the precheck reports any missing pieces, fix them before Stage 1. Running stages on insufficient input is the #1 cause of low-confidence outputs.

---

## Stage 1 — Current-state audit (45 min)

```
Run brand-intelligence-auditor against all assets in brand_inputs.json. Apply the category weights from input_schema.json: web and prior_brand carry highest audit weight (they reveal stated and public positioning), interviews and social are secondary, customer assets are tertiary, competitive material is reference only.

Produce the audit in this structure:

1. WHAT THE BRAND IS CURRENTLY SIGNALING
What positioning emerges from the assets, regardless of what the brand claims to be? Cite specific assets (by id) as evidence for each signal.

2. INTERNAL CONTRADICTIONS
Places where different assets send conflicting signals. (Example: "homepage signals premium positioning [web_001] but social copy [social_003, social_007] uses casual humor inconsistent with premium reads.") This section is usually the most actionable — it shows what's actually broken.

3. EQUITY ALREADY BUILT
Distinctive assets, language patterns, or positioning that has traction worth preserving. Cite what's working and why.

4. BORROWED CONVENTIONS
Places where the brand uses category-default language and adds nothing. ("The homepage hero copy [web_001] reads as generic SaaS positioning — the same headline structure appears in 11 of the 15 competitor sites in inputs/competitive/.")

5. STATED VS. DEMONSTRATED GAPS
Where prior_brand documents claim one thing and web/social demonstrate another. This is high-leverage — it's the gap between strategy on paper and strategy in execution.

6. BRAND VOICE APPROXIMATION (preliminary)
A first-pass description of the voice the assets currently produce. We'll refine this in Stage 3 — for now, capture the texture.

7. GAPS
Where the brand is silent or unclear. Topics, audiences, or contexts the existing assets don't address.

For every finding, include: the finding, the evidence (cited asset ids), and a confidence label (high/medium/low). Findings without citations are invalid.

Length: 1,500–3,000 words. No padding, no consultant-speak summary at the end.
```

---

## Stage 2 — Audience personas (60 min)

```
Run psychographic-profiler. Apply the category weights from input_schema.json: customer assets carry highest weight (testimonials, reviews, support transcripts, case studies are the primary persona evidence base). Interview assets are secondary — they reveal the founder's understanding of customer.

Build 2–3 personas. If the customer asset coverage only supports 1 strongly differentiated persona, return 1 — do not pad to hit a target count.

For each persona, produce these sections:

1. NAME AND ONE-LINE SUMMARY (memorable; not "Marketing Mary")

2. DEFINING VALUES
What they actually care about. Cite specific customer assets where these values are demonstrated (not stated).

3. MOTIVATIONS
What they're trying to accomplish in their life that brings them to this category.

4. ANXIETIES
What scares them about choosing wrong in this category. This is where personas differentiate most — generic personas all share the same anxieties.

5. VOCABULARY PATTERNS
8–15 verbatim phrases this persona uses, each cited to a specific asset id. Verbatim language — not paraphrased.

6. MEDIA DIET
Where they actually spend information time. Cite evidence where possible.

7. PURCHASE TRIGGERS
The specific events or realizations that prompt them to enter the buying process.

8. OBJECTIONS
Specific objections they bring to category purchases. Cite assets where these objections appear.

9. WHY OUR BRAND FITS
The specific value lever this persona responds to, evidenced by which converted customer testimonials.

10. CONFIDENCE ON THIS PERSONA
high (well-evidenced, clear differentiation) / medium (some evidence but thin) / low (mostly hypothesis)

Source every claim. Personas without verbatim language samples are flagged as low confidence — the profiler should refuse to produce them as high confidence.

Length: 800–1,200 words per persona.
```

---

## Stage 3 — Voice extraction (75 min)

```
Run brand-voice-extractor. Apply the category weights from input_schema.json: interviews (especially audio transcripts) and social carry highest voice weight. Web copy is secondary (often committee-edited). Customer and competitive assets are not used for voice — they reveal audience voice and category convention respectively, neither of which is the brand's voice.

Use the audit from Stage 1 and personas from Stage 2 as additional inputs.

Produce these sections:

1. SENTENCE DNA
Typical sentence structure, length distribution, rhythm patterns. Quantitative where possible — "average sentence length 14 words; uses sentence fragments approximately every 3rd paragraph for emphasis." Cite asset ids that exemplify each pattern.

2. VOCABULARY TELLS
Words and phrases the brand uses distinctively. Not "innovative" — actual distinctive choices. Cite assets.

3. FORBIDDEN PHRASES
Words and patterns the brand never uses, with reasoning. This section is what makes the voice document usable. Aim for 15–25 specific forbidden phrases. ("Never starts a sentence with 'In today's...'." "Never describes itself as 'innovative'." "Never uses 'leverage' as a verb.")

4. TONE CALIBRATION BY CONTEXT
Different tone treatments for: sales page, founder LinkedIn, customer support, crisis comms, social ads, long-form content. Each tone gets 2–3 sentences of description plus 2 example sentences in voice.

5. VOICE RULES
5–10 specific, applicable rules a writer can use. Concrete enough to test against. ("If a sentence uses three or more abstract nouns in a row, rewrite it.")

6. VOICE EXAMPLES
For each tone context, write 3 example sentences in voice. Make these the kind of examples a new hire would copy.

7. WHAT THE VOICE SHOULD NOT DO
Specific patterns to avoid. ("No hedging in marketing copy; hedging is for support and crisis comms only.")

8. CALIBRATION NOTE
If the brand has limited or zero existing voice assets (greenfield), mark the voice as "constructed" rather than "extracted" — and flag that it needs validation against actual customer reactions in the first 90 days post-launch.

Length: 2,000–3,500 words.
```

**End of Session 1.** Save the chat. Start Session 2 in a fresh chat in the same project.

---

## Stage 4 — AI search visibility map (45 min)

In the new chat, paste the voice doc and personas from Session 1 as references.

```
Run geo-aeo-optimizer. The Stage 1 audit, Stage 2 personas, and Stage 3 voice doc are all available — reference them.

Produce this strategy:

1. TARGET PROMPTS (30–50)
Specific prompts the brand should aim to be cited in across ChatGPT, Perplexity, Claude, and Google AI Overviews. Group by buyer journey stage (awareness / consideration / decision). Each prompt: the prompt itself, why it matters for this brand, which persona is asking it, and the specific position the brand wants to hold in the answer (cited expert / featured tool / comparative reference / etc.).

2. CURRENT VISIBILITY AUDIT (top 10 prompts only)
Pick the 10 highest-priority prompts from the list above. For each: hypothesize whether the brand currently appears in answers based on existing content presence. (You can't run live AI engine queries, but you can reason from the assets.)

3. CITATION PATTERN ANALYSIS
For each AI engine, what kind of content gets cited? (Long-form articles, primary research, structured data, expert quotes, comparison tables, case studies.) Reference current research where you have it; flag where this is conjecture.

4. CONTENT GAPS
For each high-value prompt where the brand isn't currently cited, what specific content asset would close the gap? Prioritize by: (a) prompt search volume (rough estimate), (b) prompt strategic value to the brand, (c) ease of producing the asset.

5. SCHEMA AND STRUCTURED DATA
What structured data should the brand publish to be machine-readable to AI engines? Recommendations specific to this brand's content types.

6. 90-DAY GEO/AEO PRIORITIES
The 5–10 specific actions to take in the first 90 days. Not "publish more thought leadership" — specific actions like "produce comparison content for [prompt 1, prompt 4, prompt 7]" or "publish original research on [topic] to capture [prompt 12]."

Length: 2,000–3,000 words.
```

---

## Stage 5 — 90-day content system (60 min)

```
Run content-strategist + series-bible-architect in collaboration. Reference all prior stages.

Build the content system:

1. PILLAR THEMES (3–5)
Each pillar: thesis, target persona, format mix, distribution channels. Pillars must connect to specific GEO/AEO target prompts (Stage 4) and specific persona purchase triggers (Stage 2).

2. FORMAT STRATEGY
Which formats the brand will produce, and the rationale for each. Long-form articles, video essays, founder posts, customer story features, weekly newsletter, podcast — pick what fits the team and the audience, not what's trendy.

3. CHANNEL DISTRIBUTION LOGIC
How each piece of content moves across owned channels (newsletter, blog, social) and earned channels (PR, podcasts, communities). Specific, not abstract.

4. EDITORIAL CALENDAR (90 days)
Actual calendar with: publication date, format, pillar, target persona, target prompt (from Stage 4), brief (one line), owner (content lead / freelance writer / founder).

5. REPURPOSING PATHWAYS
For each long-form piece, the specific short-form derivatives. ("The pillar article on X becomes: 1 LinkedIn carousel, 1 X thread, 3 newsletter excerpts spread over 3 weeks, 2 ad creative concepts.") Map this explicitly — repurposing is what makes the calendar economically viable.

6. SERIES STRUCTURE
For any recurring content (newsletter, video series, podcast), build the full series bible: format rules, cadence, host, length, structure template, voice constraints.

7. CAPACITY CHECK
Verify the calendar is executable by 1 content lead + 1 freelance writer. If it isn't, cut until it is.

Length: 3,000–5,000 words.
```

---

## Stage 6 — Playbook assembly (45 min)

```
Assemble the complete brand playbook. Single document, 8,000–15,000 words.

Structure:

1. BRAND FOUNDATION
- Positioning statement (one paragraph, derived from audit + personas)
- Audit findings summary (top 5 from Stage 1)
- Audience personas (full from Stage 2)

2. VOICE SYSTEM
Full from Stage 3.

3. AI SEARCH STRATEGY
- Target prompts list (Stage 4)
- Content gap priorities
- Schema recommendations
- 90-day GEO/AEO priorities

4. CONTENT SYSTEM
- Pillar themes (Stage 5)
- Format strategy
- 90-day editorial calendar
- Repurposing pathways
- Series bibles

5. EXECUTION CHECKLIST
20 specific actions for week 1, with owners and deadlines. Not "develop content strategy" — specific actions like "publish comparison article on [topic 1] by Friday, week 2, owner: freelance writer."

6. ONBOARDING BRIEF
Designed for a new hire, agency, or freelancer to read in 30 minutes and start producing on-brand work. The brief is the briefing.

7. STRUCTURED OUTPUTS
Three downloadable files for use by the other workflows:
- personas.json (machine-readable persona definitions)
- voice_system.json (machine-readable voice rules and forbidden patterns)
- icp_definition.md (ideal customer profile, derived from personas + audit, formatted for HubSpot revenue agent consumption)

Output the final playbook as a single markdown document. Then output the three structured files as separate downloadable artifacts.
```

---

## After Stage 6

Save the structured outputs to local disk:

```bash
# In ~/marketing-os/03-brand-launch-suite/outputs/
brand_playbook.md
personas.json
voice_system.json
icp_definition.md
```

Then upload `personas.json` and `voice_system.json` to the Project files of Workflows 01 (Campaign Intelligence) and 02 (SEO Content Factory). Upload `icp_definition.md` to Project files of Workflow 04 (HubSpot Revenue Agent).

The downstream workflows are now grounded in this brand foundation. Their outputs will visibly improve in quality the next time they run.
