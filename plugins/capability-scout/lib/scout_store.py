"""Private, owner-only storage shared by the hook and the probe.

Location: $CLAUDE_PLUGIN_DATA/state when Claude Code provides it (a per-plugin
data folder), otherwise <tempdir>/capability-scout-<uid>. The folder must be a
real directory owned by this user; it is created 0700 and anything group- or
world-accessible is tightened or refused. Files are read only if they are
regular, owned by this user and not accessible to group or others (0600 or
stricter), without following symlinks; they are written atomically (temp file
in the same folder, then rename). State changes happen only under an exclusive
lock: if the lock can't be taken, locked() raises LockUnavailable.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import stat
import tempfile
import time

MAX_BYTES = 4 * 1024 * 1024


class LockUnavailable(Exception):
    """The exclusive state lock could not be established."""
STATE_MAX_AGE_S = 7 * 24 * 3600


def private_dir():
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if base and os.path.isabs(base):
        d = os.path.join(base, "state")
    else:
        d = os.path.join(tempfile.gettempdir(), f"capability-scout-{os.getuid()}")
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        st = os.lstat(d)
    except OSError:
        return None
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        return None  # a symlink, a file, or someone else's folder
    if st.st_mode & 0o077:
        try:
            os.chmod(d, 0o700)
        except OSError:
            return None
    return d


def session_key(session_id, transcript_path):
    """Nested sessions can share a session id, so the transcript path is part of the key."""
    raw = f"{session_id or ''}\0{transcript_path or ''}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def read_json(path, max_age_s=None):
    """Return parsed JSON, or None if missing, stale, unsafe or invalid."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077 or st.st_size > MAX_BYTES):
            return None
        if max_age_s is not None and time.time() - st.st_mtime > max_age_s:
            return None
        with os.fdopen(fd, "rb") as f:
            fd = None
            return json.loads(f.read())
    except (OSError, ValueError):
        return None
    finally:
        if fd is not None:
            os.close(fd)


def write_json(path, obj):
    d = os.path.dirname(path)
    try:
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")  # created 0600
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, separators=(",", ":"))
        os.replace(tmp, path)
        return True
    except OSError:
        with contextlib.suppress(OSError, UnboundLocalError):
            os.unlink(tmp)
        return False


@contextlib.contextmanager
def locked(d):
    """Serialize read-modify-write of state within one folder. Fails closed.

    Raises LockUnavailable, before running the protected block, if the lock file
    can't be opened safely or the exclusive lock can't be taken.
    """
    fd = None
    try:
        fd = os.open(os.path.join(d, ".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            raise OSError("unsafe lock file")
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as e:
        if fd is not None:
            os.close(fd)
        raise LockUnavailable(str(e)) from e
    try:
        yield
    finally:
        os.close(fd)


def prune(d, prefix="state-", max_age_s=STATE_MAX_AGE_S):
    now = time.time()
    with contextlib.suppress(OSError):
        for name in os.listdir(d):
            if name.startswith(prefix) or name.startswith(".tmp-"):
                p = os.path.join(d, name)
                with contextlib.suppress(OSError):
                    if now - os.lstat(p).st_mtime > max_age_s:
                        os.unlink(p)
