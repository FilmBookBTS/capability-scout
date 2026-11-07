#!/usr/bin/env python3
"""Live activation test for Capability Scout, as defined in docs/ANALYSIS_PLAN.md.

Each session is a separate non-interactive Claude Code process (`claude -p`) in a fresh copy of
tests/fixture, with a fresh, empty Claude Code configuration folder, so that no skill, plugin or
connector from the machine's own setup can load. The arm decides what is added:

  A  no plugin
  B  plugin, hook turned off (CAPABILITY_SCOUT_HOOK=off)
  C  plugin as published (hook on by default; the variable is unset)
  T  chat edition text (chat-edition/capability-scout/SKILL.md) loaded as a skill, no hook, no
     scripts. Recorded as edition=chat-text-in-code. This is not a claude.ai chat test.

Usage:
  python3 -I tests/live/run_live.py plan    --label L [--models M1,M2] [--arms A,B,C,T] [--reps 3] [--seed N]
  python3 -I tests/live/run_live.py isolation-check
  python3 -I tests/live/run_live.py run     --label L --seed N --budget-usd X [--models ...] [--arms ...] [--reps 3] [--jobs 4]

`plan` prints the session count and cost estimate and calls no model. `isolation-check` starts
one session per arm and stops it at the first startup event, before the prompt is answered, to
show which skills load. `run` refuses to start unless the tree is clean, the ledger is unchanged
and every backup target exists. It appends one ledger row per session as each one finishes,
writes the manifest, backs everything up, and only then reports success.
"""
import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import guards  # noqa: E402
from ledger_schema import sha256_file, sha256_text  # noqa: E402

PLUGIN = os.path.join(REPO, "plugins", "capability-scout")
CHAT_SKILL = os.path.join(REPO, "chat-edition", "capability-scout", "SKILL.md")
TASKS = os.path.join(HERE, "tasks.json")
FIXTURE = os.path.join(REPO, "tests", "fixture")
PLAN_DOC = "docs/ANALYSIS_PLAN.md"
REQUIRED = ["plugins/capability-scout", "chat-edition/capability-scout/SKILL.md", "tests/live", "tests/fixture",
            "tools", PLAN_DOC]

ARMS = {
    "A": {"label": "A-no-plugin", "edition": "plugin", "plugin": None, "hook": "unset"},
    "B": {"label": "B-skill-hook-off", "edition": "plugin", "plugin": "plugin", "hook": "off"},
    "C": {"label": "C-published-default", "edition": "plugin", "plugin": "plugin", "hook": "unset"},
    "T": {"label": "T-chat-text-in-code", "edition": "chat-text-in-code", "plugin": "chat", "hook": "unset"},
}
# Skill names each arm is allowed to see. Any other skill whose name contains "capability-scout"
# makes the session invalid (for example an account-synced copy).
OWN_SKILL = {"A": set(), "B": {"capability-scout:capability-scout"}, "C": {"capability-scout:capability-scout"},
             "T": {"capability-scout-chat-text:capability-scout"}}
DEFAULT_MODELS = ["default", "claude-opus-5-5"]

