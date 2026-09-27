"""
data_model_registry.py
========================
The OS blueprint's "Core Data Model" (Section 5: Organization, Brand,
Customer/Contact, Account, Product, Campaign, Audience, Content Asset,
Opportunity, Experiment, Agent, Workflow, Task, Tool, Event, Decision,
Learning) as real, typed Pydantic schemas plus a queryable registry --
instead of each of those concepts existing only as an ad hoc file shape
a human has to infer by reading five different agent files.

Same discipline as taxonomy_registry.py (the Agent-registry half of this
same gap, already built): every schema here is grounded in a shape that
already exists somewhere real in this repo -- a checkpoint entry, an
outcomes.jsonl line, an approval_gates.jsonl line, a tool_router.py Row
class, brand/company.json -- not invented to fill out a textbook data
model. Where NO real producer exists yet in this framework repo, the node
is marked status="defined_not_yet_produced" and says so plainly, rather
than implying a live source that isn't there.

Two things this deliberately does NOT do:
  1. Redefine the Agent object. taxonomy_registry.py's
     taxonomy/marketing_taxonomy.json already IS the real, live Agent
     Registry (id, name, definition, tools, parent, children for all 238
     agent files). This module's "agent" entry is a pointer to that file,
     not a duplicate.
  2. Redefine tool_router.py's row schemas (AdRow, GSCRow, SurveyResponseRow,
     ProductEventRow, MediaCoverageRow, SocialProfileSnapshotRow). Those
     ARE the real Event/Campaign-performance objects. This module imports
     and re-exposes them under the blueprint's own object names rather
     than re-declaring their fields a second place they could drift out
     of sync.

Usage:
    python data_model_registry.py build              # regenerate data-model/core_data_model.json
    python data_model_registry.py list                 # all 17 objects + status
    python data_model_registry.py show <object_id>      # full detail incl. real producer / schema fields
    python data_model_registry.py validate <object_id> <file.jsonl>   # validate a real file against its schema
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_MODEL_DIR = REPO_ROOT / "data-model"
DATA_MODEL_JSON = DATA_MODEL_DIR / "core_data_model.json"
TAXONOMY_JSON = REPO_ROOT / "taxonomy" / "marketing_taxonomy.json"

sys.path.insert(0, str(REPO_ROOT / "marketing-os-infra" / "lib"))
try:
    from tool_router import AdRow, GSCRow, SurveyResponseRow, ProductEventRow, \
        MediaCoverageRow, SocialProfileSnapshotRow  # noqa: E402  (real row schemas -- reused, not redefined)
except ImportError:
    AdRow = GSCRow = SurveyResponseRow = ProductEventRow = MediaCoverageRow = SocialProfileSnapshotRow = None

VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Schemas grounded in a real, already-existing shape in this repo.
# ---------------------------------------------------------------------------

class Organization(BaseModel):
    """Mirrors brand/company.json exactly, written by tools/new_workspace.py."""
    name: str
    slug: str
    created: str


class DispatchContract(BaseModel):
    """The Task object. Mirrors the Step 5 dispatch-contract shape from
    chief-marketing-orchestrator.md verbatim -- this exact object is what
    a checkpoint's `contracts` array persists, not a paraphrase."""
    agent: str
    objective: str
    inputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    dispatch_kind: Literal["diagnostic", "strategic"]
    required_output_shape: list[str]
    redispatch: Optional[dict[str, Any]] = None
    versions: Optional[dict[str, Any]] = None  # gap #5: version_manifest.py's `resolve <agent>` stamp


class CheckpointRecord(BaseModel):
    """The Decision object (one orchestrator run). Mirrors
    memory/checkpoints.jsonl's real per-line shape."""
    timestamp: str
    system: Optional[str] = None
    contracts: list[DispatchContract] = Field(default_factory=list)
    approval_gates_opened: list[str] = Field(default_factory=list)
    confidence_returned: dict[str, str] = Field(default_factory=dict)  # agent -> tier; read by calibration_tracker.py


class ApprovalGateEvent(BaseModel):
    """A Decision lifecycle event. Mirrors approval_gate.py's real ledger
    line shape (memory/approval_gates.jsonl) exactly -- do not diverge
    from this without updating approval_gate.py too."""
    gate_id: str
    event: Literal["pending", "approved", "rejected", "superseded"]
    timestamp: str
    stakes_class: str
    summary: str
    what_if_approved: str
    what_if_rejected: str
    red_team_verdict: Literal["HOLDS", "HOLDS WITH CHANGES", "VULNERABLE", "N/A"]
    irreversibility_note: str
    checkpoint_ref: str
    note: Optional[str] = None


