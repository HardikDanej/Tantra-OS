"""
Tests for the wake word (tantra_core/activation.py).

Why so many table rows: "mk" is a two-letter token that collides with shell
commands (mkdir), file names (rules.mk), model marks (Mk II), brand initials
and language codes. Every rule change must be checked against both the
phrases that must switch Tantra on and the look-alikes that must not.
"""
import json
import os
import unittest
from unittest import mock

from tests.hooks.helpers import MINI_REGISTRY, activate, make_ctx, payload, run_hook, temp_home
from tantra_core import activation, state

# (prompt, expected kind). The first 24 rows are the research sample set
# (research/trigger.md); "MK Dons" is the documented, accepted false positive
# of the first-word rule.
WAKE_CASES = [
    ("mk audit acme.com's SEO", "on"),
    ("MK agent, run a full audit", "on"),
    ("mk agent: rebrand plan", "on"),
    ("Hey MK agent can you plan our launch", "on"),
    ("mk: pricing tiers for our SaaS", "on"),
    ("MK, what's our crisis plan?", "on"),
    ("mk-agent do a competitor scan", "on"),
    ("/mk launch plan", "on"),
    ("mk", "on"),
    ("run mkdir -p ~/clients/acme", None),
    ("use mktemp for the file", None),
    ("the Makefile includes rules.mk", None),
    ("mk.txt is missing", None),
    ("Mortal Kombat MK11 review", None),
    ("MK Dons vs Milton Keynes", "on"),
    ("Supermarine Spitfire Mk II history", None),
    ("Michael Kors (MK) handbag ad copy", None),
    ("set lang to mk for Macedonian", None),
    ("Tantra repo: fix the README", None),
    ("open the tantra folder", None),
    ("mmk ok", None),
    ("the file `mk agent.md`", None),
    ("mkdocs build", None),
    ("mk-2 prototype", None),
    # more ON
    ("MK", "on"),
    ("Mk; plan the launch", "on"),
    ("@mk draft a press release", "on"),
    ("mk! quick one", "on"),
    ("mk? are you there", "on"),
    ("mk. next step", "on"),
    ("mk—launch plan", "on"),
    ("mk\tfull audit", "on"),
    ("  mk   audit with leading spaces", "on"),
    ("mkagent run the audit", "on"),
    ("MKAGENT run the audit", "on"),
    ("mk_agent run the audit", "on"),
    ("please ask the mk agent to plan Q3", "on"),
    ("Can the Mk Agent look at this?", "on"),
    ("ok mk, run the audit", "on"),
    ("so mk: what next", "on"),
    ("thanks.\nmk agent, continue", "on"),
    # more OFF / never
    ("tantra", None),
    ("TANTRA plan our launch", None),
    ("use tantra to plan the launch", None),
    ("ok MK, run the audit", None),
    ("the mk file is here", None),
    ("mk2 is the codename", None),
    ("mk_file.py needs a fix", None),
    ("see docs/mk agent later", None),
    ("rename x.mk agent", None),
    ("open mk-agent.md", None),
    ("the mkagents list", None),
    ("mk-agentic flows", None),
    ("Spitfire Mk. II", None),
    ("mkdir mk", None),
    ("", None),
    ("hello there", None),
    # quoted / pasted / code never counts
    ("```\nmk agent audit\n```", None),
    ("~~~\nmk audit\n~~~\nwhat does this do?", None),
    ("run `mk agent` in the terminal?", None),
    ("> mk agent, audit everything\nwhat did they mean?", None),
    ('<pasted_content id="1">\nmk agent audit\n</pasted_content id="1">\nsummarise this', None),
    ('<pasted_content id="1">\nhello\n</pasted_content id="1">\nmk agent, summarise it', "on"),
    # switching off
    ("mk off", "off"),
    ("MK OFF", "off"),
    ("mk stop.", "off"),
    ("mk exit!", "off"),
    ("Mk sleep", "off"),
    ("mk agent off", "off"),
    ("  mk off  ", "off"),
    ("please exit mk now", "off"),
    ("stop mk", "off"),
    ("ok quit mk for today", "off"),
    ("mk agent, then stop mk", "off"),
    ("stop mkdir from failing", None),
    ("mk off the record, the launch plan", "on"),
    # review fixes: off phrasings with politeness / other verbs
    ("mk off please", "off"),
    ("mk, turn off", "off"),
    ("mk turn off", "off"),
    ("mk deactivate", "off"),
    ("please mk off", "off"),
    ("mk agent off now", "off"),
    ("turn off mk", "off"),
    ("stop mk-agent", "off"),
    ("don't stop mk agent", "on"),
    ("mkoff", None),
    # review fixes: CRLF code fences (Windows clipboard) end where they end
    ("```\r\nprint(1)\r\n```\r\nmk audit my site", "on"),
    ("```\r\nprint(1)\r\n```\r\nmk off", "off"),
    ("```\r\nmk agent audit\r\n```\r\nwhat is this?", None),
    # review fixes: language-code lists and code identifiers are not wake words
    ("Translate the page into these languages: en, de, mk, sq", None),
    ("locales: en, mk, sr", None),
    ("Supported: mk: Macedonian", None),
    ("ok, mk, run the audit", "on"),
    ("the variable mk_agent is undefined", None),
    ("rename mkAgent to foo", None),
    # review fixes: leading placeholders / mentions / thinking keywords
    ("[Image #1] mk review this ad", "on"),
    ("[Pasted text #2 +12 lines] mk summarise this", "on"),
    ("@src/app.py mk review", "on"),
    ("ultrathink mk plan the launch", "on"),
    ("[Image #1] mk off", "off"),
    ("@mk.md fix the typo", None),
]


