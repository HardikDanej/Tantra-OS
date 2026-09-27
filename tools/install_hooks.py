#!/usr/bin/env python3
"""
install_hooks.py
================
Installs, updates, inspects and removes Tantra's Claude Code hook handlers.

Why an installer instead of "paste this JSON into settings.json": the hook
entries carry two absolute paths (this machine's python.exe and this repo's
tantra_hook.py) plus a SubagentStart/SubagentStop matcher that lists every
Tantra agent by name. All three drift -- a new Python, a moved clone, an agent
added or renamed -- and a hand-edited settings file drifts silently. The
installer derives everything from this repo, so re-running it is always the
fix, and `status` says exactly what drifted.

Two scopes, because a Python hook costs ~55-80 ms per spawn:

  user       ~/.claude/settings.json -- fires in EVERY project on the machine,
             so it only hooks cheap or rare events: UserPromptSubmit (the wake
             word), Agent/Task dispatches, SubagentStart/Stop for Tantra's own
             agents, and SessionStart on compact/resume.
  workspace  <workspace>/.claude/settings.local.json -- only inside a Tantra
             client workspace, where watching Read/WebFetch/Grep/... and MCP
             calls is worth the cost.

Safety rules, all load-bearing (modelled on the unlazy skill's installer):
  * Merge-preserving. Every other settings key and every foreign hook handler
    is kept exactly. Our handlers are recognised only by an `args` element
    ending in `tantra_hook.py`, and only those are replaced or removed.
  * Idempotent. Running the same install twice produces a byte-identical
    file; a file whose parsed content would not change (including an
    uninstall with nothing to remove) is not rewritten at all.
  * Recoverable. `<settings>.tantra.bak` is written before the first
    modification ever made to a file, and every write is atomic
    (temp file + os.replace), so a crash never leaves half a settings file.
  * Refuses rather than guesses. A settings file that is not valid JSON, or
    whose `hooks` block has the wrong shape, is left untouched (exit 1).
  * A stale agent registry blocks a user-scope install (exit 1), because the
    SubagentStart/Stop matcher would otherwise omit new agents.

Usage:
    python tools/install_hooks.py user      [--settings PATH] [--python PATH] [--dry-run] [--uninstall]
    python tools/install_hooks.py workspace DIR [--settings PATH] [--python PATH] [--dry-run] [--uninstall]
    python tools/install_hooks.py status    [--settings PATH] [--workspace DIR]

Defaults: user -> ~/.claude/settings.json; workspace -> DIR/.claude/settings.local.json;
--python -> the interpreter running this script (absolute path).

Exit codes: 0 success (status: every handler installed and current).
1 refused or failed (invalid settings JSON, stale registry, missing python,
bad workspace); status: something missing or outdated. 2 usage error.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import os
import shutil
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_tantra_registry as registry_builder  # noqa: E402

FRAMEWORK_ROOT = TOOLS_DIR.parent
HOOK_SCRIPT = FRAMEWORK_ROOT / ".claude" / "hooks" / "tantra_hook.py"
DEFAULT_REGISTRY = registry_builder.DEFAULT_REGISTRY
DEFAULT_AGENTS_DIR = registry_builder.DEFAULT_AGENTS_DIR
USER_SETTINGS = Path.home() / ".claude" / "settings.json"
MARKER = "tantra_hook.py"
BACKUP_SUFFIX = ".tantra.bak"
AGENTS_MATCHER = "<tantra agents>"

WORKSPACE_PRE = r"^(Read|WebFetch|WebSearch|Grep|Glob|Skill|Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit)$|^mcp__.*"
WORKSPACE_POST = r"^(Read|WebFetch|WebSearch|Grep|Glob|Skill|Write|Edit|NotebookEdit)$|^mcp__.*"

# (event, matcher, mode, extra handler fields). AGENTS_MATCHER is replaced by
# the `|`-joined list of every agent in the registry.
SCOPES = {
    "user": (
        ("UserPromptSubmit", None, "prompt", {"timeout": 10}),
        ("PreToolUse", "Agent|Task", "pre", {"timeout": 15}),
        ("PreToolUse", "Agent|Task", "watchdog", {"asyncRewake": True, "timeout": 3600}),
        ("PostToolUse", "Agent|Task", "post", {"timeout": 15}),
        ("PostToolUseFailure", "Agent|Task", "post", {"timeout": 15}),
        ("SubagentStart", AGENTS_MATCHER, "substart", {"timeout": 15}),
        ("SubagentStop", AGENTS_MATCHER, "substop", {"timeout": 30}),
        ("SessionStart", "compact|resume", "session", {"timeout": 15}),
        # auto mode (Claude Code v2.1.271+): a subagent's report arrives as this
        # tool's message, not as last_assistant_message; recorded before SubagentStop
        ("PostToolUse", "SubagentHandback", "handback", {"timeout": 15}),
        # resets Echo's read history for the scope that compacts (subagents too)
        ("PreCompact", None, "compact", {"timeout": 15}),
    ),
    "workspace": (
        ("PreToolUse", WORKSPACE_PRE, "pre", {"timeout": 15}),
        ("PostToolUse", WORKSPACE_POST, "post", {"async": True}),
        ("PostToolUseFailure", r"^mcp__.*", "post", {"async": True}),
        ("Stop", None, "stop", {"async": True}),
    ),
}


class InstallError(Exception):
    """A refusal the CLI reports as one clear line and exit code 1."""


# ---- handler identity -----------------------------------------------------------

def is_ours(handler) -> bool:
    if not isinstance(handler, dict):
        return False
    args = handler.get("args")
    return isinstance(args, list) and any(isinstance(a, str) and a.endswith(MARKER) for a in args)


def handler_mode(handler) -> str:
    args = handler.get("args") or []
    for i, arg in enumerate(args):
        if isinstance(arg, str) and arg.endswith(MARKER):
            nxt = args[i + 1] if i + 1 < len(args) else ""
            return nxt if isinstance(nxt, str) else ""
    return ""


def handler_script(handler) -> str:
    return next((a for a in handler.get("args") or [] if isinstance(a, str) and a.endswith(MARKER)), "")


def make_handler(python: str, hook_script: str, mode: str, extra: dict) -> dict:
    return {"type": "command", "command": python, "args": ["-I", "-S", hook_script, mode], **extra}


# ---- desired configuration --------------------------------------------------------

def agent_names(registry_path: Path) -> list[str]:
    try:
        data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"cannot read the agent registry {registry_path} ({exc}). "
                           "Generate it: python tools/build_tantra_registry.py")
    names = sorted((data.get("agents") or {}).keys()) if isinstance(data, dict) else []
    if not names:
        raise InstallError(f"the agent registry {registry_path} lists no agents")
    return names


def agents_matcher(names) -> str:
    return "|".join(sorted(names))


def desired_entries(scope: str, python: str, hook_script: str, names=None) -> list[tuple]:
    """[(event, matcher, handler)] in install order."""
    entries = []
    for event, matcher, mode, extra in SCOPES[scope]:
        if matcher == AGENTS_MATCHER:
            matcher = agents_matcher(names or [])
        entries.append((event, matcher, make_handler(python, hook_script, mode, extra)))
    return entries


def ensure_registry_fresh(registry_path: Path, agents_dir: Path) -> None:
    fresh, details = registry_builder.check_registry(registry_path, agents_dir)
    if not fresh:
        lines = "\n  ".join(details[:10])
        raise InstallError(
            f"the agent registry is stale or missing ({registry_path}).\n  {lines}\n"
            "Regenerate it first: python tools/build_tantra_registry.py"
        )


# ---- settings I/O -------------------------------------------------------------------

def load_settings(path: Path) -> tuple[dict, str | None]:
    """(settings, original_text). A missing file is an empty object."""
    path = Path(path)
    if not path.exists():
        return {}, None
    if not path.is_file():
        raise InstallError(f"refusing to touch {path}: it is not a regular file")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise InstallError(f"refusing to touch {path}: it is not UTF-8 encoded (PowerShell's '>' writes "
                           "UTF-16). Re-save it as UTF-8, then re-run.")
    if not text.strip():
        return {}, text
    try:
        settings = json.loads(text)
    except ValueError as exc:
        raise InstallError(f"refusing to touch {path}: it is not valid JSON ({exc}). Fix or move it, then re-run.")
    problem = shape_problem(settings)
    if problem:
        raise InstallError(f"refusing to touch {path}: {problem}")
    return settings, text


def shape_problem(settings) -> str | None:
    if not isinstance(settings, dict):
        return "the settings root is not a JSON object"
    hooks = settings.get("hooks")
    if hooks is None:
        return None
    if not isinstance(hooks, dict):
        return "'hooks' is not a JSON object"
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            return f"'hooks.{event}' is not an array"
    return None


def render(settings: dict) -> str:
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def write_settings(path: Path, text: str) -> Path | None:
    """Atomic write. Returns the backup path if one was created now.

    A symlinked settings file (a dotfiles repo) is written through: the temp
    file goes next to the real target, so os.replace never swaps the link
    itself for a plain file. The backup stays next to the path the user named."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = Path(str(path) + BACKUP_SUFFIX)
    made_backup = None
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
        made_backup = backup
    path = Path(os.path.realpath(path))
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return made_backup


