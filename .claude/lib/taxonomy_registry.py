"""
taxonomy_registry.py
=====================
Builds and queries the marketing taxonomy required by the OS blueprint's
"Marketing Taxonomy Foundation" section: 7 major domains, with every real
agent in this repo classified as a subdomain (a domain agent) or a
sub-discipline (a specialist sub-agent) beneath one.

This is NOT hand-invented content. Every node is derived from data that
already exists in .claude/agents/*.md:
  - id / name / description / tools come straight from each file's YAML
    frontmatter.
  - parent-child links for sub-agents are EXTRACTED from the sentence
    every sub-agent file already carries ("Only accepts dispatches from
    the <X> Agent...") via regex + a small alias table, not guessed.
  - Only the domain-agent -> one-of-7-domains classification (~19 nodes)
    is hand-curated, against each domain agent's own stated real scope.
    That mapping is the one place human judgment enters, and it is kept
    in one small, auditable dict (DOMAIN_MAP) rather than spread across
    per-node fabricated text.

Deliberately NOT populated: per-node objectives/strategies/tactics/KPIs.
Inventing those for ~200 nodes would be exactly the kind of unearned
confident-sounding content this repo's own agents refuse to produce.
A node's real objectives/KPIs come from the relevant knowledge-bases/
file and the dispatch contract at run time, not from a static taxonomy
entry.

Usage:
    python taxonomy_registry.py build                 # regenerate taxonomy/marketing_taxonomy.json
    python taxonomy_registry.py validate               # check for unresolved parents / orphans
    python taxonomy_registry.py outline                # print the 7-domain -> subdomain tree with counts
    python taxonomy_registry.py node <id>               # full detail on one node
    python taxonomy_registry.py search <term>           # substring search over name/description
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
TAXONOMY_DIR = REPO_ROOT / "taxonomy"
TAXONOMY_JSON = TAXONOMY_DIR / "marketing_taxonomy.json"

VERSION = "1.0.0"

# The 7 canonical domains from the OS blueprint, Section 3.
DOMAINS = {
    "strategy_management":      "Marketing Strategy & Management",
    "brand_communications":     "Brand & Communications",
    "digital_performance":      "Digital & Performance Marketing",
    "content_social":           "Content & Social Media Marketing",
    "customer_relationship":    "Customer & Relationship Marketing",
    "product_growth_revenue":   "Product, Growth & Revenue Marketing",
    "martech_data_ai":          "Marketing Technology, Data & AI",
}

# System-level orchestration/bridge nodes: not domain agents, no 7-domain
# classification (they route to domain agents, they don't own a discipline).
SYSTEM_INFRA = {
    "chief-marketing-orchestrator",
    "brand-creative-orchestrator",
    "market-research-insights-orchestrator",
    "pr-corporate-communications-orchestrator",
    "product-marketing-gtm-orchestrator",
    "cross-system-dispatch-bridge",
}

# Cross-cutting engineering/creative/session infrastructure that isn't part
# of the marketing taxonomy at all (software-engineering pipeline, data-
# science pipeline, Claude Code session tooling, generic image/creative
# production helpers used BY design skills rather than marketing domains).
OUT_OF_SCOPE_PREFIXES = ("dsi-", "pea-")
OUT_OF_SCOPE_NAMES = {
    "claude", "claude-code-guide", "explore", "plan", "general-purpose",
    "statusline-setup", "asset-generator", "design-variant-explorer",
    "section-image-worker", "verify-lens",
}

# Hand-curated: each real domain agent -> one of the 7 blueprint domains,
# based on that agent's own stated scope (see each file's description).
# This is the one place classification judgment is applied; every other
# link in the tree is extracted mechanically from real file text.
DOMAIN_MAP = {
    "marketing-strategist-agent":                    "strategy_management",
    "competitor-red-team-agent":                      "strategy_management",
    "primary-research-customer-discovery-agent":      "strategy_management",
    "competitive-market-intelligence-agent":          "strategy_management",

    "brand-strategy-architecture-agent":              "brand_communications",
    "media-relations-earned-editorial-agent":         "brand_communications",
    "corporate-reputation-issues-crisis-management-agent": "brand_communications",
    "events-experiential-marketing-agent":            "brand_communications",

    "seo-agent":                                      "digital_performance",
    "ads-paid-media-agent":                           "digital_performance",

    "social-media-agent":                             "content_social",
    "content-marketing-editorial-strategy-agent":     "content_social",
    "organic-social-community-building-agent":        "content_social",
    "writing-content-production-agent":               "content_social",

    "revenue-crm-agent":                              "customer_relationship",
    "commercial-assets-sales-enablement-agent":       "customer_relationship",

    "growth-ops-cro-agent":                           "product_growth_revenue",
    "go-to-market-launch-strategy-agent":              "product_growth_revenue",
    "pricing-packaging-customer-adoption-agent":      "product_growth_revenue",

    "website-development-agent":                      "martech_data_ai",
    "marketing-analytics-attribution-modeling-agent": "martech_data_ai",
}

# Free-text aliases -> filename, for resolving the sub-agent parent
# sentence ("Only accepts dispatches from the <X>...") back to a real
# agent id. Keys are lowercased, punctuation-light substrings.
PARENT_ALIASES = {
    "chief marketing orchestrator": "chief-marketing-orchestrator",
    "chief orchestrator": "chief-marketing-orchestrator",
    "ads/paid-media agent": "ads-paid-media-agent",
    "ads / paid-media agent": "ads-paid-media-agent",
    "seo agent": "seo-agent",
    "website development agent": "website-development-agent",
    "social media agent": "social-media-agent",
    "writing/content production agent": "writing-content-production-agent",
    "writing agent": "writing-content-production-agent",
    "revenue/crm agent": "revenue-crm-agent",
    "revenue agent": "revenue-crm-agent",
    "growth ops/cro agent": "growth-ops-cro-agent",
    "growth operations & conversion rate optimization": "growth-ops-cro-agent",
    "competitor red team agent": "competitor-red-team-agent",
    "marketing strategist agent": "marketing-strategist-agent",
    "brand strategy & architecture agent": "brand-strategy-architecture-agent",
    "content marketing & editorial strategy agent": "content-marketing-editorial-strategy-agent",
    "organic social & community building agent": "organic-social-community-building-agent",
    "go-to-market & launch strategy agent": "go-to-market-launch-strategy-agent",
    "commercial assets & sales enablement agent": "commercial-assets-sales-enablement-agent",
    "pricing, packaging & customer adoption agent": "pricing-packaging-customer-adoption-agent",
    "primary research & customer discovery agent": "primary-research-customer-discovery-agent",
    "competitive & market intelligence agent": "competitive-market-intelligence-agent",
    "marketing analytics & attribution modeling agent": "marketing-analytics-attribution-modeling-agent",
    "media relations & earned editorial agent": "media-relations-earned-editorial-agent",
    "corporate reputation, issues & crisis management agent": "corporate-reputation-issues-crisis-management-agent",
    "events & experiential marketing agent": "events-experiential-marketing-agent",
    "one of the five top-level orchestrators": None,  # bridge: no single domain parent
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
PARENT_SENTENCE_RE = re.compile(
    r"[Oo]nly accepts dispatches from ([^.]+?)(?:,\s*never|\.|$)"
)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    name_m = re.search(r'^name:\s*(.+)$', block, re.MULTILINE)
    desc_m = re.search(r'^description:\s*"(.*)"\s*$', block, re.MULTILINE | re.DOTALL)
    if not desc_m:
        desc_m = re.search(r'^description:\s*(.+)$', block, re.MULTILINE)
    tools_m = re.search(r'^tools:\s*(.+)$', block, re.MULTILINE)
    name = name_m.group(1).strip() if name_m else None
    description = desc_m.group(1).strip() if desc_m else ""
    description = description.replace('\n', ' ')
    description = re.sub(r'\s+', ' ', description)
    tools = [t.strip() for t in tools_m.group(1).split(',')] if tools_m else []
    return {"name": name, "description": description, "tools": tools}


def resolve_parent_alias(raw: str):
    """raw is the captured text after 'Only accepts dispatches from '."""
    cleaned = raw.strip()
    # strip a trailing parenthetical like "(Paid Media & Performance Marketing)"
    cleaned_no_paren = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned).strip()
    for candidate in (cleaned, cleaned_no_paren):
        key = candidate.lower().strip()
        key = key[4:] if key.startswith("the ") else key
        key = key.strip()
        if key in PARENT_ALIASES:
            return PARENT_ALIASES[key]
    # substring match fallback
    low = cleaned_no_paren.lower()
    for alias, fname in PARENT_ALIASES.items():
        if alias in low or low in alias:
            return fname
    return "__UNRESOLVED__"


def classify(agent_id: str, meta: dict) -> str:
    if agent_id in SYSTEM_INFRA:
        return "system_infra"
    if agent_id.startswith(OUT_OF_SCOPE_PREFIXES) or agent_id in OUT_OF_SCOPE_NAMES:
        return "out_of_scope_infra"
    desc = meta.get("description") or ""
    if agent_id in DOMAIN_MAP or re.search(r'^Domain agent\b', desc):
        return "domain_agent"
    return "sub_agent"


def build():
    nodes = {}
    unresolved = []

    files = sorted(AGENTS_DIR.glob("*.md"))
    for f in files:
        agent_id = f.stem
        text = f.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta.get("name"):
            meta["name"] = agent_id
        kind = classify(agent_id, meta)

        node = {
            "id": agent_id,
            "name": meta["name"],
            "kind": kind,           # system_infra | domain_agent | sub_agent | out_of_scope_infra
            "definition": meta.get("description", ""),
            "tools": meta.get("tools", []),
            "agent_file": f".claude/agents/{f.name}",
            "taxonomy_domain": None,
            "parent": None,
        }

        if kind == "domain_agent":
            node["taxonomy_domain"] = DOMAIN_MAP.get(agent_id)
            if node["taxonomy_domain"] is None:
                unresolved.append((agent_id, "domain_agent missing DOMAIN_MAP entry"))
        elif kind == "sub_agent":
            m = PARENT_SENTENCE_RE.search(meta.get("description", ""))
            if not m:
                unresolved.append((agent_id, "no 'Only accepts dispatches from' sentence found"))
            else:
                parent_id = resolve_parent_alias(m.group(1))
                if parent_id == "__UNRESOLVED__":
                    unresolved.append((agent_id, f"unresolved parent phrase: {m.group(1)!r}"))
                    node["parent"] = None
                else:
                    node["parent"] = parent_id

        nodes[agent_id] = node

    # inherit taxonomy_domain down from resolved domain-agent parents
    for agent_id, node in nodes.items():
        if node["kind"] == "sub_agent" and node["parent"]:
            parent = nodes.get(node["parent"])
            if parent and parent.get("taxonomy_domain"):
                node["taxonomy_domain"] = parent["taxonomy_domain"]
            elif parent is None:
                unresolved.append((agent_id, f"parent id '{node['parent']}' not found among agent files"))

    # build children index
    children = {}
    for agent_id, node in nodes.items():
        p = node.get("parent")
        if p:
            children.setdefault(p, []).append(agent_id)
    for agent_id, node in nodes.items():
        node["children"] = sorted(children.get(agent_id, []))

    counts = {}
    for node in nodes.values():
        counts[node["kind"]] = counts.get(node["kind"], 0) + 1

    doc = {
        "taxonomy_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": (
            "Derived mechanically from .claude/agents/*.md frontmatter. "
            "Sub-agent parent links extracted via regex from each file's own "
            "'Only accepts dispatches from the X Agent' sentence. Domain-agent "
            "-> 7-domain classification is the one hand-curated mapping "
            "(DOMAIN_MAP in taxonomy_registry.py), based on each domain "
            "agent's own stated scope. No per-node objectives/KPIs/strategies "
            "are invented; those are read from knowledge-bases/ and the live "
            "dispatch contract at run time, not stored statically here."
        ),
        "domains": DOMAINS,
        "counts": counts,
        "unresolved": [{"id": a, "reason": r} for a, r in unresolved],
        "nodes": nodes,
    }

    TAXONOMY_DIR.mkdir(exist_ok=True)
    TAXONOMY_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {TAXONOMY_JSON} — {len(nodes)} nodes, {len(unresolved)} unresolved.")
    if unresolved:
        print("UNRESOLVED:")
        for a, r in unresolved:
            print(f"  - {a}: {r}")
    return doc


def load():
    if not TAXONOMY_JSON.exists():
        print("No taxonomy built yet. Run: python taxonomy_registry.py build")
        sys.exit(1)
    return json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))


def cmd_validate():
    doc = load()
    unresolved = doc["unresolved"]
    orphans = [
        n for n in doc["nodes"].values()
        if n["kind"] == "sub_agent" and not n.get("parent")
    ]
    if not unresolved and not orphans:
        print(f"OK — {sum(doc['counts'].values())} nodes, 0 unresolved, 0 orphans.")
        return 0
    if unresolved:
        print(f"FAIL — {len(unresolved)} unresolved parent/domain links:")
        for u in unresolved:
            print(f"  - {u['id']}: {u['reason']}")
    if orphans:
        print(f"FAIL — {len(orphans)} sub_agent nodes with no parent:")
        for n in orphans:
            print(f"  - {n['id']}")
    return 1


def cmd_outline():
    doc = load()
    nodes = doc["nodes"]
    for dom_key, dom_name in doc["domains"].items():
        domain_agents = sorted(
            (n for n in nodes.values()
             if n["kind"] == "domain_agent" and n["taxonomy_domain"] == dom_key),
            key=lambda n: n["id"])
        total_disciplines = sum(len(n["children"]) for n in domain_agents)
        print(f"\n{dom_name}  [{dom_key}]  ({len(domain_agents)} subdomains, {total_disciplines} disciplines)")
        for da in domain_agents:
            print(f"  - {da['id']}  ({len(da['children'])} sub-disciplines)")

    system_infra = sorted((n for n in nodes.values() if n["kind"] == "system_infra"), key=lambda n: n["id"])
    out_of_scope = sorted((n for n in nodes.values() if n["kind"] == "out_of_scope_infra"), key=lambda n: n["id"])
    print(f"\nSystem/orchestration infra (not a taxonomy discipline): {len(system_infra)}")
    for n in system_infra:
        print(f"  - {n['id']}")
    print(f"\nOut-of-scope infra (engineering/creative/session tooling, not marketing taxonomy): {len(out_of_scope)}")
    for n in out_of_scope:
        print(f"  - {n['id']}")


def cmd_node(node_id):
    doc = load()
    n = doc["nodes"].get(node_id)
    if not n:
        print(f"No such node: {node_id}")
        sys.exit(1)
    print(json.dumps(n, indent=2, sort_keys=True))


def cmd_search(term):
    doc = load()
    term_low = term.lower()
    hits = [
        n for n in doc["nodes"].values()
        if term_low in n["id"].lower() or term_low in n["definition"].lower()
    ]
    print(f"{len(hits)} match(es) for '{term}':")
    for n in sorted(hits, key=lambda x: x["id"]):
        dom = n.get("taxonomy_domain") or n["kind"]
        print(f"  - {n['id']}  [{dom}]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "validate":
        sys.exit(cmd_validate())
    elif cmd == "outline":
        cmd_outline()
    elif cmd == "node":
        cmd_node(sys.argv[2])
    elif cmd == "search":
        cmd_search(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
        sys.exit(1)