class OutcomeRecord(BaseModel):
    """The Learning object. Mirrors memory/outcomes.jsonl's real per-line
    shape from chief-marketing-orchestrator.md's Outcome Feedback section."""
    timestamp: str
    checkpoint_ref: str
    recommendation_summary: str
    action_taken: Literal["as recommended", "modified", "not taken"]
    outcome: str
    outcome_confidence: Literal["confirmed", "self-reported", "partial"]
    matched_prediction: Optional[Literal[True, False, "partial"]] = None
    implications: str


class RedispatchEvent(BaseModel):
    """The Task-retry object. Mirrors redispatch_tracker.py's real
    RedispatchEvent Pydantic model (memory/redispatch_log.jsonl)."""
    cycle_id: str
    event: Literal["attempt", "resolved"]
    timestamp: str
    reason: Optional[str] = None


class ToolRegistryEntry(BaseModel):
    """One entry in the Tool Registry below -- id, real module, capability,
    and gating, for every external-system connector actually in this repo."""
    id: str
    module_path: str
    platforms: list[str]
    capability: Literal["read_only", "draft_write", "scoped_write", "query_utility"]
    gated_by: Optional[str] = None  # an approval_gate.py stakes_class, or a config flag name
    requires_paid_api: bool = False
    notes: str = ""


class Opportunity(BaseModel):
    """Read-only HubSpot deal fields, exactly what hubspot_historical.py
    actually pulls (dealname, amount, dealstage, pipeline) -- never
    written to, per revenue-crm-agent's own boundary."""
    deal_id: Optional[str] = None
    dealname: str
    amount: Optional[float] = None
    dealstage: str
    pipeline: str


class Audience(BaseModel):
    """One persona entry, shaped after brand/personas.json's real per-
    persona convention (produced by audience-persona-research-subagent) --
    2-3 per brand, never padded to a round number."""
    persona_id: str
    name: str
    evidence_sources: list[str] = Field(default_factory=list)
    real_quotes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Schemas defined per the blueprint's own stated purpose (Section 5's
# table), because no real producer exists in THIS framework repo yet.
# Honest about the gap rather than implying a live source.
# ---------------------------------------------------------------------------

class Account(BaseModel):
    """Company-level prospect/customer context and stakeholders. No single
    real file backs this today -- the closest real precedent is
    brand/icp_definition.md's buyer-committee section, which is prose, not
    structured data. Defined here so a workspace CAN start logging one."""
    account_id: str
    company_name: str
    stakeholders: list[str] = Field(default_factory=list)
    stage: Optional[str] = None


class Product(BaseModel):
    """Product details, pricing, positioning, lifecycle. No real internal
    producer exists in this framework; the closest real precedent is
    ProductEventRow (usage events), which describes product BEHAVIOR, not
    the product record itself."""
    product_id: str
    name: str
    lifecycle_stage: Optional[str] = None
    pricing_tier_ref: Optional[str] = None


class ContentAsset(BaseModel):
    """Brief, format, channel, version, status, performance. The Writing/
    Content Production Agent drafts constantly but nothing in this repo
    persists a Content Asset record today -- a genuine, named gap. Defined
    here as the shape a workspace could start logging drafted assets
    against (e.g. memory/content_assets.jsonl); no script writes to it yet."""
    asset_id: str
    title: str
    format: str
    channel: Optional[str] = None
    status: Literal["draft", "approved", "published"] = "draft"
    version: int = 1


class Experiment(BaseModel):
    """Hypothesis, variants, audience, results, evidence. ab-multivariate-
    testing-subagent DESIGNS experiments (real sample-size/power
    computation) but no script persists an Experiment record once
    designed -- defined here, not yet produced."""
    experiment_id: str
    hypothesis: str
    variants: list[str]
    primary_metric: str
    status: Literal["designed", "running", "concluded"] = "designed"
    result: Optional[str] = None


# ---------------------------------------------------------------------------
# Registry metadata: one entry per blueprint Section 5 object.
# ---------------------------------------------------------------------------

