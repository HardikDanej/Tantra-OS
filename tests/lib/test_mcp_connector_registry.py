"""Tests for .claude/lib/mcp_connector_registry.py and the tool_usage_ledger.py fixes it relies on."""
import contextlib
import io
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(REPO, ".claude", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import approval_gate  # noqa: E402
import mcp_connector_registry as reg  # noqa: E402

HTTP_BASE = ["propose", "--server", "hubspot", "--transport", "http", "--url", "https://mcp.example.com/mcp",
             "--scope", "local", "--read-tools", "search_contacts,get_deal"]


def run(func, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = func(argv)
    return code, out.getvalue(), err.getvalue()


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="tantra_ws_")
        os.makedirs(os.path.join(self.ws, "memory"))
        self.gates = os.path.join(self.ws, "memory", "approval_gates.jsonl")
        self.addCleanup(shutil.rmtree, self.ws, True)

    def reg(self, *argv):
        return run(reg.main, [argv[0], "--workspace", self.ws, *argv[1:]])

    def propose(self, *extra, base=HTTP_BASE):
        return self.reg(*base, *extra)

    def state(self):
        return reg.load_state(self.ws)

    def open_gate(self, server="hubspot", decision="approved", binding=None, stakes=None):
        record = self.state()[server]
        gate_id = record["gate_id"]
        argv = [self.gates, "create", "--gate-id", gate_id,
                "--stakes-class", stakes or record["stakes_class"], "--summary", "s",
                "--what-if-approved", "a", "--what-if-rejected", "r", "--red-team-verdict", "N/A",
                "--irreversibility-note", "i", "--binding", binding or record["config_hash"]]
        self.assertEqual(run(approval_gate.main, argv)[0], 0)
        if decision:
            code = run(approval_gate.main, [self.gates, "respond", "--gate-id", gate_id,
                                            "--decision", decision, "--note", "yes, connect it"])[0]
            self.assertEqual(code, 0)
        return gate_id

    def connect(self, *extra, server="hubspot"):
        self.assertEqual(self.propose(*extra)[0], 0)
        gate_id = self.open_gate(server)
        code, out, err = self.reg("record-connect", "--server", server, "--gate-id", gate_id)
        self.assertEqual(code, 0, err)
        return gate_id


class ProposeValidationTests(WorkspaceCase):
    def assertRejected(self, *argv, fragment=""):
        code, out, err = self.reg(*argv)
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, err)
        self.assertEqual(self.state(), {})

    def test_valid_http_proposal_prints_card_and_bound_gate_command(self):
        code, out, _ = self.propose("--write-tools", "create_note", "--header", "Authorization: Bearer ${HUBSPOT_TOKEN}")
        self.assertEqual(code, 0)
        record = self.state()["hubspot"]
        self.assertEqual(record["status"], "proposed")
        self.assertEqual(record["read_tools"], ["get_deal", "search_contacts"])
        self.assertEqual(record["write_tools"], ["create_note"])
        self.assertEqual(record["stakes_class"], "mcp_write_connection")
        self.assertIn("approval card: hubspot", out)
        self.assertIn("HUBSPOT_TOKEN", out)
        self.assertIn("--stakes-class mcp_write_connection", out)
        self.assertIn("--binding " + record["config_hash"], out)
        self.assertIn("Cost:", out)

    def test_read_only_proposal_uses_mcp_connection_class(self):
        self.propose()
        self.assertEqual(self.state()["hubspot"]["stakes_class"], "mcp_connection")

    def test_literal_header_secret_rejected(self):
        self.assertRejected(*HTTP_BASE, "--header", "Authorization: Bearer pat-na1-1234abcd-12ab-34cd-56ef-1234567890ab",
                            fragment="header Authorization")

    def test_literal_env_secret_rejected(self):
        self.assertRejected("propose", "--server", "files", "--transport", "stdio", "--command", "npx",
                            "--arg=-y", "--arg", "files-mcp@1.2.3", "--scope", "local", "--read-tools", "ls",
                            "--env", "API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456", fragment="env API_KEY")

    def test_secret_in_env_default_rejected(self):
        self.assertRejected("propose", "--server", "files", "--transport", "stdio", "--command", "npx",
                            "--arg", "files-mcp@1.2.3", "--scope", "local", "--read-tools", "ls",
                            "--env", "API_KEY=${API_KEY:-ghp_abcdefghijklmnopqrstuvwxyz0123}", fragment="default")

    def test_secret_in_url_query_rejected(self):
        self.assertRejected("propose", "--server", "x", "--transport", "http", "--url",
                            "https://mcp.example.com/mcp?api_key=abc123", "--scope", "local", "--read-tools", "a",
                            fragment="credential")

    def test_secret_in_stdio_arg_rejected(self):
        self.assertRejected("propose", "--server", "x", "--transport", "stdio", "--scope", "local", "--read-tools", "a",
                            "--", "npx", "x-mcp@1.0.0", "--token", "xoxb-1234567890-abcdefghij",
                            fragment="credential")

    def test_high_entropy_literal_rejected(self):
        self.assertRejected(*HTTP_BASE, "--header", "X-Api-Key: Zq8Rt2Lm9Xp4Vn7Bk3Hs6Wd1Jf5Gc0YaUeTiOo",
                            fragment="X-Api-Key")

    def test_non_https_remote_rejected_but_localhost_allowed(self):
        self.assertRejected("propose", "--server", "x", "--transport", "sse", "--url", "http://mcp.example.com/sse",
                            "--scope", "local", "--read-tools", "a", fragment="https")
        code, _, err = self.reg("propose", "--server", "dev", "--transport", "http", "--url",
                                "http://localhost:8080/mcp", "--scope", "local", "--read-tools", "a")
        self.assertEqual(code, 0, err)

    def test_unpinned_packages_rejected(self):
        for args in (["--arg=-y", "--arg", "@acme/crm-mcp"], ["--arg=-y", "--arg", "@acme/crm-mcp@latest"],
                     ["--arg", "crm-mcp@^1.2.0"]):
            self.assertRejected("propose", "--server", "crm", "--transport", "stdio", "--command", "npx", *args,
                                "--scope", "local", "--read-tools", "a", fragment="version-pinned")
        self.assertRejected("propose", "--server", "crm", "--transport", "stdio", "--command", "cmd",
                            "--arg", "/c", "--arg", "npx", "--arg=-y", "--arg", "crm-mcp",
                            "--scope", "local", "--read-tools", "a", fragment="version-pinned")
        self.assertRejected("propose", "--server", "crm", "--transport", "stdio", "--command", "uvx",
                            "--arg", "crm-mcp", "--scope", "local", "--read-tools", "a", fragment="version-pinned")

    def test_pinned_packages_accepted(self):
        cases = (("a", ["npx", "-y", "@acme/crm-mcp@1.2.3"]), ("b", ["npx.cmd", "crm-mcp@0.4.0-beta.1"]),
                 ("c", ["uvx", "crm-mcp==1.0.2"]), ("d", ["uvx", "--from", "crm-mcp==2.1", "crm"]),
                 ("e", ["cmd", "/c", "npx", "-y", "crm-mcp@3.0.0"]))
        for server, command_line in cases:
            code, _, err = self.reg("propose", "--server", server, "--transport", "stdio", "--scope", "local",
                                    "--read-tools", "t", "--", *command_line)
            self.assertEqual(code, 0, err)
            self.assertEqual(self.state()[server]["command"], command_line[0])
            self.assertEqual(self.state()[server]["args"], command_line[1:])

    def test_trailing_command_only_for_propose(self):
        self.assertEqual(self.reg("list", "--", "npx", "x@1.0.0")[0], 1)
        self.assertRejected("propose", "--server", "x", "--transport", "stdio", "--command", "npx", "--scope", "local",
                            "--read-tools", "a", "--", "npx", "x@1.0.0", fragment="only for propose")

    def test_shape_errors_rejected(self):
        self.assertRejected("propose", "--server", "HubSpot", "--transport", "http", "--url", "https://x.io",
                            "--scope", "local", "--read-tools", "a", fragment="server name")
        self.assertRejected(*HTTP_BASE[:-1], "a,b", "--write-tools", "b", fragment="both read and write")
        self.assertRejected("propose", "--server", "x", "--transport", "http", "--url", "https://x.io",
                            "--scope", "local", fragment="at least one tool")
        self.assertRejected(*HTTP_BASE, "--env", "A=${A}", fragment="stdio servers only")

    def test_full_tool_names_are_normalized(self):
        self.propose("--write-tools", "mcp__hubspot__create_note")
        self.assertEqual(self.state()["hubspot"]["write_tools"], ["create_note"])

    def test_config_hash_covers_tools_but_not_notes(self):
        ns = reg.build_parser().parse_args(HTTP_BASE)
        base = reg.config_hash(reg.build_spec(ns))
        ns_notes = reg.build_parser().parse_args(HTTP_BASE + ["--notes", "hello"])
        self.assertEqual(base, reg.config_hash(reg.build_spec(ns_notes)))
        ns_more = reg.build_parser().parse_args(HTTP_BASE[:-1] + ["search_contacts,get_deal,get_company"])
        self.assertNotEqual(base, reg.config_hash(reg.build_spec(ns_more)))
        ns_order = reg.build_parser().parse_args(HTTP_BASE[:-1] + ["get_deal,search_contacts"])
        self.assertEqual(base, reg.config_hash(reg.build_spec(ns_order)))


