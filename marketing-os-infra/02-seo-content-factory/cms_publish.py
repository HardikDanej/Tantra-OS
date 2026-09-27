"""
cms_publish.py
==============
Takes one finished, audited article (markdown + frontmatter, the shape the
Writing Agent contract requires — see ../../workflows/02-seo-content-factory/
orchestration.md, Contract #2 REQUIRED OUTPUT SHAPE) and creates a draft on
the configured CMS. This is deliverable #6 in that workflow: "WordPress
draft (published via MCP once the Orchestrator's synthesis completes)" —
this script is the actual mechanism behind that line.

Draft-only, always. See cms_connector.py's module docstring for why that
is enforced in code and not a flag you can flip here.

Expected article frontmatter:
    ---
    title: "Why Most Remote Teams Pick the Wrong PM Tool"
    slug: remote-team-pm-tool-mistakes
    meta_description: "..."
    focus_keyphrase: project management tool for remote teams
    topic: how to choose a project management tool for remote teams
    ---
    Article body in markdown starts here...

`topic` should match a `query` value in topic_queue.csv when this article
was produced from that queue. It's written to published_log.csv's `query`
column — the exact name and casing gsc_keyword_pull.py's `load_published()`
already reads to avoid re-queuing a topic that's been published. Optional
if you're publishing something ad hoc, but then it won't suppress
re-queuing on the next GSC pull.

Usage:
    python3 cms_publish.py --article drafts/remote-team-pm-tool.md
    python3 cms_publish.py --article drafts/foo.md --platform webflow
    python3 cms_publish.py --article drafts/foo.md --dry-run

`--dry-run` validates config + frontmatter + markdown conversion and
prints exactly what would be sent, without making the network call. Use
it to check the wiring before pointing this at a real site.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import markdown as md
except ImportError:
    md = None  # checked explicitly in main() with an actionable error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from cms_connector import PublishResult, publish_draft  # noqa: E402

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
PUBLISHED_LOG_PATH = ROOT / "published_log.csv"
# Column name is "query", not "topic", on purpose: gsc_keyword_pull.py's
# load_published() already reads published_log.csv looking for a "query"
# column (matched case-insensitively against topic_queue.csv's own "query"
# column) to avoid re-queuing a topic that's already been published.
# Renaming this would silently break that dedup with no error at either end.
LOG_FIELDS = ["published_at", "query", "platform", "status", "post_id", "draft_url", "article_path", "reason"]


class ArticleParseError(Exception):
    pass


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(
            f"FATAL: {CONFIG_PATH} not found. This workflow ships a config.json with "
            f"REPLACE_WITH_* placeholders committed — copy it if it's missing and fill "
            f"in real credentials (never commit those)."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def parse_article(path: Path) -> dict[str, Any]:
    """
    Split `path` into frontmatter (YAML) + body (markdown). Raises
    ArticleParseError with a specific reason rather than returning
    partial/guessed data — a mis-shaped article should stop the run, not
    publish with a missing title.
    """
    if not path.exists():
        raise ArticleParseError(f"article file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ArticleParseError(
            "article has no YAML frontmatter block (must start with '---') — "
            "this is the Writing Agent contract's REQUIRED OUTPUT SHAPE, not optional"
        )

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ArticleParseError("frontmatter block opened with '---' but never closed")

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise ArticleParseError(f"frontmatter is not valid YAML: {e}") from e

    if not isinstance(frontmatter, dict):
        raise ArticleParseError("frontmatter must be a YAML mapping (key: value pairs)")

    title = frontmatter.get("title")
    if not title:
        raise ArticleParseError("frontmatter is missing required field: title")

    body_markdown = parts[2].strip()
    if not body_markdown:
        raise ArticleParseError("article body is empty after the frontmatter block")

    return {
        "title": title,
        "slug": frontmatter.get("slug", ""),
        "meta_description": frontmatter.get("meta_description", ""),
        "focus_keyphrase": frontmatter.get("focus_keyphrase", ""),
        "topic": frontmatter.get("topic", ""),
        "body_markdown": body_markdown,
    }


def append_published_log(row: dict[str, Any]) -> None:
    is_new = not PUBLISHED_LOG_PATH.exists()
    with open(PUBLISHED_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--article", required=True, type=Path, help="Path to the markdown article file")
    parser.add_argument("--platform", choices=["wordpress", "webflow"], default=None,
                         help="Overrides cms.platform in config.json for this run")
    parser.add_argument("--dry-run", action="store_true",
                         help="Validate config + article + conversion; do not call the CMS API")
    args = parser.parse_args()

    config = load_config()
    platform = args.platform or config.get("cms", {}).get("platform", "wordpress")
    platform_config = config.get(platform, {})

    if not platform_config.get("enabled", True) and not args.dry_run:
        sys.exit(f"FATAL: {platform}.enabled is false in config.json — nothing to publish to.")

    try:
        article = parse_article(args.article)
    except ArticleParseError as e:
        sys.exit(f"FATAL: could not parse {args.article}: {e}")

    if md is None:
        sys.exit(
            "FATAL: the 'markdown' package is not installed. Run: pip install markdown pyyaml requests"
        )
    content_html = md.markdown(article["body_markdown"], extensions=["extra", "sane_lists"])

    print(f"\n{'='*60}")
    print(f"CMS publish — {platform}")
    print(f"{'='*60}")
    print(f"Title:   {article['title']}")
    print(f"Slug:    {article['slug'] or '(none)'}")
    print(f"Topic:   {article['topic'] or '(ad hoc, not tied to topic_queue.csv)'}")
    print(f"Meta:    {article['meta_description'][:80] or '(none)'}")

    if args.dry_run:
        print("\n--dry-run: config + article validated OK, no network call made.")
        print(f"Would POST a draft to '{platform}' with {len(content_html):,} chars of HTML body.")
        return

    result: PublishResult = publish_draft(
        platform,
        platform_config,
        title=article["title"],
        content_html=content_html,
        slug=article["slug"],
        excerpt=article["meta_description"],
    )

    if result.ok():
        # Only a genuine success gets a published_log.csv row: that file's
        # "query" column is what gsc_keyword_pull.py's load_published()
        # reads to decide a topic is done and stop re-queuing it. Logging a
        # failed attempt there would mark a never-actually-published topic
        # as published and silently drop it from every future keyword pull.
        append_published_log({
            "published_at": result.attempted_at,
            "query": article["topic"],
            "platform": result.platform,
            "status": result.status,
            "post_id": result.post_id or "",
            "draft_url": result.draft_url or "",
            "article_path": str(args.article),
            "reason": "",
        })
        print(f"\nOK: draft created on {platform}.")
        print(f"  post_id:   {result.post_id}")
        print(f"  draft_url: {result.draft_url}")
        print(f"  (is_draft={result.is_draft} — this script has no live-publish code path)")
        print(f"\nLogged to {PUBLISHED_LOG_PATH}")
    else:
        print(f"\nERROR: draft NOT created on {platform}.")
        print(f"  reason: {result.error.reason}")
        print(f"  detail: {result.error.detail}")
        print(f"\nNOT written to {PUBLISHED_LOG_PATH} — a failed attempt must not mark this "
              f"topic as already published, or it silently drops out of future GSC pulls. "
              f"Fix the error above and rerun.")
        sys.exit(1)


if __name__ == "__main__":
    main()
