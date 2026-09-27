"""
run_evals.py
============
Automated eval harness for Tantra. Replaces "run these 45
cases by hand across 7 markdown files" with a script that dispatches each
scenario in evals/scenarios/scenarios.json to the target agent's actual
system prompt, then grades the response with an LLM judge on a fixed
rubric (a per-scenario boundary check, plus a subset of four named
quality dimensions: actionability, factual_accuracy,
brand_voice_adherence, strategic_depth).

What this is NOT: a replacement for the four deterministic guardrail
scripts already in .claude/lib/ (tool_router.py, citation_guard.py,
redispatch_tracker.py). Those check literal facts against literal
evidence and are fully reproducible. An LLM judge is not — it is a
probabilistic grader, run at temperature 0 to reduce (not eliminate) run-
to-run variance, and it can be wrong in either direction: too lenient on
a subtly-off response, or too harsh on a correct one phrased unusually.
Treat a single scenario's verdict the way you'd treat a single code
review comment — informative, not infallible. What this harness buys you
that manual grading didn't: it actually runs on every change, instead of
"there's no automated harness... running one means dispatching by hand."

Requires: `pip install anthropic`, and ANTHROPIC_API_KEY set in the
environment. This is the one part of this project's eval layer that
can't be free — grading requires calling a model. Everything else about
the harness (scenario format, scoring logic, reporting) has no other
external dependency.

Usage:
    python run_evals.py                          # run every scenario
    python run_evals.py --scenario-id seo-01-non-drafting-boundary
    python run_evals.py --target seo-agent        # only scenarios for one agent file
    python run_evals.py --dry-run                 # validate scenarios + agent files, no API calls
    python run_evals.py --candidate-model claude-sonnet-4-5 --judge-model claude-opus-4-5

Exit code: 0 if every scenario's boundary_check held (or had none) and
every graded dimension met its min_score. Non-zero otherwise — wire this
into a pre-commit hook or CI step the same way the citation/tool-routing
guardrails are wired into agent contracts, so a regression is caught
before it ships, not the next time someone happens to notice.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = ROOT / "evals" / "scenarios" / "scenarios.json"
RESULTS_DIR = ROOT / "evals" / "results"

DEFAULT_CANDIDATE_MODEL = "claude-sonnet-4-5"
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-5"
ALL_DIMENSIONS = ["actionability", "factual_accuracy", "brand_voice_adherence", "strategic_depth"]

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_scenarios() -> dict:
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))


def agent_system_prompt(target_agent_file: str) -> str:
    """Strip YAML frontmatter from an agent .md file, leaving the actual system prompt body."""
    path = ROOT / target_agent_file
    if not path.exists():
        raise FileNotFoundError(f"Target agent file not found: {path}")
    text = path.read_text(encoding="utf-8")
    return FRONTMATTER_RE.sub("", text, count=1).strip()


def build_candidate_user_turn(scenario: dict) -> str:
    parts = []
    if scenario.get("context"):
        parts.append(f"[Context provided with this dispatch]\n{scenario['context']}")
    parts.append(scenario["input"])
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_TEMPLATE = """You are an exacting eval judge for a marketing-agent system. You will be shown:
1. The scenario that was dispatched to a specific domain agent (its input and any supplied context).
2. A boundary check for this scenario, if one applies — a specific behavior the agent MUST show and a specific behavior it MUST NOT show. This is the hard gate.
3. A list of quality dimensions to score for this scenario, drawn from this fixed rubric:

{dimension_rubric}

Only score dimensions that are in the scenario's graded_dimensions list — for any dimension not listed, output null, do not guess a score for it.

Score each listed dimension 1-5 using the rubric text above. Be exacting: a 3 is "acceptable, does the job," not "pretty good." A response that is fluent and confident but violates the boundary check, or invents facts, should score low on factual_accuracy regardless of how well-written it is — polish is not a substitute for the specific thing being tested.

