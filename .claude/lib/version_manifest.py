"""
version_manifest.py
=====================
The OS blueprint's Section 13 promise: "Every important AI execution
should be traceable to prompt version, model version, context version,
tool version and workflow version." Real, computed versions for all five
dimensions -- not a version NUMBER invented and hand-maintained (which
goes stale the moment someone edits a file and forgets to bump it), but a
content HASH computed at snapshot time, which cannot go stale by
construction: if the file changed, the hash changed, full stop.

How each of the five dimensions is actually resolved:

  - PROMPT version  -> SHA-256 of the agent's whole .md file (frontmatter
    + body). Every one of the 237 files in .claude/agents/ gets one.
  - MODEL version    -> read directly from model-routing/model_routing.json
    (gap #4): the agent's explicit override, or "inherit" if none. The
    ACTUAL model a specific dispatch ran on when "inherit" applies is
    something only the calling orchestrator (itself the running session)
    can know -- this script can't observe that from outside, and says so
    rather than guessing.
  - CONTEXT version  -> the already-published version fields from the
    three registries built in prior gaps (taxonomy_version, data_model_
    version, model_routing_version) plus each knowledge-bases/*.md file's
    real "Last reviewed: YYYY-MM-DD" freshness date (already written by a
    human) AND a content hash (the precise machine-checkable version,
    since the human-written date isn't guaranteed bumped on every edit).
  - TOOL version     -> SHA-256 of each real connector module in
    marketing-os-infra/lib/ and each script in .claude/lib/ itself.
  - WORKFLOW version -> SHA-256 of each workflows/*/orchestration.md file.

Two real commands, same pattern as taxonomy_registry.py:
    python version_manifest.py snapshot                    # compute + write version-manifest/manifest.json (the baseline)
    python version_manifest.py check-drift                  # recompute now, diff against the stored baseline, report what changed
    python version_manifest.py resolve <agent_id>            # the full 5-dimension stamp for one agent, ready to drop into
                                                              # a dispatch contract's new optional `versions` field
                                                              # (data_model_registry.py's DispatchContract, gap #2)
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
KB_DIR = REPO_ROOT / "knowledge-bases"
LIB_DIRS = [REPO_ROOT / ".claude" / "lib", REPO_ROOT / "marketing-os-infra" / "lib"]
WORKFLOWS_DIR = REPO_ROOT / "workflows"
OUT_DIR = REPO_ROOT / "version-manifest"
MANIFEST_JSON = OUT_DIR / "manifest.json"
MODEL_ROUTING_JSON = REPO_ROOT / "model-routing" / "model_routing.json"
TAXONOMY_JSON = REPO_ROOT / "taxonomy" / "marketing_taxonomy.json"
DATA_MODEL_JSON = REPO_ROOT / "data-model" / "core_data_model.json"

VERSION = "1.0.0"
LAST_REVIEWED_RE = re.compile(r"\*\*Last reviewed:\*\*\s*([\d-]+)")


def content_hash(path: Path) -> str:
    """Hash the file's CONTENT, not its exact bytes -- normalize CRLF/LF first. Without this,
    a git checkout's line-ending normalization on Windows (autocrlf) registers as spurious
    "drift" even when git itself considers the file unchanged (confirmed while testing this
    script: `git status` reported clean, but a raw byte hash still differed)."""
    text = path.read_text(encoding="utf-8", newline=None)  # universal newlines -> all \n
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _compute() -> dict:
    prompt_versions = {f.stem: content_hash(f) for f in sorted(AGENTS_DIR.glob("*.md"))}

    kb_versions = {}
    for f in sorted(KB_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = LAST_REVIEWED_RE.search(text)
        kb_versions[f.stem] = {
            "content_hash": content_hash(f),
            "last_reviewed": m.group(1) if m else None,
        }

    tool_versions = {}
    for lib_dir in LIB_DIRS:
        if not lib_dir.exists():
            continue
        for f in sorted(lib_dir.glob("*.py")):
            tool_versions[f"{lib_dir.parent.name}/{lib_dir.name}/{f.name}"] = content_hash(f)

    workflow_versions = {}
    for f in sorted(WORKFLOWS_DIR.glob("*/orchestration.md")):
        workflow_versions[f.parent.name] = content_hash(f)

    registry_versions = {}
    for label, path, key in [("taxonomy", TAXONOMY_JSON, "taxonomy_version"),
                              ("data_model", DATA_MODEL_JSON, "data_model_version"),
                              ("model_routing", MODEL_ROUTING_JSON, "model_routing_version")]:
        if path.exists():
            registry_versions[label] = json.loads(path.read_text(encoding="utf-8")).get(key)
        else:
            registry_versions[label] = None

    manifest = {
        "manifest_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"prompts": len(prompt_versions), "knowledge_bases": len(kb_versions),
                   "tools": len(tool_versions), "workflows": len(workflow_versions)},
        "registry_versions": registry_versions,
        "prompt_versions": prompt_versions,
        "kb_versions": kb_versions,
        "tool_versions": tool_versions,
        "workflow_versions": workflow_versions,
    }
    return manifest


def snapshot() -> dict:
    manifest = _compute()
    OUT_DIR.mkdir(exist_ok=True)
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {MANIFEST_JSON} -- {manifest['counts']}")
    return manifest


def load_manifest() -> dict:
    if not MANIFEST_JSON.exists():
        print("No manifest yet. Run: python version_manifest.py snapshot")
        sys.exit(1)
    return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))


def check_drift() -> int:
    """Read-only: compares the CURRENT computed state against the stored manifest.json
    baseline, without overwriting it. Run `snapshot` explicitly to accept a new baseline."""
    baseline = load_manifest()
    current = _compute()
    changes = {"prompts": [], "knowledge_bases": [], "tools": [], "workflows": [], "registries": []}

    for agent_id, h in current["prompt_versions"].items():
        old = baseline["prompt_versions"].get(agent_id)
        if old is None:
            changes["prompts"].append(f"{agent_id}: NEW (no prior hash)")
        elif old != h:
            changes["prompts"].append(f"{agent_id}: {old} -> {h}")
    for agent_id in baseline["prompt_versions"]:
        if agent_id not in current["prompt_versions"]:
            changes["prompts"].append(f"{agent_id}: REMOVED")

    for kb_id, info in current["kb_versions"].items():
        old = baseline["kb_versions"].get(kb_id, {})
        if old.get("content_hash") != info["content_hash"]:
            changes["knowledge_bases"].append(f"{kb_id}: {old.get('content_hash')} -> {info['content_hash']}")

    for tool_id, h in current["tool_versions"].items():
        old = baseline["tool_versions"].get(tool_id)
        if old != h:
            changes["tools"].append(f"{tool_id}: {old} -> {h}")

    for wf_id, h in current["workflow_versions"].items():
        old = baseline["workflow_versions"].get(wf_id)
        if old != h:
            changes["workflows"].append(f"{wf_id}: {old} -> {h}")

    for label, v in current["registry_versions"].items():
        old = baseline["registry_versions"].get(label)
        if old != v:
            changes["registries"].append(f"{label}: {old} -> {v}")

    total = sum(len(v) for v in changes.values())
    if total == 0:
        print("No drift -- everything matches the last snapshot.")
        return 0
    print(f"DRIFT DETECTED -- {total} change(s) since last snapshot:")
    for category, items in changes.items():
        for item in items:
            print(f"  [{category}] {item}")
    return 1


def resolve(agent_id: str) -> dict:
    manifest = load_manifest()
    prompt_hash = manifest["prompt_versions"].get(agent_id)
    if prompt_hash is None:
        print(f"No such agent in the manifest: {agent_id}")
        sys.exit(1)

    model_entry = {"resolution": "inherit (parent session's model)", "override": None}
    if MODEL_ROUTING_JSON.exists():
        routing = json.loads(MODEL_ROUTING_JSON.read_text(encoding="utf-8"))
        override = routing["overrides"].get(agent_id)
        if override:
            model_entry = {"resolution": f"explicit override: {override['model']}", "override": override["model"]}

    stamp = {
        "agent_id": agent_id,
        "prompt_version": prompt_hash,
        "model": model_entry,
        "context_versions": {
            "taxonomy": manifest["registry_versions"].get("taxonomy"),
            "data_model": manifest["registry_versions"].get("data_model"),
            "model_routing": manifest["registry_versions"].get("model_routing"),
            "knowledge_bases": manifest["kb_versions"],
        },
        "tool_versions": manifest["tool_versions"],
        "workflow_versions": manifest["workflow_versions"],
        "manifest_generated_at": manifest["generated_at"],
        "note": ("Drop this under a dispatch contract's optional `versions` field "
                 "(DispatchContract, data-model/core_data_model.json) to make one execution "
                 "fully traceable. The orchestrator must fill in model.resolution's actual "
                 "resolved model itself when 'inherit' applies -- this script cannot observe "
                 "that from outside the running session."),
    }
    return stamp


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "snapshot":
        snapshot()
    elif cmd == "check-drift":
        sys.exit(check_drift())
    elif cmd == "resolve":
        print(json.dumps(resolve(sys.argv[2]), indent=2, sort_keys=True))
    else:
        print(__doc__)
        sys.exit(1)
