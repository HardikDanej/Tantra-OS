"""
Tests for tools/build_tantra_registry.py.

Why a synthetic agent tree: the real .claude/agents directory (238 files) is
edited by other work, so hierarchy assertions run against a small temp tree
whose descriptions reuse the real phrasing patterns ("Only accepts
dispatches from the SEO Agent (...)", "Sits under the
**brand-creative-orchestrator**", "one of the five top-level
orchestrators"), so parent resolution is exercised on the shapes it meets in
production. A separate class checks invariants of the real tree. The
write_agents() fixture is also used by test_install_hooks.
"""

import os
import tempfile

SYSTEM_ORCHESTRATORS = (
    "chief-marketing-orchestrator",
    "brand-creative-orchestrator",
    "product-marketing-gtm-orchestrator",
    "market-research-insights-orchestrator",
    "pr-corporate-communications-orchestrator",
)

CONTRACT_BODY = "## Output\nCONFIDENCE: high\nCITATION_CHECK: done\nGAPS: none\n"

AGENTS = {
    **{
        name: (f"Top-level orchestrator for {name}.", "Read, Agent", "Routes work. Children: see below.\n")
        for name in SYSTEM_ORCHESTRATORS
    },
    "enterprise-marketing-orchestrator": (
        "The sixth top-level entry point for holistic asks.", "Read, Agent",
        "Dispatches cross-system-dispatch-bridge when needed.\n",
    ),
    "cross-system-dispatch-bridge": (
        "Only accepts dispatches from one of the five top-level orchestrators, or from "
        "`enterprise-marketing-orchestrator` (the sixth top-level entry point).",
        "Read, Agent", "Bridge.\n",
    ),
    "seo-agent": (
        "Domain agent owning organic search. Only accepts dispatches from the Chief Marketing Orchestrator.",
        "Read, Grep, Agent", "Sub-agents: technical-seo-subagent.\n" + CONTRACT_BODY,
    ),
    "growth-ops-cro-agent": (
        "Domain agent for conversion. Only accepts dispatches from the Chief Marketing Orchestrator, and only at Step 4.",
        "Read, Task", "Sub-agents: landing-page-subagent.\n" + CONTRACT_BODY,
    ),
    "revenue-crm-agent": (
        "Domain agent for lifecycle. Only accepts dispatches from the Chief Marketing Orchestrator.",
        "Read, Agent", "Sub-agents: churn-subagent.\nCONFIDENCE: x\nGAPS: y\n",
    ),
    "competitor-red-team-agent": (
        "Attacks the plan. Only accepts dispatches from the Chief Marketing Orchestrator — never invoked directly.",
        "Read, Agent", "Sub-agents: pricing-counter-strategy-subagent.\n" + CONTRACT_BODY,
    ),
    "brand-strategy-architecture-agent": (
        "Domain agent owning brand strategy. Sits under the **brand-creative-orchestrator**, alongside its two "
        "sibling domain agents.",
        "Read, Agent", "Sub-agents: naming-subagent.\n**CONFIDENCE**: x\n- GAPS: y\n",
    ),
    "technical-seo-subagent": (
        "Crawls sites. Only accepts dispatches from the SEO Agent (Organic Acquisition & Discovery), never the "
        "Chief Orchestrator or another sub-agent directly.",
        "Read, WebFetch", CONTRACT_BODY,
    ),
    "landing-page-subagent": (
        "Only accepts dispatches from the Growth Ops/CRO Agent (Growth Operations & Conversion Rate "
        "Optimization), never the Chief Orchestrator or another sub-agent directly.",
        "Read", "CONFIDENCE: x\nGAPS: y\n",
    ),
    "churn-subagent": (
        "Only accepts dispatches from the Revenue/CRM Agent (Lifecycle, Retention & CRM Marketing), never the "
        "Chief Orchestrator or another sub-agent directly.",
        "Read", "CONFIDENCE: x\nGAPS: y\n",
    ),
    "pricing-counter-strategy-subagent": (
        "Only accepts dispatches from the Competitor Red Team Agent, never the Chief Orchestrator or a sibling "
        "domain/sub-agent directly.",
        "Read", "CONFIDENCE: x\nGAPS: y\n",
    ),
    "naming-subagent": (
        "Only accepts dispatches from the Brand Strategy & Architecture Agent, never a top-level orchestrator "
        "or another sub-agent directly.",
        "Read", "Mentions CONFIDENCE inline but has no field line.\nGAPS: y\n",
    ),
}