class LifecycleTests(WorkspaceCase):
    def test_record_connect_requires_existing_approved_gate(self):
        self.propose()
        gate_id = self.state()["hubspot"]["gate_id"]
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)
        self.open_gate(decision=None)
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("pending", err)
        self.assertEqual(self.state()["hubspot"]["status"], "proposed")

    def test_binding_mismatch_blocks_record_connect(self):
        self.propose()
        gate_id = self.open_gate(binding="0" * 64)
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("different configuration", err)

    def test_changed_spec_after_approval_blocks_record_connect(self):
        self.propose()
        gate_id = self.open_gate()
        self.propose("--write-tools", "create_note")
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("not the gate opened for the current proposal", err)

    def test_write_tools_need_write_class_gate(self):
        self.propose("--write-tools", "create_note")
        gate_id = self.open_gate(stakes="mcp_connection")
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("mcp_write_connection", err)

    def test_connect_then_check_tool_matrix(self):
        self.connect("--write-tools", "create_note")
        self.assertEqual(self.state()["hubspot"]["status"], "connected")
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")[0], 0)
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__create_note")[0], 3)
        code, out, _ = self.reg("check-tool", "--tool", "mcp__hubspot__delete_deal")
        self.assertEqual(code, 1)
        self.assertIn("not in the approved", out)
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__salesforce__query")[0], 1)

    def test_every_tool_denied_once_gate_superseded(self):
        gate_id = self.connect("--write-tools", "create_note")
        with open(self.gates, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"gate_id": gate_id, "event": "pending", "timestamp": "t", "stakes_class": "mcp_write_connection",
                                 "binding": "f" * 64}) + "\n")
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__create_note")[0], 1)
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")[0], 1)

    def test_reproposal_suspends_connection(self):
        self.connect()
        self.propose("--write-tools", "create_note")
        code, out, _ = self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")
        self.assertEqual(code, 1)
        self.assertIn("proposed", out)

    def test_revoke(self):
        self.connect()
        code, out, _ = self.reg("revoke", "--server", "hubspot", "--reason", "trial over")
        self.assertEqual(code, 0)
        self.assertIn("claude mcp remove hubspot -s local", out)
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")[0], 1)
        self.assertEqual(self.reg("revoke", "--server", "hubspot")[0], 1)
        self.assertEqual(self.reg("revoke", "--server", "nobody")[0], 1)
        self.assertEqual(self.reg("connect-command", "--server", "hubspot")[0], 1)

    def test_status_and_list(self):
        self.connect()
        code, out, _ = self.reg("status", "--server", "hubspot")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hubspot"]["status"], "connected")
        self.assertEqual(self.reg("status", "--server", "nope")[0], 1)
        code, out, _ = self.reg("list")
        self.assertIn("hubspot", out)
        self.assertIn("connected", out)

    def test_ledger_tolerates_torn_line(self):
        self.propose()
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), "a", encoding="utf-8") as fh:
            fh.write('{"event": "connec')
        self.assertEqual(self.state()["hubspot"]["status"], "proposed")