class MatchWakeTable(unittest.TestCase):
    def test_table(self):
        self.assertGreaterEqual(len(WAKE_CASES), 40)
        for prompt, want in WAKE_CASES:
            with self.subTest(prompt=prompt):
                kind, rule = activation.match_wake(prompt)
                self.assertEqual(kind, want)
                self.assertEqual(rule is None, want is None)

    def test_rule_names(self):
        self.assertEqual(activation.match_wake("MK agent go")[1], "mk_agent")
        self.assertEqual(activation.match_wake("mk go")[1], "first_word")
        self.assertEqual(activation.match_wake("ok mk, go")[1], "vocative")
        self.assertEqual(activation.match_wake("mk off")[1], "off_phrase")
        self.assertEqual(activation.match_wake("stop mk")[1], "stop_phrase")

    def test_non_string_prompt(self):
        self.assertEqual(activation.match_wake(None), (None, None))
        self.assertEqual(activation.match_wake(42), (None, None))

    def test_strip_quoted_keeps_typed_text(self):
        text = "before `code` after\n> quoted\n```\nfenced\n```\nend"
        out = activation.strip_quoted(text)
        for gone in ("code", "quoted", "fenced"):
            self.assertNotIn(gone, out)
        for kept in ("before", "after", "end"):
            self.assertIn(kept, out)

    def test_unterminated_fence_is_stripped_to_end(self):
        self.assertEqual(activation.match_wake("look:\n```\nmk agent audit"), (None, None))


class _CtxCase(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("TANTRA_ACTIVE", None)
        self.home = temp_home()

    def tearDown(self):
        self.env.stop()

    def ctx(self, event="UserPromptSubmit", registry=MINI_REGISTRY, **fields):
        return make_ctx(payload(event, **fields), home=self.home, registry=registry)

    def history(self):
        path = os.path.join(self.home, "state", "sess-test", "activation.jsonl")
        return [r["event"] for r in state.read_jsonl(path)]

    def write_config(self, section):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"activation": section}, fh)


