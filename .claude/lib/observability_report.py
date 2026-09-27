"""
observability_report.py
=========================
The OS blueprint's "Observability & Operations" (Section 23) as a real,
computed rollup over logs that already exist -- instead of workflow
success rate, escalation frequency, and human-approval rate living only
as raw jsonl lines a human has to read one at a time.

Every number in this report is computed from a real ledger already
written by an existing script in this repo:
  - memory/checkpoints.jsonl       (chief-marketing-orchestrator.md Step 6)
  - memory/evaluations.jsonl       (output_evaluator.py)
  - memory/redispatch_log.jsonl    (redispatch_tracker.py)
  - memory/approval_gates.jsonl    (approval_gate.py)
  - memory/outcomes.jsonl          (chief-marketing-orchestrator.md Outcome Feedback)
  - memory/triggers.jsonl          (trigger_registry.py)

Confidence-vs-actual-outcome is NOT recomputed here -- it imports and
reuses calibration_tracker.py's real `compute_calibration()` directly, the
same "require, don't duplicate" rule this repo already follows elsewhere.

Honest about what it can't measure: agent/model/tool LATENCY, token/model/
tool COST, and KPI movement / agent-workflow ROI are all real blueprint
metrics this report does NOT compute, because no script in this repo logs
per-dispatch timing, token counts, spend, or a KPI time series today. Each
is listed under `not_computable` with the specific instrumentation that
would need to exist first -- not silently omitted, and not faked with a
placeholder number.

Exception, when the data exists: in a workspace where Tantra's sentinel
hooks ran, memory/sentinel_runs.jsonl records every Tantra dispatch's
duration and the token usage from its own transcript. Then the report
computes a `timing_and_tokens` section (per-agent duration p50/p90/max and
output tokens) and drops the agent-timing and model-usage entries from
`not_computable`. Without that file both stay listed as not computable.

Usage:
    python observability_report.py report [--workspace .] [--min-sample-size 3] [--json-out memory/observability_report.json]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "lib"))

from calibration_tracker import read_jsonl, build_checkpoint_index, compute_calibration  # noqa: E402

DEFAULT_MAX_REDISPATCH_ATTEMPTS = 2  # matches redispatch_tracker.py's DEFAULT_MAX_ATTEMPTS

NOT_COMPUTABLE = [
    {"metric": "Agent latency and reliability (timing)",
     "why": "No script logs a dispatch start/end timestamp pair -- checkpoints.jsonl records that a "
            "dispatch happened, never how long it took.",
     "would_need": "Each orchestrator's Step 5/6 would need to record dispatch_started_at/"
                   "dispatch_completed_at per contract."},
    {"metric": "Model latency and usage",
     "why": "This system runs inside Claude Code sessions; no lib script has access to per-call model "
            "latency or token usage today.",
     "would_need": "A logging hook at the model-call boundary itself (outside this repo's current scope)."},
    {"metric": "Tool latency and errors",
     "why": "PullResult (tool_router.py) records success/partial/error per source, but not call duration.",
     "would_need": "A started_at/finished_at pair added to PullResult alongside the existing errors list."},
    {"metric": "Token/model/tool cost",
     "why": "No script anywhere in this repo captures token counts or per-call spend.",
     "would_need": "A cost-tracking layer (this is its own named gap, separate from observability) that "
                    "logs token/dollar cost per dispatch."},
    {"metric": "KPI movement after AI interventions",
     "why": "No script maintains a KPI time series; outcomes.jsonl records a recommendation's real-world "
            "result in the user's own words, not a numeric KPI delta.",
     "would_need": "A structured KPI-value log tied to checkpoint_ref, updated from real reported numbers "
                   "(never inferred)."},
    {"metric": "Agent/workflow ROI",
     "why": "Requires both cost (not tracked) and a numeric business-value figure (not tracked) per "
            "dispatch/workflow.",
     "would_need": "Both of the above, joined."},
]


def _read(path: Path) -> list[dict]:
    return read_jsonl(path) if path.exists() else []


def workflow_and_dispatch_stats(checkpoints: list[dict]) -> dict[str, Any]:
    by_system: Counter = Counter()
    by_agent: Counter = Counter()
    by_dispatch_kind: Counter = Counter()
    timestamps = []
    for cp in checkpoints:
        by_system[cp.get("system") or "chief-marketing-orchestrator"] += 1
        ts = cp.get("timestamp")
        if ts:
            timestamps.append(ts)
        for contract in cp.get("contracts", []):
            agent = contract.get("agent")
            if agent:
                by_agent[agent] += 1
            kind = contract.get("dispatch_kind")
            if kind:
                by_dispatch_kind[kind] += 1
    return {
        "total_runs": len(checkpoints),
        "runs_by_system": dict(by_system),
        "dispatch_volume_by_agent": dict(by_agent.most_common()),
        "dispatch_kind_distribution": dict(by_dispatch_kind),
        "date_range": {"earliest": min(timestamps) if timestamps else None,
                       "latest": max(timestamps) if timestamps else None},
    }


def output_quality_stats(evaluations: list[dict]) -> dict[str, Any]:
    """Proxy for 'workflow success/failure rate' + 'agent reliability' -- the closest real signal
    this repo has for those two blueprint metrics, from output_evaluator.py's own verdicts."""
    overall: Counter = Counter()
    by_agent: dict[str, Counter] = defaultdict(Counter)
    for ev in evaluations:
        verdict = ev.get("verdict", "UNKNOWN")
        overall[verdict] += 1
        agent = ev.get("agent")
        if agent:
            by_agent[agent][verdict] += 1

    total = sum(overall.values())
    pass_like = overall.get("PASS", 0) + overall.get("PASS_WITH_FLAGS", 0)

    per_agent = {}
    for agent, counts in by_agent.items():
        agent_total = sum(counts.values())
        agent_pass = counts.get("PASS", 0) + counts.get("PASS_WITH_FLAGS", 0)
        per_agent[agent] = {
            "total": agent_total, "counts": dict(counts),
            "pass_rate": round(agent_pass / agent_total, 3) if agent_total else None,
        }

    return {
        "total_evaluations": total,
        "overall_counts": dict(overall),
        "overall_pass_rate": round(pass_like / total, 3) if total else None,
        "by_agent": per_agent,
    }