class ConnectCommandTests(WorkspaceCase):
    def test_http_header_command_keeps_reference(self):
        self.propose("--header", "Authorization: Bearer ${HUBSPOT_TOKEN}")
        code, out, _ = self.reg("connect-command", "--server", "hubspot")
        self.assertEqual(code, 0)
        self.assertIn("claude mcp add --transport http --scope local hubspot https://mcp.example.com/mcp "
                      "--header 'Authorization: Bearer ${HUBSPOT_TOKEN}'", out)
        self.assertNotIn("/mcp, pick", out)

    def test_oauth_remote_mentions_mcp_login(self):
        self.propose()
        out = self.reg("connect-command", "--server", "hubspot")[1]
        self.assertIn("/mcp", out)
        self.assertIn("OAuth", out)

    def test_stdio_command(self):
        self.reg("propose", "--server", "files", "--transport", "stdio", "--env", "FILES_TOKEN=${FILES_TOKEN}",
                 "--scope", "project", "--read-tools", "ls", "--", "npx", "-y", "@acme/files-mcp@1.2.3")
        out = self.reg("connect-command", "--server", "files")[1]
        self.assertIn("claude mcp add --transport stdio --scope project files --env 'FILES_TOKEN=${FILES_TOKEN}' -- "
                      "npx -y @acme/files-mcp@1.2.3", out)

    def test_claudeai_connector(self):
        server = "1a59c906-04da-521d-bda7-7f71b9f9e01c"
        code, _, err = self.reg("propose", "--server", server, "--transport", "claudeai", "--scope", "user",
                                "--read-tools", "read,query")
        self.assertEqual(code, 0, err)
        self.assertIn("claude.ai", self.reg("connect-command", "--server", server)[1])
        self.assertEqual(self.reg("propose", "--server", "x", "--transport", "claudeai", "--url", "https://x.io",
                                  "--scope", "user", "--read-tools", "a")[0], 1)


