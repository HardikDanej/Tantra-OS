"""
sync_workspace_state.py
========================
Merges newly-discovered brand-identity facts and competitor intel into
`.memory/brand_identity.json` and `.memory/competitor_matrix.json` in the
current workspace, deterministically -- no duplicate entries, no lost
history, no silent overwrite of what an earlier session established.

Why this exists, and why it's a separate thing from `brand/` and `memory/`:
`brand/personas.json` / `voice_system.json` / `icp_definition.md` are
formal deliverables -- gated, evidence-required, produced only by the
Marketing Strategist Agent's six-stage sequence. `memory/checkpoints.jsonl`
/ `outcomes.jsonl` are the Orchestrator's own append-only audit trail, and
`outcomes.jsonl` specifically only grows when the *user* comes back and
manually reports what happened to a past recommendation (see the
Orchestrator's Outcome Feedback Ingestion section). Neither one captures
the smaller, incidental facts that surface constantly in ordinary
dispatches that were never a formal brand engagement and were never a
user reporting back an outcome -- an SEO dispatch that turns up a named
competitor, an ads brief that confirms the audience skews mid-market, a
strategist aside that the tagline direction has settled. Those used to
just evaporate at the end of the session unless someone thought to write
them down. `.memory/` is where they land instead, and this script is what
makes "sync it in without duplicating or clobbering what's already there"
a real merge instead of the Orchestrator free-handing a `Write` and
hoping it remembers what was already recorded.

The dot-prefix is deliberate, distinguishing it from `brand/` (authored,
reviewed, the source of truth when a dispatch needs grounded facts) and
`memory/` (the formal audit trail) -- `.memory/` is a lower-confidence,
continuously-accumulating cache. It supplements the formal artifacts, it
never substitutes for them: a dispatch that needs a real ICP still needs
`brand/icp_definition.md`, not a `.memory/brand_identity.json` fact.

Merge semantics:
- brand_identity: each update carries a caller-chosen `key` (a short
  stable slug, e.g. "target_audience" -- this script doesn't try to
  fuzzy-match free text to decide two facts are "the same fact"; the
  caller, who actually understands the content, picks the key). Same key
  again updates the fact in place and bumps `last_confirmed`, keeping the
  original `first_observed`. A new key creates a new entry.
- competitor_matrix: matched by name (case/whitespace-normalized -- this
  one bit of fuzzing is safe because it's exact-modulo-formatting, not
  semantic). A repeat mention appends a new note (skipped if the note
  text is byte-identical to one already recorded, so re-syncing the same
  finding twice doesn't spam the list) and bumps `last_mentioned`. A new
  name creates a new entry.

Usage:
    # 1. Write the newly-discovered facts to a scratch JSON file first
    #    (Write tool), e.g. as an array of
    #    {"key": "...", "fact": "...", "category": "...", "confidence": "..."}
    #    for brand_identity, or {"name": "...", "note": "...", "source": "..."}
    #    for competitor_matrix.
    # 2. Merge it in and see what changed:
    python sync_workspace_state.py .memory/brand_identity.json \\
        --kind brand_identity --updates-file /tmp/updates.json
    python sync_workspace_state.py .memory/competitor_matrix.json \\
        --kind competitor_matrix --updates-file /tmp/updates.json

Exit codes: 0 on success. 1 if the updates file is missing/malformed, or
an update is missing a required field for its kind.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

VALID_CATEGORIES = {"positioning", "audience", "voice", "product", "other"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def load_state(path: Path, empty: dict) -> dict:
    if not path.exists():
        return empty
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def sync_brand_identity(path: Path, updates: list[dict]) -> list[str]:
    state = load_state(path, {"last_synced": None, "facts": {}})
    report = []
    for u in updates:
        key = (u.get("key") or "").strip()
        fact = (u.get("fact") or "").strip()
        if not key or not fact:
            print(f"ERROR: brand_identity update missing required 'key' or 'fact': {u}", file=sys.stderr)
            sys.exit(1)
        category = u.get("category", "other")
        if category not in VALID_CATEGORIES:
            print(f"ERROR: '{key}' has invalid category '{category}' -- must be one of {sorted(VALID_CATEGORIES)}",
                  file=sys.stderr)
            sys.exit(1)
        confidence = u.get("confidence", "medium")
        if confidence not in VALID_CONFIDENCE:
            print(f"ERROR: '{key}' has invalid confidence '{confidence}' -- must be one of {sorted(VALID_CONFIDENCE)}",
                  file=sys.stderr)
            sys.exit(1)

        existing = state["facts"].get(key)
        if existing is None:
            state["facts"][key] = {
                "fact": fact, "category": category, "confidence": confidence,
                "first_observed": now(), "last_confirmed": now(),
            }
            report.append(f"NEW      {key}: {fact}")
        elif existing["fact"] == fact and existing["category"] == category and existing["confidence"] == confidence:
            existing["last_confirmed"] = now()
            report.append(f"CONFIRMED {key} (unchanged, re-confirmed)")
        else:
            existing.update(fact=fact, category=category, confidence=confidence, last_confirmed=now())
            report.append(f"UPDATED  {key}: {fact}")

    state["last_synced"] = now()
    save_state(path, state)
    return report


def sync_competitor_matrix(path: Path, updates: list[dict]) -> list[str]:
    state = load_state(path, {"last_synced": None, "competitors": {}})
    report = []
    for u in updates:
        name = (u.get("name") or "").strip()
        note = (u.get("note") or "").strip()
        if not name or not note:
            print(f"ERROR: competitor_matrix update missing required 'name' or 'note': {u}", file=sys.stderr)
            sys.exit(1)
        source = u.get("source", "")
        key = normalize_name(name)

        existing = state["competitors"].get(key)
        if existing is None:
            state["competitors"][key] = {
                "name": name,
                "notes": [{"note": note, "source": source, "logged_at": now()}],
                "first_observed": now(), "last_mentioned": now(),
            }
            report.append(f"NEW      {name}: {note}")
        else:
            existing["last_mentioned"] = now()
            if any(n["note"] == note for n in existing["notes"]):
                report.append(f"SEEN     {name} (note already recorded, not duplicated)")
            else:
                existing["notes"].append({"note": note, "source": source, "logged_at": now()})
                report.append(f"NOTE ADDED {name}: {note}")

    state["last_synced"] = now()
    save_state(path, state)
    return report


SYNC_FUNCS = {"brand_identity": sync_brand_identity, "competitor_matrix": sync_competitor_matrix}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target_file", help="Path to .memory/brand_identity.json or .memory/competitor_matrix.json")
    parser.add_argument("--kind", required=True, choices=list(SYNC_FUNCS.keys()))
    parser.add_argument("--updates-file", required=True,
                         help="A JSON array of updates -- see this script's module docstring for the shape per kind")
    args = parser.parse_args()

    updates_path = Path(args.updates_file)
    if not updates_path.exists():
        print(f"ERROR: --updates-file {updates_path} does not exist.", file=sys.stderr)
        return 1
    updates = json.loads(updates_path.read_text(encoding="utf-8"))
    if not isinstance(updates, list):
        print("ERROR: --updates-file must contain a JSON array.", file=sys.stderr)
        return 1
    if not updates:
        print("Nothing to sync -- the updates file is an empty array. (This is fine: not every session "
              "discovers a durable brand-identity fact or a competitor worth recording -- don't manufacture "
              "one to fill this file.)")
        return 0

    report = SYNC_FUNCS[args.kind](Path(args.target_file), updates)
    print(f"Synced {len(report)} update(s) into {args.target_file}:")
    for line in report:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
