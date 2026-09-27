# Workflow 03: Brand Launch Intelligence Suite

**Surfaces used:** Claude Code · Cowork · Claude Chat (Projects + Skills) · Google Drive MCP (optional)
**Cadence:** One-time per brand launch or rebrand (no scheduling needed)
**Setup time:** ~1 hour for asset normalization, then 4–6 hours of guided execution
**Best for:** Brand launches, rebrands, or fixing brands that have drifted

---

## What this workflow does

Unlike the recurring workflows (01, 02, 04), this is a single deep engagement. The Claude Code component does the heavy lifting *upfront* — ingesting a folder of brand assets in mixed formats (PDFs, DOCXs, audio interviews, web copy, social exports), normalizing everything into a single structured input file. Then the chat-based 6-stage workflow runs with all assets already analyzed and indexed.

The reason for the Code component: a typical brand engagement has 30–80 input artifacts in 6+ formats. Asking Claude Chat to ingest these one by one wastes hours of session time on parsing instead of strategy. The script normalizes all of them in 5 minutes, producing a single `brand_inputs.json` that the chat workflow consumes as a unified knowledge base.

**Critical:** the outputs of this workflow (`personas.json`, `voice_system.json`, `icp_definition.md`) are upstream inputs for Workflows 01, 02, and 04. Run this first if you don't already have a documented brand foundation.

---

## Architecture

```
                ┌──────────────────────────────┐
                │  ~/marketing-os/03-.../      │
                │  inputs/                     │
                │  ├── interviews/ (PDFs, MP3s)│
                │  ├── web/        (HTML, MD)  │
                │  ├── social/     (CSVs, MD)  │
                │  ├── customer/   (PDFs, CSVs)│
                │  └── prior_brand/ (any)      │
                └────────────┬─────────────────┘
                              │
                              ▼ (Claude Code, manual run)
                ┌──────────────────────────────┐
                │  asset_ingestion.py          │
                │  • PDF text extraction       │
                │  • Whisper audio transcribe  │
                │  • HTML → markdown           │
                │  • Schema normalization      │
                └────────────┬─────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │  brand_inputs.json           │
                │  (single normalized file)    │
                └────────────┬─────────────────┘
                              │
                              ▼ (Cowork or manual upload)
                ┌──────────────────────────────┐
                │  Claude Project Files        │
                │  Brand Launch Suite          │
                └────────────┬─────────────────┘
                              │
                              ▼ (Manual run, 6 stages)
                ┌──────────────────────────────┐
                │  Stage 1: brand-intelligence-auditor    │
                │  Stage 2: psychographic-profiler        │
                │  Stage 3: brand-voice-extractor         │
                │  Stage 4: geo-aeo-optimizer             │
                │  Stage 5: content-strategist            │
                │  Stage 6: series-bible-architect        │
                └────────────┬─────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │  outputs/                    │
                │  ├── brand_playbook.md       │
                │  ├── personas.json           │ → consumed by 01, 02
                │  ├── voice_system.json       │ → consumed by 01, 02
                │  └── icp_definition.md       │ → consumed by 04
                └──────────────────────────────┘
```

---

## Files in this workflow

| File | Purpose | Where it runs |
|------|---------|---------------|
| `asset_ingestion.py` | Walk inputs folder, extract/normalize all asset types | Claude Code (your machine) |
| `input_schema.json` | Schema for the normalized brand_inputs.json | Read by ingestion script |
| `system_prompt.md` | Project system prompt for the strategist role | Pasted into Project settings |
| `stage_orchestration.md` | The six-stage prompt sequence with specific prompts per stage | Used during the manual chat run |

---

## Setup (1 hour, one time)

### 1. Folder structure (5 min)

```bash
cd ~/marketing-os/03-brand-launch-suite
mkdir -p inputs/{interviews,web,social,customer,prior_brand,competitive}
mkdir -p outputs
```

### 2. Local environment (15 min)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pypdf2 python-docx beautifulsoup4 markdownify openai-whisper pandas
```

The `openai-whisper` install is heavy (~2GB with model download) — skip if you have no audio inputs.

### 3. Drop assets into folders (varies — typically 30 min)

The folder structure tells the ingestion script how to categorize each asset:

```
inputs/
├── interviews/        ← founder interviews, podcast appearances, customer calls
│   ├── founder_2024_10_15.pdf
│   ├── customer_jane_doe.mp3
│   └── ...
├── web/               ← homepage, about page, product pages, landing pages
│   ├── homepage.html
│   ├── about.md
│   └── ...
├── social/            ← LinkedIn posts, Twitter exports, Instagram captions
│   ├── linkedin_export.csv
│   └── twitter_archive.zip
├── customer/          ← testimonials, case studies, support transcripts, reviews
│   ├── g2_reviews_export.csv
│   └── case_study_acme.pdf
├── prior_brand/       ← any existing brand book, voice guide, positioning doc
│   └── 2023_brand_book.pdf
└── competitive/       ← competitor sites, positioning, key differentiators
    └── competitor_audit.md
