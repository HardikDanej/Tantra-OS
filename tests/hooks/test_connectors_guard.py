"""connectors_guard: deny/assist matrix for MCP calls, write-gate enforcement, and redacted usage logging."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

from tests.hooks.helpers import MINI_REGISTRY, REPO, make_ctx, payload, run_hook, temp_home

LIB = os.path.join(REPO, ".claude", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import approval_gate  # noqa: E402
import mcp_connector_registry as reg  # noqa: E402
from tantra_core import connectors_guard  # noqa: E402

SUBAGENT = {"agent_id": "agent-123", "agent_type": "seo-agent"}
SECRET = "sk-abcdefghijklmnopqrstuvwxyz0123456789"


def quiet(func, argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(argv)


def make_workspace():
    ws = tempfile.mkdtemp(prefix="tantra_ws_")
    os.makedirs(os.path.join(ws, "memory"))
    with open(os.path.join(ws, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# client workspace\n")
    return ws


def connect(ws, server="hubspot", reads="get_deal", writes="", approve=True, stakes=None):
    argv = ["propose", "--workspace", ws, "--server", server, "--transport", "http", "--url",
            "https://mcp.example.com/mcp", "--scope", "local", "--read-tools", reads]
    if writes:
        argv += ["--write-tools", writes]
    assert quiet(reg.main, argv) == 0
    record = reg.load_state(ws)[server]
    gates = os.path.join(ws, "memory", "approval_gates.jsonl")
    quiet(approval_gate.main, [gates, "create", "--gate-id", record["gate_id"], "--stakes-class",
                               stakes or record["stakes_class"], "--summary", "s", "--what-if-approved", "a",
                               "--what-if-rejected", "r", "--red-team-verdict", "N/A", "--irreversibility-note", "i",
                               "--binding", record["config_hash"]])
    quiet(approval_gate.main, [gates, "respond", "--gate-id", record["gate_id"], "--decision", "approved"])
    if approve:
        assert quiet(reg.main, ["record-connect", "--workspace", ws, "--server", server,
                                "--gate-id", record["gate_id"]]) == 0
    return record["gate_id"]


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.ws = make_workspace()
        self.home = temp_home()
        self.addCleanup(shutil.rmtree, self.ws, True)
        self.addCleanup(shutil.rmtree, self.home, True)

    def pre(self, tool, subagent=False, **extra):
        fields = dict(SUBAGENT) if subagent else {}
        fields.update(extra)
        ctx = make_ctx(payload("PreToolUse", cwd=self.ws, tool_name=tool, tool_input={"q": SECRET}, **fields),
                       home=self.home, registry=MINI_REGISTRY)
        return connectors_guard.handle(ctx)

    def post(self, tool, response=None, event="PostToolUse"):
        ctx = make_ctx(payload(event, cwd=self.ws, tool_name=tool, tool_input={"token": SECRET},
                               tool_response=response if response is not None else {"content": [{"text": SECRET}]}),
                       home=self.home, registry=MINI_REGISTRY)
        return connectors_guard.handle(ctx)

    def usage_rows(self):
        path = os.path.join(self.ws, "memory", "tool_usage_log.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class DecisionMatrixTests(GuardCase):
    def test_unknown_server_denied_in_tantra_subagent(self):
        result = self.pre("mcp__salesforce__query", subagent=True)
        self.assertIn("salesforce", result.deny)
        self.assertIn("tantra-connect", result.deny)
        self.assertIn("mk connect", result.deny)

    def test_unknown_server_is_a_one_time_note_on_main_thread(self):
        first = self.pre("mcp__salesforce__query")
        self.assertIsNone(first.deny)
        self.assertIn("tantra-connect", first.context)
        self.assertIsNone(self.pre("mcp__salesforce__other"))
        self.assertIsNotNone(self.pre("mcp__notion__search").context)

    def test_any_subagent_is_enforced_so_calls_cannot_be_laundered(self):
        for agent_type in ("general-purpose", "some-user-agent", None):
            result = self.pre("mcp__evil__delete_all", agent_id="a2", agent_type=agent_type)
            self.assertIsNotNone(result.deny, agent_type)
            self.assertIn("tantra-connect", result.deny)

    def test_approved_read_tool_passes_everywhere(self):
        connect(self.ws)
        self.assertIsNone(self.pre("mcp__hubspot__get_deal"))
        self.assertIsNone(self.pre("mcp__hubspot__get_deal", subagent=True))

    def test_unlisted_tool_on_connected_server(self):
        connect(self.ws)
        self.assertIn("not in the approved", self.pre("mcp__hubspot__delete_deal", subagent=True).deny)
        self.assertIsNone(self.pre("mcp__hubspot__delete_deal").deny)

    def test_proposed_but_not_connected_server(self):
        connect(self.ws, approve=False)
        self.assertIn("proposed", self.pre("mcp__hubspot__get_deal", subagent=True).deny)

    def test_revoked_server_denied_in_subagent(self):
        connect(self.ws)
        quiet(reg.main, ["revoke", "--workspace", self.ws, "--server", "hubspot"])
        self.assertIn("revoked", self.pre("mcp__hubspot__get_deal", subagent=True).deny)

    def test_approved_write_tool_with_bound_write_gate_passes(self):
        connect(self.ws, writes="create_note")
        self.assertIsNone(self.pre("mcp__hubspot__create_note"))
        self.assertIsNone(self.pre("mcp__hubspot__create_note", subagent=True))

    def test_write_tool_denied_on_main_thread_when_gate_no_longer_binds(self):
        gate_id = connect(self.ws, writes="create_note")
        gates = os.path.join(self.ws, "memory", "approval_gates.jsonl")
        with open(gates, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"gate_id": gate_id, "event": "superseded", "timestamp": "t", "note": "changed"}) + "\n")
        main_thread = self.pre("mcp__hubspot__create_note")
        self.assertIn("superseded", main_thread.deny)
        self.assertIn("mcp_write_connection", main_thread.deny)
        self.assertIsNotNone(self.pre("mcp__hubspot__create_note", subagent=True).deny)
        self.assertIn("superseded", self.pre("mcp__hubspot__get_deal", subagent=True).deny)

    def test_write_tool_of_unconnected_proposal_denied_on_main_thread(self):
        connect(self.ws, writes="create_note", approve=False)
        self.assertIsNotNone(self.pre("mcp__hubspot__create_note").deny)

    def test_claude_ai_uuid_server_names(self):
        server = "1a59c906-04da-521d-bda7-7f71b9f9e01c"
        tool = f"mcp__{server}__query"
        self.assertIsNotNone(self.pre(tool, subagent=True).deny)
        quiet(reg.main, ["propose", "--workspace", self.ws, "--server", server, "--transport", "claudeai",
                         "--scope", "user", "--read-tools", "query"])
        record = reg.load_state(self.ws)[server]
        gates = os.path.join(self.ws, "memory", "approval_gates.jsonl")
        quiet(approval_gate.main, [gates, "create", "--gate-id", record["gate_id"], "--stakes-class", "mcp_connection",
                                   "--summary", "s", "--what-if-approved", "a", "--what-if-rejected", "r",
                                   "--red-team-verdict", "N/A", "--irreversibility-note", "i",
                                   "--binding", record["config_hash"]])
        quiet(approval_gate.main, [gates, "respond", "--gate-id", record["gate_id"], "--decision", "approved"])
        quiet(reg.main, ["record-connect", "--workspace", self.ws, "--server", server, "--gate-id", record["gate_id"]])
        self.assertIsNone(self.pre(tool, subagent=True))

    def test_no_workspace_or_non_mcp_tool_means_no_opinion(self):
        ctx = make_ctx(payload("PreToolUse", cwd=REPO, tool_name="mcp__x__y", **SUBAGENT), home=self.home,
                       registry=MINI_REGISTRY)
        self.assertIsNone(connectors_guard.handle(ctx))
        self.assertIsNone(self.pre("Read", subagent=True))

    def test_config_can_switch_off_subagent_enforcement(self):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"connectors": {"enforce_subagents": False}}, fh)
        self.assertIsNone(self.pre("mcp__salesforce__query", subagent=True))


class AttestedStepTests(GuardCase):
    """A sub-agent cannot walk the human-attested approval chain on its own (finding: self-approval)."""

    LIB_CMD = "python ~/Tantra/.claude/lib/"

    def tool(self, tool_name, tool_input, subagent=True, **extra):
        fields = dict(SUBAGENT) if subagent else {}
        fields.update(extra)
        ctx = make_ctx(payload("PreToolUse", cwd=self.ws, tool_name=tool_name, tool_input=tool_input, **fields),
                       home=self.home, registry=MINI_REGISTRY)
        return connectors_guard.handle(ctx)

    def bash(self, command, **kw):
        return self.tool("Bash", {"command": command}, **kw)

    BLOCKED = (
        LIB_CMD + "approval_gate.py memory/approval_gates.jsonl respond --gate-id mcp_crm_ac9ef57e_1a2b3c "
                  "--decision approved --note yes",
        LIB_CMD + "approval_gate.py memory/approval_gates.jsonl create --gate-id x --stakes-class mcp_connection "
                  "--summary s",
        LIB_CMD + "mcp_connector_registry.py record-connect --server crm --gate-id mcp_crm_ac9ef57e_1a2b3c",
        "claude mcp add --transport http --scope local crm https://evil.example.com/mcp",
        "claude mcp remove hubspot -s local",
        "echo '{\"event\":\"connected\",\"server\":\"crm\"}' >> memory/mcp_connections.jsonl",
        "echo '{\"gate_id\":\"g\",\"event\":\"approved\"}' >> memory/approval_gates.jsonl",
        "python -c \"open('memory/approval_gates.jsonl','a').write('x')\"",
    )

    def test_subagent_attested_steps_denied(self):
        for command in self.BLOCKED:
            result = self.bash(command)
            self.assertIsNotNone(result, command)
            self.assertIn("sub-agent may not", result.deny)
        for agent_type in ("general-purpose", None):
            self.assertIsNotNone(self.bash(self.BLOCKED[0], agent_id="a9", agent_type=agent_type))
        self.assertIsNotNone(self.tool("PowerShell", {"command": self.BLOCKED[2]}))

    def test_subagent_ledger_edits_denied(self):
        for tool, key in (("Write", "file_path"), ("Edit", "file_path"), ("MultiEdit", "file_path")):
            for name in ("mcp_connections.jsonl", "approval_gates.jsonl"):
                path = os.path.join(self.ws, "memory", name)
                self.assertIsNotNone(self.tool(tool, {key: path, "content": "{}"}).deny, (tool, name))
        self.assertIsNone(self.tool("Write", {"file_path": os.path.join(self.ws, "memory", "notes.md")}))

    def test_ordinary_subagent_and_main_thread_commands_pass(self):
        LIB_CMD = self.LIB_CMD
        for command in (LIB_CMD + "approval_gate.py memory/approval_gates.jsonl respond --gate-id annual_budget_fy27 "
                                  "--decision approved --note yes",
                        LIB_CMD + "approval_gate.py memory/approval_gates.jsonl list --status pending",
                        LIB_CMD + "mcp_connector_registry.py check-tool --tool mcp__crm__search",
                        "git status", "claude mcp list"):
            self.assertIsNone(self.bash(command), command)
        for command in self.BLOCKED:
            self.assertIsNone(self.bash(command, subagent=False), command)

    def test_protection_can_be_switched_off(self):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"connectors": {"protect_approvals": False}}, fh)
        self.assertIsNone(self.bash(self.BLOCKED[0]))


class UsageLogTests(GuardCase):
    def test_post_logs_one_redacted_line_in_ledger_schema(self):
        self.assertIsNone(self.post("mcp__hubspot__get_deal"))
        rows = self.usage_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(set(row), {"tool", "timestamp", "calls", "status", "cost_usd", "note"})
        self.assertEqual((row["tool"], row["calls"], row["status"], row["cost_usd"], row["note"]),
                         ("mcp:hubspot", 1, "ok", None, "get_deal"))
        with open(os.path.join(self.ws, "memory", "tool_usage_log.jsonl"), encoding="utf-8") as fh:
            raw = fh.read()
        self.assertNotIn(SECRET, raw)
        self.assertNotIn("token", raw)

    def test_error_status(self):
        self.post("mcp__hubspot__get_deal", response={"isError": True, "content": []})
        self.post("mcp__hubspot__get_deal", event="PostToolUseFailure")
        self.assertEqual([r["status"] for r in self.usage_rows()], ["error", "error"])

    def test_post_outside_workspace_logs_nothing(self):
        ctx = make_ctx(payload("PostToolUse", cwd=REPO, tool_name="mcp__x__y"), home=self.home, registry=MINI_REGISTRY)
        self.assertIsNone(connectors_guard.handle(ctx))

    def test_ledger_reads_guard_lines(self):
        for _ in range(2):
            self.post("mcp__hubspot__get_deal")
        try:
            import tool_usage_ledger
        except ImportError:
            self.skipTest("tool_usage_ledger needs pydantic")
        summary = tool_usage_ledger.summarize(tool_usage_ledger.read_events(
            __import__("pathlib").Path(self.ws, "memory", "tool_usage_log.jsonl")), 30)
        self.assertEqual(summary["by_tool"]["mcp:hubspot"]["calls"], 2)


class EndToEndTests(GuardCase):
    def setUp(self):
        super().setUp()
        self.registry_path = os.path.join(self.home, "registry.json")
        with open(self.registry_path, "w", encoding="utf-8") as fh:
            json.dump(MINI_REGISTRY, fh)

    def hook(self, event, tool, subagent=False, active=True, **fields):
        extra = dict(SUBAGENT) if subagent else {}
        extra.update(fields)
        env = {"TANTRA_REGISTRY": self.registry_path}
        if active:
            env["TANTRA_ACTIVE"] = "1"
        extra.setdefault("tool_input", {})
        return run_hook(payload(event, cwd=self.ws, tool_name=tool, **extra),
                        mode="pre" if event == "PreToolUse" else "post", home=self.home, env=env)

    def test_subagent_call_to_unapproved_server_is_denied_by_real_dispatcher(self):
        code, out, _ = self.hook("PreToolUse", "mcp__salesforce__query", subagent=True)
        self.assertEqual(code, 0)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("Tantra connector approval", hso["permissionDecisionReason"])

    def test_subagent_self_approval_is_denied_by_real_dispatcher(self):
        command = ("python .claude/lib/approval_gate.py memory/approval_gates.jsonl respond "
                   "--gate-id mcp_crm_ac9ef57e_1a2b3c --decision approved --note yes")
        code, out, _ = self.hook("PreToolUse", "Bash", subagent=True, tool_input={"command": command})
        self.assertEqual(code, 0)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        code, out, _ = self.hook("PreToolUse", "Bash", tool_input={"command": command})
        self.assertEqual(code, 0)
        self.assertNotEqual(((out or {}).get("hookSpecificOutput") or {}).get("permissionDecision"), "deny")

    def test_approved_read_is_not_denied(self):
        connect(self.ws)
        code, out, _ = self.hook("PreToolUse", "mcp__hubspot__get_deal", subagent=True)
        self.assertEqual(code, 0)
        self.assertNotEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_inactive_session_is_left_alone(self):
        code, out, _ = self.hook("PreToolUse", "mcp__salesforce__query", active=False)
        self.assertEqual(code, 0)
        reason = ((out or {}).get("hookSpecificOutput") or {}).get("permissionDecisionReason") or ""
        self.assertNotIn("Tantra connector approval", reason)

    def test_post_hook_writes_usage_line(self):
        code, _, _ = self.hook("PostToolUse", "mcp__hubspot__get_deal", tool_response={"content": []})
        self.assertEqual(code, 0)
        self.assertEqual([r["tool"] for r in self.usage_rows()], ["mcp:hubspot"])


if __name__ == "__main__":
    unittest.main()
