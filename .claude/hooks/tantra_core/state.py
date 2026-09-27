"""
state.py -- tiny, append-only persistence for Tantra hooks.

Everything a hook remembers lives under TANTRA_HOME (default ~/.tantra),
never inside the framework repo and never inside a client workspace unless a
module deliberately mirrors a summary there:

  ~/.tantra/
    config.json                      optional user overrides, one section per module
    logs/hook_errors.log             fail-open error log (rotated at ~1 MB)
    state/<session_id>/
      activation.jsonl               {"ts","event":"on"|"off","by","match"}
      sentinel.jsonl                 every deny/block/context a module emitted
      <module-owned files>.jsonl     e.g. dispatch.jsonl, reads.jsonl

Rules:
  * Append-only JSONL, one short line per event. Hooks run in parallel (Claude
    Code runs every matching hook concurrently, and orchestrators dispatch in
    parallel), so read-modify-write of a shared file would race. Appends of
    small lines don't, as long as they hold the append lock (append_jsonl).
  * Readers tolerate a malformed or half-written line and skip it.
"""
import json
import os
import re
import time
from datetime import datetime, timezone

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def now_ts():
    return time.time()


def now_iso(ts=None):
    ts = now_ts() if ts is None else ts
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def safe_name(value, fallback="unknown"):
    value = _SAFE.sub("_", str(value or "")).strip("._")
    return value[:120] or fallback


def tantra_home():
    env = os.environ.get("TANTRA_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".tantra")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


# Appends are serialised with an exclusive lock on one byte far past any real
# end of file. Why: on Windows the CRT emulates O_APPEND as seek-then-write,
# so two hook processes appending at once overwrite and tear each other's
# lines (measured: ~36% of lines lost with 8 writers). Locking a byte beyond
# EOF is allowed on Windows and never overlaps the data readers read, so
# readers are not blocked and no sidecar .lock file is left behind. POSIX
# uses flock on the same descriptor.
_LOCK_OFFSET = 1 << 40
_LOCK_WAIT_S = 3.0

try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None
    try:
        import fcntl
    except ImportError:  # pragma: no cover - neither available
        fcntl = None


def _lock(fd):
    """Take the append lock; True when held. Gives up after _LOCK_WAIT_S (fail open)."""
    deadline = time.monotonic() + _LOCK_WAIT_S
    while True:
        try:
            if msvcrt is not None:
                os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            elif fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            return True
        except OSError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.002)


def _unlock(fd):
    try:
        if msvcrt is not None:
            os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def append_jsonl(path, obj):
    ensure_dir(os.path.dirname(path))
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    data = (line + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
    try:
        locked = _lock(fd)
        try:
            os.lseek(fd, 0, os.SEEK_END)
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
        finally:
            if locked:
                _unlock(fd)
    finally:
        os.close(fd)


def read_jsonl(path, tail=None):
    """Return parsed lines (skipping bad ones). tail=N keeps the last N."""
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    if tail is not None:
        out = out[-tail:]
    return out


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def last_event(path, key="event"):
    rows = read_jsonl(path)
    return rows[-1].get(key) if rows else None


def rotate_if_large(path, max_bytes=1_000_000):
    try:
        if os.path.getsize(path) > max_bytes:
            os.replace(path, path + ".1")
    except OSError:
        pass