REGISTRY: dict[str, dict[str, Any]] = {
    "organization": {
        "name": "Organization", "purpose": "Business identity, goals, markets, policies, constraints",
        "status": "active", "schema_class": "Organization",
        "real_producer": "tools/new_workspace.py -> brand/company.json",
    },
    "brand": {
        "name": "Brand", "purpose": "Voice, positioning, identity, messaging, approved/prohibited claims",
        "status": "active", "schema_class": None,
        "real_producer": "brand/voice_system.json + brand/icp_definition.md + brand/personas.json "
                          "(brand-voice-extraction-subagent, core-brand-positioning-subagent) -- a composite "
                          "of 3 files, each already owned/schemed by its producing sub-agent; not redefined here.",
    },
    "customer_contact": {
        "name": "Customer / Contact", "purpose": "Identity, attributes, behavior, engagement, history",
        "status": "active", "schema_class": None,
        "real_producer": "hubspot_connector.py / marketing-os-infra/04-hubspot-revenue-agent (read-only HubSpot "
                          "contact properties); no dedicated Pydantic row class exists yet for contacts "
                          "specifically -- only the deal-side (Opportunity) is currently typed.",
    },
    "account": {
        "name": "Account", "purpose": "Company-level prospect/customer context and stakeholders",
        "status": "defined_not_yet_produced", "schema_class": "Account", "real_producer": None,
    },
    "product": {
        "name": "Product", "purpose": "Product details, pricing, positioning, lifecycle",
        "status": "defined_not_yet_produced", "schema_class": "Product", "real_producer": None,
    },
    "campaign": {
        "name": "Campaign", "purpose": "Objective, audience, channels, assets, spend, results",
        "status": "active", "schema_class": "AdRow (performance) + ads_connector.CampaignDraftResult (draft)",
        "real_producer": "marketing-os-infra/lib/tool_router.py (AdRow) + marketing-os-infra/lib/ads_connector.py",
    },
    "audience": {
        "name": "Audience", "purpose": "Segment definition, eligibility, behavior, size",
        "status": "active", "schema_class": "Audience",
        "real_producer": "audience-persona-research-subagent -> brand/personas.json",
    },
    "content_asset": {
        "name": "Content Asset", "purpose": "Brief, format, channel, version, status, performance",
        "status": "defined_not_yet_produced", "schema_class": "ContentAsset", "real_producer": None,
    },
    "opportunity": {
        "name": "Opportunity", "purpose": "Pipeline stage, value, probability, sales context",
        "status": "active", "schema_class": "Opportunity",
        "real_producer": "marketing-os-infra/04-hubspot-revenue-agent/hubspot_historical.py (read-only)",
    },
    "experiment": {
        "name": "Experiment", "purpose": "Hypothesis, variants, audience, results, evidence",
        "status": "defined_not_yet_produced", "schema_class": "Experiment", "real_producer": None,
    },
    "agent": {
        "name": "Agent", "purpose": "Capability, instructions, permissions, tools, KPIs",
        "status": "active", "schema_class": None,
        "real_producer": "taxonomy/marketing_taxonomy.json via .claude/lib/taxonomy_registry.py -- the real, "
                          "live Agent Registry. Not redefined here; query that file/script for agent data.",
    },
    "workflow": {
        "name": "Workflow", "purpose": "Trigger, states, steps, dependencies, approval rules",
        "status": "active", "schema_class": None,
        "real_producer": "workflows/*.md (4 real named workflows) + .claude/lib/trigger_registry.py "
                          "(registered condition/cron triggers) -- composite, not a single file.",
    },
    "task": {
        "name": "Task", "purpose": "Atomic action, inputs, output, status, owner",
        "status": "active", "schema_class": "DispatchContract",
        "real_producer": "chief-marketing-orchestrator.md Step 5 dispatch contract, persisted verbatim in "
                          "a checkpoint's `contracts` array.",
    },
    "tool": {
        "name": "Tool", "purpose": "API/action schema, permissions, limits, cost",
        "status": "active", "schema_class": "ToolRegistryEntry",
        "real_producer": "marketing-os-infra/lib/*_connector.py -- see TOOL_REGISTRY below, the real "
                          "catalog this build generates.",
    },
    "event": {
        "name": "Event", "purpose": "Timestamped business or system occurrence",
        "status": "active", "schema_class": "AdRow / GSCRow / SurveyResponseRow / ProductEventRow / "
                                              "MediaCoverageRow / SocialProfileSnapshotRow",
        "real_producer": "marketing-os-infra/lib/tool_router.py row schemas + .claude/lib/trigger_registry.py "
                          "internal condition evaluation.",
    },
    "decision": {
        "name": "Decision", "purpose": "Recommendation/action, evidence, confidence, policy result",
        "status": "active", "schema_class": "CheckpointRecord + ApprovalGateEvent",
        "real_producer": "memory/checkpoints.jsonl + memory/approval_gates.jsonl (approval_gate.py) + "
                          "output_evaluator.py's structural verdict.",
    },
    "learning": {
        "name": "Learning", "purpose": "Observed outcome converted into reusable knowledge",
        "status": "active", "schema_class": "OutcomeRecord",
        "real_producer": "memory/outcomes.jsonl + .claude/lib/calibration_tracker.py's computed hit-rate stats.",
    },
}

