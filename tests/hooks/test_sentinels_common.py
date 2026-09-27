"""Fixtures shared by the sentinel tests, plus unit tests for sentinels/common.py."""
import copy
import json
import os
import shutil
import tempfile
import unittest

from tests.hooks.helpers import MINI_REGISTRY, make_ctx, payload, temp_home

REGISTRY = copy.deepcopy(MINI_REGISTRY)
REGISTRY["agents"]["chief-marketing-orchestrator"]["children"] = ["seo-agent", "cross-system-dispatch-bridge"]
REGISTRY["agents"]["seo-agent"]["children"] = ["technical-seo-subagent"]
REGISTRY["agents"]["seo-agent"]["has_agent_tool"] = True
REGISTRY["agents"]["technical-seo-subagent"]["children"] = []
REGISTRY["agents"]["technical-seo-subagent"]["has_agent_tool"] = False
REGISTRY["agents"]["brand-voice-subagent"] = {
    "tier": "sub", "parents": ["brand-strategy-agent"], "children": [], "contract_fields": ["CONFIDENCE", "GAPS"],
}
REGISTRY["agents"]["brand-strategy-agent"] = {
    "tier": "domain", "parents": ["brand-creative-orchestrator"], "children": ["brand-voice-subagent"],
    "contract_fields": ["CONFIDENCE", "GAPS"], "has_agent_tool": True,
}

GOOD_OUTPUT = (
    "Findings: the site has 14 crawl errors concentrated in /blog, canonical tags conflict on 3 templates, "
    "and the sitemap omits 22 indexable URLs. Recommended fixes are ordered by traffic impact below.\n"
    "CONFIDENCE: high -- verified against the crawl export\n"
    "GAPS: no Search Console access, so impressions were not checked\n"
)


def _restore_env(name, value):
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class SentinelCase(unittest.TestCase):
    """Temp TANTRA_HOME + temp project transcript folder, cleaned up after each test."""

    session = "sess-sentinel"

    def setUp(self):
        self.home = temp_home()
        # ctx.log_error writes under $TANTRA_HOME, not ctx.home: pin it so errors stay in the temp home.
        previous = os.environ.get("TANTRA_HOME")
        os.environ["TANTRA_HOME"] = self.home
        self.addCleanup(_restore_env, "TANTRA_HOME", previous)
        self.proj = tempfile.mkdtemp(prefix="tantra_proj_")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(shutil.rmtree, self.proj, True)
        self.transcript = os.path.join(self.proj, self.session + ".jsonl")
        with open(self.transcript, "w", encoding="utf-8") as fh:
            fh.write("")
        self.subagents = os.path.join(self.proj, self.session, "subagents")
        os.makedirs(self.subagents)

    def tearDown(self):
        log = os.path.join(self.home, "logs", "hook_errors.log")
        if os.path.exists(log):
            with open(log, encoding="utf-8") as fh:
                self.fail("a sentinel raised (the router's fail-open hid it):\n" + fh.read())

    def ctx(self, event, mode="", **fields):
        fields.setdefault("transcript_path", self.transcript)
        ctx = make_ctx(payload(event, session_id=self.session, **fields), home=self.home,
                       registry=REGISTRY, mode=mode)
        ctx.active = True
        return ctx

    def config(self, **sections):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump(sections, fh)

    def ledger(self, name="dispatch.jsonl"):
        from tantra_core import state
        return state.read_jsonl(os.path.join(self.home, "state", self.session, name))

    def sentinel_actions(self):
        return [r.get("action") for r in self.ledger("sentinel.jsonl")]

    def write_agent_transcript(self, agent_id, lines=None, meta=None):
        path = os.path.join(self.subagents, f"agent-{agent_id}.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for line in lines if lines is not None else sample_transcript():
                fh.write(json.dumps(line) + "\n")
        if meta is not None:
            with open(os.path.join(self.subagents, f"agent-{agent_id}.meta.json"), "w", encoding="utf-8") as fh:
                json.dump(meta, fh)
        return path


def usage_line(msg_id, output, inp=100, cache_read=1000, cache_creation=0, ts="2026-09-25T10:00:00.000Z", content=None):
    return {
        "type": "assistant", "timestamp": ts,
        "message": {"id": msg_id, "role": "assistant", "content": content or [],
                    "usage": {"input_tokens": inp, "output_tokens": output,
                              "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": cache_creation}},
    }


def tool_use(tool_id, name, tool_input):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def tool_result_line(tool_id, chars, ts="2026-09-25T10:01:00.000Z"):
    return {"type": "user", "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": "x" * chars}]}}