CHIEF_BODY = (
    "Dispatches seo-agent, growth-ops-cro-agent, revenue-crm-agent, competitor-red-team-agent, "
    "cross-system-dispatch-bridge.\n"
)


def agent_markdown(name, description, tools, body, crlf=False):
    text = f'---\nname: {name}\ndescription: "{description}"\ntools: {tools}\nmodel: sonnet\n---\n\n{body}'
    return text.replace("\n", "\r\n") if crlf else text


def write_agents(directory=None, agents=None, crlf_names=("seo-agent",)):
    directory = directory or tempfile.mkdtemp(prefix="tantra_agents_")
    os.makedirs(directory, exist_ok=True)
    for name, (description, tools, body) in (agents or AGENTS).items():
        if name == "chief-marketing-orchestrator":
            body = body + CHIEF_BODY
        if name == "brand-creative-orchestrator":
            body = body + "Dispatches brand-strategy-architecture-agent.\n"
        with open(os.path.join(directory, name + ".md"), "w", encoding="utf-8", newline="") as fh:
            fh.write(agent_markdown(name, description, tools, body, crlf=name in crlf_names))
    return directory


import contextlib
import io
import json
import shutil
import unittest
from pathlib import Path

import build_tantra_registry as brt

REPO = Path(__file__).resolve().parents[2]
NO_KB = os.path.join(tempfile.gettempdir(), "tantra-no-such-kb-dir")


def build_into(tmp, agents_dir):
    out = Path(tmp) / "registry.json"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        code = brt.main(["--agents-dir", str(agents_dir), "--out", str(out), "--kb-dir", NO_KB])
    return code, out


class Frontmatter(unittest.TestCase):
    def test_quoted_crlf_bom_and_continuations(self):
        text = '﻿---\r\nname: x-agent\r\ndescription: "Says \\"hi\\" to you"\r\ntools: Read, Agent\r\n---\r\nBody\r\n'
        fields, body = brt.parse_frontmatter(text)
        self.assertEqual(fields["name"], "x-agent")
        self.assertEqual(fields["description"], 'Says "hi" to you')
        self.assertEqual(body.strip(), "Body")
        folded, _ = brt.parse_frontmatter("---\nname: y\ndescription: >\n  one\n  two\n---\n")
        self.assertEqual(folded["description"], "one two")
        single, _ = brt.parse_frontmatter("---\nname: z\ndescription: 'it''s fine'\n---\n")
        self.assertEqual(single["description"], "it's fine")

    def test_no_frontmatter(self):
        self.assertEqual(brt.parse_frontmatter("# just markdown")[0], {})
        self.assertEqual(brt.parse_frontmatter("---\nname: open\n")[0], {})

    def test_parse_tools(self):
        self.assertEqual(brt.parse_tools("Read, Grep, Agent"), ["Read", "Grep", "Agent"])
        self.assertEqual(brt.parse_tools("[Read, 'Task']"), ["Read", "Task"])
        self.assertEqual(brt.parse_tools(""), [])