def retry_and_escalation_stats(redispatch_events: list[dict],
                                max_attempts: int = DEFAULT_MAX_REDISPATCH_ATTEMPTS) -> dict[str, Any]:
    by_cycle: dict[str, list[dict]] = defaultdict(list)
    for e in redispatch_events:
        cid = e.get("cycle_id")
        if cid:
            by_cycle[cid].append(e)

    escalated, resolved, open_within_cap = 0, 0, 0
    cycle_detail = {}
    for cid, events in by_cycle.items():
        events_sorted = sorted(events, key=lambda e: e.get("timestamp", ""))
        last_resolve_idx = max((i for i, e in enumerate(events_sorted) if e.get("event") == "resolved"), default=-1)
        attempts_since = [e for e in events_sorted[last_resolve_idx + 1:] if e.get("event") == "attempt"]
        was_resolved_at_all = any(e.get("event") == "resolved" for e in events_sorted)
        attempt_count = len(attempts_since)
        status = "escalated" if attempt_count > max_attempts else ("open" if attempt_count > 0 else "resolved")
        if status == "escalated":
            escalated += 1
        elif status == "resolved" or was_resolved_at_all and attempt_count == 0:
            resolved += 1
        else:
            open_within_cap += 1
        cycle_detail[cid] = {"attempts_since_last_resolve": attempt_count, "status": status}

    total_cycles = len(by_cycle)
    return {
        "total_cycles": total_cycles,
        "escalated_cycles": escalated,
        "resolved_cycles": resolved,
        "open_within_cap_cycles": open_within_cap,
        "escalation_rate": round(escalated / total_cycles, 3) if total_cycles else None,
        "max_attempts_cap": max_attempts,
        "cycles": cycle_detail,
    }


def human_approval_stats(gate_events: list[dict]) -> dict[str, Any]:
    by_gate: dict[str, list[dict]] = defaultdict(list)
    for e in gate_events:
        gid = e.get("gate_id")
        if gid:
            by_gate[gid].append(e)

    terminal_counts: Counter = Counter()
    by_stakes_class: dict[str, Counter] = defaultdict(Counter)
    pending_gate_ids = []
    for gid, events in by_gate.items():
        events_sorted = sorted(events, key=lambda e: e.get("timestamp", ""))
        latest = events_sorted[-1]
        status = latest.get("event", "unknown")
        terminal_counts[status] += 1
        stakes = latest.get("stakes_class", "unknown")
        by_stakes_class[stakes][status] += 1
        if status == "pending":
            pending_gate_ids.append(gid)

    decided = terminal_counts.get("approved", 0) + terminal_counts.get("rejected", 0)
    return {
        "total_gates": len(by_gate),
        "status_counts": dict(terminal_counts),
        "approval_rate_of_decided": round(terminal_counts.get("approved", 0) / decided, 3) if decided else None,
        "still_pending_gate_ids": pending_gate_ids,
        "by_stakes_class": {k: dict(v) for k, v in by_stakes_class.items()},
    }


