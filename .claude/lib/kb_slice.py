"""
kb_slice.py
===========
Load only the section of a knowledge base an agent actually needs,
instead of the whole file.

Each KB in knowledge-bases/ runs 480-640 lines and 70-110KB -- roughly
18,000-27,000 tokens at a ~4-chars-per-token estimate. The Orchestrator's
own Context Pruning step already says "pass each agent only the
knowledge-base slice it actually needs, not the full KB" -- this script
is what makes that an actual mechanism instead of a good intention. An
agent (or the Orchestrator building its dispatch contract) should never
need to `Read` an entire KB file just to answer a question that lives
under one heading.

Three operations, meant to be chained:
1. `outline` -- print just the heading structure (a table of contents),
   so the caller can see what exists without paying for the content yet.
2. `search` -- grep-style: which headings/sections actually mention a
   term, so the caller can find the right section without already
   knowing its exact name.
3. `section` -- extract one section verbatim (from its heading down to
   the next heading at the same or a shallower level), the only step
   that actually spends the tokens.

Usage:
    python kb_slice.py knowledge-bases/seo-knowledge-base.md outline
    python kb_slice.py knowledge-bases/seo-knowledge-base.md search "E-E-A-T"
    python kb_slice.py knowledge-bases/seo-knowledge-base.md section \\
        "3. Traditional / Organic SEO deep-dive"

`section` matches on heading text with a loose case-insensitive
substring match (not exact-string), since a caller found the heading via
`outline`/`search` and may not reproduce it character-for-character;
if the match is ambiguous (multiple headings match), it lists the
candidates and extracts none, rather than silently guessing which one
was meant.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# KB files contain non-ASCII punctuation (em dashes, curly quotes, "≠").
# Windows consoles default to a codepage (cp1252) that can't encode it --
# reconfigure to UTF-8 explicitly rather than let a heading crash the tool.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Heading:
    level: int
    text: str
    line_no: int  # 0-indexed line number of the heading itself


def parse_headings(lines: list[str]) -> list[Heading]:
    headings = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            headings.append(Heading(level=len(m.group(1)), text=m.group(2).strip(), line_no=i))
    return headings


def estimate_tokens(text: str) -> int:
    """Rough heuristic (chars / 4), not an exact tokenizer -- good enough to compare orders of magnitude."""
    return len(text) // 4


def cmd_outline(args: argparse.Namespace) -> int:
    lines = Path(args.kb_file).read_text(encoding="utf-8").splitlines()
    headings = parse_headings(lines)
    for h in headings:
        print(f"{'  ' * (h.level - 1)}{'#' * h.level} {h.text}")
    full_text = "\n".join(lines)
    print(f"\n{len(headings)} headings. Full file: ~{estimate_tokens(full_text):,} tokens. "
          f"Use `search` or `section` next instead of reading the whole file.")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    lines = Path(args.kb_file).read_text(encoding="utf-8").splitlines()
    headings = parse_headings(lines)
    term_lower = args.term.lower()
    hits = []
    for idx, h in enumerate(headings):
        start = h.line_no
        end = headings[idx + 1].line_no if idx + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start:end])
        if term_lower in body.lower():
            hits.append((h, estimate_tokens(body)))
    if not hits:
        print(f"No section mentions '{args.term}'.")
        return 0
    print(f"Sections mentioning '{args.term}':")
    for h, tok in hits:
        print(f"  {'#' * h.level} {h.text}  (~{tok:,} tokens)")
    return 0


def _find_section_bounds(headings: list[Heading], total_lines: int, query: str) -> list[tuple[Heading, int, int]]:
    query_lower = query.lower()
    matches = [h for h in headings if query_lower in h.text.lower()]
    bounds = []
    for h in matches:
        idx = headings.index(h)
        start = h.line_no
        # Section ends at the next heading of the same or shallower level.
        end = total_lines
        for later in headings[idx + 1:]:
            if later.level <= h.level:
                end = later.line_no
                break
        bounds.append((h, start, end))
    return bounds


def cmd_section(args: argparse.Namespace) -> int:
    lines = Path(args.kb_file).read_text(encoding="utf-8").splitlines()
    headings = parse_headings(lines)
    bounds = _find_section_bounds(headings, len(lines), args.heading)

    if not bounds:
        print(f"No heading matches '{args.heading}'. Run `outline` or `search` first to find the right one.",
              file=sys.stderr)
        return 1
    if len(bounds) > 1:
        print(f"'{args.heading}' matches {len(bounds)} headings -- ambiguous, extracting none:", file=sys.stderr)
        for h, _, _ in bounds:
            print(f"  {'#' * h.level} {h.text}", file=sys.stderr)
        print("Use a more specific match.", file=sys.stderr)
        return 1

    heading, start, end = bounds[0]
    section_text = "\n".join(lines[start:end])
    print(section_text)
    print(f"\n--- extracted '{heading.text}': {end - start} lines, "
          f"~{estimate_tokens(section_text):,} tokens (full file was "
          f"~{estimate_tokens(chr(10).join(lines)):,}) ---", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kb_file", help="Path to a knowledge-base markdown file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_outline = sub.add_parser("outline", help="Print the heading structure only")
    p_outline.set_defaults(func=cmd_outline)

    p_search = sub.add_parser("search", help="Find which sections mention a term")
    p_search.add_argument("term")
    p_search.set_defaults(func=cmd_search)

    p_section = sub.add_parser("section", help="Extract one section by heading text (substring match)")
    p_section.add_argument("heading")
    p_section.set_defaults(func=cmd_section)

    args = parser.parse_args()
    if not Path(args.kb_file).exists():
        print(f"ERROR: {args.kb_file} not found.", file=sys.stderr)
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
