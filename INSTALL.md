# Install

Two locations decide whether Claude Code can see any of this. Get the location right and there's nothing else to install. No build step. No dependencies. It's markdown in a folder.

## The two scopes

**Project-level.** A `.claude/` folder inside one specific project. Only that project sees it.

**User-level.** `~/.claude/` on the machine. Every project on that machine sees it.

You want user-level. This is meant to follow you across projects, not live inside one of them.

## First device

```bash
git clone https://github.com/HardikDanej/Tantra-OS.git ~/Tantra
mkdir -p ~/.claude/skills ~/.claude/agents
ln -s ~/Tantra/.claude/skills/* ~/.claude/skills/
ln -s ~/Tantra/.claude/agents/* ~/.claude/agents/
```

Symlink, not copy. A copy goes stale the next time something in the repo changes. A symlink stays current the moment you pull.

On Windows, symlinks need either admin rights or Developer Mode turned on. If neither is available, copy the folders instead and re-copy after every pull — worse, but it works:

```powershell
git clone https://github.com/HardikDanej/Tantra-OS.git $HOME\Tantra
New-Item -ItemType Directory -Force -Path "$HOME\.claude\agents", "$HOME\.claude\skills" | Out-Null
Copy-Item "$HOME\Tantra\.claude\agents\*.md" "$HOME\.claude\agents\" -Force
Copy-Item "$HOME\Tantra\.claude\skills\*" "$HOME\.claude\skills\" -Recurse -Force
```

This is the actually-verified path on a real device without admin/Developer Mode — `tools/check_install.py` reports every agent and skill `COPY` (not `MISSING`) after running this, which is the expected, working state for this fallback, not a degraded one to fix.

### Then install the hooks (once per machine)

The wake word (`mk` / "MK agent") and the sentinels run as Claude Code hooks, not agents, so they need one more step:

```bash
python ~/Tantra/tools/install_hooks.py user --dry-run   # preview, writes nothing
python ~/Tantra/tools/install_hooks.py user
```

This merges Tantra's handlers into `~/.claude/settings.json`. It keeps every other setting and hook, saves a `.tantra.bak` backup before its first change, and is safe to re-run. Restart open Claude Code sessions afterwards. Re-run it after moving the repo, switching Python versions, or adding or renaming an agent (run `python ~/Tantra/tools/build_tantra_registry.py` first; the installer refuses while the registry is stale). `--uninstall` removes only Tantra's handlers. The full reference is in `.claude/hooks/README.md`.

Without this step the agents still load, but nothing gates them on the wake word and no sentinels run.

### Optional: the Laya fast pre-screen (once per machine)

```bash
pip install -r ~/Tantra/.claude/lib/laya_requirements.txt
```

