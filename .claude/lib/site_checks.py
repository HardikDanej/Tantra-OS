#!/usr/bin/env python3
"""Tantra site checks: deterministic, zero-token technical checks on one URL.

Replaces the part of technical/on-page/schema/performance/security specialist
work that is measurement rather than judgment. Specialists run this, then
spend their tokens only on interpreting the result.

Every value here is OBSERVED from a real fetch. `flags` are rule-based
(e.g. title over 60 chars), not judgments about ranking or conversion impact.

Results are cached per URL + options for 24h in ~/.tantra/site_checks/, so
several specialists auditing the same page share one fetch.

Usage:
    python site_checks.py <url> [--pagespeed] [--links N] [--no-cache]

    --pagespeed   also call the free PageSpeed Insights API (mobile); slow, ~20-60s.
                  Set PAGESPEED_API_KEY for a reliable quota; keyless calls often hit 429.
    --links N     status-check the first N internal links (default 0)

Prints one JSON object and exits 0, even on failure ({"error": ...}).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (compatible; TantraSiteChecks/1.0)"
TIMEOUT = 20
CACHE_DIR = pathlib.Path.home() / ".tantra" / "site_checks"
CACHE_TTL = 24 * 3600
SECURITY_HEADERS = ["strict-transport-security", "content-security-policy",
                    "x-content-type-options", "x-frame-options",
                    "referrer-policy", "permissions-policy"]


def _get(session, url, **kw):
    start = time.time()
    r = session.get(url, timeout=TIMEOUT, allow_redirects=True, **kw)
    return r, round((time.time() - start) * 1000)


def fetch_page(session, url):
    r, ms = _get(session, url)
    return r, {
        "requested_url": url,
        "final_url": r.url,
        "status": r.status_code,
        "redirect_chain": [f"{h.status_code} {h.url}" for h in r.history],
        "https": r.url.startswith("https://"),
        "response_ms": ms,
        "html_bytes": len(r.content),
    }


def header_checks(r):
    h = {k.lower(): v for k, v in r.headers.items()}
    return {
        "security_headers_present": [x for x in SECURITY_HEADERS if x in h],
        "security_headers_missing": [x for x in SECURITY_HEADERS if x not in h],
        "cache_control": h.get("cache-control"),
        "content_encoding": h.get("content-encoding"),
        "server": h.get("server"),
        "x_powered_by": h.get("x-powered-by"),
    }


def onpage_checks(soup, base_url):
    def meta(name=None, prop=None):
        tag = soup.find("meta", attrs={"name": name} if name else {"property": prop})
        return tag.get("content", "").strip() if tag else None

    title = soup.title.get_text(strip=True) if soup.title else None
    desc = meta(name="description")
    headings = [(int(t.name[1]), t.get_text(" ", strip=True)[:120])
                for t in soup.find_all(re.compile(r"^h[1-6]$"))]
    skips = [f"h{a}->h{b}" for (a, _), (b, _) in zip(headings, headings[1:]) if b > a + 1]
    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    host = urlparse(base_url).netloc
    internal, external = set(), set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"]).split("#")[0]
        if not href.startswith("http"):
            continue
        (internal if urlparse(href).netloc == host else external).add(href)
    imgs = soup.find_all("img")
    missing_alt = [i.get("src", "")[:120] for i in imgs if not (i.get("alt") or "").strip()]
    text = soup.get_text(" ", strip=True)
    return {
        "title": title, "title_length": len(title) if title else 0,
        "meta_description": desc, "meta_description_length": len(desc) if desc else 0,
        "h1": [t for lvl, t in headings if lvl == 1],
        "heading_count": len(headings), "heading_level_skips": skips,
        "canonical": canonical.get("href") if canonical else None,
        "robots_meta": meta(name="robots"),
        "viewport": meta(name="viewport"),
        "html_lang": (soup.html.get("lang") if soup.html else None),
        "hreflang_count": len(soup.find_all("link", hreflang=True)),
        "open_graph": {k: meta(prop=f"og:{k}") for k in ("title", "description", "image", "type")},
        "twitter_card": meta(name="twitter:card"),
        "images": len(imgs), "images_missing_alt": len(missing_alt),
        "images_missing_alt_sample": missing_alt[:10],
        "internal_links": len(internal), "external_links": len(external),
        "word_count": len(text.split()),
        "_internal_link_list": sorted(internal),
    }


def schema_checks(soup):
    blocks, types, errors = soup.find_all("script", type="application/ld+json"), [], []

    def collect(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if t:
                types.extend(t if isinstance(t, list) else [t])
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    for i, b in enumerate(blocks):
        try:
            collect(json.loads(b.string or b.get_text() or ""))
        except Exception as e:
            errors.append(f"block {i}: {str(e)[:120]}")
    return {
        "jsonld_blocks": len(blocks),
        "jsonld_types": sorted(set(types)),
        "jsonld_parse_errors": errors,
        "microdata_items": len(soup.find_all(attrs={"itemscope": True})),
    }


def site_files(session, final_url):
    root = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
    out = {}
    for name in ("robots.txt", "sitemap.xml", "llms.txt"):
        try:
            r, _ = _get(session, f"{root}/{name}")
            out[name] = {"status": r.status_code, "bytes": len(r.content)}
            if name == "robots.txt" and r.ok:
                body = r.text
                out[name]["sitemaps"] = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", body)
                out[name]["disallow_all"] = bool(re.search(r"(?im)^\s*disallow:\s*/\s*$", body))
                out[name]["ai_bot_rules"] = sorted(set(re.findall(
                    r"(?im)^\s*user-agent:\s*(GPTBot|ClaudeBot|anthropic-ai|PerplexityBot|Google-Extended|CCBot|OAI-SearchBot)\b", body)))
            if name == "sitemap.xml" and r.ok:
                out[name]["loc_count"] = len(re.findall(r"<loc>", r.text))
                out[name]["is_index"] = "<sitemapindex" in r.text
        except Exception as e:
            out[name] = {"error": str(e)[:160]}
    return out


def link_checks(session, links, n):
    results = []
    for url in links[:n]:
        try:
            r = session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code in (405, 403):
                r = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
            results.append({"url": url, "status": r.status_code})
        except Exception as e:
            results.append({"url": url, "error": str(e)[:120]})
    return {"checked": len(results),
            "broken": [x for x in results if x.get("error") or x.get("status", 0) >= 400]}


def pagespeed(session, url):
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": "mobile"}
    if os.environ.get("PAGESPEED_API_KEY"):
        params["key"] = os.environ["PAGESPEED_API_KEY"]
    r = session.get(api, params=params, timeout=120)
    if not r.ok:
        hint = (" -- the keyless quota is shared and often exhausted; set PAGESPEED_API_KEY "
                "(free, Google Cloud console) for a reliable quota") if r.status_code == 429 else ""
        return {"error": f"PSI HTTP {r.status_code}{hint}"}
    d = r.json()
    lh = d.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    lab = {k: audits.get(k, {}).get("displayValue") for k in (
        "largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time",
        "first-contentful-paint", "speed-index", "server-response-time")}
    field = {k: v.get("percentile") for k, v in
             d.get("loadingExperience", {}).get("metrics", {}).items()}
    opps = sorted(
        [(a.get("details", {}).get("overallSavingsMs", 0), a.get("title")) for a in audits.values()
         if a.get("details", {}).get("type") == "opportunity" and a.get("details", {}).get("overallSavingsMs")],
        reverse=True)[:6]
    return {
        "strategy": "mobile",
        "performance_score": round((lh.get("categories", {}).get("performance", {}).get("score") or 0) * 100),
        "lab": lab,
        "field_percentiles": field or None,
        "field_overall": d.get("loadingExperience", {}).get("overall_category"),
        "top_opportunities": [{"title": t, "savings_ms": round(ms)} for ms, t in opps],
    }


def flags(res):
    f, p = [], res.get("onpage", {})
    if p:
        if not p["title"]:
            f.append("missing <title>")
        elif p["title_length"] > 60:
            f.append(f"title is {p['title_length']} chars (>60, likely truncated in SERPs)")
        if not p["meta_description"]:
            f.append("missing meta description")
        elif not 70 <= p["meta_description_length"] <= 160:
            f.append(f"meta description is {p['meta_description_length']} chars (outside 70-160)")
        if len(p["h1"]) != 1:
            f.append(f"{len(p['h1'])} <h1> elements (expected 1)")
        if p["heading_level_skips"]:
            f.append(f"heading level skips: {', '.join(p['heading_level_skips'][:5])}")
        if not p["canonical"]:
            f.append("no canonical link")
        if p["robots_meta"] and "noindex" in p["robots_meta"].lower():
            f.append("robots meta contains noindex")
        if not p["viewport"]:
            f.append("no viewport meta (mobile rendering risk)")
        if not p["html_lang"]:
            f.append("no <html lang>")
        if p["images_missing_alt"]:
            f.append(f"{p['images_missing_alt']}/{p['images']} images missing alt text")
        if not p["open_graph"].get("image"):
            f.append("no og:image")
    s = res.get("schema", {})
    if s and not s["jsonld_blocks"] and not s["microdata_items"]:
        f.append("no structured data found")
    for e in s.get("jsonld_parse_errors", []):
        f.append(f"JSON-LD parse error: {e}")
    fx = res.get("fetch", {})
    if fx and not fx["https"]:
        f.append("final URL is not HTTPS")
    if len(fx.get("redirect_chain", [])) > 1:
        f.append(f"{len(fx['redirect_chain'])}-hop redirect chain")
    h = res.get("headers", {})
    if h.get("security_headers_missing"):
        f.append("missing security headers: " + ", ".join(h["security_headers_missing"]))
    sf = res.get("site_files", {})
    if sf.get("robots.txt", {}).get("status") not in (200, None):
        f.append(f"robots.txt returned {sf['robots.txt'].get('status')}")
    if sf.get("robots.txt", {}).get("disallow_all"):
        f.append("robots.txt contains 'Disallow: /' (check which user-agent group)")
    if sf.get("sitemap.xml", {}).get("status") != 200 and not sf.get("robots.txt", {}).get("sitemaps"):
        f.append("no sitemap at /sitemap.xml and none declared in robots.txt")
    if sf.get("llms.txt", {}).get("status") != 200:
        f.append("no /llms.txt")
    for b in res.get("links", {}).get("broken", []):
        f.append(f"broken internal link: {b['url']} ({b.get('status', b.get('error'))})")
    return f


def run(url, do_psi, n_links):
    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as e:
        return {"error": f"missing dependency: {e} -- pip install requests beautifulsoup4"}
    if not re.match(r"^https?://", url):
        url = "https://" + url
    s = requests.Session()
    s.headers["User-Agent"] = UA
    res = {"url": url, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        r, res["fetch"] = fetch_page(s, url)
    except Exception as e:
        return {**res, "error": f"fetch failed: {str(e)[:200]}"}
    res["headers"] = header_checks(r)
    if "html" in r.headers.get("content-type", ""):
        soup = BeautifulSoup(r.text, "html.parser")
        res["onpage"] = onpage_checks(soup, r.url)
        res["schema"] = schema_checks(soup)
    res["site_files"] = site_files(s, r.url)
    internal = res.get("onpage", {}).pop("_internal_link_list", [])
    if n_links:
        res["links"] = link_checks(s, internal, n_links)
    if do_psi:
        try:
            res["pagespeed"] = pagespeed(s, r.url)
        except Exception as e:
            res["pagespeed"] = {"error": str(e)[:200]}
    res["flags"] = flags(res)
    res["note"] = "All values observed from live fetches; flags are rule-based, not ranking or conversion judgments."
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--pagespeed", action="store_true")
    ap.add_argument("--links", type=int, default=0)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    # Keyed by URL only: a fuller cached run (pagespeed, more links) satisfies a
    # lighter request, so sibling specialists share one fetch.
    norm = a.url if re.match(r"^https?://", a.url) else "https://" + a.url
    cache = CACHE_DIR / (hashlib.sha256(norm.rstrip("/").lower().encode()).hexdigest()[:24] + ".json")
    cached = None
    if not a.no_cache and cache.exists() and time.time() - cache.stat().st_mtime < CACHE_TTL:
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            cached = None
    if cached and cached.get("_opts", {}).get("links", 0) >= a.links and (
            not a.pagespeed or ("pagespeed" in cached and "error" not in cached["pagespeed"])):
        out = cached
        out["cache"] = "hit"
    else:
        out = run(a.url, a.pagespeed, a.links)
        out["_opts"] = {"links": a.links, "pagespeed": a.pagespeed}
        out["cache"] = "miss"
        if "error" not in out:
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(out), encoding="utf-8")
            except OSError:
                pass
    print(json.dumps(out))


if __name__ == "__main__":
    main()
