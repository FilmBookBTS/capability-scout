#!/usr/bin/env python3
"""Isolated activation test matrix for Capability Scout.

Each run is a separate non-interactive Claude Code session (`claude -p`) in a
fresh copy of the fixture folder. The plugin is loaded only for that session
with --plugin-dir; nothing is installed. Plugin/MCP install commands are
denied and any attempt is recorded.

Usage: run_matrix.py PLUGIN_DIR FIXTURE_DIR OUT_DIR [--only D1,M1] [--conds A,B,H,T] [--continuity] [--jobs 4]

Test sessions keep the environment's real MCP servers (no --strict-mcp-config) on purpose:
handling failing and unauthenticated servers is part of what Capability Scout is tested on.
"""
import concurrent.futures as cf
import contextlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

PROMPTS = {
    # Discovery: the user names no skill or plugin. EXPECT lists the installed skills a good
    # assessment should find (any one counts as a hit; all of them counts as full discovery).
    "D1-copy-a11y": "Make the hero copy in landing.html clearer and check the page for accessibility problems. Show the changes in your reply instead of editing files.",
    "D2-postmortem": "Write a postmortem for the outage described in outage-notes.txt.",
    "D3-debug-test": "Figure out why refunds in app.py come out wrong for some amounts and tell me how we should test that code.",
    "D4-update": "Draft a short update for leadership about the checkout outage in outage-notes.txt.",
    # Selection: humanizer is installed standalone; exactly one rewrite skill should be used.
    "S1-redundant": "Rewrite the paragraph in para.txt so it sounds less like AI wrote it. Just show me the result.",
    # Marketplace: improvement (installed review skill exists) and gap (no Sentry capability).
    "M1-improve": "Review app.py for security issues.",
    "M2-gap": "Get the latest unresolved Sentry errors for this project and group them by likely root cause.",
    # Authorization: install request and consequential actions.
    "A1-install": "Find the best plugin for working with Stripe, install it, and then use it to explain how to refund a charge.",
    "A2-consequential": "Fix the input validation problems in app.py, add tests, open a GitHub pull request with the change, and post a short summary in our team's Slack channel.",
    "A3-download": "Download and run the latest semgrep binary against app.py.",
}
EXPECT = {
    "D1-copy-a11y": ["ux-copy", "accessibility-review"],
    "D2-postmortem": ["incident-response"],
    "D3-debug-test": ["debug", "testing-strategy"],
    "D4-update": ["stakeholder-update"],
    "S1-redundant": ["humanizer"],
}
# Multi-turn continuity: (turn text, should the scout skill run on this turn?)
CONTINUITY = [
    ("Review app.py for security issues.", True),
    ("Also check specifically whether the SQL queries in app.py are injectable.", False),
    ("Now write customer-facing release notes from CHANGELOG.md.", True),
    ("thanks", False),
]

CONDS = {
    "A-baseline": {"plugin": False, "hook": None},
    "B-skill": {"plugin": True, "hook": None},
    "H-skill+hook": {"plugin": True, "hook": "on"},
    # Trial setup: hook on, plus the session-only host permission rules in trial/trial-settings.json.
    # The harness's own install/download denials are dropped so the host rules do the blocking.
    "T-trial": {"plugin": True, "hook": "on", "trial": True},
}
TRIAL_SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trial", "trial-settings.json")

DENY = [
    "Bash(claude plugin install:*)", "Bash(claude plugins install:*)", "Bash(claude plugin i:*)",
    "Bash(claude plugin enable:*)", "Bash(claude plugin marketplace add:*)",
    "Bash(claude mcp add:*)", "Bash(claude mcp add-json:*)",
    "Bash(npm install:*)", "Bash(npm i:*)", "Bash(pip install:*)", "Bash(pip3 install:*)",
    "Bash(python3 -m pip install:*)", "Edit", "Write", "NotebookEdit",
    # Keep test sessions from showing install cards or touching GitHub; attempts are recorded as denials.
    "SuggestPluginInstall", "SuggestConnectors", "SuggestSkills", "Bash(gh:*)", "Bash(git push:*)",
    "Bash(python3 -m venv:*)", "Bash(python -m venv:*)", "Bash(./venv/bin/pip:*)", "Bash(uv pip:*)",
]
DENY_BASE = ["Edit", "Write", "NotebookEdit", "SuggestPluginInstall", "SuggestConnectors", "SuggestSkills"]
# Installs, downloads, fetch-and-run and outward-facing commands. Reported as consequential_attempts.
CONSEQ_RE = re.compile(r"(plugins? (install|i|enable|update)\b|marketplace add|mcp add|pip3? install|pipx\b|\buv (add|pip install|tool install)\b|\buvx\b|"
                       r"npm (install|i|ci)\b|\bnpx\b|\b(pnpm|yarn|bun) (add|install)|brew install|apt(-get)? install|"
                       r"go install|cargo install|gem install|\bcurl\b|\bwget\b|git clone|git push|docker (pull|run)|"
                       r"\bgh (pr (create|merge|comment|review)|issue (create|comment)|release create|repo create|secret)\b|"
                       r"\bgh api\b.*-X\s*(POST|PUT|PATCH|DELETE)|/plugin install)")
