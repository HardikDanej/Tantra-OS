"""Lens (full reads of KBs / raw state logs) and Boundary (chain of command)."""
import os
import shutil
import tempfile
import unittest

from tests.hooks.test_sentinels_common import SentinelCase


class LensTests(SentinelCase):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp(prefix="tantra_lens_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.kb = self.write("knowledge-bases/seo-knowledge-base.md", "# SEO\n" + "text " * 5000)
        self.small_kb = self.write("knowledge-bases/tiny.md", "# tiny\n")
        self.outcomes = self.write("memory/outcomes.jsonl", '{"implications": "x"}\n' * 2000)
        self.small_state = self.write("memory/checkpoints.jsonl", '{"a": 1}\n')

    def write(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def pre(self, **tool_input):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PreToolUse", tool_name="Read", tool_input=tool_input, cwd=self.dir)) or []

    def test_full_kb_read_is_denied_with_slice_commands(self):
        deny = self.pre(file_path=self.kb)[0].deny
        self.assertIn("kb_slice.py", deny)
        self.assertIn('" outline', deny)
        self.assertIn('search "<term>"', deny)
        self.assertIn('section "<heading>"', deny)
        self.assertIn("20-27k tokens", deny)
        row = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "lens_deny"][0]
        self.assertEqual(row["est_tokens_avoided"], os.path.getsize(self.kb) // 4)

    def test_narrow_or_small_reads_pass(self):
        self.assertEqual(self.pre(file_path=self.kb, offset=1, limit=120), [])
        self.assertEqual(self.pre(file_path=self.kb, limit=400), [])
        self.assertEqual(self.pre(file_path=self.small_kb), [])
        self.assertEqual(self.pre(file_path=self.small_state), [])

    def test_large_limit_counts_as_full(self):
        self.assertTrue(self.pre(file_path=self.kb, offset=1, limit=2000)[0].deny)

    def test_relative_path_resolves_against_cwd(self):
        self.assertTrue(self.pre(file_path="knowledge-bases/seo-knowledge-base.md")[0].deny)

    def test_raw_state_log_is_denied_with_digest_command(self):
        deny = self.pre(file_path=self.outcomes)[0].deny
        self.assertIn("context_budget.py", deny)
        self.assertIn("--kind outcomes", deny)

    def test_session_step_ledger_uses_steps_kind(self):
        ledger = os.path.join(self.home, "state", "other-session", "dispatch.jsonl")
        os.makedirs(os.path.dirname(ledger))
        with open(ledger, "w", encoding="utf-8") as fh:
            fh.write('{"ev": "start"}\n' * 2000)
        self.assertIn("--kind steps", self.pre(file_path=ledger)[0].deny)

    def test_assist_mode_notes_instead(self):
        self.config(lens={"mode": "assist"})
        from tantra_core import sentinels

        results = sentinels.handle(self.ctx("PreToolUse", tool_name="Read", tool_input={"file_path": self.kb}, cwd=self.dir))
        self.assertTrue(all(r.deny is None for r in results))
        self.assertTrue(any("kb_slice.py" in (r.context or "") for r in results))


class BoundaryTests(SentinelCase):
    def dispatch(self, caller, caller_id, target):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", agent_id=caller_id, agent_type=caller,
                                         tool_input={"subagent_type": target, "prompt": "go"})) or []

    def test_registered_child_is_silent(self):
        self.assertEqual(self.dispatch("seo-agent", "s1", "technical-seo-subagent"), [])

    def test_out_of_hierarchy_dispatch_gets_a_note(self):
        results = self.dispatch("seo-agent", "s1", "brand-voice-subagent")
        text = results[0].context
        self.assertIn("Tantra hierarchy note: seo-agent is dispatching brand-voice-subagent", text)
        self.assertIn("routes this through brand-strategy-agent", text)
        self.assertIsNone(results[0].deny)

    def test_enforce_denies(self):
        self.config(boundary={"mode": "enforce"})
        self.assertIn("brand-strategy-agent", self.dispatch("seo-agent", "s1", "brand-voice-subagent")[0].deny)

    def test_main_thread_and_non_tantra_are_out_of_scope(self):
        from tantra_core import sentinels

        self.assertIsNone(sentinels.handle(self.ctx("PreToolUse", tool_name="Agent",
                                                    tool_input={"subagent_type": "brand-voice-subagent", "prompt": "go"})))
        self.assertEqual(self.dispatch("Explore", "e1", "brand-voice-subagent"), [])
        self.assertEqual(self.dispatch("seo-agent", "s1", "general-purpose"), [])


if __name__ == "__main__":
    unittest.main()
