"""Scribe: step ledger, Run Brief, depth note, compaction brief, workspace run summary."""
import json
import os
import shutil
import tempfile
import unittest

from tests.hooks.test_sentinels_common import GOOD_OUTPUT, SentinelCase


class ScribeTests(SentinelCase):
    def launch(self, prompt, tool_use_id, agent_type="technical-seo-subagent", **extra):
        """The parent's PreToolUse(Agent): the only event that sees the task's prompt."""
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", tool_use_id=tool_use_id,
                                         tool_input={"subagent_type": agent_type, "prompt": prompt}, **extra))

    def start(self, agent_id, agent_type="technical-seo-subagent"):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("SubagentStart", agent_id=agent_id, agent_type=agent_type)) or []

    def stop(self, agent_id, message=GOOD_OUTPUT, agent_type="technical-seo-subagent", **extra):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("SubagentStop", agent_id=agent_id, agent_type=agent_type,
                                         last_assistant_message=message, stop_hook_active=False, **extra))

    def test_start_and_stop_write_one_ledger_line_each_and_save_output(self):
        self.write_agent_transcript("a1")
        self.assertEqual(self.start("a1"), [])
        self.stop("a1")
        rows = self.ledger()
        self.assertEqual([r["ev"] for r in rows], ["start", "stop"])
        stop = rows[1]
        self.assertEqual(stop["tier"], "sub")
        self.assertTrue(stop["contract_ok"])
        self.assertEqual(stop["tokens"]["output"], 800)
        self.assertEqual(stop["output_chars"], len(GOOD_OUTPUT))
        with open(stop["output_path"], encoding="utf-8") as fh:
            self.assertEqual(fh.read(), GOOD_OUTPUT)

    def test_non_tantra_agents_are_ignored(self):
        from tantra_core import sentinels

        self.assertIsNone(sentinels.handle(self.ctx("SubagentStart", agent_id="x", agent_type="Explore")) or None)
        self.assertEqual(self.ledger(), [])

    def test_output_is_capped(self):
        self.start("a1")
        self.stop("a1", message=GOOD_OUTPUT + "z" * 30000)
        with open(self.ledger()[-1]["output_path"], encoding="utf-8") as fh:
            self.assertEqual(len(fh.read()), 20000)

    def test_run_brief_on_redispatch(self):
        self.launch("Audit example.com canonicals", "tu-1")
        self.start("a1")
        self.stop("a1", message="HEAD-MARK " + "detail " * 2000 + GOOD_OUTPUT + "TAIL-MARK")
        self.launch("Audit  example.com CANONICALS", "tu-2")
        results = self.start("a2")
        self.assertEqual(len(results), 1)
        text = results[0].context
        self.assertIn("Tantra Run Brief: this dispatch re-runs an earlier technical-seo-subagent run in this "
                      "session (matched by identical dispatch prompt", text)
        self.assertIn("HEAD-MARK", text)
        self.assertIn("TAIL-MARK", text)
        self.assertIn("Missing contract fields last time: none", text)
        self.assertLess(len(text), 4400)
        brief = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "run_brief"][0]
        self.assertGreater(brief["est_tokens_avoided"], 0)

    def test_run_brief_reports_missing_fields(self):
        self.config(contract={"mode": "observe"})
        self.launch("Audit example.com", "tu-1")
        self.start("a1")
        self.stop("a1", message="x" * 400)
        self.launch("Audit example.com", "tu-2")
        text = self.start("a2")[0].context
        self.assertIn("Missing contract fields last time: CONFIDENCE, GAPS", text)

    def test_run_brief_respects_mode_off(self):
        self.config(scribe={"mode": "off"})
        self.launch("Audit example.com", "tu-1")
        self.start("a1")
        self.stop("a1")
        self.launch("Audit example.com", "tu-2")
        self.assertEqual(self.start("a2"), [])
        self.assertEqual([r["ev"] for r in self.ledger()], ["launch", "start", "stop", "launch", "start"])

    # -- regression: the Run Brief must only reach a re-dispatch of the same task --
    def brief_rows(self):
        return [r for r in self.ledger("sentinel.jsonl") if r["action"] == "run_brief"]

    def test_no_run_brief_for_a_different_task_of_the_same_agent_type(self):
        self.launch("Audit competitor ACME.com canonicals", "tu-1")
        self.start("p1")
        self.stop("p1", message="ACME findings " * 200 + GOOD_OUTPUT)
        self.launch("Audit competitor BETA.io canonicals", "tu-2")
        self.assertEqual(self.start("p2"), [])
        self.assertEqual(self.brief_rows(), [], "no brief, and no saving booked")
        start = [r for r in self.ledger() if r["ev"] == "start"][-1]
        self.assertEqual((start["tool_use_id"], start["pair"], start["parent_agent_id"]), ("tu-2", "unique", "main"))

    def test_no_run_brief_for_parallel_fan_out_siblings(self):
        self.launch("Audit ACME.com", "tu-1")
        self.start("p1")
        self.stop("p1", message="ACME findings " * 200 + GOOD_OUTPUT)
        for i in range(3):  # three dispatches issued together
            self.launch("Audit ACME.com", f"tu-f{i}")
        for i in range(3):
            self.assertEqual(self.start(f"f{i}"), [], "pairing is ambiguous, so no other run's output is injected")
        self.assertEqual(self.brief_rows(), [])

    def test_run_brief_on_redispatch_marker_with_revised_prompt(self):
        self.launch('{"agent": "technical-seo-subagent", "objective": "audit", "redispatch": null}', "tu-1")
        self.start("r1")
        self.stop("r1", message="FIRST-ATTEMPT " * 50 + GOOD_OUTPUT)
        self.launch('{"agent": "technical-seo-subagent", "objective": "audit, fix hreflang", '
                    '"redispatch": {"cycle_id": "seo_eeat:a-42", "attempt": 2, "of": 2}}', "tu-2")
        results = self.start("r2")
        self.assertEqual(len(results), 1)
        self.assertIn("matched by re-dispatch cycle seo_eeat:a-42", results[0].context)
        self.assertIn("FIRST-ATTEMPT", results[0].context)
        self.assertEqual(self.brief_rows()[0]["basis"], "re-dispatch cycle seo_eeat:a-42 (first attempt)")

    def test_redispatch_marker_with_several_unrelated_prior_runs_gets_no_brief(self):
        for i, target in enumerate(("ACME", "BETA")):
            self.launch(f"Audit {target}", f"tu-{i}")
            self.start(f"q{i}")
            self.stop(f"q{i}")
        self.launch('Audit ACME again "redispatch": {"cycle_id": "c1", "attempt": 2}', "tu-9")
        self.assertEqual(self.start("q9"), [])

    def test_resumed_subagent_does_not_consume_a_pending_launch(self):
        self.launch("Audit ACME", "tu-1")
        self.start("a1")
        self.launch("Audit BETA", "tu-2")
        self.start("a1")  # SubagentStart again for a resumed a1, while tu-2 is still pending
        self.start("a2")
        starts = [r for r in self.ledger() if r["ev"] == "start"]
        self.assertNotIn("tool_use_id", starts[1])
        self.assertEqual(starts[2]["tool_use_id"], "tu-2")

    # -- regression: SubagentHandback (auto mode) carries the report --------------
    def handback(self, agent_id, message, agent_type="technical-seo-subagent"):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PostToolUse", tool_name="SubagentHandback", agent_id=agent_id,
                                         agent_type=agent_type, tool_input={"message": message}))

    def test_handback_report_is_saved_instead_of_the_closing_text(self):
        self.start("h1")
        self.handback("h1", GOOD_OUTPUT)
        self.assertIsNone(self.stop("h1", message="Handed back the report to the parent.") or None)
        stop = self.ledger()[-1]
        self.assertTrue(stop["contract_ok"])
        self.assertTrue(stop["handback"])
        with open(stop["output_path"], encoding="utf-8") as fh:
            self.assertTrue(fh.read().startswith(GOOD_OUTPUT.strip()))
        self.assertFalse(os.path.exists(os.path.join(self.home, "state", self.session, "handbacks", "h1.txt")),
                         "consumed at the stop, so a later resume cannot reuse it")

    # -- regression: a subagent's compaction resets its own read history ----------
    def test_subagent_compaction_writes_a_marker_for_its_scope(self):
        from tantra_core import sentinels

        self.assertIsNone(sentinels.handle(self.ctx("SessionStart", source="compact", agent_id="sub1",
                                                    agent_type="technical-seo-subagent")) or None)
        marks = [r for r in self.ledger("reads.jsonl") if r["kind"] == "compact"]
        self.assertEqual([m["scope"] for m in marks], ["sub1"])

    def test_depth_note_at_spawn_depth_three(self):
        self.write_agent_transcript("d1", meta={"agentType": "seo-agent", "spawnDepth": 3})
        results = self.start("d1", agent_type="seo-agent")
        self.assertEqual(len(results), 1)
        self.assertIn("spawn depth 3", results[0].context)
        self.assertIn("return", results[0].context.lower())

    def test_no_depth_note_below_limit_or_without_meta(self):
        self.write_agent_transcript("d1", meta={"spawnDepth": 2})
        self.assertEqual(self.start("d1", agent_type="seo-agent"), [])
        self.assertEqual(self.start("d2", agent_type="seo-agent"), [])

    def test_parent_side_returned_line(self):
        from tantra_core import sentinels

        sentinels.handle(self.ctx(
            "PostToolUse", tool_name="Agent", tool_use_id="tu-9",
            tool_input={"subagent_type": "seo-agent", "prompt": "Audit  the SITE", "description": "audit"},
            tool_response={"status": "completed", "agentId": "a1", "totalDurationMs": 5000, "totalToolUseCount": 7},
        ))
        row = self.ledger()[0]
        self.assertEqual(row["ev"], "returned")
        self.assertEqual((row["tool_use_id"], row["status"], row["agent_id"], row["parent"]), ("tu-9", "completed", "a1", "main"))
        self.assertEqual(row["total_duration_ms"], 5000)