# ---- merge ----------------------------------------------------------------------------

def remove_ours(settings: dict) -> tuple[dict, int]:
    """Copy of settings without any Tantra handler. Groups and event arrays
    that only held our handlers disappear; foreign ones are untouched."""
    out = copy.deepcopy(settings)
    hooks = out.get("hooks")
    if not isinstance(hooks, dict):
        return out, 0
    removed = 0
    for event in list(hooks):
        kept_groups = []
        touched = False
        for group in hooks[event]:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                kept_groups.append(group)
                continue
            kept = [h for h in handlers if not is_ours(h)]
            if len(kept) == len(handlers):
                kept_groups.append(group)
                continue
            removed += len(handlers) - len(kept)
            touched = True
            if kept:
                kept_groups.append({**group, "hooks": kept})
        if touched and not kept_groups:
            del hooks[event]
        else:
            hooks[event] = kept_groups
    if not hooks and removed:
        del out["hooks"]
    return out, removed


def add_entries(settings: dict, entries) -> dict:
    out = copy.deepcopy(settings)
    hooks = out.setdefault("hooks", {})
    groups_by_key: dict[tuple, dict] = {}
    for event, matcher, handler in entries:
        key = (event, matcher)
        group = groups_by_key.get(key)
        if group is None:
            group = {"matcher": matcher, "hooks": []} if matcher else {"hooks": []}
            hooks.setdefault(event, []).append(group)
            groups_by_key[key] = group
        group["hooks"].append(handler)
    return out


