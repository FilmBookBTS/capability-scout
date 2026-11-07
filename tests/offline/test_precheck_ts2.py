"""Offline pre-check of the hook on task set ts-2 (no model calls). See docs/ANALYSIS_PLAN_0.4.1.md.

Reports, for every ts-2 prompt, whether the hook treats it as work. It does not judge the result:
a check passes when the prompt was evaluated. The 0.4.0 hook (commit 211904d) is shown alongside
when git can provide it. The classifier must not be changed because of what this shows; a change
would be a new version, tested on a new task set.
Run: python3 -I test_precheck_ts2.py PATH_TO_PLUGIN
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
OLD_COMMIT = "211904d"


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def old_hook(tmp):
    """The 0.4.0 hook and its lib, from git, or None."""
    try:
        for rel in ("hooks/scout-activate", "lib/scout_store.py"):
            src = subprocess.run(["git", "show", f"{OLD_COMMIT}:plugins/capability-scout/{rel}"], cwd=REPO,
                                 capture_output=True, text=True, check=True).stdout
            os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
            with open(os.path.join(tmp, rel), "w") as f:
                f.write(src)
        return load(os.path.join(tmp, "hooks", "scout-activate"), "scout_activate_040")
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    new = load(os.path.join(plugin, "hooks", "scout-activate"), "scout_activate_new")
    tmp = tempfile.mkdtemp()
    try:
        old = old_hook(tmp)
        t = json.load(open(os.path.join(REPO, "tests", "live", "tasks-ts2.json")))
        n = 0
        counts = {}
        print(f"task set {t['task_set_version']}; columns: 0.4.0 hook ({OLD_COMMIT}), current hook; 1 = treated as work")
        for group in ("substantive", "non_substantive"):
            for x in t[group]:
                a = "-" if old is None else int(old.is_request(x["prompt"]))
                b = int(new.is_request(x["prompt"]))
                kind = "substantive" if group == "substantive" else x["kind"]
                key = "names-other-tool" if kind == "names-other-tool" else (
                    "near-miss" if x["id"].startswith("NM") else ("substantive" if group == "substantive" else "plainly trivial"))
                c = counts.setdefault(key, [0, 0, 0])
                c[0] += 1
                c[1] += 0 if a == "-" else a
                c[2] += b
                print(f"{x['id']:<22} {a} {b}")
                n += 1
        print()
        for key, (tot, a, b) in counts.items():
            print(f"{key}: 0.4.0 treats {'?' if old is None else a}/{tot} as work; current hook {b}/{tot}")
        print(f"{n}/{n} passed (prompts evaluated; this suite reports and does not judge)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
