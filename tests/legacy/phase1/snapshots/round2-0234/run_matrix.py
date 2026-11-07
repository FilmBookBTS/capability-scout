#!/usr/bin/env python3
"""Isolated activation test matrix for Capability Scout.

Each run is a separate non-interactive Claude Code session (`claude -p`) in a
fresh copy of the fixture folder. The plugin is loaded only for that session
with --plugin-dir; nothing is installed. Plugin/MCP install commands are
denied and any attempt is recorded.

Usage: run_matrix.py PLUGIN_DIR FIXTURE_DIR OUT_DIR [--only P1,P2] [--conds A,B,C] [--jobs 4]
"""
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import time

PROMPTS = {
    "P1-security": "Review app.py in this folder for security vulnerabilities and give me a prioritized list of fixes. Do not modify any files.",
    "P2-unavailable": "Pull our team's open Linear issues and summarize which ones are blocked and why.",
    "P3-missing": "Get the latest unresolved Sentry errors for this project and group them by likely root cause.",
    "P4-approval": "Find the best plugin for working with Stripe, install it, and then use it to explain how to refund a charge.",
    "P5-redundant": "Rewrite the paragraph in para.txt so it sounds less like AI wrote it. Just show me the result.",
    "P6-trivial": "What is 17 times 23?",
    "P7-testing": "Write a thorough set of unit tests for parse_amount in app.py and tell me how to run them. Show the tests in your reply instead of writing files.",
    "P8-multistep": "Fix the input validation problems in app.py, add tests for them, open a GitHub pull request with the change, and post a short summary in our team's Slack channel.",
}

CONDS = {
    "A-baseline": {"plugin": False, "hook": None},
    "B-skill": {"plugin": True, "hook": None},
    "C-skill+hook": {"plugin": True, "hook": "nudge"},
    "D-skill+directive": {"plugin": True, "hook": "directive"},
    "E-skill+digest": {"plugin": True, "hook": "digest"},
}

DENY = [
    "Bash(claude plugin install:*)", "Bash(claude plugins install:*)", "Bash(claude plugin i:*)",
    "Bash(claude plugin enable:*)", "Bash(claude plugin marketplace add:*)",
    "Bash(claude mcp add:*)", "Bash(claude mcp add-json:*)",
    "Bash(npm install:*)", "Bash(npm i:*)", "Bash(pip install:*)", "Bash(pip3 install:*)",
    "Bash(python3 -m pip install:*)", "Edit", "Write", "NotebookEdit",
    # Keep test sessions from showing install cards or touching GitHub; attempts are recorded as denials.
    "SuggestPluginInstall", "SuggestConnectors", "SuggestSkills", "Bash(gh:*)", "Bash(git push:*)",
]
INSTALL_RE = re.compile(r"(plugins? (install|i|enable)\b|marketplace add|mcp add|pip3? install|npm (install|i)\b|/plugin install)")
MODEL = os.environ.get("SCOUT_TEST_MODEL")
WORK_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "Agent", "Task"}


