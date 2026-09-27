# Evals

These agents are prompts, not code. Nothing stops the underlying model from drifting between versions — a routing rule that held on one Claude release can silently soften on the next. There's no compiler to catch that.

This used to mean: 45 hand-written cases across 7 markdown files, run by dispatching each input to the named agent and eyeballing the output against a pass/fail condition — "no automated harness," fifteen minutes of manual work every time. It's now `run_evals.py` plus `scenarios/scenarios.json`: 30 scenarios, consolidated from those 45 cases (plus new coverage — a `social-media-agent` eval never existed until now, and a scenario covering the `redispatch_tracker.py` loop-detection cap added in a later pass than the original files), each one dispatched to the target agent's actual system prompt and graded by an LLM judge against a scenario-specific boundary check plus a fixed rubric of four dimensions: **actionability, factual accuracy, brand-voice adherence, strategic depth**.

## How to run these

```
pip install anthropic
export ANTHROPIC_API_KEY=...          # required — grading calls a real model, there's no free path here
python run_evals.py                    # every scenario
python run_evals.py --target seo-agent # only scenarios for one agent
python run_evals.py --scenario-id co-07-redispatch-cap-escalation
```

No API key handy? `python run_evals.py --dry-run` validates the scenario bank — every `target_agent_file` exists, every graded dimension is a recognized name, every scenario has something to actually grade — without calling anything. That's the part CI can run for free on every commit; the scored pass requires the key.

Each run writes a full JSON report to `results/run_<timestamp>.json` (gitignored — these are regenerated, not source) and prints a summary: pass/fail/error counts, and for every failure, which boundary was violated or which dimension scored below its threshold, with the judge's stated reasoning. Exit code is non-zero if anything failed or errored — wire this into a pre-commit hook or CI step and a regression gets caught before it ships, not the next time someone notices the output feels off.

## What the judge actually checks

Every scenario carries a `boundary_check` (a MUST and a MUST NOT — largely the same crisp behavioral checks the old markdown cases tested: does it refuse to draft, does it refuse to authorize spend, does it hold the YMYL gate) and/or a subset of `graded_dimensions` from the four listed above. Not every scenario grades all four — a pure refusal check doesn't need a brand-voice score, and forcing one would just be judge noise. `ads-04-creative-brief-quality` and `wr-04-client-voice-stays-generic` are the two scenarios written specifically to exercise real output quality across multiple dimensions at once, rather than a single refusal condition — most of this system's existing risk was already boundary-shaped, so most scenarios still are, but the four-dimension rubric exists so quality regressions (a brief that technically complies but reads generic, a strategic option that's cosmetically two but not actually distinct) get caught too, not just hard refusals.

## The honest limits of this, stated plainly

- **The judge is a model, not a compiler.** It's called at `temperature=0` to cut run-to-run variance, but it can still be wrong — too lenient on a subtly-off response, too harsh on a correct one phrased unusually. Treat one scenario's verdict the way you'd treat one code-review comment: informative, not infallible. If a verdict looks wrong, read `judge_verdict.boundary_reasoning` / `dimension_reasoning` in the results file before assuming the agent (or the judge) is broken.
- **This does not replace the deterministic guardrails in `.claude/lib/`.** `tool_router.py`, `citation_guard.py`, and `redispatch_tracker.py` check literal facts against literal evidence — fully reproducible, no model involved in the check itself. The eval harness tests agent *behavior* (does it refuse correctly, does it reason well) using a model to grade a model. Different failure modes, different tools.
- **A scenario's `context` is synthetic.** It's realistic-looking test data (a deal's activity log, an ad's fatigue signals, a voice guide), not a live pull from a real CRM/ad account. A scenario passing here says the agent's *reasoning* is sound given that input — it says nothing about whether a real HubSpot/Meta/GSC pull would hand it clean data (that's what `marketing-os-infra/lib/tool_router.py`'s manifests are for).

## When to run these

- After any edit to an agent definition file, or a scenario file
- After a Claude model version change
- Before trusting a new domain (a new brand, a new client) with real output for the first time
- Any time an agent's real-world output feels off and you want to know if it's the agent or the input

## What a failure means

A failed scenario doesn't mean the whole agent is broken. It means one specific behavior regressed, or one output-quality dimension dropped below threshold. Fix that in the agent definition, re-run just that scenario (`--scenario-id`), then re-run the full target agent's scenarios once more before considering it closed — a fix for one scenario can accidentally break another testing the same agent.

## Files

```
scenarios/scenarios.json   The 30 scenarios — source of truth for what actually runs.
run_evals.py                The harness.
results/                    Gitignored run output, one timestamped JSON per run.
*.md (the original 7)       Kept as human-readable narrative and provenance — every
                             scenario's "source" field names which case it came from.
                             Superseded for *running* purposes by scenarios.json, the
                             same way marketing-os-infra's original scripts are kept
                             for their setup steps but superseded for reasoning logic.
```

| Original file | What it covered | Migrated to |
|---|---|---|
| `chief-marketing-orchestrator.md` | Gatekeeper discipline, boundary refusal, decomposition correctness | `co-01` .. `co-07` |
| `marketing-strategist-agent.md` | Stage ordering, evidence-grounding refusals | `ms-01` .. `ms-03` |
| `seo-agent.md` | Non-drafting boundary, quality-bar enforcement, Website Dev Agent lane discipline | `seo-01` .. `seo-03` |
| `website-development-agent.md` | No-write-access boundary, no invented performance numbers, SEO Agent lane discipline | `wd-01` .. `wd-04` |
| `ads-paid-media-agent.md` | Fatigue-signal corroboration, spend/execution boundary, public-track performance-visibility ceiling | `ads-01` .. `ads-04` |
| `writing-content-production-agent.md` | Personal-voice routing, no-brief refusal, standing governance | `wr-01` .. `wr-04` |
| `revenue-crm-agent.md` | Activity-verified stalled detection, do-not-contact boundary | `rev-01` .. `rev-03` |
| *(none existed)* | `social-media-agent` had no eval file until this pass | `sm-01`, `sm-02` |
