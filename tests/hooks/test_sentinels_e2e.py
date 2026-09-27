"""End-to-end: the real dispatcher (python -I -S tantra_hook.py) with sentinels, as Claude Code runs it."""
import json
import os
import shutil
import tempfile
import time
import unittest

from tests.hooks.helpers import payload, run_hook, temp_home
from tests.hooks.test_sentinels_common import GOOD_OUTPUT, REGISTRY


class EndToEndTests(unittest.TestCase):
    session = "sess-e2e"

    def setUp(self):
        self.home = temp_home()
        self.dir = tempfile.mkdtemp(prefix="tantra_e2e_")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.registry = os.path.join(self.dir, "registry.json")
        with open(self.registry, "w", encoding="utf-8") as fh:
            json.dump(REGISTRY, fh)
        self.env = {"TANTRA_ACTIVE": "1", "TANTRA_REGISTRY": self.registry}

    def tearDown(self):
        log = os.path.join(self.home, "logs", "hook_errors.log")
        if os.path.exists(log):
            with open(log, encoding="utf-8") as fh:
                self.fail("hook logged an error (fail-open hid it):\n" + fh.read())

    def hook(self, event, mode="", **fields):
        fields.setdefault("cwd", self.dir)
        return run_hook(payload(event, session_id=self.session, **fields), mode=mode, home=self.home, env=self.env)

    def config(self, **sections):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump(sections, fh)

    def test_contract_block_on_subagent_stop(self):
        code, out, _ = self.hook("SubagentStop", agent_id="a1", agent_type="technical-seo-subagent",
                                 last_assistant_message="Analysis " * 60, stop_hook_active=False)
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("missing CONFIDENCE, GAPS", out["reason"])

    def test_handback_report_is_not_blocked(self):
        self.hook("PostToolUse", tool_name="SubagentHandback", agent_id="a1", agent_type="technical-seo-subagent",
                  tool_input={"message": GOOD_OUTPUT})
        code, out, _ = self.hook("SubagentStop", agent_id="a1", agent_type="technical-seo-subagent",
                                 last_assistant_message="Handed back the report to the parent.", stop_hook_active=False)
        self.assertEqual(code, 0)
        self.assertIsNone(out)

    def test_lens_denies_full_kb_read(self):
        kb = os.path.join(self.dir, "knowledge-bases", "seo-knowledge-base.md")
        os.makedirs(os.path.dirname(kb))
        with open(kb, "w", encoding="utf-8") as fh:
            fh.write("# SEO\n" + "word " * 6000)
        code, out, _ = self.hook("PreToolUse", tool_name="Read", tool_input={"file_path": kb})
        self.assertEqual(code, 0)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("kb_slice.py", hso["permissionDecisionReason"])

    def test_echo_denies_third_identical_read(self):
        target = os.path.join(self.dir, "brand.md")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("brand voice\n" * 100)
        read = {"file_path": target}
        decisions = []
        for _ in range(3):
            _, out, _ = self.hook("PreToolUse", tool_name="Read", tool_input=read)
            decisions.append(((out or {}).get("hookSpecificOutput") or {}).get("permissionDecision"))
            self.hook("PostToolUse", tool_name="Read", tool_input=read,
                      tool_response={"type": "text", "file": {"content": "brand voice\n" * 100}})
        self.assertEqual(decisions, [None, None, "deny"])

    def test_run_brief_on_second_subagent_start(self):
        launch = {"subagent_type": "technical-seo-subagent", "prompt": "Audit example.com crawl errors"}
        self.hook("PreToolUse", tool_name="Agent", tool_use_id="tu-1", tool_input=launch)
        _, first, _ = self.hook("SubagentStart", agent_id="a1", agent_type="technical-seo-subagent")
        self.assertIsNone(first)
        self.hook("SubagentStop", agent_id="a1", agent_type="technical-seo-subagent",
                  last_assistant_message=GOOD_OUTPUT, stop_hook_active=False)
        self.hook("PreToolUse", tool_name="Agent", tool_use_id="tu-2", tool_input=launch)
        _, second, _ = self.hook("SubagentStart", agent_id="a2", agent_type="technical-seo-subagent")
        ctx = second["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(second["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertIn("Tantra Run Brief: this dispatch re-runs an earlier technical-seo-subagent run", ctx)
        self.assertIn("crawl errors", ctx)

    def test_pulse_stall_rewakes_within_seconds(self):
        from tantra_core import state

        self.config(pulse={"poll_s": 1, "idle_min": 0.02})
        state.append_jsonl(os.path.join(self.home, "state", self.session, "dispatch.jsonl"),
                           {"ev": "start", "t": time.time(), "agent_id": "a1",
                            "agent_type": "technical-seo-subagent", "tier": "sub"})
        began = time.time()
        code, out, err = self.hook("PreToolUse", mode="watchdog", tool_name="Agent", tool_use_id="tu-1",
                                   tool_input={"subagent_type": "technical-seo-subagent", "prompt": "audit"})
        self.assertLess(time.time() - began, 10)
        self.assertEqual(code, 2)
        self.assertIsNone(out)
        self.assertIn("Tantra Pulse stall report", err)

    def test_inactive_session_is_silent(self):
        env = {"TANTRA_REGISTRY": self.registry}
        code, out, _ = run_hook(payload("SubagentStop", session_id="cold", agent_id="x", agent_type="Explore",
                                        last_assistant_message="short"), home=self.home, env=env)
        self.assertEqual((code, out), (0, None))


if __name__ == "__main__":
    unittest.main()
