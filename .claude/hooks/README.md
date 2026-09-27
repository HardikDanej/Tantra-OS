# Tantra hooks: wake word, sentinels, guards

Everything in this folder runs as Claude Code hooks through one dispatcher, `tantra_hook.py`. It is stdlib-only, fails open, and stays silent while Tantra is off. Connector approvals are documented in `connectors/README.md`, deliverable signing in `provenance/README.md`.

## Switching Tantra on: the wake word

Tantra is the name of the OS. Saying "Tantra" does not switch anything on.
The marketing OS turns on only when you use the wake word:

| You type | What happens |
| --- | --- |
| `mk audit acme.com's SEO` | On. The message starts with "mk". An `[Image #1]` placeholder, an `@file` mention or `ultrathink` in front of it is skipped. |
| `MK, what's our crisis plan?` / `mk: pricing tiers` / `@mk ...` / `/mk ...` | On. The first word is "mk" in any case, followed by a space, the end of the message, or `, : ; ! ? .` or an em dash. |
| `Hey MK agent, plan our launch` / `mk-agent ...` / `mkagent ...` | On. "MK agent" or "mk-agent" counts anywhere in the message, in any case. The glued forms `mkagent` / `mk_agent` count only as the first word, because mid-sentence they are usually code identifiers. |
| `ok mk, run the audit` | On. A lowercase "mk," or "mk:" in the middle of a sentence is read as you addressing the OS, unless it sits in a list of language codes (`en, de, mk, sq`) or after a label (`Supported: mk: ...`). |
| `use tantra to plan the launch` | Nothing happens. |
| `mkdir`, `mktemp`, `mkdocs`, `rules.mk`, `mk.txt`, `mk-2`, `MK11`, `Spitfire Mk II`, `Michael Kors (MK)`, `set lang to mk`, `locales: en, mk, sr`, `the variable mk_agent` | Nothing happens. |

Once it's on, it stays on for the rest of that Claude Code session. You don't
need to repeat "mk" in follow-ups like "approve the gate" or "continue".

To switch it off, send `mk off`, `mk stop`, `mk exit`, `mk sleep`,
`mk deactivate` or `mk turn off` as the whole message (a trailing "please",
"now", "thanks" or "for today" is fine, and so is `please mk off`). A message
that contains "stop mk", "exit mk", "quit mk" or "turn off mk" also works,
unless it is negated ("don't stop mk agent"). Off beats on if a message has
both. If Tantra was not on, an off phrase does nothing and prints nothing.

Tantra ignores the wake word inside text you pasted in, fenced code blocks
(LF or CRLF line endings), `inline code` and `>` quoted lines. Pasting a document that happens to say
"MK agent" does not switch it on.

While Tantra is off, Claude Code will not dispatch Tantra's own agents, from
the main session or from a non-Tantra subagent such as general-purpose. If
one gets called anyway, the hook refuses it and says the wake word is needed.
Dispatches a running Tantra agent makes to its own sub-agents are not
gated. Other agents (Explore, general-purpose, your own, another plugin's
`other:seo-agent`) are never blocked. If `~/.tantra` can't be written, the
wake word can't be recorded, so the gate lets Tantra agents through rather
than refuse them.

**Known false positive.** The first-word rule accepts "MK" in any case, so a
message that starts with the abbreviation in another sense, like
"MK Dons won again", switches Tantra on. Send `mk off` if that happens.

**Unattended and scheduled runs** (cron, scheduled tasks, headless
`claude -p`) can't type a wake word. Set the environment variable
`TANTRA_ACTIVE=1` for those runs and Tantra starts active:

```bash
TANTRA_ACTIVE=1 claude -p "run the weekly competitor monitor"
```

```powershell
$env:TANTRA_ACTIVE = "1"; claude -p "run the weekly competitor monitor"
```

Starting the scheduled prompt with `mk` works too.

Optional settings live in `~/.tantra/config.json`, under the `"activation"` section:

```json
{ "activation": { "remind_each_prompt": true, "hard_gate": true } }
```

`remind_each_prompt` adds one short line to each prompt while Tantra is on.
`hard_gate` controls the refusal of Tantra agents while Tantra is off.

## Installing the hooks

Tantra's wake word, sentinels and guards run as Claude Code hooks. There are
two scopes, because each hook starts a Python process:

- **User scope** (`~/.claude/settings.json`) covers every project on the
  machine. It only hooks cheap or rare events: your prompts, agent
  dispatches, Tantra agents starting and stopping, and session
  resume/compact.
- **Workspace scope** (`<workspace>/.claude/settings.local.json`) covers
  one client workspace. It adds the heavier watchers: reads, web fetches,
  searches, skills, edits and MCP calls.

Run these from the Tantra repo:

```bash
# once per machine
python tools/install_hooks.py user

# once per client workspace
python tools/install_hooks.py workspace ~/clients/acme

# preview first: prints the change, writes nothing
python tools/install_hooks.py user --dry-run

# check what is installed, missing or outdated
python tools/install_hooks.py status
python tools/install_hooks.py status --workspace ~/clients/acme
```

