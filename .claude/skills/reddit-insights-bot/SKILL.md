---
name: reddit-insights-bot
description: Activate when the user wants to extract genuine market / customer / competitive insight from Reddit — voice-of-customer language, unmet needs, competitor complaints, emerging trends, niche community dynamics — for marketing research, content ideation, product positioning, or category understanding. Produces structured insight reports with linked sources, exact quotations within fair-use limits, and analytical synthesis. Refuses to scrape Reddit at scale in violation of Reddit's API terms or to harvest user data without ethical justification. Refuses to recommend astroturfing, undisclosed brand participation, or manipulating subreddits. Treats Reddit as a research corpus — read carefully, cite, never manipulate.
---

# Reddit Insights Bot

Reddit is one of the few large public corpora where people speak relatively unfiltered about what they want, hate, struggle with, and recommend. For marketing research, that's gold — provided you read it as research, not as a marketing channel to spam.

## Core principle

**Listen, don't post.** The skill's job is reading: extracting language, frustrations, recommendations, and emerging consensus from communities that produced it organically. Posting in those communities to promote, build links, or game discussion is a different (and usually wrong) skill — handle separately, with disclosure, in alignment with each subreddit's rules.

## When to use

| Situation | Activate? |
|---|---|
| Voice-of-customer research for a category | Yes |
| Competitive intelligence (how customers describe competitors) | Yes |
| Content ideation from real questions / pain points | Yes |
| Product positioning / messaging research | Yes |
| Pre-launch sentiment on similar products | Yes |
| Niche community dynamics (B2B, hobbyist, professional) | Yes |
| Building a list of accounts to DM / harvest emails | Refuse |
| Astroturfing strategy | Refuse |
| Mass-scraping for training data without consent | Refuse |
| One-off "what's a fun subreddit" question | No — too small |

## Workflow

### Step 1: Identify the right subreddits

Don't just go to the obvious ones. For most categories:

**Tier 1 — Direct category subreddits**
- Search Reddit for the category, product type, or problem
- Look for subreddits with > 5K members AND active recent posts
- Examples: r/marketing, r/PPC, r/socialmedia for marketing tools

**Tier 2 — Adjacent communities**
- Where the same audience hangs out for related interests
- e.g., for marketing: r/Entrepreneur, r/smallbusiness, r/SaaS
- Often higher signal than the obvious ones because conversation is more contextual

**Tier 3 — Pain-point subreddits**
- Communities organized around problems the category addresses
- e.g., for productivity tools: r/ADHD, r/Notion, r/getdisciplined

**Tier 4 — Anti-fan subreddits**
- Communities critiquing competitors / category ("X sucks" subs, where they exist)
- Under-rated source for honest objections

For each subreddit, note:
- Subscriber count (proxy for reach)
- Activity level (posts per day; not all big subs are active)
- Tone / culture (skeptical / earnest / technical / casual)
- Mod culture (strict rules vs loose)

### Step 2: Define research questions

Before reading, define what you want to learn. Common questions:

- What words / phrases do people use to describe the problem?
- What products / services do they currently use?
- What do they hate about current solutions?
- What do they wish existed?
- What questions do they ask that aren't well-answered elsewhere?
- What recommendations spread (mentioned by multiple unrelated users)?
- What's the emerging trend / shift in conversation?

Without questions, reading is unstructured and patterns don't surface.

### Step 3: Search and sample

Use Reddit's search:
- Within subreddit: `subreddit:r/marketing keyword`
- Across Reddit: `keyword`
- Filter by time: last week / month / year — recency matters for trends, depth matters for problem framing

Also use:
- **Top posts of all time** in the subreddit — establishes what the community values
- **Hot / Rising** for emerging topics
- **Search by phrase** for specific wording ("how do I", "I'm looking for", "best alternative to")

Read enough to recognize patterns. Typically 30–100 posts + comments per question for solid pattern recognition. Less than 20 is anecdote.

### Step 4: Extract insights with sources

