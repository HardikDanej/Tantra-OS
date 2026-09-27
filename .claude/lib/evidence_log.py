"""
evidence_log.py
================
Append-only evidence ledger for live research (WebFetch/WebSearch) done by
a domain agent mid-dispatch.

Why this exists: a domain agent's anti-hallucination behavior today is
entirely a prompt instruction ("don't make things up") that the model
grades on its own output. That's "asked nicely." This script is the other
half — a place to put the literal bytes a tool call actually returned, so
a later, separate, non-LLM check (citation_guard.py) can confirm a cited
number or URL traces back to something that was really fetched this
session, instead of trusting the model's memory of its own research.

Usage (run via Bash, once per WebFetch/WebSearch call worth citing from):

    # 1. Write the tool result's raw text to a file first (Write tool), e.g.
    #    evidence/raw/ev_003.txt containing the WebFetch/WebSearch output.
    # 2. Record it:
    python evidence_log.py <ledger.json> add \\
        --source-type webfetch --url "https://example.com/pricing" \\
        --content-file evidence/raw/ev_003.txt \\
        --note "Pricing page for CompetitorX"

    # Review what's been logged so far:
    python evidence_log.py <ledger.json> list

The ledger is a flat JSON array on disk. Nothing here calls a network API —
this only records what the agent already fetched and is choosing to log.
It cannot verify the agent logged everything, only that what IS logged is
traceable to a real file with real content and a timestamp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["webfetch", "websearch", "bash", "mcp"]


class EvidenceRecord(BaseModel):
    id: str
    source_type: SourceType
    url: str | None = None
    note: str = ""
    content_path: str
    content_length: int
    content_sha256: str
    logged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def load_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def cmd_add(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    content_path = Path(args.content_file)
    if not content_path.exists():
        print(f"ERROR: --content-file {content_path} does not exist. "
              f"Write the tool result's raw text to a file first, then log it.", file=sys.stderr)
        return 1

    content = content_path.read_text(encoding="utf-8", errors="replace")
    if len(content.strip()) == 0:
        print(f"ERROR: {content_path} is empty. Logging an empty fetch as evidence "
              f"would let a later claim 'verify' against nothing — refusing.", file=sys.stderr)
        return 1

    records = load_ledger(ledger_path)
    record = EvidenceRecord(
        id=f"ev_{len(records) + 1:04d}",
        source_type=args.source_type,
        url=args.url,
        note=args.note or "",
        content_path=str(content_path),
        content_length=len(content),
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
    )
    records.append(json.loads(record.model_dump_json()))
    save_ledger(ledger_path, records)
    print(f"Logged {record.id}: {args.source_type} "
          f"{'(' + args.url + ') ' if args.url else ''}"
          f"— {record.content_length} chars from {content_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    records = load_ledger(Path(args.ledger))
    if not records:
        print("Ledger is empty — no evidence logged yet.")
        return 0
    for r in records:
        url_part = f" [{r['url']}]" if r.get("url") else ""
        print(f"{r['id']}: {r['source_type']}{url_part} — {r['content_length']} chars "
              f"— {r['note']} ({r['logged_at']})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ledger", help="Path to the ledger JSON file (created if missing)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Log one piece of fetched evidence")
    p_add.add_argument("--source-type", required=True, choices=["webfetch", "websearch", "bash", "mcp"])
    p_add.add_argument("--url", default=None, help="The URL fetched, if applicable")
    p_add.add_argument("--content-file", required=True, help="Path to a file containing the raw tool result text")
    p_add.add_argument("--note", default="", help="Short human note on what this evidence is")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="Print everything logged so far")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
