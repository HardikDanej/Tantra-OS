# PR & Corporate Communications Knowledge Base

Dedicated knowledge base for the Public Relations & Corporate Communications agentic system (`media-relations-earned-editorial-agent`, `corporate-reputation-issues-crisis-management-agent`, `events-experiential-marketing-agent`, and their thirty sub-agents). Closes the standing "no dedicated KB/skill backing" disclosure most of those sub-agents carried — `marketing-knowledge-base.md` names PR only briefly, as the canonical Earned channel. This file is the PR-craft-specific depth that brief mention pointed at. Sliced via `kb_slice.py outline` / `section "<heading>"` — never read in full. **Nothing in this file is legal, financial, or compliance advice** — the four regulated-territory sub-agents (ESG, investor relations, government relations, labor relations) still require real qualified counsel regardless of anything cited here.

## 1. CORE TIER — Measurement, Crisis, and Messaging Frameworks

### 1.1 Earned Media Measurement — the AMEC Framework

The **AMEC Integrated Evaluation Framework** (International Association for Measurement and Evaluation of Communication) is the industry-standard replacement for Advertising Value Equivalency (AVE), which the field has broadly repudiated as methodologically unsound (it conflates paid-media cost with earned-media value, two fundamentally different things). AMEC's five-stage chain, each stage a real, distinct measurement:

```
Inputs (the plan, resources, strategy)
  → Activities (what was actually done — pitches sent, releases distributed)
    → Outputs (what actually resulted — coverage secured, reach, share of voice)
      → Out-takes (what the audience actually took away — message pull-through, sentiment, awareness change)
        → Outcomes (behavior/attitude change attributable to the communication)
          → Impact (organizational-level effect — revenue, reputation score, policy change)
```

`editorial-media-monitoring-clipping-subagent`'s "hits, sentiment, and message pull-through" tracking sits at the Output/Out-take stages — never claim Outcome or Impact-level causation from coverage-count data alone; that requires the same causal rigor the Market Research system's `incremental-lift-media-incrementality-subagent` applies elsewhere, and PR measurement is not exempt from that standard just because "PR is different."

### 1.2 Crisis Communication — Situational Crisis Communication Theory (SCCT)

Timothy Coombs' SCCT is the dominant academic and practitioner framework `crisis-communications-playbook-scenario-planning-subagent` should build from. Core logic: the appropriate response strategy depends on **attributed crisis responsibility**, assessed across three crisis-type clusters, from least to most organizational blame:

| Cluster | Example | Baseline response posture |
|---|---|---|
| **Victim cluster** | Natural disaster, workplace violence, product tampering by an outside actor | Deny/minimize responsibility is appropriate — the org is genuinely also a victim |
| **Accidental cluster** | Technical error, unforeseeable product harm | Excuse or justify, paired with corrective action |
| **Preventable cluster** | Organizational misconduct, negligence, known-and-ignored risk | Full apology and corrective action — minimizing responsibility here compounds the damage |

Misreading which cluster a real crisis falls into (treating a preventable crisis with a victim-cluster response posture) is the single most common real-world crisis-communications failure this framework exists to prevent — `rapid-response-issue-triage-subagent`'s severity classification should include this read explicitly, not just a generic severity tier.

**The crisis lifecycle** (three phases, each with a distinct communications job): **pre-crisis** (playbook-building, this system's `crisis-communications-playbook-scenario-planning-subagent`) → **crisis** (the actual response window, `rapid-response-issue-triage-subagent` + Writing Agent's `crisis-sensitive-content-subagent`) → **post-crisis** (reputation-repair messaging, follow-through commitments, and — critically — evaluating whether the pre-crisis playbook actually held up, feeding back into the next version of it).

### 1.3 Key Message Architecture ("Message House")

The standard structure for any spokesperson-facing or campaign-facing message set, used across `media-training-interview-prep-subagent`, `press-conference-media-briefing-subagent`, and `executive-thought-leadership-op-ed-subagent`:

```
                    [ Roof: the single core message, one sentence ]
                    /              |                \
     [ Pillar 1: proof point ]  [ Pillar 2: proof point ]  [ Pillar 3: proof point ]
```

A message house with more than three pillars usually means the core message isn't actually decided yet — three is a practical ceiling for what a spokesperson can hold under real interview pressure, not an arbitrary stylistic rule.

### 1.4 Stakeholder Mapping — Power/Interest Grid

A 2×2 grid (Power: low/high × Interest: low/high) used across Corporate Reputation's sub-agents (investor relations, government relations, internal comms, executive reputation) to decide communication intensity:

| | Low Interest | High Interest |
|---|---|---|
| **High Power** | Keep satisfied (minimal but respectful engagement) | Manage closely (the highest-touch communication tier — investors, regulators, key media) |
| **Low Power** | Monitor (minimal effort) | Keep informed (regular updates, lower-touch) |

