"""
context.py -- everything a Tantra hook module needs to know about the event
it is handling, built once per hook process.

Modules read from ctx; they never parse stdin themselves.

  ctx.event            hook_event_name ("PreToolUse", "SubagentStop", ...)
  ctx.mode             trailing CLI argument ("pre", "watchdog", ...)
  ctx.payload          the raw event JSON
  ctx.session_id       main-session id (subagent tool calls share it)
  ctx.agent_id         set only when the hook fires inside a subagent
  ctx.agent_type       subagent name (frontmatter `name`), or --agent name
  ctx.tool_name        canonical tool name ("Task" is normalised to "Agent")
  ctx.tool_input       dict
  ctx.tool_response    dict/str/None
  ctx.cwd              the session's working directory
  ctx.root             the Tantra framework repo (two levels above .claude/hooks)
  ctx.home             TANTRA_HOME (~/.tantra by default)
  ctx.session_dir      ~/.tantra/state/<session_id>
  ctx.workspace_dir    cwd when cwd is a Tantra client workspace, else None
  ctx.registry         parsed .claude/hooks/tantra_registry.json (lazy)
  ctx.active           is Tantra switched on for this session (lazy, settable)

  ctx.cfg(section, defaults)   defaults merged with ~/.tantra/config.json[section]
  ctx.is_tantra_agent(name)    True for any of the framework's own agents
  ctx.tier(name)               "entry" | "bridge" | "domain" | "sub" | None
  ctx.log_sentinel(source, action, **fields)   append to sentinel.jsonl
  ctx.log_error(where, exc)    fail-open error log

Test hooks: TANTRA_HOME redirects all state; TANTRA_REGISTRY points at an
alternative registry file; TANTRA_ACTIVE=1 forces activation (also the
supported switch for unattended/cron runs that cannot type the wake word).
"""
import json
import os
import traceback

from . import state

TRUTHY = {"1", "true", "yes", "on"}
OWN_NAMESPACE = "tantra:"


def own_agent_name(name):
    """Drop Tantra's own "tantra:" plugin prefix. Any other "plugin:" prefix is
    kept: that agent belongs to another plugin, even if its short name matches."""
    if name and name.lower().startswith(OWN_NAMESPACE):
        return name[len(OWN_NAMESPACE):]
    return name


def log_error_standalone(where, exc, home=None):
    try:
        path = os.path.join(home or state.tantra_home(), "logs", "hook_errors.log")
        state.ensure_dir(os.path.dirname(path))
        state.rotate_if_large(path)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{state.now_iso()} [{where}] {type(exc).__name__}: {exc}\n")
            fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:] + "\n")
    except Exception:  # noqa: BLE001
        pass


class Context:
    def __init__(self, payload, mode="", hooks_dir=None, registry=None, home=None):
        self.payload = payload
        self.mode = mode or ""
        self.hooks_dir = hooks_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root = os.path.dirname(os.path.dirname(self.hooks_dir))
        self.home = home or state.tantra_home()

        p = payload
        self.event = p.get("hook_event_name") or ""
        self.session_id = p.get("session_id") or ""
        self.agent_id = p.get("agent_id") or None
        agent_type = p.get("agent_type") or None
        self.agent_type = own_agent_name(agent_type) if isinstance(agent_type, str) else None
        tool = p.get("tool_name") or ""
        self.tool_name = "Agent" if tool == "Task" else tool
        ti = p.get("tool_input")
        self.tool_input = ti if isinstance(ti, dict) else {}
        self.tool_response = p.get("tool_response")
        self.tool_use_id = p.get("tool_use_id") or ""
        self.cwd = p.get("cwd") or os.getcwd()
        self.transcript_path = p.get("transcript_path") or ""
        self.session_dir = os.path.join(self.home, "state", state.safe_name(self.session_id, "no-session"))

        self._registry = registry
        self._config = None
        self._active = None
        self._workspace = "unset"

    # ---- registry ---------------------------------------------------------
    @property
    def registry(self):
        if self._registry is None:
            path = os.environ.get("TANTRA_REGISTRY") or os.path.join(self.hooks_dir, "tantra_registry.json")
            self._registry = state.read_json(path, default={}) or {}
        return self._registry

    def agent_info(self, name):
        if not name:
            return None
        return (self.registry.get("agents") or {}).get(own_agent_name(name))

    def is_tantra_agent(self, name):
        return self.agent_info(name) is not None

    def tier(self, name):
        info = self.agent_info(name)
        return info.get("tier") if info else None

    # ---- config -----------------------------------------------------------
    def cfg(self, section, defaults):
        if self._config is None:
            self._config = state.read_json(os.path.join(self.home, "config.json"), default={}) or {}
        merged = dict(defaults)
        override = self._config.get(section)
        if isinstance(override, dict):
            merged.update(override)
        return merged

    # ---- activation -------------------------------------------------------
    @property
    def activation_path(self):
        return os.path.join(self.session_dir, "activation.jsonl")

    @property
    def active(self):
        if self._active is None:
            self._active = self._compute_active()
        return self._active

    @active.setter
    def active(self, value):
        self._active = bool(value)

    def _compute_active(self):
        last = state.last_event(self.activation_path) if self.session_id else None
        if last == "off":
            return False
        if (os.environ.get("TANTRA_ACTIVE") or "").strip().lower() in TRUTHY:
            return True
        if last == "on":
            return True
        # A Tantra agent is already running in this session, so Tantra was
        # activated upstream (possibly under a session id we have not seen).
        if self.agent_type and self.is_tantra_agent(self.agent_type):
            return True
        return False

    # ---- workspace ----------------------------------------------------------
    @property
    def workspace_dir(self):
        if self._workspace == "unset":
            cwd = self.cwd
            is_ws = (
                os.path.isfile(os.path.join(cwd, "CLAUDE.md"))
                and (os.path.isdir(os.path.join(cwd, "memory")) or os.path.isdir(os.path.join(cwd, "brand")))
                and not os.path.isdir(os.path.join(cwd, "knowledge-bases"))
            )
            self._workspace = cwd if is_ws else None
        return self._workspace

    # ---- logging ------------------------------------------------------------
    def session_file(self, name):
        return os.path.join(self.session_dir, name)

    def log_sentinel(self, source, action, **fields):
        row = {"ts": state.now_iso(), "event": self.event, "source": source, "action": action}
        if self.tool_name:
            row["tool"] = self.tool_name
        if self.agent_type:
            row["agent_type"] = self.agent_type
        row.update(fields)
        try:
            state.append_jsonl(self.session_file("sentinel.jsonl"), row)
        except OSError:
            pass

    def record_actions(self, results):
        for r in results:
            for kind in ("deny", "ask", "block", "context", "system_message", "rewake"):
                text = getattr(r, kind)
                if text:
                    self.log_sentinel(r.source, kind, chars=len(text))

    def log_error(self, where, exc):
        log_error_standalone(where, exc, self.home)

    def debug(self, message):
        if (os.environ.get("TANTRA_HOOK_DEBUG") or "").strip().lower() in TRUTHY:
            try:
                path = os.path.join(self.home, "logs", "hook_debug.log")
                state.ensure_dir(os.path.dirname(path))
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(f"{state.now_iso()} {self.event} {message}\n")
            except OSError:
                pass

    def dumps(self, obj):
        return json.dumps(obj, ensure_ascii=False, default=str)