# Real Tool Registry -- one entry per external-system connector actually
# in this repo (marketing-os-infra/lib/). Hand-curated against each
# module's own docstring (capability/gating stated there, not guessed).
TOOL_REGISTRY: list[dict[str, Any]] = [
    {"id": "ads_connector", "module_path": "marketing-os-infra/lib/ads_connector.py",
     "platforms": ["Meta", "Google Ads", "TikTok"], "capability": "draft_write",
     "gated_by": "ad_platform_write", "requires_paid_api": False,
     "notes": "Draft-only campaign creation; never launches live."},
    {"id": "cms_connector", "module_path": "marketing-os-infra/lib/cms_connector.py",
     "platforms": ["WordPress", "generic CMS"], "capability": "draft_write",
     "gated_by": "PAUSED/draft state, config write_access_confirmed", "requires_paid_api": False,
     "notes": "Publishes into a PAUSED/draft state, never live, without confirmation."},
    {"id": "hubspot_connector", "module_path": "marketing-os-infra/lib/hubspot_connector.py",
     "platforms": ["HubSpot"], "capability": "scoped_write",
     "gated_by": "config write_access_confirmed", "requires_paid_api": True,
     "notes": "Task/note creation ONLY -- no email sends, no workflow enrollment, no deal-stage or property writes."},
    {"id": "press_wire_connector", "module_path": "marketing-os-infra/lib/press_wire_connector.py",
     "platforms": ["press wire services"], "capability": "draft_write",
     "gated_by": "other_high_stakes (approval_gate.py)", "requires_paid_api": True,
     "notes": "Draft/pending-review only, gated end-to-end like ads_connector."},
    {"id": "product_analytics_connector", "module_path": "marketing-os-infra/lib/product_analytics_connector.py",
     "platforms": ["Amplitude", "Mixpanel"], "capability": "read_only",
     "gated_by": None, "requires_paid_api": True, "notes": "No write function exists anywhere in the module."},
    {"id": "media_coverage_connector", "module_path": "marketing-os-infra/lib/media_coverage_connector.py",
     "platforms": ["NewsAPI"], "capability": "read_only",
     "gated_by": None, "requires_paid_api": True, "notes": "No write function exists anywhere in the module."},
    {"id": "social_profile_connector", "module_path": "marketing-os-infra/lib/social_profile_connector.py",
     "platforms": ["Instagram", "LinkedIn"], "capability": "read_only",
     "gated_by": None, "requires_paid_api": True, "notes": "No write function exists anywhere in the module."},
    {"id": "survey_platform_connector", "module_path": "marketing-os-infra/lib/survey_platform_connector.py",
     "platforms": ["Typeform", "SurveyMonkey"], "capability": "read_only",
     "gated_by": None, "requires_paid_api": True, "notes": "No write function exists anywhere in the module."},
    {"id": "tool_router", "module_path": "marketing-os-infra/lib/tool_router.py",
     "platforms": ["all of the above"], "capability": "query_utility",
     "gated_by": None, "requires_paid_api": False,
     "notes": "Not a connector itself -- the shared PullResult/row-validation framework every puller uses."},
]