class CatalogTests(WorkspaceCase):
    def write_catalog(self, **entry):
        base = {"id": "hubspot", "vendor": "HubSpot", "display_name": "HubSpot CRM (official)", "category": "crm",
                "official": True, "transport": "http", "url": "https://mcp.example.com/mcp", "auth": "oauth",
                "read_tools": ["search_contacts", "get_deal"], "write_tools": ["create_note"],
                "cost_note": "Included in every HubSpot tier.", "sources": ["https://developers.example.com/mcp"],
                "verified_at": date.today().isoformat()}
        base.update(entry)
        path = os.path.join(self.ws, "catalog.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "generated_at": "2026-09-01T00:00:00Z", "entries": [base]}, fh)
        return path

    def test_fresh_matching_entry_fills_card_without_checks(self):
        catalog = self.write_catalog()
        out = self.propose("--catalog-id", "hubspot", "--catalog", catalog)[1]
        self.assertIn("HubSpot CRM (official)", out)
        self.assertIn("Included in every HubSpot tier.", out)
        self.assertNotIn("CHECK:", out)

    def test_stale_or_mismatched_entry_is_flagged(self):
        old = (date.today() - timedelta(days=90)).isoformat()
        catalog = self.write_catalog(verified_at=old, url="https://other.example.com/mcp")
        out = self.propose("--catalog-id", "hubspot", "--catalog", catalog, "--read-tools", "search_contacts,create_note",
                           "--confirm-read-tools", "create_note")[1]
        self.assertIn("re-verify", out)
        self.assertIn("URL differs", out)
        self.assertIn("catalog marks as WRITE: create_note", out)

    def test_missing_catalog_id_is_flagged(self):
        catalog = self.write_catalog()
        out = self.propose("--catalog-id", "salesforce", "--catalog", catalog)[1]
        self.assertIn("not in connectors/mcp_catalog.json", out)

    def test_schema_file_is_valid_json_and_requires_sources(self):
        with open(os.path.join(REPO, "connectors", "mcp_catalog.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        required = schema["$defs"]["entry"]["required"]
        for key in ("sources", "verified_at", "read_tools", "write_tools", "cost_note"):
            self.assertIn(key, required)


class RedactionTests(unittest.TestCase):
    def test_redact_scrubs_tokens_and_keeps_references(self):
        text = ("Authorization: Bearer abcdefghijklmnop12345 url=https://x.io/?api_key=s3cr3tvalue&x=1 "
                "key sk-abcdefghijklmnopqrstuvwxyz0123 ghp_abcdefghijklmnopqrstuvwxyz012345 "
                "env ${HUBSPOT_TOKEN} id 1a59c906-04da-521d-bda7-7f71b9f9e01c")
        out = reg.redact(text)
        for secret in ("abcdefghijklmnop12345", "s3cr3tvalue", "sk-abcdef", "ghp_abcdef"):
            self.assertNotIn(secret, out)
        self.assertIn("${HUBSPOT_TOKEN}", out)
        self.assertIn("1a59c906-04da-521d-bda7-7f71b9f9e01c", out)
        self.assertEqual(reg.redact(None), "")

    def test_ordinary_names_are_not_secrets(self):
        for text in ("https://mcp.hubspot.com/anthropic", "@modelcontextprotocol/server-filesystem@2025.1.14",
                     "search_crm_objects", "1a59c906-04da-521d-bda7-7f71b9f9e01c", "Bearer ${TOKEN}"):
            self.assertFalse(reg.looks_like_secret(text), text)

    def test_split_and_classify(self):
        self.assertEqual(reg.split_tool_name("mcp__1a59c906-04da__batch_get"), ("1a59c906-04da", "batch_get"))
        self.assertEqual(reg.split_tool_name("mcp__srv"), ("srv", None))
        self.assertEqual(reg.split_tool_name("Read"), (None, None))
        state = {"srv": {"read_tools": ["a"], "write_tools": ["b"], "status": "connected"}}
        self.assertEqual(reg.classify_tool(state, "mcp__srv__a")[0], "read")
        self.assertEqual(reg.classify_tool(state, "mcp__srv__b")[0], "write")
        self.assertEqual(reg.classify_tool(state, "mcp__srv__c")[0], "unknown")
        self.assertEqual(reg.classify_tool(state, "mcp__other__a"), ("unknown", None))


def commander_parse(line):
    """Parse a printed `claude mcp add` line the way claude CLI 2.1.263 (commander.js) does.

    -t/--transport and -s/--scope take one value; -e/--env and -H/--header are VARIADIC and keep
    consuming values until the next token that starts with '-'; `--` ends option parsing.
    """
    tokens = shlex.split(line)
    assert tokens[:3] == ["claude", "mcp", "add"], tokens
    opts, positionals, i, rest = {"env": [], "header": []}, [], 3, tokens[3:]
    single = {"--transport": "transport", "-t": "transport", "--scope": "scope", "-s": "scope"}
    variadic = {"--env": "env", "-e": "env", "--header": "header", "-H": "header"}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--":
            positionals += rest[i + 1:]
            break
        if tok in single:
            opts[single[tok]] = rest[i + 1]
            i += 2
            continue
        if tok in variadic:
            i += 1
            while i < len(rest) and not rest[i].startswith("-"):
                opts[variadic[tok]].append(rest[i])
                i += 1
            continue
        positionals.append(tok)
        i += 1
    return opts, positionals


class ConnectCommandParseTests(WorkspaceCase):
    """The printed command must survive the real CLI's variadic -e/-H parsing (finding: name swallowed)."""

    def test_http_with_headers_keeps_name_and_url(self):
        self.propose("--header", "Authorization: Bearer ${HUBSPOT_TOKEN}", "--header", "X-Portal: ${PORTAL_ID}")
        line = self.reg("connect-command", "--server", "hubspot")[1].splitlines()[0]
        opts, positionals = commander_parse(line)
        self.assertEqual(positionals, ["hubspot", "https://mcp.example.com/mcp"])
        self.assertEqual(sorted(opts["header"]), ["Authorization: Bearer ${HUBSPOT_TOKEN}", "X-Portal: ${PORTAL_ID}"])
        self.assertEqual((opts["transport"], opts["scope"]), ("http", "local"))

    def test_stdio_with_env_keeps_name_and_command(self):
        self.reg("propose", "--server", "files", "--transport", "stdio", "--env", "FILES_TOKEN=${FILES_TOKEN}",
                 "--env", "B=${B}", "--scope", "local", "--read-tools", "ls", "--", "npx", "-y", "@acme/files-mcp@1.2.3")
        line = self.reg("connect-command", "--server", "files")[1].splitlines()[0]
        opts, positionals = commander_parse(line)
        self.assertEqual(positionals, ["files", "npx", "-y", "@acme/files-mcp@1.2.3"])
        self.assertEqual(sorted(opts["env"]), ["B=${B}", "FILES_TOKEN=${FILES_TOKEN}"])


class ShellQuotingTests(WorkspaceCase):
    SMART = ("‘", "’", "‚", "‛")

    def test_quote_characters_never_reach_a_printed_command(self):
        for ch in self.SMART + ("'",):
            code, _, err = self.reg("propose", "--server", "pz", "--transport", "http", "--url",
                                    f"https://mcp.example.com/mcp?x={ch};Write-Output PWNED;{ch}",
                                    "--scope", "local", "--read-tools", "a")
            self.assertEqual(code, 1, ch)
            self.assertIn("printable ASCII", err)
            code, _, _ = self.reg("propose", "--server", "pz", "--transport", "stdio", "--scope", "local",
                                  "--read-tools", "a", "--", "npx", "-y", "x@1.0.0", f"--opt={ch};calc;{ch}")
            self.assertEqual(code, 1, ch)
            code, _, _ = self.reg("propose", "--server", "pz", "--transport", "stdio", "--scope", "local",
                                  "--read-tools", "a", "--env", f"K=${{K:-a{ch}b}}", "--", "npx", "x@1.0.0")
            self.assertEqual(code, 1, ch)
        self.assertEqual(self.state(), {})

    def test_q_refuses_instead_of_stripping(self):
        for bad in ("a'b", "a’b", "a\nb"):
            with self.assertRaises(ValueError):
                reg._q(bad)
        self.assertEqual(reg._q("${A}"), "'${A}'")

    def test_tampered_record_is_not_printed(self):
        self.propose()
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), encoding="utf-8") as fh:
            event = json.loads(fh.readline())
        event["url"] = "https://mcp.example.com/mcp?x=’;calc;’"
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
        code, out, err = self.reg("connect-command", "--server", "hubspot")
        self.assertEqual(code, 1)
        self.assertNotIn("calc", out)


class ApprovalReuseTests(WorkspaceCase):
    def other_workspace(self):
        other = tempfile.mkdtemp(prefix="tantra_ws_b_")
        os.makedirs(os.path.join(other, "memory"))
        self.addCleanup(shutil.rmtree, other, True)
        return other

    def test_revoked_approval_cannot_restore_the_connection(self):
        gate_id = self.connect()
        self.assertEqual(self.reg("revoke", "--server", "hubspot", "--reason", "user withdrew")[0], 0)
        self.propose()
        code, _, err = self.reg("record-connect", "--server", "hubspot", "--gate-id", gate_id)
        self.assertEqual(code, 1)
        self.assertIn("not the gate opened for the current proposal", err)
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")[0], 1)
        self.connect()  # a fresh gate and a fresh yes still work
        self.assertEqual(self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")[0], 0)

    def test_approval_from_another_workspace_is_refused(self):
        gate_id = self.connect()
        other = self.other_workspace()
        self.assertEqual(run(reg.main, ["propose", "--workspace", other, *HTTP_BASE[1:]])[0], 0)
        other_record = reg.load_state(other)["hubspot"]
        self.assertNotEqual(other_record["config_hash"], self.state()["hubspot"]["config_hash"])
        code, _, err = run(reg.main, ["record-connect", "--workspace", other, "--server", "hubspot",
                                      "--gate-id", gate_id, "--gates-ledger", self.gates])
        self.assertEqual(code, 1)
        code, _, err = run(reg.main, ["record-connect", "--workspace", other, "--server", "hubspot",
                                      "--gate-id", other_record["gate_id"], "--gates-ledger", self.gates])
        self.assertEqual(code, 1)
        self.assertIn("inside this workspace", err)
        shutil.copy(self.gates, os.path.join(other, "memory", "approval_gates.jsonl"))
        code, _, _ = run(reg.main, ["record-connect", "--workspace", other, "--server", "hubspot",
                                    "--gate-id", other_record["gate_id"]])
        self.assertEqual(code, 1)
        self.assertEqual(run(reg.main, ["check-tool", "--workspace", other, "--tool", "mcp__hubspot__get_deal"])[0], 1)

    def test_copied_ledgers_do_not_carry_a_connection(self):
        self.connect()
        other = self.other_workspace()
        for name in ("mcp_connections.jsonl", "approval_gates.jsonl"):
            shutil.copy(os.path.join(self.ws, "memory", name), os.path.join(other, "memory", name))
        code, out, _ = run(reg.main, ["check-tool", "--workspace", other, "--tool", "mcp__hubspot__get_deal"])
        self.assertEqual(code, 1)
        self.assertIn("different workspace", out)

    def test_forged_connected_line_without_approved_gate_is_refused(self):
        self.propose()
        record = self.state()["hubspot"]
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": "connected", "timestamp": "t", "server": "hubspot",
                                 "gate_id": record["gate_id"], "config_hash": record["config_hash"]}) + "\n")
        code, out, _ = self.reg("check-tool", "--tool", "mcp__hubspot__get_deal")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", out)


