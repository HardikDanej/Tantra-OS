"""
Shared helpers for Tantra hook tests (stdlib unittest only; no pytest).

Run every test from the repo root:

    python -m unittest discover -s tests -t . -v

Two ways to exercise a hook:
  * run_hook(): spawns the real dispatcher exactly the way Claude Code does
    (exec form, python -I -S, JSON on stdin) and returns (exit, stdout_obj,
    stderr_text). Use it for end-to-end behaviour.
  * make_ctx(): builds an in-process Context for fast unit tests of a module.

Both isolate state in a throwaway TANTRA_HOME so tests never touch ~/.tantra.
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS_DIR = os.path.join(REPO, ".claude", "hooks")
HOOK = os.path.join(HOOKS_DIR, "tantra_hook.py")

if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)


def temp_home():
    return tempfile.mkdtemp(prefix="tantra_home_")


def payload(event, session_id="sess-test", **fields):
    base = {
        "session_id": session_id,
        "transcript_path": "",
        "cwd": fields.pop("cwd", REPO),
        "permission_mode": "default",
        "hook_event_name": event,
    }
    base.update(fields)
    return base


def run_hook(obj, mode="", home=None, env=None, timeout=60):
    e = dict(os.environ)
    e.pop("TANTRA_ACTIVE", None)
    e["TANTRA_HOME"] = home or temp_home()
    if env:
        e.update(env)
    proc = subprocess.run(
        [sys.executable, "-I", "-S", HOOK, mode],
        input=json.dumps(obj).encode("utf-8"),
        capture_output=True,
        env=e,
        timeout=timeout,
    )
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    parsed = json.loads(out) if out else None
    return proc.returncode, parsed, proc.stderr.decode("utf-8", errors="replace")


def make_ctx(obj, home=None, registry=None, mode=""):
    from tantra_core.context import Context

    return Context(obj, mode=mode, hooks_dir=HOOKS_DIR, registry=registry, home=home or temp_home())


def activate(home, session_id="sess-test"):
    """Mark a session active the same way the activation module does."""
    from tantra_core import state

    path = os.path.join(home, "state", state.safe_name(session_id), "activation.jsonl")
    state.append_jsonl(path, {"ts": state.now_iso(), "event": "on", "by": "test"})


MINI_REGISTRY = {
    "version": 1,
    "entry_points": ["chief-marketing-orchestrator", "enterprise-marketing-orchestrator"],
    "agents": {
        "chief-marketing-orchestrator": {"tier": "entry", "parents": ["main"], "contract_fields": []},
        "enterprise-marketing-orchestrator": {"tier": "entry", "parents": ["main"], "contract_fields": []},
        "cross-system-dispatch-bridge": {"tier": "bridge", "parents": ["chief-marketing-orchestrator", "enterprise-marketing-orchestrator"], "contract_fields": []},
        "seo-agent": {"tier": "domain", "parents": ["chief-marketing-orchestrator"], "contract_fields": ["CONFIDENCE", "CITATION_CHECK", "GAPS"]},
        "technical-seo-subagent": {"tier": "sub", "parents": ["seo-agent"], "contract_fields": ["CONFIDENCE", "GAPS"]},
    },
    "knowledge_bases": ["knowledge-bases/seo-knowledge-base.md"],
}
