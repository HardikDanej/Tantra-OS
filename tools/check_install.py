"""
check_install.py
=================
Confirms the global-core / local-workspace-state boundary this system
depends on, instead of leaving it as an assumption INSTALL.md describes
but nothing ever actually checks.

The boundary:
- GLOBAL CORE — `.claude/agents/`, `.claude/skills/` (symlinked per
  INSTALL.md into `~/.claude/agents`, `~/.claude/skills`, so every
  project on the machine sees them) and `.claude/lib/`, `knowledge-bases/`
  (deliberately NOT symlinked -- referenced by every agent via the full
  path `~/Tantra/...` instead, so they're always read live
  from the one true copy, no propagation step needed at all). All of it
  lives only in this repo and is the same for every company.
- LOCAL WORKSPACE STATE — `brand/`, `memory/`, `.memory/`, `CLAUDE.md`
  inside a company workspace directory (see `new_workspace.py` and
  `sync_workspace_state.py`). All of it is specific to one company and
  never touches this repo.

A `git pull` in this repo is supposed to reach every workspace instantly
through the agents/skills symlinks, and never touch a workspace's own
`brand/`/`memory/`/`.memory/`/`CLAUDE.md` at all, because those live in a
completely separate directory tree. That guarantee has exactly one real
way to silently break: a workspace ending up with its own `.claude/agents/` or
`.claude/skills/` (copy-pasted, left over from some other setup, created
by hand). Claude Code resolves a project-level `.claude/` before the
user-level one, so a shadowed workspace would keep working -- on
whatever version of the agent/skill happened to get copied there, frozen
at that moment, forever, with no error and no warning. This script is
the check for exactly that failure mode, plus the more ordinary one
(symlinks that were never created, or a Windows copy-fallback that's
gone stale).

It also checks the Hooks layer (see tools/install_hooks.py): the user-scope
Tantra handlers in ~/.claude/settings.json must exist, point at THIS repo's
.claude/hooks/tantra_hook.py and at a python that still exists, and the
agent registry the SubagentStart/Stop matcher is built from must be fresh.
A hook pointing at an old clone fails exactly like a stale agent copy:
silently, forever.

Usage:
    python check_install.py                    # global install only
    python check_install.py <workspace-dir>     # + that workspace's isolation

Exit codes: 0 if everything checked is clean. 1 if anything in GLOBAL
CORE is missing/stale, or a workspace shadows the global agents/skills,
or a "workspace" is actually the framework repo itself, or a user-scope
Tantra hook is missing / points elsewhere / is out of date, or the agent
registry is stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
if str(FRAMEWORK_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT / "tools"))
HOME_CLAUDE = Path.home() / ".claude"


def check_linked_set(kind: str, source_dir: Path, target_dir: Path, is_dir_entry: bool) -> bool:
    """kind: 'agent file' or 'skill dir'. Returns True if this set is fully clean."""
    print(f"\n--- {kind}s: {source_dir} -> {target_dir} ---")
    if not source_dir.exists():
        print(f"  ERROR: source directory doesn't exist -- {source_dir}", file=sys.stderr)
        return False

    entries = sorted(p for p in source_dir.iterdir() if (p.is_dir() if is_dir_entry else p.suffix == ".md"))
    if not entries:
        print("  (nothing to check -- source directory is empty)")
        return True

    clean = True
    for src in entries:
        dst = target_dir / src.name
        if not dst.exists():
            print(f"  MISSING  {src.name} -- not linked at all; run the INSTALL.md symlink commands")
            clean = False
        elif dst.is_symlink():
            resolved = dst.resolve()
            if resolved == src.resolve():
                print(f"  OK       {src.name} (symlinked, live)")
            else:
                print(f"  WRONG    {src.name} -- symlinked, but points at {resolved}, not this repo")
                clean = False
        else:
            # Exists but isn't a symlink -- the Windows copy-fallback INSTALL.md documents.
            stale = _differs(src, dst, is_dir_entry)
            if stale:
                print(f"  STALE    {src.name} -- a plain copy that no longer matches this repo; re-copy it")
                clean = False
            else:
                print(f"  COPY     {src.name} -- a plain copy, currently matches, but won't auto-update on the next pull")
    return clean


def _differs(src: Path, dst: Path, is_dir_entry: bool) -> bool:
    if is_dir_entry:
        src_files = {p.relative_to(src): p.read_bytes() for p in src.rglob("*") if p.is_file()}
        dst_files = {p.relative_to(dst): p.read_bytes() for p in dst.rglob("*") if p.is_file()}
        return src_files != dst_files
    return src.read_bytes() != dst.read_bytes()


def check_global() -> bool:
    print("=== Global core ===")
    ok = True
    ok &= check_linked_set("agent file", FRAMEWORK_ROOT / ".claude" / "agents", HOME_CLAUDE / "agents", is_dir_entry=False)
    ok &= check_linked_set("skill dir", FRAMEWORK_ROOT / ".claude" / "skills", HOME_CLAUDE / "skills", is_dir_entry=True)

    print("\n--- not symlinked, by design (referenced by full path instead) ---")
    for name, rel in (("lib scripts", ".claude/lib"), ("knowledge bases", "knowledge-bases")):
        p = FRAMEWORK_ROOT / rel
        if p.exists():
            print(f"  OK       {rel} exists at {p} -- agents call it via the full "
                  f"~/Tantra/{rel}/... path, so it's always live, no propagation step needed")
        else:
            print(f"  ERROR    {rel} is missing from the framework repo itself -- {p}", file=sys.stderr)
            ok = False
    return ok


def check_hooks(settings_path: Path | None = None, registry_path: Path | None = None,
                agents_dir: Path | None = None) -> bool:
    """Hooks section: user-scope handlers + registry freshness. True if clean."""
    import install_hooks

    settings_path = settings_path or install_hooks.USER_SETTINGS
    registry_path = registry_path or install_hooks.DEFAULT_REGISTRY
    agents_dir = agents_dir or install_hooks.DEFAULT_AGENTS_DIR
    print(f"\n=== Hooks (user scope): {settings_path} ===")
    try:
        rows = install_hooks.status_rows(settings_path, "user", registry_path)
    except (install_hooks.InstallError, OSError, ValueError) as exc:
        print(f"  WRONG    cannot inspect the hook settings -- {exc}")
        rows, ok = [], False
    else:
        ok = True
    label = {"ok": "OK", "missing": "MISSING", "wrong": "WRONG", "stale": "STALE"}
    fix = "; run: python tools/install_hooks.py user"
    for r in rows:
        where = f"{r['event']} {install_hooks.describe_matcher(r['matcher'])}".strip()
        detail = r["detail"] if r["kind"] == "ok" else r["detail"] + fix
        print(f"  {label[r['kind']]:<8} {where} ({r['mode']}) -- {detail}")
        ok = ok and r["kind"] == "ok"

    fresh, details = install_hooks.registry_builder.check_registry(registry_path, agents_dir)
    if fresh:
        print(f"  OK       agent registry is fresh -- {registry_path}")
    else:
        first = details[0] if details else "out of date"
        print(f"  STALE    agent registry -- {first}; run: python tools/build_tantra_registry.py, "
              f"then python tools/install_hooks.py user")
    return ok and fresh


def check_laya() -> None:
    """Advisory only -- never affects the PASS/FAIL exit code. Every orchestrator's
    Laya pre-screen (`.claude/lib/laya_screen.py`) degrades to a skipped signal on
    its own when the package or model isn't available, by design (see that
    script's module docstring), so a missing install here is a NOTE, not an
    ERROR -- the OS runs correctly without it, just without the fast local
    cross-check on HITL stakes classification."""
    print("\n=== Laya fast pre-screen (optional) ===")
    script = FRAMEWORK_ROOT / ".claude" / "lib" / "laya_screen.py"
    if not script.exists():
        print(f"  ERROR    {script} is missing from the framework repo itself", file=sys.stderr)
        return
    try:
        import importlib.util
        found = importlib.util.find_spec("laya") is not None
    except Exception:
        found = False
    if found:
        print("  OK       `laya` package importable -- orchestrators' HITL pre-screen is live "
              "(first real call still downloads the model from Hugging Face once)")
    else:
        print("  NOTE     `laya` package not importable -- orchestrators will skip the fast "
              "pre-screen and classify HITL stakes on their own judgment alone, exactly as "
              "before this feature existed. Install with: pip install laya")


def check_workspace(target: Path) -> bool:
    print(f"\n=== Workspace isolation: {target} ===")
    if not target.exists():
        print(f"  ERROR: {target} doesn't exist.", file=sys.stderr)
        return False

    ok = True

    if (target / "knowledge-bases").exists():
        print(f"  ERROR    {target} looks like the framework repo itself (has knowledge-bases/), "
              f"not a company workspace -- nothing below applies here", file=sys.stderr)
        return False

    for shadow in (".claude/agents", ".claude/skills"):
        p = target / shadow
        if p.exists() and any(p.iterdir()):
            print(f"  ERROR    {p} exists and is non-empty -- this SHADOWS the global {shadow.split('/')[-1]} "
                  f"for this workspace only. Claude Code resolves a project-level .claude/ first, so this "
                  f"workspace will silently keep running whatever version is frozen in here and never see a "
                  f"framework update again. Remove it unless this is a deliberate, known override.",
                  file=sys.stderr)
            ok = False
        else:
            print(f"  OK       no local {shadow} -- this workspace sees the global one, live")

    for label, rel in (("brand/company.json", "brand/company.json"), ("CLAUDE.md", "CLAUDE.md"),
                       ("memory/", "memory"), (".memory/", ".memory")):
        p = target / rel
        print(f"  {'OK' if p.exists() else 'NOTE'}       {label} {'present' if p.exists() else 'not created yet'}")

    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workspace_dir", nargs="?", default=None,
                         help="Optional: also check this company workspace for isolation from global core")
    args = parser.parse_args()

    ok = check_global()
    ok = check_hooks() and ok
    check_laya()
    if args.workspace_dir:
        ok = check_workspace(Path(args.workspace_dir)) and ok

    print(f"\n{'PASS' if ok else 'FAIL'}: {'clean' if ok else 'see ERROR/WRONG/STALE lines above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