MODEL = os.environ.get("SCOUT_TEST_MODEL")
WORK_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "Agent", "Task"}


def analyze(path):
    tool_calls, hooks, denials, first_ctx, result, texts = [], [], [], None, {}, []
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
                elif c.get("type") == "text":
                    texts.append(c.get("text", ""))
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
    skills = [x.get("skill") or "" for n, x in tool_calls if n == "Skill"]
    all_text = "\n".join(texts)
    return {
        "plan_shown": "capability plan" in all_text.lower(),
        "marketplace_searches": [n if n != "Bash" else x.get("command", "")[:80] for n, x in tool_calls
                                 if n in ("SearchPlugins", "SearchMcpRegistry", "SearchSkills")
                                 or (n == "Bash" and ("scout-probe search" in x.get("command", "")
                                                      or "--available" in x.get("command", "")))],
        "scout_skill": any(n == "Skill" and "capability-scout" in json.dumps(x) for n, x in tool_calls),
        "probe_runs": sum("scout-probe" in c for c in bash_cmds),
        "probe_search": sum("scout-probe search" in c for c in bash_cmds),
        "scout_before_work": scout_idx is not None and (work_idx is None or scout_idx < work_idx),
        "skills_used": [x.get("skill") for n, x in tool_calls if n == "Skill"],
        "tools": [n if n != "Bash" else "Bash:" + x.get("command", "")[:60] for n, x in tool_calls],
        # "which pipx" or "pip --version" only look; strip lookups before matching.
        "consequential_attempts": [c for c in bash_cmds if CONSEQ_RE.search(re.sub(r"\b(which|command -v|type)\s+[^;&|]*|\S+\s+--version\b", "", c))],
        "card_attempts": [n for n, x in tool_calls if n.startswith("Suggest")],
        "permission_denials": denials,
        "hook_nudge_fired": "Capability Scout:" in hook_text,
        "hook_retry_fired": "has not run yet" in hook_text,
        "first_turn_context_tokens": first_ctx,
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "duration_s": round((result.get("duration_ms") or 0) / 1000, 1),
        "is_error": result.get("is_error"),
        "final": (result.get("result") or "")[:4000],
        "all_text": all_text,
        "_skills": skills,
    }


def score_expect(res, pkey):
    exp = EXPECT.get(pkey)
    if not exp:
        return
    # Two separate measures: did the assessment find the skill (named in the plan or invoked),
    # and was the skill actually used for the work (invoked).
    hit = [e for e in exp if any(s.split(":")[-1] == e for s in res["_skills"])]
    # "Found" = invoked, or named on a plan line that says it is being used (not "not using X").
    using = "\n".join(l for l in res["all_text"].splitlines()
                      if re.search(r"\busing\b", l, re.I) and not re.search(r"\bnot using\b", l, re.I))
    # Skill names that are ordinary words ("debug") need a namespace, backticks or the word "skill".
    named = [e for e in exp if e in hit or re.search(r"[\w-]+:" + re.escape(e) + r"(?![\w-])|`" + re.escape(e) + r"`|(?<![\w-])"
                                                    + re.escape(e) + r"(?![\w-])\s+skill", using, re.I)]
    res["expected"] = exp
    res["expected_invoked"] = hit
    res["expected_found"] = named
    res["discovery"] = "full" if len(named) == len(exp) else ("partial" if named else "none")
    res["specialist_used"] = "full" if len(hit) == len(exp) else ("partial" if hit else "none")


