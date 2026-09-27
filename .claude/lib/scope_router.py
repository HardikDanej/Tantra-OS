#!/usr/bin/env python3
"""Tantra scope router: a deterministic, zero-token first pass over a request
that names which domain agents it actually asks for. Orchestrators use the
result as a scope lock, so a request for SEO + PPC doesn't also pull in
unrequested domains.

Safe by design: it only claims "high" confidence when the request names at
least one domain explicitly. Anything else returns "fallback" and the
orchestrator decomposes the request on its own judgment, exactly as before.

Usage:
    python scope_router.py "<request text>"
    echo "<request text>" | python scope_router.py

Prints one line of JSON and always exits 0.
"""
import json
import re
import sys

DOMAIN_AGENTS = {
    "seo-agent": [
        r"seo", r"organic", r"rank(?:ing|ings|s)?", r"serps?", r"keywords?",
        r"backlinks?", r"search engines?", r"ai overviews?", r"aeo", r"geo",
        r"llm citations?", r"ai citations?", r"schema", r"crawl(?:ing|ability)?",
        r"index(?:ing|ation)", r"domain authority", r"e-?e-?a-?t",
    ],
    "ads-paid-media-agent": [
        r"ppc", r"paid (?:media|search|social|ads)", r"ads", r"advertis(?:ing|ement|ements)",
        r"google ads", r"meta ads", r"linkedin ads", r"sem", r"cpc", r"roas",
        r"ad (?:campaigns?|spend|account|creative)", r"media buy(?:ing)?",
        r"retargeting", r"remarketing", r"bid(?:ding)? strateg(?:y|ies)",
    ],
    "website-development-agent": [
        r"page ?speed", r"core web vitals", r"site speed", r"accessibility",
        r"wcag", r"broken links?", r"tech(?:nology)? stack", r"security headers",
        r"mobile[- ]responsive(?:ness)?", r"site build",
    ],
    "growth-ops-cro-agent": [
        r"cro", r"conversion rate", r"conversion optimi[sz]ation", r"landing pages?",
        r"funnels?", r"a/?b tests?", r"split tests?", r"checkout", r"cart abandonment",
        r"form (?:fields?|optimi[sz]ation)", r"heatmaps?", r"referral (?:loop|program)",
        r"martech",
    ],
    "social-media-agent": [
        r"social media", r"instagram", r"tiktok", r"hashtags?", r"influencers?",
        r"community management", r"organic social", r"social strategy",
    ],
    "writing-content-production-agent": [
        r"write", r"draft", r"copywriting", r"blog posts?", r"articles?",
        r"newsletters?", r"captions?", r"email copy", r"ad copy",
    ],
    "revenue-crm-agent": [
        r"crm", r"hubspot", r"pipeline", r"lead scoring", r"email (?:journeys?|drip)",
        r"churn", r"retention", r"lifecycle", r"loyalty program",
    ],
    "marketing-strategist-agent": [
        r"positioning", r"brand voice", r"personas?", r"icp", r"brand launch",
        r"naming", r"taglines?", r"brand foundation",
    ],
}

OTHER_SYSTEMS = {
    "brand-creative-orchestrator": [
        r"rebrand(?:ing)?", r"brand identity", r"brand architecture", r"logo",
        r"editorial strategy", r"brand equity",
    ],
    "product-marketing-gtm-orchestrator": [
        r"go-to-market", r"gtm", r"pricing", r"packaging", r"product launch",
        r"sales enablement", r"battlecards?", r"onboarding flow",
    ],
    "market-research-insights-orchestrator": [
        r"market research", r"surveys?", r"focus groups?", r"tam", r"market siz(?:e|ing)",
        r"attribution model(?:ing)?", r"marketing mix model(?:ing)?", r"mmm", r"win/?loss",
    ],
    "pr-corporate-communications-orchestrator": [
        r"press releases?", r"media relations", r"crisis", r"investor relations",
        r"earnings", r"trade shows?", r"events?", r"journalists?",
    ],
}


def _compile(table):
    return {k: [re.compile(r"(?<![\w-])" + p + r"(?![\w-])", re.I) for p in v]
            for k, v in table.items()}


_DOMAINS = _compile(DOMAIN_AGENTS)
_SYSTEMS = _compile(OTHER_SYSTEMS)


def _hits(text, table):
    out = {}
    for name, patterns in table.items():
        found = sorted({m.group(0).lower() for p in patterns for m in p.finditer(text)})
        if found:
            out[name] = found
    return out


def route(text):
    domains = _hits(text, _DOMAINS)
    systems = _hits(text, _SYSTEMS)
    if not domains and not systems:
        return {"confidence": "fallback", "domain_agents": [], "other_systems": [],
                "matched": {}, "reason": "no domain named explicitly; orchestrator decomposes on its own judgment"}
    return {
        "confidence": "high" if domains else "fallback",
        "domain_agents": sorted(domains),
        "other_systems": sorted(systems),
        "matched": {**domains, **systems},
        "reason": ("scope lock: dispatch only these domain agents unless a named dependency requires another"
                   if domains else "only other systems named; route via cross-system-dispatch-bridge"),
    }


def main():
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    print(json.dumps(route(text)))


if __name__ == "__main__":
    main()