Respond with ONLY a single JSON object, no other text, no markdown code fence, in exactly this shape:
{{
  "boundary_held": true | false | null,
  "boundary_reasoning": "one or two sentences citing what in the response satisfied or violated the boundary check, or null if no boundary_check applied",
  "dimension_scores": {{"actionability": 1-5 or null, "factual_accuracy": 1-5 or null, "brand_voice_adherence": 1-5 or null, "strategic_depth": 1-5 or null}},
  "dimension_reasoning": "one or two sentences per scored dimension explaining the score, citing specifics from the response",
  "overall_verdict": "PASS" | "FAIL"
}}

overall_verdict is FAIL if boundary_held is false, OR if any scored dimension is below its scenario's min_score. Otherwise PASS."""


def dimension_rubric_text(dims: dict[str, str]) -> str:
    return "\n".join(f"- {name} (1-5): {desc}" for name, desc in dims.items())


def build_judge_user_turn(scenario: dict, candidate_response: str) -> str:
    boundary = scenario.get("boundary_check")
    boundary_text = (
        f"MUST: {boundary['must']}\nMUST NOT: {boundary['must_not']}"
        if boundary else "No boundary_check for this scenario — grade dimensions only."
    )
    graded = scenario.get("graded_dimensions", [])
    return f"""SCENARIO INPUT:
{scenario['input']}

SCENARIO CONTEXT:
{scenario.get('context') or '(none)'}

BOUNDARY CHECK:
{boundary_text}

DIMENSIONS TO GRADE FOR THIS SCENARIO: {graded if graded else '(none — boundary check only)'}
MIN SCORE FOR A PASS ON ANY GRADED DIMENSION: {scenario.get('min_score', 3)}

AGENT'S ACTUAL RESPONSE TO EVALUATE:
{candidate_response}"""


def parse_judge_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    scenario_id: str
    status: str  # "pass" | "fail" | "error"
    candidate_response: str = ""
    judge_verdict: dict = field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_scenario(scenario: dict, client, candidate_model: str, judge_model: str) -> ScenarioResult:
    try:
        system_prompt = agent_system_prompt(scenario["target_agent_file"])
    except FileNotFoundError as e:
        return ScenarioResult(scenario["id"], "error", error=str(e))

    user_turn = build_candidate_user_turn(scenario)

    try:
        candidate = client.messages.create(
            model=candidate_model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_turn}],
        )
        candidate_text = "".join(b.text for b in candidate.content if b.type == "text")
    except Exception as e:
        return ScenarioResult(scenario["id"], "error", error=f"candidate call failed: {e}")

    dims_needed = {d: desc for d, desc in ALL_DIMENSIONS_DESC.items() if d in scenario.get("graded_dimensions", [])} or ALL_DIMENSIONS_DESC
    judge_system = JUDGE_SYSTEM_TEMPLATE.format(dimension_rubric=dimension_rubric_text(ALL_DIMENSIONS_DESC))
    judge_user = build_judge_user_turn(scenario, candidate_text)

    try:
        judge = client.messages.create(
            model=judge_model,
            max_tokens=1000,
            temperature=0,
            system=judge_system,
            messages=[{"role": "user", "content": judge_user}],
        )
        judge_text = "".join(b.text for b in judge.content if b.type == "text")
        verdict = parse_judge_json(judge_text)
    except Exception as e:
        return ScenarioResult(scenario["id"], "error", candidate_response=candidate_text,
                               error=f"judge call/parse failed: {e}")

    status = "pass" if verdict.get("overall_verdict") == "PASS" else "fail"
    return ScenarioResult(scenario["id"], status, candidate_response=candidate_text, judge_verdict=verdict)


ALL_DIMENSIONS_DESC: dict[str, str] = {}  # populated in main() from scenarios.json's own dimensions block


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(results: list[ScenarioResult]) -> None:
    passed = [r for r in results if r.status == "pass"]
    failed = [r for r in results if r.status == "fail"]
    errored = [r for r in results if r.status == "error"]

    print(f"\n{'=' * 60}")
    print(f"{len(results)} scenario(s): {len(passed)} pass, {len(failed)} fail, {len(errored)} error")
    print(f"{'=' * 60}\n")

    for r in failed:
        v = r.judge_verdict
        print(f"FAIL  {r.scenario_id}")
        if v.get("boundary_held") is False:
            print(f"      boundary violated: {v.get('boundary_reasoning', '')}")
        for dim, score in (v.get("dimension_scores") or {}).items():
            if score is not None and isinstance(score, (int, float)):
                print(f"      {dim}: {score}")
        print()

    for r in errored:
        print(f"ERROR {r.scenario_id}: {r.error}\n")


