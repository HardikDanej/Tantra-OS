"""
new_workspace.py
=================
Creates the `brand/` + `memory/` + `.memory/` + `deliverables/` scaffold
for a company workspace, and writes the two artifacts that give a
workspace its identity and its standing instructions: `brand/company.json`
and `CLAUDE.md`. (`.memory/`'s own two files -- brand_identity.json,
competitor_matrix.json -- are created lazily by `sync_workspace_state.py`
on first actual sync, not here; there's nothing to write for a workspace
that hasn't discovered anything yet.)

The multi-tenant model this system runs on: one directory = one company.
Opening Claude Code in a directory that has a `brand/company.json` *is*
the brand selection -- the Orchestrator reads that file instead of asking
which company a request is for, or inferring it from conversation. This
script is what makes "created once, the first time a workspace is used"
an actual mechanism instead of a Write call the model free-hands (and
might repeat, or get the slug wrong on, on a later run) -- same reasoning
as `redispatch_tracker.py` turning a rule into persisted, checked state.

`CLAUDE.md` is the other half: Claude Code auto-loads a project-root
CLAUDE.md the moment a session opens in that directory, with nothing the
user has to ask for. That's the one place a standing instruction ("Tantra
routing applies only once the user has said the wake word 'mk' / 'MK
agent'; when it does, route through exactly one orchestrator") and this
specific company's own boundaries (a competitor never to name, a spend
ceiling, a mandatory review step) can live so they apply from the very
first message, not from whenever someone remembers to restate them. It's
rendered once from `templates/CLAUDE.md.template` and then left alone -- a
human is expected to add real boundaries to it over time, so this script
never overwrites an existing one on its own. `--refresh-claude-md` is the
explicit, opt-in way to pick up a newer template (e.g. the wake-word
routing rules): it backs the current file up to
`CLAUDE.md.bak-<UTC timestamp>` first, re-renders from the template, and
carries the hand-written "Company-specific boundaries" section across so
those rules keep applying. Any other hand-added `##` section is named in
the output so it can be copied back from the backup.

The scaffold also carries the pieces the Tantra hooks rely on:
  - `deliverables/` -- where file deliverables are written; the Tantra
    Seal hook signs whatever lands there (C2PA + Ed25519 sidecar).
  - `memory/mcp_connections.jsonl` -- the append-only ledger of approved
    MCP connectors (written by the `tantra-connect` skill). Created empty,
    never truncated.
  - `.claude/settings.local.json` -- the workspace-scope Tantra hooks,
    installed by running `tools/install_hooks.py workspace <dir>` with
    this same interpreter. Skipped with `--no-hooks`. A missing installer
    or a failed install is a WARNING, never a failure: the workspace
    itself is still valid, and the printed command retries the install.

THE CROSS-SESSION COLLISION THIS SCRIPT NOW PREVENTS
-----------------------------------------------------
"One directory = one company" only holds if every session that resolves
a company name actually lands on the *same* directory. Two orchestrators
dispatched as separate agent sessions for the same real company -- e.g.
via the cross-system-dispatch-bridge, or any top-level fan-out across
multiple systems -- have no shared CWD and no way to see each other's
choice of `target_dir`. Left unchecked, each one independently decides
"no workspace exists yet, I'll create one" and they silently create two
non-communicating workspaces for the same company: two `company.json`
files, two `memory/checkpoints.jsonl` logs, two `.memory/` caches, none
of them aware the other exists. Every cross-system file-based dependency
this framework relies on (the bridge's shared-workspace table, any
`brand/*` artifact a sibling system reads) breaks silently in exactly
this scenario -- it produces no error, just two workspaces quietly
drifting apart.

The fix is a small, fixed-location registry (`.workspaces/registry.json`,
next to this script's own repo root -- not inside any workspace, so it's
discoverable from any CWD via the same `~/Tantra/tools/...`
path every agent already uses) mapping a company's slug to the one
absolute path that's canonical for it. Before scaffolding anything, this
script checks the registry for the resolved name's slug:
  - No entry yet -> proceed normally, then register this path as canonical.
  - Entry matches `target_dir` -> just a repeat call on the real workspace,
    proceed as before.
  - Entry points somewhere else, and that other path still has a real
    `brand/company.json` -> REFUSE. Print the canonical path and stop,
    rather than silently creating a second workspace. The caller (human
    or agent) should operate in the canonical directory instead.
  - Entry points somewhere that no longer exists (moved/deleted) -> treat
    as stale, warn, and re-register at the new `target_dir`.
A deliberate second, disconnected workspace for the same company name
(rare -- a sandbox, a what-if scenario) is still possible via
`--force-new-location`, which skips the refusal but never touches the
registry, so the canonical entry other sessions rely on stays intact.

`--lookup-only --name "..."` resolves a company name against the registry
and prints the canonical path (or NOT_FOUND) without creating or touching
anything -- the check an orchestrator should run *before* picking a
`target_dir` at all, when it can't be sure a workspace doesn't already
exist somewhere else for this company.

Usage:
    python new_workspace.py <target-dir> --name "Acme Co"
    python new_workspace.py <target-dir> --no-hooks
    python new_workspace.py <target-dir> --refresh-claude-md
    python new_workspace.py --lookup-only --name "Acme Co"

Creates <target-dir>/brand/, <target-dir>/memory/ (with evidence/raw/ and
an empty mcp_connections.jsonl), <target-dir>/.memory/ and
<target-dir>/deliverables/ if missing (and <target-dir> itself, if it
doesn't exist yet). Writes brand/company.json with {name, slug, created}
and CLAUDE.md from the template. --name may be omitted on a later run if
brand/company.json already exists -- its recorded name is reused.
company.json itself is left untouched unless --force is passed (a
workspace's identity, once set, doesn't silently change underneath it);
an existing CLAUDE.md is only ever replaced by --refresh-claude-md, and
always backed up first.

Exit codes: 0 on success (including a --lookup-only hit, and including a
hook install that only warned). 1 if no name is available (neither
--name nor an existing company.json to read one from). 2 if the registry
already has a *different*, still-valid canonical path for this company's
slug (the collision this script exists to catch) --
--force-new-location downgrades this to a warning and proceeds. 3 if
--lookup-only found no registry entry for the name.

Warns (non-fatal) if the target already has a non-empty .claude/agents/
or .claude/skills/ -- a workspace isn't supposed to have either, since
they'd shadow the global ones symlinked per INSTALL.md and this
workspace would silently stop seeing framework updates. This script
only warns; `check_install.py <target-dir>` is the actual check.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "tools" / "templates" / "CLAUDE.md.template"
REGISTRY_PATH = REPO_ROOT / ".workspaces" / "registry.json"
INSTALL_HOOKS_PATH = REPO_ROOT / "tools" / "install_hooks.py"
BOUNDARIES_HEADING = "## Company-specific boundaries"
HOOK_INSTALL_TIMEOUT_S = 120


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "workspace"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(f"WARNING: {REGISTRY_PATH} exists but couldn't be parsed -- treating as empty rather than "
              f"failing the whole command. Inspect it by hand if this persists.", file=sys.stderr)
        return {}


def save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def registry_entry_is_live(entry: dict) -> bool:
    """A registry entry is live if its path still has a real company.json -- not just if the path exists."""
    try:
        return (Path(entry["path"]) / "brand" / "company.json").exists()
    except (KeyError, TypeError):
        return False


def ensure_scaffold(root: Path) -> list[str]:
    """Create the workspace directories and empty ledgers that are missing; return what was created.

    Existing files are never truncated -- `memory/mcp_connections.jsonl` in particular is an
    append-only approval ledger, so "create if missing" is the only safe operation on it.
    """
    created = []
    for rel in ("brand", "memory", "memory/evidence/raw", ".memory", "deliverables"):
        path = root / rel
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel + "/")
    ledger = root / "memory" / "mcp_connections.jsonl"
    if not ledger.exists():
        ledger.touch()
        created.append("memory/mcp_connections.jsonl")
    return created


def render_claude_md(company_name: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{COMPANY_NAME}}", company_name)


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    """(start, end) line indexes of a `## ` section's body, or None. Headings inside code fences don't count."""
    target = heading.strip().lower()
    start = None
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line.startswith("## "):
            continue
        if start is not None:
            return start, i
        if stripped.lower().startswith(target):
            start = i + 1
    return (start, len(lines)) if start is not None else None


def extract_section(text: str, heading: str) -> str | None:
    lines = text.splitlines(keepends=True)
    bounds = _section_bounds(lines, heading)
    return "".join(lines[bounds[0]:bounds[1]]) if bounds else None


def replace_section(text: str, heading: str, body: str) -> str:
    lines = text.splitlines(keepends=True)
    bounds = _section_bounds(lines, heading)
    if bounds is None:
        return text
    if body and not body.endswith("\n"):
        body += "\n"
    return "".join(lines[:bounds[0]]) + body + "".join(lines[bounds[1]:])


def level2_headings(text: str) -> list[str]:
    headings, in_fence = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            headings.append(line.strip())
    return headings


def backup_path_for(claude_file: Path, now: datetime) -> Path:
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    candidate = claude_file.with_name(f"{claude_file.name}.bak-{stamp}")
    n = 1
    while candidate.exists():
        candidate = claude_file.with_name(f"{claude_file.name}.bak-{stamp}-{n}")
        n += 1
    return candidate


def refresh_claude_md(claude_file: Path, company_name: str, now: datetime | None = None) -> Path:
    """Back up the existing CLAUDE.md byte-for-byte, then re-render it from the template.

    The hand-written boundaries section is carried over because it holds this company's hard
    rules -- dropping it on a template refresh would silently lift them. Returns the backup path.
    """
    now = now or datetime.now(timezone.utc)
    old_text = claude_file.read_text(encoding="utf-8")
    backup = backup_path_for(claude_file, now)
    shutil.copy2(claude_file, backup)
    print(f"CLAUDE.md backed up -> {backup.name}")

    new_text = render_claude_md(company_name)
    old_boundaries = extract_section(old_text, BOUNDARIES_HEADING)
    new_boundaries = extract_section(new_text, BOUNDARIES_HEADING)
    if old_boundaries is None:
        print(f"NOTE: the previous CLAUDE.md had no \"{BOUNDARIES_HEADING}\" section, so no boundaries were "
              f"carried over. Review {backup.name} for any rules that need re-adding.")
    elif new_boundaries is not None and old_boundaries.strip() != new_boundaries.strip():
        new_text = replace_section(new_text, BOUNDARIES_HEADING, old_boundaries)
        print(f"Carried the existing \"{BOUNDARIES_HEADING}\" section over unchanged.")

    new_headings = {h.lower() for h in level2_headings(new_text)}
    dropped = [h for h in level2_headings(old_text) if h.lower() not in new_headings]
    if dropped:
        print(f"NOTE: these sections from the previous CLAUDE.md are not in the current template and were not "
              f"carried over -- copy them back from {backup.name} if they're still wanted: {', '.join(dropped)}")

    claude_file.write_text(new_text, encoding="utf-8")
    print(f"CLAUDE.md re-rendered from the current template for \"{company_name}\"")
    return backup


def install_workspace_hooks(root: Path) -> bool:
    """Run `install_hooks.py workspace <root>` with this interpreter. Returns True only on a clean install.

    Every problem here is reported as a WARNING with the exact retry command, never raised: the
    workspace scaffold is already valid without hooks, so a hook problem must not fail the run.
    """
    cmd = [sys.executable, str(INSTALL_HOOKS_PATH), "workspace", str(root)]
    retry = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    if not INSTALL_HOOKS_PATH.is_file():
        print(f"WARNING: {INSTALL_HOOKS_PATH} not found -- Tantra workspace hooks were NOT installed. "
              f"The workspace works without them (no sentinels, connector guard, or auto-seal). "
              f"Once the installer exists, run: {retry}", file=sys.stderr)
        return False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=HOOK_INSTALL_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"WARNING: Tantra workspace hook install could not run ({type(exc).__name__}: {exc}). "
              f"Retry with: {retry}", file=sys.stderr)
        return False
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip())
    indented = "\n".join(f"    {line}" for line in output.splitlines())
    if proc.returncode != 0:
        print(f"WARNING: Tantra workspace hook install exited {proc.returncode}; hooks may be missing or "
              f"outdated in {root / '.claude' / 'settings.local.json'}. Retry with: {retry}", file=sys.stderr)
        if indented:
            print(indented, file=sys.stderr)
        return False
    print(f"Tantra workspace hooks installed into {root / '.claude' / 'settings.local.json'} (ran: {retry})")
    if indented:
        print(indented)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target_dir", nargs="?", default=None,
                         help="The company workspace directory (created if missing). Not required with --lookup-only.")
    parser.add_argument("--name", default=None,
                         help="The company/brand's real name, e.g. \"Acme Co\". "
                              "Optional if brand/company.json already exists -- its name is reused.")
    parser.add_argument("--force", action="store_true",
                         help="Overwrite an existing brand/company.json's name/slug. Never affects CLAUDE.md "
                              "(only --refresh-claude-md does).")
    parser.add_argument("--force-new-location", action="store_true",
                         help="Proceed even though the registry already has a different, still-valid canonical "
                              "path for this company's slug. Use only for a deliberate, disconnected second "
                              "workspace (a sandbox, a what-if) -- the registry's canonical entry is left "
                              "pointing at the original, so this new one stays undiscoverable by name on purpose.")
    parser.add_argument("--lookup-only", action="store_true",
                         help="Resolve --name against the registry and print the canonical path (or NOT_FOUND). "
                              "Creates and touches nothing. Run this before picking a target_dir whenever a "
                              "workspace might already exist elsewhere for this company.")
    parser.add_argument("--refresh-claude-md", action="store_true",
                         help="Opt-in: back up an existing CLAUDE.md to CLAUDE.md.bak-<UTC timestamp> and "
                              "re-render it from the current template, carrying the Company-specific "
                              "boundaries section over. Never happens without this flag.")
    parser.add_argument("--no-hooks", action="store_true",
                         help="Skip installing the workspace-scope Tantra hooks "
                              "(tools/install_hooks.py workspace <dir>).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.lookup_only:
        if not args.name:
            print("ERROR: --lookup-only requires --name.", file=sys.stderr)
            return 1
        registry = load_registry()
        slug = slugify(args.name)
        entry = registry.get(slug)
        if entry and registry_entry_is_live(entry):
            print(entry["path"])
            return 0
        print("NOT_FOUND")
        return 3

    if not args.target_dir:
        print("ERROR: target_dir is required unless --lookup-only is passed.", file=sys.stderr)
        return 1

    root = Path(args.target_dir)
    company_file = root / "brand" / "company.json"
    claude_file = root / "CLAUDE.md"

    for shadow in ("agents", "skills"):
        shadow_dir = root / ".claude" / shadow
        if shadow_dir.exists() and any(shadow_dir.iterdir()):
            print(f"WARNING: {shadow_dir} already exists and is non-empty. A workspace isn't supposed to have "
                  f"its own .claude/{shadow} -- it shadows the global one (see INSTALL.md) and this workspace "
                  f"will silently stop seeing framework updates to {shadow} it shadows. Proceeding anyway -- "
                  f"this script only writes .claude/settings.local.json (the Tantra hooks) under .claude/, "
                  f"never agents or skills -- but run `python check_install.py {root}` after this to confirm "
                  f"whether that's deliberate.",
                  file=sys.stderr)

    existing_company = json.loads(company_file.read_text(encoding="utf-8")) if company_file.exists() else None

    name = (args.name or "").strip()
    if not name and existing_company:
        name = existing_company.get("name", "")
    if not name:
        print("ERROR: --name is required (no existing brand/company.json to read a name from).", file=sys.stderr)
        return 1

    # --- Cross-session collision check, before anything is created ---
    resolved_target = root.resolve()
    slug_for_check = slugify(name)
    registry = load_registry()
    existing_entry = registry.get(slug_for_check)
    if existing_entry and Path(existing_entry["path"]).resolve() != resolved_target:
        if registry_entry_is_live(existing_entry) and not args.force_new_location:
            print(
                f"REFUSED: a workspace for \"{existing_entry.get('name', name)}\" (slug \"{slug_for_check}\") "
                f"already exists at:\n\n    {existing_entry['path']}\n\n"
                f"Creating another one at {resolved_target} would silently split this company's state into "
                f"two non-communicating workspaces -- two company.json files, two memory logs, none of them "
                f"aware of the other. Operate in the existing workspace above instead.\n\n"
                f"If this is genuinely meant to be a separate, disconnected workspace (a sandbox, a what-if "
                f"scenario), re-run with --force-new-location. The registry's canonical entry will be left "
                f"pointing at the original -- this new one will not be discoverable by company name.",
                file=sys.stderr,
            )
            return 2
        elif not registry_entry_is_live(existing_entry):
            print(
                f"NOTE: the registry pointed \"{slug_for_check}\" at {existing_entry['path']}, but that "
                f"workspace no longer has a brand/company.json (moved or deleted) -- treating it as stale "
                f"and re-registering this slug at {resolved_target}.",
                file=sys.stderr,
            )
        else:
            print(
                f"WARNING: proceeding at {resolved_target} despite an existing, still-valid workspace for "
                f"\"{existing_entry.get('name', name)}\" at {existing_entry['path']} (--force-new-location). "
                f"This new workspace will NOT be registered under \"{slug_for_check}\" -- the original stays "
                f"canonical for that name.",
                file=sys.stderr,
            )

    created = ensure_scaffold(root)
    if created:
        print(f"Created: {', '.join(created)}")

    if existing_company is not None and not args.force:
        print(f"brand/company.json already exists (name: \"{existing_company['name']}\") "
              f"-- left untouched. Pass --force to rename.")
        company = existing_company
    else:
        company = {
            "name": name,
            "slug": slugify(name),
            "created": existing_company["created"] if existing_company else datetime.now(timezone.utc).isoformat(),
        }
        company_file.write_text(json.dumps(company, indent=2), encoding="utf-8")
        renamed = existing_company is not None
        print(f"brand/company.json {'renamed' if renamed else 'written'} -> {json.dumps(company)}")
        if (renamed and claude_file.exists() and not args.refresh_claude_md
                and existing_company["name"] != company["name"]):
            print(f"NOTE: CLAUDE.md was not touched and may still say \"{existing_company['name']}\" "
                  f"in its heading and boundaries text -- update it by hand, or re-run with --refresh-claude-md.")

    if not claude_file.exists():
        claude_file.write_text(render_claude_md(company["name"]), encoding="utf-8")
        print(f"CLAUDE.md written for \"{company['name']}\"")
    elif args.refresh_claude_md:
        refresh_claude_md(claude_file, company["name"])
    else:
        print("CLAUDE.md already exists -- left untouched (edit it by hand, or pass --refresh-claude-md to back "
              "it up and re-render it from the current template).")

    # Register (or re-confirm) this path as canonical for the slug, unless this was a deliberate
    # forced second location -- that one stays unregistered on purpose (see --force-new-location above).
    slug = company["slug"]
    already_canonical = registry.get(slug, {}).get("path") == str(resolved_target)
    if not (existing_entry and registry_entry_is_live(existing_entry) and args.force_new_location):
        if not already_canonical:
            registry[slug] = {
                "name": company["name"],
                "path": str(resolved_target),
                "created": company["created"],
                "updated": datetime.now(timezone.utc).isoformat(),
            }
            save_registry(registry)
            print(f"Registered as canonical workspace for \"{company['name']}\" (slug \"{slug}\") "
                  f"in {REGISTRY_PATH}")

    if args.no_hooks:
        print("Tantra workspace hooks: skipped (--no-hooks).")
    else:
        install_workspace_hooks(resolved_target)

    print(f"Workspace ready at {resolved_target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