```

The more, the better. The depth of input directly determines the depth of output. 5 assets → hedged, low-confidence personas. 50 assets → grounded, high-confidence personas.

### 4. Run the ingestion script (5 min)

```bash
python3 asset_ingestion.py
```

Expected output:
```
[Inputs] Found 47 assets across 6 categories
[PDF] Processing 14 PDFs... done
[Audio] Processing 3 MP3s with Whisper... done (took 4 min)
[HTML] Processing 8 HTML files... done
[Markdown] Processing 12 MD files... done
[CSV] Processing 7 CSVs... done
[DOCX] Processing 3 DOCX files... done
[Output] brand_inputs.json written (84 KB)
[Output] inputs_manifest.csv written (47 rows)
```

The `inputs_manifest.csv` is your verification file — scan it to confirm everything was picked up.

### 5. Upload to Claude Project (5 min)

- Create Project: "Brand Launch Suite"
- Upload skills: `brand-intelligence-auditor.md`, `psychographic-profiler.md`, `brand-voice-extractor.md`, `geo-aeo-optimizer.md`, `content-strategist.md`, `series-bible-architect.md`
- Upload `brand_inputs.json` and `inputs_manifest.csv` to Project files
- Paste `system_prompt.md` into Project custom instructions

### 6. Run the engagement (4–6 hours, split across 2 sessions)

Open `stage_orchestration.md` and execute the prompts in order. Stages 1–3 run in Session 1 (~3 hours). Stages 4–6 run in Session 2 (~2 hours). The split exists because voice extraction (Stage 3) is cognitively heavy and benefits from a fresh chat for Stage 4.

### 7. Save outputs for downstream workflows

After Stage 6 completes, the final playbook contains structured JSON blocks for personas, voice system, and ICP. Extract these to standalone files:

```bash
# In the chat after Stage 6, ask Claude to:
# "Output personas.json, voice_system.json, and icp_definition.md as separate
# downloadable files I can use as inputs for the other workflows."
```

Drop these into:
- `~/marketing-os/03-brand-launch-suite/outputs/`
- Project files of Workflows 01, 02, and 04 (so those workflows can read them)

---

## Why this architecture beats pure-chat brand engagements

The original chat-only version of Workflow 03 worked, but had two friction points:

1. **Asset ingestion ate session time.** Uploading 47 mixed-format files to chat one at a time, asking Claude to read each, and remembering which insight came from which source consumed 60–90 minutes per engagement before any strategy work began.

2. **Audio inputs were excluded.** Founder podcast transcripts were typically the most voice-revealing source material, but transcribing them manually was friction nobody wanted.

The Code component solves both. Whisper transcribes audio in minutes. Mixed-format ingestion happens in parallel. The chat session opens with all source material already analyzed, indexed, and queryable as a single JSON.

The downstream effect: voice extraction (Stage 3) gets dramatically richer because it can pattern-match across audio transcripts, not just written copy. Founder voice is usually closest to "the real brand voice" — and audio captures it in a way written copy doesn't.

---

## Refusal patterns

The system will refuse to:

- Run Stage 1 with under 5 brand assets ingested (audit needs evidence)
- Build personas in Stage 2 without customer language inputs (testimonials, reviews, support transcripts) — refuses to invent personas from demographic templates
- Extract voice in Stage 3 with under 3 founder/exec-authored inputs (interviews, LinkedIn posts, internal writing) — voice without founder signal is template, not voice
- Skip stages or run them out of order (audit must precede personas; personas inform voice; voice and personas inform GEO; all four inform content)
- Generate "aspirational" voice when assets show a different actual voice — voice is descriptive of reality, not normative aspiration

If you're getting refusals, the most common cause is thin input. Go gather more before forcing through.

---

## Outputs and downstream consumption

```
outputs/
├── brand_playbook.md       ← the deliverable a new hire reads to onboard
├── personas.json           ← machine-readable; consumed by 01 and 02
├── voice_system.json       ← machine-readable; consumed by 01 and 02
└── icp_definition.md       ← human + machine-readable; consumed by 04
```

After running this workflow, you go back to Workflows 01, 02, and 04 and update their Project files with these outputs. Suddenly:
- Workflow 01's creative briefs are voiced correctly because voice_system.json is loaded
- Workflow 02's articles target the right personas because personas.json is loaded
- Workflow 04's deal qualification scores against a real ICP because icp_definition.md is loaded

The compounding value is real. Workflow 03 once → quality lift across all three recurring workflows continuously.