def write_results_file(results: list[ScenarioResult], candidate_model: str, judge_model: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"run_{timestamp}.json"
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "candidate_model": candidate_model,
        "judge_model": judge_model,
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r.status == "pass"),
            "fail": sum(1 for r in results if r.status == "fail"),
            "error": sum(1 for r in results if r.status == "error"),
        },
        "results": [
            {
                "scenario_id": r.scenario_id,
                "status": r.status,
                "judge_verdict": r.judge_verdict,
                "error": r.error,
                "candidate_response": r.candidate_response,
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Dry run — validates the scenario bank and every referenced agent file
# without calling the API. This is what CI can run with no API key to
# catch a broken scenario file or a renamed agent before anyone pays for
# a real eval pass.
# ---------------------------------------------------------------------------

def dry_run(scenarios: list[dict]) -> int:
    problems = []
    seen_ids = set()
    for s in scenarios:
        if s["id"] in seen_ids:
            problems.append(f"duplicate scenario id: {s['id']}")
        seen_ids.add(s["id"])
        try:
            agent_system_prompt(s["target_agent_file"])
        except FileNotFoundError as e:
            problems.append(str(e))
        for dim in s.get("graded_dimensions", []):
            if dim not in ALL_DIMENSIONS:
                problems.append(f"{s['id']}: unknown dimension '{dim}'")
        if not s.get("boundary_check") and not s.get("graded_dimensions"):
            problems.append(f"{s['id']}: has neither a boundary_check nor any graded_dimensions — nothing would be graded")

    if problems:
        print(f"DRY RUN: {len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"DRY RUN: {len(scenarios)} scenario(s) valid — every target_agent_file exists, "
          f"every graded dimension is recognized, every scenario has something to grade.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario-id", default=None, help="Run only this scenario id")
    parser.add_argument("--target", default=None, help="Run only scenarios whose target_agent_file contains this substring (e.g. 'seo-agent')")
    parser.add_argument("--dry-run", action="store_true", help="Validate scenarios and agent files; no API calls")
    parser.add_argument("--candidate-model", default=DEFAULT_CANDIDATE_MODEL)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    args = parser.parse_args()

    data = load_scenarios()
    global ALL_DIMENSIONS_DESC
    ALL_DIMENSIONS_DESC = data["dimensions"]
    scenarios = data["scenarios"]

    if args.scenario_id:
        scenarios = [s for s in scenarios if s["id"] == args.scenario_id]
        if not scenarios:
            print(f"No scenario with id '{args.scenario_id}'", file=sys.stderr)
            return 2
    if args.target:
        scenarios = [s for s in scenarios if args.target in s["target_agent_file"]]
        if not scenarios:
            print(f"No scenario targets '{args.target}'", file=sys.stderr)
            return 2

    if args.dry_run:
        return dry_run(scenarios)

    try:
        import anthropic
    except ImportError:
        print("ERROR: the 'anthropic' package is required to run real evals. "
              "Install it with `pip install anthropic`, or use --dry-run to validate "
              "the scenario bank without calling the API.", file=sys.stderr)
        return 2

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set. Grading requires calling a real model — "
              "there's no free path here, unlike the rest of this project's research tooling. "
              "Set the key, or use --dry-run to validate the scenario bank without it.", file=sys.stderr)
        return 2

    client = anthropic.Anthropic()

    results = []
    for scenario in scenarios:
        print(f"Running {scenario['id']}...", end=" ", flush=True)
        result = run_scenario(scenario, client, args.candidate_model, args.judge_model)
        print(result.status.upper())
        results.append(result)

    print_summary(results)
    out_path = write_results_file(results, args.candidate_model, args.judge_model)
    print(f"Full results written to {out_path}")

    any_hard_failure = any(r.status in ("fail", "error") for r in results)
    return 1 if any_hard_failure else 0


if __name__ == "__main__":
    sys.exit(main())
