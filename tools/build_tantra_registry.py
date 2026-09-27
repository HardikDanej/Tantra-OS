#!/usr/bin/env python3
"""
build_tantra_registry.py
========================
Generates `.claude/hooks/tantra_registry.json`: the machine-readable map of
Tantra's 238 agents that the hooks read on every event.

Why a generated file instead of parsing `.claude/agents/*.md` inside the hook:
the hooks run on every matching tool call in every project on the machine,
and parsing 238 Markdown files per call would cost far more than loading one
small JSON file. Why generated instead of hand-written: the hierarchy already
lives in the agents' own descriptions ("Only accepts dispatches from the SEO
Agent", "Sits under the brand-creative-orchestrator"), so a hand-kept copy
would drift the first time someone edits an agent.

What each entry records (schema v1):

  tier             entry | bridge | domain | sub
  system           which of the five systems (or cross-system) the agent
                   belongs to, by following its parents up to an entry point
  parents          who may dispatch it ("main" = the user's own session)
  children         the inverse of parents
  has_agent_tool   whether its `tools:` list includes Agent (can dispatch)
  contract_fields  which of CONFIDENCE / CITATION_CHECK / GAPS its own output
                   template requires (entry points and the bridge answer the
                   user, so they get [])

Parents are resolved from each description's "Only accepts dispatches from X"
and "Sits under X" sentences. X may be an agent id, a display name ("the
Growth Ops/CRO Agent (Growth Operations & ...)"), or a group phrase ("one of
the five top-level orchestrators"). Resolution tries, in order: known group
phrases, explicit agent ids, the slug of the display name, then a unique best
token-overlap match. Every domain agent and sub-agent must resolve at least
one parent; otherwise the build prints the unresolved agents and exits 1, so
a reworded description can never silently drop an agent out of the hierarchy.
Each resolved edge is also cross-checked against the parent's body mentioning
the child's id; mismatches are printed as warnings (not failures), because
the domain agents usually list their sub-agents by display name.

Usage:
    python tools/build_tantra_registry.py            # write the registry
    python tools/build_tantra_registry.py --check    # exit 1 if it is stale
    python tools/build_tantra_registry.py --agents-dir DIR --out PATH

`--check` ignores `generated_at` and the informational `knowledge_bases`
list, so only a real hierarchy change counts.

Exit codes: 0 ok / fresh. 1 unresolved parents, or (--check) the registry is
missing or stale. 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENTS_DIR = FRAMEWORK_ROOT / ".claude" / "agents"
DEFAULT_REGISTRY = FRAMEWORK_ROOT / ".claude" / "hooks" / "tantra_registry.json"
DEFAULT_KB_DIR = FRAMEWORK_ROOT / "knowledge-bases"

SCHEMA_VERSION = 1

SYSTEM_OF_ENTRY = {
    "chief-marketing-orchestrator": "digital-marketing-growth",
    "brand-creative-orchestrator": "brand-creative",
    "product-marketing-gtm-orchestrator": "product-marketing-gtm",
    "market-research-insights-orchestrator": "market-research",
    "pr-corporate-communications-orchestrator": "pr-corporate-comms",
    "enterprise-marketing-orchestrator": "cross-system",
}
ENTRY_POINTS = tuple(SYSTEM_OF_ENTRY)
SYSTEM_ORCHESTRATORS = tuple(n for n in ENTRY_POINTS if n != "enterprise-marketing-orchestrator")
BRIDGE = "cross-system-dispatch-bridge"
DOMAIN_OVERRIDES = frozenset({"competitor-red-team-agent"})
CONTRACT_FIELDS = ("CONFIDENCE", "CITATION_CHECK", "GAPS")

GROUP_PHRASES = (
    (re.compile(r"\btop-level orchestrators?\b", re.I), SYSTEM_ORCHESTRATORS),
    (re.compile(r"\bchief(?: marketing)? orchestrator\b", re.I), ("chief-marketing-orchestrator",)),
)
SYNONYMS = (
    (re.compile(r"\bpublic relations\b", re.I), "pr"),
    (re.compile(r"\bgo[\s-]+to[\s-]+market\b", re.I), "gtm"),
)
PARENT_SENTENCES = (
    re.compile(r"Only accepts dispatches from (?P<p>.+?)(?=, never\b|, and only\b| — | -- |\.(?:\s|$)|;|$)"),
    re.compile(r"\b[Ss]its under (?P<p>.+?)(?=, | — | -- |\.(?:\s|$)|;|$)"),
)
ALTERNATIVES = re.compile(r"\s*,?\s+or\s+(?:from\s+)?", re.I)
DOMAIN_DESCRIPTION = re.compile(
    r"\bDomain agent (?:owning|for|in)\b|\b[Oo]rchestrates (?:ten|\d+) (?:specialist )?sub-agents\b"
)
FIELD_LINE = {
    f: re.compile(r"^[ \t>*_`-]*" + f + r"[*_`]*[ \t]*:", re.M) for f in CONTRACT_FIELDS
}
NAME_OK = re.compile(r"^[a-z0-9][a-z0-9-]*$")


# ---- frontmatter -------------------------------------------------------------

def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Top-level `key: value` pairs of a Markdown file's YAML frontmatter.

    Deliberately small: agent frontmatter is flat scalars plus the odd nested
    map (skills' `metadata:`). Indented continuation lines extend the
    previous key's value; nested maps are kept as their raw text.
    """
    text = text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text
    raw: dict[str, list[str]] = {}
    key = None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:(.*)$", line)
        if m and not line[:1].isspace():
            key = m.group(1)
            raw[key] = [m.group(2).strip()]
        elif key is not None and line.strip():
            raw[key].append(line.strip())
    fields = {}
    for k, parts in raw.items():
        head, rest = parts[0], parts[1:]
        if head.startswith("|"):
            fields[k] = "\n".join(rest)
        elif head.startswith(">") or head == "":
            fields[k] = " ".join(rest)
        else:
            fields[k] = _unquote(" ".join([head] + rest))
    body = "\n".join(lines[end + 1:])
    return fields, body