For each insight, note:
- The pattern (what's recurring)
- 2–4 example posts/comments with permalinks
- Date range of the conversation (recency check)
- Counts (how many threads / commenters express this)

Exact quotations: keep short (under ~25 words for fair-use comfort), in quotes, attributed to the username if public + not sensitive (and never to anonymized accounts in sensitive contexts). Paraphrase liberally; quote sparingly.

### Step 5: Categorize patterns

Common categories:

**Language patterns**
- Specific phrases used to describe the problem ("I keep losing track of...")
- Names for product categories ("Notion-likes," "Slack-killers")
- Shorthand and slang

**Pain points**
- Recurring frustrations
- Workflow breakdowns
- Cost / pricing complaints
- Trust issues with vendors

**Solutions in use**
- Tools mentioned (with frequency + sentiment)
- DIY workarounds
- Adjacent products being misused for the job

**Unmet needs / wishlist**
- "I wish there was..."
- "Why doesn't anyone build..."
- "The closest thing is X but it doesn't..."

**Decision criteria**
- What features people prioritize
- Pricing sensitivity
- Switching triggers (what makes someone change tools)

**Sentiment trends**
- Conversations shifting (e.g., "everyone used to love X; now they're complaining")
- Emerging tools entering the conversation
- Communities migrating

### Step 6: Synthesize

The deliverable is not a list of links. It's analysis:

- What does the data tell us about how the audience thinks?
- What's the gap our offering could fill?
- What language should our marketing use that we're not using?
- What competitors are weak / strong in customer perception?

Insight is the synthesis. Without it, you've delivered a clipping service.

### Step 7: Don't manipulate

Once you have insights, the temptation is to act on them in Reddit itself. Resist most of the time:

**Acceptable**
- Replying to questions in subreddits where you've disclosed your affiliation, when you genuinely have value to add and the community allows it
- Posting your own content where the subreddit explicitly allows promotional posts
- Engaging organically as a brand (verified accounts, with the brand attribution clear)

**Not acceptable**
- Posting from non-disclosed accounts
- Creating accounts to upvote your content / downvote competitors
- Mass DMing users
- "Asking a question" you've staged to drive answers toward your product
- Posting in subreddits whose rules forbid promotion

Reddit moderators and users detect inauthentic behavior. Backlash is severe. Just don't.

## Output format

```
# Reddit Insights — [Topic / Category] — [Date]

## Subreddits researched
| Subreddit | Members | Activity | Tone |
|---|---|---|---|

## Research questions
1. [Question]
2. ...

## Sample size
- Threads read: N
- Comments analyzed: M
- Date range: [from – to]

## Patterns

### Language
- Phrase X used in [N] threads
  - Example: "[short quote]" — [permalink, date]
  - Example: ...

### Pain points
- [Pain] — frequency: high / med / low
  - Examples: [permalinks]
  - Synthesis: [what this tells us]

### Solutions in current use
| Tool | Mentions | Sentiment | Notes |
|---|---|---|---|

### Unmet needs
- [Need]
  - Quotes: ...
  - Synthesis: ...

### Sentiment trends
- [Trend with evidence]

## Synthesis
[The interpretive section — what this means for the brand / product]

## Recommendations
1. [Marketing / product / content action]
2. ...

## Caveats
- Reddit is not representative of [demographic / audience]
- Patterns from [community X] may not generalize
- Recency: most active discussion was [period]
```

## Anti-patterns

1. ❌ Quoting long passages — fair use; keep quotes short, link to source for full context
2. ❌ Identifying users by name in sensitive contexts — pseudonyms are still people; respect privacy
3. ❌ Reporting "sentiment is 70% negative" without methodology — sentiment claims need defined methodology, not vibes
4. ❌ Confusing "Reddit said X" with "the market says X" — Reddit is a slice; varies by category
5. ❌ Cherry-picking quotes that confirm hypothesis — note disconfirming evidence too
6. ❌ Skipping date ranges — old threads may not reflect current sentiment
7. ❌ Treating one viral post as a trend — sample of 1
8. ❌ Confusing insight with information — listing what people said is reporting; analyzing why is insight
9. ❌ Recommending posting in subreddits without checking their rules — rapid bans, brand damage
10. ❌ Mass-scraping in violation of Reddit API terms — terms exist for good reason
11. ❌ Building user lists from Reddit for outreach — privacy violation, manipulative
12. ❌ Over-relying on Reddit as the only research source — triangulate with surveys, interviews, other communities
13. ❌ Ignoring subreddit-specific culture — same words mean different things across communities
14. ❌ Reporting community opinion as universal truth — Redditors skew younger, English-speaking, technical, skeptical; not your whole market

## Confidence calibration

- Pattern recognition from substantial sample: high
- Pattern projection to the broader market: medium-low — Reddit's bias is real
- Specific product / tool sentiment: medium — recency matters; tools rise/fall fast
- Predicted impact of acting on insights: refuse to predict; treat as research that informs, not decides
