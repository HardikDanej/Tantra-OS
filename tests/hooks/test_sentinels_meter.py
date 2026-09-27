"""Meter: transcript usage into the stop line, hotspot notes to the parent, session budget warnings."""
import unittest

from tests.hooks.test_sentinels_common import GOOD_OUTPUT, SentinelCase, sample_transcript


class MeterTests(SentinelCase):
    def start_stop(self, agent_id, agent_type="technical-seo-subagent", transcript=None):
        from tantra_core import sentinels

        self.write_agent_transcript(agent_id, lines=transcript)
        sentinels.handle(self.ctx("SubagentStart", agent_id=agent_id, agent_type=agent_type))
        return sentinels.handle(self.ctx("SubagentStop", agent_id=agent_id, agent_type=agent_type,
                                         last_assistant_message=GOOD_OUTPUT, stop_hook_active=False)) or []

    def returned(self, agent_id, target="technical-seo-subagent", status="completed", **fields):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PostToolUse", tool_name="Agent", tool_use_id="tu-" + agent_id,
                                         tool_input={"subagent_type": target, "prompt": "p"},
                                         tool_response={"status": status, "agentId": agent_id}, **fields)) or []

    def test_stop_line_carries_deduped_tokens_and_duration(self):
        self.start_stop("a1")
        stop = self.ledger()[-1]
        self.assertEqual(stop["tokens"], {"input": 200, "output": 800, "cache_read": 2000, "cache_creation": 0, "total": 3000})
        self.assertIsNotNone(stop["duration_s"])
        self.assertFalse(stop["over_budget"])

    def test_over_budget_note_is_delivered_to_parent_once(self):
        self.start_stop("a1", transcript=sample_transcript(output_a=15000, output_b=9000))
        self.assertTrue(self.ledger()[-1]["over_budget"])
        results = self.returned("a1")
        self.assertEqual(len(results), 1)
        text = results[0].context
        self.assertIn("Tantra Meter: technical-seo-subagent (a1) used 24,000 output tokens", text)
        self.assertIn("budget 20,000 output tokens", text)
        self.assertIn("WebFetch https://example.com/pricing (40,000 chars)", text)
        self.assertEqual(self.returned("a1"), [])

    def test_background_dispatch_note_reaches_the_parent_scope_later(self):
        self.returned("a1", status="async_launched")
        self.start_stop("a1", transcript=sample_transcript(output_a=30000))
        results = self.returned("b2", target="seo-agent")
        self.assertEqual(len(results), 1)
        self.assertIn("(a1)", results[0].context)

    def test_session_budget_warns_once_per_band(self):
        self.config(meter={"session_output_budget": 1000, "session_step": 2000})
        first = [r.system_message for r in self.start_stop("a1") if r.system_message]
        self.assertEqual(first, [])
        second = [r.system_message for r in self.start_stop("a2") if r.system_message]
        self.assertEqual(len(second), 1)
        self.assertIn("1,600 output tokens", second[0])
        third = [r.system_message for r in self.start_stop("a3") if r.system_message]
        self.assertEqual(third, [])
        fourth = [r.system_message for r in self.start_stop("a4") if r.system_message]
        self.assertEqual(len(fourth), 1)

    def test_missing_transcript_is_tolerated(self):
        from tantra_core import sentinels

        sentinels.handle(self.ctx("SubagentStart", agent_id="z", agent_type="seo-agent"))
        sentinels.handle(self.ctx("SubagentStop", agent_id="z", agent_type="seo-agent",
                                  last_assistant_message=GOOD_OUTPUT + "CITATION_CHECK: pass\n"))
        stop = self.ledger()[-1]
        self.assertIsNone(stop["tokens"])
        self.assertFalse(stop["over_budget"])


if __name__ == "__main__":
    unittest.main()
