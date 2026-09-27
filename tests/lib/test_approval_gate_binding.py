"""approval_gate.py: the --binding / binding_matches additions, and that existing invocations are unchanged."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(REPO, ".claude", "lib")
SCRIPT = os.path.join(LIB, "approval_gate.py")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import approval_gate  # noqa: E402

CREATE = ["--summary", "Raise FY27 budget", "--what-if-approved", "spend", "--what-if-rejected", "hold",
          "--red-team-verdict", "HOLDS", "--irreversibility-note", "annual commitment"]


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = approval_gate.main(argv)
    return code, out.getvalue(), err.getvalue()


class GateCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="tantra_gate_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ledger = os.path.join(self.dir, "memory", "approval_gates.jsonl")
        self.latest = os.path.join(self.dir, "memory", "latest.json")

    def create(self, gate_id, stakes="annual_budget", binding=None):
        argv = [self.ledger, "create", "--gate-id", gate_id, "--stakes-class", stakes, *CREATE,
                "--latest-json", self.latest]
        if binding:
            argv += ["--binding", binding]
        return run(argv)

    def respond(self, gate_id, decision="approved"):
        return run([self.ledger, "respond", "--gate-id", gate_id, "--decision", decision, "--note", "yes",
                    "--latest-json", self.latest])

    def events(self):
        with open(self.ledger, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class BackwardCompatibilityTests(GateCase):
    def test_existing_create_respond_check_list_unchanged(self):
        code, out, _ = self.create("annual_budget_fy27")
        self.assertEqual(code, 0)
        created = json.loads(out)["created"]
        self.assertNotIn("binding", created)
        self.assertEqual(set(created), {"gate_id", "event", "timestamp", "stakes_class", "summary", "what_if_approved",
                                        "what_if_rejected", "red_team_verdict", "irreversibility_note", "checkpoint_ref"})
        with open(self.latest, encoding="utf-8") as fh:
            self.assertEqual(len(json.load(fh)["pending_approval_gates"]), 1)
        self.assertEqual(self.respond("annual_budget_fy27")[0], 0)
        self.assertEqual(self.respond("annual_budget_fy27")[0], 1)
        code, out, _ = run([self.ledger, "check", "--gate-id", "annual_budget_fy27"])
        self.assertEqual((code, json.loads(out)["current_status"]), (0, "approved"))
        self.assertEqual(run([self.ledger, "check", "--gate-id", "nope"])[0], 1)
        rows = json.loads(run([self.ledger, "list", "--status", "approved"])[1])["gates"]
        self.assertEqual([r["gate_id"] for r in rows], ["annual_budget_fy27"])
        self.assertEqual(approval_gate.get_current_status(__import__("pathlib").Path(self.ledger), "annual_budget_fy27"),
                         "approved")

    def test_every_original_stakes_class_still_accepted(self):
        for i, stakes in enumerate(["annual_budget", "final_creative", "pricing_change", "brand_relaunch",
                                    "ad_platform_write", "crm_write", "product_launch_go",
                                    "research_fielding_commitment", "investor_disclosure", "crisis_response_go",
                                    "labor_relations_action", "government_relations_action",
                                    "cross_system_high_stakes", "other_high_stakes"]):
            self.assertEqual(self.create(f"g{i}", stakes)[0], 0, stakes)

    def test_unknown_stakes_class_still_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            approval_gate.main([self.ledger, "create", "--gate-id", "x", "--stakes-class", "made_up", *CREATE])

    def test_cli_as_subprocess_still_works(self):
        proc = subprocess.run([sys.executable, SCRIPT, self.ledger, "create", "--gate-id", "g", "--stakes-class",
                               "crm_write", *CREATE], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run([sys.executable, SCRIPT, self.ledger, "supersede", "--gate-id", "g"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class BindingTests(GateCase):
    HASH = "a" * 64

    def test_new_mcp_stakes_classes_and_binding_stored_on_pending_only(self):
        self.assertEqual(self.create("mcp_hubspot_aaaaaaaa", "mcp_connection", self.HASH)[0], 0)
        self.assertEqual(self.create("mcp_sf_bbbbbbbb", "mcp_write_connection", "b" * 64)[0], 0)
        self.respond("mcp_hubspot_aaaaaaaa")
        events = self.events()
        self.assertEqual(events[0]["binding"], self.HASH)
        self.assertNotIn("binding", events[-1])

    def test_binding_matches_only_when_approved_and_equal(self):
        gate = "mcp_hubspot_aaaaaaaa"
        self.assertFalse(approval_gate.binding_matches(self.ledger, gate, self.HASH))
        self.create(gate, "mcp_connection", self.HASH)
        self.assertFalse(approval_gate.binding_matches(self.ledger, gate, self.HASH))
        self.respond(gate)
        self.assertTrue(approval_gate.binding_matches(self.ledger, gate, self.HASH))
        self.assertFalse(approval_gate.binding_matches(self.ledger, gate, "c" * 64))
        self.assertFalse(approval_gate.binding_matches(self.ledger, gate, ""))
        self.assertFalse(approval_gate.binding_matches(self.ledger, "other", self.HASH))

    def test_rejected_or_unbound_gate_never_matches(self):
        self.create("g1", "mcp_connection", self.HASH)
        self.respond("g1", "rejected")
        self.assertFalse(approval_gate.binding_matches(self.ledger, "g1", self.HASH))
        self.create("g2", "mcp_connection")
        self.respond("g2")
        self.assertFalse(approval_gate.binding_matches(self.ledger, "g2", self.HASH))

    def test_reused_gate_id_uses_latest_lifecycle(self):
        self.create("g", "mcp_connection", self.HASH)
        self.respond("g")
        self.create("g", "mcp_write_connection", "d" * 64)
        self.assertFalse(approval_gate.binding_matches(self.ledger, "g", self.HASH))
        state = approval_gate.gate_state(self.ledger, "g")
        self.assertEqual((state["status"], state["stakes_class"], state["binding"]), ("pending", "mcp_write_connection", "d" * 64))
        self.respond("g")
        self.assertTrue(approval_gate.binding_matches(self.ledger, "g", "d" * 64))
        self.assertFalse(approval_gate.binding_matches(self.ledger, "g", self.HASH))

    def test_gate_state_unknown_is_none(self):
        self.assertIsNone(approval_gate.gate_state(self.ledger, "missing"))


if __name__ == "__main__":
    unittest.main()
