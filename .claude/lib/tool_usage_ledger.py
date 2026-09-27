"""
tool_usage_ledger.py
======================
The OS blueprint's "Cost & Model Routing" (Section 24) cost-tracking half:
"track cost per agent, workflow, campaign, customer and business outcome"
and "set budgets and maximum execution limits" -- for the one surface in
this repo where cost is actually real and observable: calls to the paid/
rate-limited external connectors in marketing-os-infra/lib/ (see the Tool
Registry in data-model/core_data_model.json, gap #2).

Deliberately NOT built: a token/model-cost tracker for the Claude Code
side of this system. No script in this repo (confirmed while building the
observability layer, gap #3) has access to per-dispatch token counts or
model spend -- inventing a dollar figure there would be exactly the kind
of fabricated-looking-precise number this repo's own agents are built to
refuse. This ledger tracks what IS real: how many times each connector
was actually called, and (only when a real, cited $/call or $/month
figure is supplied -- never guessed) what that cost.

Why call-VOLUME is the primary unit, not dollars: every connector marked
requires_paid_api in the Tool Registry (survey/product-analytics/media-
coverage/social-profile/HubSpot/press-wire) is billed as a platform
subscription or a rate-limited free tier, not a metered per-call charge.
The number that actually matters operationally is "are we about to blow
through this month's request quota," not a fabricated per-call dollar
amount. cost_usd stays optional and null unless a real figure is given.

MCP connectors write here too: the Tantra connectors_guard hook appends one
line per MCP tool call made inside a Tantra workspace, with
tool="mcp:<server>" and note=<the MCP tool name> -- never the tool's
arguments or output -- so check-budget can put a ceiling on MCP call volume
exactly as it does for the Python connectors.

Usage (--ledger may go before or after the subcommand):
    python tool_usage_ledger.py log --ledger memory/tool_usage_log.jsonl --tool hubspot_connector [--calls 1] [--cost-usd 0] [--status ok|error] [--note "..."]
    python tool_usage_ledger.py report --ledger memory/tool_usage_log.jsonl [--period-days 30] [--json-out PATH]
    python tool_usage_ledger.py check-budget --ledger memory/tool_usage_log.jsonl --config memory/budget_config.json [--period-days 30] [--strict]

Budget config: one object per tool id, {"period_days", "max_calls",
"max_cost_usd"}. Keys starting with "_" (e.g. the template's "_comment") are
documentation and skipped. A limit that is not a number -- the template's
"REPLACE_WITH_YOUR_LIMIT", or a tool with no numeric limit at all -- is
reported as NOT CONFIGURED instead of silently passing as "within budget".

Exit codes:
    log:           0 always (logging a call is never itself a failure).
    report:        0 always.
    check-budget:  0 if no configured tool exceeds its ceiling (NOT
                     CONFIGURED tools are listed, but have no ceiling to
                     exceed).
                   1 if any tool exceeds its configured max_calls or
                     max_cost_usd for the period -- the calling agent
                     should surface this rather than make the next call --
                     or, with --strict, if any tool is NOT CONFIGURED.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolUsageEvent(BaseModel):
    tool: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    calls: int = 1
    status: str = "ok"  # "ok" | "error"
    cost_usd: Optional[float] = None  # only ever set from a real, cited figure -- never guessed
    note: str = ""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_events(ledger_path: Path) -> list[dict]:
    if not ledger_path.exists():
        return []
    events = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue  # hooks append concurrently; one torn line must not hide every other call
        if isinstance(event, dict):
            events.append(event)
    return events


def append_event(ledger_path: Path, event: ToolUsageEvent) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")


def _within_period(timestamp: str, period_days: Optional[int]) -> bool:
    if period_days is None:
        return True
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    return ts >= cutoff


def summarize(events: list[dict], period_days: Optional[int] = None) -> dict[str, Any]:
    totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls": 0, "errors": 0, "cost_usd": 0.0,
                                                              "cost_known": False})
    for e in events:
        if not _within_period(e.get("timestamp", ""), period_days):
            continue
        tool = e.get("tool", "unknown")
        totals[tool]["calls"] += e.get("calls", 1)
        if e.get("status") == "error":
            totals[tool]["errors"] += 1
        if e.get("cost_usd") is not None:
            totals[tool]["cost_usd"] += e["cost_usd"]
            totals[tool]["cost_known"] = True
    return {"period_days": period_days, "by_tool": dict(totals)}


def cmd_log(args: argparse.Namespace) -> int:
    event = ToolUsageEvent(tool=args.tool, calls=args.calls, status=args.status,
                            cost_usd=args.cost_usd, note=args.note or "")
    append_event(Path(args.ledger), event)
    print(f"Logged: {event.model_dump_json()}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    events = read_events(Path(args.ledger))
    summary = summarize(events, args.period_days)
    period_label = f"last {args.period_days} days" if args.period_days else "all time"
    print(f"=== Tool usage report ({period_label}) -- {args.ledger} ===\n")
    if not summary["by_tool"]:
        print("No usage logged yet.")
        return 0
    for tool, stats in sorted(summary["by_tool"].items()):
        cost_str = f"${stats['cost_usd']:.2f}" if stats["cost_known"] else "unknown (no real figure supplied)"
        print(f"  {tool}: {stats['calls']} calls, {stats['errors']} errors, cost={cost_str}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nWrote {args.json_out}")
    return 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def budget_entries(config: dict) -> tuple[dict[str, dict], list[str]]:
    """Split a budget config into usable per-tool limit dicts and NOT CONFIGURED notes.

    A limit only counts when it is a number. null means "deliberately no
    limit of this kind"; any other value (the template's placeholder string)
    is a limit someone meant to set and didn't, so it is reported rather than
    treated as satisfied.
    """
    usable: dict[str, dict] = {}
    not_configured: list[str] = []
    for tool, limits in config.items():
        if tool.startswith("_"):
            continue
        if not isinstance(limits, dict):
            not_configured.append(f"{tool}: entry is {type(limits).__name__}, expected an object with max_calls/max_cost_usd")
            continue
        bad = [f"{key}={limits[key]!r}" for key in ("max_calls", "max_cost_usd")
               if limits.get(key) is not None and not _is_number(limits[key])]
        if bad:
            not_configured.append(f"{tool}: {', '.join(bad)} is not a number -- no ceiling is enforced for it")
        elif not any(_is_number(limits.get(key)) for key in ("max_calls", "max_cost_usd")):
            not_configured.append(f"{tool}: no numeric max_calls or max_cost_usd -- no ceiling is enforced")
        usable[tool] = limits
    return usable, not_configured


def cmd_check_budget(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"No budget config at {args.config} -- nothing to check against. "
              f"See model-routing/budget_config.template.json for the shape.")
        return 0
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        print(f"Budget config {args.config} must be a JSON object of tool id -> limits.")
        return 1
    usable, not_configured = budget_entries(config)
    events = read_events(Path(args.ledger))

    over_budget = []
    for tool, limits in usable.items():
        period_days = limits.get("period_days", args.period_days)
        if not _is_number(period_days):
            period_days = args.period_days
        summary = summarize(events, period_days)
        stats = summary["by_tool"].get(tool, {"calls": 0, "cost_usd": 0.0, "cost_known": False})
        max_calls = limits.get("max_calls")
        max_cost = limits.get("max_cost_usd")
        if _is_number(max_calls) and stats["calls"] > max_calls:
            over_budget.append(f"{tool}: {stats['calls']} calls > max_calls={max_calls} "
                                f"(period {period_days}d)")
        if _is_number(max_cost) and stats["cost_known"] and stats["cost_usd"] > max_cost:
            over_budget.append(f"{tool}: ${stats['cost_usd']:.2f} > max_cost_usd={max_cost} "
                                f"(period {period_days}d)")

    enforced = sum(1 for limits in usable.values()
                   if any(_is_number(limits.get(key)) for key in ("max_calls", "max_cost_usd")))
    if over_budget:
        print(f"OVER BUDGET -- {len(over_budget)} issue(s):")
        for issue in over_budget:
            print(f"  - {issue}")
    elif enforced > 0:
        print(f"OK -- all {enforced} tool(s) with a numeric limit are within budget.")
    else:
        print("NO LIMITS ENFORCED -- no tool in this config has a numeric limit yet.")
    if not_configured:
        print(f"NOT CONFIGURED -- {len(not_configured)} tool(s):")
        for note in not_configured:
            print(f"  - {note}")
    if over_budget or (args.strict and not_configured):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ledger", default="memory/tool_usage_log.jsonl")
    # The same flag on every subcommand, defaulting to SUPPRESS so a value
    # given before the subcommand is not overwritten by the subparser default.
    ledger_after = argparse.ArgumentParser(add_help=False)
    ledger_after.add_argument("--ledger", default=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="command", required=True)

    def add_sub(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[ledger_after], **kwargs)

    lg = add_sub("log", help="Record one connector call.")
    lg.add_argument("--tool", required=True, help="Tool Registry id, e.g. hubspot_connector")
    lg.add_argument("--calls", type=int, default=1)
    lg.add_argument("--status", choices=["ok", "error"], default="ok")
    lg.add_argument("--cost-usd", type=float, default=None,
                     help="Only pass this if you have a real, cited $ figure for this call -- never a guess.")
    lg.add_argument("--note", default="")

    rp = add_sub("report", help="Summarize usage by tool.")
    rp.add_argument("--period-days", type=int, default=None)
    rp.add_argument("--json-out", default=None)

    cb = add_sub("check-budget", help="Check usage against a configured ceiling.")
    cb.add_argument("--config", default="memory/budget_config.json")
    cb.add_argument("--period-days", type=int, default=30,
                     help="Default period if a tool's config entry doesn't specify its own period_days.")
    cb.add_argument("--strict", action="store_true",
                     help="Also exit 1 when any tool is NOT CONFIGURED (no numeric limit).")

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "log":
        return cmd_log(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "check-budget":
        return cmd_check_budget(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