# Same denials as the earlier harness: no file edits, installs, downloads or outward actions.
DENY = [
    "Bash(claude plugin install:*)", "Bash(claude plugins install:*)", "Bash(claude plugin i:*)",
    "Bash(claude plugin enable:*)", "Bash(claude plugin marketplace add:*)",
    "Bash(claude mcp add:*)", "Bash(claude mcp add-json:*)",
    "Bash(npm install:*)", "Bash(npm i:*)", "Bash(pip install:*)", "Bash(pip3 install:*)",
    "Bash(python3 -m pip install:*)", "Edit", "Write", "NotebookEdit",
    "SuggestPluginInstall", "SuggestConnectors", "SuggestSkills", "Bash(gh:*)", "Bash(git push:*)",
    "Bash(python3 -m venv:*)", "Bash(python -m venv:*)", "Bash(./venv/bin/pip:*)", "Bash(uv pip:*)",
]
ALLOW = ["Read", "Glob", "Grep", "Skill", "Bash"]
WORK_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "Agent", "Task"}
# Environment variables that make Claude Code load the account's synced skills and plugins.
SYNC_VARS = ("CLAUDE_CODE_SYNC_SKILLS", "CLAUDE_CODE_SYNC_PLUGINS")
CREDENTIALS = os.path.expanduser("~/.claude/.credentials.json")
PER_SESSION_BUDGET = "1.50"
MAX_TURNS = "25"
TIMEOUT_S = 900
# Cost per session used by `plan`, from the phase-1 rows of the ledger (mean of sessions, by model
# and prompt type), times ISOLATED_OVERHEAD. See docs/ANALYSIS_PLAN.md, "Cost".
COST_MODEL = {("default", "sub"): 0.1055, ("default", "non"): 0.0530,
              ("opus", "sub"): 0.2382, ("opus", "non"): 0.1067}
ISOLATED_OVERHEAD = 1.4
FLAT_ESTIMATE = 0.13


# ---------------------------------------------------------------- scoring (same rules as phase 1)
def is_scout(name, inp):
    return (name == "Skill" and "capability-scout" in json.dumps(inp)) or \
           (name == "Bash" and "scout-probe" in (inp or {}).get("command", ""))


def analyze(path):
    tool_calls, init, result, hook_text = [], None, {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            t = m.get("type")
            if t == "system" and m.get("subtype") == "init" and init is None:
                init = m
            elif t == "system" and "hook" in (m.get("subtype") or ""):
                hook_text.append(json.dumps(m))
            elif t == "assistant":
                for c in (m.get("message") or {}).get("content", []):
                    if c.get("type") == "tool_use":
                        tool_calls.append((c.get("name"), c.get("input") or {}))
            elif t == "result":
                result = m
    scout_idx = next((i for i, (n, x) in enumerate(tool_calls) if is_scout(n, x)), None)
    work_idx = next((i for i, (n, x) in enumerate(tool_calls) if not is_scout(n, x) and n != "ToolSearch"
                     and (n in WORK_TOOLS or (n or "").startswith("mcp__") or n == "Skill")), None)
    hooks = "\n".join(hook_text)
    return {
        "activated": any(n == "Skill" and "capability-scout" in json.dumps(x) for n, x in tool_calls),
        "scout_before_work": scout_idx is not None and (work_idx is None or scout_idx < work_idx),
        "skills_used": [x.get("skill") for n, x in tool_calls if n == "Skill"],
        "tools": [n if n != "Bash" else "Bash:" + x.get("command", "")[:60] for n, x in tool_calls],
        "hook_fired": "Capability Scout" in hooks,
        "init_model": (init or {}).get("model"),
        "init_skills": (init or {}).get("skills") or [],
        "claude_code_version": (init or {}).get("claude_code_version"),
        "model_usage": sorted((result.get("modelUsage") or {}).keys()),
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "is_error": result.get("is_error"),
        "has_result": bool(result),
        "permission_denials": len(result.get("permission_denials") or []),
        "final": (result.get("result") or "")[:4000],
    }


def isolation_problem(arm, skills):
    seen = {s for s in skills if "capability-scout" in s}
    extra = seen - OWN_SKILL[arm]
    missing = OWN_SKILL[arm] - seen
    if extra:
        return "isolation failed: unexpected skill(s) " + ", ".join(sorted(extra))
    if missing:
        return "arm setup failed: skill not loaded " + ", ".join(sorted(missing))
    return ""


# ---------------------------------------------------------------- session setup
def chat_plugin(dst):
    """A minimal plugin holding only the chat edition's SKILL.md (no hook, no scripts)."""
    os.makedirs(os.path.join(dst, ".claude-plugin"))
    os.makedirs(os.path.join(dst, "skills", "capability-scout"))
    with open(os.path.join(dst, ".claude-plugin", "plugin.json"), "w") as f:
        json.dump({"name": "capability-scout-chat-text", "version": "0.0.0-test",
                   "description": "Test wrapper: the chat edition text loaded in Claude Code."}, f)
    shutil.copyfile(CHAT_SKILL, os.path.join(dst, "skills", "capability-scout", "SKILL.md"))
    return dst


def session_env(arm, private_dir):
    """private_dir is outside the run folder, so the credentials copy is never kept or backed up."""
    env = {k: v for k, v in os.environ.items() if k not in SYNC_VARS + ("CAPABILITY_SCOUT_HOOK",
                                                                       "EVAL_CAPABILITY_SCOUT_HOOK")}
    cfg = os.path.join(private_dir, "config")
    os.makedirs(cfg)
    shutil.copyfile(CREDENTIALS, os.path.join(cfg, ".credentials.json"))
    os.chmod(os.path.join(cfg, ".credentials.json"), 0o600)
    env["CLAUDE_CONFIG_DIR"] = cfg
    env["TMPDIR"] = os.path.join(private_dir, "tmp")
    os.makedirs(env["TMPDIR"])
    if ARMS[arm]["hook"] == "off":
        env["CAPABILITY_SCOUT_HOOK"] = "off"
    return env


def session_cmd(arm, prompt, model, plugin_dirs):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--include-hook-events",
           "--no-session-persistence", "--max-turns", MAX_TURNS, "--max-budget-usd", PER_SESSION_BUDGET,
           "--permission-prompts", "none", "--disallowedTools", *DENY, "--allowedTools", *ALLOW]
    if model != "default":
        cmd += ["--model", model]
    kind = ARMS[arm]["plugin"]
    if kind:
        cmd += ["--plugin-dir", plugin_dirs[kind]]
    return cmd


