"""
citation_guard.py
==================
Deterministic citation checker. Extracts every URL, dollar figure,
percentage, ranking position, and large/suffixed number from a draft of an
agent's output, then checks each one against the evidence ledger built by
`evidence_log.py` (the raw text of what WebFetch/WebSearch calls actually
returned this session).

This is the "structurally can't" half of the guardrail. It does not use
the model to judge the model's own output — it's regex extraction plus a
literal substring/URL match against files on disk. It will have false
positives (a legitimately-computed number that isn't verbatim in any
single source, e.g. "23% CTR" derived from clicks/impressions on a fetched
page) and false negatives (a hallucinated number that happens to also
appear somewhere in the evidence by coincidence). It is not a hallucination
oracle. What it reliably catches is the failure mode this guardrail exists
for: a number or URL that traces to NOTHING actually retrieved this
session — which is exactly what "asked nicely not to lie" fails to catch,
because the model has no external check on its own memory.

Known weak spot: small numbers (a rank like "#3", a single-digit percent)
are matched by exact numeric value against every token in the evidence
corpus, with no notion of which claim a given evidence number was
originally attached to. A fabricated "#3" ranking will verify as long as
the digit 3 appears anywhere in the evidence for an unrelated reason (a
date, an unrelated count). Treat a VERIFIED verdict on a 1-2 digit claim
as a weaker signal than a VERIFIED verdict on a distinctive multi-digit
figure, and spot-check rank/position claims by eye regardless of verdict.

Usage:
    python citation_guard.py <ledger.json> <draft.txt> [--json-out report.json]

Exit code 0: every extracted claim matched the evidence, OR nothing citable
             was found in the draft.
Exit code 1: at least one claim is UNVERIFIED — could not be traced to any
             logged evidence. The calling agent must not present an
             UNVERIFIED claim as confirmed fact: cut it, show the
             computation from a VERIFIED source number, or move it to GAPS.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Extraction patterns. Deliberately over-inclusive — a false positive here
# just means one more claim gets checked and (likely) verified; a false
# negative means a real citation slips past unchecked, which is the worse
# direction of error for a guardrail whose job is to be suspicious.
# ---------------------------------------------------------------------------

URL_RE = re.compile(r"https?://[^\s)>\]\"'.,]+(?:\.[^\s)>\]\"'.,]+)*[^\s)>\]\"'.,;]")
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?[kKmMbB]?(?:illion)?\b")
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%")
RANK_RE = re.compile(r"#\d{1,3}\b|\bposition\s+\d{1,3}\b", re.IGNORECASE)
SUFFIXED_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\s?[kKmMbB]\b(?!\w)")
COMMA_NUM_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b")

CLAIM_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("url", URL_RE),
    ("money", MONEY_RE),
    ("percent", PERCENT_RE),
    ("rank", RANK_RE),
    ("suffixed_number", SUFFIXED_NUM_RE),
    ("comma_number", COMMA_NUM_RE),
]


NUMBER_TOKEN_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def claim_to_float(claim_text: str) -> float | None:
    """Strip currency/percent/suffix symbols down to the numeral, parsed as a float."""
    digits = re.sub(r"[^\d.]", "", claim_text)
    if not digits or digits == ".":
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def extract_claims(draft_text: str) -> list[dict]:
    claims: list[dict] = []
    seen_spans: set[tuple[int, int]] = set()
    for claim_type, pattern in CLAIM_PATTERNS:
        for m in pattern.finditer(draft_text):
            span = m.span()
            # Skip a span already claimed by an earlier (more specific) pattern
            # — e.g. don't double-report "47,000" both as comma_number and as
            # part of a money match "$47,000".
            if any(span[0] >= s and span[1] <= e for s, e in seen_spans):
                continue
            seen_spans.add(span)
            claims.append({"type": claim_type, "text": m.group(0).strip()})
    return claims


def load_evidence_corpus(ledger_path: Path) -> tuple[str, set[float], list[str], list[dict]]:
    """
    Returns (raw concatenated text corpus, set of distinct numeric token
    values found in it, list of logged URLs, raw ledger records).

    The numeric set is extracted token-by-token from the ORIGINAL text
    (respecting word/number boundaries), not by stripping punctuation from
    the whole concatenated corpus into one digit blob first — that earlier
    approach could false-verify a fabricated number that happened to appear
    as a substring spanning two unrelated numbers once boundaries were
    erased (e.g. "51,200,003" and "1200000" colliding after stripping).
    Per-token float equality avoids that class of false positive.
    """
    if not ledger_path.exists():
        return "", set(), [], []
    records = json.loads(ledger_path.read_text(encoding="utf-8"))
    texts = []
    urls = []
    numbers: set[float] = set()
    for r in records:
        content_path = Path(r["content_path"])
        if content_path.exists():
            content = content_path.read_text(encoding="utf-8", errors="replace")
            texts.append(content)
            for m in NUMBER_TOKEN_RE.finditer(content):
                try:
                    numbers.add(float(m.group(0).replace(",", "")))
                except ValueError:
                    continue
        if r.get("url"):
            urls.append(r["url"])
    return "\n".join(texts), numbers, urls, records


def verify_url_claim(url_text: str, corpus: str, logged_urls: list[str]) -> tuple[str, str | None]:
    url_text = url_text.rstrip(").,;'\"")
    if url_text in logged_urls or url_text in corpus:
        return "VERIFIED", "exact match in evidence"
    # Domain-level fallback: the exact path may differ (redirects, tracking
    # params) but the same domain was genuinely fetched this session.
    try:
        domain = urlparse(url_text).netloc
    except ValueError:
        domain = ""
    if domain and any(domain in u for u in logged_urls):
        return "VERIFIED", f"domain '{domain}' matches a logged fetch (exact path not confirmed)"
    return "UNVERIFIED", None


def verify_numeric_claim(claim_text: str, corpus_numbers: set[float]) -> tuple[str, str | None]:
    value = claim_to_float(claim_text)
    if value is None:
        return "UNVERIFIED", None
    if any(abs(value - n) < 1e-6 for n in corpus_numbers):
        return "VERIFIED", "numeric value matches a token in evidence"
    return "UNVERIFIED", None


def run_guard(ledger_path: Path, draft_path: Path) -> dict:
    draft_text = draft_path.read_text(encoding="utf-8", errors="replace")
    corpus, corpus_numbers, logged_urls, records = load_evidence_corpus(ledger_path)

    claims = extract_claims(draft_text)
    results = []
    for c in claims:
        if c["type"] == "url":
            verdict, reason = verify_url_claim(c["text"], corpus, logged_urls)
        else:
            verdict, reason = verify_numeric_claim(c["text"], corpus_numbers)
        results.append({**c, "verdict": verdict, "reason": reason})

    verified = [r for r in results if r["verdict"] == "VERIFIED"]
    unverified = [r for r in results if r["verdict"] == "UNVERIFIED"]

    return {
        "draft_file": str(draft_path),
        "ledger_file": str(ledger_path),
        "evidence_records_available": len(records),
        "claims_found": len(results),
        "verified_count": len(verified),
        "unverified_count": len(unverified),
        "overall": "PASS" if not unverified else "FAIL",
        "claims": results,
    }


def print_report(report: dict) -> None:
    print(f"\nCitation guard: {report['claims_found']} claim(s) found in draft, "
          f"checked against {report['evidence_records_available']} evidence record(s).")
    print(f"Result: {report['overall']} "
          f"({report['verified_count']} verified, {report['unverified_count']} unverified)\n")
    if report["unverified_count"]:
        print("UNVERIFIED claims — do not present these as confirmed fact. Cut them, show the "
              "computation from a verified source number, or move them to GAPS:")
        for r in report["claims"]:
            if r["verdict"] == "UNVERIFIED":
                print(f"  - [{r['type']}] \"{r['text']}\"")
    if report["evidence_records_available"] == 0 and report["claims_found"] > 0:
        print("NOTE: the evidence ledger is empty. Every numeric/URL claim in this draft is "
              "unverified by definition — either this research didn't use evidence_log.py, or "
              "no real tool calls back these claims yet.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ledger", help="Path to the evidence ledger JSON (from evidence_log.py)")
    parser.add_argument("draft", help="Path to a text file containing the agent's draft output")
    parser.add_argument("--json-out", default=None, help="Write the full JSON report here")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    draft_path = Path(args.draft)
    if not draft_path.exists():
        print(f"ERROR: draft file {draft_path} does not exist.", file=sys.stderr)
        return 2

    report = run_guard(ledger_path, draft_path)
    print_report(report)

    json_out = Path(args.json_out) if args.json_out else draft_path.with_suffix(draft_path.suffix + ".citation_report.json")
    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Full report: {json_out}")

    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
