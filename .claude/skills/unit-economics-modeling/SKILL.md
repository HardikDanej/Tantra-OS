---
name: unit-economics-modeling
description: Activate whenever a strategic option's EVIDENCE field needs an actual projected CAC, LTV, payback period, or ROAS instead of only qualitative reasoning ("this channel looks underpriced"). Runs real arithmetic via `unit_economics.py` against caller-supplied inputs and compares the result to a labeled industry-heuristic band (not a live-sourced benchmark). Used most by the Marketing Strategist Agent and Ads/Paid-Media Agent when building strategic-dispatch options, and by the Revenue/CRM Agent for pipeline-value framing. Refuses to invent inputs the dispatch didn't supply, and refuses to present the benchmark table as anything more authoritative than a commonly-cited heuristic.
---

# Unit Economics Modeling

A strategic option is a weaker claim when its EVIDENCE field is qualitative only. "Paid search looks underpriced for this ICP" is an opinion. "At a $250 modeled CAC and $1,500 modeled LTV (6:1, comfortably above the 3:1 SMB SaaS heuristic), a 4.2-month payback" is a number someone can actually argue with, test, or budget against. This skill is the bridge from the first to the second — real arithmetic on real or explicitly-labeled-as-assumed inputs, never a plausible-sounding number invented to fill a field.

## Core principle

**Compute, don't estimate in prose.** Any time CAC, LTV, payback, or ROAS shows up in an option's EVIDENCE or WHAT WOULD PROVE THIS WRONG field, run it through `python ~/Tantra/.claude/lib/unit_economics.py compute ...` rather than writing "roughly 3-4x" from intuition. The script does the division; you supply and label the inputs.

**Every input is either real or a stated assumption — never silently blended.** An input pulled from the workspace's own connected data (a real spend total, a real churn rate from the account) is real. An input that's a planning scenario ("if we assume a 4% monthly churn based on category norms") is an assumption. The output must say which each input was — this is the same discipline the rest of this system applies to confidence tiers and citation checks, just aimed at model inputs instead of claims.

**The benchmark table is a heuristic, not a fact.** `unit_economics.py benchmarks` returns commonly-cited planning rules of thumb (3:1 LTV:CAC, sub-12-month SaaS payback), not a sourced industry average. Every comparison the script returns carries this caveat in its own output — pass it through to the option's EVIDENCE field intact, don't paraphrase it into something that reads as verified.

## When to use

| Situation | Activate? |
|---|---|
| Building a strategic option (`dispatch_kind: "strategic"`) that makes a channel, pricing, or positioning bet | Yes — the EVIDENCE field should carry a computed number, not just a qualitative read |
| A diagnostic dispatch already has real account CAC/LTV and just needs it stated | Yes, but this is closer to reporting than modeling — still run it through the script for consistent formula labeling |
| Comparing two strategic options that differ in channel or pricing assumption | Yes — run both through the script so the comparison is apples-to-apples, same formula, different inputs |
| The dispatch has no real spend/customer/margin data and none is inferable from workspace state | No — see Refusal-first checks; don't fabricate inputs to produce a number |
| A request for a single ad's copy or a metadata fix | No — no unit-economics claim is being made |

## Workflow

### Step 1 — Identify the business model

`subscription` (recurring revenue, churn-driven LTV) or `transactional` (order-based, lifespan-driven LTV). Don't guess this from the request's vibe — it should be inferable from the workspace's `brand/` artifacts (a SaaS pricing page vs. an ecommerce catalog) or stated directly in the dispatch. If genuinely ambiguous and the choice would change which formula applies, that's worth a one-line flag in GAPS rather than a silent pick.

### Step 2 — Gather inputs, and label each one