Gives every orchestrator's HITL Approval Gate step a fast, local, calibrated-confidence cross-check (`.claude/lib/laya_screen.py`) before it classifies a plan's stakes (see the Laya line in the README's "What's underneath") The first real call downloads the model from Hugging Face (~2.7GB, several minutes) and caches it; every call after that is local, no API key, no per-call cost. Skipping this step is safe: every orchestrator classifies exactly as before, with no local model to fall back on. `python ~/Tantra/tools/check_install.py` reports whether it's importable without failing the install check either way.

## Every other device

```bash
git clone https://github.com/HardikDanej/Tantra-OS.git ~/Tantra
mkdir -p ~/.claude/skills ~/.claude/agents
ln -s ~/Tantra/.claude/skills/* ~/.claude/skills/
ln -s ~/Tantra/.claude/agents/* ~/.claude/agents/
```

Same commands (or the PowerShell copy-fallback above, on Windows without admin/Developer Mode). Every device runs the identical setup. Nothing about a second machine is special.

## Confirm it actually loaded

```bash
python ~/Tantra/tools/check_install.py
```

This checks every agent file and skill directory in this repo against `~/.claude/agents` / `~/.claude/skills` and reports each one `OK` (symlinked, live), `COPY` (the Windows fallback — works, won't auto-update), `STALE` (a copy that's fallen behind), or `MISSING`. Asking Claude Code directly ("what skills or agents are available") works too, but only tells you the agent/skill loaded *this session* — it can't tell you whether it's a live symlink or a copy that's about to go stale, which is the thing actually worth confirming. If anything comes back `MISSING`, the symlinks didn't land in the right folder, or Claude Code hasn't been restarted since they were created.

## Updating after this

```bash
cd ~/Tantra
git pull
python ~/Tantra/tools/check_install.py
```

Symlinked, that's the whole update — nothing to re-copy, nothing to reconfigure. The `check_install.py` run afterward isn't optional if you're on the Windows copy-fallback: a `COPY` from before the pull is now a `STALE` one until it's re-copied, and the script is the only thing that will actually tell you that instead of you finding out from an agent behaving like an old version of itself. Re-copy with the same two lines from the fallback above:

```powershell
Copy-Item "$HOME\Tantra\.claude\agents\*.md" "$HOME\.claude\agents\" -Force
Copy-Item "$HOME\Tantra\.claude\skills\*" "$HOME\.claude\skills\" -Recurse -Force
```

## What this does not install

The knowledge bases, the `.claude/lib/` scripts, and the workflow docs stay inside the repo, at `knowledge-bases/`, `.claude/lib/`, and `workflows/` — deliberately *not* symlinked. Agents reference them by the full path `~/Tantra/knowledge-bases/...` / `~/Tantra/.claude/lib/...` instead, which is exactly what makes symlinking them unnecessary: they never need to exist inside whatever directory you're actually working in. If the clone location changes between devices, update those paths in the agent files, or keep the clone location identical everywhere — `~/Tantra`, every time — and this problem never comes up.

`marketing-os-infra/` holds the cron scripts and API configs for the four scheduled workflows. None of that runs from a symlink. Each script needs its own Python environment and its own credentials on whichever machine actually runs the schedule, per `SETUP.md`. That's real infrastructure, not a file-copy problem, and it doesn't need to exist on every device — only the one running the cron jobs.

## Setting up a company workspace

The four commands above install the framework once, globally. They don't create anywhere to actually do client work — that's a separate, ordinary directory, one per company:

```bash
mkdir -p ~/clients/acme-co
python ~/Tantra/tools/new_workspace.py ~/clients/acme-co --name "Acme Co"
cd ~/clients/acme-co
claude
```

The symlinks above already put every agent and skill in scope for any directory on the machine; the only `.claude/` a workspace gets is `.claude/settings.local.json`, which `new_workspace.py` writes by running `tools/install_hooks.py workspace <dir>` to add the per-workspace sentinels (Echo, Lens, the connector guard, the deliverable seal). Pass `--no-hooks` to skip that. `new_workspace.py` also creates `brand/`, `memory/` (with an empty `memory/mcp_connections.jsonl` connector ledger), `deliverables/`, and `.memory/` (the last one starts empty — `.claude/lib/sync_workspace_state.py` fills it in over time as the Orchestrator's synthesis passes actually discover something durable), writes `brand/company.json` (the file that tells the Orchestrator which company this workspace is without asking), and renders a project-root `CLAUDE.md` from `tools/templates/CLAUDE.md.template`. That last one matters even if nothing else did: Claude Code auto-loads a project's `CLAUDE.md` the instant a session opens there, so it's what makes "once the user says `mk`, route through exactly one orchestrator, never straight to a domain agent" a standing fact about this directory from the very first message, not something restated every session — and it's where this company's own boundaries go as they come up (a competitor never named, a spend ceiling, a claim needing legal review). It's written once and left alone after — edit it by hand, the script never overwrites it unless you pass `--refresh-claude-md`, which backs the old one up first. Workspaces created before the wake word existed need that refresh (or the hooks' hard gate will simply refuse un-woken dispatches there). Skip the explicit `new_workspace.py` call if you'd rather let the Orchestrator do it on first contact — it runs the same script itself once it has a real company name, per its own Workspace Identity rules — but running it up front means the very first request never has to ask, and gives you `CLAUDE.md` to add real boundaries to before that first request happens.

**Actually a workspace, not the framework repo with a `.claude/` accidentally copied into it:** `python ~/Tantra/tools/check_install.py ~/clients/acme-co` — confirms this specific directory has no local `.claude/agents`/`.claude/skills` shadowing the global ones (the one way a workspace stops seeing framework updates without any error telling you so), and that `brand/company.json`, `CLAUDE.md`, `memory/`, and `.memory/` are actually there. `new_workspace.py` already warns at creation time if it finds a shadow, but this is the thing to run any time a workspace starts behaving like it's stuck on an old skill or agent.

A second company is a second directory: `mkdir -p ~/clients/other-co && python ~/Tantra/tools/new_workspace.py ~/clients/other-co --name "Other Co"`. Nothing in one workspace's `brand/`, `memory/`, `.memory/`, or `CLAUDE.md` is visible from another — that isolation is the entire point.

## Connecting apps via MCP (approval required)

Inside a workspace, say `mk connect HubSpot` (or Salesforce, NetSuite, Notion, …). The `tantra-connect` skill looks up the vendor's official MCP server, defaults to read-only tools, shows an approval card, and opens an approval gate bound to that exact configuration. After your explicit yes, **you** run the `claude mcp add …` command it prints (local scope: this workspace only, stored in `~/.claude.json`, never committed) and sign in with `/mcp` for OAuth apps. Secrets go in environment variables or OAuth, never in chat. The connection is recorded in `memory/mcp_connections.jsonl`, and the workspace hooks block Tantra sub-agents from any unapproved server and block write tools that lack their own write approval. `mk revoke <app>` undoes it. Full reference: `connectors/README.md`.

## Tantra Seal (owner only, once per machine that signs)

Signing needs the `cryptography` and `c2pa-python` packages, and your normal `python` (not `-I -S`):

```bash
python ~/Tantra/.claude/lib/provenance.py init --name "Hardik Danej" --export-public ~/Tantra/provenance/public
python ~/Tantra/.claude/lib/provenance.py seal-frontmatter
python ~/Tantra/.claude/lib/provenance.py sign-os
python ~/Tantra/.claude/lib/provenance.py fingerprint register-os
```

Keys live in `~/.tantra/keys`, never in the repo; back that folder up offline, because losing it means new signatures can't be linked to old ones. Set `TANTRA_KEY_PASSPHRASE` before `init` if you want the private keys encrypted. Re-run `seal-frontmatter` and `sign-os` after changing agents or skills. After that, anything the OS writes into a workspace's `deliverables/` folder is signed automatically; check it with `python ~/Tantra/.claude/lib/provenance.py verify-file <path>`. What each layer does and doesn't prove is in `provenance/README.md`.