def sample_transcript(output_a=300, output_b=500):
    """msg_a appears twice (streaming repeat) and must be counted once."""
    return [
        usage_line("msg_a", output_a // 2, ts="2026-09-25T10:00:00.000Z"),
        usage_line("msg_a", output_a, ts="2026-09-25T10:00:01.000Z",
                   content=[tool_use("tu1", "Read", {"file_path": "/ws/brand/voice.md"})]),
        tool_result_line("tu1", 9000),
        usage_line("msg_b", output_b, ts="2026-09-25T10:02:00.000Z",
                   content=[tool_use("tu2", "WebFetch", {"url": "https://example.com/pricing"}),
                            tool_use("tu3", "Grep", {"pattern": "canonical"})]),
        tool_result_line("tu2", 40000, ts="2026-09-25T10:03:00.000Z"),
        tool_result_line("tu3", 120, ts="2026-09-25T10:03:30.000Z"),
    ]


class AppendRaceTests(unittest.TestCase):
    """state.append_jsonl from several processes at once (the hooks run in parallel)."""

    def test_concurrent_appends_lose_and_tear_nothing(self):
        import subprocess
        import sys

        from tests.hooks.helpers import HOOKS_DIR

        folder = tempfile.mkdtemp(prefix="tantra_race_")
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "claims.jsonl")
        code = ("import sys; sys.path.insert(0, sys.argv[1]); from tantra_core import state\n"
                "for i in range(250): state.append_jsonl(sys.argv[2], {'w': sys.argv[3], 'i': i, 'pad': 'x' * 300})")
        procs = [subprocess.Popen([sys.executable, "-I", "-S", "-c", code, HOOKS_DIR, path, str(w)]) for w in range(6)]
        for proc in procs:
            self.assertEqual(proc.wait(timeout=120), 0)
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        self.assertEqual(len(lines), 6 * 250)
        rows = [json.loads(line) for line in lines]  # raises on a torn line
        self.assertEqual({(r["w"], r["i"]) for r in rows}, {(str(w), i) for w in range(6) for i in range(250)})


class CommonTests(SentinelCase):
    def test_transcript_usage_is_deduped_by_message_id(self):
        from tantra_core.sentinels import common

        path = self.write_agent_transcript("a1")
        facts = common.analyse_transcript(path)
        self.assertEqual(facts["messages"], 2)
        self.assertEqual(facts["tokens"]["output"], 800)
        self.assertEqual(facts["tokens"]["input"], 200)
        self.assertEqual(facts["tokens"]["cache_read"], 2000)
        self.assertEqual(facts["heaviest"][0], {"tool": "WebFetch", "target": "https://example.com/pricing", "chars": 40000})
        self.assertEqual(facts["tool_counts"], {"Read": 1, "WebFetch": 1, "Grep": 1})
        self.assertEqual(facts["last_tool"]["tool"], "Grep")

    def test_agent_file_derives_from_main_transcript(self):
        from tantra_core.sentinels import common

        self.assertEqual(common.agent_file(self.transcript, "abc"), os.path.join(self.subagents, "agent-abc.jsonl"))
        inner = os.path.join(self.subagents, "agent-x.jsonl")
        self.assertEqual(common.agent_file(inner, "abc", ".meta.json"), os.path.join(self.subagents, "agent-abc.meta.json"))
        self.assertIsNone(common.agent_file("", "abc"))

    def test_modes_shape_the_result(self):
        from tantra_core.sentinels import common

        ctx = self.ctx("PreToolUse", tool_name="Read", tool_input={})
        self.assertIsNone(common.outcome(ctx, "x", "off", "echo_deny", deny="no"))
        self.assertIsNone(common.outcome(ctx, "x", "observe", "echo_deny", deny="no", est_tokens_avoided=50))
        assisted = common.outcome(ctx, "x", "assist", "echo_deny", deny="no", est_tokens_avoided=50)
        self.assertIsNone(assisted.deny)
        self.assertIn("no", assisted.context)
        enforced = common.outcome(ctx, "x", "enforce", "echo_deny", deny="no", est_tokens_avoided=50)
        self.assertEqual(enforced.deny, "no")
        rows = self.ledger("sentinel.jsonl")
        self.assertEqual([r["applied"] for r in rows], [False, True, True])
        self.assertEqual([r["est_tokens_avoided"] for r in rows], [0, 0, 50])

    def test_unknown_mode_falls_back_to_default(self):
        from tantra_core.sentinels import common

        self.config(echo={"mode": "loud"})
        ctx = self.ctx("PreToolUse")
        self.assertEqual(common.settings(ctx, "echo", {"mode": "enforce"})["mode"], "enforce")

    def test_per_tier_accepts_number_or_map(self):
        from tantra_core.sentinels import common

        self.assertEqual(common.per_tier(0.02, "sub", {"sub": 6}), 0.02)
        self.assertEqual(common.per_tier({"domain": 9}, "domain", {"domain": 10}), 9.0)
        self.assertEqual(common.per_tier({"domain": 9}, "sub", {"sub": 6}), 6.0)

    def test_head_tail_keeps_both_ends(self):
        from tantra_core.sentinels import common

        text = "HEAD" + "m" * 10000 + "TAIL"
        out = common.head_tail(text, 500)
        self.assertLessEqual(len(out), 500)
        self.assertTrue(out.startswith("HEAD") and out.endswith("TAIL"))


if __name__ == "__main__":
    unittest.main()
