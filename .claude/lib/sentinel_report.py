"""
sentinel_report.py
==================
Read-only report over what Tantra's sentinel bots recorded, plus pruning of
old per-session state.

Why it exists: the sentinels (scribe, pulse, echo, lens, contract, meter,
boundary; .claude/hooks/tantra_core/sentinels/) intervene inside hooks,
where nobody sees the running total. Without a report there is no way to
tell whether they help (tokens avoided, stalls caught) or just add noise
(notes the model ignores), and no way to tune ~/.tantra/config.json from
evidence. Everything here is computed from the append-only ledgers the
hooks wrote; nothing is inferred and no model is called.

Sources (TANTRA_HOME, default ~/.tantra):
  state/<session_id>/dispatch.jsonl   start / stop / returned / contract_block
  state/<session_id>/sentinel.jsonl   every bot action (mode, applied, estimate)
  state/<session_id>/notes.jsonl      meter hotspots and session-budget crossings
  <workspace>/memory/sentinel_runs.jsonl   (optional, --workspace) per-turn summaries

Token savings are ESTIMATES: chars/4 of reads that were denied, and the
recorded transcript usage of re-dispatches a Run Brief or contract fix made
unnecessary. Only interventions that were actually applied count.

Usage:
    python sentinel_report.py report                       # most recent session
    python sentinel_report.py report --session <id>
    python sentinel_report.py report --all --json-out report.json
    python sentinel_report.py report --workspace <client workspace>
    python sentinel_report.py prune --older-than-days 30 [--dry-run]
    (both accept --home PATH to read a TANTRA_HOME other than the default)

Exit codes: 0 success (including "no sentinel data yet", which is a
legitimate state); 1 unknown --session id or an invalid --older-than-days.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

COUNTED_ACTIONS = {
    "run_brief": "re-dispatch briefs injected",
    "depth_note": "spawn-depth notes",
    "compaction_brief": "compaction briefs",
    "stall": "stalls reported",
    "echo_note": "echo notes",
    "echo_cross_scope": "echo cross-agent notes",
    "echo_dispatch_note": "echo identical-dispatch notes",
    "echo_deny": "echo denials",
    "lens_deny": "lens denials",
    "contract_block": "contract fixes requested",
    "contract_note": "contract notes",
    "meter_hotspot": "meter hotspots",
    "meter_note": "meter notes delivered",
    "meter_session_budget": "session budget warnings",
    "boundary_note": "boundary notes",
    "boundary_deny": "boundary denials",
}
ESTIMATE_LABEL = "ESTIMATE (chars/4 of avoided reads; recorded usage of avoided re-dispatches)"


def default_home() -> Path:
    env = os.environ.get("TANTRA_HOME")
    return Path(env).expanduser().resolve() if env else Path.home() / ".tantra"


def read_jsonl(path: Path) -> list[dict]:
    """Tolerant reader: hooks append concurrently, so a torn line is skipped, not fatal."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def percentile(values: list[float], pct: int) -> float | None:
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    rank = max(1, -(-len(values) * pct // 100))
    return values[int(rank) - 1]


def session_dirs(home: Path) -> list[Path]:
    root = home / "state"
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return sorted(dirs, key=newest_mtime)


def newest_mtime(folder: Path) -> float:
    newest = folder.stat().st_mtime
    for dirpath, _dirs, files in os.walk(folder):
        for name in files:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
            except OSError:
                continue
    return newest


# ---------------------------------------------------------------------------
# Per-session rollup
# ---------------------------------------------------------------------------

def latest_stops(dispatch: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in dispatch:
        if r.get("ev") == "stop" and r.get("agent_id"):
            out[r["agent_id"]] = r
    return out


def summarise_session(folder: Path) -> dict:
    dispatch = read_jsonl(folder / "dispatch.jsonl")
    sentinel = read_jsonl(folder / "sentinel.jsonl")
    notes = read_jsonl(folder / "notes.jsonl")
    stops = list(latest_stops(dispatch).values())
    applied = [r for r in sentinel if r.get("action") in COUNTED_ACTIONS and r.get("applied", True)]
    observed = [r for r in sentinel if r.get("action") in COUNTED_ACTIONS and r.get("applied") is False]
    return {
        "session_id": folder.name,
        "dispatches": len(stops),
        "starts": sum(1 for r in dispatch if r.get("ev") == "start"),
        "by_tier": dict(Counter(r.get("tier") or "unknown" for r in stops)),
        "by_agent": dict(Counter(r.get("agent_type") or "unknown" for r in stops).most_common()),
        "durations_s": [r["duration_s"] for r in stops if isinstance(r.get("duration_s"), (int, float))],
        "output_tokens_by_agent": _tokens_by_agent(stops),
        "stalls": [
            {"agent_type": r.get("target"), "agent_id": r.get("stalled_agent_id"), "reason": r.get("reason"),
             "idle_s": r.get("idle_s"), "elapsed_s": r.get("elapsed_s")}
            for r in applied if r.get("action") == "stall"
        ],
        "actions": dict(Counter(r["action"] for r in applied)),
        "observed_only": dict(Counter(r["action"] for r in observed)),
        "est_tokens_avoided": sum(int(r.get("est_tokens_avoided") or 0) for r in applied),
        "hotspots": sorted(
            ({"agent_type": n.get("agent_type"), "agent_id": n.get("agent_id"),
              "output_tokens": n.get("output_tokens") or 0, "duration_s": n.get("duration_s")}
             for n in notes if n.get("ev") == "note" and n.get("kind") == "meter"),
            key=lambda h: -(h["output_tokens"] or 0),
        ),
        "contract_failures": sum(1 for r in stops if r.get("contract_ok") is False),
    }


def _tokens_by_agent(stops: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for r in stops:
        out = (r.get("tokens") or {}).get("output")
        if isinstance(out, int):
            totals[r.get("agent_type") or "unknown"] += out
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))


def combine(sessions: list[dict]) -> dict:
    durations = [d for s in sessions for d in s["durations_s"]]
    by_tier: Counter = Counter()
    by_agent: Counter = Counter()
    actions: Counter = Counter()
    tokens: Counter = Counter()
    for s in sessions:
        by_tier.update(s["by_tier"])
        by_agent.update(s["by_agent"])
        actions.update(s["actions"])
        tokens.update(s["output_tokens_by_agent"])
    hotspots = sorted((h for s in sessions for h in s["hotspots"]), key=lambda h: -(h["output_tokens"] or 0))
    return {
        "sessions": len(sessions),
        "dispatches": sum(s["dispatches"] for s in sessions),
        "by_tier": dict(by_tier),
        "by_agent": dict(by_agent.most_common()),
        "duration_s": {"p50": percentile(durations, 50), "p90": percentile(durations, 90),
                       "max": max(durations) if durations else None},
        "output_tokens_by_agent": dict(tokens.most_common()),
        "output_tokens_total": sum(tokens.values()),
        "stalls": sum(len(s["stalls"]) for s in sessions),
        "actions": dict(actions),
        "est_tokens_avoided": sum(s["est_tokens_avoided"] for s in sessions),
        "est_tokens_avoided_basis": ESTIMATE_LABEL,
        "top_hotspots": hotspots[:10],
    }


def workspace_runs(workspace: Path) -> dict | None:
    runs = read_jsonl(workspace / "memory" / "sentinel_runs.jsonl")
    if not runs:
        return None
    return {
        "file": str(workspace / "memory" / "sentinel_runs.jsonl"),
        "runs": len(runs),
        "dispatches": sum(int(r.get("dispatches") or 0) for r in runs),
        "stalls": sum(len(r.get("stalls") or []) for r in runs),
        "contract_blocks": sum(int(r.get("contract_blocks") or 0) for r in runs),
        "run_briefs": sum(int(r.get("run_briefs") or 0) for r in runs),
        "est_tokens_avoided": sum(int(r.get("est_tokens_avoided") or 0) for r in runs),
        "first": runs[0].get("ts"),
        "last": runs[-1].get("ts"),
    }


def build_report(home: Path, session: str | None, all_sessions: bool, workspace: Path | None) -> dict:
    dirs = session_dirs(home)
    if session:
        chosen = [d for d in dirs if d.name == session]
        if not chosen:
            raise LookupError(f"no sentinel state for session {session!r} under {home / 'state'}")
    elif all_sessions:
        chosen = dirs
    else:
        chosen = dirs[-1:]
    sessions = [summarise_session(d) for d in chosen]
    for s in sessions:
        s["duration_s"] = {"p50": percentile(s["durations_s"], 50), "p90": percentile(s["durations_s"], 90),
                           "max": max(s["durations_s"]) if s["durations_s"] else None}
    return {
        "home": str(home),
        "scope": "session" if session else ("all" if all_sessions else "latest"),
        "sessions": sessions,
        "total": combine(sessions),
        "workspace": workspace_runs(workspace) if workspace else None,
    }


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def _fmt_s(value) -> str:
    return "n/a" if value is None else f"{value:,.0f} s"


def print_report(report: dict) -> None:
    total = report["total"]
    print(f"=== Tantra sentinel report ({report['scope']}; {report['home']}) ===\n")
    if not report["sessions"]:
        print("No sentinel data yet -- no Tantra session has been recorded under this home.")
    for s in report["sessions"]:
        print_session(s)
    if len(report["sessions"]) > 1:
        print("--- Total across sessions ---")
        print(f"Dispatches: {total['dispatches']} by tier {total['by_tier']}")
        print(f"Duration p50/p90/max: {_fmt_s(total['duration_s']['p50'])} / {_fmt_s(total['duration_s']['p90'])} / "
              f"{_fmt_s(total['duration_s']['max'])}")
        print(f"Output tokens: {total['output_tokens_total']:,}  Stalls: {total['stalls']}")
        print(f"Interventions: {total['actions']}")
    print(f"\nEstimated tokens avoided: ~{total['est_tokens_avoided']:,}  [{ESTIMATE_LABEL}]")
    if total["top_hotspots"]:
        print("Top hotspots:")
        for h in total["top_hotspots"][:5]:
            print(f"  {h['agent_type']} ({h['agent_id']}): {h['output_tokens']:,} output tokens, {_fmt_s(h['duration_s'])}")
    ws = report.get("workspace")
    if ws:
        print(f"\nWorkspace summaries ({ws['file']}): {ws['runs']} turn(s), {ws['dispatches']} dispatches, "
              f"{ws['stalls']} stalls, {ws['contract_blocks']} contract fixes, {ws['run_briefs']} run briefs, "
              f"~{ws['est_tokens_avoided']:,} tokens avoided (estimate)")


def print_session(s: dict) -> None:
    d = s["duration_s"]
    print(f"--- Session {s['session_id']} ---")
    print(f"Dispatches: {s['dispatches']} completed ({s['starts']} started) by tier {s['by_tier']}")
    if s["by_agent"]:
        print(f"By agent: {s['by_agent']}")
    print(f"Duration p50/p90/max: {_fmt_s(d['p50'])} / {_fmt_s(d['p90'])} / {_fmt_s(d['max'])}")
    if s["output_tokens_by_agent"]:
        print(f"Output tokens by agent: {s['output_tokens_by_agent']}")
    a = s["actions"]
    print(f"Stalls: {len(s['stalls'])}  Re-dispatch briefs: {a.get('run_brief', 0)}  "
          f"Echo notes/denials: {a.get('echo_note', 0) + a.get('echo_cross_scope', 0) + a.get('echo_dispatch_note', 0)}"
          f"/{a.get('echo_deny', 0)}  Lens denials: {a.get('lens_deny', 0)}  "
          f"Contract fixes: {a.get('contract_block', 0)}  Boundary notes: {a.get('boundary_note', 0) + a.get('boundary_deny', 0)}")
    if s["observed_only"]:
        print(f"Observe-mode (logged, not applied): {s['observed_only']}")
    print(f"Estimated tokens avoided: ~{s['est_tokens_avoided']:,}\n")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_report(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve() if args.home else default_home()
    try:
        report = build_report(home, args.session, args.all, Path(args.workspace) if args.workspace else None)
    except LookupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print_report(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nReport JSON written to {args.json_out}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    if args.older_than_days < 0:
        print("ERROR: --older-than-days must be >= 0", file=sys.stderr)
        return 1
    home = Path(args.home).expanduser().resolve() if args.home else default_home()
    cutoff = time.time() - args.older_than_days * 86400
    removed = []
    for folder in session_dirs(home):
        if newest_mtime(folder) < cutoff:
            removed.append(folder.name)
            if not args.dry_run:
                shutil.rmtree(folder, ignore_errors=True)
    verb = "Would remove" if args.dry_run else "Removed"
    print(f"{verb} {len(removed)} session state folder(s) older than {args.older_than_days} day(s) under {home / 'state'}"
          + (": " + ", ".join(removed) if removed else "."))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("report", help="Summarise what the sentinels recorded.")
    r.add_argument("--home", default=None, help="TANTRA_HOME to read (default: $TANTRA_HOME or ~/.tantra)")
    which = r.add_mutually_exclusive_group()
    which.add_argument("--session", default=None, help="One session id (default: the most recent session)")
    which.add_argument("--all", action="store_true", help="Every recorded session")
    r.add_argument("--workspace", default=None, help="Also summarise <workspace>/memory/sentinel_runs.jsonl")
    r.add_argument("--json-out", default=None)

    pr = sub.add_parser("prune", help="Delete per-session state folders older than N days.")
    pr.add_argument("--home", default=None)
    pr.add_argument("--older-than-days", type=float, required=True)
    pr.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return {"report": cmd_report, "prune": cmd_prune}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
