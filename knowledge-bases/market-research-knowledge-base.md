# Market Research & Consumer Insights Knowledge Base

Dedicated knowledge base for the Market Research & Consumer Insights agentic system (`primary-research-customer-discovery-agent`, `competitive-market-intelligence-agent`, `marketing-analytics-attribution-modeling-agent`, and their thirty sub-agents). This system already has unusually strong grounding in `marketing-knowledge-base.md`'s MARKETING RESEARCH and MARKETING MEASUREMENT sections — this file goes a level deeper, into the specific methodological and statistical reference material those sections point at but don't fully spell out. Sliced via `kb_slice.py outline` / `section "<heading>"` — never read in full.

## 1. CORE TIER — Research Method Selection

### 1.1 The Method Selection Matrix

The first decision any Primary Research dispatch should make explicit, before any instrument gets designed:

| Question type | Best-fit method(s) | Why |
|---|---|---|
| "What's happening, and how much?" (descriptive) | Quantitative survey, usage analytics | Needs a real number, ideally at scale |
| "Why is this happening?" (exploratory/explanatory) | In-depth interviews, focus groups, ethnographic observation | Needs depth and context a closed-ended survey can't capture |
| "What will happen if we change X?" (causal) | Concept/prototype testing, A/B-style experiments (Growth Ops/CRO Agent, sibling system) | Needs a controlled comparison, not just correlation |
| "How does behavior/attitude change over time?" (longitudinal) | Diary studies, repeated-wave surveys | A single time point can't show a trajectory |
| "What's the real, in-context experience?" (contextual) | Ethnographic/in-context observation, usability testing | Self-report is unreliable for habitual or embodied behavior |

**The governing warning, restated because it's this system's single most load-bearing fact:** stated behavior ≠ observed behavior. A method-selection error that substitutes a cheaper self-report method (a survey) for a genuinely behavioral question (what people actually do) doesn't just produce a weaker answer — it produces a *confidently wrong* one, because the data looks quantitative and rigorous while measuring the wrong thing entirely.

### 1.2 Sampling & Statistical Reference

**Sample size for a proportion** (the formula `quantitative-survey-design-sampling-subagent` should compute via Bash, never estimate by eye):