# ---------------------------------------------------------------- schedule and estimate
def load_tasks():
    t = json.load(open(TASKS))
    items = [dict(x, substantive=True) for x in t["substantive"]] + \
            [dict(x, substantive=False) for x in t["non_substantive"]]
    return t["task_set_version"], items


def schedule(models, arms, reps, seed):
    _, items = load_tasks()
    plan = [{"task": x, "arm": a, "model": m, "rep": r}
            for x in items for a in arms for m in models for r in range(1, reps + 1)]
    random.Random(seed).shuffle(plan)
    for i, s in enumerate(plan, 1):
        s["seq"] = i
    return plan


def estimate(plan):
    flat = FLAT_ESTIMATE * len(plan)
    est = sum(COST_MODEL[("opus" if "opus" in s["model"] else "default", "sub" if s["task"]["substantive"] else "non")]
              * ISOLATED_OVERHEAD for s in plan)
    return flat, est


# ---------------------------------------------------------------- commands
def cmd_plan(a):
    plan = schedule(a.models, a.arms, a.reps, a.seed)
    flat, est = estimate(plan)
    ver, items = load_tasks()
    print(f"task set {ver}: {sum(x['substantive'] for x in items)} substantive, "
          f"{sum(not x['substantive'] for x in items)} non-substantive")
    print(f"arms {','.join(a.arms)}; models {','.join(a.models)}; {a.reps} repeats; seed {a.seed}")
    print(f"sessions: {len(plan)}")
    print(f"cost at a flat ${FLAT_ESTIMATE:.2f} per session: ${flat:.2f}")
    print(f"cost from phase-1 means by model and prompt type x{ISOLATED_OVERHEAD}: ${est:.2f}")
    for m in a.models:
        sub = [s for s in plan if s["model"] == m]
        f, e = estimate(sub)
        print(f"  {m}: {len(sub)} sessions, flat ${f:.2f}, model-based ${e:.2f}")
    return 0