class ParentResolution(unittest.TestCase):
    NAMES = set(AGENTS)

    def resolve(self, phrase, exclude="x"):
        return brt.resolve_phrase(phrase, self.NAMES, exclude)

    def test_display_names(self):
        cases = {
            "the Growth Ops/CRO Agent (Growth Operations & Conversion Rate Optimization)": ["growth-ops-cro-agent"],
            "the Revenue/CRM Agent (Lifecycle, Retention & CRM Marketing)": ["revenue-crm-agent"],
            "the Brand Strategy & Architecture Agent": ["brand-strategy-architecture-agent"],
            "the Competitor Red Team Agent": ["competitor-red-team-agent"],
            "the SEO Agent (Organic Acquisition & Discovery)": ["seo-agent"],
            "the Chief Marketing Orchestrator": ["chief-marketing-orchestrator"],
            "the **brand-creative-orchestrator**": ["brand-creative-orchestrator"],
        }
        for phrase, want in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.resolve(phrase), want)

    def test_group_phrase_with_alternative(self):
        got = self.resolve("one of the five top-level orchestrators, or from `enterprise-marketing-orchestrator` "
                           "(the sixth top-level entry point)", exclude="cross-system-dispatch-bridge")
        self.assertEqual(sorted(got), sorted(SYSTEM_ORCHESTRATORS + ("enterprise-marketing-orchestrator",)))

    def test_unknown_or_ambiguous_resolves_to_nothing(self):
        self.assertEqual(self.resolve("the Quantum Widget Agent"), [])
        self.assertEqual(self.resolve(""), [])

    def test_never_resolves_to_self(self):
        self.assertEqual(self.resolve("the SEO Agent", exclude="seo-agent"), [])

    def test_description_sentences_stop_at_never_clause(self):
        desc = AGENTS["technical-seo-subagent"][0]
        self.assertEqual(brt.description_parents("technical-seo-subagent", desc, self.NAMES), ["seo-agent"])


class BuildSynthetic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tantra_reg_")
        self.agents_dir = write_agents(os.path.join(self.tmp, "agents"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def build(self):
        registry, unresolved, _ = brt.build_registry(Path(self.agents_dir), None)
        return registry, unresolved

    def test_tiers_parents_children_and_system(self):
        reg, unresolved = self.build()
        self.assertEqual(unresolved, [])
        agents = reg["agents"]
        self.assertEqual(reg["agent_count"], len(AGENTS))
        self.assertEqual(len(reg["entry_points"]), 6)
        self.assertEqual(agents["chief-marketing-orchestrator"]["tier"], "entry")
        self.assertEqual(agents["chief-marketing-orchestrator"]["parents"], ["main", "cross-system-dispatch-bridge"])
        self.assertEqual(agents["enterprise-marketing-orchestrator"]["parents"], ["main"])
        bridge = agents["cross-system-dispatch-bridge"]
        self.assertEqual(bridge["tier"], "bridge")
        self.assertEqual(len(bridge["parents"]), 6)
        for name in ("seo-agent", "growth-ops-cro-agent", "revenue-crm-agent", "competitor-red-team-agent",
                     "brand-strategy-architecture-agent"):
            self.assertEqual(agents[name]["tier"], "domain", name)
        self.assertEqual(agents["technical-seo-subagent"]["tier"], "sub")
        self.assertEqual(agents["pricing-counter-strategy-subagent"]["parents"], ["competitor-red-team-agent"])
        self.assertEqual(agents["landing-page-subagent"]["parents"], ["growth-ops-cro-agent"])
        self.assertEqual(agents["churn-subagent"]["parents"], ["revenue-crm-agent"])
        self.assertEqual(agents["naming-subagent"]["system"], "brand-creative")
        self.assertEqual(agents["technical-seo-subagent"]["system"], "digital-marketing-growth")
        self.assertEqual(agents["cross-system-dispatch-bridge"]["system"], "cross-system")
        self.assertIn("technical-seo-subagent", agents["seo-agent"]["children"])
        for name, info in agents.items():
            for parent in info["parents"]:
                if parent != "main":
                    self.assertIn(name, agents[parent]["children"])

    def test_agent_tool_and_contract_fields(self):
        agents = self.build()[0]["agents"]
        self.assertTrue(agents["seo-agent"]["has_agent_tool"])
        self.assertTrue(agents["growth-ops-cro-agent"]["has_agent_tool"])
        self.assertFalse(agents["technical-seo-subagent"]["has_agent_tool"])
        self.assertEqual(agents["seo-agent"]["contract_fields"], ["CONFIDENCE", "CITATION_CHECK", "GAPS"])
        self.assertEqual(agents["brand-strategy-architecture-agent"]["contract_fields"], ["CONFIDENCE", "GAPS"])
        self.assertEqual(agents["naming-subagent"]["contract_fields"], ["GAPS"])
        self.assertEqual(agents["chief-marketing-orchestrator"]["contract_fields"], [])
        self.assertEqual(agents["cross-system-dispatch-bridge"]["contract_fields"], [])

    def test_output_is_deterministic(self):
        a, b = self.build()[0], self.build()[0]
        a.pop("generated_at"), b.pop("generated_at")
        self.assertEqual(brt.dumps(a), brt.dumps(b))

    def test_unresolved_parent_fails_the_build(self):
        with open(os.path.join(self.agents_dir, "orphan-subagent.md"), "w", encoding="utf-8") as fh:
            fh.write(agent_markdown("orphan-subagent", "Only accepts dispatches from the Nonexistent Agent.", "Read", ""))
        code, out = build_into(self.tmp, self.agents_dir)
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())
        self.assertIn("orphan-subagent", self.build()[1])

    def test_check_detects_fresh_stale_and_missing(self):
        code, out = build_into(self.tmp, self.agents_dir)
        self.assertEqual(code, 0)
        self.assertEqual(brt.check_registry(out, Path(self.agents_dir), None), (True, []))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brt.main(["--check", "--agents-dir", self.agents_dir, "--out", str(out), "--kb-dir", NO_KB]), 0)

        data = json.loads(out.read_text(encoding="utf-8"))
        data["generated_at"] = "2000-01-01T00:00:00Z"
        out.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(brt.check_registry(out, Path(self.agents_dir), None)[0], "generated_at must be ignored")

        with open(os.path.join(self.agents_dir, "new-subagent.md"), "w", encoding="utf-8") as fh:
            fh.write(agent_markdown("new-subagent", "Only accepts dispatches from the SEO Agent.", "Read", ""))
        fresh, details = brt.check_registry(out, Path(self.agents_dir), None)
        self.assertFalse(fresh)
        self.assertIn("added: new-subagent", details)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(brt.main(["--check", "--agents-dir", self.agents_dir, "--out", str(out), "--kb-dir", NO_KB]), 1)
        self.assertIn("STALE", err.getvalue())

        self.assertFalse(brt.check_registry(Path(self.tmp) / "missing.json", Path(self.agents_dir), None)[0])

    def test_adding_a_knowledge_base_file_does_not_make_it_stale(self):
        kb = Path(self.tmp) / "knowledge-bases"
        kb.mkdir()
        (kb / "seo-knowledge-base.md").write_text("# SEO\n", encoding="utf-8")
        out = Path(self.tmp) / "registry.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brt.main(["--agents-dir", self.agents_dir, "--out", str(out), "--kb-dir", str(kb)]), 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["knowledge_bases"],
                         ["knowledge-bases/seo-knowledge-base.md"])
        (kb / "new-notes.md").write_text("# notes\n", encoding="utf-8")
        self.assertEqual(brt.check_registry(out, Path(self.agents_dir), kb), (True, []))

    def test_missing_agents_dir_is_an_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(brt.main(["--agents-dir", os.path.join(self.tmp, "nope")]), 1)