```
n = (Z² × p × (1 - p)) / E²
```
Where `Z` = the z-score for the desired confidence level (1.96 for 95%, 2.576 for 99%), `p` = estimated proportion (use 0.5 if genuinely unknown — it's the most conservative/largest-sample assumption), `E` = desired margin of error (as a decimal, e.g. 0.05 for ±5%).

**Finite population correction** (apply when sampling a small, known population — e.g., a company's own 3,000-customer base, not the general public):
```
n_adjusted = n / (1 + (n - 1) / N)
```
Where `N` = total population size. Skipping this correction on a small known population overstates the needed sample size.

**Confidence interval for a proportion:**
```
CI = p ± Z × sqrt(p × (1 - p) / n)
```

**Statistical power reference** (relevant when a concept test or survey needs to detect a real difference between two groups, not just describe one): the four inputs that trade off against each other are effect size, sample size, significance threshold (α, conventionally 0.05), and power (1-β, conventionally 0.80). Increasing any one of effect size, sample size, or α increases power; a study that can't afford a larger sample has to either accept lower power or only claim to detect a larger effect size.

### 1.3 Bias Taxonomy — the checklist every research design should be run against

| Bias | What it does | Which method it hits hardest |
|---|---|---|
| Recall bias | Respondents misremember past events/decisions, often reconstructing a cleaner narrative than what happened | Interviews, retrospective surveys — the exact reason diary studies exist |
| Social desirability bias | Respondents answer how they think they *should*, not how they actually feel/act | Any self-report, worse in group settings |
| Groupthink / dominant-voice distortion | Group consensus reads as if every member independently held it | Focus groups specifically — never report group consensus as individually-held belief |
| Selection/self-selection bias | Who chose to participate isn't representative of who the finding is claimed to describe | Any opt-in panel or convenience sample |
| Survivorship bias | Only looking at customers who stayed (or won deals) hides the reasons others left (or lost) | Win/loss analysis when only closed-won deals get reviewed |
| Confirmation bias (researcher-side) | A discussion guide or survey worded to elicit the answer already expected | Instrument design itself — the reason a second reviewer on guide wording matters |
| Leading-question bias | Question wording implies the "right" answer | Interview guides, survey items |

## 2. REFERENCE TIER — Competitive & Market Intelligence

### 2.1 Competitive Intelligence Source Taxonomy

Real, citable public sources `competitive-market-intelligence-agent`'s sub-agents should draw from, ranked roughly by reliability for a *current* fact (verify freshness on all of them — this is not a live feed):

1. **Regulatory filings** (10-K/10-Q/S-1 for public companies, patent filings) — highest reliability, legally attested, but lagged and only covers public/patenting companies
2. **The company's own pricing/product pages** — current by definition when fetched live, but reflects what they want shown, not internal reality
3. **Job postings** — a genuinely underused signal: a surge in postings for a specific role/region reveals real strategic investment before it's announced
4. **Review sites** (G2, Capterra, TrustRadius) — real customer voice, but selection-biased toward extreme (very happy or very frustrated) reviewers
5. **Web archive / Wayback Machine** — for tracking how a competitor's own positioning/pricing has changed over time
6. **Conference talks, webinars, earnings calls** — often where genuinely new strategic information gets said first, before a press release

### 2.2 Market Sizing Methods (all computed, never asserted)

| Method | Approach | Best when |
|---|---|---|
| **Top-down** | Start from a broad industry-size figure (analyst report), narrow by real filtering criteria (geography, segment, use case) | A credible industry report exists for the category |
| **Bottom-up** | Real unit economics × real addressable unit count (e.g., price per customer × number of real target customers) | Direct data on target customer count is available or estimable |
| **Value-theory** | Estimate the real economic value created/saved per customer, multiplied by adoption-realistic capture rate | No existing market to size — the product creates a genuinely new category |

`tam-sam-som-market-sizing-subagent`'s discipline: TAM (Total Addressable Market) → SAM (Serviceable, i.e. the segment the current product/GTM can actually reach) → SOM (Serviceable Obtainable, i.e. a realistic capture percentage of SAM given competition and go-to-market capacity) — each narrowing step needs its own named justification, not just a round-number haircut applied for looking appropriately conservative.

### 2.3 Win/Loss Analysis Structure

A structured interview covers, at minimum: (1) the buying committee's actual decision criteria, ranked; (2) which competitors were genuinely in the final consideration set (not just who was pitched); (3) the specific moment or factor that tipped the decision; (4) what would have changed the outcome. A win/loss program that only interviews closed-won deals cannot distinguish "we're good" from "we only talk to people who already picked us" — see survivorship bias above.

## 3. REFERENCE TIER — Attribution & Measurement Math

### 3.1 Multi-Touch Attribution Model Reference

All models below distribute 100% credit for a conversion across the customer's real touchpoint history — the difference is entirely in *how* the credit splits:

| Model | Credit distribution |
|---|---|
| First-touch | 100% to the first touchpoint |
| Last-touch | 100% to the last touchpoint before conversion |
| Linear | Equal credit to every touchpoint |
| Time-decay | More credit to touchpoints closer in time to conversion (commonly a 7-day half-life) |
| Position-based (U-shaped) | 40% first, 40% last, 20% split across the middle touchpoints |
| Algorithmic/data-driven | Credit weights derived from a real statistical model (e.g., Shapley value or a trained conversion-probability model) comparing converted vs. non-converted paths |

**The governing distinction, restated because it's this domain's single most load-bearing fact:** every model above is **correlational** (the Attribution rung) — it answers "who touched the path," never "who caused the conversion to happen at all." Proving causation requires a real experiment (geo-holdout, matched-market test, PSA/ghost-ad holdout) — the Causal rung, owned by `incremental-lift-media-incrementality-subagent`.

### 3.2 Core Financial Formulas

```
CAC (Customer Acquisition Cost) = Total acquisition spend / Number of customers acquired
LTV (Lifetime Value) = Average revenue per customer × Gross margin % × Average customer lifespan
LTV:CAC ratio = LTV / CAC        (commonly cited healthy benchmark: 3:1 or higher — a labeled heuristic, not a law)
Payback period = CAC / (Average monthly revenue per customer × Gross margin %)
ROAS (Return on Ad Spend) = Revenue attributed / Ad spend
```

Every one of these requires real inputs — `cac-payback-analysis-subagent` and `clv-ltv-modeling-subagent` compute them via Bash from real supplied data; neither ever fills in an assumed number to complete the formula.

## 4. Market Research Maturity Ladder

```
Anecdotal (decisions justified by isolated stories/opinions, no instrument behind them)
  → Systematic (real instruments, real sampling, real analysis — but reactive, one-off)
    → Predictive (a standing research/measurement program that forecasts, not just describes)
```

A recommendation to build a predictive-tier capability (e.g., ongoing propensity modeling) for an organization still at the anecdotal rung is skipping the systematic-rung foundation that predictive models actually depend on for real training data.
