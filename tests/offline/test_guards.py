#!/usr/bin/env python3
"""Offline tests for the run guards (tools/guards.py) in a throwaway clone of this repository.

Checks: a dirty tree is refused; a changed or removed ledger row is detected against HEAD and
against a backup copy; appending is allowed; a missing backup target ends with NOT BACKED UP.
Run: python3 -I tests/offline/test_guards.py [IGNORED_PLUGIN_PATH]
"""
import os
import shutil
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(here))
results = []


def check(ok, name):
    results.append((bool(ok), name))


def sh(cwd, *cmd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)


tmp = tempfile.mkdtemp(prefix="scout-guards-")
try:
    clone = os.path.join(tmp, "repo")
    r = sh(tmp, "git", "clone", "-q", repo, clone)
    check(r.returncode == 0, "clone the committed repository")
    sh(clone, "git", "config", "user.name", "test")
    sh(clone, "git", "config", "user.email", "test@example.invalid")
    probe = ("import sys; sys.path.insert(0, 'tools'); import guards\n"
             "try:\n"
             "    guards.require_clean_tree(['tools'])\n"
             "    guards.check_ledger_append_only()\n"
             "    print('OK')\n"
             "except guards.GuardError as e:\n"
             "    print('REFUSED', e)\n")
    check(sh(clone, sys.executable, "-I", "-c", probe).stdout.startswith("OK"), "clean clone passes")
    with open(os.path.join(clone, "stray.txt"), "w") as f:
        f.write("x")
    check("REFUSED" in sh(clone, sys.executable, "-I", "-c", probe).stdout, "untracked file: refused")
    os.remove(os.path.join(clone, "stray.txt"))
    ledger = os.path.join(clone, "results", "ledger.csv")
    original = open(ledger, encoding="utf-8").read()
    lines = original.splitlines(keepends=True)
    # Change one existing row (and commit nothing): detected against HEAD.
    with open(ledger, "w", encoding="utf-8") as f:
        f.write("".join(lines[:5] + [lines[5].rstrip("\n") + " edited\n"] + lines[6:]))
    chk = ("import sys; sys.path.insert(0, 'tools'); import guards\n"
           "try:\n    guards.check_ledger_append_only(); print('OK')\n"
           "except guards.GuardError as e:\n    print('REFUSED', e)\n")
    tampered = open(ledger, encoding="utf-8").read() != original
    check(tampered and "REFUSED" in sh(clone, sys.executable, "-I", "-c", chk).stdout, "changed row: detected against HEAD")
    with open(ledger, "w", encoding="utf-8") as f:
        f.write("".join(lines[:-1]))
    check("REFUSED" in sh(clone, sys.executable, "-I", "-c", chk).stdout, "removed row: detected against HEAD")
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(original + lines[-1].replace(lines[-1].split(",")[0], lines[-1].split(",")[0] + "-new", 1))
    check(sh(clone, sys.executable, "-I", "-c", chk).stdout.startswith("OK"), "appended row: allowed")
    # Backup copy that holds a row the working ledger no longer has.
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(original)
    bk = os.path.join(tmp, "backup")
    os.makedirs(bk)
    with open(os.path.join(bk, "ledger.csv"), "w", encoding="utf-8") as f:
        f.write(original + "extra-row-only-in-backup\n")
    with open(os.path.join(clone, "results", "backup_targets.json"), "w") as f:
        f.write('{"filesystem": ["%s"]}' % bk)
    check("REFUSED" in sh(clone, sys.executable, "-I", "-c", chk).stdout and "backup" in sh(clone, sys.executable, "-I", "-c", chk).stdout,
          "backup holds a row the ledger lost: detected")
    # Missing backup target: NOT BACKED UP and exit code 3.
    with open(os.path.join(clone, "results", "backup_targets.json"), "w") as f:
        f.write('{"filesystem": ["%s"]}' % os.path.join(tmp, "does-not-exist"))
    os.makedirs(os.path.join(clone, "results", "runs", "x"), exist_ok=True)
    with open(os.path.join(clone, "results", "runs", "x", "manifest.json"), "w") as f:
        f.write("{}")
    b = sh(clone, sys.executable, "-I", "-c", "import sys; sys.path.insert(0, 'tools'); import guards; guards.backup('results/runs/x')")
    check(b.returncode == 3 and "NOT BACKED UP" in b.stderr, "missing backup target: NOT BACKED UP, exit 3")
    # No targets file at all.
    os.remove(os.path.join(clone, "results", "backup_targets.json"))
    b = sh(clone, sys.executable, "-I", "-c", "import sys; sys.path.insert(0, 'tools'); import guards; guards.backup('results/runs/x')")
    check(b.returncode == 3 and "NOT BACKED UP" in b.stderr, "no backup targets configured: NOT BACKED UP, exit 3")
    # Working backup: copies verified.
    os.makedirs(os.path.join(tmp, "ok"))
    with open(os.path.join(clone, "results", "backup_targets.json"), "w") as f:
        f.write('{"filesystem": ["%s"]}' % os.path.join(tmp, "ok"))
    b = sh(clone, sys.executable, "-I", "-c", "import sys; sys.path.insert(0, 'tools'); import guards; print(guards.backup('results/runs/x'))")
    check(b.returncode == 0 and os.path.exists(os.path.join(tmp, "ok", "results", "runs", "x", "manifest.json"))
          and os.path.exists(os.path.join(tmp, "ok", "ledger.csv")), "working target: ledger and run copied")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

failed = [n for ok, n in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
for n in failed:
    print("FAIL", n)
sys.exit(1 if failed else 0)
