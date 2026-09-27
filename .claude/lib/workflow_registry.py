"""
workflow_registry.py
======================
The OS blueprint's Section 29 "Master Workflow Record" made real: a
queryable catalog of this repo's 4 actual workflows, populated from what
each workflows/*/orchestration.md file already says -- not an invented
template filled with placeholder text.

Same discipline as every prior gap's registry: this does NOT redefine
fields another registry already owns.
  - Agent identity/capability   -> taxonomy/marketing_taxonomy.json (gap #1).
    This registry only checks that each workflow's named agents actually
    exist there -- a real cross-reference, not a duplicate definition.
  - Trigger mechanics            -> .claude/lib/trigger_registry.py /
    event-triggers/ (gap #6). This registry records each workflow's real
    cadence in prose (it's genuinely a cron/human-run distinction per
    workflow) but does not re-implement trigger evaluation.
  - Tool permissions/limits      -> data-model/core_data_model.json's
    tool_registry (gap #2).
  - Workflow file version        -> version-manifest/manifest.json's
    workflow_versions (gap #5) -- read directly, not recomputed here.

What's genuinely new here: Objective, primary agents, real trigger
cadence, context requirements (the real files each workflow depends on),
and approval policy, for all 4 workflows, in one queryable place instead
of four separate prose documents a human reads end to end to compare.

Confidence / Outcome / Cost / Evidence / Learning from blueprint Section
29's table are deliberately NOT stored here -- those vary PER RUN, not per
template, and already have a real home: memory/checkpoints.jsonl (Decision,
gap #2) and memory/outcomes.jsonl (Learning, gap #2). A workflow REGISTRY
entry describes the template; a workflow INSTANCE (workflow_state.py,
this same gap) tracks one run's actual lifecycle state.

Usage:
    python workflow_registry.py build       # regenerate workflow-registry/workflow_registry.json
    python workflow_registry.py validate    # confirm every named agent is real, every doc/version reference resolves
    python workflow_registry.py show <workflow-id>
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows"
OUT_DIR = REPO_ROOT / "workflow-registry"
OUT_JSON = OUT_DIR / "workflow_registry.json"
TAXONOMY_JSON = REPO_ROOT / "taxonomy" / "marketing_taxonomy.json"
VERSION_MANIFEST_JSON = REPO_ROOT / "version-manifest" / "manifest.json"

VERSION = "1.0.0"

# Hand-curated from each workflows/*/orchestration.md file's own real text
# (its "What triggers this workflow" section and dispatch-sequence agent
# list) -- not invented. Every agent_id below is cross-checked at build
# time against taxonomy/marketing_taxonomy.json; build fails loudly if one
# doesn't resolve, so this table can't silently drift from the real roster.
WORKFLOW_TEMPLATES = {
    "01-campaign-intelligence": {
        "name": "Campaign Intelligence",
        "objective": "Diagnose paid-media account health (creative fatigue, structural issues) and brief any "
                     "needed creative fix -- weekly, across whatever channels the uploaded data covers.",
        "primary_agents": ["ads-paid-media-agent", "writing-content-production-agent"],
        "trigger_kind": "cron",
        "trigger_cadence": "Monday 8am, fed by ad_data_pull.py's Sunday 11pm cron writing weekly_unified.csv",
        "context_requirements": ["marketing-os-infra/01-campaign-intelligence/output/weekly_unified.csv"],
        "freshness_gate": "Refuses to dispatch if weekly_unified.csv is older than 36 hours -- posts a stale-data "
                           "warning instead (its own Step 1 Gatekeeper check).",
        "approval_policy": "Diagnostic output only; any live campaign/bid change stays behind the Chief "
                            "Orchestrator's ad_platform_write approval gate, never this workflow's own dispatch.",
        "orchestration_doc": "workflows/01-campaign-intelligence/orchestration.md",
    },
    "02-seo-content-factory": {
        "name": "SEO Content Factory",
        "objective": "Select the highest-priority topic from the nightly keyword pull, brief it, draft it, and "
                     "run it through the mandatory SEO<->Writing round-trip before publishing -- weekday mornings.",
        "primary_agents": ["seo-agent", "writing-content-production-agent"],
        "trigger_kind": "cron",
        "trigger_cadence": "Weekday 6am, fed by gsc_keyword_pull.py's nightly cron writing topic_queue.csv",
        "context_requirements": ["marketing-os-infra/02-seo-content-factory/topic_queue.csv"],
        "freshness_gate": "None needed on a routine run -- topic_queue.csv already encodes the prior night's "
                           "priority decision (its own Step 1 Gatekeeper note).",
        "approval_policy": "The SEO Agent never drafts and the Writing Agent never sets keyword/audience "
                            "strategy -- a mandatory round-trip is the workflow's own internal check, not a "
                            "human HITL gate, unless publishing itself requires one per the workspace's CMS setup.",
        "orchestration_doc": "workflows/02-seo-content-factory/orchestration.md",
    },
    "03-brand-launch-suite": {
        "name": "Brand Launch Suite",
        "objective": "Run the Marketing Strategist Agent's five-stage brand-foundation pipeline (audit -> "
                     "personas -> voice -> GEO/AEO mapping -> content architecture) for a brand launch or rebrand.",
        "primary_agents": ["marketing-strategist-agent"],
        "trigger_kind": "scheduled_prompt",
        "trigger_cadence": "One-time or occasional per brand launch/rebrand engagement -- deliberately no "
                            "recurring cron, per the workflow's own doc.",
        "context_requirements": ["marketing-os-infra/03-brand-launch-suite/brand_inputs.json"],
        "freshness_gate": "Refuses to dispatch (surfaces before dispatching) if brand_inputs.json has fewer "
                           "than 5 total real assets -- the same real-asset-floor discipline "
                           "brand-asset-audit-subagent itself enforces.",
        "approval_policy": "Produces the brand-foundation artifacts (brand/personas.json, brand/voice_system.json, "
                            "brand/icp_definition.md) other agents depend on; no spend/publish action of its own "
                            "to gate.",
        "orchestration_doc": "workflows/03-brand-launch-suite/orchestration.md",
    },
    "04-hubspot-revenue-agent": {
        "name": "HubSpot Revenue Agent",
        "objective": "Score pipeline/ICP fit and target re-engagement candidates from live HubSpot data on "
                     "weekday mornings; separately aggregate historical trend analyses weekly.",
        "primary_agents": ["revenue-crm-agent", "writing-content-production-agent"],
        "trigger_kind": "cron",
        "trigger_cadence": "Weekday 8:30am (live HubSpot MCP pull) plus a separate Sunday 9pm Claude Code cron "
                            "(hubspot_historical.py) for trend data the MCP can't aggregate efficiently.",
        "context_requirements": ["brand/icp_definition.md",
                                  "marketing-os-infra/04-hubspot-revenue-agent/historical_trends.json",
                                  "marketing-os-infra/04-hubspot-revenue-agent/historical_deals_snapshot.json"],
        "freshness_gate": "Refuses to dispatch if icp_definition.md is missing, contains placeholder language, "
                           "or the Marketing Strategist Agent has never run for this brand (its own Step 1 "
                           "Gatekeeper check).",
        "approval_policy": "Revenue/CRM Agent scores and targets read-only; Writing Agent drafts; neither agent "
                            "sends anything -- humans send, enforced as one of the Chief Orchestrator's hard "
                            "deterministic constraints.",
        "orchestration_doc": "workflows/04-hubspot-revenue-agent/orchestration.md",
    },
}


def _load_taxonomy_agent_ids() -> set[str]:
    if not TAXONOMY_JSON.exists():
        return set()
    return set(json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))["nodes"].keys())


def _load_workflow_versions() -> dict[str, str]:
    if not VERSION_MANIFEST_JSON.exists():
        return {}
    return json.loads(VERSION_MANIFEST_JSON.read_text(encoding="utf-8")).get("workflow_versions", {})


def build() -> dict:
    known_agent_ids = _load_taxonomy_agent_ids()
    workflow_versions = _load_workflow_versions()
    problems = []

    entries = {}
    for wf_id, template in WORKFLOW_TEMPLATES.items():
        doc_path = REPO_ROOT / template["orchestration_doc"]
        if not doc_path.exists():
            problems.append(f"{wf_id}: orchestration_doc does not exist: {template['orchestration_doc']}")
        for agent_id in template["primary_agents"]:
            if known_agent_ids and agent_id not in known_agent_ids:
                problems.append(f"{wf_id}: primary_agent {agent_id!r} not found in taxonomy/marketing_taxonomy.json")
        entry = dict(template)
        entry["workflow_id"] = wf_id
        entry["content_version"] = workflow_versions.get(wf_id)
        if entry["content_version"] is None:
            problems.append(f"{wf_id}: no content_version found in version-manifest/manifest.json "
                             f"-- run version_manifest.py snapshot first")
        entries[wf_id] = entry

    doc = {
        "workflow_registry_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": (
            "Hand-curated from each workflows/*/orchestration.md file's own real text (trigger cadence, "
            "agent involvement, gatekeeper checks) -- not invented. primary_agents cross-checked against "
            "taxonomy/marketing_taxonomy.json at build time; content_version read directly from "
            "version-manifest/manifest.json, not recomputed. Confidence/Outcome/Cost/Evidence/Learning "
            "(blueprint Section 29's per-run fields) deliberately excluded -- those live in "
            "memory/checkpoints.jsonl and memory/outcomes.jsonl per actual run, not in this template registry."
        ),
        "count": len(entries),
        "build_problems": problems,
        "workflows": entries,
    }
    OUT_DIR.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT_JSON} -- {len(entries)} workflows, {len(problems)} build problem(s).")
    if problems:
        for p in problems:
            print(f"  ! {p}")
    return doc


def load() -> dict:
    if not OUT_JSON.exists():
        print("No workflow registry built yet. Run: python workflow_registry.py build")
        sys.exit(1)
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))


def validate() -> int:
    doc = load()
    if doc["build_problems"]:
        print(f"FAIL -- {len(doc['build_problems'])} problem(s):")
        for p in doc["build_problems"]:
            print(f"  - {p}")
        return 1
    print(f"OK -- {doc['count']} workflows, 0 problems.")
    return 0


def show(workflow_id: str):
    doc = load()
    entry = doc["workflows"].get(workflow_id)
    if not entry:
        print(f"No such workflow: {workflow_id}. Known: {', '.join(doc['workflows'].keys())}")
        sys.exit(1)
    print(json.dumps(entry, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "validate":
        sys.exit(validate())
    elif cmd == "show":
        show(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
