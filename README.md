# Tantra

**A marketing department that runs inside Claude Code. 238 agents, one chain of command, and a hard rule that none of them ever touches your money, your customers, or your live site.**

Most AI marketing tools are one brilliant generalist with a nice prompt. Ask it about SEO, it answers. Ask it about pricing, it answers. Ask it about a crisis, it answers that too, in the same confident voice, with the same blind spots. That works right up to the moment it matters, because a real marketing org was never one person who knows everything. It's specialists who know exactly where their job ends and somebody else's begins.

Tantra is built the second way. It's an org chart, not a chatbot.

---

## The part I tell people about first

Near the end of every strategic request, one agent's whole job is to argue against the answer you're about to get.

It plays your strongest competitor, with roughly twice your budget, and asks one question: what's the fastest, cheapest way to blunt this plan before it ever reaches the market? Ten counter-strategy lenses sit under it: pricing, product, channel, messaging, speed, partnerships, trust, talent, legal, and funding. If your plan survives that, it ships. If it doesn't, you find out from an agent, not from a quarter of lost revenue.

That's the whole philosophy in one feature. Good strategy isn't the plan that sounds right. It's the plan that's still standing after someone tried to break it.

---

## The org chart

| Nickname | Runs | What it owns |
|---|---|---|
| **Hardik** | `enterprise-marketing-orchestrator` | The rare company-wide ask. A full audit. "How are we doing everywhere?" |
| **MTO** | Digital Marketing & Growth | SEO, paid media, website, social, writing, revenue/CRM, growth ops. The biggest system. |
| **BDCVO** | Brand & Creative | Positioning, identity systems, editorial strategy, community. |
| **GTM** | Product Marketing & Go-to-Market | Launches, sales enablement, pricing and packaging. |
| **Researcher** | Market Research & Insights | Primary research, competitive intelligence, attribution. |
| **PR** | PR & Corporate Communications | Media relations, crisis and reputation, events. |
| **Dispatch Bridge** | `cross-system-dispatch-bridge` | The only thing allowed to talk across systems. |

Under those: **21 domain agents**, one per real discipline. Under them: **210 specialists**, each scoped so narrow it can only do the job it's named for. A specialist never calls another specialist. A domain agent never reaches into another system. The moment sideways calls are allowed, nobody can tell you who actually decided what.

Yes, I named the top of it after myself. Somebody has to be the single point where a company-wide question lands. Pretending that seat needs a grander title than the person who built it felt dishonest.

---

## What it refuses to do, on purpose

The agents diagnose, brief, draft, model and design. They don't execute.

No agent spends money. No agent sends an email, posts, or publishes live. No agent writes to your CRM or your ad account. CMS output lands as a draft. An ad-platform or CRM write needs a human approval gate first, and the script re-checks that gate itself instead of trusting the agent that called it.

That refusal is load-bearing. An agent that can only recommend is an agent you can let think aggressively, because the worst case is a bad suggestion, not a bad email that already went out.

And when a decision is expensive to walk back (an annual budget, final creative, a price change, a rebrand, an investor disclosure), Tantra stops and opens a tracked sign-off. "Okay, thanks" doesn't count as approval. Only an unambiguous yes does.

---

## Strategy comes in pairs

Ask a diagnostic question ("is this ad fatigued?") and you get a verdict. Ask a strategic one ("what should our content strategy be next year?") and Tantra is required to hand back **two genuinely different options**, not one idea in two fonts. Each comes as a claim, the evidence behind it, what would prove it wrong, and the smallest real test that tells you which one is right.

An option that hedges instead of committing gets sent back before you ever see it.

---

## It got cheaper, and here's the receipt

An agent system that burns tokens to look thorough has already failed. So I measured it.

I ran the same request twice: a full SEO and paid-media audit of a real company's site, plus a six-month growth plan. The first run was the baseline. It wasted about a third of its output on a Growth Ops fan-out nobody asked for, and its heaviest specialist wrote 5,000 tokens where 1,500 would do. So I fixed the system, not the prompt, and ran it again.

| Same request | Run 1 | Run 2 |
|---|---|---|
| Agents dispatched | 28 (5 never finished) | 13 (all finished) |
| Tokens returned by agents | ~57,900 | ~21,400 (**-63%**) |
| Heaviest single specialist | 5,006 | 1,375 |
| Stalled dispatches | 2 | 0 |
| Output-format repair loops | 8 | 3 |

What changed:

