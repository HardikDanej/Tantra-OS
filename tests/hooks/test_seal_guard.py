"""seal_guard: auto-signing of workspace deliverables after Write/Edit (Tantra Seal)."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from tests.hooks.helpers import MINI_REGISTRY, REPO, activate, make_ctx, payload, run_hook, temp_home

LIB = os.path.join(REPO, ".claude", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import provenance  # noqa: E402
from tantra_core import seal_guard  # noqa: E402

CAN_SIGN = importlib.util.find_spec("cryptography") is not None and importlib.util.find_spec("c2pa") is not None


def make_workspace():
    ws = tempfile.mkdtemp(prefix="tantra_ws_")
    os.makedirs(os.path.join(ws, "memory"))
    os.makedirs(os.path.join(ws, "deliverables", "2026-09-25-launch"))
    with open(os.path.join(ws, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# client workspace\n")
    return ws


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def init_keys(home):
    with mock.patch.dict(os.environ, {"TANTRA_HOME": home}), \
            contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        os.environ.pop("TANTRA_KEY_PASSPHRASE", None)
        assert provenance.main(["init", "--name", "Test Owner"]) == 0


def write_event(ws, path, tool="Write", session="sess-seal"):
    return payload("PostToolUse", session_id=session, cwd=ws, tool_name=tool,
                   tool_input={"file_path": path, "content": "x"}, tool_response={"success": True})


class SealGuardUnitTests(unittest.TestCase):
    def setUp(self):
        self.home = temp_home()
        self.ws = make_workspace()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(shutil.rmtree, self.ws, True)
        activate(self.home, "sess-seal")
        self.doc = write(os.path.join(self.ws, "deliverables", "2026-09-25-launch", "brief.md"), "# Brief\n\nText.\n")

    def ctx(self, obj):
        return make_ctx(obj, home=self.home, registry=MINI_REGISTRY)

    def test_no_keys_note_once_per_session(self):
        first = seal_guard.handle(self.ctx(write_event(self.ws, self.doc)))
        self.assertIn("no signing keys exist yet", first.context)
        self.assertIn('init --name "Hardik Danej"', first.context)
        self.assertIsNone(seal_guard.handle(self.ctx(write_event(self.ws, self.doc))))

    def test_ignored_cases(self):
        outside = write(os.path.join(self.ws, "memory", "latest.json"), "{}")
        own = write(self.doc + ".tantra-sig.json", "{}")
        sidecar = write(self.doc + ".c2pa", "x")
        folder = os.path.join(self.ws, "deliverables")
        cases = {
            "outside deliverables": write_event(self.ws, outside),
            "own signature file": write_event(self.ws, own),
            "own sidecar": write_event(self.ws, sidecar),
            "deliverables folder itself": write_event(self.ws, folder),
            "read tool": dict(write_event(self.ws, self.doc), tool_name="Read"),
            "pre tool use": dict(write_event(self.ws, self.doc), hook_event_name="PreToolUse"),
            "missing file": write_event(self.ws, os.path.join(folder, "gone.md")),
            "not a workspace": write_event(REPO, os.path.join(REPO, "deliverables", "x.md")),
        }
        for label, obj in cases.items():
            with self.subTest(label):
                self.assertIsNone(seal_guard.handle(self.ctx(obj)))

    def test_inactive_session_is_silent(self):
        obj = write_event(self.ws, self.doc, session="never-activated")
        self.assertIsNone(seal_guard.handle(self.ctx(obj)))

    def test_disabled_by_config(self):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"seal": {"enabled": False}}, fh)
        self.assertIsNone(seal_guard.handle(self.ctx(write_event(self.ws, self.doc))))

    def test_relative_path_and_custom_dirs(self):
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"seal": {"dirs": ["exports"]}}, fh)
        write(os.path.join(self.ws, "exports", "a.md"), "# a\n")
        self.assertIsNone(seal_guard.handle(self.ctx(write_event(self.ws, self.doc))))
        result = seal_guard.handle(self.ctx(write_event(self.ws, os.path.join("exports", "a.md"))))
        self.assertIn("no signing keys", result.context)

    def test_path_prefix_trick_is_not_a_deliverable(self):
        lookalike = write(os.path.join(self.ws, "deliverables-old", "x.md"), "# x\n")
        self.assertIsNone(seal_guard.handle(self.ctx(write_event(self.ws, lookalike))))

    def test_subprocess_failure_is_reported_not_raised(self):
        init_keys(self.home)
        with open(os.path.join(self.home, "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"seal": {"python": os.path.join(self.ws, "no-such-python.exe")}}, fh)
        result = seal_guard.handle(self.ctx(write_event(self.ws, self.doc)))
        self.assertIn("could not fully sign brief.md", result.context)

    def test_parse_result_takes_last_json_line(self):
        out = b'noise\n{"file": "a", "ok": true}\n'
        self.assertEqual(seal_guard.parse_result(out), {"file": "a", "ok": True})
        self.assertIsNone(seal_guard.parse_result(b"Traceback ...\n"))

    @unittest.skipUnless(CAN_SIGN, "cryptography/c2pa not installed")
    def test_signs_markdown_with_sidecar(self):
        init_keys(self.home)
        result = seal_guard.handle(self.ctx(write_event(self.ws, self.doc, tool="Edit")))
        self.assertIn("Tantra Seal signed brief.md", result.context)
        self.assertIn("C2PA sidecar", result.context)
        self.assertTrue(os.path.isfile(self.doc + ".c2pa"))
        with open(self.doc + ".tantra-sig.json", encoding="utf-8") as fh:
            record = json.load(fh)
        self.assertEqual(record["workspace"], os.path.basename(self.ws))
        self.assertEqual(record["run_id"], "sess-seal")
        with mock.patch.dict(os.environ, {"TANTRA_HOME": self.home}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(provenance.main(["verify-file", self.doc]), 0)


@unittest.skipUnless(CAN_SIGN, "cryptography/c2pa not installed")
class SealGuardEndToEndTests(unittest.TestCase):
    def test_hook_signs_deliverable(self):
        home = temp_home()
        ws = make_workspace()
        self.addCleanup(shutil.rmtree, home, True)
        self.addCleanup(shutil.rmtree, ws, True)
        init_keys(home)
        activate(home, "sess-seal")
        doc = write(os.path.join(ws, "deliverables", "2026-09-25-launch", "plan.html"), "<h1>Plan</h1>\n")
        code, out, err = run_hook(write_event(ws, doc), mode="post", home=home)
        self.assertEqual(code, 0, err)
        ctx_text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Tantra Seal signed plan.html", ctx_text)
        self.assertTrue(os.path.isfile(doc + ".tantra-sig.json"))

    def test_hook_silent_when_inactive(self):
        home = temp_home()
        ws = make_workspace()
        self.addCleanup(shutil.rmtree, home, True)
        self.addCleanup(shutil.rmtree, ws, True)
        doc = write(os.path.join(ws, "deliverables", "x.md"), "# x\n")
        code, out, _ = run_hook(write_event(ws, doc), mode="post", home=home)
        self.assertEqual((code, out), (0, None))
        self.assertFalse(os.path.exists(doc + ".tantra-sig.json"))


if __name__ == "__main__":
    unittest.main()
