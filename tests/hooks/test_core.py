import json
import os
import unittest

from tests.hooks.helpers import MINI_REGISTRY, activate, make_ctx, payload, run_hook, temp_home


class ResultMergeTests(unittest.TestCase):
    def test_pretooluse_deny_beats_ask_and_carries_context(self):
        from tantra_core.result import Result, build_output

        code, out, err = build_output(
            "PreToolUse",
            [Result("a", ask="confirm?"), Result("b", deny="no", context="fact one"), Result("c", context="fact two")],
        )
        self.assertEqual(code, 0)
        self.assertIsNone(err)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertEqual(hso["permissionDecisionReason"], "no")
        self.assertIn("fact one", hso["additionalContext"])
        self.assertIn("fact two", hso["additionalContext"])

    def test_subagentstop_block_is_top_level(self):
        from tantra_core.result import Result, build_output

        _, out, _ = build_output("SubagentStop", [Result("contract", block="add GAPS")])
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "add GAPS")

    def test_rewake_uses_exit_2_and_stderr(self):
        from tantra_core.result import Result, build_output

        code, out, err = build_output("PreToolUse", [Result("pulse", rewake="stalled")])
        self.assertEqual((code, out, err), (2, None, "stalled"))

    def test_nothing_means_no_output(self):
        from tantra_core.result import build_output

        self.assertEqual(build_output("PostToolUse", []), (0, None, None))

    def test_context_is_capped(self):
        from tantra_core.result import FIELD_CAP, Result, build_output

        _, out, _ = build_output("PostToolUse", [Result("x", context="y" * 50000)])
        self.assertLessEqual(len(out["hookSpecificOutput"]["additionalContext"]), FIELD_CAP)


class ContextTests(unittest.TestCase):
    def test_task_is_normalised_to_agent(self):
        ctx = make_ctx(payload("PreToolUse", tool_name="Task", tool_input={"subagent_type": "seo-agent"}), registry=MINI_REGISTRY)
        self.assertEqual(ctx.tool_name, "Agent")

    def test_inactive_by_default_active_after_marker(self):
        home = temp_home()
        ctx = make_ctx(payload("PreToolUse"), home=home, registry=MINI_REGISTRY)
        self.assertFalse(ctx.active)
        activate(home)
        ctx2 = make_ctx(payload("PreToolUse"), home=home, registry=MINI_REGISTRY)
        self.assertTrue(ctx2.active)

    def test_running_tantra_agent_implies_active(self):
        ctx = make_ctx(payload("PreToolUse", agent_id="a1", agent_type="seo-agent"), registry=MINI_REGISTRY)
        self.assertTrue(ctx.active)
        ctx2 = make_ctx(payload("PreToolUse", agent_id="a1", agent_type="Explore"), registry=MINI_REGISTRY)
        self.assertFalse(ctx2.active)

    def test_env_forces_active(self):
        old = os.environ.get("TANTRA_ACTIVE")
        os.environ["TANTRA_ACTIVE"] = "1"
        try:
            self.assertTrue(make_ctx(payload("PreToolUse"), registry=MINI_REGISTRY).active)
        finally:
            if old is None:
                os.environ.pop("TANTRA_ACTIVE", None)
            else:
                os.environ["TANTRA_ACTIVE"] = old

    def test_user_config_overrides_module_defaults(self):
        home = temp_home()
        with open(os.path.join(home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"echo": {"deny_after": 5}}, fh)
        ctx = make_ctx(payload("PreToolUse"), home=home)
        self.assertEqual(ctx.cfg("echo", {"deny_after": 2, "x": 1}), {"deny_after": 5, "x": 1})


class DispatcherTests(unittest.TestCase):
    def test_garbage_stdin_fails_open(self):
        import subprocess
        import sys

        from tests.hooks.helpers import HOOK

        proc = subprocess.run([sys.executable, "-I", "-S", HOOK], input=b"not json", capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"")

    def test_unknown_event_is_silent(self):
        code, out, _ = run_hook(payload("Notification"))
        self.assertEqual((code, out), (0, None))

    def test_inactive_session_is_silent_for_ordinary_tools(self):
        code, out, _ = run_hook(payload("PreToolUse", tool_name="Read", tool_input={"file_path": __file__}))
        self.assertEqual((code, out), (0, None))


if __name__ == "__main__":
    unittest.main()
