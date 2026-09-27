# Version Manifest Changelog

## 1.0.0 — 2026-09-06

Initial build. Closes the "prompt/model/context/tool/workflow version
stamping" gap identified against the OS blueprint (`Marketing OS.md` §13):
full execution traceability, computed rather than hand-maintained.

- New: `.claude/lib/version_manifest.py` — `snapshot` (baseline), `check-drift`
  (read-only diff), `resolve <agent-id>` (the full 5-dimension stamp).
- Content-hash based versioning for prompts (237 agents), tools (27
  scripts across `.claude/lib/` and `marketing-os-infra/lib/`), and
  workflows (4). Context version reuses the already-published
  `taxonomy_version` / `data_model_version` / `model_routing_version`
  registries (gaps #1/#2/#4) plus each knowledge base's real
  `**Last reviewed:**` date. Model version reads `model-routing/model_routing.json`.
- `data_model_registry.py`'s `DispatchContract` (gap #2) extended with an
  optional `versions` field to hold a `resolve` stamp.
- **Real bug found and fixed during verification**: the initial byte-level
  hash registered false "drift" from git's own CRLF/LF line-ending
  normalization on this Windows repo, even when `git status` reported the
  file clean. Fixed by hashing universal-newline-normalized text instead
  of raw bytes — verified both that a real content edit is still caught
  and that the false positive is gone.
- Not yet wired into any of the 5 orchestrators' actual Step 5 dispatch
  logic — a named, separate follow-on, same precedent as gaps #1 and #4's
  deferred wiring steps.