class LiteralSecretShapeTests(WorkspaceCase):
    HEX = "9f86d081884c7d659a2feaa0c55ad015"

    def stdio(self, *tail, env=()):
        extra = [x for e in env for x in ("--env", e)]
        return self.reg("propose", "--server", "k", "--transport", "stdio", "--scope", "local", "--read-tools", "a",
                        *extra, "--", *tail)

    def test_review_shapes_are_rejected(self):
        self.assertEqual(self.stdio("npx", "-y", "pkg@1.0.0", env=[f"K=${{K:-{self.HEX}}}"])[0], 1)
        self.assertEqual(self.stdio("npx", "-y", "pkg@1.0.0", "--api-key", self.HEX)[0], 1)
        self.assertEqual(self.stdio("npx", "-y", "pkg@1.0.0", "--password=Hunter2Hunter2!")[0], 1)
        self.assertEqual(self.stdio("npx", "-y", "pkg@1.0.0", "--token", "shortone")[0], 1)
        self.assertEqual(self.reg("propose", "--server", "k", "--transport", "http", "--url",
                                  f"https://mcp.example.com/s/{self.HEX}/mcp", "--scope", "local",
                                  "--read-tools", "a")[0], 1)
        self.assertEqual(self.propose("--header", "X-Api-Key: ${K:-abcdEFGH1234abcd}")[0], 1)
        self.assertEqual(self.state(), {})
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), "a"):
            pass
        with open(os.path.join(self.ws, "memory", "mcp_connections.jsonl"), encoding="utf-8") as fh:
            self.assertNotIn(self.HEX, fh.read())

    def test_plain_defaults_and_reference_flags_still_pass(self):
        code, _, err = self.stdio("npx", "-y", "pkg@1.0.0", "--api-key", "${PKG_KEY}", "--region", "eu",
                                  env=["REGION=${REGION:-us-east-1}", "MODE=${MODE:-production}"])
        self.assertEqual(code, 0, err)

    def test_redact_covers_the_new_shapes(self):
        out = reg.redact(f"id {self.HEX} --api-key abcd1234 --password=Hunter2 ok ${{KEY}} --api-key ${{KEY}}")
        self.assertNotIn(self.HEX, out)
        self.assertNotIn("abcd1234", out)
        self.assertNotIn("Hunter2", out)
        self.assertIn("--api-key ${KEY}", out)