def build():
    taxonomy_summary = None
    if TAXONOMY_JSON.exists():
        tx = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))
        taxonomy_summary = {"taxonomy_version": tx.get("taxonomy_version"), "counts": tx.get("counts")}

    counts = {"active": 0, "defined_not_yet_produced": 0}
    for entry in REGISTRY.values():
        counts[entry["status"]] += 1

    doc = {
        "data_model_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": (
            "Every schema is grounded in a real, already-existing shape in this repo (a checkpoint "
            "entry, an outcomes.jsonl line, a tool_router.py Row class, brand/company.json) -- see "
            "each entry's real_producer field. Where no real producer exists yet, status is "
            "'defined_not_yet_produced' and real_producer is null, stated plainly rather than implying "
            "a live source. The Agent object is a pointer to taxonomy/marketing_taxonomy.json, not a "
            "duplicate of it."
        ),
        "counts": counts,
        "objects": REGISTRY,
        "tool_registry": TOOL_REGISTRY,
        "agent_registry_pointer": "taxonomy/marketing_taxonomy.json",
        "agent_registry_summary": taxonomy_summary,
    }

    DATA_MODEL_DIR.mkdir(exist_ok=True)
    DATA_MODEL_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {DATA_MODEL_JSON} -- {len(REGISTRY)} objects "
          f"({counts['active']} active, {counts['defined_not_yet_produced']} defined-not-yet-produced), "
          f"{len(TOOL_REGISTRY)} tool registry entries.")
    return doc


def load():
    if not DATA_MODEL_JSON.exists():
        print("No data model built yet. Run: python data_model_registry.py build")
        sys.exit(1)
    return json.loads(DATA_MODEL_JSON.read_text(encoding="utf-8"))


SCHEMA_CLASSES = {
    "Organization": Organization, "DispatchContract": DispatchContract,
    "CheckpointRecord": CheckpointRecord, "ApprovalGateEvent": ApprovalGateEvent,
    "OutcomeRecord": OutcomeRecord, "RedispatchEvent": RedispatchEvent,
    "ToolRegistryEntry": ToolRegistryEntry, "Opportunity": Opportunity,
    "Audience": Audience, "Account": Account, "Product": Product,
    "ContentAsset": ContentAsset, "Experiment": Experiment,
}

VALIDATABLE_BY_OBJECT_ID = {
    "organization": Organization, "task": DispatchContract, "decision": CheckpointRecord,
    "learning": OutcomeRecord, "opportunity": Opportunity, "audience": Audience,
    "account": Account, "product": Product, "content_asset": ContentAsset,
    "experiment": Experiment, "tool": ToolRegistryEntry,
}


def cmd_list():
    doc = load()
    for oid, entry in doc["objects"].items():
        print(f"  [{entry['status']:>26}] {oid:<16} {entry['name']}")
    print(f"\n{doc['counts']['active']} active, {doc['counts']['defined_not_yet_produced']} defined-not-yet-produced.")
    print(f"Tool registry: {len(doc['tool_registry'])} real connectors.")
    print(f"Agent registry: see {doc['agent_registry_pointer']} ({doc.get('agent_registry_summary')})")


def cmd_show(object_id):
    doc = load()
    entry = doc["objects"].get(object_id)
    if not entry:
        print(f"No such object: {object_id}. Known: {', '.join(doc['objects'].keys())}")
        sys.exit(1)
    print(json.dumps(entry, indent=2, sort_keys=True))
    cls = VALIDATABLE_BY_OBJECT_ID.get(object_id)
    if cls:
        print(f"\nSchema fields ({cls.__name__}):")
        for fname, finfo in cls.model_fields.items():
            print(f"  - {fname}: {finfo.annotation}")


def cmd_validate(object_id, file_path):
    cls = VALIDATABLE_BY_OBJECT_ID.get(object_id)
    if not cls:
        print(f"No validatable Pydantic schema registered for '{object_id}'. "
              f"Validatable: {', '.join(VALIDATABLE_BY_OBJECT_ID.keys())}")
        sys.exit(1)
    path = Path(file_path)
    if not path.exists():
        print(f"No such file: {file_path}")
        sys.exit(1)
    text = path.read_text(encoding="utf-8").strip()
    lines = text.splitlines() if path.suffix == ".jsonl" else [text]
    ok, fail = 0, 0
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            cls.model_validate_json(line)
            ok += 1
        except ValidationError as e:
            fail += 1
            print(f"  line {i}: FAIL -- {e.errors()[0]['msg']} (field: {e.errors()[0]['loc']})")
    print(f"\n{object_id} <- {file_path}: {ok} valid, {fail} invalid, against {cls.__name__}.")
    return 1 if fail else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "list":
        cmd_list()
    elif cmd == "show":
        cmd_show(sys.argv[2])
    elif cmd == "validate":
        sys.exit(cmd_validate(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__)
        sys.exit(1)
