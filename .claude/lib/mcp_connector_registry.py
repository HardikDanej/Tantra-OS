r"""
mcp_connector_registry.py
=========================
The per-workspace record of which MCP servers (CRMs, ERPs, analytics, docs,
any app that ships an MCP server) Tantra is allowed to use, and with exactly
which tools.

Why this exists: Claude Code will happily run any MCP server it is configured
with, and many vendor servers expose write tools (update a deal, post an
invoice) under the same OAuth grant as their read tools. Tantra's rule is
"agents diagnose, humans execute", and the owner's rule is "nothing connects
without my explicit yes". So a connection here is a three-step, human-attested
lifecycle, and each step is an append-only line in
`<workspace>/memory/mcp_connections.jsonl`:

  proposed   the exact spec (transport, URL or pinned package, scope, the
             resolved workspace directory, env var NAMES, the read-tool and
             write-tool allowlists) plus its config_hash and a gate id unique to
             this proposal. `propose` validates the spec and prints the approval
             card and the approval_gate.py command that opens that gate BOUND to
             the hash.
  connected  recorded only for the gate opened for the current proposal, when
             it is approved AND its binding is still this spec's config_hash
             (approval_gate.binding_matches). A revoked or earlier approval, or
             one from another workspace, never carries over. The user runs
             `claude mcp add` themselves; this script only prints it.
  revoked    the connection is withdrawn; `claude mcp remove` is printed.

The last event per server wins, so proposing again (changed or not) suspends a
connected server until the new proposal's gate is approved and recorded: an
approval covers one exact configuration, never "whatever it becomes later".

The connectors_guard hook imports this module (stdlib only, no side effects
on import) and enforces the record on every `mcp__<server>__<tool>` call made
inside a Tantra workspace. A tool in neither allowlist is not approved, and
every call (read or write) re-checks that the record still hashes to its
config, belongs to this workspace, and that its bound gate is still approved.

Secrets never enter this ledger, the chat, or the printed commands: every env
and header value must be a `${VAR}` reference (a `${VAR:-default}` fallback may
only be a short plain word), stdio flags such as --api-key/--password may only
carry a `${VAR}`, and values that look like literal tokens are rejected.
`redact()` is the shared scrubber the hook uses before it logs anything.

Stdio launchers fail closed: npx/bunx/pnpm dlx/npm exec/yarn dlx/uvx/pipx
run/docker run must name a pinned version (or @sha256 digest); any other
command needs --unpinned-ok, which is hashed and shown on the card. Read tools
named like write actions (delete_*, update*, send_*, ...) are refused unless
repeated in --confirm-read-tools. Every printed value is printable ASCII with
no quote characters, so a pasted command cannot break out of its quoting in
Git Bash or PowerShell.

Usage (run from the client workspace, or pass --workspace):
    python mcp_connector_registry.py propose --server hubspot --transport http \
        --url https://mcp.example.com/mcp --scope local \
        --read-tools search_contacts,get_deal [--write-tools create_note] \
        [--header 'Authorization: Bearer ${HUBSPOT_TOKEN}'] [--env KEY=${VAR}] \
        [--catalog-id hubspot] [--notes "..."]
    python mcp_connector_registry.py propose --server files --transport stdio --scope local \
        --read-tools list_files [--env FILES_TOKEN=${FILES_TOKEN}] -- npx -y @scope/files-mcp@1.2.3
        (the stdio command line goes after a bare `--`; --command CMD --arg=A ... also works)
    python mcp_connector_registry.py connect-command --server hubspot
    python mcp_connector_registry.py record-connect --server hubspot --gate-id mcp_hubspot_1a2b3c4d_5e6f70
    python mcp_connector_registry.py revoke --server hubspot [--reason "..."]
    python mcp_connector_registry.py status [--server hubspot]
    python mcp_connector_registry.py list
    python mcp_connector_registry.py check-tool --tool mcp__hubspot__search_contacts

Exit codes:
    propose:         0 proposed and card printed; 1 spec rejected (reason on stderr).
    connect-command: 0 printed; 1 server unknown or revoked.
    record-connect:  0 recorded; 1 no proposal, not the current proposal's gate,
                     gate not approved, gate bound to a different config or
                     workspace, or wrong stakes class (reason printed).
    revoke:          0 recorded; 1 server unknown or already revoked.
    status:          0; 1 if --server is unknown.
    list:            0 always.
    check-tool:      0 approved read tool; 3 approved write tool whose
                     mcp_write_connection gate is approved and bound (each write
                     action still needs the orchestrator's own action gate, e.g.
                     crm_write); 1 not approved (why is printed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import shlex
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

LEDGER_REL = os.path.join("memory", "mcp_connections.jsonl")
GATES_REL = os.path.join("memory", "approval_gates.jsonl")
LATEST_REL = os.path.join("memory", "latest.json")
DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "connectors" / "mcp_catalog.json"
CATALOG_MAX_AGE_DAYS = 60

TRANSPORTS = ("http", "sse", "stdio", "claudeai")
SCOPES = ("local", "project", "user")
READ_CLASS = "mcp_connection"
WRITE_CLASS = "mcp_write_connection"

SERVER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
TOOL_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HEADER_KEY_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
VAR_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
AUTH_SCHEMES = {"", "bearer", "basic", "token", "apikey", "api-key"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
SECRET_QUERY_KEYS = re.compile(
    r"(?i)([?&;](?:access_token|api[_-]?key|apikey|key|token|secret|client_secret|password|pass|sig|signature|auth)=)([^&#\s]+)")
KNOWN_TOKEN_RE = re.compile(
    r"(?:\bsk-[A-Za-z0-9_\-]{20,}|\bsk_(?:live|test)_[A-Za-z0-9]{8,}|\bxox[abprs]-[A-Za-z0-9\-]{8,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{16,}|\bgithub_pat_[A-Za-z0-9_]{16,}|\bglpat-[A-Za-z0-9_\-]{12,}"
    r"|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_\-]{20,}|\bpat-[a-z0-9]{2,4}-[0-9a-f\-]{20,}"
    r"|\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,})")
BEARER_LITERAL_RE = re.compile(r"(?i)\b(bearer|basic|token)\s+(?!\$\{)([^\s\"',;]{8,})")
CANDIDATE_RE = re.compile(r"[A-Za-z0-9_\-+/=]{24,}")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
PINNED_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.\-]+)?$")
HEX_RUN_RE = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])")
SECRET_FLAG_NAMES = (r"api[-_]?key|apikey|access[-_]?token|auth[-_]?token|token|secret|client[-_]?secret"
                     r"|password|passwd|pass|auth|credentials?")
SECRET_FLAG_RE = re.compile(rf"(?i)^--?(?:{SECRET_FLAG_NAMES})(?:=(.*))?$")
SECRET_FLAG_TEXT_RE = re.compile(rf"(?i)((?<![\w-])--?(?:{SECRET_FLAG_NAMES})[= ])(?!\$\{{)([^\s\"',;]+)")
SAFE_DEFAULT_RE = re.compile(r"^[A-Za-z0-9._\-]{0,40}$")
MIXED_RUN_RE = re.compile(r"[A-Za-z0-9]{16,}")
# PowerShell treats U+2018..U+201B as single quotes too, so none of them may reach a printed command.
QUOTE_CHARS = "'\u2018\u2019\u201a\u201b"
PRINTABLE_ASCII_RE = re.compile(r"^[\x20-\x7e]*$")
WRITE_VERBS_ANYWHERE = {"delete", "remove", "update", "create", "send", "write", "upsert", "patch", "archive",
                        "publish", "invite", "cancel", "refund", "insert", "drop", "destroy", "modify", "edit",
                        "execute", "exec", "purge", "revoke", "transfer", "charge", "unsubscribe", "subscribe"}
WRITE_VERBS_LEADING = {"post", "put", "set", "add", "merge", "move", "run", "mark", "assign", "submit", "save",
                       "append", "reply", "share", "upload", "import", "sync", "trigger", "enroll", "close",
                       "approve", "reject", "pay", "book", "schedule", "clear", "reset", "rename", "tag"}


class SpecError(ValueError):
    """A proposed connector spec that must not be recorded."""


# --------------------------------------------------------------------------- secrets

def _entropy(text: str) -> float:
    counts = {ch: text.count(ch) for ch in set(text)}
    return -sum((n / len(text)) * math.log2(n / len(text)) for n in counts.values())


def _is_high_entropy_token(piece: str) -> bool:
    core = piece.strip("=-_/+")
    if len(core) < 24 or UUID_RE.match(core):
        return False
    if re.fullmatch(r"[0-9a-fA-F]{32,}", core) and re.search(r"[0-9]", core) and re.search(r"[a-fA-F]", core):
        return True
    classes = sum(bool(re.search(p, core)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]"))
    return classes == 3 and len(core) >= 32 and _entropy(core) >= 4.0


def looks_like_secret(text: str) -> bool:
    """True when text contains something shaped like a literal credential."""
    if not text:
        return False
    stripped = VAR_REF_RE.sub("", text)
    if KNOWN_TOKEN_RE.search(stripped) or BEARER_LITERAL_RE.search(stripped):
        return True
    if SECRET_QUERY_KEYS.search(stripped) or SECRET_FLAG_TEXT_RE.search(stripped):
        return True
    if any(re.search(r"[0-9]", m.group(0)) and re.search(r"[a-fA-F]", m.group(0))
           for m in HEX_RUN_RE.finditer(stripped)):
        return True
    return any(_is_high_entropy_token(m.group(0)) for m in CANDIDATE_RE.finditer(stripped))


def redact(text) -> str:
    """Scrub anything credential-shaped from text before it is logged or shown."""
    if text is None:
        return ""
    out = str(text)
    out = KNOWN_TOKEN_RE.sub("[REDACTED]", out)
    out = BEARER_LITERAL_RE.sub(lambda m: f"{m.group(1)} [REDACTED]", out)
    out = SECRET_QUERY_KEYS.sub(lambda m: m.group(1) + ("[REDACTED]" if not m.group(2).startswith("${") else m.group(2)), out)
    out = SECRET_FLAG_TEXT_RE.sub(lambda m: m.group(1) + "[REDACTED]", out)
    out = HEX_RUN_RE.sub(lambda m: "[REDACTED]" if re.search(r"[0-9]", m.group(0))
                         and re.search(r"[a-fA-F]", m.group(0)) else m.group(0), out)
    return CANDIDATE_RE.sub(lambda m: "[REDACTED]" if _is_high_entropy_token(m.group(0)) else m.group(0), out)


# --------------------------------------------------------------------------- validation

def _split_csv(value: Optional[str]) -> list[str]:
    return [t.strip() for t in (value or "").split(",") if t.strip()]


def _normalize_tools(server: str, tools: list[str]) -> list[str]:
    prefix = f"mcp__{server}__"
    names = sorted({t[len(prefix):] if t.startswith(prefix) else t for t in tools})
    bad = [t for t in names if not TOOL_RE.match(t)]
    if bad:
        raise SpecError(f"invalid tool name(s): {', '.join(bad)}")
    return names


def _check_printable(label: str, value: str) -> None:
    """Printed commands are pasted into Git Bash or PowerShell: printable ASCII and no quote characters."""
    if not PRINTABLE_ASCII_RE.match(value or "") or any(ch in (value or "") for ch in QUOTE_CHARS):
        raise SpecError(f"{label} may contain printable ASCII only, and no quote characters")


def _default_is_safe(default: Optional[str]) -> bool:
    """A ${VAR:-default} fallback is shown and stored, so it may only be a short plain word, never a key."""
    if not default:
        return True
    if not SAFE_DEFAULT_RE.match(default) or looks_like_secret(default):
        return False
    return not any(re.search(r"[0-9]", m.group(0)) and re.search(r"[A-Za-z]", m.group(0))
                   for m in MIXED_RUN_RE.finditer(default))


def _check_reference_only(label: str, value: str) -> None:
    _check_printable(label, value)
    refs = VAR_REF_RE.fullmatch(value.strip())
    if not refs:
        raise SpecError(f"{label} must be a ${{VAR}} or ${{VAR:-default}} reference, never a literal value")
    if not _default_is_safe(refs.group(2)):
        raise SpecError(f"{label} has a default that looks like a literal secret -- use a bare ${{VAR}}")


def parse_env(items: list[str]) -> dict[str, str]:
    env = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not ENV_KEY_RE.match(key):
            raise SpecError(f"--env must be KEY=${{VAR}}, got {redact(item)!r}")
        _check_reference_only(f"env {key}", value)
        env[key] = value.strip()
    return env


def parse_headers(items: list[str]) -> dict[str, str]:
    headers = {}
    for item in items or []:
        key, sep, value = item.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not HEADER_KEY_RE.match(key):
            raise SpecError(f"--header must be 'Name: ${{VAR}}', got {redact(item)!r}")
        _check_printable(f"header {key}", value)
        refs = VAR_REF_RE.findall(value)
        literal = VAR_REF_RE.sub("", value).strip().lower()
        if not refs or literal not in AUTH_SCHEMES:
            raise SpecError(f"header {key} must be a ${{VAR}} reference (optionally after 'Bearer '), "
                            f"never a literal value")
        if not all(_default_is_safe(default) for _, default in refs):
            raise SpecError(f"header {key} has a default that looks like a literal secret")
        headers[key] = value
    return headers


def validate_url(url: str) -> str:
    if not url:
        raise SpecError("--url is required for http/sse transports")
    _check_printable("the URL", url)
    if looks_like_secret(url):
        raise SpecError("the URL contains something that looks like a credential -- put it in a "
                        "${VAR} header instead")
    match = re.match(r"^(https?)://([^/:?#]+|\[[^\]]+\])(?::\d+)?(?:[/?#].*)?$", url)
    if not match:
        raise SpecError(f"not a valid http(s) URL: {url}")
    scheme, host = match.group(1), match.group(2).lower()
    if scheme != "https" and host not in LOCAL_HOSTS:
        raise SpecError("remote MCP servers must use https (http is allowed only for localhost)")
    return url


CMD_SWITCH_RE = re.compile(r"(?i)^/(?:s|d|q|a|u|[efvt]:\w+)$")
DOCKER_VALUE_FLAGS = {"-e", "--env", "--env-file", "-v", "--volume", "-p", "--publish", "--name", "--network",
                      "--net", "-w", "--workdir", "-u", "--user", "--entrypoint", "--mount", "-l", "--label",
                      "--platform", "-m", "--memory", "--cpus", "--add-host", "-h", "--hostname", "--pull",
                      "--cap-add", "--cap-drop", "--device", "--dns", "--log-driver", "--restart", "--tmpfs"}


def _launcher(command: str) -> str:
    base = os.path.basename(command.replace("\\", "/")).lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        base = base.removesuffix(suffix)
    return base


def _unwrap_shell(command: str, args: list[str]) -> tuple[str, list[str]]:
    """Peel `cmd [/s /d /q] /c <command line>` (possibly nested, possibly one quoted string)."""
    for _ in range(4):
        if _launcher(command) != "cmd":
            break
        rest = list(args)
        while rest and CMD_SWITCH_RE.match(rest[0]):
            rest.pop(0)
        if len(rest) < 2 or rest[0].lower() not in ("/c", "/k"):
            break
        payload = rest[1:]
        if len(payload) == 1:
            try:
                payload = shlex.split(payload[0])
            except ValueError as exc:
                raise SpecError(f"cannot parse the cmd /c command line: {exc}") from None
            if not payload:
                break
        command, args = payload[0], payload[1:]
    return command, args


def _npm_pinned(spec: str) -> bool:
    name, _, version = spec[1:].partition("@") if spec.startswith("@") else spec.partition("@")
    return bool(name) and bool(PINNED_VERSION_RE.match(version))


def _py_pinned(spec: str) -> bool:
    for sep in ("==", "@"):
        name, found, version = spec.partition(sep)
        if found and name and PINNED_VERSION_RE.match(version.strip()):
            return True
    return False


def _docker_pinned(image: str) -> bool:
    if "@sha256:" in image:
        return True
    _, _, tag = image.rpartition("/")[2].partition(":")
    return bool(PINNED_VERSION_RE.match(tag))


def _first_package(args: list[str], value_flags: tuple[str, ...]) -> Optional[str]:
    it = iter(args)
    for arg in it:
        if arg in value_flags:
            return next(it, None)
        flag, eq, value = arg.partition("=")
        if eq and flag in value_flags:
            return value
        if not arg.startswith("-"):
            return arg
    return None


def _docker_image(args: list[str]) -> Optional[str]:
    it = iter(args)
    for arg in it:
        if arg in DOCKER_VALUE_FLAGS:
            next(it, None)
        elif not arg.startswith("-"):
            return arg
    return None


def check_package_pinned(command: str, args: list[str], unpinned_ok: bool = False) -> Optional[str]:
    """Fail closed: only launchers whose package version can be read from the command line pass.

    Anything else (a bare binary, `node server.js`, a shell) is refused unless the user
    explicitly accepts it with --unpinned-ok; the returned note then goes on the card.
    """
    command, args = _unwrap_shell(command, args)
    base = _launcher(command)
    sub = [a.lower() for a in args[:2]]
    npm_style = (base in ("npx", "bunx", "pnpx") or (base == "bun" and sub[:1] == ["x"])
                 or (base in ("pnpm", "yarn") and sub[:1] == ["dlx"]) or (base == "npm" and sub[:1] in (["exec"], ["x"])))
    if npm_style:
        rest = args if base in ("npx", "bunx", "pnpx") else args[1:]
        pkg = _first_package(rest, ("-p", "--package"))
        if not pkg or not _npm_pinned(pkg):
            raise SpecError(f"{base} package must be version-pinned (e.g. @scope/pkg@1.2.3), got {pkg!r}")
        return None
    if base == "uvx" or (base == "uv" and sub == ["tool", "run"]):
        pkg = _first_package(args if base == "uvx" else args[2:], ("--from",))
        if not pkg or not _py_pinned(pkg):
            raise SpecError(f"uvx package must be version-pinned (e.g. pkg==1.2.3), got {pkg!r}")
        return None
    if base == "pipx" and sub[:1] == ["run"]:
        pkg = _first_package(args[1:], ("--spec",))
        if not pkg or not _py_pinned(pkg):
            raise SpecError(f"pipx run package must be version-pinned (e.g. pkg==1.2.3), got {pkg!r}")
        return None
    if base in ("docker", "podman") and sub[:1] == ["run"]:
        image = _docker_image(args[1:])
        if not image or not _docker_pinned(image):
            raise SpecError(f"{base} image must be pinned to a version tag or @sha256 digest, got {image!r}")
        return None
    if not unpinned_ok:
        raise SpecError(f"cannot verify a pinned version for stdio command {base!r} -- use a version-pinned "
                        f"npx/bunx/pnpm dlx/npm exec/yarn dlx/uvx/pipx run/docker run launcher, or pass "
                        f"--unpinned-ok only if the user explicitly accepts running {base!r} unpinned")
    return (f"Runs {base!r}, whose version Tantra cannot pin: the approval covers whatever that command "
            f"runs at call time, with the user's full privileges.")


def _check_secret_flags(args: list[str]) -> None:
    for i, piece in enumerate(args):
        match = SECRET_FLAG_RE.match(piece)
        if not match:
            continue
        value = match.group(1)
        if value is None and i + 1 < len(args) and not args[i + 1].startswith("-"):
            value = args[i + 1]
        if value and not VAR_REF_RE.fullmatch(value):
            raise SpecError(f"stdio argument {piece.partition('=')[0]} carries a literal value -- pass "
                            f"credentials through --env KEY=${{VAR}} (or a ${{VAR}} argument), never inline")


def workspace_key(workspace) -> str:
    """The identity an approval is bound to: one resolved workspace directory."""
    return os.path.normcase(os.path.realpath(str(workspace)))


def build_spec(args: argparse.Namespace) -> dict:
    """Validate CLI arguments into the canonical spec that gets hashed and approved."""
    server = (args.server or "").strip()
    if not SERVER_RE.match(server):
        raise SpecError("server name must be lowercase letters, digits and hyphens (e.g. hubspot-crm)")
    transport = args.transport
    spec = {"server": server, "transport": transport, "scope": args.scope,
            "workspace": workspace_key(getattr(args, "workspace", None) or "."),
            "url": None, "command": None, "args": [], "env": {}, "headers": {}, "unpinned_ok": False}
    if transport in ("http", "sse"):
        if args.command or args.arg or args.env:
            raise SpecError("--command/--arg/--env apply to stdio servers only; use --header for http/sse")
        spec["url"] = validate_url(args.url)
        spec["headers"] = parse_headers(args.header)
    elif transport == "stdio":
        if args.url or args.header:
            raise SpecError("--url/--header apply to http/sse servers only")
        if not args.command:
            raise SpecError("--command is required for stdio servers")
        cmd_args = list(args.arg or [])
        for piece in [args.command, *cmd_args]:
            _check_printable("the stdio command and its arguments", piece)
            if looks_like_secret(piece):
                raise SpecError("the command or its arguments contain something that looks like a "
                                "credential -- pass it through --env KEY=${VAR}")
        _check_secret_flags(cmd_args)
        _check_secret_flags(_unwrap_shell(args.command, cmd_args)[1])
        note = check_package_pinned(args.command, cmd_args, bool(getattr(args, "unpinned_ok", False)))
        spec.update(command=args.command, args=cmd_args, env=parse_env(args.env), unpinned_ok=bool(note))
    else:
        if args.url or args.command or args.arg or args.env or args.header:
            raise SpecError("claudeai connectors are attached in claude.ai settings -- no url/command/env/header")
    reads = _normalize_tools(server, _split_csv(args.read_tools))
    writes = _normalize_tools(server, _split_csv(args.write_tools))
    overlap = set(reads) & set(writes)
    if overlap:
        raise SpecError(f"tool(s) listed as both read and write: {', '.join(sorted(overlap))}")
    if not reads and not writes:
        raise SpecError("list at least one tool in --read-tools or --write-tools; unlisted tools are never approved")
    confirmed = set(_normalize_tools(server, _split_csv(getattr(args, "confirm_read_tools", None))))
    suspicious = [t for t in reads if write_shaped(t)]
    unconfirmed = [t for t in suspicious if t not in confirmed]
    if unconfirmed:
        raise SpecError(f"read tool(s) named like write actions: {', '.join(unconfirmed)} -- list them under "
                        f"--write-tools, or, only after checking the vendor's docs that they cannot change "
                        f"anything, repeat them in --confirm-read-tools")
    spec.update(read_tools=reads, write_tools=writes, confirmed_read_tools=suspicious)
    return spec


def _name_tokens(tool: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", tool)
    return [t for t in re.split(r"[\s_.\-]+", spaced.lower()) if t]


def write_shaped(tool: str) -> bool:
    """True when a tool name reads like an action that changes something."""
    tokens = _name_tokens(tool)
    return bool(tokens) and (tokens[0] in WRITE_VERBS_LEADING or any(t in WRITE_VERBS_ANYWHERE for t in tokens))


HASHED_FIELDS = ("server", "transport", "scope", "workspace", "url", "command", "args", "env", "headers",
                 "unpinned_ok", "read_tools", "write_tools")


def config_hash(spec: dict) -> str:
    canonical = {k: spec.get(k) for k in HASHED_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def stakes_class_for(spec: dict) -> str:
    return WRITE_CLASS if spec.get("write_tools") else READ_CLASS


def gate_id_for(spec: dict, digest: str, nonce: str) -> str:
    """One gate per proposal: the nonce keeps an old approval (revoked, or for an earlier proposal) from being reused."""
    return f"mcp_{spec['server'].replace('-', '_')}_{digest[:8]}_{nonce}"


# --------------------------------------------------------------------------- ledger

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ledger_path(workspace) -> Path:
    return Path(workspace) / LEDGER_REL


def read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get("server"):
                events.append(obj)
    return events


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def fold(events: list[dict]) -> dict[str, dict]:
    """Fold events into one record per server: fields carry forward, the last event sets status."""
    state: dict[str, dict] = {}
    for event in events:
        record = dict(state.get(event["server"], {}))
        if event.get("event") == "proposed":
            record = {}
        record.update(event)
        record["status"] = event.get("event")
        state[event["server"]] = record
    return state


def load_state(workspace) -> dict[str, dict]:
    """{server: record} for a workspace; status is proposed | connected | revoked."""
    return fold(read_events(ledger_path(workspace)))


def split_tool_name(tool_name: str) -> tuple[Optional[str], Optional[str]]:
    """'mcp__<server>__<tool>' -> (server, tool); either part None when absent."""
    if not tool_name or not tool_name.startswith("mcp__"):
        return None, None
    server, sep, tool = tool_name[len("mcp__"):].partition("__")
    return (server or None), (tool if sep and tool else None)


def classify_tool(state: dict, tool_name: str) -> tuple[str, Optional[dict]]:
    """("read" | "write" | "unknown", record or None) from the recorded allowlists.

    The record is returned whenever the server is known, whatever its status;
    only a server whose status is "connected" makes a classification usable.
    """
    server, tool = split_tool_name(tool_name)
    record = state.get(server) if server else None
    if not record or not tool:
        return "unknown", record
    if tool in (record.get("read_tools") or []):
        return "read", record
    if tool in (record.get("write_tools") or []):
        return "write", record
    return "unknown", record


def _approval_gate():
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import approval_gate  # noqa: E402 - stdlib-only sibling, imported lazily for the hook
    return approval_gate


def _inside(workspace, path: Path) -> bool:
    root = workspace_key(workspace)
    target = workspace_key(path if path.is_absolute() else Path(workspace) / path)
    return target == root or target.startswith(root.rstrip(os.sep) + os.sep)


def gates_ledger_for(workspace, record: dict) -> Path:
    """The workspace's own gate ledger; a recorded path outside the workspace is never honoured."""
    path = Path(record.get("gates_ledger") or GATES_REL)
    if not _inside(workspace, path):
        path = Path(GATES_REL)
    return path if path.is_absolute() else Path(workspace) / path