class CompactionAndSummaryTests(SentinelCase):
    def setUp(self):
        super().setUp()
        self.ws = tempfile.mkdtemp(prefix="tantra_ws_")
        self.addCleanup(shutil.rmtree, self.ws, True)
        os.makedirs(os.path.join(self.ws, "memory"))
        with open(os.path.join(self.ws, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write("# client\n")
        with open(os.path.join(self.ws, "memory", "latest.json"), "w", encoding="utf-8") as fh:
            json.dump({"pending_approval_gates": [{"gate_id": "g-7", "stakes_class": "high", "summary": "Publish press release"}]}, fh)
        with open(os.path.join(self.ws, "memory", "checkpoints.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"timestamp": "2026-09-24", "request_summary": "Q4 SEO plan", "dispatched_to": ["seo-agent"]}) + "\n")

    def run_one_dispatch(self):
        from tantra_core import sentinels

        sentinels.handle(self.ctx("SubagentStart", agent_id="a1", agent_type="seo-agent", cwd=self.ws))
        sentinels.handle(self.ctx("SubagentStop", agent_id="a1", agent_type="seo-agent", cwd=self.ws,
                                  last_assistant_message=GOOD_OUTPUT + "CITATION_CHECK: pass\n"))

    def test_compaction_brief_lists_dispatches_gates_and_checkpoint(self):
        from tantra_core import sentinels

        self.run_one_dispatch()
        sentinels.handle(self.ctx("SubagentStart", agent_id="b9", agent_type="technical-seo-subagent", cwd=self.ws))
        results = sentinels.handle(self.ctx("SessionStart", source="compact", cwd=self.ws))
        text = results[0].context
        self.assertIn("Tantra session state after compact", text)
        self.assertIn("seo-agent (a1)", text)
        self.assertIn("technical-seo-subagent (b9): started", text)
        self.assertIn("g-7 (high): Publish press release", text)
        self.assertIn("Q4 SEO plan", text)
        self.assertIn("seo-agent (1)", text)
        self.assertLessEqual(len(text), 3000)
        self.assertEqual(self.ledger("reads.jsonl")[-1]["kind"], "compact")

    def test_startup_source_is_ignored(self):
        from tantra_core import sentinels

        self.run_one_dispatch()
        self.assertIsNone(sentinels.handle(self.ctx("SessionStart", source="startup", cwd=self.ws)))

    def test_stop_appends_one_summary_per_new_activity(self):
        from tantra_core import sentinels

        self.run_one_dispatch()
        sentinels.handle(self.ctx("Stop", cwd=self.ws))
        sentinels.handle(self.ctx("Stop", cwd=self.ws))
        from tantra_core import state

        runs = state.read_jsonl(os.path.join(self.ws, "memory", "sentinel_runs.jsonl"))
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["dispatches"], 1)
        self.assertEqual(runs[0]["by_tier"], {"domain": 1})
        self.assertEqual(runs[0]["dispatch_list"][0]["agent_type"], "seo-agent")

    def test_stop_outside_workspace_writes_nothing(self):
        from tantra_core import sentinels

        self.run_one_dispatch()
        sentinels.handle(self.ctx("Stop", cwd=self.proj))
        self.assertFalse(os.path.exists(os.path.join(self.proj, "memory", "sentinel_runs.jsonl")))


if __name__ == "__main__":
    unittest.main()
