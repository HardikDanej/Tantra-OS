# Workflow 03: Brand Launch Suite — Agent-Orchestrated Edition

**Change from the original marketing-os version:** the smallest change of the four, because this workflow already maps almost one-to-one onto a single agent. The six-stage sequence, the skills, the stage-gating logic, and the refusal conditions all now live inside the **Marketing Strategist Agent** (see marketing-strategist.md) rather than a standalone Project system prompt — the Chief Orchestrator's role here is thin: dispatch once, receive the finished playbook, and — critically — distribute the three machine-readable outputs to the other workflows.

## What triggers this workflow

Same as before: `asset_ingestion.py` normalizes brand assets into `brand_inputs.json`, run once per brand launch/rebrand engagement (no scheduling — this is a deliberate one-time or occasional engagement, not a recurring cron job).

## The dispatch sequence

```
User or scheduled trigger: "mk run brand foundation for [brand]"  (wake word; or TANTRA_ACTIVE=1 when headless)
        │
        ▼
CHIEF ORCHESTRATOR — DISPATCH mode
  Step 1 (Gatekeeper): if brand_inputs.json has fewer than 5 total assets,
    surface this BEFORE dispatching rather than let the Marketing Strategist
    Agent discover it mid-engagement: "only N assets available — Stage 1
    will be thin. Proceed anyway with hedged output, or gather more first?"
  Step 2 (Decomposition): single workstream, but internally staged (the
    Marketing Strategist Agent's own six-stage sequence — audit → personas →
    voice → GEO → content system → playbook). The Orchestrator dispatches
    once for the full engagement; it does not re-dispatch per stage unless
    the Marketing Strategist Agent itself halts on a stage-specific refusal.
  Step 3 (Contract):
    AGENT: Marketing Strategist Agent
    OBJECTIVE: full six-stage brand foundation engagement, ending in playbook
      assembly
    INPUTS: brand_inputs.json, input_schema.json (category weighting)
    CONSTRAINTS: stage order is non-negotiable; personas/voice must be
      language-grounded, not demographic-templated; voice must include
      forbidden patterns; 90-day content system must fit 1 lead + 1 freelancer
    REQUIRED OUTPUT SHAPE: brand_playbook.md + personas.json + voice_system.json
      + icp_definition.md
    CONFIDENCE REPORTING: required, per artifact — a "constructed" (not
      "extracted") voice for a pre-launch brand must be flagged as such
        │
        ▼
MARKETING STRATEGIST AGENT (runs its own six-stage internal sequence —
  see marketing-strategist.md for full stage logic and refusal checks)
        │
        ▼
CHIEF ORCHESTRATOR — SYNTHESIZE mode
  Step 2 (Epistemic Uncertainty Mapping): if the voice system is flagged
    "constructed" (pre-launch, no real voice signal yet) or any persona is
    low-confidence, surface this prominently — these are the artifacts every
    other agent will treat as ground truth going forward, so understating
    their uncertainty here propagates downstream
  Step 3 (Self-Correction Pass): check that the produced ICP definition, voice
    system, and personas are internally consistent with each other (e.g., the
    ICP's stated decision-maker profile should not contradict a persona's
    stated authority level) — this is the one place a genuine cross-artifact
    consistency check matters even within a single agent's output, because
    these three documents will be cited independently by three different
    downstream agents who won't cross-check them against each other
  Step 4 (Progressive Disclosure): return the playbook summary + the three
    structured files; the full 8,000–15,000 word playbook is available on
    request, not dumped by default
  Step 5 (Checkpoint) — the most consequential checkpoint in the whole system:
    write personas.json, voice_system.json, and icp_definition.md to a
    location the other three workflows' dispatches can reference by default
    going forward. From this point on, every Campaign Intelligence, SEO
    Content Factory, and HubSpot Revenue Agent dispatch for this brand should
    include these three files as standing inputs, not something the user has
    to remember to re-attach each time.
```

## Deliverables (unchanged from the original)

```
outputs/
├── brand_playbook.md       ← the deliverable a new hire reads to onboard
├── personas.json           ← consumed by Ads Agent (via Orchestrator) and SEO Agent
├── voice_system.json       ← consumed by Ads Agent, SEO Agent, and Writing Agent
└── icp_definition.md       ← consumed by Revenue/CRM Agent
```

## What changed vs. the original marketing-os version, and why it matters

Functionally, almost nothing changed in how the six stages run — that logic was already sound and is now just formally owned by the Marketing Strategist Agent rather than a Project-level system prompt. What's new is the Orchestrator's explicit responsibility to treat this workflow's output as **standing state for every other workflow**, not just a file the user has to remember to re-upload into three other Projects. The original marketing-os README already said "run 03 first... plug its outputs into 01, 02, and 04" as manual advice; the Orchestrator's checkpoint logic now makes that propagation automatic rather than dependent on the user remembering to do it.