def analyze(path):
    tool_calls, hooks, denials, first_ctx, result = [], [], [], None, {}
    for line in open(path):
        try:
            m = json.loads(line)
        except ValueError:
            continue
        t = m.get("type")
        if t == "assistant":
            msg = m.get("message", {})
            if first_ctx is None and msg.get("usage"):
                u = msg["usage"]
                first_ctx = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            for c in msg.get("content", []):
                if c.get("type") == "tool_use":
                    tool_calls.append((c.get("name"), c.get("input", {})))
        elif t == "system" and "hook" in (m.get("subtype") or ""):
            hooks.append(m)
        elif t == "result":
            result = m
            denials = m.get("permission_denials") or []

    def is_scout(name, inp):
        return (name == "Skill" and "capability-scout" in json.dumps(inp)) or \
               (name == "Bash" and "scout-probe" in inp.get("command", ""))

    scout_idx = next((i for i, (n, x) in enumerate(tool_calls) if is_scout(n, x)), None)
    work_idx = next((i for i, (n, x) in enumerate(tool_calls) if not is_scout(n, x) and n != "ToolSearch"
                     and (n in WORK_TOOLS or n.startswith("mcp__") or n == "Skill")), None)
    bash_cmds = [x.get("command", "") for n, x in tool_calls if n == "Bash"]
    hook_text = json.dumps(hooks)
    return {
        "scout_skill": any(n == "Skill" and "capability-scout" in json.dumps(x) for n, x in tool_calls),
        "probe_runs": sum("scout-probe" in c for c in bash_cmds),
        "probe_search": sum("scout-probe search" in c for c in bash_cmds),
        "scout_before_work": scout_idx is not None and (work_idx is None or scout_idx < work_idx),
        "skills_used": [x.get("skill") for n, x in tool_calls if n == "Skill"],
        "tools": [n if n != "Bash" else "Bash:" + x.get("command", "")[:60] for n, x in tool_calls],
        "install_attempts": [c for c in bash_cmds if INSTALL_RE.search(c)],
        "permission_denials": denials,
        "hook_nudge_fired": "Capability Scout:" in hook_text,
        "first_turn_context_tokens": first_ctx,
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "duration_s": round((result.get("duration_ms") or 0) / 1000, 1),
        "is_error": result.get("is_error"),
        "final": (result.get("result") or "")[:4000],
    }


def run_one(plugin_dir, fixture, out_dir, pkey, ckey):
    cond = CONDS[ckey]
    run_dir = os.path.join(out_dir, f"{pkey}__{ckey}")
    work = os.path.join(run_dir, "work")
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(fixture, work)
    cmd = ["claude", "-p", PROMPTS[pkey], *(["--model", MODEL] if MODEL else []), "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--no-session-persistence", "--max-turns", "25",
           "--max-budget-usd", "1.50", "--permission-prompts", "none",
           "--disallowedTools", *DENY, "--allowedTools", "Read", "Glob", "Grep", "Skill", "Bash"]
    if cond["plugin"]:
        cmd += ["--plugin-dir", plugin_dir]
    env = dict(os.environ)
    env.pop("CAPABILITY_SCOUT_HOOK", None)
    if cond["hook"]:
        env["CAPABILITY_SCOUT_HOOK"] = cond["hook"]
    # Nested sessions here inherit the parent's session id, so give each run its
    # own temp dir: the hook's once-per-session marker and the probe cache stay per run.
    env["TMPDIR"] = os.path.join(run_dir, "tmp")
    os.makedirs(env["TMPDIR"], exist_ok=True)
    t0 = time.time()
    with open(os.path.join(run_dir, "stream.jsonl"), "w") as so, open(os.path.join(run_dir, "stderr.txt"), "w") as se:
        try:
            subprocess.run(cmd, cwd=work, env=env, stdout=so, stderr=se, timeout=900)
        except subprocess.TimeoutExpired:
            se.write("TIMEOUT\n")
    res = analyze(os.path.join(run_dir, "stream.jsonl"))
    res.update({"prompt": pkey, "cond": ckey, "wall_s": round(time.time() - t0, 1)})
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


def main():
    plugin_dir, fixture, out_dir = sys.argv[1:4]
    args = sys.argv[4:]
    only = args[args.index("--only") + 1].split(",") if "--only" in args else list(PROMPTS)
    conds = args[args.index("--conds") + 1].split(",") if "--conds" in args else list(CONDS)
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 4
    os.makedirs(out_dir, exist_ok=True)
    pairs = [(p, c) for p in PROMPTS if any(p.startswith(o) for o in only)
             for c in CONDS if any(c.startswith(x) for x in conds)]
    with cf.ThreadPoolExecutor(jobs) as ex:
        futs = {ex.submit(run_one, plugin_dir, fixture, out_dir, p, c): (p, c) for p, c in pairs}
        for f in cf.as_completed(futs):
            r = f.result()
            print(json.dumps({k: r[k] for k in ("prompt", "cond", "scout_skill", "probe_runs", "scout_before_work",
                                                "hook_nudge_fired", "install_attempts", "first_turn_context_tokens",
                                                "cost_usd", "wall_s")}), flush=True)


if __name__ == "__main__":
    main()
