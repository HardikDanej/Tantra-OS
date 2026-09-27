# Scheduled Prompt — Mon-Fri 6:00am

Paste into Claude Scheduling UI for the SEO Content Factory project.

**Cadence:** Daily at 06:00 (your timezone), Mon–Fri only
**Delivery:** New chat thread + WordPress draft via MCP
**Project:** SEO Content Factory

---

## The prompt

```
Read topic_queue.csv from Project files.

PRECHECK:
- If the file's modification timestamp is older than 30 hours, abort: post nothing, write "stale topic queue" to chat. The nightly cron job likely failed.
- If the file has zero entries with status = "queued", abort: post "topic queue exhausted" to chat and stop. Manual review needed.
- If eeat_evidence.json is missing from Project files, abort: post "evidence library missing — articles will fail E-E-A-T audit" to chat and stop.

TOPIC SELECTION:
- Pick the highest composite_score row where status = "queued"
- Update its status to "in_progress" in topic_queue.csv (rewrite the file with the change)
- Confirm the topic in chat: "Today's topic: [query] (gap_type: [type], composite_score: [N])"

PRODUCTION SEQUENCE — execute all stages without pausing for approval:

STEP 1 — Audience research
Run reddit-insights-bot on the topic. Mine top 5 relevant subreddits. Output: 8–15 verbatim quotes (cited to subreddit), vocabulary patterns, top 3 unmet information gaps. If the skill returns "insufficient Reddit signal," fall through to alternative research sources (LinkedIn comments, Quora, Stack Exchange depending on topic). If no signal anywhere, mark topic as "skipped" in topic_queue.csv with notes "no audience signal available" and pick the next topic.

STEP 2 — Brief generation
Run content-brief-generator using keyword + audience research + assigned_persona (if specified in queue row, otherwise pick best-fit from personas in Project files). Output the structured brief.

STEP 3 — Article drafting
Run long-form-article-architect using the brief. Word count: 2,000 for narrow informational queries, 3,000-4,000 for comprehensive guides, length determined by SERP intent not arbitrary target. Required: defended thesis, integrated citations from eeat_evidence.json (matched by topic_tags), first-person experience markers from brand voice doc, three headline variants.

STEP 4 — E-E-A-T audit
Run core-eeat-benchmark. Score each pillar 1–5 with cited evidence from the article. Verdict: ready_to_publish / needs_revision / fails_quality_bar.

If needs_revision: return to architect with specific revision requirements. Maximum two revision cycles. If still failing after two cycles, mark topic status = "blocked_quality" in topic_queue.csv with notes describing the persistent failure mode, and stop. Do not publish.

If fails_quality_bar: stop immediately. Mark topic status = "blocked_quality". Do not publish.

If ready_to_publish: proceed.

STEP 5 — De-ai-ify pass
Run de-ai-ify on the cleared article. Output the cleaned article and the diff log. If de-ai-ify strips more than 15% of the article, something is wrong (likely brand voice mismatch) — mark topic as "drafted_review_needed" in queue, do not publish, surface the issue in chat.

STEP 6 — WordPress publication
Use the WordPress.com MCP to create a draft post:
- Title: best-performing headline from the three variants (architect picks)
- Slug: URL-friendly version of target keyword
- Meta description: 150-155 characters, generated from article opening
- Excerpt: paste the three headline variants for editor selection
- Categories: pick from existing site categories (query the site if needed)
- Tags: 3-5 relevant tags from existing tag list
- Status: DRAFT (never publish directly — editor reviews before scheduling)

Confirm the WP draft URL.

STEP 7 — Update tracking
- Update topic_queue.csv: change status from "in_progress" to "drafted", add notes with the WP draft URL
- Append to published_log.csv: query, drafted_at timestamp, eeat_score, wp_draft_url, word_count, headline_chosen
- Final chat output: "✓ Drafted: [headline] | E-E-A-T: [verdict] | WP: [draft URL] | Length: [N] words"

If any step fails after Step 1, mark the topic with appropriate status:
- "blocked_no_audience" — Step 1 fell through completely
- "blocked_brief" — Step 2 returned an unworkable brief
- "blocked_quality" — Step 4 failed twice or returned fails_quality_bar
- "drafted_review_needed" — Step 5 over-corrected
- "blocked_wp" — Step 6 connector failure (article preserved in chat)

Then stop. Do not auto-pick another topic. The factory is daily, not iterative.
```

---

## What makes this safe to run unattended

1. **Three precheck conditions** prevent wasted runs on stale data, exhausted queues, or missing evidence libraries.
2. **The status state machine** in `topic_queue.csv` makes failures recoverable. A topic blocked at "blocked_quality" can be reviewed manually, fixed, and re-queued — the workflow doesn't lose the work.
3. **Hard stops on quality failures** — the system would rather skip a day than ship a bad article. This is the right tradeoff because in SEO, one bad article cannibalizes site authority for months.
4. **Maximum two revision cycles in Step 4.** Without this cap, the system could spend an hour trying to rescue an article that should never have been written.
5. **WordPress publication as `draft`, never `publish`.** A human always reviews before going live. The workflow is the writer; the editor remains.

## Reading the daily output

Each morning's chat thread tells you exactly what happened:
- ✓ Drafted = success path, draft is in WordPress
- "topic queue exhausted" = you need to either populate manually or wait for tomorrow's cron
- "blocked_quality" = an article failed audit; check whether the topic is worth pursuing or whether the evidence library needs strengthening
- "stale topic queue" = the cron job failed last night; check that machine

Three days of clean ✓ Drafted output is the signal that the system is calibrated. If you're seeing two or more blocked_quality per week, your evidence library is the bottleneck — populate `eeat_evidence.json` with more topic-specific citations.
