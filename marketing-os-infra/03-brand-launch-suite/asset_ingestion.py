"""
asset_ingestion.py
==================
Walk the inputs/ folder, normalize all asset types, and produce brand_inputs.json
that the chat workflow consumes as a unified knowledge base.

Supported formats:
- PDF (text extraction via PyPDF2)
- DOCX (python-docx)
- HTML (BeautifulSoup → markdownify for clean markdown)
- Markdown (passthrough)
- TXT (passthrough)
- CSV (read as structured data, summarized in JSON)
- MP3/WAV/M4A audio (Whisper transcription — local, no API)

The output JSON has this structure:
{
    "ingestion_metadata": {
        "generated_at": "...",
        "total_assets": 47,
        "asset_count_by_category": {...},
        "asset_count_by_format": {...}
    },
    "assets": [
        {
            "id": "interviews_001",
            "category": "interviews",
            "filename": "founder_2024_10_15.pdf",
            "format": "pdf",
            "extracted_at": "...",
            "word_count": 4823,
            "content": "...",
            "metadata": {...}
        },
        ...
    ]
}

Run:
    python3 asset_ingestion.py
    python3 asset_ingestion.py --skip-audio   # if Whisper not installed
    python3 asset_ingestion.py --whisper-model base   # default; tiny/base/small/medium
"""

import argparse
import csv
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from tool_router import SourceError  # noqa: E402

ROOT = Path(__file__).resolve().parent
INPUTS_DIR = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

CATEGORIES = ["interviews", "web", "social", "customer", "prior_brand", "competitive"]
SUPPORTED_FORMATS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".html": "html",
    ".htm": "html",
    ".md": "markdown",
    ".txt": "text",
    ".csv": "csv",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
}


def extract_pdf(path: Path) -> tuple[str, dict]:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return "", {"error": "PyPDF2 not installed"}
    reader = PdfReader(str(path))
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n\n".join(text_parts)
    return text, {"page_count": len(reader.pages)}


def extract_docx(path: Path) -> tuple[str, dict]:
    try:
        from docx import Document
    except ImportError:
        return "", {"error": "python-docx not installed"}
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs), {"paragraph_count": len(paragraphs)}


def extract_html(path: Path) -> tuple[str, dict]:
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify
    except ImportError:
        return "", {"error": "beautifulsoup4 or markdownify not installed"}
    with open(path, encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    # Strip nav, footer, script, style — they pollute brand voice analysis
    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()
    title = soup.title.string if soup.title else ""
    cleaned_html = str(soup)
    md = markdownify(cleaned_html, heading_style="ATX")
    # Compress whitespace
    while "\n\n\n" in md:
        md = md.replace("\n\n\n", "\n\n")
    return md, {"title": title}


def extract_markdown(path: Path) -> tuple[str, dict]:
    with open(path, encoding="utf-8") as f:
        return f.read(), {}


def extract_text(path: Path) -> tuple[str, dict]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(), {}


def extract_csv(path: Path) -> tuple[str, dict]:
    """For CSVs, we generate a structured summary plus a sample of rows.
    The full CSV stays accessible for the chat workflow if needed."""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append(row)
            if i >= 50:  # cap sample size
                break

    if not rows:
        return "", {"error": "empty CSV"}

    headers = list(rows[0].keys())

    # Build a readable text representation for the LLM
    lines = [
        f"CSV with {len(headers)} columns: {', '.join(headers)}",
        f"Sample of {len(rows)} rows:",
        "",
    ]
    for row in rows[:20]:
        lines.append(" | ".join(f"{k}: {v}" for k, v in row.items() if v))

    return "\n".join(lines), {"columns": headers, "rows_sampled": len(rows)}


def extract_audio(path: Path, model_name: str = "base") -> tuple[str, dict]:
    try:
        import whisper
    except ImportError:
        return "", {"error": "openai-whisper not installed"}
    logging.info(f"Transcribing {path.name} with Whisper {model_name}... (slow)")
    model = whisper.load_model(model_name)
    result = model.transcribe(str(path), fp16=False)
    return result["text"], {
        "language": result.get("language", "unknown"),
        "duration_minutes": round(len(result.get("segments", [])) * 0.5, 1),
    }


EXTRACTORS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "html": extract_html,
    "markdown": extract_markdown,
    "text": extract_text,
    "csv": extract_csv,
}


