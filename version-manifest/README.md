# Version Manifest

The OS blueprint's Section 13 promise made real: *"Every important AI
execution should be traceable to prompt version, model version, context
version, tool version and workflow version."* `.claude/lib/version_manifest.py`
resolves all five dimensions for any agent, computed — not hand-maintained.

## Why content hashes, not hand-bumped version numbers

A human-maintained `prompt_version: 1.3` field in an agent's frontmatter
goes stale the moment someone edits the file and forgets to bump it — and
nobody notices until a downstream audit needs it. A SHA-256 content hash
can't go stale by construction: if the file's content changed, the hash
changed, full stop. So:

- **Prompt version** — hash of every `.claude/agents/*.md` file (237 of them).
- **Tool version** — hash of every script in `.claude/lib/` and
  `marketing-os-infra/lib/` (27 of them).
- **Workflow version** — hash of every `workflows/*/orchestration.md` (4).
- **Context version** — the already-published version fields from the
  three registries built in prior gaps (`taxonomy_version`,
  `data_model_version`, `model_routing_version`) **plus** each
  `knowledge-bases/*.md` file's real, human-written `**Last reviewed:**`
  date (where present) **and** a content hash — both together, since the
  human-written date isn't guaranteed to be bumped on every single edit.
- **Model version** — read from `model-routing/model_routing.json`
  (gap #4): the agent's explicit override, or `"inherit"` if none. This
  script cannot observe which model a live dispatch actually ran on when
  `"inherit"` applies — only the orchestrator (itself the running session)
  knows that — and says so plainly rather than guessing.

## A real bug this caught during its own build

The first version of `content_hash()` hashed raw bytes. Testing it against
a real file revealed that `git checkout` on this Windows repo (autocrlf
line-ending normalization) can change a file's on-disk bytes in a way
`git status` reports as **clean** — no diff against HEAD — while a raw
byte hash still registered "drift." That's a false positive that would
have made this tool cry wolf on ordinary git operations, undermining trust
in every real alert it raises. Fixed by hashing **universal-newline-
normalized** text instead of raw bytes — confirmed afterward: a real
content edit still gets caught, and reverting it now correctly returns to
"no drift," matching what `git status` itself reports.

## Using it

```bash
python .claude/lib/version_manifest.py snapshot                 # compute + write version-manifest/manifest.json (the baseline)
python .claude/lib/version_manifest.py check-drift               # read-only: diff current state against the stored baseline
python .claude/lib/version_manifest.py resolve <agent-id>          # the full 5-dimension stamp for one agent
```

`check-drift` is read-only by design — it never overwrites the baseline as
a side effect of checking. Run `snapshot` explicitly whenever you want to
accept the current state as the new baseline (e.g. after a deliberate
prompt/KB/tool/workflow edit, right before running evals against it — the
blueprint's own "test agents before changing prompts... models, tools or
workflows" discipline, §17, made mechanical instead of relying on memory).

## Wiring into a real dispatch

`resolve <agent-id>`'s output is shaped to drop directly into a dispatch
contract's `versions` field — added to `DispatchContract` in
`.claude/lib/data_model_registry.py` (gap #2) as of this pass. An
orchestrator building a Step 5 dispatch contract can call `resolve` for
the agent it's about to dispatch, fill in the actual resolved model when
the result says `"inherit"`, and store the whole stamp verbatim in that
contract — the same way a checkpoint's `contracts` array already persists
every other field of that contract verbatim.

**Not yet done, and kept separate for review:** actually editing the 5
orchestrators' `.md` files to call `resolve` and populate `versions` on
every real dispatch. This pass builds and verifies the mechanism; wiring
it into the orchestrators' own Step 5 instructions is the natural next
step, same precedent as gap #1's deferred taxonomy-search wiring and gap
#4's deferred tool-usage-ledger wiring.

## Versioning

`manifest.json` carries its own `manifest_version` (currently `1.0.0`) —
this refers to the SHAPE of the manifest file itself (what fields it has),
not the per-agent/per-file hashes inside it, which change on every
`snapshot` by design.
