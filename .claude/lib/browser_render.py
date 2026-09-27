"""
browser_render.py
==================
Self-hosted, free real-browser rendering for the Website Development Agent
(and any other agent that hits the same ceiling). `WebFetch` does a plain
HTTP fetch — it cannot execute JavaScript, so a JS-rendered SPA looks like
an empty shell, and a page behind a basic bot-detection JS challenge looks
like a block. Both of those are things a *real* browser resolves as a side
effect of just being a real browser. This wraps a real, local, headless
Chromium (via Playwright) so the agent can get an honest answer instead of
reporting "unverified" on every page that isn't plain server-rendered HTML.

Why self-hosted instead of a paid rendering API (ScrapingBee, Browserless,
ScraperAPI, etc.): those cost per request and this need is occasional and
diagnostic, not high-volume. Playwright + a local Chromium is free, and
free is the right default before paying for infrastructure this project
doesn't need yet. If a real future need for scale, proxy rotation, or
managed CAPTCHA-solving shows up, that's a distinct, explicit decision to
add a paid vendor — not something to quietly build into this module.

What this deliberately does NOT do — read this before "improving" it:
- No CAPTCHA solving, no third-party unblocking service, no stealth/evasion
  plugins (e.g. playwright-stealth), no fingerprint spoofing, no proxy
  rotation to dodge IP-based rate limiting. If a page returns a real
  bot-challenge or CAPTCHA, this script reports `status: "blocked"` and
  stops — the same stop condition the agent already has for WebFetch, not
  a prompt to retry harder. A real browser legitimately clears a basic JS
  "checking your browser" interstitial as a side effect of executing JS
  like any other visitor's browser would; it does not, and must not be
  made to, get past an actual challenge designed to stop automation.
- No form submission, no clicking anything that posts data or triggers a
  side effect on the target site (a "Send"/"Submit"/"Subscribe" button).
  This is a read-only diagnostic tool, same boundary the agent itself
  operates under: diagnose, never act on the live site. The one exception
  is a non-destructive UI toggle probe (`--click-selector`) meant for
  things like "does the mobile nav actually open" — it clicks, then only
  reads back DOM state, never anything that looks like a form control.

Usage:
    python3 browser_render.py https://example.com
    python3 browser_render.py https://example.com --wait-selector ".hero"
    python3 browser_render.py https://example.com --click-selector "button.nav-toggle" --wait-selector "nav.open"
    python3 browser_render.py https://example.com --screenshot out/shot.png --out out/page.html

Prints a compact JSON result to stdout (for the calling agent to parse).
Full rendered HTML is written to `--out` (default: a temp file path printed
in the result) rather than dumped to stdout, since a rendered page can
easily be hundreds of KB — an agent's context budget shouldn't pay for
that by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

RenderStatus = Literal["ok", "blocked", "error"]

# Heuristic signals for a real bot-challenge/CAPTCHA page, not a broken
# page. Checked against the rendered title + a slice of body text. This is
# read-only pattern matching for REPORTING a block — never used to decide
# "so try to get past it."
_BLOCK_SIGNALS = [
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-browser-verification",
    "cf-chl-",
    "verify you are human",
    "captcha",
    "access denied",
    "request unsuccessful",
]


class RenderError(BaseModel):
    reason: str
    detail: str | None = None


class RenderResult(BaseModel):
    url: str
    final_url: str | None = None
    status: RenderStatus
    http_status: int | None = None
    title: str | None = None
    blocked_reason: str | None = None
    html_path: str | None = None
    screenshot_path: str | None = None
    text_excerpt: str | None = None
    render_time_ms: int | None = None
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: RenderError | None = None

    def ok(self) -> bool:
        return self.status == "ok"


def _detect_block(title: str, body_sample: str, http_status: int | None) -> str | None:
    haystack = f"{title}\n{body_sample}".lower()
    for signal in _BLOCK_SIGNALS:
        if signal in haystack:
            return signal
    if http_status in (403, 503) and http_status is not None:
        return f"http_{http_status}_no_matched_challenge_text"
    return None


def render_page(
    url: str,
    *,
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "networkidle",
    wait_selector: str | None = None,
    click_selector: str | None = None,
    timeout_ms: int = 30_000,
    html_out_path: Path | None = None,
    screenshot_path: Path | None = None,
) -> RenderResult:
    """
    Render `url` in a real headless Chromium and return a typed result.
    Never raises past this boundary — every failure mode (timeout, DNS
    error, navigation error, detected block) comes back as a RenderResult
    with `status` set honestly, never as an exception the caller has to
    guess the meaning of.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return RenderResult(
            url=url, status="error",
            error=RenderError(
                reason="playwright_not_installed",
                detail="Run: pip install playwright && python -m playwright install chromium",
            ),
        )

    if click_selector and any(bad in click_selector.lower() for bad in ("submit", "send", "subscribe")):
        return RenderResult(
            url=url, status="error",
            error=RenderError(
                reason="refused_selector",
                detail=(
                    f"--click-selector {click_selector!r} looks like a form-submission control. "
                    f"This tool is read-only diagnostics and refuses to click anything that "
                    f"looks like it submits data to the target site. Use a UI-toggle selector "
                    f"(nav/menu/accordion) instead, or note the finding for a human to test."
                ),
            ),
        )

    started = datetime.now(timezone.utc)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                response = page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                http_status = response.status if response else None

                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=timeout_ms)
                    except Exception as e:
                        browser.close()
                        return RenderResult(
                            url=url, final_url=page.url, status="error", http_status=http_status,
                            error=RenderError(
                                reason="wait_selector_not_found",
                                detail=f"{wait_selector!r} did not appear within {timeout_ms}ms: {e}"[:500],
                            ),
                        )

                if click_selector:
                    try:
                        page.click(click_selector, timeout=timeout_ms)
                        page.wait_for_timeout(500)  # let any resulting UI transition settle
                    except Exception as e:
                        browser.close()
                        return RenderResult(
                            url=url, final_url=page.url, status="error", http_status=http_status,
                            error=RenderError(
                                reason="click_selector_failed",
                                detail=f"{click_selector!r} could not be clicked: {e}"[:500],
                            ),
                        )

                title = page.title()
                html = page.content()
                body_text = re.sub(r"\s+", " ", page.inner_text("body"))[:2000] if page.query_selector("body") else ""

                blocked_reason = _detect_block(title, body_text, http_status)

                if screenshot_path:
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot_path), full_page=True)

                final_url = page.url
                browser.close()
            except Exception:
                browser.close()
                raise
    except Exception as e:
        return RenderResult(
            url=url, status="error",
            error=RenderError(reason="navigation_failed", detail=str(e)[:500]),
        )

    if html_out_path is None:
        fd, tmp_name = tempfile.mkstemp(prefix="browser_render_", suffix=".html")
        html_out_path = Path(tmp_name)
    html_out_path.parent.mkdir(parents=True, exist_ok=True)
    html_out_path.write_text(html, encoding="utf-8")

    render_time_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    return RenderResult(
        url=url,
        final_url=final_url,
        status="blocked" if blocked_reason else "ok",
        http_status=http_status,
        title=title,
        blocked_reason=blocked_reason,
        html_path=str(html_out_path),
        screenshot_path=str(screenshot_path) if screenshot_path else None,
        text_excerpt=body_text[:500],
        render_time_ms=render_time_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--wait-until", choices=["load", "domcontentloaded", "networkidle"], default="networkidle")
    parser.add_argument("--wait-selector", default=None, help="CSS selector that must appear — proves JS-rendered content actually mounted")
    parser.add_argument("--click-selector", default=None,
                         help="CSS selector for a non-destructive UI toggle to click (nav/menu/accordion). "
                              "Refused if it looks like a submit/send/subscribe control.")
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--out", default=None, help="Where to write the full rendered HTML (default: a temp file)")
    parser.add_argument("--screenshot", default=None, help="Where to write a full-page screenshot (PNG)")
    args = parser.parse_args()

    result = render_page(
        args.url,
        wait_until=args.wait_until,
        wait_selector=args.wait_selector,
        click_selector=args.click_selector,
        timeout_ms=args.timeout_ms,
        html_out_path=Path(args.out) if args.out else None,
        screenshot_path=Path(args.screenshot) if args.screenshot else None,
    )

    print(json.dumps(json.loads(result.model_dump_json()), indent=2))

    if result.status == "blocked":
        print(
            f"\nBLOCKED: {result.blocked_reason!r} — this is a real bot-challenge/CAPTCHA signal, "
            f"not a tool failure. Report it as a stop condition (same as a blocked WebFetch), "
            f"do not retry with different settings to try to get past it.",
            file=sys.stderr,
        )
        return 2
    if result.status == "error":
        print(f"\nERROR: {result.error.reason} — {result.error.detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
