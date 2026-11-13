"""Offline pre-check for 0.4.5 (no model calls). See docs/ANALYSIS_PLAN_0.4.5.md.

Part 1 reports, for every ts-6 prompt, whether the 0.4.4 hook (commit 08ca5af) and the current hook
treat it as work. It does not judge. Part 2: on ts-1 to ts-5, the
current hook must treat as work every substantive prompt the 0.4.4 hook treats as work, and must
leave quiet every non-substantive prompt the 0.4.4 hook leaves quiet. Part 2's checks pass or fail.
Run: python3 -I test_precheck_ts6.py PATH_TO_PLUGIN
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
OLD_COMMIT = "08ca5af"


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
    return load(os.path.join(tmp, "hooks", "scout-activate"), "scout_activate_044")


def tasks(name):
    return json.load(open(os.path.join(REPO, "tests", "live", name)))


def main():
    new = load(os.path.join(plugin, "hooks", "scout-activate"), "scout_activate_new")
    tmp = tempfile.mkdtemp()
    checks = []
    try:
        old = old_hook(tmp)
        t = tasks("tasks-ts6.json")
        print(f"Part 1, task set {t['task_set_version']}; columns: 0.4.4 hook ({OLD_COMMIT}), current hook; 1 = work")
        for group in ("substantive", "non_substantive"):
            for x in t[group]:
                print(f"{x['id']:<22} {int(old.is_request(x['prompt']))} {int(new.is_request(x['prompt']))}")
        print("\nPart 2, regression on ts-1 to ts-5")
        for name in ("tasks.json", "tasks-ts2.json", "tasks-ts3.json", "tasks-ts4.json", "tasks-ts5.json"):
            t = tasks(name)
            for x in t["substantive"]:
                if old.is_request(x["prompt"]):
                    checks.append((new.is_request(x["prompt"]), f"{t['task_set_version']} {x['id']} still work"))
            for x in t["non_substantive"]:
                if old.is_request(x["prompt"]):
                    continue
                checks.append((not new.is_request(x["prompt"]), f"{t['task_set_version']} {x['id']} not work"))
        if hasattr(new, "tier"):
            print("\nPart 3 (reports, does not judge): prompts that get the conditional reminder ('maybe') or,")
            print("if not substantive, any reminder; ts-1 to ts-9")
            for name in ("tasks.json", "tasks-ts2.json", "tasks-ts3.json", "tasks-ts4.json", "tasks-ts5.json",
                         "tasks-ts6.json", "tasks-ts7.json", "tasks-ts8.json", "tasks-ts9.json"):
                if not os.path.exists(os.path.join(REPO, "tests", "live", name)):
                    continue
                t = tasks(name)
                for group in ("substantive", "non_substantive"):
                    for x in t[group]:
                        level = new.tier(x["prompt"])
                        if level == "maybe" or (group == "non_substantive" and level):
                            print(f"  {t['task_set_version']} {x['id']}: {level}")
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