The installer:

- keeps every other setting and every other hook in the file. It only
  replaces its own entries, which it recognises by `tantra_hook.py` in the
  arguments.
- is safe to re-run. A second run changes nothing, and running it again is
  also how you repair a drifted install.
- saves the previous file as `settings.json.tantra.bak` before the first
  change it ever makes, and writes atomically.
- refuses to touch a settings file that isn't valid JSON or isn't UTF-8
  (Windows PowerShell 5.1's `>` writes UTF-16), and leaves it exactly as it
  was.
- leaves the file byte-for-byte alone when nothing would change, including
  an uninstall with no Tantra handlers to remove.
- writes through a symlinked `settings.json` (a dotfiles repo) instead of
  replacing the link.
- uses the Python you run it with, by absolute path. Pass
  `--python C:\Python314\python.exe` to pick a different one.
  `--settings PATH` edits a different settings file.

Re-run `python tools/install_hooks.py user` after any of these:

- you add, rename or remove an agent. Regenerate the agent registry first
  with `python tools/build_tantra_registry.py`. The installer refuses to
  continue while the registry is stale. Adding a knowledge-base file does
  not make it stale.
- you move the repo.
- you change Python versions.

Restart open Claude Code sessions afterwards, or check `/hooks`.

### Uninstalling

```bash
python tools/install_hooks.py user --uninstall
python tools/install_hooks.py workspace ~/clients/acme --uninstall
```

This removes only Tantra's handlers. Other hooks and settings stay. Event
lists that held only Tantra entries are removed too.

### Checking the install

`python tools/check_install.py` now has a **Hooks** section. Each user-scope
handler is reported as:

- `OK`: installed and current.
- `MISSING`: not installed.
- `WRONG`: it points at another clone of the repo, or at a Python that no
  longer exists.
- `STALE`: the options or the agent list are out of date.

The section also checks that the agent registry is fresh. Each problem line
names the command that fixes it.

## Sentinels: the watcher bots

Tantra runs seven small watcher bots inside its Claude Code hooks. They follow the orchestrators, domain agents, sub-agents and skills step by step. The goal is to stop the OS from repeating work it already did, re-reading history it already has, or waiting on a step that has stalled. They are plain Python rules. They never call a model, and they only act while Tantra is active (after you say "MK agent" / "mk").

| id | Name | What it watches | What it does | Default mode | Config keys (`~/.tantra/config.json`) |
|---|---|---|---|---|---|
| `scribe` | Tantra Scribe | Every Tantra dispatch (the parent's Agent call, the subagent's start/stop, the Agent result), SubagentHandback reports, compaction/resume, end of turn | Keeps the step ledger. When a dispatch **re-runs** an earlier one it injects a **Run Brief**: the earlier final answer (head and tail) so the new run picks up where the last one stopped. A re-run is recognised only by an identical prompt or the orchestrators' `redispatch` marker (`{"cycle_id": ...}`); a new task for the same agent type, or a parallel fan-out of it, gets no brief. In auto mode (Claude Code v2.1.271+) the report a subagent hands back through SubagentHandback is what gets saved, not its closing text. Adds a note when an agent sits at spawn depth 3, where the Agent tool is withheld. After compaction or resume it injects a short session-state brief covering dispatches, pending approval gates, the last checkpoint and saved outputs. At the end of each turn in a client workspace it appends one summary line to `memory/sentinel_runs.jsonl`. | assist | `mode`, `brief_chars` (3500), `output_cap` (20000), `depth_limit` (3), `compaction_brief_chars` (3000), `launch_window_s` (120) |
| `pulse` | Tantra Pulse | A dispatched Tantra agent that stops producing activity | Runs as a background watchdog for each dispatch. When the child's transcript, and those of any agents it dispatched, go quiet for too long, or the whole run exceeds its time limit, it wakes the main thread with a stall report: which dispatch, how long, the last tool it used, completed tool calls, and Tantra's stall protocol (re-dispatch only the unfinished part, synchronously). A child in the middle of one long tool call (a foreground dispatch, a slow Bash or MCP call) is not called idle; only the time limit applies. With several dispatches of the same agent type in flight, each watchdog follows the child Claude Code reports for its own call as soon as that is known. | assist | `mode`, `poll_s` (30), `idle_min` {sub 6, domain 10, entry/bridge 15}, `max_min` {sub 20, domain 35, entry/bridge 55} |
| `echo` | Tantra Echo | Read / WebFetch / Grep / Glob calls, and Agent dispatches | The first repeat of an identical call in the same agent gets a factual note. Once a call has run `deny_after` times with the file unchanged, the next repeat is denied, with a hint to use a narrower offset/limit. Earlier Grep/Glob results stop counting after any Write/Edit, Bash, PowerShell or MCP call (any of them can change files), and every earlier result stops counting after a compaction of that agent or the main thread. Fetching a URL another agent already fetched gets a note naming that agent, plus any evidence file that holds the URL. Re-dispatching an identical prompt that already completed gets a note pointing at the saved output. | enforce | `mode`, `deny_after` (2) |
| `lens` | Tantra Lens | Full reads of large knowledge bases and raw state logs | Denies a whole-file Read of a `knowledge-bases/*.md` over 12k chars and returns the exact `kb_slice.py outline / search / section` commands. Denies a whole-file Read of `memory/checkpoints|outcomes|redispatch_log.jsonl` (or the session step ledger) over 20k chars and returns the `context_budget.py --kind …` digest command. Reads with a limit of 400 lines or fewer always pass. | enforce | `mode`, `kb_max_chars`, `state_max_chars`, `full_read_limit` |
| `contract` | Tantra Contract | The final answer of every domain agent and sub-agent | When CONFIDENCE / CITATION_CHECK / GAPS are missing, or the answer is under 200 chars, it keeps the agent running for one more turn and asks it to add only the missing lines. The analysis is not redone. This happens at most once per agent. Entry orchestrators and the bridge are never blocked. A report handed back through SubagentHandback counts as the answer. | enforce | `mode`, `max_blocks_per_agent` (1), `min_chars` (200), `fallback_fields` |
| `meter` | Tantra Meter | Tokens and time used by every Tantra dispatch | Reads the subagent's own transcript, with duplicate message ids removed, and records its tokens and duration. When a dispatch goes over its tier budget, the parent gets a note that names the three heaviest tool results. When the session passes 400k output tokens, you see a warning, repeated once per extra 100k. | assist | `mode`, `output_budget` {sub 20k, domain 50k, entry/bridge 100k}, `duration_min` {sub 15, domain 30, entry/bridge 50}, `session_output_budget`, `session_step` |
| `boundary` | Tantra Boundary | A Tantra agent dispatching another Tantra agent outside its registered children | Adds a note naming the target's registered parent (the chain of command). In `enforce` mode it denies the dispatch instead. | assist | `mode` |

**Modes.** Every bot has one of `off`, `observe` (log only; nothing reaches the model), `assist` (factual notes only; a deny/block becomes a note) or `enforce` (may deny a tool call or keep a subagent running).

### Tuning `~/.tantra/config.json`
Each bot reads its own section. Any key you leave out keeps its default.
```json
{
  "echo":     {"mode": "assist", "deny_after": 3},
  "lens":     {"kb_max_chars": 20000},
  "pulse":    {"idle_min": {"sub": 8, "domain": 12}, "poll_s": 20},
  "meter":    {"session_output_budget": 600000},
  "boundary": {"mode": "enforce"},
  "contract": {"mode": "observe"}
}
```
A threshold can be one number, which applies to every tier, or a per-tier map.

### Reading the report
```
python .claude/lib/sentinel_report.py report                    # most recent session
python .claude/lib/sentinel_report.py report --all --json-out sentinels.json
python .claude/lib/sentinel_report.py report --workspace <client workspace>
python .claude/lib/sentinel_report.py prune --older-than-days 30 [--dry-run]
```
For each session the report shows:
- dispatches by tier and by agent, and duration p50/p90/max;
- output tokens by agent;
- stalls, Run Briefs injected, echo notes and denials, lens denials, contract fixes and boundary notes;
- actions that were only observed and not applied;
- the heaviest dispatches;
- **estimated tokens avoided**.

Related tools:
- `context_budget.py <state dir>/dispatch.jsonl --kind steps` digests a session's step ledger.
- `observability_report.py` computes real timing and token rollups whenever `memory/sentinel_runs.jsonl` exists. Without that file, those metrics are still listed as not computable.
- `trigger_registry.py` has three new condition kinds: `stalled_dispatch`, `repeated_read_loop` and `token_hotspot`. For example: `trigger_registry.py memory/triggers.jsonl register --trigger-id stalls --kind condition --condition-kind stalled_dispatch --target "surface to user" --description "Dispatches that stalled"`. The documented `check --workspace-root` flag now works.

### Honest limits
- Hooks only fire at events (a tool call, a subagent start or stop, the end of a turn). Nothing can interrupt a model in the middle of generating. The bots act at the next event.
- Pulse wakes the main thread reliably. If the parent is itself blocked inside a foreground dispatch, it sees the report only when control returns to it.
- Every "tokens avoided" figure is an **estimate**: chars/4 for reads that were denied, and the recorded usage for re-dispatches that were avoided. Notes the model is free to ignore are logged with 0.
- Token usage comes from Claude Code's transcript files. If the transcript format changes, meter and pulse fall back to durations and ledger timestamps.
- Each bot's text is capped at about 2,500 chars (a Run Brief at about 4,300), so a bot can never flood the context.
- Echo cannot see a file changed outside Claude Code (by you, in an editor) between two identical Grep/Glob calls. Read is safe, because it is keyed on the file's own mtime and size.
- The sentinels' ledgers are append-only JSONL written by many hook processes at once; each append holds a lock, so lines are never lost or torn by a concurrent writer.
