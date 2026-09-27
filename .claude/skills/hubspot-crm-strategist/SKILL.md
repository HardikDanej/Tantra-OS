---
name: hubspot-crm-strategist
description: Activate when the user is architecting, cleaning up, or scaling a HubSpot CRM — designing pipelines, lifecycle stages, properties, lead scoring, workflows, lists, sequences, reporting, and integrations. Produces concrete CRM structures that match how the team actually sells, not generic templates. Refuses to design a 47-property contact record nobody fills in. Refuses to recommend automation that obscures account state from reps. Treats HubSpot as a tool whose value is realized through discipline (clean data, defined stages, agreed definitions) more than features. Most CRM problems are not "we need more workflows"; they're "sales and marketing don't agree on what an MQL is."
---

# HubSpot CRM Strategist

The strategist's deliverable is structure that supports honest conversations about pipeline reality. The CRM that has 30 custom properties nobody fills in is worse than the CRM with 5 that everyone fills in correctly. Bias every recommendation toward fewer fields, clearer stages, agreed definitions.

## Core principle

**A CRM is a shared model of reality between sales, marketing, and ops.** Misalignment in the model causes more pain than missing automation. Before designing workflows, get the model right: what is a contact, lead, MQL, SQL, opportunity, customer? When does state change? Who's accountable for the change? With those answers, automation is straightforward. Without them, automation entrenches the confusion.

## When to use

| Situation | Activate? |
|---|---|
| Setting up HubSpot for the first time | Yes |
| Cleaning up an accumulated mess of properties / stages / lists | Yes |
| Designing lead scoring | Yes |
| Designing nurture sequences and workflows | Yes |
| Sales / marketing handoff dysfunction | Yes — usually CRM-rooted |
| Reporting on pipeline / funnel | Yes |
| Picking between HubSpot tiers | Yes |
| Building integrations (Salesforce sync, custom objects) | Yes |
| One-off "create this list" task | No — too small |
| User wants to compare HubSpot to Salesforce / Pipedrive | Yes (briefly) |

## Workflow

### Step 1: Define the business model in CRM terms

Before touching HubSpot, get explicit answers:

1. **What's a contact vs lead vs prospect?** HubSpot uses the term "contact" for everything; the team's mental model needs mapping.
2. **What's the funnel?** Marketing-led demand gen, sales-led outbound, PLG signup-driven, channel/partner — each has different stage logic.
3. **What's the sales cycle length?** 7 days vs 90 days vs 9 months → vastly different pipeline structure.
4. **One pipeline or many?** Different products, segments, geographies, motion types may need separate pipelines.
5. **How does an opportunity / deal advance?** What's the gating event from stage to stage?
6. **What's an MQL vs SQL?** Forced precision: a specific signal + a specific action, not "feels qualified."
7. **What's a customer? Lifecycle after close?** Onboarding → activated → expanding → churning — which states need CRM representation?

The output of this conversation is a **CRM model document** — pre-implementation. Skipping this step is the single most common cause of HubSpot becoming a mess.

### Step 2: Lifecycle stages

HubSpot has built-in lifecycle stages. Don't over-customize:
- **Subscriber** — opted into communication
- **Lead** — known contact, not yet qualified
- **MQL** — Marketing-qualified
- **SQL** — Sales-qualified
- **Opportunity** — active deal
- **Customer** — closed-won
- **Evangelist** — referring / advocating
- **Other** — explicit catch-all

For most B2B SaaS, this map is sufficient. Resist adding "Hot Lead," "Warm Lead," etc. — those should be lead score bands, not lifecycle stages.

For ecommerce / consumer, simplify further: Subscriber → Lead → Customer is often enough; lifecycle isn't where the value is.

### Step 3: Deal pipeline stages

Number of stages: 5–7 typical. Each stage should answer:
- **What's the gating event?** (Specific, observable; not a vibe)
- **Who owns advancing?** (Sales rep, by default)
- **What's the typical time-in-stage?** (Helps detect stalls)
- **What's the conversion rate to next stage?** (Helps forecast)

Example for SMB SaaS, 30-day cycle:
1. **Discovery** — first call booked. Out: discovery call held; pain identified.
2. **Demo Scheduled** — demo on calendar. Out: demo held; champion identified.
3. **Evaluation** — POC / trial active. Out: success criteria met; pricing discussed.
4. **Proposal** — proposal/quote sent. Out: terms negotiated.
5. **Contract** — paperwork in motion. Out: signed.
6. **Closed Won** | **Closed Lost** — terminal.

