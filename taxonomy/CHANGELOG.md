# Taxonomy Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "Marketing Taxonomy Foundation" gap identified
against the OS blueprint (`Marketing OS.md` §3): a formal, versioned,
extensible taxonomy node structure, rather than the taxonomy existing only
implicitly in agent descriptions and knowledge-base prose.

- Generated from all 237 files in `.claude/agents/` as of this date.
- 7 domains (blueprint §3's exact list), 21 subdomains (domain agents),
  210 disciplines (specialist sub-agents) — a clean 10-per-domain-agent
  split with 0 unresolved parent links and 0 orphans on first build.
- 6 system-infra nodes (5 orchestrators + `cross-system-dispatch-bridge`)
  kept outside the 7-domain tree — they route dispatches, they don't own
  a discipline.
- No per-node objectives/strategies/tactics/KPIs populated — see
  `README.md`'s "Deliberately NOT included" section for why.