def record_problem(workspace, record: dict) -> Optional[str]:
    """None when the record's spec still hashes to its approved config and belongs to this workspace."""
    if record.get("workspace") != workspace_key(workspace):
        return "its approval belongs to a different workspace"
    if config_hash(record) != record.get("config_hash"):
        return "its recorded configuration no longer matches its config hash"
    return None


def gate_problem(gates_ledger: Path, gate_id: Optional[str], digest: str, need_write: bool) -> Optional[str]:
    """None when the gate authorises this exact config, else a one-line reason."""
    if not gate_id:
        return "no approval gate is recorded for this connection"
    ag = _approval_gate()
    try:
        gate = ag.gate_state(gates_ledger, gate_id)
    except (OSError, ValueError):
        gate = None
    if gate is None:
        return f"approval gate {gate_id} does not exist in {gates_ledger.name}"
    if gate["status"] != "approved":
        return f"approval gate {gate_id} is {gate['status']}, not approved"
    if not ag.binding_matches(gates_ledger, gate_id, digest):
        return (f"approval gate {gate_id} was approved for a different configuration "
                f"(bound to {str(gate.get('binding'))[:12]}..., current config {digest[:12]}...)")
    if need_write and gate["stakes_class"] != WRITE_CLASS:
        return f"approval gate {gate_id} is {gate['stakes_class']}; write tools need an approved {WRITE_CLASS} gate"
    if gate["stakes_class"] not in (READ_CLASS, WRITE_CLASS):
        return f"approval gate {gate_id} is {gate['stakes_class']}, not an MCP connection gate"
    return None


