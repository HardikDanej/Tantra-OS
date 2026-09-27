"""
Tests for tools/new_workspace.py and the wake-word wiring Builder E put into
the CLAUDE.md template, the agent descriptions, and the unattended prompts.

new_workspace.py writes to three places that must never be real during a
test: the target workspace, the repo-level `.workspaces/registry.json`, and
whatever `tools/install_hooks.py` touches. Every test therefore points
REGISTRY_PATH at a temp file and INSTALL_HOOKS_PATH at a fake installer that
only records its argv, and setUp asserts the temp location as a tripwire.
The one test that runs the real installer targets a temp workspace, whose
`.claude/settings.local.json` is the only file workspace scope writes.

The wiring tests read repo files as text: those edits are the contract the
activation hook and the evals depend on, and a later edit that silently
drops the activation clause from one entry point would otherwise go unseen.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import new_workspace as nw

REPO = Path(__file__).resolve().parents[2]
AGENTS = REPO / ".claude" / "agents"
REAL_INSTALLER = REPO / "tools" / "install_hooks.py"

ACTIVATION = ("Only dispatched after the user has activated Tantra in this session with the wake word "
              "'mk' / 'MK agent' (a hook reports 'Tantra marketing OS is active'); never auto-delegated "
              "otherwise — the product name 'Tantra' alone is not an activation.")
ENTRY_POINTS = [
    "chief-marketing-orchestrator", "brand-creative-orchestrator", "product-marketing-gtm-orchestrator",
    "market-research-insights-orchestrator", "pr-corporate-communications-orchestrator",
    "enterprise-marketing-orchestrator", "cross-system-dispatch-bridge",
]
DOMAIN_PARENTS = {
    "brand-strategy-architecture-agent": "brand-creative-orchestrator",
    "content-marketing-editorial-strategy-agent": "brand-creative-orchestrator",
    "organic-social-community-building-agent": "brand-creative-orchestrator",
    "go-to-market-launch-strategy-agent": "product-marketing-gtm-orchestrator",
    "commercial-assets-sales-enablement-agent": "product-marketing-gtm-orchestrator",
    "pricing-packaging-customer-adoption-agent": "product-marketing-gtm-orchestrator",
    "primary-research-customer-discovery-agent": "market-research-insights-orchestrator",
    "competitive-market-intelligence-agent": "market-research-insights-orchestrator",
    "marketing-analytics-attribution-modeling-agent": "market-research-insights-orchestrator",
    "media-relations-earned-editorial-agent": "pr-corporate-communications-orchestrator",
    "corporate-reputation-issues-crisis-management-agent": "pr-corporate-communications-orchestrator",
    "events-experiential-marketing-agent": "pr-corporate-communications-orchestrator",
}

FAKE_INSTALLER = """\
import json, sys
from pathlib import Path
Path(__file__).with_suffix(".argv.json").write_text(json.dumps(sys.argv), encoding="utf-8")
print("fake installer: wrote hooks")
sys.exit({code})
"""


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = nw.main(argv)
    return code, out.getvalue(), err.getvalue()


def frontmatter_description(name):
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines()[:10] if line.startswith("description:")]
    return lines[0] if lines else ""


class _WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tantra_ws_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.assertTrue(str(self.tmp).startswith(tempfile.gettempdir()))
        self.ws = self.tmp / "acme"
        self.registry = self.tmp / "registry.json"
        self.installer = self.tmp / "fake_install_hooks.py"
        self.write_installer(0)
        for attr, value in (("REGISTRY_PATH", self.registry), ("INSTALL_HOOKS_PATH", self.installer)):
            patcher = mock.patch.object(nw, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_installer(self, code):
        self.installer.write_text(FAKE_INSTALLER.format(code=code), encoding="utf-8")

    def installer_argv(self):
        recorded = self.installer.with_suffix(".argv.json")
        return json.loads(recorded.read_text(encoding="utf-8")) if recorded.exists() else None

    def scaffold(self, *extra):
        return run_main([str(self.ws), "--name", "Acme Co", *extra])


class ScaffoldTests(_WorkspaceCase):
    def test_fresh_workspace_gets_every_directory_and_an_empty_connector_ledger(self):
        code, out, _ = self.scaffold()
        self.assertEqual(code, 0)
        for rel in ("brand", "memory", "memory/evidence/raw", ".memory", "deliverables"):
            self.assertTrue((self.ws / rel).is_dir(), rel)
        ledger = self.ws / "memory" / "mcp_connections.jsonl"
        self.assertTrue(ledger.is_file())
        self.assertEqual(ledger.read_bytes(), b"")
        self.assertIn("deliverables/", out)
        self.assertIn("memory/mcp_connections.jsonl", out)

    def test_company_json_and_claude_md_are_rendered(self):
        self.scaffold()
        company = json.loads((self.ws / "brand" / "company.json").read_text(encoding="utf-8"))
        self.assertEqual((company["name"], company["slug"]), ("Acme Co", "acme-co"))
        claude = (self.ws / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("# Acme Co — Marketing Workspace"))
        self.assertNotIn("{{COMPANY_NAME}}", claude)

    def test_rerun_never_truncates_the_connector_ledger(self):
        self.scaffold()
        ledger = self.ws / "memory" / "mcp_connections.jsonl"
        ledger.write_text('{"event": "connected", "server": "hubspot"}\n', encoding="utf-8")
        code, out, _ = self.scaffold()
        self.assertEqual(code, 0)
        self.assertIn("hubspot", ledger.read_text(encoding="utf-8"))
        self.assertNotIn("Created:", out)

    def test_ensure_scaffold_reports_only_what_it_created(self):
        (self.ws / "brand").mkdir(parents=True)
        created = nw.ensure_scaffold(self.ws)
        self.assertNotIn("brand/", created)
        self.assertIn("deliverables/", created)
        self.assertEqual(nw.ensure_scaffold(self.ws), [])

    def test_existing_claude_md_is_left_alone_without_the_refresh_flag(self):
        self.scaffold()
        claude = self.ws / "CLAUDE.md"
        claude.write_text("# hand edited\n", encoding="utf-8")
        code, out, _ = self.scaffold()
        self.assertEqual(code, 0)
        self.assertEqual(claude.read_text(encoding="utf-8"), "# hand edited\n")
        self.assertIn("--refresh-claude-md", out)
        self.assertEqual(list(self.ws.glob("CLAUDE.md.bak-*")), [])

    def test_registry_collision_is_still_refused_before_anything_is_created(self):
        self.scaffold()
        other = self.tmp / "other"
        code, _, err = run_main([str(other), "--name", "Acme Co"])
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)
        self.assertFalse(other.exists())

    def test_registry_is_written_to_the_patched_path_only(self):
        self.scaffold()
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(Path(registry["acme-co"]["path"]), self.ws.resolve())

    def test_docstring_uses_wake_word_wording(self):
        doc = nw.__doc__
        self.assertNotIn("route everything through the Orchestrator first", doc)
        self.assertIn("wake word", doc)
        self.assertIn("--refresh-claude-md", doc)
        self.assertIn("--no-hooks", doc)


class HookInstallTests(_WorkspaceCase):
    def test_installer_runs_with_this_interpreter_in_workspace_scope(self):
        code, out, _ = self.scaffold()
        self.assertEqual(code, 0)
        argv = self.installer_argv()
        self.assertIsNotNone(argv, "installer was not invoked")
        self.assertEqual(argv[1:], ["workspace", str(self.ws.resolve())])
        self.assertIn("Tantra workspace hooks installed", out)
        self.assertIn("fake installer: wrote hooks", out)

    def test_no_hooks_skips_the_installer(self):
        code, out, _ = self.scaffold("--no-hooks")
        self.assertEqual(code, 0)
        self.assertIsNone(self.installer_argv())
        self.assertIn("skipped (--no-hooks)", out)

    def test_missing_installer_only_warns(self):
        self.installer.unlink()
        code, out, err = self.scaffold()
        self.assertEqual(code, 0)
        self.assertIn("WARNING", err)
        self.assertIn("NOT installed", err)
        self.assertIn("workspace", err)
        self.assertIn("Workspace ready", out)

    def test_failing_installer_only_warns_and_shows_its_output(self):
        self.write_installer(1)
        code, out, err = self.scaffold()
        self.assertEqual(code, 0)
        self.assertIn("exited 1", err)
        self.assertIn("fake installer: wrote hooks", err)
        self.assertNotIn("hooks installed", out)

    def test_install_helper_reports_success_as_a_bool(self):
        self.ws.mkdir()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(nw.install_workspace_hooks(self.ws))
            self.write_installer(3)
            self.assertFalse(nw.install_workspace_hooks(self.ws))

    @unittest.skipUnless(REAL_INSTALLER.is_file(), "tools/install_hooks.py not present")
    def test_real_installer_writes_only_the_temp_workspace_settings(self):
        with mock.patch.object(nw, "INSTALL_HOOKS_PATH", REAL_INSTALLER):
            code, out, err = self.scaffold()
        self.assertEqual(code, 0, out + err)
        settings = self.ws / ".claude" / "settings.local.json"
        self.assertTrue(settings.is_file(), out + err)
        self.assertIn("tantra_hook.py", settings.read_text(encoding="utf-8"))
        self.assertIn("Tantra workspace hooks installed", out)


class RefreshClaudeMdTests(_WorkspaceCase):
    OLD = (
        "# Acme Co — Marketing Workspace\n\n"
        "## Routing — always through one of the five orchestrators\n\nold routing rule\n\n"
        "## Company-specific boundaries\n\n- Never name CompetitorX.\n- Spend ceiling $5k.\n\n"
        "## Our own notes\n\nhand-added section\n"
    )

    def prepare(self):
        self.scaffold("--no-hooks")
        claude = self.ws / "CLAUDE.md"
        claude.write_text(self.OLD, encoding="utf-8")
        return claude

    def test_refresh_backs_up_byte_for_byte_and_rerenders(self):
        claude = self.prepare()
        old_bytes = claude.read_bytes()
        code, out, _ = self.scaffold("--no-hooks", "--refresh-claude-md")
        self.assertEqual(code, 0)
        backups = list(self.ws.glob("CLAUDE.md.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertRegex(backups[0].name, r"^CLAUDE\.md\.bak-\d{8}T\d{6}Z$")
        self.assertEqual(backups[0].read_bytes(), old_bytes)
        new = claude.read_text(encoding="utf-8")
        self.assertIn("## Activation — Tantra runs only on the wake word", new)
        self.assertNotIn("old routing rule", new)
        self.assertIn("backed up", out)

    def test_refresh_carries_boundaries_and_names_dropped_sections(self):
        claude = self.prepare()
        _, out, _ = self.scaffold("--no-hooks", "--refresh-claude-md")
        new = claude.read_text(encoding="utf-8")
        boundaries = nw.extract_section(new, nw.BOUNDARIES_HEADING)
        self.assertIn("Never name CompetitorX.", boundaries)
        self.assertNotIn("None recorded yet", boundaries)
        self.assertIn("## Connected tools (MCP)", new)
        self.assertIn("## Our own notes", out)
        self.assertNotIn("hand-added section", new)

    def test_refresh_without_boundaries_section_says_so(self):
        claude = self.prepare()
        claude.write_text("# Acme\n\n## Something\n\ntext\n", encoding="utf-8")
        _, out, _ = self.scaffold("--no-hooks", "--refresh-claude-md")
        self.assertIn("no \"## Company-specific boundaries\" section", out)
        self.assertIn("None recorded yet", claude.read_text(encoding="utf-8"))

    def test_refresh_on_a_workspace_without_claude_md_just_writes_it(self):
        self.ws.mkdir()
        code, _, _ = self.scaffold("--no-hooks", "--refresh-claude-md")
        self.assertEqual(code, 0)
        self.assertTrue((self.ws / "CLAUDE.md").is_file())
        self.assertEqual(list(self.ws.glob("CLAUDE.md.bak-*")), [])

    def test_backup_names_never_collide(self):
        claude = self.prepare()
        now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
        with contextlib.redirect_stdout(io.StringIO()):
            first = nw.refresh_claude_md(claude, "Acme Co", now=now)
            second = nw.refresh_claude_md(claude, "Acme Co", now=now)
        self.assertEqual(first.name, "CLAUDE.md.bak-20260925T120000Z")
        self.assertEqual(second.name, "CLAUDE.md.bak-20260925T120000Z-1")

    def test_section_helpers_ignore_headings_inside_code_fences(self):
        text = "## A\n\n```\n## not a heading\n```\n\n## B\n\nb\n"
        self.assertEqual(nw.level2_headings(text), ["## A", "## B"])
        self.assertIn("## not a heading", nw.extract_section(text, "## A"))
        self.assertEqual(nw.replace_section(text, "## B", "new"), text.replace("\nb\n", "new\n"))


class TemplateWiringTests(unittest.TestCase):
    def setUp(self):
        self.text = nw.TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_routing_applies_only_when_active(self):
        self.assertIn("Tantra routing applies only while Tantra is active", self.text)
        self.assertIn("never dispatch a Tantra agent", self.text)
        self.assertIn('starting the message with "mk"', self.text)
        self.assertIn('"Tantra" on its own is not a wake word', self.text)
        self.assertNotIn("always through one of the five orchestrators", self.text)

    def test_all_six_entry_points_are_routable(self):
        for name in ENTRY_POINTS[:-1]:
            self.assertRegex(self.text, rf"\| `{name}` \|", name)

    def test_connectors_deliverables_and_ownership_sections(self):
        self.assertIn("## Connected tools (MCP)", self.text)
        self.assertIn("memory/mcp_connections.jsonl", self.text)
        self.assertIn('"mk connect <app>"', self.text)
        self.assertIn("## Deliverables & provenance", self.text)
        self.assertIn("deliverables/<YYYY-MM-DD>-<slug>/", self.text)
        self.assertIn("provenance.py verify-file <path>", self.text)
        self.assertIn("Tantra is proprietary to Hardik Danej; see LICENSE", self.text)


class AgentWiringTests(unittest.TestCase):
    def test_every_entry_point_carries_the_activation_clause(self):
        for name in ENTRY_POINTS:
            with self.subTest(agent=name):
                self.assertIn(ACTIVATION, frontmatter_description(name))

    def test_chief_no_longer_self_activates(self):
        self.assertNotIn("Activates on any request", frontmatter_description("chief-marketing-orchestrator"))

    def test_bridge_keeps_its_dispatch_restriction(self):
        self.assertIn("never from a domain agent, a sub-agent, or the user directly",
                      frontmatter_description("cross-system-dispatch-bridge"))

    def test_domain_agents_accept_only_their_orchestrator(self):
        for name, parent in DOMAIN_PARENTS.items():
            with self.subTest(agent=name):
                guard = f"Only accepts dispatches from the {parent}, never auto-delegated from a raw request."
                self.assertIn(guard, frontmatter_description(name))

    def test_descriptions_stay_single_line_quoted_strings(self):
        for name in ENTRY_POINTS + list(DOMAIN_PARENTS):
            with self.subTest(agent=name):
                self.assertRegex(frontmatter_description(name), r'^description: ".*"$')

    def test_orchestrator_bodies_mention_sentinels_connectors_and_seal(self):
        for name in ENTRY_POINTS:
            text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            with self.subTest(agent=name):
                self.assertIn("Tantra sentinels", text)
                self.assertIn("mcp_connection", text)
                self.assertIn("mcp_write_connection", text)
                self.assertIn("tantra-connect", text)
                self.assertIn("deliverables/<YYYY-MM-DD>-<slug>/", text)
                self.assertIn("provenance.py verify-file <path>", text)
                self.assertIn("never describe a deliverable as human-only", text)

    def test_agent_files_keep_consistent_line_endings(self):
        for name in ENTRY_POINTS + list(DOMAIN_PARENTS):
            raw = (AGENTS / f"{name}.md").read_bytes()
            with self.subTest(agent=name):
                crlf = raw.count(b"\r\n")
                self.assertIn(crlf, (0, raw.count(b"\n")))


class UnattendedPromptTests(unittest.TestCase):
    def test_competitor_scheduled_prompt_starts_with_the_wake_word(self):
        text = (REPO / "marketing-os-infra" / "05-competitor-monitoring" / "scheduled_prompt.md").read_text(
            encoding="utf-8")
        prompt = text.split("\n---", 1)[1].strip()
        self.assertTrue(re.match(r"mk\s", prompt), prompt[:40])
        self.assertIn("TANTRA_ACTIVE=1", text)

    def test_scheduled_workflows_document_activation(self):
        for wf in ("01-campaign-intelligence", "02-seo-content-factory", "03-brand-launch-suite",
                   "04-hubspot-revenue-agent"):
            text = (REPO / "workflows" / wf / "orchestration.md").read_text(encoding="utf-8")
            with self.subTest(workflow=wf):
                self.assertIn("TANTRA_ACTIVE=1", text)
                self.assertRegex(text, r'"mk run ')

    def test_the_activation_hook_actually_fires_on_these_prompts(self):
        hooks_dir = str(REPO / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        try:
            from tantra_core.activation import match_wake
        except ImportError as exc:
            self.skipTest(f"activation module unavailable: {exc}")
        text = (REPO / "marketing-os-infra" / "05-competitor-monitoring" / "scheduled_prompt.md").read_text(
            encoding="utf-8")
        prompts = [text.split("\n---", 1)[1].strip(), "mk run brand foundation for Acme",
                   "mk run the weekly campaign intelligence diagnostic"]
        for prompt in prompts:
            with self.subTest(prompt=prompt[:40]):
                self.assertEqual(match_wake(prompt)[0], "on")


if __name__ == "__main__":
    unittest.main()
