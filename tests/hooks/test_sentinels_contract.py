"""Contract: missing output-contract fields on domain/sub agents are fixed in-run, once."""
import unittest

from tests.hooks.test_sentinels_common import GOOD_OUTPUT, SentinelCase

ANALYSIS = "Analysis: " + "the crawl shows duplicate titles on product templates. " * 8


class ContractTests(SentinelCase):
    def stop(self, message, agent_type="technical-seo-subagent", agent_id="a1", active=False):
        from tantra_core import sentinels

        return sentinels.handle(self.ctx("SubagentStop", agent_id=agent_id, agent_type=agent_type,
                                         last_assistant_message=message, stop_hook_active=active)) or []

    def blocks(self, results):
        return [r.block for r in results if r.block]

    def handback(self, message, agent_id="a1", agent_type="technical-seo-subagent"):
        from tantra_core import sentinels

        sentinels.handle(self.ctx("PostToolUse", tool_name="SubagentHandback", agent_id=agent_id,
                                  agent_type=agent_type, tool_input={"message": message}))

    def test_handback_report_satisfies_the_contract(self):
        """Auto mode (v2.1.271+): the report arrives via SubagentHandback, the closing text is short."""
        self.handback(GOOD_OUTPUT)
        self.assertEqual(self.blocks(self.stop("Handed back the report to the parent.")), [])
        self.assertTrue(self.ledger()[-1]["contract_ok"])
        self.assertNotIn("contract_block", self.sentinel_actions())

    def test_handback_missing_field_is_fixed_by_closing_text(self):
        self.handback(ANALYSIS + "\nCONFIDENCE: medium -- sampled 40 pages")
        block = self.blocks(self.stop("Handed back."))[0]
        self.assertIn("missing GAPS", block)
        self.assertNotIn("too short", block)
        # the block keeps the hand-back, so the fixed stop is judged on report + closing line
        self.stop("GAPS: no Search Console access", active=True)
        self.assertTrue(self.ledger()[-1]["contract_ok"])

    def test_complete_response_passes(self):
        self.assertEqual(self.blocks(self.stop(GOOD_OUTPUT)), [])
        self.assertTrue(self.ledger()[-1]["contract_ok"])

    def test_missing_field_blocks_with_only_the_missing_line(self):
        block = self.blocks(self.stop(ANALYSIS + "\nCONFIDENCE: medium -- sampled 40 pages"))[0]
        self.assertIn("missing GAPS", block)
        self.assertIn("does not need to be redone", block)
        self.assertNotIn("CONFIDENCE:", block.split("e.g.")[0])
        stop = [r for r in self.ledger() if r["ev"] == "stop"][-1]
        self.assertFalse(stop["contract_ok"])
        self.assertEqual(stop["contract_missing"], ["GAPS"])

    def test_registry_fields_are_used(self):
        block = self.blocks(self.stop(GOOD_OUTPUT, agent_type="seo-agent"))[0]
        self.assertIn("CITATION_CHECK", block)

    def test_markdown_labels_count(self):
        text = ANALYSIS + "\n**CONFIDENCE:** high -- checked\n- **GAPS**: none material\n"
        self.assertEqual(self.blocks(self.stop(text)), [])

    def test_short_response_blocks(self):
        block = self.blocks(self.stop("CONFIDENCE: low\nGAPS: all"))[0]
        self.assertIn("too short", block)

    def test_only_one_block_per_agent_and_never_when_stop_hook_active(self):
        first = self.blocks(self.stop(ANALYSIS))
        second = self.blocks(self.stop(ANALYSIS))
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(self.blocks(self.stop(ANALYSIS, agent_id="a2", active=True)), [])

    def test_entry_and_bridge_are_never_blocked(self):
        self.assertEqual(self.blocks(self.stop("ok", agent_type="chief-marketing-orchestrator")), [])
        self.assertEqual(self.blocks(self.stop("ok", agent_type="cross-system-dispatch-bridge")), [])

    def test_assist_mode_turns_block_into_note(self):
        self.config(contract={"mode": "assist"})
        results = self.stop(ANALYSIS)
        self.assertEqual(self.blocks(results), [])
        self.assertIn("missing CONFIDENCE, GAPS", results[0].context)

    def test_estimate_uses_meter_tokens_when_transcript_exists(self):
        self.write_agent_transcript("a1")
        self.stop(ANALYSIS)
        row = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "contract_block"][0]
        self.assertEqual(row["est_tokens_avoided"], 800 + 200 + 2000)

    def test_estimate_falls_back_to_output_chars(self):
        self.stop(ANALYSIS)
        row = [r for r in self.ledger("sentinel.jsonl") if r["action"] == "contract_block"][0]
        self.assertEqual(row["est_tokens_avoided"], len(ANALYSIS) // 4 * 3)


if __name__ == "__main__":
    unittest.main()