def tool_decision(workspace, state: dict, tool_name: str) -> tuple[str, str]:
    """("read" | "write" | "denied", reason) -- the single rule the CLI and the hook share."""
    kind, record = classify_tool(state, tool_name)
    server, tool = split_tool_name(tool_name)
    if record is None:
        return "denied", f"MCP server '{server}' has no Tantra connection record in this workspace"
    if record.get("status") != "connected":
        return "denied", f"MCP server '{server}' is {record.get('status')}, not connected, in this workspace"
    if kind == "unknown":
        return "denied", f"tool '{tool}' is not in the approved read or write list for '{server}'"
    problem = record_problem(workspace, record) or gate_problem(
        gates_ledger_for(workspace, record), record.get("gate_id"), record.get("config_hash", ""),
        need_write=kind == "write")
    if problem:
        return "denied", f"{kind} tool '{tool}' on '{server}': {problem}"
    return kind, f"{kind} tool '{tool}' on connected server '{server}'"


# --------------------------------------------------------------------------- catalog

def load_catalog(path: Optional[str]) -> dict[str, dict]:
    catalog_path = Path(path) if path else DEFAULT_CATALOG
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = data.get("entries") if isinstance(data, dict) else None
    return {e["id"]: e for e in entries or [] if isinstance(e, dict) and e.get("id")}


