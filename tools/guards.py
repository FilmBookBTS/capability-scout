"""Guards every test run must pass. Used by tools/run_offline.py and tests/live/run_live.py.

1. require_clean_tree: the repository has no uncommitted or untracked changes, and the files a run
   depends on are committed. A run refuses to start otherwise.
2. check_ledger_append_only: every row already in results/ledger.csv is unchanged. The committed
   ledger (HEAD) and every backup copy must each be an exact prefix of the working ledger.
3. append_rows: writes the manifest and the new ledger rows. The run only reports success after this.
4. backup: copies the ledger, the run's manifest and its evidence folder to every backup target in
   results/backup_targets.json and verifies each copy by hash. If any copy fails, it prints
   NOT BACKED UP and the run exits with an error.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger_schema import LEDGER_COLUMNS, header_line, row_to_csv_line, sha256_file, validate_row  # noqa: E402

REPO = os.path.dirname(HERE)
LEDGER = os.path.join(REPO, "results", "ledger.csv")
TARGETS = os.path.join(REPO, "results", "backup_targets.json")


class GuardError(RuntimeError):
    pass


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise GuardError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def head_commit():
    return git("rev-parse", "HEAD").strip()


def require_clean_tree(required_paths):
    """Refuse unless the tree is clean and each required path is tracked in HEAD."""
    dirty = git("status", "--porcelain", "--untracked-files=all")
    if dirty.strip():
        raise GuardError("working tree is not clean; commit first:\n" + dirty)
    tracked = set(git("ls-files").splitlines())
    for p in required_paths:
        rel = os.path.relpath(os.path.join(REPO, p), REPO)
        if not any(t == rel or t.startswith(rel.rstrip("/") + "/") for t in tracked):
            raise GuardError(f"required file is not committed: {rel}")
    return head_commit()


def file_commit(path):
    """Last commit that touched a path."""
    return git("log", "-1", "--format=%H", "--", path).strip()


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def check_ledger_append_only():
    """Raise if any existing ledger row changed. Returns the number of data rows."""
    cur = _read(LEDGER)
    if not cur.startswith(header_line()):
        raise GuardError("ledger header changed")
    try:
        committed = git("show", "HEAD:results/ledger.csv")
    except GuardError:
        committed = ""
    if committed and not cur.startswith(committed):
        raise GuardError("ledger rows differ from the committed ledger (HEAD): an existing row was changed or removed")
    for t in load_targets(optional=True):
        copy = os.path.join(t, "ledger.csv")
        if os.path.exists(copy):
            b = _read(copy)
            if not cur.startswith(b):
                raise GuardError(f"ledger rows differ from the backup at {copy}: an existing row was changed or removed")
    return cur.count("\n") - 1


def append_rows(rows):
    for r in rows:
        p = validate_row(r)
        if p:
            raise GuardError(f"invalid ledger row {r.get('run_id')}: {p}")
    existing = set()
    import csv
    with open(LEDGER, encoding="utf-8", newline="") as f:
        for x in csv.DictReader(f):
            existing.add(x["run_id"])
    dup = [r["run_id"] for r in rows if r["run_id"] in existing]
    if dup:
        raise GuardError(f"run_id already in the ledger: {dup[:5]}")
    with open(LEDGER, "a", encoding="utf-8", newline="") as f:
        for r in rows:
            f.write(row_to_csv_line({c: r.get(c, "") for c in LEDGER_COLUMNS}))
            f.flush()
        os.fsync(f.fileno())


def load_targets(optional=False):
    if not os.path.exists(TARGETS):
        if optional:
            return []
        raise GuardError(f"no backup targets configured in {TARGETS}")
    cfg = json.load(open(TARGETS))
    targets = [os.path.expanduser(os.path.expandvars(t)) for t in cfg.get("filesystem", [])]
    if not targets and not optional:
        raise GuardError("backup_targets.json lists no filesystem targets")
    return targets


def _copy_verified(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if sha256_file(src) != sha256_file(dst):
        raise OSError(f"hash mismatch after copying to {dst}")


def backup(run_dir_rel):
    """Copy ledger + run folder to every target. Returns list of targets. Exits on any failure."""
    failures, done = [], []
    try:
        targets = load_targets()
    except GuardError as e:
        print(f"NOT BACKED UP: {e}", file=sys.stderr)
        sys.exit(3)
    src_run = os.path.join(REPO, run_dir_rel)
    for t in targets:
        try:
            if not os.path.isdir(t):
                raise OSError(f"backup target does not exist: {t}")
            _copy_verified(LEDGER, os.path.join(t, "ledger.csv"))
            for dp, _, fn in os.walk(src_run):
                for f in fn:
                    s = os.path.join(dp, f)
                    _copy_verified(s, os.path.join(t, os.path.relpath(s, REPO)))
            done.append(t)
        except OSError as e:
            failures.append(f"{t}: {e}")
    if failures:
        print("NOT BACKED UP:\n  " + "\n  ".join(failures), file=sys.stderr)
        sys.exit(3)
    return done
