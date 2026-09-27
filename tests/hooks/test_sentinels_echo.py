"""Echo: identical reads, fetches and dispatches are noted, then denied."""
import os
import shutil
import tempfile
import time
import unittest

from tests.hooks.test_sentinels_common import GOOD_OUTPUT, SentinelCase


class EchoTests(SentinelCase):
    def setUp(self):
        super().setUp()
        self.ws = tempfile.mkdtemp(prefix="tantra_ws_")
        self.addCleanup(shutil.rmtree, self.ws, True)
        os.makedirs(os.path.join(self.ws, "memory", "evidence", "raw"))
        with open(os.path.join(self.ws, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write("# client\n")
        self.file = os.path.join(self.ws, "brand.md")
        with open(self.file, "w", encoding="utf-8") as fh:
            fh.write("voice " * 500)

    def call(self, tool, tool_input, agent_id=None, agent_type=None, response="x" * 2000):
        """One Pre + Post pair; returns the Pre results."""
        from tantra_core import sentinels

        extra = {"agent_id": agent_id, "agent_type": agent_type} if agent_id else {}
        pre = sentinels.handle(self.ctx("PreToolUse", tool_name=tool, tool_input=tool_input, cwd=self.ws, **extra)) or []
        if not any(r.deny for r in pre):
            sentinels.handle(self.ctx("PostToolUse", tool_name=tool, tool_input=tool_input, cwd=self.ws,
                                      tool_response=response, **extra))
        return pre

    def test_second_read_notes_third_is_denied(self):
        read = {"file_path": self.file}
        self.assertEqual(self.call("Read", read), [])
        second = self.call("Read", read)
        self.assertIn("already ran in the main thread", second[0].context)
        self.assertIsNone(second[0].deny)
        third = self.call("Read", read)
        self.assertIn("already ran 2 time(s)", third[0].deny)
        self.assertIn("offset/limit", third[0].deny)
        row = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "echo_deny"][0]
        self.assertEqual(row["est_tokens_avoided"], 500)

    def test_relative_and_absolute_paths_share_a_key(self):
        self.call("Read", {"file_path": "brand.md"})
        self.assertTrue(self.call("Read", {"file_path": self.file}))

    def test_changed_file_resets_the_count(self):
        read = {"file_path": self.file}
        self.call("Read", read)
        self.call("Read", read)
        with open(self.file, "a", encoding="utf-8") as fh:
            fh.write("new line\n")
        stamp = time.time() + 5
        os.utime(self.file, (stamp, stamp))
        self.assertEqual(self.call("Read", read), [])

    def test_different_offsets_are_different_calls(self):
        self.call("Read", {"file_path": self.file, "offset": 1, "limit": 50})
        self.assertEqual(self.call("Read", {"file_path": self.file, "offset": 51, "limit": 50}), [])

    def test_scopes_are_separate(self):
        read = {"file_path": self.file}
        self.call("Read", read)
        self.call("Read", read)
        self.assertEqual(self.call("Read", read, agent_id="s1", agent_type="seo-agent"), [])

    def test_compaction_resets_the_count(self):
        from tantra_core import sentinels

        read = {"file_path": self.file}
        self.call("Read", read)
        self.call("Read", read)
        time.sleep(0.01)
        sentinels.handle(self.ctx("PreCompact", cwd=self.ws))
        time.sleep(0.01)
        self.assertEqual(self.call("Read", read), [])

    def test_write_resets_grep(self):
        grep = {"pattern": "voice", "path": self.ws}
        self.call("Grep", grep)
        self.assertTrue(self.call("Grep", grep))
        time.sleep(0.01)
        self.call("Write", {"file_path": self.file, "content": "x"})
        time.sleep(0.01)
        self.assertEqual(self.call("Grep", grep), [])

    # -- regression: files changed by Bash / PowerShell / MCP reset Grep and Glob --
    def test_bash_resets_glob(self):
        glob = {"pattern": "out/*.md"}
        self.call("Glob", glob)
        self.assertTrue(self.call("Glob", glob))
        time.sleep(0.01)
        self.call("Bash", {"command": "python render.py --out out/report3.md"})
        time.sleep(0.01)
        self.assertEqual(self.call("Glob", glob), [], "the new file would be missing from the earlier result")

    def test_mcp_tool_resets_grep_but_not_read(self):
        grep = {"pattern": "voice", "path": self.ws}
        read = {"file_path": self.file}
        self.call("Grep", grep)
        self.call("Grep", grep)
        self.call("Read", read)
        self.call("Read", read)
        time.sleep(0.01)
        self.call("mcp__drive__export_file", {"id": "abc"})
        time.sleep(0.01)
        self.assertEqual(self.call("Grep", grep), [])
        self.assertTrue(self.call("Read", read)[0].deny, "Read is keyed on the file's own stat, still unchanged")

    def test_same_second_same_size_rewrite_resets_read(self):
        read = {"file_path": self.file}
        base = (int(time.time()) - 100) * 1_000_000_000 + 100_000_000
        os.utime(self.file, ns=(base, base))
        self.call("Read", read)
        self.call("Read", read)
        with open(self.file, "w", encoding="utf-8") as fh:
            fh.write("tone " * 600)  # same size (3,000 chars), same whole second
        os.utime(self.file, ns=(base + 400_000_000, base + 400_000_000))
        self.assertEqual(self.call("Read", read), [])

    # -- regression: a subagent's own compaction resets its read history -----------
    def test_subagent_precompact_resets_its_scope(self):
        from tantra_core import sentinels

        read = {"file_path": self.file}
        sub = {"agent_id": "sub1", "agent_type": "technical-seo-subagent"}
        self.call("Read", read, **sub)
        self.call("Read", read, **sub)
        time.sleep(0.01)
        sentinels.handle(self.ctx("PreCompact", cwd=self.ws, trigger="auto", **sub))
        time.sleep(0.01)
        self.assertEqual(self.call("Read", read, **sub), [])

    def test_subagent_compaction_session_start_resets_its_scope(self):
        from tantra_core import sentinels

        read = {"file_path": self.file}
        sub = {"agent_id": "sub1", "agent_type": "technical-seo-subagent"}
        self.call("Read", read, **sub)
        self.call("Read", read, **sub)
        time.sleep(0.01)
        sentinels.handle(self.ctx("SessionStart", cwd=self.ws, source="compact", **sub))
        time.sleep(0.01)
        self.assertEqual(self.call("Read", read, **sub), [])

    def test_cross_scope_webfetch_names_other_agent_and_evidence(self):
        url = "https://example.com/pricing"
        with open(os.path.join(self.ws, "memory", "evidence", "raw", "pricing.md"), "w", encoding="utf-8") as fh:
            fh.write(f"source: {url}\n")
        self.call("WebFetch", {"url": url, "prompt": "prices"}, agent_id="s1", agent_type="seo-agent")
        note = self.call("WebFetch", {"url": url, "prompt": "plans"}, agent_id="s2", agent_type="technical-seo-subagent")
        self.assertIn("already fetched by seo-agent (s1)", note[0].context)
        self.assertIn("pricing.md", note[0].context)

    def test_assist_mode_never_denies(self):
        self.config(echo={"mode": "assist"})
        read = {"file_path": self.file}
        for _ in range(3):
            results = self.call("Read", read)
        self.assertIsNone(results[0].deny)
        self.assertIn("already ran 2 time(s)", results[0].context)

    def test_identical_completed_dispatch_points_to_saved_output(self):
        from tantra_core import sentinels

        dispatch = {"subagent_type": "seo-agent", "prompt": "Audit the site"}
        self.assertIsNone(sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", tool_input=dispatch)))
        sentinels.handle(self.ctx("SubagentStart", agent_id="a1", agent_type="seo-agent"))
        sentinels.handle(self.ctx("SubagentStop", agent_id="a1", agent_type="seo-agent",
                                  last_assistant_message=GOOD_OUTPUT + "CITATION_CHECK: pass\n"))
        sentinels.handle(self.ctx("PostToolUse", tool_name="Agent", tool_use_id="t1", tool_input=dispatch,
                                  tool_response={"status": "completed", "agentId": "a1"}))
        again = {"subagent_type": "seo-agent", "prompt": "  audit THE site "}
        note = sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", tool_input=again))
        self.assertIn("identical dispatch of seo-agent", note[0].context)
        self.assertIn(os.path.join("outputs", "seo-agent", "a1.txt"), note[0].context)
        other = {"subagent_type": "seo-agent", "prompt": "Audit the blog only"}
        self.assertIsNone(sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", tool_input=other)))


if __name__ == "__main__":
    unittest.main()
