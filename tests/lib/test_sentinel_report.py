"""Tests for sentinel_report.py and the sentinel-data additions to context_budget.py,
trigger_registry.py and observability_report.py."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(REPO, ".claude", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import context_budget  # noqa: E402
import observability_report  # noqa: E402
import sentinel_report  # noqa: E402
import trigger_registry  # noqa: E402


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def iso(delta_days=0):
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def capture(func, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = func(*args)
    return code, out.getvalue(), err.getvalue()


DISPATCH = [
    {"ev": "start", "t": 1, "agent_id": "a1", "agent_type": "seo-agent", "tier": "domain"},
    {"ev": "start", "t": 2, "agent_id": "b1", "agent_type": "technical-seo-subagent", "tier": "sub"},
    {"ev": "stop", "t": 50, "agent_id": "b1", "agent_type": "technical-seo-subagent", "tier": "sub", "duration_s": 48,
     "contract_ok": False, "tokens": {"output": 1000, "total": 5000}},
    {"ev": "contract_block", "agent_id": "b1"},
    {"ev": "stop", "t": 60, "agent_id": "b1", "agent_type": "technical-seo-subagent", "tier": "sub", "duration_s": 58,
     "contract_ok": True, "tokens": {"output": 1200, "total": 6000}},
    {"ev": "stop", "t": 120, "agent_id": "a1", "agent_type": "seo-agent", "tier": "domain", "duration_s": 119,
     "contract_ok": True, "tokens": {"output": 30000, "total": 90000}},
    {"ev": "returned", "t": 121, "tool_use_id": "t1", "subagent_type": "seo-agent", "status": "completed", "agent_id": "a1"},
    {"ev": "start", "t": 130, "agent_id": "c1", "agent_type": "seo-agent", "tier": "domain"},
]
SENTINEL = [
    {"source": "scribe", "action": "run_brief", "applied": True, "est_tokens_avoided": 4000},
    {"source": "echo", "action": "echo_deny", "applied": True, "est_tokens_avoided": 700},
    {"source": "echo", "action": "echo_note", "applied": True, "est_tokens_avoided": 0},
    {"source": "lens", "action": "lens_deny", "applied": True, "est_tokens_avoided": 6000},
    {"source": "lens", "action": "lens_deny", "applied": False, "est_tokens_avoided": 0},
    {"source": "contract", "action": "contract_block", "applied": True, "est_tokens_avoided": 5000},
    {"source": "boundary", "action": "boundary_note", "applied": True},
    {"source": "pulse", "action": "stall", "applied": True, "target": "seo-agent", "stalled_agent_id": "c1",
     "reason": "idle", "idle_s": 400, "elapsed_s": 500},
    {"source": "echo", "action": "deny", "chars": 300},
]
NOTES = [{"ev": "note", "kind": "meter", "agent_id": "a1", "agent_type": "seo-agent", "output_tokens": 30000, "duration_s": 119}]


def sentinel_run(ts, **overrides):
    run = {
        "schema": "tantra-sentinel-run/1", "ts": ts, "session_id": "s1", "dispatches": 2, "starts": 2,
        "by_tier": {"domain": 1, "sub": 1}, "output_tokens_total": 31200,
        "dispatch_list": [
            {"agent_type": "seo-agent", "tier": "domain", "duration_s": 119, "output_tokens": 30000, "total_tokens": 90000, "contract_ok": True},
            {"agent_type": "technical-seo-subagent", "tier": "sub", "duration_s": 58, "output_tokens": 1200, "total_tokens": 6000, "contract_ok": False},
        ],
        "stalls": [], "interventions": {}, "denials": {}, "contract_blocks": 1, "run_briefs": 1,
        "repeated_reads": [], "hotspots": [], "est_tokens_avoided": 15700,
    }
    run.update(overrides)
    return run


class HomeCase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="tantra_home_")
        self.addCleanup(shutil.rmtree, self.home, True)

    def session(self, sid, dispatch=DISPATCH, sentinel=SENTINEL, notes=NOTES, age_days=0):
        folder = os.path.join(self.home, "state", sid)
        write_jsonl(os.path.join(folder, "dispatch.jsonl"), dispatch)
        write_jsonl(os.path.join(folder, "sentinel.jsonl"), sentinel)
        write_jsonl(os.path.join(folder, "notes.jsonl"), notes)
        if age_days:
            stamp = time.time() - age_days * 86400
            for name in os.listdir(folder):
                os.utime(os.path.join(folder, name), (stamp, stamp))
            os.utime(folder, (stamp, stamp))
        return folder


class SentinelReportTests(HomeCase):
    def test_session_rollup(self):
        self.session("s1")
        report = sentinel_report.build_report(sentinel_report.Path(self.home), "s1", False, None)
        s = report["sessions"][0]
        self.assertEqual(s["dispatches"], 2)
        self.assertEqual(s["starts"], 3)
        self.assertEqual(s["by_tier"], {"sub": 1, "domain": 1})
        self.assertEqual(s["output_tokens_by_agent"], {"seo-agent": 30000, "technical-seo-subagent": 1200})
        self.assertEqual(s["duration_s"], {"p50": 58, "p90": 119, "max": 119})
        self.assertEqual(s["actions"]["lens_deny"], 1)
        self.assertEqual(s["observed_only"], {"lens_deny": 1})
        self.assertEqual(len(s["stalls"]), 1)
        self.assertEqual(s["est_tokens_avoided"], 4000 + 700 + 6000 + 5000)
        self.assertEqual(report["total"]["top_hotspots"][0]["agent_type"], "seo-agent")
        self.assertIn("ESTIMATE", report["total"]["est_tokens_avoided_basis"])

    def test_cli_default_is_latest_session_and_all_combines(self):
        self.session("old", age_days=3)
        self.session("new")
        code, out, _ = capture(sentinel_report.main, ["report", "--home", self.home])
        self.assertEqual(code, 0)
        self.assertIn("Session new", out)
        self.assertNotIn("Session old", out)
        self.assertIn("Estimated tokens avoided: ~15,700", out)
        json_out = os.path.join(self.home, "r.json")
        code, out, _ = capture(sentinel_report.main, ["report", "--home", self.home, "--all", "--json-out", json_out])
        with open(json_out, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["total"]["sessions"], 2)
        self.assertEqual(data["total"]["dispatches"], 4)
        self.assertIn("Total across sessions", out)

    def test_unknown_session_is_exit_1_and_empty_home_is_fine(self):
        code, out, _ = capture(sentinel_report.main, ["report", "--home", self.home])
        self.assertEqual(code, 0)
        self.assertIn("No sentinel data yet", out)
        code, _, err = capture(sentinel_report.main, ["report", "--home", self.home, "--session", "nope"])
        self.assertEqual(code, 1)
        self.assertIn("nope", err)

    def test_workspace_summaries(self):
        self.session("s1")
        ws = tempfile.mkdtemp(prefix="tantra_ws_")
        self.addCleanup(shutil.rmtree, ws, True)
        write_jsonl(os.path.join(ws, "memory", "sentinel_runs.jsonl"), [sentinel_run(iso()), sentinel_run(iso())])
        code, out, _ = capture(sentinel_report.main, ["report", "--home", self.home, "--workspace", ws])
        self.assertEqual(code, 0)
        self.assertIn("2 turn(s), 4 dispatches", out)

    def test_prune_removes_only_old_sessions(self):
        self.session("old", age_days=40)
        self.session("new")
        code, out, _ = capture(sentinel_report.main, ["prune", "--home", self.home, "--older-than-days", "30", "--dry-run"])
        self.assertIn("Would remove 1", out)
        self.assertTrue(os.path.isdir(os.path.join(self.home, "state", "old")))
        capture(sentinel_report.main, ["prune", "--home", self.home, "--older-than-days", "30"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.home, "state"))), ["new"])
        code, _, _ = capture(sentinel_report.main, ["prune", "--home", self.home, "--older-than-days", "-1"])
        self.assertEqual(code, 1)


class ContextBudgetStepsTests(HomeCase):
    def test_steps_digest(self):
        folder = self.session("s1")
        digest = context_budget.build_digest(context_budget.Path(folder) / "dispatch.jsonl", "steps", 2)
        self.assertEqual(digest["total_entries"], len(DISPATCH))
        rollup = digest["rollup"]
        self.assertEqual(rollup["completed_dispatches_by_agent"], {"technical-seo-subagent": 1, "seo-agent": 1})
        self.assertEqual(rollup["output_tokens_total"], 31200)
        self.assertEqual(rollup["agents_missing_contract_fields"], [])
        self.assertEqual(rollup["started_without_recorded_stop"], 0)
        self.assertLess(digest["estimated_tokens_digest"], digest["estimated_tokens_full_file"] + 200)

    def test_steps_tolerates_and_reports_a_torn_line(self):
        folder = self.session("s1")
        path = os.path.join(folder, "dispatch.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('{"ev":"stop","agent_id":"z9","to\n')  # a line torn by a concurrent writer
        write_jsonl(path, [{"ev": "start", "t": 200, "agent_id": "d1", "agent_type": "seo-agent"}])
        digest = context_budget.build_digest(context_budget.Path(path), "steps", 2)
        self.assertEqual(digest["total_entries"], len(DISPATCH) + 1)
        self.assertEqual(digest["malformed_lines_skipped"], [len(DISPATCH) + 1])
        proc = subprocess.run([sys.executable, os.path.join(LIB, "context_budget.py"), path, "--kind", "steps"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NOTE: 1 malformed (torn) line(s)", proc.stdout)
        with self.assertRaises(ValueError):  # orchestrator-written kinds stay strict
            context_budget.build_digest(context_budget.Path(path), "checkpoints", 2)

    def test_steps_cli(self):
        folder = self.session("s1")
        proc = subprocess.run([sys.executable, os.path.join(LIB, "context_budget.py"),
                               os.path.join(folder, "dispatch.jsonl"), "--kind", "steps"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("completed_dispatches_by_agent", proc.stdout)


class TriggerRegistryTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="tantra_ws_")
        self.addCleanup(shutil.rmtree, self.ws, True)
        self.runs = os.path.join(self.ws, "memory", "sentinel_runs.jsonl")
        self.ledger = os.path.join(self.ws, "memory", "triggers.jsonl")

    def cli(self, *argv):
        args = trigger_registry.build_parser().parse_args(list(argv))
        handlers = {"register": trigger_registry.cmd_register, "check": trigger_registry.cmd_check,
                    "acknowledge": trigger_registry.cmd_acknowledge}
        return capture(handlers[args.command], args)

    def register(self, tid, kind, params=None):
        argv = [self.ledger, "register", "--trigger-id", tid, "--kind", "condition", "--condition-kind", kind,
                "--target", "surface to user", "--description", "sentinel"]
        if params:
            argv += ["--params", json.dumps(params)]
        code, _, err = self.cli(*argv)
        self.assertEqual(code, 0, err)

    def check(self):
        code, out, _ = self.cli("memory/triggers.jsonl", "check", "--workspace-root", self.ws, "--alerts-log", "")
        self.assertEqual(code, 0)
        return out

    def test_workspace_root_flag_is_accepted_and_resolves_paths(self):
        self.register("stalls", "stalled_dispatch")
        write_jsonl(self.runs, [sentinel_run(iso(), stalls=[{"agent_type": "seo-agent", "agent_id": "c1"}])])
        out = self.check()
        self.assertIn("[stalls]", out)
        self.assertIn("seo-agent x1", out)

    def test_documented_cli_form_runs(self):
        self.register("stalls", "stalled_dispatch")
        proc = subprocess.run([sys.executable, os.path.join(LIB, "trigger_registry.py"), "memory/triggers.jsonl",
                               "check", "--workspace-root", self.ws, "--gates-ledger", "memory/approval_gates.jsonl",
                               "--outcomes-log", "memory/outcomes.jsonl", "--redispatch-log", "memory/redispatch_log.jsonl"],
                              capture_output=True, text=True, encoding="utf-8", cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("nothing fired", proc.stdout)

    def test_old_runs_and_acknowledged_runs_do_not_fire(self):
        self.register("stalls", "stalled_dispatch")
        write_jsonl(self.runs, [sentinel_run(iso(-30), stalls=[{"agent_type": "seo-agent"}])])
        self.assertIn("nothing fired", self.check())
        write_jsonl(self.runs, [sentinel_run(iso(-0.001), stalls=[{"agent_type": "seo-agent"}])])
        self.assertIn("[stalls]", self.check())
        self.cli(self.ledger, "acknowledge", "--trigger-id", "stalls")
        self.assertIn("nothing fired", self.check())

    def test_repeated_read_loop(self):
        self.register("loops", "repeated_read_loop", {"min_calls": 3, "min_denials": 5})
        write_jsonl(self.runs, [sentinel_run(iso(), repeated_reads=[{"desc": "Read brand.md", "calls": 2}])])
        self.assertIn("nothing fired", self.check())
        write_jsonl(self.runs, [sentinel_run(iso(), repeated_reads=[{"desc": "Read brand.md", "calls": 4}])])
        self.assertIn("Read brand.md x4", self.check())

    def test_repeated_read_loop_from_denials(self):
        self.register("loops", "repeated_read_loop")
        write_jsonl(self.runs, [sentinel_run(iso(), denials={"echo": 2})])
        self.assertIn("2 repeated call(s) denied", self.check())

    def test_token_hotspot(self):
        self.register("hot", "token_hotspot", {"min_output_tokens": 40000})
        write_jsonl(self.runs, [sentinel_run(iso(), hotspots=[{"agent_type": "seo-agent", "output_tokens": 30000}])])
        self.assertIn("nothing fired", self.check())
        write_jsonl(self.runs, [sentinel_run(iso(), hotspots=[{"agent_type": "seo-agent", "output_tokens": 55000}])])
        self.assertIn("seo-agent 55,000 output tokens", self.check())


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="tantra_ws_")
        self.addCleanup(shutil.rmtree, self.ws, True)
        os.makedirs(os.path.join(self.ws, "memory"))

    def test_without_sentinel_runs_timing_stays_not_computable(self):
        report = observability_report.build_report(observability_report.Path(self.ws), 3)
        self.assertIsNone(report["timing_and_tokens"])
        metrics = {m["metric"] for m in report["not_computable"]}
        self.assertIn("Agent latency and reliability (timing)", metrics)
        self.assertIn("Model latency and usage", metrics)

    def test_with_sentinel_runs_timing_is_computed(self):
        write_jsonl(os.path.join(self.ws, "memory", "sentinel_runs.jsonl"),
                    [sentinel_run(iso()), sentinel_run(iso(), stalls=[{"agent_type": "seo-agent"}])])
        report = observability_report.build_report(observability_report.Path(self.ws), 3)
        tt = report["timing_and_tokens"]
        self.assertEqual(tt["dispatches"], 4)
        self.assertEqual(tt["per_agent"]["seo-agent"]["p50_s"], 119)
        self.assertEqual(tt["output_tokens_by_agent"]["seo-agent"], 60000)
        self.assertEqual(tt["stalls"], 1)
        self.assertEqual(tt["contract_misses_by_agent"], {"technical-seo-subagent": 2})
        metrics = {m["metric"] for m in report["not_computable"]}
        self.assertNotIn("Agent latency and reliability (timing)", metrics)
        self.assertNotIn("Model latency and usage", metrics)
        self.assertIn("Token/model/tool cost", metrics)
        _, out, _ = capture(observability_report.print_report, report)
        self.assertIn("Timing and tokens", out)


if __name__ == "__main__":
    unittest.main()
