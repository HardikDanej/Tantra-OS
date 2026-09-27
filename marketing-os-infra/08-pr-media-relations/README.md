# 08 — PR & Media Relations

Tool-layer connectors for the **Public Relations & Corporate Communications** agentic system — the first live tool access this system has had.

## Two connectors, two different risk profiles

1. **`media_coverage_pull.py`** — read-only, no gate needed. Pulls real, published news coverage matching a query (NewsAPI-shaped) for `editorial-media-monitoring-clipping-subagent`. Never submits anything; purely a structured, re-runnable replacement for ad-hoc WebSearch coverage checks.

2. **`press_release_submit.py`** — draft/pending-review write, **gated**. This is the highest-risk connector added across all four newly-tooled systems, because unlike the read-only pulls, it reaches a real wire-service vendor account. Three independent checks must all pass before anything is submitted (see the script's own module docstring): an `approval_gate.py` gate for this exact release must show `"approved"`, `write_access_confirmed: true` must be explicitly set in `config.json`, and the connector itself hard-codes the submission state to `"draft"`/`"pending_review"` — there is no code path anywhere in `press_wire_connector.py` that produces a live-distributed release. **`media-relations-earned-editorial-agent` never calls this script itself** — same discipline as `ads_campaign_draft.py`: only `pr-corporate-communications-orchestrator` opens the gate and, once approved, invokes this directly.

## Vendor note

PR Newswire / Business Wire / GlobeNewswire don't expose a uniform public REST API — most require a sales-negotiated contract with vendor-specific credentials and endpoint shapes. `press_wire_connector.py` is written against a generic, documented REST shape; fill `config.json`'s `endpoint_base`/`submit_path`/`api_key` from your actual vendor's own API documentation once that contract exists. What's fixed in the connector is the *safety* shape (draft-only, gated), not the vendor-specific payload field names.

## Setup

1. Fill in `config.json`'s `newsapi` block for coverage monitoring.
2. Fill in the wire-service fields once a real vendor contract and credentials exist; leave `write_access_confirmed: false` until then.
3. Coverage pull: `python3 media_coverage_pull.py --query "YourBrand"`
4. Release submission (only after an orchestrator-opened gate is approved): `python3 press_release_submit.py --release release.json --gate-id <approved-gate-id> --gates-ledger memory/approval_gates.jsonl`

## Output

`output/coverage_<query>.csv` + `.sources.json` manifest for coverage pulls; `wire_submissions_log.csv` (append-only) for every successful release submission, recording the gate id used, submission state, and the vendor's own review URL.