def parse_tools(value) -> list[str]:
    if not value:
        return []
    value = value.strip().strip("[]")
    parts = re.split(r"[,\n]|\s-\s", value)
    return [p.strip().strip("-").strip().strip("'\"") for p in parts if p.strip().strip("-").strip()]


def load_agents(agents_dir: Path) -> tuple[dict, list[str]]:
    agents, warnings = {}, []
    for path in sorted(Path(agents_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fields, body = parse_frontmatter(text)
        name = (fields.get("name") or path.stem).strip()
        if name != path.stem:
            warnings.append(f"{path.name}: frontmatter name '{name}' differs from the file name")
        if not NAME_OK.match(name):
            warnings.append(f"{path.name}: agent name '{name}' is not a plain lowercase id; skipped")
            continue
        agents[name] = {
            "description": fields.get("description", ""),
            "tools": parse_tools(fields.get("tools", "")),
            "body": body,
        }
    return agents, warnings


# ---- parent resolution -------------------------------------------------------

def _clean_phrase(phrase: str) -> str:
    phrase = re.sub(r"[*`]", "", phrase)
    while True:
        stripped = re.sub(r"\([^()]*\)", " ", phrase)
        if stripped == phrase:
            break
        phrase = stripped
    return re.sub(r"\s+", " ", phrase).strip(" ,.;:")


def _slug(text: str) -> str:
    text = re.sub(r"^(?:the|a|an)\s+", "", text.strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _tokens(text: str) -> set[str]:
    for pattern, repl in SYNONYMS:
        text = pattern.sub(repl, text)
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in {"the", "and", "a", "an", "of"}}


def resolve_phrase(phrase: str, names: set[str], exclude: str) -> list[str]:
    phrase = _clean_phrase(phrase)
    found: list[str] = []
    for alt in ALTERNATIVES.split(phrase):
        alt = alt.strip()
        if not alt:
            continue
        hit: list[str] = []
        for pattern, targets in GROUP_PHRASES:
            if pattern.search(alt):
                hit.extend(targets)
        hit.extend(n for n in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", alt) if n in names)
        if not hit and _slug(alt) in names:
            hit.append(_slug(alt))
        if not hit:
            hit.extend(_fuzzy(alt, names, exclude))
        found.extend(h for h in hit if h != exclude and h not in found)
    return found


def _fuzzy(phrase: str, names: set[str], exclude: str) -> list[str]:
    words = _tokens(phrase)
    if not words:
        return []
    scored = []
    for name in names:
        if name == exclude or name.endswith("-subagent"):
            continue
        name_tokens = set(name.split("-"))
        score = len(name_tokens & words) / len(name_tokens)
        if score >= 0.75:
            scored.append((score, name))
    scored.sort(reverse=True)
    if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):
        return []
    return [scored[0][1]]


def description_parents(name: str, description: str, names: set[str]) -> list[str]:
    parents: list[str] = []
    for sentence in PARENT_SENTENCES:
        for m in sentence.finditer(description):
            for p in resolve_phrase(m.group("p"), names, exclude=name):
                if p not in parents:
                    parents.append(p)
    return parents


# ---- registry ------------------------------------------------------------------

def _system(name: str, parents: dict, seen=None) -> str | None:
    if name in SYSTEM_OF_ENTRY:
        return SYSTEM_OF_ENTRY[name]
    if name == BRIDGE:
        return "cross-system"
    seen = seen or set()
    if name in seen:
        return None
    seen.add(name)
    for p in sorted(parents.get(name, [])):
        if p in ("main", BRIDGE):
            continue
        system = _system(p, parents, seen)
        if system:
            return system
    return None


def _contract_fields(body: str) -> list[str]:
    return [f for f in CONTRACT_FIELDS if FIELD_LINE[f].search(body)]


def build_registry(agents_dir: Path = DEFAULT_AGENTS_DIR, kb_dir: Path | None = DEFAULT_KB_DIR):
    """Return (registry_dict, unresolved_names, warnings)."""
    agents, warnings = load_agents(agents_dir)
    names = set(agents)
    missing_entries = [n for n in (*ENTRY_POINTS, BRIDGE) if n not in names]
    if missing_entries:
        warnings.append("expected top-level agents not found: " + ", ".join(missing_entries))

    parents: dict[str, list[str]] = {}
    for name, info in agents.items():
        if name in SYSTEM_OF_ENTRY:
            parents[name] = ["main"] + ([BRIDGE] if name in SYSTEM_ORCHESTRATORS and BRIDGE in names else [])
        elif name == BRIDGE:
            parents[name] = [n for n in ENTRY_POINTS if n in names]
        else:
            parents[name] = description_parents(name, info["description"], names)

    children: dict[str, list[str]] = {n: [] for n in names}
    for child, plist in parents.items():
        for p in plist:
            if p in children:
                children[p].append(child)

    unresolved = sorted(n for n, plist in parents.items() if not plist)
    for child, plist in sorted(parents.items()):
        if child in SYSTEM_OF_ENTRY or child == BRIDGE:
            continue
        for p in plist:
            if child not in agents[p]["body"]:
                warnings.append(f"cross-check: {p}'s body never mentions {child} by id")

    entries = {}
    for name in sorted(names):
        info = agents[name]
        if name in SYSTEM_OF_ENTRY:
            tier = "entry"
        elif name == BRIDGE:
            tier = "bridge"
        elif name in DOMAIN_OVERRIDES or DOMAIN_DESCRIPTION.search(info["description"]) or children[name]:
            tier = "domain"
        else:
            tier = "sub"
        entries[name] = {
            "tier": tier,
            "system": _system(name, parents),
            "parents": sorted(parents[name], key=lambda p: (p != "main", p)),
            "children": sorted(children[name]),
            "has_agent_tool": any(t in ("Agent", "Task") for t in info["tools"]),
            "contract_fields": [] if tier in ("entry", "bridge") else _contract_fields(info["body"]),
        }
        if entries[name]["system"] is None and tier != "entry":
            warnings.append(f"{name}: could not derive a system from its parents")

    registry = {
        "version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_from": ".claude/agents",
        "agent_count": len(entries),
        "entry_points": sorted(n for n in ENTRY_POINTS if n in names),
        "knowledge_bases": _knowledge_bases(kb_dir),
        "agents": entries,
    }
    return registry, unresolved, warnings


def _knowledge_bases(kb_dir: Path | None) -> list[str]:
    if not kb_dir or not Path(kb_dir).is_dir():
        return []
    return sorted(f"knowledge-bases/{p.name}" for p in Path(kb_dir).glob("*.md"))


def dumps(registry: dict) -> str:
    return json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# generated_at always differs; knowledge_bases is an informational list no hook
# or matcher depends on, so adding a KB note must not mark the registry stale
# (a stale registry blocks the user-scope install and fails check_install).
_NOT_COMPARED = ("generated_at", "knowledge_bases")


def _comparable(registry: dict | None) -> dict | None:
    if not isinstance(registry, dict):
        return None
    return {k: v for k, v in registry.items() if k not in _NOT_COMPARED}


def check_registry(registry_path: Path = DEFAULT_REGISTRY, agents_dir: Path = DEFAULT_AGENTS_DIR,
                   kb_dir: Path | None = DEFAULT_KB_DIR) -> tuple[bool, list[str]]:
    """(fresh, details). Fresh means the committed file equals a rebuild, ignoring generated_at."""
    try:
        committed = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False, [f"{registry_path} does not exist"]
    except (OSError, ValueError) as exc:
        return False, [f"{registry_path} is unreadable: {exc}"]
    fresh, unresolved, _ = build_registry(agents_dir, kb_dir)
    details = [f"unresolved parent for {n}" for n in unresolved]
    old, new = _comparable(committed), _comparable(fresh)
    if old == new and not unresolved:
        return True, details
    old_agents = (old or {}).get("agents") or {}
    new_agents = new["agents"]
    for n in sorted(set(new_agents) - set(old_agents)):
        details.append(f"added: {n}")
    for n in sorted(set(old_agents) - set(new_agents)):
        details.append(f"removed: {n}")
    for n in sorted(set(old_agents) & set(new_agents)):
        if old_agents[n] != new_agents[n]:
            keys = sorted(k for k in set(old_agents[n]) | set(new_agents[n]) if old_agents[n].get(k) != new_agents[n].get(k))
            details.append(f"changed: {n} ({', '.join(keys)})")
    for k in sorted(set(old or {}) | set(new)):
        if k != "agents" and (old or {}).get(k) != new.get(k):
            details.append(f"changed: top-level '{k}'")
    return False, details


def write_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the registry file is missing or stale")
    parser.add_argument("--agents-dir", type=Path, default=DEFAULT_AGENTS_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_REGISTRY, help="registry path (read by --check)")
    parser.add_argument("--kb-dir", type=Path, default=DEFAULT_KB_DIR)
    parser.add_argument("--verbose", action="store_true", help="also print cross-check warnings")
    args = parser.parse_args(argv)

    if not args.agents_dir.is_dir():
        print(f"ERROR: agents directory not found: {args.agents_dir}", file=sys.stderr)
        return 1

    if args.check:
        fresh, details = check_registry(args.out, args.agents_dir, args.kb_dir)
        if fresh:
            print(f"OK: {args.out} is fresh")
            return 0
        print(f"STALE: {args.out} does not match {args.agents_dir}", file=sys.stderr)
        for line in details[:40]:
            print(f"  {line}", file=sys.stderr)
        print("Regenerate it with: python tools/build_tantra_registry.py", file=sys.stderr)
        return 1

    registry, unresolved, warnings = build_registry(args.agents_dir, args.kb_dir)
    shown = [w for w in warnings if args.verbose or not w.startswith("cross-check:")]
    for w in shown:
        print(f"  WARNING  {w}")
    hidden = len(warnings) - len(shown)
    if hidden:
        print(f"  ({hidden} parent-body cross-check warning(s) hidden; --verbose shows them)")
    if unresolved:
        print("ERROR: no parent could be resolved for these agents (reword the 'Only accepts dispatches "
              "from ...' / 'Sits under ...' sentence in their description):", file=sys.stderr)
        for n in unresolved:
            print(f"  UNRESOLVED  {n}", file=sys.stderr)
        return 1
    write_atomic(args.out, dumps(registry))
    tiers = {}
    for info in registry["agents"].values():
        tiers[info["tier"]] = tiers.get(info["tier"], 0) + 1
    summary = ", ".join(f"{tiers.get(t, 0)} {t}" for t in ("entry", "bridge", "domain", "sub"))
    print(f"Wrote {args.out} ({registry['agent_count']} agents: {summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
