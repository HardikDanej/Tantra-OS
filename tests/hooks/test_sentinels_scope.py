"""Scope: the hook runs scope_router.py on the user's message and enforces its lock."""
import unittest

from tests.hooks.test_sentinels_common import SentinelCase

SEO_PPC = "mk audit example.com for SEO, AI Overviews and paid ads, and build a 6-month SEO + PPC plan"


class ScopeTests(SentinelCase):
    def prompt(self, text):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("UserPromptSubmit", prompt=text))

    def dispatch(self, target, prompt="go", caller="chief-marketing-orchestrator", caller_id="o1"):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("PreToolUse", tool_name="Agent", agent_id=caller_id, agent_type=caller,
                                         tool_input={"subagent_type": target, "prompt": prompt})) or []

    def scope_results(self, results):
        return [r for r in results if r.source == "scope"]

    def test_prompt_records_lock_and_stays_silent(self):
        self.assertIsNone(self.prompt(SEO_PPC))
        from tantra_core import state
        import os
        lock = state.read_json(os.path.join(self.home, "state", self.session, "scope.json"))
        self.assertEqual(lock["confidence"], "high")
        self.assertEqual(lock["domain_agents"], ["ads-paid-media-agent", "seo-agent"])

    def test_in_scope_dispatch_is_allowed(self):
        self.prompt(SEO_PPC)
        self.assertEqual(self.scope_results(self.dispatch("seo-agent")), [])
        self.assertEqual(self.scope_results(self.dispatch("ads-paid-media-agent")), [])

    def test_out_of_scope_domain_agent_is_denied(self):
        self.prompt(SEO_PPC)
        [r] = self.scope_results(self.dispatch("growth-ops-cro-agent"))
        self.assertIn("growth-ops-cro-agent is outside it", r.deny)
        self.assertIn("scope_dependency:", r.deny)

    def test_declared_dependency_is_allowed(self):
        self.prompt(SEO_PPC)
        results = self.dispatch("marketing-strategist-agent",
                                prompt='{"agent": "marketing-strategist-agent"}\nscope_dependency: no brand voice exists yet')
        self.assertEqual(self.scope_results(results), [])

    def test_non_domain_targets_are_not_locked(self):
        self.prompt(SEO_PPC)
        self.assertEqual(self.scope_results(self.dispatch("competitor-red-team-agent")), [])
        self.assertEqual(self.scope_results(self.dispatch("cross-system-dispatch-bridge")), [])

    def test_vague_request_clears_the_lock(self):
        self.prompt(SEO_PPC)
        self.prompt("mk help us grow")
        self.assertEqual(self.scope_results(self.dispatch("growth-ops-cro-agent")), [])

    def test_pasted_text_does_not_set_scope(self):
        self.prompt("mk help us grow\n```\nour PPC and SEO notes\n```")
        self.assertEqual(self.scope_results(self.dispatch("growth-ops-cro-agent")), [])

    def test_only_the_orchestrator_is_locked(self):
        self.prompt(SEO_PPC)
        self.assertEqual(self.scope_results(self.dispatch("growth-ops-cro-agent", caller="seo-agent", caller_id="s1")), [])

    def test_assist_mode_notes_instead_of_denying(self):
        self.config(scope={"mode": "assist"})
        self.prompt(SEO_PPC)
        [r] = self.scope_results(self.dispatch("website-development-agent"))
        self.assertIsNone(r.deny)
        self.assertIn("website-development-agent is outside it", r.context)

    def test_off_mode_does_nothing(self):
        self.config(scope={"mode": "off"})
        self.prompt(SEO_PPC)
        self.assertEqual(self.scope_results(self.dispatch("growth-ops-cro-agent")), [])


if __name__ == "__main__":
    unittest.main()