class LauncherPinningTests(WorkspaceCase):
    def stdio(self, server, *tail, extra=()):
        return self.reg("propose", "--server", server, "--transport", "stdio", "--scope", "local",
                        "--read-tools", "a", *extra, "--", *tail)

    def test_unpinned_launchers_fail_closed(self):
        for i, tail in enumerate((["pnpm", "dlx", "some-mcp"], ["npm", "exec", "-y", "some-mcp"],
                                  ["cmd", "/s", "/c", "npx", "-y", "some-mcp"], ["docker", "run", "-i", "mcp/some"],
                                  ["docker", "run", "-i", "mcp/some:latest"], ["cmd", "/c", "npx -y some-mcp"],
                                  ["yarn", "dlx", "some-mcp"], ["pipx", "run", "some-mcp"], ["node", "server.js"],
                                  ["powershell", "-c", "npx some-mcp"])):
            code, _, err = self.stdio(f"s{i}", *tail)
            self.assertEqual(code, 1, tail)
        self.assertEqual(self.state(), {})

    def test_pinned_launchers_pass(self):
        digest = "sha256:" + "a" * 64
        for i, tail in enumerate((["pnpm", "dlx", "some-mcp@1.0.0"], ["npm", "exec", "--package=some-mcp@1.0.0", "--", "some"],
                                  ["cmd", "/s", "/c", "npx -y some-mcp@2.0.1"], ["docker", "run", "-i", "--rm", "-e", "K",
                                  f"mcp/some@{digest}"], ["docker", "run", "-i", "ghcr.io/acme/some:1.2.0"],
                                  ["pipx", "run", "some-mcp==1.0"], ["uv", "tool", "run", "some-mcp==1.0"])):
            code, _, err = self.stdio(f"p{i}", *tail)
            self.assertEqual(code, 0, f"{tail}: {err}")

    def test_unpinned_ok_is_explicit_hashed_and_on_the_card(self):
        code, out, err = self.stdio("local", "node", "server.js", extra=["--unpinned-ok"])
        self.assertEqual(code, 0, err)
        self.assertIn("CHECK:", out)
        self.assertIn("cannot pin", out)
        record = self.state()["local"]
        self.assertTrue(record["unpinned_ok"])
        self.assertEqual(reg.config_hash(record), record["config_hash"])
        flipped = dict(record, unpinned_ok=False)
        self.assertNotEqual(reg.config_hash(flipped), record["config_hash"])