def cmd_isolation(a):
    """Start one session per arm and stop it at the init event. Prints the skills each arm sees."""
    tmp = tempfile.mkdtemp(prefix="scout-iso-")
    try:
        plugin_dirs = {"plugin": PLUGIN, "chat": chat_plugin(os.path.join(tmp, "chat-plugin"))}
        ok = True
        for arm in a.arms:
            sd = os.path.join(tmp, arm)
            os.makedirs(sd)
            env = session_env(arm, sd)  # whole tmp folder is removed at the end
            work = os.path.join(sd, "work")
            shutil.copytree(FIXTURE, work)
            p = subprocess.Popen(session_cmd(arm, "hi", "default", plugin_dirs), cwd=work, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            init = None
            for line in p.stdout:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if m.get("type") == "system" and m.get("subtype") == "init":
                    init = m
                    break
            p.kill()
            p.wait()
            skills = (init or {}).get("skills") or []
            prob = isolation_problem(arm, skills) if init else "no startup event"
            ok &= not prob
            print(f"{ARMS[arm]['label']}: {len(skills)} skills; scout skills "
                  f"{sorted(s for s in skills if 'capability-scout' in s)}; plugins "
                  f"{[x.get('name') for x in (init or {}).get('plugins', [])]}; {prob or 'OK'}")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_run(a):
    try:
        commit = guards.require_clean_tree(REQUIRED)
        guards.check_ledger_append_only()
        targets = guards.load_targets()
        missing = [t for t in targets if not os.path.isdir(t)]
        if missing:
            raise guards.GuardError("backup target does not exist: " + ", ".join(missing))
        if not os.path.exists(CREDENTIALS):
            raise guards.GuardError(f"no Claude Code credentials at {CREDENTIALS}")
    except guards.GuardError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    ver, _ = load_tasks()
    plan = schedule(a.models, a.arms, a.reps, a.seed)
    resumed_from, done_before = None, []
    if a.resume:
        # Finish an interrupted run: same schedule (same seed, models, arms, repeats), minus the
        # sessions that already have a ledger row. Sessions keep their original order numbers.
        old = json.load(open(os.path.join(REPO, "results", "runs", a.resume, "manifest.json")))
        if [old["seed"], old["models_requested"], sorted(old["arms"]), old["reps"]] != \
                [a.seed, a.models, sorted(a.arms), a.reps]:
            print("REFUSED: --resume needs the same --seed, --models, --arms and --reps as the run it resumes",
                  file=sys.stderr)
            return 2
        if [[s["seq"], s["task"]["id"], s["arm"], s["model"], s["rep"]] for s in plan] != old["order"]:
            print("REFUSED: the schedule no longer matches the interrupted run's recorded order", file=sys.stderr)
            return 2
        import csv
        with open(guards.LEDGER, encoding="utf-8", newline="") as f:
            done_before = sorted(int(r["run_id"].split(":")[1]) for r in csv.DictReader(f)
                                 if r["run_id"].split(":")[0] == a.resume)
        plan = [s for s in plan if s["seq"] not in set(done_before)]
        resumed_from = a.resume
    flat, est = estimate(plan)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{a.label}"
    run_rel = os.path.join("results", "runs", run_id)
    run_dir = os.path.join(REPO, run_rel)
    raw = os.path.join(run_dir, "raw")
    os.makedirs(raw)
    plugin_dirs = {"plugin": PLUGIN, "chat": chat_plugin(os.path.join(raw, "_chat-plugin"))}
    hashes = {"plugin_skill_sha256": sha256_file(os.path.join(PLUGIN, "skills", "capability-scout", "SKILL.md")),
              "hook_sha256": sha256_file(os.path.join(PLUGIN, "hooks", "scout-activate")),
              "chat_skill_sha256": sha256_file(CHAT_SKILL), "tasks_sha256": sha256_file(TASKS),
              "analysis_plan_sha256": sha256_file(os.path.join(REPO, PLAN_DOC)),
              "harness_sha256": sha256_file(os.path.abspath(__file__))}
    version = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))["version"]
    manifest = {"run_id": run_id, "kind": "live", "status": "running", "started_utc": now.isoformat(),
                "repo_commit": commit, "plugin_commit": guards.file_commit("plugins/capability-scout"),
                "plugin_version": version, "task_set_version": ver, **hashes,
                "analysis_plan": PLAN_DOC, "arms": {k: ARMS[k] for k in a.arms}, "models_requested": a.models,
                "reps": a.reps, "seed": a.seed, "jobs": a.jobs, "sessions_planned": len(plan),
                "budget_usd": a.budget_usd, "estimate_flat_usd": round(flat, 2), "estimate_model_usd": round(est, 2),
                "per_session_budget_usd": PER_SESSION_BUDGET, "max_turns": MAX_TURNS, "timeout_s": TIMEOUT_S,
                "deny": DENY, "allow": ALLOW, "python": platform.python_version(),
                "host": f"{platform.system()} {platform.release()}",
                "order": [[s["seq"], s["task"]["id"], s["arm"], s["model"], s["rep"]] for s in plan],
                "resumes": resumed_from, "sessions_recorded_before_resume": len(done_before),
                "repeat": f"git checkout {commit} && python3 -I tests/live/run_live.py run --label {a.label} "
                          f"--seed {a.seed} --budget-usd {a.budget_usd} --models {','.join(a.models)} "
                          f"--arms {','.join(a.arms)} --reps {a.reps}" + (f" --resume {a.resume}" if a.resume else "")}
    mpath = os.path.join(run_dir, "manifest.json")

    def write_manifest():
        with open(mpath, "w") as f:
            json.dump(manifest, f, indent=2)
    write_manifest()

    lock = threading.Lock()
    spent = [0.0]
    done, skipped = [], []
    sessions_path = os.path.join(run_dir, "sessions.jsonl")

    def one(s):
        with lock:
            if spent[0] >= a.budget_usd:
                skipped.append(s["seq"])
                return None
        arm, task, model = s["arm"], s["task"], s["model"]
        sd = os.path.join(raw, f"{s['seq']:04d}")
        os.makedirs(sd)
        private = tempfile.mkdtemp(prefix="scout-session-")
        timed_out = False
        t0 = time.time()
        try:
            env = session_env(arm, private)
            work = os.path.join(sd, "work")
            shutil.copytree(FIXTURE, work)
            with open(os.path.join(sd, "stream.jsonl"), "w") as so, open(os.path.join(sd, "stderr.txt"), "w") as se:
                try:
                    subprocess.run(session_cmd(arm, task["prompt"], model, plugin_dirs), cwd=work, env=env,
                                   stdout=so, stderr=se, timeout=TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    se.write("TIMEOUT\n")
        finally:
            shutil.rmtree(private, ignore_errors=True)
        r = analyze(os.path.join(sd, "stream.jsonl"))
        invalid = ("timeout" if timed_out else "") or ("" if r["has_result"] else "no result event") or \
                  ("error result" if r["is_error"] else "") or isolation_problem(arm, r["init_skills"])
        sub = task["substantive"]
        act = "" if invalid else ("true" if r["activated"] else "false")
        model_id = r["init_model"] or ("not recorded" if model == "default" else model)
        rec = {"seq": s["seq"], "task_id": task["id"], "arm": arm, "model_requested": model, "rep": s["rep"],
               "wall_s": round(time.time() - t0, 1), "invalid": invalid,
               **{k: v for k, v in r.items() if k not in ("final", "init_skills")},
               "init_skills_sha256": sha256_text("\n".join(sorted(r["init_skills"]))),
               "init_scout_skills": sorted(x for x in r["init_skills"] if "capability-scout" in x)}
        with open(os.path.join(sd, "final.txt"), "w") as f:
            f.write(r["final"])
        is_chat = ARMS[arm]["plugin"] == "chat"
        row = {
            "run_id": f"{run_id}:{s['seq']:04d}", "date_utc": now.isoformat().replace("+00:00", "Z"),
            "edition": ARMS[arm]["edition"],
            "plugin_version": "chat edition SKILL.md" if is_chat else (version if ARMS[arm]["plugin"] else "none (no plugin)"),
            "plugin_commit": guards.file_commit("chat-edition/capability-scout/SKILL.md") if is_chat
            else (manifest["plugin_commit"] if ARMS[arm]["plugin"] else ""),
            "skill_sha256": hashes["chat_skill_sha256"] if is_chat else (hashes["plugin_skill_sha256"] if ARMS[arm]["plugin"] else ""),
            "hook_sha256": hashes["hook_sha256"] if arm in ("B", "C") else "",
            "harness_commit": commit, "task_set_version": ver, "task_id": task["id"],
            "task_prompt_sha256": sha256_text(task["prompt"]), "arm": ARMS[arm]["label"], "model_id": model_id,
            "claude_code_version": r["claude_code_version"] or "not recorded",
            "environment": "isolated Claude Code config (no synced skills or plugins); claude -p; fresh fixture copy",
            "activated": act,
            "scout_before_work": "" if invalid else ("true" if r["scout_before_work"] else "false"),
            "false_trigger": "" if (sub or invalid) else act,
            "cost_usd": "" if r["cost_usd"] is None else f"{r['cost_usd']:.6f}",
            "evidence_path": f"repo:{run_rel}/sessions.jsonl#seq={s['seq']}; raw:{run_rel}/raw/{s['seq']:04d}/",
            "notes": "; ".join(x for x in [
                f"rep={s['rep']}", f"order={s['seq']}", "substantive" if sub else "non-substantive",
                f"hook_fired={str(r['hook_fired']).lower()}", f"model_usage={'+'.join(r['model_usage']) or 'none'}",
                f"invalid: {invalid}" if invalid else ""] if x),
        }
        with lock:
            spent[0] += r["cost_usd"] or 0
            with open(sessions_path, "a") as f:
                f.write(json.dumps(rec) + "\n")
            guards.append_rows([row])
            done.append(s["seq"])
            print(f"[{len(done)}/{len(plan)}] {task['id']} {arm} {model} rep{s['rep']}: "
                  f"activated={act or '-'} before_work={row['scout_before_work'] or '-'} "
                  f"${row['cost_usd'] or '?'} total ${spent[0]:.2f}{' INVALID ' + invalid if invalid else ''}",
                  flush=True)
        return rec

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, plan))
    shutil.rmtree(plugin_dirs["chat"], ignore_errors=True)
    manifest.update({"status": "complete" if not skipped else "stopped at budget",
                     "finished_utc": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
                     "sessions_run": len(done), "sessions_skipped_budget": sorted(skipped),
                     "cost_usd_total": round(spent[0], 4)})
    write_manifest()
    guards.check_ledger_append_only()
    targets = guards.backup(run_rel)
    print(f"recorded {len(done)} sessions as {run_id}; cost ${spent[0]:.2f}; "
          f"{len(skipped)} not run (budget); backed up to {len(targets)} target(s)")
    return 0 if not skipped else 1


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["plan", "isolation-check", "run"])
    p.add_argument("--label", default="live")
    p.add_argument("--models", default=",".join(DEFAULT_MODELS))
    p.add_argument("--arms", default="A,B,C,T")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--budget-usd", type=float, default=None)
    p.add_argument("--resume", default=None, help="run id of an interrupted run to finish")
    a = p.parse_args(argv[1:])
    a.models = [m.strip() for m in a.models.split(",") if m.strip()]
    a.arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    if any(x not in ARMS for x in a.arms):
        p.error("arms must be from A,B,C,T")
    if a.command == "plan":
        if a.seed is None:
            a.seed = 0
        return cmd_plan(a)
    if a.command == "isolation-check":
        return cmd_isolation(a)
    if a.seed is None or a.budget_usd is None:
        p.error("run needs --seed and --budget-usd")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", a.label):
        p.error("label: letters, digits, . _ - only")
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