Pull from, in order of preference:
1. **Workspace data** — `memory/outcomes.jsonl`, `.memory/brand_identity.json`, or figures a domain agent already reported this session (e.g. the Ads Agent's own-account diagnostic track). Label as `real`.
2. **A domain agent's live research** (a WebFetch/WebSearch figure that already went through `citation_guard.py`). Label as `researched`, and carry its own CITATION_CHECK status forward.
3. **An explicit planning assumption**, stated as one — "assuming a 4% monthly churn, consistent with the category norm the SEO Agent's competitor scan surfaced." Label as `assumed`, and say what it's grounded in even loosely.

Never fabricate an input with no label at all — that's the one thing this skill exists to prevent.

### Step 3 — Run the calculator

```bash
python ~/Tantra/.claude/lib/unit_economics.py compute \
    --model subscription \
    --spend <total acquisition spend for the period> \
    --new-customers <new customers acquired for that spend> \
    --arpu <avg revenue per user per month> \
    --gross-margin <fraction 0-1> \
    --monthly-churn <fraction, e.g. 0.04> \
    --business-type saas_b2b_smb
```

or for a transactional model:

```bash
python ~/Tantra/.claude/lib/unit_economics.py compute \
    --model transactional \
    --spend <spend> --new-customers <n> \
    --aov <avg order value> --gross-margin <fraction> \
    --orders-per-year <orders/customer/year> --customer-lifespan-years <years> \
    --business-type ecommerce_dtc
```

Read the script's own `warnings` array before using the output — it flags things like a churn rate that's plausibly mislabeled as annual, or an LTV built on a hard-to-validate multi-year lifespan assumption. Don't drop these when quoting the result upstream.

### Step 4 — Attach it to the option, with the sourcing intact

In the strategic-dispatch OPTION format, the computed figures go in EVIDENCE, formatted so the formula is visible, not just the output number:

```
EVIDENCE: Modeled at a $250 CAC (real, from Q3 account spend/new-customer data)
and a $1,500 LTV (ARPU $80/mo x 75% gross margin / 4% assumed monthly churn --
churn is an assumption, category norm per SEO Agent's competitor scan, not
measured yet). LTV:CAC of 6:1 sits within the commonly-cited 3:1-and-up
heuristic band for SMB SaaS (planning heuristic, not a sourced industry
average). Payback of 4.2 months is at or under the "excellent" heuristic
threshold for this business type.
```

Never quote just the ratio ("6:1, which is good") without the formula and input labels behind it — a reader can't stress-test a number they can't see the arithmetic for, and the Competitor Red Team Agent's Step 3 (attack the load-bearing assumption) needs exactly this labeling to know which input to attack.

### Step 5 — Feed the load-bearing assumption forward

Whichever input was labeled `assumed` and most drives the result (usually churn rate or customer lifespan) is the natural candidate for the option's own `WHAT WOULD PROVE THIS WRONG` field in the strategic-dispatch format — state it there explicitly rather than burying it only in EVIDENCE. This is also exactly what the Competitor Red Team Agent's Step 3 (Ads/Paid-Media, Marketing Strategist dispatch) reads first when red-teaming the option, so leaving it unstated there weakens that check downstream.

## Refusal-first checks

1. **No inputs, no number.** If the dispatch has no real spend/customer/margin data and nothing inferable from workspace state, don't run the calculator with invented placeholder figures to produce a plausible-looking number — say in GAPS that unit economics can't be modeled without at least a rough spend and customer-count figure, and ask the Orchestrator to source them (a domain agent's own diagnostic pass, or a direct question to the user).
2. **No unlabeled blending of real and assumed inputs.** Every input that isn't from the workspace's own real data must be named as an assumption in the output — a computed LTV built partly on real ARPU and partly on a guessed churn rate is not, overall, "real."
3. **No presenting the heuristic table as verified data.** Always carry `unit_economics.py`'s own sourcing_note forward, or restate its substance, rather than dropping it because it makes the number sound less impressive.
4. **No silent business-model mismatch.** Don't run a subscription business's numbers through the transactional formula (or vice versa) because it's the one you have inputs for — if the actual model doesn't match either shape cleanly (e.g. a usage-based/consumption pricing model), say so and flag that neither formula is a clean fit rather than forcing one.
5. **Zero or near-zero churn/lifespan inputs.** The script itself refuses `--monthly-churn 0` because it produces an infinite LTV — don't work around this by passing a token value like 0.0001 to force a huge number through; use a deliberately-chosen floor and label it as a modeling choice, not a real observation.

## Confidence calibration

**HIGH:** The arithmetic itself, given labeled inputs — a formula applied correctly to stated numbers isn't a judgment call.

**MEDIUM:** Whether a `researched` input (a competitor's public pricing, a category-average AOV pulled from web research) actually transfers cleanly to this brand's context — flag if the source business differs meaningfully in scale or model from the one being modeled.

**LOW:** Any `assumed` input with no grounding beyond "this is a common figure for the category," and any LTV built on a lifespan or churn assumption longer than roughly 18-24 months out — the further the assumption reaches, the less the arithmetic's precision should be trusted as precision rather than a scenario.

## Stop conditions

- No spend, customer-count, or margin data available or inferable — refuse to fabricate inputs; report the gap instead of a number
- The business model doesn't cleanly fit `subscription` or `transactional` (e.g. usage-based/consumption pricing, a hybrid model) — flag the mismatch rather than forcing one formula
- `unit_economics.py` exits 1 (e.g. a zero-churn input) — surface its stated error, don't work around it with a token nonzero value chosen only to avoid the refusal
- A `--business-type` isn't a clean fit for the brand's actual category — run without `--business-type` (arithmetic-only, no benchmark band) rather than picking the closest-sounding option and presenting its heuristic band as if it applied