class WriteShapedReadToolTests(WorkspaceCase):
    def test_write_verbs_under_read_tools_are_refused(self):
        code, _, err = self.propose("--read-tools", "search,delete_contact,update_deal,send_email", "--catalog-id", "hubspot")
        self.assertEqual(code, 1)
        for tool in ("delete_contact", "update_deal", "send_email"):
            self.assertIn(tool, err)
        self.assertEqual(self.state(), {})

    def test_confirmed_read_tools_pass_with_a_check_line(self):
        code, out, err = self.propose("--read-tools", "search,run_report", "--confirm-read-tools", "run_report")
        self.assertEqual(code, 0, err)
        self.assertIn("confirmed read-only by the user: run_report", out)

    def test_classifier(self):
        for name in ("delete_contact", "deleteContact", "crm.update", "post_message", "contact_remove", "upsertDeal"):
            self.assertTrue(reg.write_shaped(name), name)
        for name in ("search", "get_post", "list_settings", "get_dataset", "search_crm_objects", "fetch"):
            self.assertFalse(reg.write_shaped(name), name)


class ToolUsageLedgerFixTests(unittest.TestCase):
    """The ledger fixes Builder C owns: docstring usage, _comment, placeholder limits."""

    @classmethod
    def setUpClass(cls):
        try:
            import tool_usage_ledger
        except ImportError as exc:  # pydantic missing on this interpreter
            raise unittest.SkipTest(f"tool_usage_ledger needs pydantic: {exc}")
        cls.tul = tool_usage_ledger

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="tantra_tul_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ledger = os.path.join(self.dir, "tool_usage_log.jsonl")

    def config(self, obj):
        path = os.path.join(self.dir, "budget.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return path

    def test_docstring_usage_with_ledger_after_subcommand(self):
        code, _, _ = run(self.tul.main, ["log", "--ledger", self.ledger, "--tool", "hubspot_connector"])
        self.assertEqual(code, 0)
        code, out, _ = run(self.tul.main, ["report", "--ledger", self.ledger])
        self.assertIn("hubspot_connector: 1 calls", out)
        code, _, _ = run(self.tul.main, ["--ledger", self.ledger, "log", "--tool", "x"])
        self.assertEqual(code, 0)

    def test_template_placeholders_are_not_configured_not_ok(self):
        template = os.path.join(REPO, "model-routing", "budget_config.template.json")
        code, out, _ = run(self.tul.main, ["check-budget", "--ledger", self.ledger, "--config", template])
        self.assertEqual(code, 0)
        self.assertIn("NOT CONFIGURED", out)
        self.assertIn("NO LIMITS ENFORCED", out)
        self.assertNotIn("_comment", out)
        code, _, _ = run(self.tul.main, ["check-budget", "--ledger", self.ledger, "--config", template, "--strict"])
        self.assertEqual(code, 1)

    def test_mcp_lines_from_the_guard_count_against_budget(self):
        with open(self.ledger, "w", encoding="utf-8") as fh:
            for _ in range(3):
                fh.write(json.dumps({"tool": "mcp:hubspot", "timestamp": "2099-01-01T00:00:00.00Z", "calls": 1,
                                     "status": "ok", "cost_usd": None, "note": "get_deal"}) + "\n")
        cfg = self.config({"_comment": "x", "mcp:hubspot": {"period_days": 30, "max_calls": 2, "max_cost_usd": None}})
        code, out, _ = run(self.tul.main, ["check-budget", "--ledger", self.ledger, "--config", cfg])
        self.assertEqual(code, 1)
        self.assertIn("mcp:hubspot: 3 calls > max_calls=2", out)
        cfg = self.config({"mcp:hubspot": {"max_calls": 10}})
        code, out, _ = run(self.tul.main, ["check-budget", "--ledger", self.ledger, "--config", cfg])
        self.assertEqual(code, 0)
        self.assertIn("OK -- all 1 tool(s)", out)


if __name__ == "__main__":
    unittest.main()
