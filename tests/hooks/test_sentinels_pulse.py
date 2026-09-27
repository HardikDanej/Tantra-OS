"""Pulse: the asyncRewake stall watchdog (unit tests use a fake clock; no real waiting)."""
import os
import time
import unittest

from tests.hooks.test_sentinels_common import SentinelCase


class FakeTime:
    def __init__(self):
        self.now = time.time()
        self.sleeps = 0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds


class PulseTests(SentinelCase):
    def setUp(self):
        super().setUp()
        self.fake = FakeTime()

    def watchdog_ctx(self, tool_use_id="tu-1", target="technical-seo-subagent"):
        return self.ctx("PreToolUse", mode="watchdog", tool_name="Agent", tool_use_id=tool_use_id,
                        tool_input={"subagent_type": target, "prompt": "audit"})

    def add(self, row, name="dispatch.jsonl"):
        from tantra_core import state

        row.setdefault("t", self.fake.now)
        state.append_jsonl(os.path.join(self.home, "state", self.session, name), row)

    def watch(self, ctx):
        from tantra_core.sentinels import pulse

        return pulse.watch(ctx, clock=self.fake.clock, sleep=self.fake.sleep)

    def test_non_tantra_target_exits_immediately(self):
        self.assertIsNone(self.watch(self.watchdog_ctx(target="Explore")))
        self.assertEqual(self.fake.sleeps, 0)

    def test_idle_child_is_reported_once_with_last_activity(self):
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent", "tier": "sub"})
        self.write_agent_transcript("a1")
        result = self.watch(self.watchdog_ctx())
        report = result.rewake
        self.assertIn("Tantra Pulse stall report: the dispatch of technical-seo-subagent (tier sub, agent id a1", report)
        self.assertIn("no transcript activity for 6 min", report)
        self.assertIn("Last recorded activity: Grep canonical.", report)
        self.assertIn("Read x1", report)
        self.assertIn("re-dispatch only the unfinished part, synchronously", report)
        self.assertLessEqual(len(report), 2000)
        stall = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "stall"][0]
        self.assertEqual((stall["stalled_agent_id"], stall["reason"], stall["est_tokens_avoided"]), ("a1", "idle", 0))

    def test_async_launched_return_does_not_end_the_watch(self):
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        self.add({"ev": "returned", "tool_use_id": "tu-1", "status": "async_launched", "agent_id": "a1"})
        self.assertIsNotNone(self.watch(self.watchdog_ctx()))

    def test_completed_return_or_stop_ends_the_watch(self):
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        self.add({"ev": "returned", "tool_use_id": "tu-1", "status": "completed", "agent_id": "a1"})
        self.assertIsNone(self.watch(self.watchdog_ctx()))
        self.add({"ev": "start", "agent_id": "b1", "agent_type": "technical-seo-subagent"})
        self.add({"ev": "stop", "agent_id": "b1", "agent_type": "technical-seo-subagent"})
        self.assertIsNone(self.watch(self.watchdog_ctx(tool_use_id="tu-2")))

    def test_parallel_watchdogs_claim_different_children(self):
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        self.add({"ev": "start", "agent_id": "a2", "agent_type": "technical-seo-subagent"})
        began = self.fake.now
        first = self.watch(self.watchdog_ctx("tu-1"))
        self.fake.now = began
        second = self.watch(self.watchdog_ctx("tu-2"))
        self.assertIn("agent id a1", first.rewake)
        self.assertIn("agent id a2", second.rewake)

    def test_max_duration_with_live_heartbeat(self):
        self.config(pulse={"idle_min": 100, "max_min": {"sub": 1}})
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        result = self.watch(self.watchdog_ctx())
        self.assertIn("running for 1 min", result.rewake)

    def test_no_start_gives_up_quietly(self):
        self.assertIsNone(self.watch(self.watchdog_ctx()))
        self.assertLess(self.fake.now - time.time(), 400)

    def test_observe_mode_logs_without_rewake(self):
        self.config(pulse={"mode": "observe"})
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        self.assertIsNone(self.watch(self.watchdog_ctx()))
        self.assertEqual(self.ledger("sentinel.jsonl")[-1]["applied"], False)

    def test_always_returns_before_deadline(self):
        self.config(pulse={"idle_min": 1000, "max_min": 1000, "poll_s": 60})
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent"})
        started = self.fake.now
        self.assertIsNone(self.watch(self.watchdog_ctx()))
        self.assertLess(self.fake.now - started, 3500)

    # -- regression: matching the right child among same-type siblings -------------
    def test_returned_agent_id_overrides_an_earlier_guess(self):
        from tantra_core.sentinels import pulse

        target = "technical-seo-subagent"
        self.add({"ev": "start", "agent_id": "aY", "agent_type": target})
        self.add({"ev": "start", "agent_id": "aX", "agent_type": target})
        ctx = self.watchdog_ctx("tu-X")
        ws = {"agent_id": None, "start_t": None, "sure": False}
        began = self.fake.now
        # first poll, before any returned line exists: a guess, and the wrong one
        self.assertIsNone(pulse._tick(ctx, pulse.DEFAULTS, target, "sub", {"idle": 60, "max": 1200},
                                      began, began, ws))
        self.assertEqual(ws["agent_id"], "aY")
        self.add({"ev": "returned", "tool_use_id": "tu-X", "status": "async_launched", "agent_id": "aX"})
        self.add({"ev": "returned", "tool_use_id": "tu-Y", "status": "async_launched", "agent_id": "aY"})
        self.add({"ev": "stop", "agent_id": "aY", "agent_type": target})
        verdict = pulse._tick(ctx, pulse.DEFAULTS, target, "sub", {"idle": 60, "max": 1200}, began, began + 600, ws)
        self.assertNotEqual(verdict, "done", "the sibling finishing must not end this watch")
        self.assertEqual(ws["agent_id"], "aX")
        self.assertIn("agent id aX", verdict.rewake)
        self.assertEqual(pulse._owner(ctx, "aX"), "tu-X")

    def test_guess_is_released_when_a_sure_claim_takes_the_child(self):
        from tantra_core.sentinels import pulse

        target = "technical-seo-subagent"
        self.add({"ev": "start", "agent_id": "aX", "agent_type": target})
        self.add({"ev": "start", "agent_id": "aY", "agent_type": target})
        began = self.fake.now
        ctx_y = self.watchdog_ctx("tu-Y")
        ws_y = {"agent_id": None, "start_t": None, "sure": False}
        limits = {"idle": 60, "max": 1200}
        pulse._tick(ctx_y, pulse.DEFAULTS, target, "sub", limits, began, began, ws_y)
        self.assertEqual(ws_y["agent_id"], "aX")  # wrong guess
        pulse._adopt(self.watchdog_ctx("tu-X"), {"agent_id": None, "start_t": None}, "aX")  # tu-X learns aX for certain
        pulse._tick(ctx_y, pulse.DEFAULTS, target, "sub", limits, began, began + 1, ws_y)
        self.assertEqual(ws_y["agent_id"], "aY")

    def test_unique_launch_pairing_picks_this_dispatchs_child(self):
        target = "technical-seo-subagent"
        self.add({"ev": "start", "agent_id": "b1", "agent_type": target, "tool_use_id": "tu-1", "pair": "unique"})
        self.add({"ev": "start", "agent_id": "b2", "agent_type": target, "tool_use_id": "tu-2", "pair": "unique"})
        result = self.watch(self.watchdog_ctx("tu-2"))
        self.assertIn("agent id b2", result.rewake)

    # -- regression: a parent waiting on work is not idle --------------------------
    def test_parent_with_an_active_descendant_is_not_idle(self):
        from tests.hooks.test_sentinels_common import tool_result_line, usage_line, tool_use

        # seo-agent launched its child in the background (the Agent call already has a result),
        # then waits; only the child's transcript moves
        parent = self.write_agent_transcript("d1", lines=[
            usage_line("m1", 10, content=[tool_use("t1", "Agent", {"subagent_type": "technical-seo-subagent"})]),
            tool_result_line("t1", 50),
        ])
        os.utime(parent, (self.fake.now, self.fake.now))
        self.add({"ev": "start", "agent_id": "d1", "agent_type": "seo-agent", "tier": "domain"})
        self.add({"ev": "start", "agent_id": "c1", "agent_type": "technical-seo-subagent", "tier": "sub",
                  "parent_agent_id": "d1"})
        child = self.write_agent_transcript("c1")
        fake = self.fake

        def sleep(seconds):
            fake.sleep(seconds)
            os.utime(child, (fake.now, fake.now))

        from tantra_core.sentinels import pulse

        ctx = self.ctx("PreToolUse", mode="watchdog", tool_name="Agent", tool_use_id="tu-D",
                       tool_input={"subagent_type": "seo-agent", "prompt": "audit"})
        result = pulse.watch(ctx, clock=fake.clock, sleep=sleep)
        self.assertNotIn("no transcript activity", result.rewake)
        self.assertIn("running for 35 min", result.rewake)

    def test_silence_inside_an_unfinished_tool_call_is_not_idle(self):
        from tests.hooks.test_sentinels_common import usage_line, tool_use

        path = self.write_agent_transcript("a1", lines=[
            usage_line("m1", 10, content=[tool_use("t1", "Bash", {"command": "python render_report.py"})]),
        ])
        os.utime(path, (self.fake.now, self.fake.now))
        self.add({"ev": "start", "agent_id": "a1", "agent_type": "technical-seo-subagent", "tier": "sub"})
        result = self.watch(self.watchdog_ctx())
        self.assertIn("running for 20 min", result.rewake)
        self.assertIn("Last recorded activity: Bash python render_report.py.", result.rewake)


if __name__ == "__main__":
    unittest.main()