Avoid:
- Stages that are wishes, not states ("Hopeful," "Likely")
- Stages that are sub-rep activities ("Awaiting Response," "Following Up") — those are tasks, not pipeline state
- More than 8 stages — forecasting accuracy degrades; reps stop updating

### Step 4: Properties — the discipline

Default to fewer properties. Each new property is a tax on data quality.

**Required fields** for a contact: 4–6 max
- Email (required, unique)
- First/Last name
- Company
- Lifecycle stage (auto-managed by workflows where possible)
- Lead source (one of a small enum)

**Required for a deal**: 4–6 max
- Deal name
- Amount
- Close date
- Pipeline / Stage
- Owner
- (One or two custom: e.g., Product line, Geography)

**Custom properties added later** only when answering: *what report or workflow needs this, that we'd block without it?* If the answer is unclear, don't add it.

**Property types matter**:
- Dropdown (enum) for finite choices — never free-text for stage / source / segment
- Number for things you'll average / sum
- Date for things you'll filter by recency
- Calculated property for derived values (don't have reps compute LTV manually)

### Step 5: Lead scoring

Two kinds:

**Predictive lead scoring** (Enterprise tier): HubSpot's ML scores based on historical conversion patterns. Useful when you have 1000+ closed-won deals to train on. Below that volume: don't trust it.

**Manual lead scoring**: explicit point system you define.

Template:
```
Demographic / firmographic (positive)
+5 Title contains "Director" or "VP"
+10 Title contains "Head of" or "Chief"
+5 Company size 50–500 (ideal SMB target)
+10 Company size 500–5000 (ideal mid-market)
-10 Title contains "student" or "intern"
-15 Email contains @gmail.com / @yahoo.com (no business domain)

Behavioral (positive, decay-able)
+3 Visited pricing page
+5 Submitted contact form
+10 Booked a demo
+3 Watched a webinar
+2 Opened an email (capped at 10/period)
+5 Clicked a link in email

Behavioral (negative)
-5 Unsubscribed
-3 Marked email as spam (some teams hard-bounce these)
-2 No activity in 60 days
```

MQL threshold is the score where conversion to SQL becomes economically interesting — typically validated by observing what scores actually convert in your data, not picked arbitrarily.

Decay matters: a contact who downloaded an ebook 2 years ago shouldn't carry that score forever. Implement score expiry on behavioral points (90/180-day decay).

### Step 6: Workflows — restraint over enthusiasm

HubSpot workflows can fire on enrollment / property change / form submission / list membership / etc. Tempting to automate everything; usually a mistake.

**Workflows that pay off**:
1. **Lead routing**: new MQL → assigned to rep based on territory / product / round-robin
2. **Lifecycle progression**: behavior X → set lifecycle to Y (tightly guarded — usually only forward, with explicit conditions)
3. **Internal notification**: high-intent action → Slack message to AE
4. **Nurture sequences**: time-based emails for educational content, with clear suppression rules
5. **Re-engagement**: dormant lead → trigger touch sequence
6. **Data hygiene**: missing required field → task for ops

**Workflows that backfire**:
1. ❌ Auto-changing deal stages based on rep activity — corrupts forecast; reps lose trust
2. ❌ Auto-deleting / archiving contacts based on inactivity — loses data; recovery is painful
3. ❌ Cascading lifecycle changes that fire other workflows that fire other workflows — debugging becomes impossible
4. ❌ Personalization tokens that fail silently when properties are blank ("Hi ,") — pre-validate
5. ❌ Sending to unsubscribed contacts via "marketing email exempt" loophole — legal and reputational
6. ❌ Workflow that updates a property used in another workflow's enrollment — infinite loop unless guarded

**Workflow design rules**:
- Single-purpose; if a workflow has 12 branches, split it
- Suppression list applied (no workflow ignores opt-out)
- Goal completion on every workflow (so contacts exit when they meet the goal)
- Test on a sandbox or test contact before going live
- Review monthly — workflows that haven't fired in 90 days should be audited

### Step 7: Reporting

Default reports to build:

**Pipeline**
- Deal count by stage, current
- Deal $$ by stage, current
- Stage conversion rates (last 90 days)
- Time in stage (median, p90)
- Deals by close date forecasted vs actual

**Funnel**
- Contact-to-MQL conversion rate
- MQL-to-SQL conversion rate
- SQL-to-Opportunity rate
- Opp-to-Closed rate
- Cycle time at each stage

**Source**
- Deals / revenue by lead source
- Cost per lead / per opportunity / per closed (paired with marketing spend)

**Activity**
- Calls / meetings / emails per rep per week
- Activity-to-meeting-booked rate

**Reps**
- Quota attainment
- Pipeline coverage (open pipeline / quota gap)

Avoid:
- Reports that nobody pulls up — kill them
- Reports with too many filters — anyone can produce vanity charts; useful reports stay simple
- Reports without a defined consumer — every report needs a person who reads it weekly

### Step 8: Sales / marketing handoff

The friction point. Codify:
- **MQL definition** (specific score, specific behavior or both)
- **SLA on follow-up** (e.g., AE attempts contact within 4 business hours)
- **Disqualification flow** — what happens when AE marks bad MQL? Goes back to nurture? Gets feedback to marketing? Both?
- **Recycling** — when does an SQL that didn't close return to nurture?

Without a documented handoff, marketing claims they sent leads and sales claims the leads were bad. With it, both sides have data.

### Step 9: Integrations

Common integrations:
- **Salesforce sync** (if hybrid stack) — bidirectional, mapping is a project
- **Slack** — workflow notifications; channel-per-segment, not just one #pipeline channel
- **Calendly / Chili Piper** — meeting booking embeds in CRM
- **LinkedIn Sales Navigator** — contact enrichment
- **Clearbit / Apollo / ZoomInfo** — firmographic enrichment
- **Stripe / Chargebee** — close → customer lifecycle automation
- **Product analytics (Mixpanel / Amplitude / Pendo)** — behavioral signals into lead score
- **Custom API** — for product-led signals (in-app actions, usage milestones)

For each integration: map fields explicitly. Document what HubSpot owns vs what the integrated system owns. Ambiguity creates duplicates and overrides.

## Output format

When designing or auditing a CRM:

```
# HubSpot Strategy — [Org] — [Date]

## Business model
- Funnel type: [Demand-gen / Outbound / PLG / Hybrid]
- Sales cycle: [length]
- Pipeline count: [1 / multi, by criterion]

## Lifecycle stages
[Stage list with definitions and entry criteria]

## Pipelines and stages
[Per pipeline: stages, gating events, owners, time-in-stage targets]

## Required properties
[Contact + deal + company, with rationale per field]

## Lead scoring
[Demographic + behavioral, MQL threshold]

## Workflows (priority)
1. [Name] — trigger / action / suppression / goal
2. ...

## Reporting (priority)
1. [Report name] — consumer, cadence, decision it informs

## Sales/marketing handoff
- MQL definition: [precise]
- SLA: [time]
- Disqual / recycle flow: [steps]

## Integrations
[Per integration: scope, field mapping, ownership]

## Hygiene tasks
[Things to do monthly / quarterly]
```

## Anti-patterns

1. ❌ 47 custom properties on the contact record — most blank; review/cull annually
2. ❌ Lifecycle stages used as lead-score bands ("Hot Lead", "Warm Lead") — confuses tooling and reporting
3. ❌ Deal stages that aren't states ("Following Up") — those are activities, not pipeline state
4. ❌ MQL definition like "shows interest" — too vague; pick a score / action
5. ❌ Auto-progressing deal stages based on emails opened — corrupts forecast trust
6. ❌ One mega-workflow for all post-MQL nurture — split by segment / persona / behavior
7. ❌ Marketing emails sent without suppression list (unsubscribes, customers) — legal + brand risk
8. ❌ Lead scoring without decay — old behaviors keep contacts artificially hot
9. ❌ Reports nobody owns — clean them up; useful reports have weekly consumers
10. ❌ Salesforce-HubSpot sync without explicit field ownership map — duplicates, override fights
11. ❌ Treating HubSpot's defaults as the right answer — defaults are starting points; tune to your motion
12. ❌ Skipping the model conversation, jumping to property design — bakes in misalignment
13. ❌ Custom properties for what should be tags / list memberships — properties multiply; tags don't
14. ❌ Deal owner set to a generic queue user — accountability black hole
15. ❌ Lifecycle stage going backward via automation — creates impossible-to-debug loops
16. ❌ Forecasting on stage probability defaults (e.g., "Proposal = 75%") without calibration to actual close rates

## Reference files

- `references/lifecycle-handoff-templates.md` — concrete templates for MQL/SQL definitions, SLAs, disqual flows, by motion type

## Confidence calibration

- Structural recommendations (stage design, property minimalism): high
- Lead scoring threshold values: low — must be calibrated to your data, not template numbers
- Workflow specifics: medium — HubSpot UI / capabilities evolve; verify current behavior
- Salesforce-HubSpot sync recommendations: medium — sync gotchas are version-specific
- Predicted impact of CRM cleanup: refuse to predict; measure pipeline conversion and rep adoption pre/post
