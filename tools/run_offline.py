#!/usr/bin/env python3
"""Run every offline test suite against the committed plugin and record the result in the ledger.

Usage: python3 -I tools/run_offline.py RUN_LABEL

Refuses to start on a dirty tree. Writes results/runs/<run_id>/manifest.json and one ledger row per
suite, then backs up to every target in results/backup_targets.json. Exits non-zero if any suite
fails or the backup fails.
"""
import datetime
import json
import os
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guards  # noqa: E402
from ledger_schema import sha256_file  # noqa: E402

REPO = guards.REPO
PLUGIN = os.path.join(REPO, "plugins", "capability-scout")
SUITES = ["test_default_on", "test_hook_classifier", "test_pasted_and_followups", "test_state_and_storage", "test_guards", "test_live_scoring", "test_precheck_ts2", "test_harness_messages", "test_precheck_ts3", "test_precheck_ts4", "test_precheck_ts5", "test_precheck_ts6"]


def plugin_version():
    return json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))["version"]


def main(argv):
    label = argv[1] if len(argv) > 1 else "offline"
    try:
        commit = guards.require_clean_tree(["plugins/capability-scout", "tests/offline", "tests/live", "tools"])
        guards.check_ledger_append_only()
    except guards.GuardError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{label}"
    run_rel = os.path.join("results", "runs", run_id)
    os.makedirs(os.path.join(REPO, run_rel), exist_ok=False)
    version = plugin_version()
    skill = sha256_file(os.path.join(PLUGIN, "skills", "capability-scout", "SKILL.md"))
    hook = sha256_file(os.path.join(PLUGIN, "hooks", "scout-activate"))
    cc = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip() or "not available"
    rows, results, failed = [], [], False
    env = {k: v for k, v in os.environ.items() if k not in ("CAPABILITY_SCOUT_HOOK", "EVAL_CAPABILITY_SCOUT_HOOK")}
    for i, s in enumerate(SUITES, 1):
        # Paths relative to the repository root, so the manifest holds no machine-specific path.
        cmd = [sys.executable, "-I", os.path.join("tests", "offline", s + ".py"), os.path.join("plugins", "capability-scout")]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env, timeout=600)
        summary = next((l for l in r.stdout.splitlines() if "/" in l and "passed" in l), "no summary line")
        ok = r.returncode == 0 and "FAIL" not in r.stdout
        failed |= not ok
        with open(os.path.join(REPO, run_rel, s + ".txt"), "w") as f:
            f.write(r.stdout + r.stderr)
        results.append({"suite": s, "command": "python3 " + " ".join(cmd[1:]), "returncode": r.returncode, "summary": summary})
        rows.append({
            "run_id": f"{run_id}:{i:03d}", "date_utc": now.isoformat().replace("+00:00", "Z"), "edition": "plugin",
            "plugin_version": version, "plugin_commit": guards.file_commit("plugins/capability-scout"),
            "skill_sha256": skill, "hook_sha256": hook, "harness_commit": commit,
            "task_set_version": "offline suites", "task_id": s, "task_prompt_sha256": "", "arm": "offline",
            "model_id": "none (no model calls)", "claude_code_version": cc,
            "environment": f"{platform.system()} {platform.release()}, python {platform.python_version()}",
            "activated": "", "scout_before_work": "", "false_trigger": "", "cost_usd": "0",
            "evidence_path": f"repo:{run_rel}/{s}.txt",
            "notes": f"offline suite, not a model session; result {summary}" + ("" if ok else "; FAILED"),
        })
    manifest = {"run_id": run_id, "kind": "offline", "started_utc": now.isoformat(), "repo_commit": commit,
                "plugin_version": version, "skill_sha256": skill, "hook_sha256": hook,
                "claude_code_version": cc, "python": platform.python_version(), "suites": results,
                "analysis_plan": "not applicable (offline)", "repeat": f"git checkout {commit} && python3 -I tools/run_offline.py {label}"}
    with open(os.path.join(REPO, run_rel, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    guards.append_rows(rows)
    guards.check_ledger_append_only()
    targets = guards.backup(run_rel)
    for x in results:
        print(f"{x['suite']}: {x['summary']}")
    print(f"recorded {len(rows)} rows as {run_id}; backed up to {len(targets)} target(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
