#!/usr/bin/env python3
"""Tantra Laya Screen: a generic, deterministic calibrated-confidence
pre-screen used by any Tantra orchestrator's HITL / stakes-classification
step (System 1, fast, non-LLM) before its own System 2 judgment finalizes a
gate. Modeled on Sot Engi's sot-engi-gate-screen skill, generalized so any
orchestrator can supply its own trigger questions instead of a fixed set.

Reads one JSON object from a file path given as argv[1], or from stdin if
no argv[1] is given:
    {
      "objective": "...",
      "deliverable_text": "...",
      "questions": {
        "<trigger_key>": {"type": "noul", "instructions": "..."},
        ...
      },
      "flag_threshold": 0.85   // optional, defaults to 0.85
    }

Always prints exactly one line of JSON to stdout and exits 0, even when
Laya isn't installed, the model fails to load, or inference fails — a
broken screen must never crash an orchestrator's synthesis pass or produce
something that isn't valid JSON. A failure is reported as {"error": "..."}
with every trigger's probability null and flagged false, so it can never
manufacture a false-positive or false-negative gate.

This script never decides whether a gate should open. It reports one
model's calibrated read of the supplied text; the orchestrator's own
Step 4.6-equivalent judgment weighs that against everything else it knows
(specialist findings, Red Team verdict, company-specific boundaries) and
is the only thing that actually opens or skips a gate.
"""
import json
import sys
import time

DEFAULT_FLAG_THRESHOLD = 0.85


def emit(obj):
    print(json.dumps(obj))


def empty_triggers(questions):
    return {k: {"probability": None, "flagged": False} for k in questions}


def main():
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            emit({"error": "could not read input file %s: %s" % (sys.argv[1], e),
                  "triggers": {}, "flag_threshold": DEFAULT_FLAG_THRESHOLD})
            return
    else:
        raw = sys.stdin.read()

    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        emit({"error": "invalid JSON input: %s" % e,
              "triggers": {}, "flag_threshold": DEFAULT_FLAG_THRESHOLD})
        return

    objective = payload.get("objective") or ""
    deliverable_text = payload.get("deliverable_text") or ""
    questions = payload.get("questions") or {}
    flag_threshold = payload.get("flag_threshold", DEFAULT_FLAG_THRESHOLD)

    if not questions:
        emit({"error": "no questions supplied — caller must name at least one trigger to screen for",
              "triggers": {}, "flag_threshold": flag_threshold})
        return

    state = {"objective": objective, "deliverable": deliverable_text}

    try:
        import laya
    except Exception as e:
        emit({
            "error": (
                "laya not importable: %s -- run `pip install laya` (or "
                "`pip install -r requirements.txt` in "
                ".claude/skills/tantra-laya-screen/scripts/) in the Python "
                "environment the calling orchestrator's Bash tool resolves" % e
            ),
            "triggers": empty_triggers(questions),
            "flag_threshold": flag_threshold,
        })
        return

    try:
        agent = laya.load("convaiinnovations/laya")
    except Exception as e:
        emit({"error": "laya model load failed: %s" % e,
              "triggers": empty_triggers(questions), "flag_threshold": flag_threshold})
        return

    # Timed from here, not from laya.load() above: load includes a first-run
    # Hugging Face download (seconds to minutes, or paused indefinitely if
    # the machine sleeps mid-download) that would otherwise swamp the actual
    # inference latency this field is meant to report.
    start = time.time()
    try:
        result = agent.predict(state, questions)
    except Exception as e:
        emit({"error": "laya inference failed: %s" % e,
              "triggers": empty_triggers(questions), "flag_threshold": flag_threshold})
        return
    latency_ms = (time.time() - start) * 1000.0

    triggers = {}
    answers = result.get("answers", {}) if isinstance(result, dict) else {}
    for key, q in questions.items():
        ans = answers.get(key) or {}
        prob = ans.get(q.get("type", "noul"))
        triggers[key] = {
            "probability": prob,
            "flagged": bool(prob is not None and prob >= flag_threshold),
        }

    emit({
        "model": "laya-english (convaiinnovations/laya)",
        "triggers": triggers,
        "flag_threshold": flag_threshold,
        "latency_ms": round(latency_ms, 1),
        "error": None,
    })


if __name__ == "__main__":
    main()
