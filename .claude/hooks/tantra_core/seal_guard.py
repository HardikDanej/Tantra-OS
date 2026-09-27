"""
seal_guard -- signs client deliverables automatically ("Tantra Seal").

Why a hook: deliverables are written by agents through Write/Edit, and an
instruction like "remember to sign the file" is exactly the kind of step a
model skips. Signing on PostToolUse makes provenance a property of the
workspace instead of a habit.

Scope, deliberately narrow:
  * only when Tantra is active and the session runs inside a Tantra client
    workspace (ctx.workspace_dir);
  * only files under the configured deliverable folders (default
    `<workspace>/deliverables/`), never memory/ or brand/ state files, which
    are machine-read and change constantly;
  * never the seal's own outputs (`.c2pa`, `.tantra-sig.json`).

The hook runs with `python -I -S` and cannot import `cryptography`/`c2pa`,
so it launches `.claude/lib/provenance.py sign-file` with the same
interpreter WITHOUT -I -S (site-packages load) as a bounded subprocess.
It is installed as an async PostToolUse hook, so signing never blocks the
agent. Missing keys produce one factual note per session, not an error.

Config section "seal" in ~/.tantra/config.json: enabled, dirs, timeout_s,
python (interpreter override).
"""
import json
import os
import subprocess
import sys

from .result import Result

DEFAULTS = {
    "enabled": True,
    "dirs": ["deliverables"],
    "timeout_s": 90,
    "python": "",
}

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
OWN_SUFFIXES = (".c2pa", ".tantra-sig.json", ".c2pa.upstream")
REQUIRED_KEYS = ("identity_ed25519.pem", "c2pa_signer.key", "c2pa_chain.pem")
NO_KEYS_MARKER = "seal_no_keys_noted"
SOURCE = "seal_guard"


def handle(ctx):
    try:
        return _handle(ctx)
    except Exception as exc:  # noqa: BLE001 - provenance must never break a tool call
        ctx.log_error(SOURCE, exc)
        return None


def _handle(ctx):
    if ctx.event != "PostToolUse" or ctx.tool_name not in WRITE_TOOLS or not ctx.active:
        return None
    cfg = ctx.cfg("seal", DEFAULTS)
    workspace = ctx.workspace_dir
    if not cfg.get("enabled") or not workspace:
        return None
    path = target_path(ctx)
    if not path or not in_deliverables(path, workspace, cfg.get("dirs") or []):
        return None
    if path.lower().endswith(OWN_SUFFIXES) or ".tantra-tmp-" in os.path.basename(path) or not os.path.isfile(path):
        return None
    if not keys_present(ctx.home):
        return no_keys_note(ctx)
    return sign(ctx, cfg, path, workspace)


def target_path(ctx):
    raw = ctx.tool_input.get("file_path") or ctx.tool_input.get("notebook_path")
    if not raw:
        return None
    path = raw if os.path.isabs(raw) else os.path.join(ctx.cwd, raw)
    return os.path.realpath(path)


def in_deliverables(path, workspace, dirs):
    for d in dirs:
        base = os.path.realpath(os.path.join(workspace, d))
        try:
            if os.path.commonpath([os.path.normcase(base), os.path.normcase(path)]) == os.path.normcase(base) \
                    and os.path.normcase(path) != os.path.normcase(base):
                return True
        except ValueError:
            continue
    return False


def keys_present(home):
    return all(os.path.isfile(os.path.join(home, "keys", k)) for k in REQUIRED_KEYS)


def no_keys_note(ctx):
    marker = ctx.session_file(NO_KEYS_MARKER)
    if os.path.exists(marker):
        return None
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("1\n")
    except OSError:
        pass
    script = os.path.join(ctx.root, ".claude", "lib", "provenance.py")
    return Result(SOURCE, context=(
        "Tantra Seal is installed but no signing keys exist yet; the owner runs "
        f'`python "{script}" init --name "Hardik Danej"` once. Deliverables written before that are not signed.'
    ))


def sign(ctx, cfg, path, workspace):
    script = os.path.join(ctx.root, ".claude", "lib", "provenance.py")
    python = cfg.get("python") or sys.executable
    cmd = [python, script, "sign-file", path, "--workspace", workspace, "--json"]
    if ctx.session_id:
        cmd += ["--run-id", ctx.session_id]
    env = dict(os.environ, TANTRA_HOME=ctx.home, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=float(cfg.get("timeout_s") or 90), env=env,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as exc:
        return failure(path, f"{type(exc).__name__}: {exc}")
    result = parse_result(proc.stdout)
    if result is None:
        err = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        return failure(path, err[-1] if err else f"provenance.py exited {proc.returncode} with no output")
    return success(path, result) if result.get("ok") else failure(path, result.get("c2pa_error") or "unknown error", result)


def parse_result(stdout):
    lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and "file" in obj:
            return obj
    return None


def success(path, result):
    name = os.path.basename(path)
    text = (f"Tantra Seal signed {name} (sha256 {str(result.get('sha256', ''))[:16]}..., "
            f"C2PA {result.get('c2pa')}, signature {name}.tantra-sig.json).")
    notes = result.get("notes") or []
    if notes:
        text += " " + "; ".join(notes) + "."
    return Result(SOURCE, context=text)


def failure(path, error, result=None):
    name = os.path.basename(path)
    signed = bool(result and result.get("sig_path"))
    tail = " The Ed25519 signature file was still written." if signed else ""
    return Result(SOURCE, context=f"Tantra Seal could not fully sign {name}: {str(error)[:400]}.{tail}")