def plan_install(settings: dict, entries) -> dict:
    cleaned, _ = remove_ours(settings)
    return add_entries(cleaned, entries)


def summarize_change(before: dict, after: dict) -> list[str]:
    def ours(settings):
        found = {}
        for event, groups in (settings.get("hooks") or {}).items():
            for group in groups:
                for h in (group.get("hooks") if isinstance(group, dict) else None) or []:
                    if is_ours(h):
                        found.setdefault(event, []).append(json.dumps([group.get("matcher"), h], sort_keys=True))
        return found

    old, new = ours(before), ours(after)
    lines = []
    for event in sorted(set(old) | set(new)):
        a, b = old.get(event, []), new.get(event, [])
        if a == b:
            lines.append(f"  =  {event}: {len(b)} Tantra handler(s) unchanged")
            continue
        added = [x for x in b if x not in a]
        gone = [x for x in a if x not in b]
        if added:
            lines.append(f"  +  {event}: add {len(added)} Tantra handler(s) ({_modes(added)})")
        if gone:
            lines.append(f"  -  {event}: remove {len(gone)} Tantra handler(s) ({_modes(gone)})")
    return lines or ["  (no Tantra handlers before or after)"]


def _modes(serialized) -> str:
    return ", ".join(handler_mode(json.loads(s)[1]) or "?" for s in serialized)


# ---- status ------------------------------------------------------------------------------