class PromptHandling(_CtxCase):
    def test_wake_word_activates_and_briefs(self):
        ctx = self.ctx(prompt="mk audit acme.com")
        res = activation.handle(ctx)
        self.assertTrue(ctx.active)
        self.assertEqual(res.system_message, "Tantra: active (wake word detected)")
        self.assertIn("chief-marketing-orchestrator", res.context)
        self.assertIn("enterprise-marketing-orchestrator", res.context)
        self.assertIn("tantra-connect", res.context)
        self.assertIn("mk off", res.context)
        self.assertEqual(self.history(), ["on"])
        row = state.read_jsonl(ctx.activation_path)[0]
        self.assertEqual((row["by"], row["match"]), ("wake_word", "first_word"))

    def test_brief_is_factual_and_short(self):
        brief = activation.ACTIVATION_BRIEF
        self.assertLessEqual(len(brief), 1500)
        self.assertIn("'Tantra' on its own is not a wake word", brief)
        for orchestrator in ("brand-creative-orchestrator", "product-marketing-gtm-orchestrator",
                             "market-research-insights-orchestrator",
                             "pr-corporate-communications-orchestrator", "cross-system-dispatch-bridge"):
            self.assertIn(orchestrator, brief)
        for imperative in ("YOU MUST", "SYSTEM:", "IMPORTANT:", "Ignore"):
            self.assertNotIn(imperative, brief)

    def test_second_wake_word_is_short_and_not_rewritten(self):
        activation.handle(self.ctx(prompt="mk agent, plan"))
        res = activation.handle(self.ctx(prompt="mk again"))
        self.assertEqual(res.context, activation.REPEAT_BRIEF)
        self.assertIsNone(res.system_message)
        self.assertEqual(self.history(), ["on"])

    def test_reminder_while_active(self):
        activate(self.home)
        res = activation.handle(self.ctx(prompt="approve the gate"))
        self.assertEqual(res.context, activation.REMINDER)
        self.assertEqual(self.history(), ["on"])

    def test_reminder_can_be_disabled(self):
        self.write_config({"remind_each_prompt": False})
        activate(self.home)
        self.assertIsNone(activation.handle(self.ctx(prompt="approve the gate")))

    def test_inactive_without_wake_word_is_silent(self):
        ctx = self.ctx(prompt="use tantra to plan the launch")
        self.assertIsNone(activation.handle(ctx))
        self.assertFalse(ctx.active)
        self.assertEqual(self.history(), [])

    def test_off_phrase_deactivates(self):
        activate(self.home)
        ctx = self.ctx(prompt="mk off")
        res = activation.handle(ctx)
        self.assertFalse(ctx.active)
        self.assertEqual(res.system_message, "Tantra: off")
        self.assertIn("now inactive", res.context)
        self.assertEqual(self.history(), ["on", "off"])
        self.assertIsNone(activation.handle(self.ctx(prompt="what's next?")))

    def test_off_when_never_on_is_silent(self):
        # "should we stop mk production?" matches the stop phrase; in a session
        # that was never on it must not claim the user said "mk off".
        for prompt in ("mk stop", "should we stop mk production?"):
            ctx = self.ctx(prompt=prompt)
            self.assertIsNone(activation.handle(ctx))
            self.assertFalse(ctx.active)
        self.assertEqual(self.history(), [])

    def test_off_when_already_off_is_silent(self):
        activate(self.home)
        activation.handle(self.ctx(prompt="mk off"))
        self.assertIsNone(activation.handle(self.ctx(prompt="mk off")))
        self.assertEqual(self.history(), ["on", "off"])

    def test_off_please_switches_off_not_on(self):
        activate(self.home)
        res = activation.handle(self.ctx(prompt="mk off please"))
        self.assertEqual(res.system_message, "Tantra: off")
        self.assertEqual(self.history(), ["on", "off"])

    def test_reactivation_after_off(self):
        activate(self.home)
        activation.handle(self.ctx(prompt="mk off"))
        res = activation.handle(self.ctx(prompt="mk agent, back to work"))
        self.assertEqual(res.system_message, "Tantra: active (wake word detected)")
        self.assertEqual(self.history(), ["on", "off", "on"])

    def test_env_forces_on_once(self):
        os.environ["TANTRA_ACTIVE"] = "1"
        first = activation.handle(self.ctx(prompt="run the weekly monitor"))
        self.assertIn("chief-marketing-orchestrator", first.context)
        self.assertIn("TANTRA_ACTIVE", first.system_message)
        second = activation.handle(self.ctx(prompt="continue"))
        self.assertEqual(second.context, activation.REMINDER)
        rows = state.read_jsonl(os.path.join(self.home, "state", "sess-test", "activation.jsonl"))
        self.assertEqual([(r["event"], r["by"]) for r in rows], [("on", "env")])

    def test_other_events_ignored(self):
        self.assertIsNone(activation.handle(self.ctx(event="PostToolUse", tool_name="Agent")))
        self.assertIsNone(activation.handle(self.ctx(event="PreToolUse", tool_name="Read")))