- **A scope router.** Plain Python reads your request and names which departments may work on it. Then run 2 showed something uncomfortable: the orchestrator loaded that instruction and never ran the script. So after run 2, it stopped being an instruction. A hook now enforces the lock before any dispatch happens. Instructions are requests. Hooks are rules.
- **Output budgets for all 210 specialists.** Ranked findings in one fixed format, a hard cap, and no preamble.
- **Measurement moved out of the model.** `site_checks.py` fetches a page and measures status, headers, on-page basics, schema, robots, sitemap, `llms.txt`, links and Core Web Vitals in about 1,000 tokens of JSON, cached so sibling specialists share one fetch. The model only interprets.
- **A leaner orchestrator.** Situational rules load only when the situation actually happens.

One honest caveat: that's two runs, not a benchmark, and run-to-run variance is real. The mechanisms are verified. The exact percentage will move.

---

## What's underneath

- **238 agents** in `.claude/agents/`
- **62 skills** the agents call to do the work
- **7 knowledge bases**, read in slices, never whole
- **27 deterministic scripts** in `.claude/lib/` (approval gates, scope routing, site checks, context budgets, calibration, redispatch caps, provenance). None of them calls a model.
- **8 sentinels** that run as Claude Code hooks and never call a model. **Scribe** keeps the ledger and hands a re-dispatched agent its last answer. **Pulse** catches stalls. **Echo** blocks repeated reads. **Lens** refuses whole-file reads of the knowledge bases. **Contract** fixes a missing output line without a full re-run. **Meter** tracks tokens and time. **Boundary** flags chain-of-command skips. **Scope** enforces the router.
- **Laya**, an optional local classifier trained for calibrated confidence, that gives every approval gate a fast second read before the orchestrator decides. It's a cross-check, never the decision.
- **Approval-gated MCP connectors** for your CRM, analytics or docs. Read-only by default, and nothing connects without an explicit yes.
- **8 workflows** in `marketing-os-infra/` for scheduled, unattended runs once you have real credentials
- **406 tests**, all passing

Nothing here needs a paid API to start. The paid infrastructure only matters when you want something to run on a schedule without you, and `SETUP.md` tells you exactly which tier you're on before you spend anything.

---

## Waking it up

Tantra is the name, not the switch. Saying "Tantra" does nothing.

It wakes when a message starts with `mk`, or says "MK agent" anywhere, and stays on for the session until `mk off`. Without the wake word, Claude Code behaves like plain Claude Code and refuses to dispatch Tantra's agents, even if you name one. Pasted text and code blocks can't switch it on by accident.

```
mk audit example.com's SEO and tell me what to fix first
```

---

## Install

```bash
git clone https://github.com/HardikDanej/Tantra-OS.git ~/Tantra
mkdir -p ~/.claude/skills ~/.claude/agents
ln -s ~/Tantra/.claude/skills/* ~/.claude/skills/
ln -s ~/Tantra/.claude/agents/* ~/.claude/agents/
python ~/Tantra/tools/install_hooks.py user
python ~/Tantra/tools/check_install.py
```

No build step and no dependency tree. It's markdown and stdlib Python in a folder. `INSTALL.md` covers Windows (where symlinks may need admin rights), company workspaces and the optional extras. `SETUP.md` separates what runs today from what needs credentials.

To see what a run cost you:

```bash
python ~/Tantra/.claude/lib/sentinel_report.py report
```

---

## Whose it is

Tantra is mine. Copyright (c) 2026 Hardik Danej, all rights reserved.

This repository is public so you can read it, learn from it and see how it's built. **Public is not the same as open source.** The `LICENSE` doesn't grant you the right to copy, modify, redistribute or use it commercially. If you want to use Tantra for real work, talk to me first. Third-party pieces keep their own licences, listed in `NOTICE`.

To make that provable rather than just stated, there's the **Tantra Seal**: an Ed25519-signed manifest of every file in the OS, a visible copyright notice on every agent and skill with a seal id only my key can produce, C2PA content credentials on deliverables the OS writes into a workspace, and keyed fingerprints that can recognize my text again after it's been reformatted or excerpted. It doesn't stop copying. It proves origin. `provenance/README.md` says exactly what each layer proves and what it doesn't.

---

I didn't build this to prove agents can write ad copy. Any of them can do that on a bad day with no system around them. I built it because the difference between a marketing team and a room full of smart people is structure: who owns what, who checks whom, and who's allowed to say no. That's the product. The agents are just the staff.
