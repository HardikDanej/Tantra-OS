# Ideal Customer Profile

> **Note:** This is a template. The Revenue Intelligence Agent will refuse to score deals against an ICP that contains placeholder language ("e.g.", "[fill in]", "industry: various"). Spend an hour with your VP Sales filling this in honestly. Generic ICPs produce generic scores; specific ICPs produce actionable ones.

---

## 1. Firmographic criteria

These are the *non-negotiable* attributes. A prospect missing more than one of these is rarely worth pursuing, regardless of expressed interest.

**Industry / vertical:**
List the 3–5 industries where you have demonstrated traction. Not "B2B SaaS" — too broad. "Vertical SaaS for healthcare staffing agencies" or "DTC apparel brands at $5M-$50M revenue."

- Industry 1: [specific vertical]
- Industry 2: [specific vertical]
- Industry 3: [specific vertical]

**Company size:**
- Employee headcount range: [e.g., 50–500]
- Annual revenue range: [e.g., $5M–$50M ARR]
- Funding stage (if relevant): [e.g., Series A through C]

**Geography:**
- Primary markets: [e.g., North America, UK]
- Secondary markets: [if any]
- Hard-no geographies: [where compliance, support, or ICP fit makes the geo unworkable]

**Operating model attributes:**
- [e.g., Multi-location operations]
- [e.g., Distributed workforce >40%]
- [e.g., Contract-based revenue model]

---

## 2. Technographic criteria

The tools and tech stack that signal a prospect can actually use what you sell.

**Required tools (prospect must have one of these):**
- [e.g., Salesforce or HubSpot CRM]
- [e.g., Slack or MS Teams for primary comms]

**Indicative tools (presence increases ICP fit):**
- [e.g., Snowflake or BigQuery — signals data maturity]
- [e.g., Marketo or HubSpot Marketing Hub — signals marketing maturity]

**Disqualifying tools (presence is red flag):**
- [e.g., Custom homegrown CRM — usually means engineering-driven, slow to adopt new tools]
- [e.g., Recently switched CRM <90 days ago — won't add new tools right now]

---

## 3. Buying triggers

Specific events or signals that indicate a prospect is in the buying window.

**Strong triggers (act within 48 hours):**
- [e.g., Posted a job for "Head of Revenue Operations"]
- [e.g., Series B funding announcement in the last 60 days]
- [e.g., Public statement about scaling sales team 2x]

**Medium triggers (act within 2 weeks):**
- [e.g., Hired a new VP Sales in the last 90 days]
- [e.g., Launched a new product line]
- [e.g., Announced expansion into new geography]

**Weak triggers (worth noting but not acting on alone):**
- [e.g., Visited pricing page 3+ times]
- [e.g., Downloaded our top-funnel ebook]

---

## 4. Disqualifiers

Red flags that mean "don't pursue, no matter how interested they seem." These are the lessons learned from deals you wish you'd disqualified earlier.

**Hard disqualifiers (refuse to engage):**
- [e.g., Active litigation visible in public records]
- [e.g., Decision-maker title is "Consultant" or "Advisor" — proxy buyer]
- [e.g., Required procurement process exceeds 6 months]

**Soft disqualifiers (engage with caution, flag in notes):**
- [e.g., More than 2 decision-makers turned over in the last 12 months]
- [e.g., Currently using a competitor with multi-year contract]
- [e.g., Reference customer in their industry has churned]

---

## 5. Decision-maker profile

Who actually signs. Without this, the agent can't score "decision-maker engagement" meaningfully.

**Primary decision-maker:**
- Title patterns: [e.g., "VP Revenue Operations", "Director of Sales Operations", "Head of GTM Operations"]
- Seniority: [e.g., 2 levels below CRO, OR direct report to CRO at sub-100-employee orgs]
- Tenure indicator: [e.g., 6+ months in current role — too new = no political capital]
- Buying authority: [e.g., signing authority up to $100k, board approval over $250k]

**Champion profile (the person who advocates internally):**
- Title patterns: [e.g., "Senior Operations Analyst", "RevOps Manager"]
- Behavioral signals: [e.g., active on LinkedIn about RevOps, attends industry events]

**Economic buyer (who controls the budget — may differ from primary):**
- Title patterns: [e.g., "CRO", "VP Sales", "CFO at sub-200 employee orgs"]
- Engagement requirement: [e.g., must have at least one 1:1 conversation before contract signature]

**Blocker profile (who can kill the deal):**
- Title patterns: [e.g., IT/Security if data is involved, Legal for contract review]
- Engagement strategy: [e.g., loop in by Stage 4, never wait until Stage 6]

---

## 6. Value lever per persona

How does this customer measure success after buying? Different ICP segments respond to different value framings.

**For [Persona 1 — fill in name]:**
- Primary pain: [what brings them to category]
- Their measure of success: [how they'll know it worked, in their words]
- Objection they'll voice: [the specific resistance they bring]
- The proof we offer: [the case study, metric, or demo that lands]

**For [Persona 2 — fill in name]:**
- Primary pain:
- Their measure of success:
- Objection they'll voice:
- The proof we offer:

(Add as many personas as your real ICP supports — typically 2–3.)

---

## 7. Calibration history

This section is *not* a template — it's the living record of where this ICP has been wrong, and how it's been refined. Update quarterly.

| Date | Change | Reason |
|------|--------|--------|
| [YYYY-MM-DD] | [What was changed in the ICP] | [What deal experience drove the change] |

---

## How the agent uses this document

The Revenue Intelligence Agent reads this file at every daily run. Specifically:

- **Step 3 of the daily prompt** scores top deals against this ICP across firmographic, technographic, decision-maker engagement, and disqualifier dimensions.
- **Re-engagement drafting (Step 4)** uses Section 6 to match the value lever to the persona profile in the deal record.
- **Forecast risk flagging** uses Section 4 to surface deals carrying disqualifiers that should reduce confidence in their close probability.

If this document is missing, generic, or contains placeholder text, the agent will refuse to score deals against ICP and will instead post a status message asking for the document to be populated.
