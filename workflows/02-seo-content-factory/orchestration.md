# Workflow 02: SEO Content Factory — Agent-Orchestrated Edition

**Change from the original marketing-os version:** the biggest structural change of all four workflows. Originally, one Project's system prompt ran `long-form-article-architect` for drafting AND `core-eeat-benchmark`/`de-ai-ify` for QA — strategy and execution lived in the same undifferentiated role. Now those are split across two agents with a mandatory round-trip: the **SEO Agent** never drafts, the **Writing Agent** never sets keyword/audience strategy.

## What triggers this workflow

Same as before: `gsc_keyword_pull.py` runs nightly via cron, updates `topic_queue.csv`, a scheduled task fires weekday mornings at 6am.

**Activation:** Tantra's agents are only dispatched once Tantra is active, so the scheduled prompt that fires this workflow starts with the wake word `mk ` (e.g. "mk run the daily SEO content factory"); a scheduled or headless run may alternatively set `TANTRA_ACTIVE=1` in its environment.

## The dispatch sequence

```
Scheduled trigger (weekday 6am)
        │
        ▼
CHIEF ORCHESTRATOR — DISPATCH mode
  Step 1 (Gatekeeper): none needed on a routine run — topic_queue.csv already
    encodes the priority decision from the prior night's pull. If the queue is
    empty or every remaining topic was already rejected in a prior run, THAT
    is the one condition worth surfacing as a consolidated question: "topic
    queue is dry / stuck — want me to lower the scoring threshold, or is
    there a manual topic to inject?"
  Step 2 (Decomposition): two sequential workstreams — SEO Agent (strategy)
    must complete before Writing Agent (drafting) starts. Not parallel; this
    is a genuine data dependency.
  Step 3 (Contract #1):
    AGENT: SEO Agent
    OBJECTIVE: pick the top-scored unworked topic, research it, produce an
      approved brief
    INPUTS: topic_queue.csv, personas.json + voice_system.json (from Marketing
      Strategist Agent, if a Brand Launch Suite run exists for this brand)
    CONSTRAINTS: refuse keywords under 100 monthly searches without strategic
      justification; refuse YMYL topics without a named expert byline
    REQUIRED OUTPUT SHAPE: per SEO Agent's own contract format (brief, not draft)
    CONFIDENCE REPORTING: required
        │
        ▼
SEO AGENT (topic prioritization → audience research via reddit-insights-bot →
  brief construction via content-brief-generator — see seo-agent.md)
        │
        ▼
CHIEF ORCHESTRATOR — re-enters DISPATCH mode for workstream 2
  Step 4 (Contract #2):
    AGENT: Writing Agent
    OBJECTIVE: draft the full article against the SEO Agent's approved brief
    INPUTS: the approved brief, voice_system.json (if available)
    CONSTRAINTS: 2,000–4,000 words per brief target; every claim sourced or
      hedged; anti-hallucination/anti-confabulation/de-ai-ify are standing,
      non-optional passes (see writing-agent.md)
    REQUIRED OUTPUT SHAPE: markdown with frontmatter (title, meta description,
      slug, focus keyphrase, internal link targets)
    CONFIDENCE REPORTING: required, split craft vs. factual grounding
        │
        ▼
WRITING AGENT (routes to long-form-article-architect internally, or seo-writer/
  geo-aio-writer if the SEO Agent's brief named a specific target surface —
  runs the mandatory de-ai-ify pass before returning)
        │
        ▼
CHIEF ORCHESTRATOR — dispatches the draft BACK to SEO Agent for audit
  Step 5 (Contract #3):
    AGENT: SEO Agent
    OBJECTIVE: E-E-A-T audit + citation/GEO check on the returned draft
    INPUTS: the drafted article, eeat_evidence.json
    REQUIRED OUTPUT SHAPE: verdict (ready_to_publish / needs_revision /
      fails_quality_bar) with per-pillar scoring
        │
        ▼
   IF needs_revision or fails_quality_bar:
      → Orchestrator re-dispatches to Writing Agent with the specific
        required changes attached. One revision cycle. A second failure
        escalates to the user rather than cycling again blind (this mirrors
        the Writing Agent's own stop condition).
   IF ready_to_publish:
      → proceed to SYNTHESIZE mode
        │
        ▼
CHIEF ORCHESTRATOR — SYNTHESIZE mode
  Step 2 (Epistemic Uncertainty Mapping): a "ready_to_publish" verdict built on
    an empty eeat_evidence.json is a capped-confidence pass, not a true high —
    the SEO Agent's own GAPS field should already say this; if it doesn't,
    treat the omission itself as a flag
  Step 4 (Progressive Disclosure): call `marketing-os-infra/02-seo-content-factory/
    cms_publish.py --article <finished draft>` to create the draft on the
    configured CMS (WordPress or Webflow — draft-only, enforced in
    `marketing-os-infra/lib/cms_connector.py`, not a flag this step can
    override), return a compact summary + draft URL, keep the full research
    dossier/brief/audit/de-ai-ify diff log available on request rather than
    inlined by default. If the call returns an error, surface it plainly —
    this is the one step in the pipeline that touches a live external
    system, so a silent failure here means an audited, approved article
    just vanishes instead of reaching the CMS.
  Step 5 (Checkpoint): move the topic from queued → drafted in topic_queue.csv,
    log confidence and any evidence-library gaps for the next run to inherit
```

## Deliverables per article (unchanged in substance from the original)

1. Audience research dossier (SEO Agent, reusable for related topics)
2. Editorial brief (SEO Agent, archived)
3. Drafted article (Writing Agent)
4. E-E-A-T audit scorecard (SEO Agent)
5. De-ai-ify diff log (Writing Agent — now a first-class deliverable, not buried inside one agent's internal process)
6. CMS draft (WordPress or Webflow, created via `cms_publish.py` once the Orchestrator's synthesis completes — always a draft, never live)
7. Updated `topic_queue.csv`

## What changed vs. the original marketing-os version, and why it matters

The original workflow let one role write the article AND grade its own E-E-A-T homework in the same undifferentiated pass — a real, if soft, conflict of interest. Splitting strategy (SEO Agent) from execution (Writing Agent) with a mandatory round-trip means the audit is now genuinely independent of the drafting: the agent that wrote the piece isn't the one deciding whether it's good enough to publish. The original's own troubleshooting section flagged "every article passes E-E-A-T audit on first try" as a red flag for a too-lenient audit — that risk is structurally lower now because the two roles don't share incentives to agree with each other.