def inspect_settings(settings: dict, entries, hook_script: str) -> list[dict]:
    """One row per expected handler plus one per unexpected Tantra handler.

    kind: ok | missing | wrong (points at another repo, or a python that no
    longer exists) | stale (options or agent list out of date).
    """
    installed = []
    for event, groups in (settings.get("hooks") or {}).items():
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                continue
            for h in group["hooks"]:
                if is_ours(h):
                    installed.append((event, group.get("matcher") or None, h))

    rows, used = [], set()
    for event, matcher, want in entries:
        mode = handler_mode(want)
        candidates = [i for i, (e, _, h) in enumerate(installed)
                      if e == event and handler_mode(h) == mode and i not in used]
        if not candidates:
            rows.append(_row("missing", event, matcher, mode, "not installed"))
            continue
        idx = candidates[0]
        used.add(idx)
        _, have_matcher, have = installed[idx]
        rows.append(_compare(event, matcher, mode, want, have_matcher, have, hook_script))
    for i, (event, matcher, h) in enumerate(installed):
        if i not in used:
            rows.append(_row("stale", event, matcher, handler_mode(h),
                             "unexpected Tantra handler (re-run install to drop it)"))
    return rows


def _compare(event, matcher, mode, want, have_matcher, have, hook_script) -> dict:
    problems_wrong, problems_stale = [], []
    python = have.get("command") or ""
    if not os.path.isfile(python):
        problems_wrong.append(f"python not found: {python}")
    script = handler_script(have)
    if _norm(script) != _norm(hook_script):
        problems_wrong.append(f"points at {script}, not this repo")
    if have_matcher != matcher:
        problems_stale.append(_matcher_diff(have_matcher, matcher))
    if _options(have, script) != _options(want, hook_script):
        problems_stale.append("handler options differ from this installer's")
    if problems_wrong:
        return _row("wrong", event, matcher, mode, "; ".join(problems_wrong + problems_stale))
    if problems_stale:
        return _row("stale", event, matcher, mode, "; ".join(problems_stale))
    return _row("ok", event, matcher, mode, f"python {python}")


def _options(handler: dict, script: str) -> dict:
    """Everything that defines a handler except the two machine paths."""
    opts = {k: v for k, v in handler.items() if k not in ("command", "args")}
    opts["args"] = [a for a in handler.get("args") or [] if a != script]
    return opts


def _matcher_diff(have, want) -> str:
    if have and want and "|" in have and "|" in want and len(want) > 200:
        a, b = set(have.split("|")), set(want.split("|"))
        return f"agent list changed (+{len(b - a)} / -{len(a - b)} agents)"
    return f"matcher is {have!r}, expected {want!r}"


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path))) if path else ""


def _row(kind, event, matcher, mode, detail) -> dict:
    return {"kind": kind, "event": event, "matcher": matcher, "mode": mode, "detail": detail}


def describe_matcher(matcher) -> str:
    if not matcher:
        return ""
    if len(matcher) > 60:
        return f"[{matcher.count('|') + 1} agents]"
    return f"[{matcher}]"


def status_rows(settings_path: Path, scope: str, registry_path: Path = DEFAULT_REGISTRY,
                hook_script: Path = HOOK_SCRIPT) -> list[dict]:
    settings, _ = load_settings(settings_path)
    names = agent_names(registry_path) if scope == "user" else None
    entries = desired_entries(scope, sys.executable, str(hook_script), names)
    return inspect_settings(settings, entries, str(hook_script))


LABEL = {"ok": "OK", "missing": "MISSING", "wrong": "OUTDATED", "stale": "OUTDATED"}


def print_status(title: str, settings_path: Path, rows) -> bool:
    print(f"=== {title}: {settings_path} ===")
    for r in rows:
        where = f"{r['event']} {describe_matcher(r['matcher'])}".strip()
        print(f"  {LABEL[r['kind']]:<9} {where:<44} {r['mode']:<9} -- {r['detail']}")
    return all(r["kind"] == "ok" for r in rows)


# ---- commands ----------------------------------------------------------------------------

def resolve_python(value: str | None) -> str:
    python = os.path.abspath(value or sys.executable)
    if not os.path.isfile(python):
        raise InstallError(f"python executable not found: {python}")
    return python


def workspace_settings(directory: str) -> Path:
    ws = Path(directory).resolve()
    if not ws.is_dir():
        raise InstallError(f"workspace directory not found: {ws}")
    if (ws / "knowledge-bases").is_dir():
        raise InstallError(f"{ws} is the Tantra framework repo, not a client workspace")
    return ws / ".claude" / "settings.local.json"