class RealRepository(unittest.TestCase):
    """Invariants of the real agent tree and the committed registry."""

    @classmethod
    def setUpClass(cls):
        cls.registry, cls.unresolved, _ = brt.build_registry()

    def test_every_agent_resolves_a_parent(self):
        self.assertEqual(self.unresolved, [])
        for name, info in self.registry["agents"].items():
            self.assertTrue(info["parents"], name)
            self.assertIn(info["tier"], ("entry", "bridge", "domain", "sub"))
            self.assertIsNotNone(info["system"], name)

    def test_known_structure(self):
        agents = self.registry["agents"]
        self.assertEqual(sorted(self.registry["entry_points"]), sorted(SYSTEM_ORCHESTRATORS + ("enterprise-marketing-orchestrator",)))
        self.assertEqual(agents["competitor-red-team-agent"]["tier"], "domain")
        self.assertIn("chief-marketing-orchestrator", agents["competitor-red-team-agent"]["parents"])
        self.assertEqual(agents["cross-system-dispatch-bridge"]["tier"], "bridge")
        self.assertEqual(self.registry["agent_count"], len(list((REPO / ".claude" / "agents").glob("*.md"))))

    def test_committed_registry_is_valid_json_with_schema(self):
        path = REPO / ".claude" / "hooks" / "tantra_registry.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("version", "generated_at", "generated_from", "agent_count", "entry_points", "agents"):
            self.assertIn(key, data)
        self.assertEqual(data["version"], 1)


if __name__ == "__main__":
    unittest.main()