class DispatchGate(_CtxCase):
    def pre(self, subagent, tool="Agent", key="subagent_type", **fields):
        return self.ctx(event="PreToolUse", tool_name=tool, tool_input={key: subagent, "prompt": "x"}, **fields)

    def test_denies_tantra_agent_when_inactive(self):
        res = activation.handle(self.pre("chief-marketing-orchestrator"))
        self.assertEqual(res.deny, activation.GATE_REASON)
        self.assertIn("'mk'", res.deny)

    def test_task_alias_and_fallback_keys_and_plugin_prefix(self):
        self.assertIsNotNone(activation.handle(self.pre("seo-agent", tool="Task")))
        self.assertIsNotNone(activation.handle(self.pre("seo-agent", key="agent_type")))
        self.assertIsNotNone(activation.handle(self.pre("seo-agent", key="agent")))
        self.assertIsNotNone(activation.handle(self.pre("tantra:SEO-Agent")))

    def test_allows_when_active(self):
        activate(self.home)
        self.assertIsNone(activation.handle(self.pre("chief-marketing-orchestrator")))

    def test_never_gates_foreign_agents(self):
        self.assertIsNone(activation.handle(self.pre("Explore")))
        self.assertIsNone(activation.handle(self.pre("general-purpose")))
        self.assertIsNone(activation.handle(self.ctx(event="PreToolUse", tool_name="Agent", tool_input={})))

    def test_nested_dispatch_inside_tantra_agent_is_not_gated(self):
        self.assertIsNone(activation.handle(
            self.pre("seo-agent", agent_id="a-1", agent_type="chief-marketing-orchestrator")))

    def test_non_tantra_subagent_cannot_bypass_gate(self):
        for parent in ("general-purpose", "Explore"):
            res = activation.handle(self.pre("seo-agent", agent_id="a-1", agent_type=parent))
            self.assertEqual(res.deny, activation.GATE_REASON)
        activate(self.home)
        self.assertIsNone(activation.handle(self.pre("seo-agent", agent_id="a-1", agent_type="general-purpose")))

    def test_other_plugins_agent_is_not_gated(self):
        self.assertIsNone(activation.handle(self.pre("otherplugin:seo-agent")))
        # ...and another plugin's look-alike parent is not a Tantra agent, so it gets no nested pass.
        res = activation.handle(
            self.pre("seo-agent", agent_id="a-1", agent_type="otherplugin:chief-marketing-orchestrator"))
        self.assertEqual(res.deny, activation.GATE_REASON)

    def test_fail_open_when_state_cannot_be_written(self):
        # TANTRA_HOME is a regular file: the wake word can never be recorded,
        # so the gate must not deny what the user just switched on.
        blocker = os.path.join(self.home, "not-a-dir")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("x")
        prompt_ctx = make_ctx(payload("UserPromptSubmit", prompt="mk audit my site"), home=blocker,
                              registry=MINI_REGISTRY)
        self.assertIn("chief-marketing-orchestrator", activation.handle(prompt_ctx).context)
        gate_ctx = make_ctx(payload("PreToolUse", tool_name="Agent",
                                    tool_input={"subagent_type": "chief-marketing-orchestrator"}),
                            home=blocker, registry=MINI_REGISTRY)
        self.assertIsNone(activation.handle(gate_ctx))

    def test_fail_open_without_registry(self):
        self.assertIsNone(activation.handle(self.pre("chief-marketing-orchestrator", registry={})))

    def test_hard_gate_can_be_disabled(self):
        self.write_config({"hard_gate": False})
        self.assertIsNone(activation.handle(self.pre("chief-marketing-orchestrator")))

    def test_dispatch_target(self):
        self.assertEqual(activation.dispatch_target({"subagent_type": " Tantra:Seo-Agent "}), "seo-agent")
        self.assertEqual(activation.dispatch_target({"subagent_type": "Plugin:Seo-Agent"}), "plugin:seo-agent")
        self.assertIsNone(activation.dispatch_target({"subagent_type": "  "}))


class EndToEnd(unittest.TestCase):
    """Through the real dispatcher, exactly as Claude Code spawns it."""

    def test_prompt_then_reminder_then_off(self):
        home = temp_home()
        code, out, _ = run_hook(payload("UserPromptSubmit", prompt="MK agent, audit acme.com"), "prompt", home=home)
        self.assertEqual(code, 0)
        self.assertEqual(out["systemMessage"], "Tantra: active (wake word detected)")
        self.assertIn("chief-marketing-orchestrator", out["hookSpecificOutput"]["additionalContext"])
        _, out, _ = run_hook(payload("UserPromptSubmit", prompt="looks good"), "prompt", home=home)
        self.assertIn(activation.REMINDER, out["hookSpecificOutput"]["additionalContext"])
        _, out, _ = run_hook(payload("UserPromptSubmit", prompt="mk off"), "prompt", home=home)
        self.assertEqual(out["systemMessage"], "Tantra: off")
        code, out, _ = run_hook(payload("UserPromptSubmit", prompt="and now?"), "prompt", home=home)
        self.assertEqual((code, out), (0, None))

    def test_inactive_prompt_prints_nothing(self):
        code, out, err = run_hook(payload("UserPromptSubmit", prompt="use tantra to plan"), "prompt")
        self.assertEqual((code, out), (0, None))

    def test_gate_denies_through_dispatcher(self):
        obj = payload("PreToolUse", tool_name="Task",
                      tool_input={"subagent_type": "chief-marketing-orchestrator", "prompt": "x"})
        code, out, _ = run_hook(obj, "pre")
        self.assertEqual(code, 0)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertEqual(hso["permissionDecisionReason"], activation.GATE_REASON)

    def test_env_active_allows_dispatch(self):
        obj = payload("PreToolUse", tool_name="Agent",
                      tool_input={"subagent_type": "chief-marketing-orchestrator", "prompt": "x"})
        _, out, _ = run_hook(obj, "pre", env={"TANTRA_ACTIVE": "1"})
        decision = ((out or {}).get("hookSpecificOutput") or {}).get("permissionDecision")
        self.assertNotEqual(decision, "deny")


if __name__ == "__main__":
    unittest.main()
