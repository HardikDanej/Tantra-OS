Synthetic test fixtures for `data_model_registry.py validate` — not real
business data, not a real client's dispatch history. They exist only to
prove the validator actually rejects a malformed record instead of
accepting anything handed to it.

- `task.example.jsonl` — two well-formed `DispatchContract` lines (one
  diagnostic, one strategic), should validate 2/2 clean.
- `task.example.bad.jsonl` — two deliberately broken lines (missing
  `dispatch_kind`, invalid `dispatch_kind` value), should fail both.

Run:
```bash
python .claude/lib/data_model_registry.py validate task data-model/examples/task.example.jsonl
python .claude/lib/data_model_registry.py validate task data-model/examples/task.example.bad.jsonl
```