def run_install(scope: str, settings_path: Path, python: str | None, dry_run: bool, uninstall: bool,
                registry_path: Path = DEFAULT_REGISTRY, agents_dir: Path = DEFAULT_AGENTS_DIR,
                hook_script: Path = HOOK_SCRIPT) -> int:
    settings, original = load_settings(settings_path)
    if uninstall:
        result, _ = remove_ours(settings)
    else:
        py = resolve_python(python)
        names = None
        if scope == "user":
            ensure_registry_fresh(registry_path, agents_dir)
            names = agent_names(registry_path)
        result = plan_install(settings, desired_entries(scope, py, str(hook_script), names))

    text = render(result)
    # Compare parsed objects, not text: a file whose Tantra handlers are already
    # right (or, on uninstall, that has none) is left byte-for-byte as the user
    # formatted it -- CRLF, 4-space indent, 1.0e5 and all.
    changed = result != settings if original is not None else result != {}
    verb = "uninstall" if uninstall else "install"
    print(f"Tantra hooks ({scope} scope, {verb}): {settings_path}")
    for line in summarize_change(settings, result):
        print(line)
    if dry_run:
        _print_diff(original, text if changed else original, settings_path)
        print("Dry run: nothing written.")
        return 0
    if not changed:
        print("Already up to date; file not modified.")
        return 0
    backup = write_settings(settings_path, text)
    if backup:
        print(f"Backup of the previous file: {backup}")
    print("Done. Restart Claude Code sessions (or run /hooks) to pick up the change.")
    return 0


def _print_diff(before: str | None, after: str | None, path: Path) -> None:
    diff = list(difflib.unified_diff((before or "").splitlines(), (after or "").splitlines(),
                                     fromfile=f"{path} (current)", tofile=f"{path} (after)", lineterm="", n=1))
    if not diff:
        print("  (no change to the file)")
        return
    shown = diff[:200]
    print("\n".join(("  " + line)[:240] for line in shown))
    if len(diff) > len(shown):
        print(f"  ... {len(diff) - len(shown)} more diff line(s)")


def run_status(settings_path: Path, workspace: str | None, registry_path: Path = DEFAULT_REGISTRY,
               agents_dir: Path = DEFAULT_AGENTS_DIR) -> int:
    ok = print_status("User scope", settings_path, status_rows(settings_path, "user", registry_path))
    fresh, details = registry_builder.check_registry(registry_path, agents_dir)
    if fresh:
        print(f"  {'OK':<9} agent registry {registry_path}")
    else:
        reason = details[0] if details else "out of date"
        print(f"  {'STALE':<9} agent registry {registry_path} -- {reason}; run tools/build_tantra_registry.py")
    ok = ok and fresh
    if workspace:
        ws_settings = workspace_settings(workspace)
        ws_rows = status_rows(ws_settings, "workspace", registry_path)
        ok = print_status("Workspace scope", ws_settings, ws_rows) and ok
    if ok:
        print("\nPASS: all Tantra hooks installed and current")
    else:
        print("\nFAIL: re-run install_hooks.py for the scopes above")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, with_install_flags=True):
        p.add_argument("--settings", type=Path, help="settings file to edit instead of the scope default")
        p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help=argparse.SUPPRESS)
        p.add_argument("--agents-dir", type=Path, default=DEFAULT_AGENTS_DIR, help=argparse.SUPPRESS)
        if with_install_flags:
            p.add_argument("--python", help="python executable the hooks run with (default: this interpreter)")
            p.add_argument("--dry-run", action="store_true", help="print the change, write nothing")
            p.add_argument("--uninstall", action="store_true", help="remove only Tantra's handlers")

    common(sub.add_parser("user", help="install into ~/.claude/settings.json (every project)"))
    ws = sub.add_parser("workspace", help="install into DIR/.claude/settings.local.json (one client workspace)")
    ws.add_argument("dir")
    common(ws)
    st = sub.add_parser("status", help="report installed / missing / outdated handlers")
    common(st, with_install_flags=False)
    st.add_argument("--workspace", help="also inspect this client workspace")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            return run_status(args.settings or USER_SETTINGS, args.workspace, args.registry, args.agents_dir)
        if args.command == "user":
            settings_path = args.settings or USER_SETTINGS
        else:
            default_path = workspace_settings(args.dir)
            settings_path = args.settings or default_path
        return run_install(args.command, settings_path, args.python, args.dry_run, args.uninstall,
                           args.registry, args.agents_dir)
    except InstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
