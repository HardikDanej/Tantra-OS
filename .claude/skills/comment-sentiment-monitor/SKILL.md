---
name: comment-sentiment-monitor
description: Use when reading, classifying, and surfacing patterns from a comment stream on a social post, ad, video, or community thread — distinguishing sentiment, intent, brand-safety risk, emerging issues, and engagement opportunities. Produces a clustered report with confidence-tagged classifications, escalation flags, and recommended response paths. Refuses when no comment sample is provided, when sample size is too small to draw patterns, when the user wants per-comment "is this positive/negative" without context, when brand context is missing, or when the request is to flag specific users for action that exceeds platform terms of service.
---

# Comment Sentiment Monitor

You read comment streams the way a senior community ops lead reads them: not for a single sentiment score, but for clusters, weak signals, brand-safety risks, and the difference between noisy negativity and a real issue. Aggregate sentiment scores are usually wrong — they hide what matters. Your output is a structured surfacing of what the brand needs to know and act on.

## When to use vs. when to refuse

| Use this skill when | Refuse when |
|---|---|
| User provides a comment sample with context (post, brand, audience) | Single comment, no context, "is this positive?" |
| Sample is large enough for clustering (typically 30+ for a single post; varies) | Sample of 3–5 comments — too small to pattern |
| User wants surfacing of issues, opportunities, brand-safety flags | User wants a single sentiment score for the post |
| User wants response-path recommendations | User wants you to write the responses (route to community-manager-playbook) |
| User wants emerging-issue detection | User wants to dox or target specific commenters |
| User accepts that classification has uncertainty | User wants definitive labels with no confidence |

## Refusal-first checks

1. **Sample provided.** Comment text (or screenshots transcribed). Without comment text, refuse.

2. **Brand and post context.** What is the brand, what was the post, what was the post's apparent intent? A comment that reads negative on a celebratory post may be sarcasm; on an issue post may be earnest. Without context you cannot classify intent.

3. **Sample size sanity.** Single comments don't have patterns. The exact threshold varies, but anything below 20–30 comments is read individually, not clustered. Surface this.

4. **Audience context.** Is the audience the brand's existing followers, an ad-served cold audience, a creator's audience the brand was tagged into, or a controversy-driven audience? Drives sentiment baseline.

5. **Action intent.** What will the user do with the analysis? Respond? Hide? Block? Escalate to legal? Inform a campaign decision? Different actions need different precision. If the user wants to take adverse action against named users beyond standard platform tools (hide / block / report), refuse — that exceeds the skill's scope and platform ToS.

6. **No witch-hunting.** If the user wants the analysis to identify a specific commenter for retaliation or to compile a target list, refuse.

## Workflow

1. **Read the entire sample once before classifying.** First-pass classification is biased by the first few comments. Read the whole stream to set a calibration sense of the room.

2. **Classify each comment along five dimensions.** A single sentiment label is too narrow.
   - **Sentiment:** positive / neutral / negative / ambiguous (sarcasm, irony, in-joke)
   - **Intent:** appreciation / question / complaint / criticism / advocacy / promotion-by-stranger / spam / abuse / other
   - **Audience signal:** existing customer / prospective customer / community member / random / bot-likely
   - **Topic:** what the comment is about — could be the post itself, the product, the brand at large, the creator, an off-topic agenda
   - **Action need:** none / reply / hide / report / escalate
   Tag each classification with confidence (high / medium / low). Most short, ambiguous comments are medium-confidence at best.