def trigger_activity_stats(trigger_events: list[dict]) -> dict[str, Any]:
    fired: Counter = Counter()
    acknowledged_ids = set()
    fired_ids = set()
    by_kind_fired: Counter = Counter()
    for e in trigger_events:
        tid = e.get("trigger_id")
        event = e.get("event")
        if event == "fired":
            fired[tid] += 1
            fired_ids.add(tid)
            if e.get("kind"):
                by_kind_fired[e["kind"]] += 1
        elif event == "acknowledged":
            acknowledged_ids.add(tid)

    dangling = sorted(fired_ids - acknowledged_ids)
    return {
        "total_fires": sum(fired.values()),
        "fires_by_trigger_id": dict(fired),
        "fires_by_kind": dict(by_kind_fired),
        "dangling_unacknowledged_trigger_ids": dangling,
    }


SENTINEL_MEASURED_METRICS = {"Agent latency and reliability (timing)", "Model latency and usage"}


def _percentile(values: list[float], pct: int) -> Any:
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    rank = max(1, -(-len(values) * pct // 100))
    return values[int(rank) - 1]


def timing_and_token_stats(runs: list[dict]) -> dict[str, Any]:
    """Real per-dispatch timing and token rollups from memory/sentinel_runs.jsonl.

    Tantra's sentinel hooks (scribe + meter) record every Tantra subagent's
    start/stop time and the usage its own transcript recorded, then write one
    summary line per turn into the workspace. That closes the two timing/usage
    gaps listed in NOT_COMPUTABLE for any workspace where the hooks ran.
    """
    durations_by_agent: dict[str, list[float]] = defaultdict(list)
    output_by_agent: Counter = Counter()
    total_by_agent: Counter = Counter()
    by_tier: Counter = Counter()
    contract_misses: Counter = Counter()
    for run in runs:
        for d in run.get("dispatch_list") or []:
            agent = d.get("agent_type") or "unknown"
            by_tier[d.get("tier") or "unknown"] += 1
            if isinstance(d.get("duration_s"), (int, float)):
                durations_by_agent[agent].append(d["duration_s"])
            output_by_agent[agent] += d.get("output_tokens") or 0
            total_by_agent[agent] += d.get("total_tokens") or 0
            if d.get("contract_ok") is False:
                contract_misses[agent] += 1
    all_durations = [v for vals in durations_by_agent.values() for v in vals]
    per_agent = {
        agent: {"dispatches": len(vals), "p50_s": _percentile(vals, 50), "p90_s": _percentile(vals, 90),
                "max_s": max(vals), "output_tokens": output_by_agent.get(agent, 0),
                "total_tokens": total_by_agent.get(agent, 0)}
        for agent, vals in sorted(durations_by_agent.items())
    }
    return {
        "source": "memory/sentinel_runs.jsonl (Tantra sentinel hooks)",
        "turns_recorded": len(runs),
        "dispatches": sum(int(r.get("dispatches") or 0) for r in runs),
        "dispatches_by_tier": dict(by_tier),
        "duration_s": {"p50": _percentile(all_durations, 50), "p90": _percentile(all_durations, 90),
                       "max": max(all_durations) if all_durations else None},
        "per_agent": per_agent,
        "output_tokens_total": sum(int(r.get("output_tokens_total") or 0) for r in runs),
        "output_tokens_by_agent": dict(output_by_agent.most_common()),
        "stalls": sum(len(r.get("stalls") or []) for r in runs),
        "contract_misses_by_agent": dict(contract_misses),
        "est_tokens_avoided": sum(int(r.get("est_tokens_avoided") or 0) for r in runs),
        "token_basis": "usage recorded in each subagent's own Claude Code transcript; avoided tokens are ESTIMATES",
    }


def build_report(workspace: Path, min_sample_size: int) -> dict[str, Any]:
    checkpoints = _read(workspace / "memory" / "checkpoints.jsonl")
    evaluations = _read(workspace / "memory" / "evaluations.jsonl")
    redispatch_events = _read(workspace / "memory" / "redispatch_log.jsonl")
    gate_events = _read(workspace / "memory" / "approval_gates.jsonl")
    outcomes = _read(workspace / "memory" / "outcomes.jsonl")
    trigger_events = _read(workspace / "memory" / "triggers.jsonl")
    sentinel_runs = _read(workspace / "memory" / "sentinel_runs.jsonl")

    checkpoint_index = build_checkpoint_index(checkpoints)
    calibration = compute_calibration(outcomes, checkpoint_index, min_sample_size)
    timing = timing_and_token_stats(sentinel_runs) if sentinel_runs else None
    not_computable = [m for m in NOT_COMPUTABLE if not (timing and m["metric"] in SENTINEL_MEASURED_METRICS)]

    return {
        "workspace": str(workspace),
        "workflow_and_dispatch": workflow_and_dispatch_stats(checkpoints),
        "output_quality": output_quality_stats(evaluations),
        "retry_and_escalation": retry_and_escalation_stats(redispatch_events),
        "human_approval": human_approval_stats(gate_events),
        "trigger_activity": trigger_activity_stats(trigger_events),
        "confidence_calibration": calibration,
        "timing_and_tokens": timing,
        "not_computable": not_computable,
    }


def print_report(report: dict[str, Any]) -> None:
    wf = report["workflow_and_dispatch"]
    print(f"=== Observability Report -- {report['workspace']} ===\n")
    print(f"Workflow runs: {wf['total_runs']}  (range: {wf['date_range']['earliest']} -> {wf['date_range']['latest']})")
    print(f"Runs by system: {wf['runs_by_system']}")
    print(f"Dispatch volume by agent: {wf['dispatch_volume_by_agent']}")
    print(f"Dispatch kind distribution: {wf['dispatch_kind_distribution']}")

    oq = report["output_quality"]
    print(f"\nOutput quality (proxy for workflow success/failure + agent reliability):")
    print(f"  overall pass rate: {oq['overall_pass_rate']}  counts: {oq['overall_counts']}")
    for agent, stats in oq["by_agent"].items():
        print(f"    {agent}: pass_rate={stats['pass_rate']} n={stats['total']} {stats['counts']}")

    re_ = report["retry_and_escalation"]
    print(f"\nRetry/escalation: {re_['total_cycles']} cycles, "
          f"escalation_rate={re_['escalation_rate']} (cap={re_['max_attempts_cap']})")

    ha = report["human_approval"]
    print(f"\nHuman approval: {ha['total_gates']} gates, "
          f"approval_rate_of_decided={ha['approval_rate_of_decided']}, "
          f"still_pending={len(ha['still_pending_gate_ids'])}")

    ta = report["trigger_activity"]
    print(f"\nTrigger activity: {ta['total_fires']} fires, "
          f"{len(ta['dangling_unacknowledged_trigger_ids'])} dangling unacknowledged")

    cal = report["confidence_calibration"]
    print(f"\nConfidence calibration: {len(cal['per_agent_tier'])} (agent, tier) entries, "
          f"{len(cal['flags'])} flags")
    for f in cal["flags"]:
        print(f"  ! {f}")

    tt = report.get("timing_and_tokens")
    if tt:
        d = tt["duration_s"]
        print(f"\nTiming and tokens ({tt['source']}): {tt['dispatches']} dispatches over {tt['turns_recorded']} turn(s), "
              f"duration p50/p90/max = {d['p50']}/{d['p90']}/{d['max']} s, "
              f"{tt['output_tokens_total']:,} output tokens, {tt['stalls']} stall(s)")
        for agent, stats in tt["per_agent"].items():
            print(f"    {agent}: n={stats['dispatches']} p50={stats['p50_s']}s max={stats['max_s']}s "
                  f"output_tokens={stats['output_tokens']:,}")

    print(f"\nNot computable today ({len(report['not_computable'])} metrics) -- see 'not_computable' in JSON output.")


def cmd_report(args: argparse.Namespace) -> int:
    report = build_report(Path(args.workspace), args.min_sample_size)
    print_report(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nWrote {args.json_out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("report", help="Compute and print the observability report.")
    r.add_argument("--workspace", default=".", help="Workspace root (default: current directory)")
    r.add_argument("--min-sample-size", type=int, default=3)
    r.add_argument("--json-out", default=None)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "report":
        return cmd_report(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
