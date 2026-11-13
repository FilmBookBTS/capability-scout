"""Offline pre-check for 0.4.4 (no model calls). See docs/ANALYSIS_PLAN_0.4.4.md.

Part 1 reports, for every ts-5 prompt, whether the 0.4.3 hook (commit 15351c2) and the current hook
treat it as work. It does not judge. Part 2 is criterion 5 of the plan: on ts-1 to ts-4, the
current hook must treat as work every substantive prompt the 0.4.3 hook treats as work, and must
leave quiet every non-substantive prompt the 0.4.3 hook leaves quiet. Part 2's checks pass or fail.
Run: python3 -I test_precheck_ts5.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "plugins", "capability-scout")
OLD_COMMIT = "15351c2"


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def old_hook(tmp):
    for rel in ("hooks/scout-activate", "lib/scout_store.py"):
        src = subprocess.run(["git", "show", f"{OLD_COMMIT}:plugins/capability-scout/{rel}"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
        os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
        with open(os.path.join(tmp, rel), "w") as f:
            f.write(src)
    return load(os.path.join(tmp, "hooks", "scout-activate"), "scout_activate_043")


def tasks(name):
    return json.load(open(os.path.join(REPO, "tests", "live", name)))


def main():
    new = load(os.path.join(plugin, "hooks", "scout-activate"), "scout_activate_new")
    tmp = tempfile.mkdtemp()
    checks = []
    try:
        old = old_hook(tmp)
        t = tasks("tasks-ts5.json")
        print(f"Part 1, task set {t['task_set_version']}; columns: 0.4.3 hook ({OLD_COMMIT}), current hook; 1 = work")
        for group in ("substantive", "non_substantive"):
            for x in t[group]:
                print(f"{x['id']:<22} {int(old.is_request(x['prompt']))} {int(new.is_request(x['prompt']))}")
        print("\nPart 2, regression on ts-1 to ts-4")
        for name in ("tasks.json", "tasks-ts2.json", "tasks-ts3.json", "tasks-ts4.json"):
            t = tasks(name)
            for x in t["substantive"]:
                if old.is_request(x["prompt"]):
                    checks.append((new.is_request(x["prompt"]), f"{t['task_set_version']} {x['id']} still work"))
            for x in t["non_substantive"]:
                if old.is_request(x["prompt"]):
                    continue
                checks.append((not new.is_request(x["prompt"]), f"{t['task_set_version']} {x['id']} not work"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for ok, label in checks:
        if not ok:
            print("FAIL", label)
    passed = sum(ok for ok, _ in checks)
    print(f"{passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