Placing a stakeholder in the wrong quadrant is a recurring, correctable failure mode — e.g., treating a low-power-but-high-interest employee population as "monitor" rather than "keep informed" is a common driver of internal-communications-triggered leaks and morale crises.

## 2. REFERENCE TIER — Media, Events, and Regulated Territory

### 2.1 Press Release & Wire Distribution

**Standard anatomy** `press-release-wire-embargo-subagent` structures (drafting itself still routes to the Writing/Content Production Agent): Headline → Dateline → Lede (who/what/when/where/why in the first sentence) → Supporting paragraphs (most-important-first, "inverted pyramid") → Boilerplate → Media contact. The inverted-pyramid structure exists because most readers (and most editors deciding whether to run it) never get past the first two paragraphs — front-load the actual news.

**Embargo protocol** — an embargo is a voluntary agreement with named journalists to hold publication until a stated time; it has no legal force, only relationship consequences (breaking an embargo, even accidentally, damages trust with that journalist going forward). `press-release-wire-embargo-subagent`'s "track the lift time" discipline exists because embargo times are frequently stated in the releasing company's local time zone without saying so, a common real-world source of accidental breaks.

### 2.2 Media Pitch Angle Taxonomy

| Angle type | What it offers a journalist | Best fit |
|---|---|---|
| **Exclusive** | First/only access to a story | High-value news with real embargo leverage |
| **Data-story** | A genuinely newsworthy data point/trend the company can uniquely supply | Companies sitting on real proprietary data |
| **Trend-jack** | Connecting the company's expertise to an already-breaking news cycle | Requires real speed — the news cycle window is short |
| **Expert-commentary** | Offering a spokesperson as a source for a story the journalist is already writing | Ongoing relationship-building more than a single placement |
| **Contributed op-ed** | A full piece the company writes, for the outlet to publish under a named author | Thought-leadership positioning, `executive-thought-leadership-op-ed-subagent`'s core mechanism |

`media-pitching-journalist-outreach-subagent` should name which angle a pitch actually is — a pitch that doesn't fit any of these clearly is usually not yet a real pitch, just a company announcement looking for a journalist to care about it.

### 2.3 Regulated-Communications Reference (non-legal-advice; real counsel required in every real case)

- **Regulation FD (Fair Disclosure)** — U.S. SEC rule requiring that material information be disclosed to all investors simultaneously, not selectively briefed to favored analysts first. The reason `investor-relations-earnings-release-subagent` treats "who sees this, and when" as load-bearing, not a formatting detail.
- **TIPS framework** (labor relations) — the four classic categories of unlawful employer conduct regarding union activity: **T**hreaten, **I**nterrogate, **P**romise, **S**urveil. `labor-relations-union-workplace-comms-subagent`'s hard refusal gate is built directly on this framework — any message resembling one of these four, even unintentionally, is refused rather than softened.
- **Lobbying disclosure basics** — in the U.S., the Lobbying Disclosure Act generally requires registration once a threshold of lobbying-contact time/compensation is crossed; requirements vary meaningfully by jurisdiction and change over time. `government-relations-public-policy-subagent` names this as a real compliance question, never answers it itself.
- **Materiality (securities context)** — information is "material" if a reasonable investor would consider it important to an investment decision; this is a legal determination made by qualified securities counsel based on real facts, never something this system asserts on its own analysis.

### 2.4 Event Format Taxonomy & Fit Criteria

| Format | Ownership | Scale | Fits when |
|---|---|---|---|
| **Trade show / industry conference** | Third-party owned, company exhibits | Large, shared audience | Category-wide visibility, competitive presence matters |
| **Owned flagship summit** | Fully company-owned | Company-controlled, any scale | Enough of an installed base/community to fill a room around the company alone |
| **Roadshow** | Company-owned, repeated across markets | Small, local, high-touch, repeated | Relationship-building across multiple geographies without one big-bet event |
| **Webinar / digital event** | Company-owned, virtual | Scalable, low marginal cost | Broad reach needed without travel/venue cost |
| **Pop-up / experiential activation** | Company-owned, short-duration | Small footprint, high intensity | A single memorable brand moment matters more than reach |

## 3. PR/Corporate Communications Maturity Ladder

```
Reactive (only responds when a journalist calls or an issue erupts)
  → Proactive (regular pitching cadence, a real crisis playbook exists before it's needed)
    → Strategic (PR is planned alongside product/business strategy, not bolted on after)
      → Embedded (communications risk/opportunity is a standing input to major business decisions, not a separate workstream)
```

A rapid-response crisis capability recommendation for an organization still at the reactive rung needs the playbook-building step first — you cannot rapid-response a scenario that was never war-gamed.