def catalog_age_days(entry: dict, today: Optional[date] = None) -> Optional[int]:
    try:
        verified = date.fromisoformat(str(entry.get("verified_at"))[:10])
    except ValueError:
        return None
    return ((today or date.today()) - verified).days


def catalog_findings(spec: dict, entry: Optional[dict], catalog_id: Optional[str]) -> list[str]:
    if not catalog_id:
        return ["No catalog entry was given: confirm the endpoint/package against the vendor's official MCP docs "
                "and show the source URLs before approving."]
    if entry is None:
        return [f"Catalog id '{catalog_id}' is not in connectors/mcp_catalog.json: re-verify against the vendor's "
                f"official MCP docs and show the source URLs before approving."]
    notes = []
    age = catalog_age_days(entry)
    if age is None or age > CATALOG_MAX_AGE_DAYS:
        notes.append(f"Catalog entry '{catalog_id}' was verified {entry.get('verified_at') or 'never'} "
                     f"(older than {CATALOG_MAX_AGE_DAYS} days): re-verify before approving.")
    if entry.get("url") and spec.get("url") and entry["url"] != spec["url"]:
        notes.append(f"URL differs from the verified catalog entry ({entry['url']}).")
    if entry.get("package") and entry["package"] not in (spec.get("args") or []):
        notes.append(f"Package differs from the verified catalog entry ({entry['package']}).")
    known = set(entry.get("read_tools") or []) | set(entry.get("write_tools") or [])
    catalog_writes = set(entry.get("write_tools") or [])
    misfiled = sorted(set(spec["read_tools"]) & catalog_writes)
    if misfiled:
        notes.append(f"Listed as read but the catalog marks as WRITE: {', '.join(misfiled)}.")
    unknown = sorted(t for t in spec["read_tools"] + spec["write_tools"] if known and t not in known)
    if unknown:
        notes.append(f"Not in the catalog's tool list (verify they exist): {', '.join(unknown)}.")
    return notes