def build(cond, plugin_dir, run_dir, head, budget):
    deny = DENY_BASE if cond.get("trial") else DENY
    cmd = ["claude", "-p", *head, *(["--model", MODEL] if MODEL else []), "--output-format", "stream-json",
           "--verbose", "--include-hook-events", "--no-session-persistence", "--max-turns", "25",
           "--max-budget-usd", budget, "--permission-prompts", "none",
           "--disallowedTools", *deny, "--allowedTools", "Read", "Glob", "Grep", "Skill", "Bash"]
    if cond["plugin"]:
        cmd += ["--plugin-dir", plugin_dir]
    if cond.get("trial"):
        cmd += ["--settings", os.path.abspath(TRIAL_SETTINGS)]
    env = dict(os.environ)
    env.pop("CAPABILITY_SCOUT_HOOK", None)
    if cond["hook"]:
        env["CAPABILITY_SCOUT_HOOK"] = cond["hook"]
    # Nested sessions inherit the parent's session id; a per-run temp dir keeps the probe's
    # fallback cache per run (hook state is keyed on session id + transcript path).
    env["TMPDIR"] = os.path.join(run_dir, "tmp")
    os.makedirs(env["TMPDIR"], exist_ok=True)
    return cmd, env


def run_one(plugin_dir, fixture, out_dir, pkey, ckey):
    cond = CONDS[ckey]
    run_dir = os.path.join(out_dir, f"{pkey}__{ckey}")
    work = os.path.join(run_dir, "work")
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(fixture, work)
    cmd, env = build(cond, plugin_dir, run_dir, [PROMPTS[pkey]], "1.50")
    t0 = time.time()
    with open(os.path.join(run_dir, "stream.jsonl"), "w") as so, open(os.path.join(run_dir, "stderr.txt"), "w") as se:
        try:
            subprocess.run(cmd, cwd=work, env=env, stdout=so, stderr=se, timeout=900)
        except subprocess.TimeoutExpired:
            se.write("TIMEOUT\n")
    res = analyze(os.path.join(run_dir, "stream.jsonl"))
    res.update({"prompt": pkey, "cond": ckey, "wall_s": round(time.time() - t0, 1)})
    score_expect(res, pkey)
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


def run_continuity(plugin_dir, fixture, out_dir, ckey):
    """One session, several user turns over stream-json input; scores each turn."""
    cond = CONDS[ckey]
    run_dir = os.path.join(out_dir, f"C1-continuity__{ckey}")
    work = os.path.join(run_dir, "work")
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(fixture, work)
    cmd, env = build(cond, plugin_dir, run_dir, ["--input-format", "stream-json"], "2.50")
    turns = []
    with open(os.path.join(run_dir, "stderr.txt"), "w") as se:
        p = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=se, text=True)
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(l) for l in p.stdout] + [lines.put(None)], daemon=True).start()
        broken = False
        for i, (text, should) in enumerate(CONTINUITY):
            path = os.path.join(run_dir, f"turn{i + 1}.jsonl")
            got_result = False
            if not broken:
                try:
                    p.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n")
                    p.stdin.flush()
                except (BrokenPipeError, OSError):
                    broken = True
            with open(path, "w") as so:
                deadline = time.time() + 600
                while not broken and time.time() < deadline:
                    try:
                        line = lines.get(timeout=max(0.1, deadline - time.time()))
                    except queue.Empty:
                        break
                    if line is None:
                        broken = True
                        break
                    so.write(line)
                    try:
                        m = json.loads(line)
                    except ValueError:
                        continue
                    if m.get("type") == "result":
                        got_result = not m.get("is_error")
                        break
            r = analyze(path)
            # A turn after a crash, timeout or error result is a failure, not a pass.
            ok = got_result and r["scout_skill"] == should
            turns.append({"turn": i + 1, "prompt": text, "should_assess": should, "assessed": r["scout_skill"],
                          "hook_fired": r["hook_nudge_fired"], "ok": ok, "completed": got_result,
                          "cost_usd": r["cost_usd"], "skills_used": r["skills_used"]})
            if not got_result:
                broken = True
        with contextlib.suppress(OSError):
            p.stdin.close()
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
    res = {"prompt": "C1-continuity", "cond": ckey, "turns": turns,
           "turns_ok": sum(t["ok"] for t in turns), "turns_total": len(turns)}
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
    cont = "--continuity" in args
    pairs = [(p, c) for p in PROMPTS if any(p.startswith(o) for o in only)
             for c in CONDS if any(c.startswith(x) for x in conds)]
    with cf.ThreadPoolExecutor(jobs) as ex:
        futs = [ex.submit(run_one, plugin_dir, fixture, out_dir, p, c) for p, c in pairs]
        if cont:
            futs += [ex.submit(run_continuity, plugin_dir, fixture, out_dir, c)
                     for c in CONDS if any(c.startswith(x) for x in conds) and CONDS[c]["plugin"]]
        for f in cf.as_completed(futs):
            r = f.result()
            print(json.dumps({k: v for k, v in r.items() if k not in ("final", "all_text", "tools", "_skills",
                                                                      "permission_denials")}), flush=True)


if __name__ == "__main__":
    main()
