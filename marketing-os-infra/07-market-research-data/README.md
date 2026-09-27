# 07 — Market Research Data

Read-only Tool-layer connectors for the **Market Research & Consumer Insights** agentic system — closing that system's previous zero-live-data-access state, which every one of its domain agents disclosed explicitly ("no live human-subject contact, no live platform API access").

## Two connectors, both structurally read-only

1. **`survey_results_pull.py`** — real, already-collected responses from Typeform/SurveyMonkey, for `quantitative-survey-design-sampling-subagent` and `nps-csat-audit-subagent`. There is no field/send function in `survey_platform_connector.py` — that's not a missing feature, it's the enforced boundary. This system designs the instrument; it never fields the study.
2. **`product_analytics_pull.py`** — real usage events from Amplitude/Mixpanel, for `product-analytics-cohort-retention-subagent`, whose output becomes the canonical cohort-computation source the Product Marketing & GTM system and Digital Marketing & Growth's Revenue/CRM Agent should consume rather than re-deriving.

**Neither connector can write to its platform.** No event-tracking call, no survey-creation call, no cohort-modification call exists anywhere in either connector module. This mirrors the domain agent's own hardest constraint at the code level, not just the prompt level.

## Setup

Fill in `config.json` with real credentials per platform (see each block's `_help` field). Then:

```bash
python3 survey_results_pull.py --platform typeform --form-id <your-form-id>
python3 product_analytics_pull.py --platform amplitude --start 20260801 --end 20260901
```

## Output

Each run writes a CSV under `output/` plus a `.sources.json` manifest (`tool_router.write_source_manifest`) — read the manifest before treating either CSV as a complete dataset; a partial pull (an expired token, a rate limit) is recorded there, not silently absorbed into a smaller-looking-but-still-confident file.