def asset_id(category: str, filename: str, idx: int) -> str:
    return f"{category}_{idx:03d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-audio", action="store_true",
                        help="Skip audio files (Whisper not available)")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    if not INPUTS_DIR.exists():
        sys.exit(f"FATAL: {INPUTS_DIR} does not exist. Create it and the category subfolders.")

    assets: list[dict] = []
    manifest_rows: list[dict] = []
    counts_by_category: dict[str, int] = {c: 0 for c in CATEGORIES}
    counts_by_format: dict[str, int] = {}
    ingestion_errors: list[SourceError] = []

    for category in CATEGORIES:
        cat_dir = INPUTS_DIR / category
        if not cat_dir.exists():
            logging.debug(f"Category folder missing: {cat_dir}")
            continue

        for path in sorted(cat_dir.iterdir()):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in SUPPORTED_FORMATS:
                logging.debug(f"Skipping unsupported file: {path.name}")
                continue

            fmt = SUPPORTED_FORMATS[ext]
            print(f"[{fmt.upper()}] Processing {category}/{path.name}...")

            try:
                if fmt == "audio":
                    if args.skip_audio:
                        logging.info(f"Skipping audio (--skip-audio): {path.name}")
                        continue
                    content, meta = extract_audio(path, args.whisper_model)
                else:
                    extractor = EXTRACTORS[fmt]
                    content, meta = extractor(path)
            except Exception as e:
                logging.error(f"Failed to extract {path}: {e}")
                ingestion_errors.append(SourceError(
                    source_id=f"{category}/{path.name}", reason="extraction_failed", detail=str(e)[:500],
                ))
                continue

            if meta.get("error"):
                # Extractor caught its own failure (missing optional dependency,
                # e.g. PyPDF2/python-docx not installed) and returned empty
                # content instead of raising — still a real failure, not a
                # legitimately empty file, so it must be recorded the same way.
                logging.error(f"Extractor reported error for {path.name}: {meta['error']}")
                ingestion_errors.append(SourceError(
                    source_id=f"{category}/{path.name}", reason="extractor_dependency_missing",
                    detail=meta["error"],
                ))
                continue

            if not content or len(content.strip()) < 50:
                logging.warning(f"Empty/tiny content from {path.name}, skipping")
                ingestion_errors.append(SourceError(
                    source_id=f"{category}/{path.name}", reason="empty_or_tiny_content",
                    detail=f"{len(content.strip()) if content else 0} chars extracted, floor is 50",
                ))
                continue

            counts_by_category[category] += 1
            counts_by_format[fmt] = counts_by_format.get(fmt, 0) + 1

            aid = asset_id(category, path.name, counts_by_category[category])
            asset = {
                "id": aid,
                "category": category,
                "filename": path.name,
                "format": fmt,
                "extracted_at": datetime.utcnow().isoformat() + "Z",
                "word_count": len(content.split()),
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "content": content,
                "metadata": meta,
            }
            assets.append(asset)
            manifest_rows.append({
                "id": aid,
                "category": category,
                "filename": path.name,
                "format": fmt,
                "word_count": asset["word_count"],
                "extracted_at": asset["extracted_at"],
            })

    if not assets and not ingestion_errors:
        sys.exit("No assets ingested. Check that inputs/ subfolders contain supported files.")

    output = {
        "ingestion_metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_assets": len(assets),
            "total_words": sum(a["word_count"] for a in assets),
            "asset_count_by_category": counts_by_category,
            "asset_count_by_format": counts_by_format,
            "files_failed_or_skipped": len(ingestion_errors),
        },
        "assets": assets,
    }

    output_path = ROOT / "brand_inputs.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    manifest_path = ROOT / "inputs_manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        if manifest_rows:
            writer = csv.DictWriter(f, fieldnames=manifest_rows[0].keys())
            writer.writeheader()
            writer.writerows(manifest_rows)

    # Every extraction failure/skip, not just a log line that scrolls away —
    # this is what the Marketing Strategist Agent must check before trusting
    # `total_assets` against its 5-asset (or 30-asset) floor. A brand with
    # 47 files on disk and 12 silent extraction failures should never read
    # as confidently "47 real assets."
    errors_path = ROOT / "brand_inputs.errors.json"
    with open(errors_path, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "files_failed_or_skipped": len(ingestion_errors),
            "errors": [json.loads(e.model_dump_json()) for e in ingestion_errors],
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ {output_path} written ({output_path.stat().st_size / 1024:.1f} KB)")
    print(f"✓ {manifest_path} written ({len(manifest_rows)} rows)")
    print(f"✓ {errors_path} written ({len(ingestion_errors)} failed/skipped files) — CHECK THIS before trusting the asset count")
    print(f"\nIngestion summary:")
    print(f"  Total assets: {len(assets)}")
    print(f"  Total words: {output['ingestion_metadata']['total_words']:,}")
    print(f"  By category:")
    for cat, count in counts_by_category.items():
        if count > 0:
            print(f"    {cat}: {count}")
    print(f"  By format:")
    for fmt, count in counts_by_format.items():
        print(f"    {fmt}: {count}")
    if ingestion_errors:
        print(f"\n  Failed/skipped ({len(ingestion_errors)}):")
        for err in ingestion_errors[:20]:
            print(f"    - {err.source_id}: {err.reason} — {err.detail}")
        if len(ingestion_errors) > 20:
            print(f"    ... and {len(ingestion_errors) - 20} more, see {errors_path}")

    # Calibration warning
    if len(assets) < 10:
        print(f"\n⚠️  Only {len(assets)} assets ingested. Brand foundation work")
        print(f"   typically requires 30+ inputs for confident outputs. Consider")
        print(f"   gathering more material before running the chat workflow.")


if __name__ == "__main__":
    main()