# --------------------------------------------------------------------------- rendering

def _q(value: str) -> str:
    """Single-quote for Git Bash and PowerShell alike; ${VAR} stays a literal reference.

    A value that could close the quotes (ASCII or typographic single quotes, which PowerShell honours too)
    or carries control characters is refused, never silently altered: the printed command must be exactly
    the approved configuration.
    """
    if any(ch in value for ch in QUOTE_CHARS) or re.search(r"[\x00-\x1f\x7f]", value):
        raise ValueError(f"refusing to print a shell argument containing a quote or control character: {value!r}")
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./\-]+", value) and "${" not in value:
        return value
    return "'" + value + "'"


def credential_line(spec: dict) -> str:
    names = sorted({m.group(1) for v in [*spec["env"].values(), *spec["headers"].values()]
                    for m in VAR_REF_RE.finditer(v)})
    if spec["transport"] == "claudeai":
        return "Managed by claude.ai (connector authorised in claude.ai settings); nothing stored here."
    if names:
        return ("Environment variables (names only; values live in your shell/OS, never in chat or this ledger): "
                + ", ".join(names))
    if spec["transport"] in ("http", "sse"):
        return "OAuth via /mcp in Claude Code (tokens kept by Claude Code, never in chat or this ledger)."
    return "None declared."


def gate_command(spec: dict, digest: str, gate_id: str, lib_dir: Path) -> str:
    klass = stakes_class_for(spec)
    what = "read-only" if klass == READ_CLASS else f"read + {len(spec['write_tools'])} WRITE tool(s)"
    summary = f"Connect MCP server {spec['server']} ({spec['transport']}, scope {spec['scope']}, {what})"
    approved = (f"Tantra may call only the listed tools of {spec['server']} in this workspace, "
                f"for config {digest[:12]}; any change needs a new approval")
    rejected = "Nothing is connected; the proposal stays on record as not approved"
    irreversible = ("Connects a live external system: tool output enters the Tantra session context"
                    + ("; write tools can change live records" if spec["write_tools"] else ""))
    parts = ["python", _q(str(lib_dir / "approval_gate.py")), _q(GATES_REL.replace(os.sep, "/")), "create",
             "--gate-id", gate_id, "--stakes-class", klass,
             "--summary", _q(summary), "--what-if-approved", _q(approved),
             "--what-if-rejected", _q(rejected), "--red-team-verdict", _q("N/A"),
             "--irreversibility-note", _q(irreversible),
             "--latest-json", _q(LATEST_REL.replace(os.sep, "/")), "--binding", digest]
    return " ".join(parts)


def approval_card(spec: dict, digest: str, gate_id: str, entry: Optional[dict], findings: list[str]) -> str:
    where = spec.get("url") or " ".join([spec.get("command") or "", *spec.get("args", [])]).strip() or "claude.ai connector"
    title = (entry or {}).get("display_name") or spec["server"]
    scope_note = {"local": "this workspace only, kept in ~/.claude.json, never committed",
                  "project": "shared .mcp.json in this workspace (committable; ${VAR} references only)",
                  "user": "every project on this machine"}.get(spec["scope"], spec["scope"])
    cost = (entry or {}).get("cost_note") or "UNKNOWN until checked against the vendor's pricing page -- state it before approving."
    lines = [
        f"=== Tantra connector approval card: {spec['server']} ===",
        f"Connects:            {title} -- {where}",
        f"Transport / scope:   {spec['transport']}, {spec['scope']} ({scope_note})",
        f"Read tools ({len(spec['read_tools'])}):       {', '.join(spec['read_tools']) or 'none'}",
        f"Write tools ({len(spec['write_tools'])}):      {', '.join(spec['write_tools']) or 'none -- read-only connection'}",
        f"Credentials:         {credential_line(spec)}",
        f"Cost:                {cost}",
        ("Approval authorises: exactly this configuration (hash " + digest[:12] + "...). Tantra may call only the "
         "tools listed above in this workspace. Any other tool, a changed URL/package/scope/tool list, or another "
         "workspace needs a new approval."
         + (" Write tools may run only while this gate stays approved; each write still goes through the "
            "orchestrator's own action gate." if spec["write_tools"] else "")),
        f"Workspace:           {spec.get('workspace')}",
        f"Gate:                {gate_id} (stakes class {stakes_class_for(spec)})",
        f"Config hash:         {digest}",
    ]
    for note in findings:
        lines.append(f"CHECK:               {note}")
    return "\n".join(lines)


def connect_command(record: dict) -> str:
    server, transport, scope = record["server"], record["transport"], record["scope"]
    if transport == "claudeai":
        return (f"# {server} is a claude.ai connector: authorise it in claude.ai > Settings > Connectors; "
                f"no `claude mcp add` is needed.")
    # `-e/--env` and `-H/--header` are variadic in the claude CLI: placed before <name> they swallow
    # the name and URL. So the positionals come first, then the options, then `--` and the stdio command.
    parts = ["claude", "mcp", "add", "--transport", transport, "--scope", scope, server]
    if transport in ("http", "sse"):
        parts.append(_q(record["url"]))
        for key, value in sorted((record.get("headers") or {}).items()):
            parts += ["--header", _q(f"{key}: {value}")]
    else:
        for key, value in sorted((record.get("env") or {}).items()):
            parts += ["--env", _q(f"{key}={value}")]
        parts += ["--", _q(record["command"]), *[_q(a) for a in record.get("args") or []]]
    command = " ".join(parts)
    if transport in ("http", "sse") and not record.get("headers"):
        command += f"\n# Then in Claude Code run /mcp, pick '{server}' and complete the vendor's OAuth sign-in."
    return command


def remove_command(record: dict) -> str:
    if record.get("transport") == "claudeai":
        return f"# Disconnect {record['server']} in claude.ai > Settings > Connectors."
    return f"claude mcp remove {record['server']} -s {record.get('scope', 'local')}"


# --------------------------------------------------------------------------- commands

def _err(message: str) -> int:
    print(f"ERROR: {redact(message)}", file=sys.stderr)
    return 1


def cmd_propose(args: argparse.Namespace) -> int:
    try:
        spec = build_spec(args)
    except SpecError as exc:
        return _err(str(exc))
    digest = config_hash(spec)
    gate_id = gate_id_for(spec, digest, secrets.token_hex(3))
    entry = load_catalog(args.catalog).get(args.catalog_id) if args.catalog_id else None
    findings = catalog_findings(spec, entry, args.catalog_id)
    if spec["unpinned_ok"]:
        findings.append(check_package_pinned(spec["command"], spec["args"], True))
    if spec["confirmed_read_tools"]:
        findings.append("Named like write actions but confirmed read-only by the user: "
                        + ", ".join(spec["confirmed_read_tools"]) + ". Cite the vendor doc that says so.")
    try:
        gate_cmd = gate_command(spec, digest, gate_id, Path(__file__).resolve().parent)
        connect_command(spec)
    except ValueError as exc:
        return _err(str(exc))
    event = {"event": "proposed", "timestamp": _now_iso(), **spec, "config_hash": digest,
             "stakes_class": stakes_class_for(spec), "gate_id": gate_id,
             "catalog_id": args.catalog_id, "notes": redact(args.notes or "")}
    append_event(ledger_path(args.workspace), event)
    print(approval_card(spec, digest, gate_id, entry, findings))
    print("\nOpen the approval gate (run from the workspace root), then wait for an unambiguous yes:")
    print(gate_cmd)
    print("\nAfter the user approves, record it with approval_gate.py respond, then run connect-command.")
    return 0


def _record_or_err(workspace, server: str) -> tuple[Optional[dict], Optional[int]]:
    record = load_state(workspace).get(server)
    if record is None:
        return None, _err(f"no connection record for '{server}' in {ledger_path(workspace)}")
    return record, None


def cmd_connect_command(args: argparse.Namespace) -> int:
    record, code = _record_or_err(args.workspace, args.server)
    if record is None:
        return code
    if record["status"] == "revoked":
        return _err(f"'{args.server}' is revoked -- propose it again to reconnect")
    try:
        command = connect_command(record)
    except ValueError as exc:
        return _err(f"{exc} -- propose the connection again with a clean spec")
    print(command)
    print(f"# Verify with: claude mcp get {args.server}")
    return 0


def cmd_record_connect(args: argparse.Namespace) -> int:
    record, code = _record_or_err(args.workspace, args.server)
    if record is None:
        return code
    if record["status"] not in ("proposed", "connected"):
        return _err(f"'{args.server}' is {record['status']} -- propose it again first")
    if args.gate_id != record.get("gate_id"):
        return _err(f"not recording '{args.server}' as connected: gate {args.gate_id} is not the gate opened for "
                    f"the current proposal ({record.get('gate_id')}); an earlier or revoked approval never carries over")
    if args.gates_ledger and not _inside(args.workspace, Path(args.gates_ledger)):
        return _err(f"not recording '{args.server}' as connected: --gates-ledger must be inside this workspace; "
                    f"another workspace's approval never counts here")
    gates = Path(args.gates_ledger) if args.gates_ledger else Path(args.workspace) / GATES_REL
    problem = record_problem(args.workspace, record) or gate_problem(
        gates, args.gate_id, record["config_hash"], need_write=bool(record.get("write_tools")))
    if problem:
        return _err(f"not recording '{args.server}' as connected: {problem}")
    event = {"event": "connected", "timestamp": _now_iso(), "server": args.server,
             "gate_id": args.gate_id, "config_hash": record["config_hash"],
             "gates_ledger": args.gates_ledger or GATES_REL.replace(os.sep, "/")}
    append_event(ledger_path(args.workspace), event)
    print(f"Recorded: {args.server} connected under gate {args.gate_id} (config {record['config_hash'][:12]}...).")
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    record, code = _record_or_err(args.workspace, args.server)
    if record is None:
        return code
    if record["status"] == "revoked":
        return _err(f"'{args.server}' is already revoked")
    event = {"event": "revoked", "timestamp": _now_iso(), "server": args.server,
             "reason": redact(args.reason or "")}
    append_event(ledger_path(args.workspace), event)
    print(f"Recorded: {args.server} revoked. Remove it from Claude Code with:")
    print(remove_command(record))
    return 0


def _summary(record: dict) -> dict:
    keys = ("server", "status", "transport", "scope", "url", "command", "args", "env", "headers",
            "read_tools", "write_tools", "stakes_class", "gate_id", "config_hash", "catalog_id", "timestamp")
    return {k: record.get(k) for k in keys}


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(args.workspace)
    if args.server:
        if args.server not in state:
            return _err(f"no connection record for '{args.server}'")
        state = {args.server: state[args.server]}
    print(json.dumps({s: _summary(r) for s, r in sorted(state.items())}, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    state = load_state(args.workspace)
    if not state:
        print("No MCP connections recorded in this workspace.")
        return 0
    for server, record in sorted(state.items()):
        print(f"{server:<28} {record.get('status', '?'):<10} {record.get('transport', '?'):<8} "
              f"scope={record.get('scope', '?'):<8} read={len(record.get('read_tools') or [])} "
              f"write={len(record.get('write_tools') or [])} gate={record.get('gate_id') or '-'}")
    return 0


def cmd_check_tool(args: argparse.Namespace) -> int:
    decision, reason = tool_decision(args.workspace, load_state(args.workspace), args.tool)
    if decision == "denied":
        print(f"NOT APPROVED: {reason}. Use the tantra-connect skill ('mk connect <app>') to propose it.")
        return 1
    if decision == "write":
        print(f"APPROVED WRITE: {reason}. Each write action still needs the orchestrator's action gate.")
        return 3
    print(f"APPROVED READ: {reason}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=".", help="Client workspace root (default: current directory).")
    sub = p.add_subparsers(dest="command_name", required=True)

    pr = sub.add_parser("propose", parents=[common], help="Validate a connector spec and print its approval card.")
    pr.add_argument("--server", required=True)
    pr.add_argument("--transport", required=True, choices=TRANSPORTS)
    pr.add_argument("--url")
    pr.add_argument("--command")
    pr.add_argument("--arg", action="append", default=[], help="One stdio argument (write flags as --arg=-y), or put the whole command line after a bare --.")
    pr.add_argument("--env", action="append", default=[], help="KEY=${VAR}; repeat for more.")
    pr.add_argument("--header", action="append", default=[], help="'Name: ${VAR}'; repeat for more.")
    pr.add_argument("--scope", required=True, choices=SCOPES)
    pr.add_argument("--read-tools", default="")
    pr.add_argument("--write-tools", default="")
    pr.add_argument("--unpinned-ok", action="store_true",
                    help="Accept a stdio command whose version cannot be pinned (the user's explicit choice; shown on the card).")
    pr.add_argument("--confirm-read-tools", default="",
                    help="Read tools whose names look like write actions, confirmed read-only against the vendor's docs.")
    pr.add_argument("--catalog-id")
    pr.add_argument("--catalog", help="Alternative catalog path (default: <repo>/connectors/mcp_catalog.json).")
    pr.add_argument("--notes")

    cc = sub.add_parser("connect-command", parents=[common], help="Print the claude mcp add command.")
    cc.add_argument("--server", required=True)

    rc = sub.add_parser("record-connect", parents=[common], help="Record a connection whose bound gate is approved.")
    rc.add_argument("--server", required=True)
    rc.add_argument("--gate-id", required=True)
    rc.add_argument("--gates-ledger", help=f"Default: <workspace>/{GATES_REL}")

    rv = sub.add_parser("revoke", parents=[common], help="Withdraw a connection.")
    rv.add_argument("--server", required=True)
    rv.add_argument("--reason")

    st = sub.add_parser("status", parents=[common], help="Show connection records as JSON.")
    st.add_argument("--server")

    sub.add_parser("list", parents=[common], help="One line per recorded server.")

    ct = sub.add_parser("check-tool", parents=[common], help="Is mcp__server__tool approved here?")
    ct.add_argument("--tool", required=True)
    return p


COMMANDS = {
    "propose": cmd_propose, "connect-command": cmd_connect_command, "record-connect": cmd_record_connect,
    "revoke": cmd_revoke, "status": cmd_status, "list": cmd_list, "check-tool": cmd_check_tool,
}


def split_stdio_tail(argv: list[str]) -> tuple[list[str], list[str]]:
    """Everything after a bare `--` is the stdio command line, flags like -y included."""
    if "--" not in argv:
        return argv, []
    cut = argv.index("--")
    return argv[:cut], argv[cut + 1:]


def main(argv: Optional[list[str]] = None) -> int:
    head, tail = split_stdio_tail(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(head)
    if tail:
        if args.command_name != "propose" or args.command or args.arg:
            return _err("a trailing '-- <command> [args...]' is only for propose, instead of --command/--arg")
        args.command, args.arg = tail[0], tail[1:]
    return COMMANDS[args.command_name](args)


if __name__ == "__main__":
    sys.exit(main())
