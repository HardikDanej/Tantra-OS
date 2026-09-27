"""
Tests for tools/install_hooks.py and the Hooks section of tools/check_install.py.

Every test edits a settings file inside a temp dir via --settings / an
explicit path. Nothing here may ever touch the real ~/.claude/settings.json
or a real client workspace; setUp asserts the temp location as a tripwire.
The registry comes from a temp agent tree (test_registry.write_agents) so a
concurrent edit of the real .claude/agents cannot make these tests flaky.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build_tantra_registry as brt
import check_install
import install_hooks as ih
from tests.tools.test_registry import AGENTS, write_agents

REPO = Path(__file__).resolve().parents[2]
PY = os.path.abspath(sys.executable)
HOOK = str(REPO / ".claude" / "hooks" / "tantra_hook.py")

FOREIGN = {
    "model": "opus",
    "permissions": {"allow": ["Bash(git status)"]},
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.sh"}]},
            {"matcher": "Agent|Task", "hooks": [{"type": "command", "command": "node", "args": ["audit.js"]}]},
        ],
        "Stop": [],
    },
}


def quiet(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = fn(*args, **kwargs)
        except ih.InstallError as exc:
            err.write(f"ERROR: {exc}\n")
            code = 1
    return code, out.getvalue(), err.getvalue()


class _InstallerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tantra_install_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.assertTrue(self.tmp.startswith(tempfile.gettempdir()))
        self.agents_dir = Path(write_agents(os.path.join(self.tmp, "agents")))
        self.registry = Path(self.tmp) / "registry.json"
        code, _, _ = quiet(brt.main, ["--agents-dir", str(self.agents_dir), "--out", str(self.registry)])
        self.assertEqual(code, 0)
        self.settings = Path(self.tmp) / "home" / ".claude" / "settings.json"

    def install(self, scope="user", settings=None, **kw):
        kw.setdefault("python", PY)
        kw.setdefault("dry_run", False)
        kw.setdefault("uninstall", False)
        return quiet(ih.run_install, scope, settings or self.settings, kw["python"], kw["dry_run"],
                     kw["uninstall"], self.registry, self.agents_dir)

    def load(self, path=None):
        return json.loads(Path(path or self.settings).read_text(encoding="utf-8"))

    def write(self, obj, path=None):
        path = Path(path or self.settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=4) if not isinstance(obj, str) else obj, encoding="utf-8")

    def ours(self, settings):
        found = []
        for event, groups in settings.get("hooks", {}).items():
            for group in groups:
                for h in group.get("hooks", []):
                    if ih.is_ours(h):
                        found.append((event, group.get("matcher"), h))
        return found

    def status(self, settings=None, scope="user"):
        return {(r["event"], r["mode"]): r for r in ih.status_rows(settings or self.settings, scope, self.registry)}


class UserInstall(_InstallerCase):
    def test_fresh_install_writes_every_handler_in_exec_form(self):
        code, out, _ = self.install()
        self.assertEqual(code, 0, out)
        handlers = self.ours(self.load())
        by_mode = {h["args"][-1]: (event, matcher, h) for event, matcher, h in handlers}
        self.assertEqual(sorted(by_mode), sorted(["prompt", "pre", "watchdog", "post", "substart", "substop", "session",
                                                  "handback", "compact"]))
        for event, matcher, h in handlers:
            self.assertEqual(h["type"], "command")
            self.assertEqual(h["command"], PY)
            self.assertEqual(h["args"][:3], ["-I", "-S", HOOK])
        self.assertEqual(by_mode["prompt"][:2], ("UserPromptSubmit", None))
        self.assertEqual(by_mode["prompt"][2]["timeout"], 10)
        self.assertEqual(by_mode["pre"][:2], ("PreToolUse", "Agent|Task"))
        self.assertEqual(by_mode["watchdog"][2]["asyncRewake"], True)
        self.assertEqual(by_mode["watchdog"][2]["timeout"], 3600)
        posts = {(event, matcher) for event, matcher, h in handlers if h["args"][-1] == "post"}
        self.assertEqual(posts, {("PostToolUse", "Agent|Task"), ("PostToolUseFailure", "Agent|Task")})
        self.assertEqual(by_mode["session"][:2], ("SessionStart", "compact|resume"))
        # auto-mode reports (SubagentHandback) and compaction resets reach the sentinels
        self.assertEqual(by_mode["handback"][:2], ("PostToolUse", "SubagentHandback"))
        self.assertEqual(by_mode["compact"][:2], ("PreCompact", None))
        self.assertEqual(by_mode["substop"][2]["timeout"], 30)
        agents = "|".join(sorted(AGENTS))
        self.assertEqual(by_mode["substart"][1], agents)
        self.assertEqual(by_mode["substop"][1], agents)
        pre_groups = self.load()["hooks"]["PreToolUse"]
        self.assertEqual(len(pre_groups), 1, "pre and watchdog share one Agent|Task group")
        self.assertFalse(Path(str(self.settings) + ih.BACKUP_SUFFIX).exists(), "nothing to back up")

    def test_idempotent(self):
        self.write(FOREIGN)
        self.install()
        first = self.settings.read_bytes()
        mtime = self.settings.stat().st_mtime_ns
        code, out, _ = self.install()
        self.assertEqual(code, 0)
        self.assertIn("Already up to date", out)
        self.assertEqual(self.settings.read_bytes(), first)
        self.assertEqual(self.settings.stat().st_mtime_ns, mtime)

    def test_preserves_foreign_settings_and_backs_up_once(self):
        self.write(FOREIGN)
        original = self.settings.read_text(encoding="utf-8")
        self.install()
        data = self.load()
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["permissions"], FOREIGN["permissions"])
        self.assertEqual(data["hooks"]["PreToolUse"][:2], FOREIGN["hooks"]["PreToolUse"])
        self.assertEqual(data["hooks"]["Stop"], [])
        backup = Path(str(self.settings) + ih.BACKUP_SUFFIX)
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        self.install(python=PY, uninstall=True)
        self.assertEqual(backup.read_text(encoding="utf-8"), original, "backup is never overwritten")

    def test_uninstall_restores_foreign_only_state(self):
        self.write(FOREIGN)
        self.install()
        code, out, _ = self.install(uninstall=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.load(), FOREIGN)
        self.assertEqual(self.ours(self.load()), [])

    def test_uninstall_drops_hooks_key_it_created(self):
        self.write({"model": "opus"})
        self.install()
        self.install(uninstall=True)
        self.assertEqual(self.load(), {"model": "opus"})

    def test_uninstall_without_file_writes_nothing(self):
        code, out, _ = self.install(uninstall=True)
        self.assertEqual(code, 0)
        self.assertFalse(self.settings.exists())

    def test_uninstall_with_nothing_to_remove_leaves_file_byte_identical(self):
        text = ('{\r\n    "number": 1.0e5,\r\n    "hooks": {\r\n        "Stop": [{"hooks": '
                '[{"type": "command", "command": "guard.sh"}]}]\r\n    }\r\n}\r\n')
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_bytes(text.encode("utf-8"))
        code, out, _ = self.install(uninstall=True)
        self.assertEqual(code, 0)
        self.assertIn("file not modified", out)
        self.assertEqual(self.settings.read_bytes(), text.encode("utf-8"))
        self.assertFalse(Path(str(self.settings) + ih.BACKUP_SUFFIX).exists())

    def test_reinstall_over_hand_formatted_file_is_not_rewritten(self):
        self.write(FOREIGN)
        self.install()
        reformatted = json.dumps(self.load(), indent=4).replace("\n", "\r\n").encode("utf-8")
        self.settings.write_bytes(reformatted)
        code, out, _ = self.install()
        self.assertIn("Already up to date", out)
        self.assertEqual(self.settings.read_bytes(), reformatted)

    def test_non_utf8_settings_is_refused_cleanly(self):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        raw = '{"model": "opus"}'.encode("utf-16")  # what PowerShell 5.1's '>' writes
        self.settings.write_bytes(raw)
        code, _, err = self.install()
        self.assertEqual(code, 1)
        self.assertIn("not UTF-8", err)
        self.assertEqual(self.settings.read_bytes(), raw)
        cli_code = subprocess.run([sys.executable, str(REPO / "tools" / "install_hooks.py"), "workspace",
                                   self.tmp, "--settings", str(self.settings)],
                                  capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(cli_code.returncode, 1)
        self.assertNotIn("Traceback", cli_code.stderr)
        self.assertIn("not UTF-8", cli_code.stderr)

    def test_symlinked_settings_is_written_through(self):
        target = Path(self.tmp) / "dotfiles" / "settings.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, self.settings)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"cannot create symlinks here: {exc}")
        code, out, _ = self.install()
        self.assertEqual(code, 0, out)
        self.assertTrue(self.settings.is_symlink(), "the link must survive the atomic write")
        self.assertTrue(self.ours(json.loads(target.read_text(encoding="utf-8"))))

    def test_replaces_outdated_handlers_instead_of_duplicating(self):
        old = {"type": "command", "command": "C:\\OldPython\\python.exe",
               "args": ["-I", "-S", "D:\\old-clone\\.claude\\hooks\\tantra_hook.py", "pre"], "timeout": 5}
        foreign = {"type": "command", "command": "node", "args": ["keep.js"]}
        self.write({"hooks": {"PreToolUse": [{"matcher": "Agent|Task", "hooks": [old, foreign]}]}})
        self.install()
        data = self.load()
        self.assertEqual(data["hooks"]["PreToolUse"][0], {"matcher": "Agent|Task", "hooks": [foreign]})
        pres = [h for e, m, h in self.ours(data) if h["args"][-1] == "pre"]
        self.assertEqual(len(pres), 1)
        self.assertEqual(pres[0]["command"], PY)

    def test_invalid_json_is_refused_untouched(self):
        self.write("{ not json,,")
        code, _, err = self.install()
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{ not json,,")
        self.assertFalse(Path(str(self.settings) + ih.BACKUP_SUFFIX).exists())

    def test_wrong_shapes_are_refused(self):
        for bad in ([1, 2], {"hooks": []}, {"hooks": {"PreToolUse": {}}}):
            with self.subTest(bad=bad):
                self.write(bad)
                code, _, err = self.install()
                self.assertEqual(code, 1)
                self.assertIn("refusing", err)

    def test_dry_run_writes_nothing(self):
        self.write(FOREIGN)
        before = self.settings.read_bytes()
        code, out, _ = self.install(dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("+  PreToolUse: add 2 Tantra handler(s) (pre, watchdog)", out)
        self.assertIn("Dry run: nothing written.", out)
        self.assertIn("tantra_hook.py", out)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertFalse(Path(str(self.settings) + ih.BACKUP_SUFFIX).exists())

    def test_stale_registry_blocks_user_install(self):
        (self.agents_dir / "late-subagent.md").write_text(
            "---\nname: late-subagent\ndescription: Only accepts dispatches from the SEO Agent.\n---\n", encoding="utf-8")
        code, _, err = self.install()
        self.assertEqual(code, 1)
        self.assertIn("build_tantra_registry.py", err)
        self.assertFalse(self.settings.exists())

    def test_missing_python_is_refused(self):
        code, _, err = self.install(python=os.path.join(self.tmp, "no-python.exe"))
        self.assertEqual(code, 1)
        self.assertIn("python executable not found", err)

    def test_handler_identity(self):
        self.assertTrue(ih.is_ours({"args": ["-I", "x/tantra_hook.py", "pre"]}))
        self.assertFalse(ih.is_ours({"command": "python tantra_hook.py pre"}))
        self.assertFalse(ih.is_ours({"args": ["tantra_hook.py.bak"]}))
        self.assertFalse(ih.is_ours("string"))
        self.assertEqual(ih.handler_mode({"args": ["-I", "-S", "a/tantra_hook.py", "watchdog"]}), "watchdog")
        self.assertEqual(ih.handler_mode({"args": ["a/tantra_hook.py"]}), "")


class WorkspaceInstall(_InstallerCase):
    def make_workspace(self):
        ws = Path(self.tmp) / "acme"
        (ws / "memory").mkdir(parents=True)
        (ws / "CLAUDE.md").write_text("# acme\n", encoding="utf-8")
        return ws

    def test_default_path_and_handlers(self):
        ws = self.make_workspace()
        code, out, err = quiet(ih.main, ["workspace", str(ws), "--python", PY])
        self.assertEqual(code, 0, err)
        target = ws / ".claude" / "settings.local.json"
        data = self.load(target)
        found = {(e, h["args"][-1]): (m, h) for e, m, h in self.ours(data)}
        self.assertEqual(set(found), {("PreToolUse", "pre"), ("PostToolUse", "post"), ("PostToolUseFailure", "post"), ("Stop", "stop")})
        self.assertEqual(found[("PreToolUse", "pre")][0], ih.WORKSPACE_PRE)
        # connectors_guard stops sub-agents from self-approving MCP connections via shell or file edits.
        for tool in ("Bash", "PowerShell", "Write", "Edit", "mcp__crm__search", "Read"):
            self.assertRegex(tool, ih.WORKSPACE_PRE)
        self.assertNotRegex("Agent", ih.WORKSPACE_PRE)
        self.assertEqual(found[("PreToolUse", "pre")][1]["timeout"], 15)
        self.assertEqual(found[("PostToolUse", "post")][0], ih.WORKSPACE_POST)
        self.assertTrue(found[("PostToolUse", "post")][1]["async"])
        self.assertIsNone(found[("Stop", "stop")][0])
        self.assertTrue(found[("Stop", "stop")][1]["async"])

    def test_workspace_install_ignores_stale_registry(self):
        (self.agents_dir / "late-subagent.md").write_text("---\nname: late-subagent\n---\n", encoding="utf-8")
        target = Path(self.tmp) / "ws.json"
        code, _, err = self.install("workspace", settings=target)
        self.assertEqual(code, 0, err)

    def test_refuses_framework_repo_and_missing_dir(self):
        fake_repo = Path(self.tmp) / "repo"
        (fake_repo / "knowledge-bases").mkdir(parents=True)
        code, _, err = quiet(ih.main, ["workspace", str(fake_repo), "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("framework repo", err)
        code, _, err = quiet(ih.main, ["workspace", str(Path(self.tmp) / "nope"), "--dry-run"])
        self.assertEqual(code, 1)

    def test_both_scopes_coexist_in_one_file(self):
        self.install("user")
        self.install("workspace")
        modes = sorted(h["args"][-1] for _, _, h in self.ours(self.load()))
        self.assertEqual(modes, ["post", "post", "pre", "stop"], "a second scope replaces ours in that file")


class Status(_InstallerCase):
    def test_all_ok_after_install(self):
        self.install()
        rows = self.status()
        self.assertEqual({r["kind"] for r in rows.values()}, {"ok"})
        self.assertEqual(len(rows), 10)
        code, out, _ = quiet(ih.run_status, self.settings, None, self.registry, self.agents_dir)
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_missing(self):
        rows = self.status()
        self.assertEqual({r["kind"] for r in rows.values()}, {"missing"})
        code, out, _ = quiet(ih.run_status, self.settings, None, self.registry, self.agents_dir)
        self.assertEqual(code, 1)
        self.assertIn("MISSING", out)

    def test_wrong_python_and_wrong_repo(self):
        self.install()
        data = self.load()
        for _, _, h in self.ours(data):
            if h["args"][-1] == "pre":
                h["command"] = os.path.join(self.tmp, "gone", "python.exe")
            if h["args"][-1] == "post":
                h["args"][2] = "D:\\elsewhere\\.claude\\hooks\\tantra_hook.py"
        self.write(data)
        rows = self.status()
        self.assertEqual(rows[("PreToolUse", "pre")]["kind"], "wrong")
        self.assertIn("python not found", rows[("PreToolUse", "pre")]["detail"])
        self.assertEqual(rows[("PostToolUse", "post")]["kind"], "wrong")
        self.assertIn("not this repo", rows[("PostToolUse", "post")]["detail"])
        self.assertEqual(rows[("UserPromptSubmit", "prompt")]["kind"], "ok")

    def test_agent_list_change_and_option_drift_are_stale(self):
        self.install()
        data = self.load()
        for event, _, h in self.ours(data):
            if h["args"][-1] == "session":
                h["timeout"] = 99
        for group in data["hooks"]["SubagentStart"]:
            group["matcher"] = "|".join(sorted(AGENTS)[:-1]) + "|retired-subagent"
        self.write(data)
        rows = self.status()
        self.assertEqual(rows[("SessionStart", "session")]["kind"], "stale")
        self.assertEqual(rows[("SubagentStart", "substart")]["kind"], "stale")
        self.assertIn("+1 / -1", rows[("SubagentStart", "substart")]["detail"])

    def test_unexpected_extra_handler_is_reported(self):
        self.install()
        data = self.load()
        data["hooks"]["Notification"] = [{"hooks": [{"type": "command", "command": PY,
                                                     "args": ["-I", "-S", HOOK, "notify"]}]}]
        self.write(data)
        rows = self.status()
        self.assertEqual(rows[("Notification", "notify")]["kind"], "stale")

    def test_workspace_status(self):
        ws = Path(self.tmp) / "acme"
        ws.mkdir()
        target = ws / ".claude" / "settings.local.json"
        self.install("workspace", settings=target)
        self.install()
        code, out, _ = quiet(ih.run_status, self.settings, str(ws), self.registry, self.agents_dir)
        self.assertEqual(code, 0, out)
        self.assertIn("Workspace scope", out)

    def test_invalid_settings_status_is_an_error(self):
        self.write("nope")
        code, _, err = quiet(ih.main, ["status", "--settings", str(self.settings),
                                       "--registry", str(self.registry), "--agents-dir", str(self.agents_dir)])
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)


class CheckInstallHooksSection(_InstallerCase):
    def check(self):
        return quiet(check_install.check_hooks, self.settings, self.registry, self.agents_dir)

    def test_ok(self):
        self.install()
        ok, out, _ = self.check()
        self.assertTrue(ok)
        self.assertIn("=== Hooks (user scope)", out)
        self.assertIn("OK       agent registry is fresh", out)
        self.assertNotIn("MISSING", out)

    def test_missing_wrong_and_stale(self):
        ok, out, _ = self.check()
        self.assertFalse(ok)
        self.assertIn("MISSING  UserPromptSubmit (prompt)", out)
        self.install()
        data = self.load()
        for _, _, h in self.ours(data):
            h["command"] = os.path.join(self.tmp, "gone.exe")
        self.write(data)
        (self.agents_dir / "late-subagent.md").write_text(
            "---\nname: late-subagent\ndescription: Only accepts dispatches from the SEO Agent.\n---\n", encoding="utf-8")
        ok, out, _ = self.check()
        self.assertFalse(ok)
        self.assertIn("WRONG", out)
        self.assertIn("STALE    agent registry", out)

    def test_unreadable_settings(self):
        self.write("{bad")
        ok, out, _ = self.check()
        self.assertFalse(ok)
        self.assertIn("WRONG    cannot inspect", out)


class CommandLine(_InstallerCase):
    """The real CLI in a subprocess, always with --settings pointing at a temp file."""

    def run_cli(self, *args):
        proc = subprocess.run([sys.executable, str(REPO / "tools" / "install_hooks.py"), *args,
                               "--registry", str(self.registry), "--agents-dir", str(self.agents_dir)],
                              capture_output=True, text=True, encoding="utf-8", timeout=120)
        return proc.returncode, proc.stdout, proc.stderr

    def test_install_status_uninstall_roundtrip(self):
        code, out, err = self.run_cli("user", "--settings", str(self.settings))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.ours(self.load())), 10)
        code, out, _ = self.run_cli("status", "--settings", str(self.settings))
        self.assertEqual(code, 0, out)
        code, _, err = self.run_cli("user", "--settings", str(self.settings), "--uninstall")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.load(), {})

    def test_usage_error(self):
        proc = subprocess.run([sys.executable, str(REPO / "tools" / "install_hooks.py"), "bogus"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