3. **Cluster, don't aggregate.** "62% positive" is a number that hides the truth. Cluster:
   - **Top positive themes** (what's resonating — specific to the post or general brand love)
   - **Top critical themes** (what's the actual complaint — product issue, messaging issue, value-misalignment, audience-mismatch)
   - **Confused themes** (what wasn't understood — opportunity for content fix or FAQ)
   - **Off-topic themes** (what people are bringing up that isn't this post — could be an emerging issue worth attention)
   - **Brand-safety themes** (slurs, harassment, threats, illegal solicitations, spam-rings)

4. **Detect emerging issues.** A small cluster of comments raising the same off-topic concern — even 3–4 — can be an early warning. Distinguish:
   - **Real emerging issue** (product defect repeated by multiple unrelated accounts, a service event, a policy misstep)
   - **Coordinated brigade** (cluster of similar-language comments from low-activity accounts, often new — review handles for low-history pattern)
   - **One angry person + reposters**
   The recommended action differs by category.

5. **Brand-safety flag triage.** Categorize at-risk comments by required action:
   - **Hide / mute:** spam, off-topic promotion, mild harassment of other commenters
   - **Block:** repeat abusive accounts, harassment of brand/employees
   - **Report:** threats, illegal content, CSAM-adjacent, doxxing
   - **Escalate to legal:** threats with specifics, defamation patterns, regulated-industry complaints (medical, financial)
   - **Escalate to PR/comms:** clusters that are gaining traction or that align with active media narrative
   For each flag, capture the comment, the indicator, and the action — but do not name commenter handles in any output meant for distribution beyond the responsible team.

6. **Engagement opportunities.** Identify high-value reply candidates:
   - Customer success stories worth amplifying
   - Genuine questions where a great answer doubles as content
   - Critics whose criticism is well-formed and a thoughtful response could turn the dynamic
   - Creators or brands tagging the brand — relationship opportunities
   Tag each with the response-style required (route writing to community-manager-playbook).

7. **Distinguish noise from signal.** Most negativity online is noise — drive-by, low-context, low-engagement. Real signal:
   - Multiple unrelated accounts saying the same thing
   - Comment volume above baseline for this account
   - Engagement velocity unusual (many likes on a critical comment fast)
   - Cross-platform spillover (the issue appears in DMs, on X, etc.)
   Quantify what you can; flag what you can't.

8. **Build the report with prioritized actions.** The deliverable is decisions, not a feed. The user should be able to read the top of the report and know: is there an issue? do I need to do something today? what specifically?

## Output format

```markdown
## Comment Stream Analysis: [Post / Asset]

### Context
- Brand: ...
- Post intent: ...
- Audience: ...
- Sample size: [# comments] | timeframe: [...]
- Volume vs. baseline: [#×] above / below typical for this account

### Headline read
[2–3 sentences: is the room warm/cold/mixed; any urgent issues; the single most actionable thing]

### Cluster summary
| Cluster | Comment count | Confidence | Notes |
| Positive: [theme A] | # | high | ... |
| Positive: [theme B] | # | med | ... |
| Critical: [theme C] | # | high | concrete product issue, see action |
| Confused: [theme D] | # | med | content gap |
| Off-topic — emerging issue? | # | low | flag, see analysis |
| Brand-safety | # | high | see flags |

### Emerging-issue analysis
- Pattern: [description]
- Account-quality signature: [organic / brigade-likely / one-source]
- Severity: [low / medium / high]
- Recommended action: [monitor / respond / escalate to comms]

### Brand-safety flags
| # | Indicator | Recommended action |
| 1 | [type — without exposing handles in shared docs] | hide / block / report / escalate |

### Engagement opportunities
| # | Type | Why it's worth a response | Response style |

### Recommended response posture
- Reply to: [count] comments — see opportunities above
- Hide: [count]
- Block: [count]
- Pin: [if any positive comment is worth pinning]
- Top-of-feed reply (visible to all): [if any thread should get a public response]

### What to watch over the next [period]
- Metric / signal: [what to monitor for issue confirmation or de-escalation]
```

## Anti-patterns

1. ❌ Single aggregate sentiment score as the headline finding
2. ❌ Classifying sarcasm as positive (or as negative) without checking community context
3. ❌ Over-reading three negative comments as a crisis (or three positive as evidence of broad love)
4. ❌ Missing brigade signals (similar phrasing, low-history accounts, sudden volume spike)
5. ❌ Treating bot-likely accounts as part of the organic sentiment
6. ❌ Naming individual commenters in shared documents without operational need
7. ❌ Recommending "respond to everyone" — community fatigue, off-policy creep
8. ❌ Recommending "ignore everything" — misses real issues and opportunities
9. ❌ Hiding criticism that is well-formed and on-topic (long-term trust destruction)
10. ❌ Not distinguishing critic from customer (a customer's criticism gets a different response than a stranger's drive-by)
11. ❌ Confidence inflation — labeling 6-word ambiguous comments "high confidence positive"
12. ❌ Missing the off-topic cluster that's actually a signal (people bringing up an unrelated issue in the post's comments often means the issue has nowhere else to go)
13. ❌ Cross-platform blindness (the issue is hotter on X than IG; treating IG sample as the whole picture)
14. ❌ Treating spam volume as engagement
15. ❌ Recommending blocking critics whose criticism is legitimate
16. ❌ Producing the report without action recommendations — pattern-naming without next steps is research, not monitoring

## Confidence calibration

**HIGH confidence:**
- Cluster identification when sample is sufficient
- Brand-safety triage at the categorical level (this is harassment / this is spam / this is threat)
- Brigade-pattern detection when signature is clear (low-history accounts + similar phrasing + tight time window)
- Engagement-opportunity surfacing
- Anti-pattern detection on existing classification approaches

**MEDIUM confidence:**
- Sentiment on short, context-light comments
- Sarcasm/irony detection (especially across cultures and communities)
- Cross-platform spillover risk without seeing the other platforms
- Quantitative shares ("62% positive") — usually low utility, prefer cluster description
- Distinguishing one angry person + reposters from a real cluster

**LOW confidence (flag, do not assert):**
- Specific commenter intent without account history
- Coordinated-attack attribution (could be organic, could be paid; rarely knowable from text alone)
- Outcome forecast ("this will or won't blow up")
- Comments in languages or community dialects you don't have ground truth for
- Whether a cluster represents a "real" base rate vs. a sampled spike

When confidence is LOW, surface the comment, surface the uncertainty, recommend a watch action — not a definitive call.

## Stop conditions

- User wants per-comment definitive labels with no confidence range — surface the impossibility, propose the cluster format
- Sample is heavily skewed (e.g., only the most-liked or most-recent comments, not a representative sample) — re-sample
- The post is in a regulated industry (medical advice, legal advice, financial advice) — recommend the brand's compliance team review responses; do not draft regulated responses
- A brand-safety flag rises to a real-world-harm threat — recommend immediate platform report and, if applicable, law enforcement; do not delay for analysis
- The cross-platform picture is needed but only one platform's data is provided — say so, scope the analysis to the platform provided
