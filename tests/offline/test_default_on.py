#!/usr/bin/env python3
"""Offline tests for the 0.4.0 default: the hook is on unless CAPABILITY_SCOUT_HOOK is off or 0.

Runs the real hook process with a private plugin data folder. No model calls.
Run: python3 -I tests/offline/test_default_on.py PATH_TO_PLUGIN
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "plugins", "capability-scout")
exe = os.path.join(plugin, "hooks", "scout-activate")
results = []


def check(ok, name):
    results.append((bool(ok), name))


root = tempfile.mkdtemp(prefix="scout-default-on-")
base = {k: v for k, v in os.environ.items() if k not in ("CAPABILITY_SCOUT_HOOK", "EVAL_CAPABILITY_SCOUT_HOOK")}


def run(prompt, sid, hook=None, eval_hook=None, data="d", confirm=None):
    env = dict(base, CLAUDE_PLUGIN_DATA=os.path.join(root, data))
    if hook is not None:
        env["CAPABILITY_SCOUT_HOOK"] = hook
    if eval_hook is not None:
        env["EVAL_CAPABILITY_SCOUT_HOOK"] = eval_hook
    event = {"session_id": sid, "transcript_path": f"/t/{sid}.jsonl", "prompt": prompt}
    args = [sys.executable, "-I", exe]
    if confirm is not None:
        event = {"session_id": sid, "transcript_path": f"/t/{sid}.jsonl", "tool_name": "Skill",
                 "tool_input": {"skill": "capability-scout"}, "tool_response": {"success": confirm}}
        args.append("confirm")
    r = subprocess.run(args, input=json.dumps(event), capture_output=True, text=True, env=env, timeout=20)
    out = r.stdout.strip()
    return r.returncode, (json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else "")


def state_files(data="d"):
    d = os.path.join(root, data, "state")
    return sorted(f for f in os.listdir(d) if f.startswith("state-")) if os.path.isdir(d) else []


try:
    SUBSTANTIVE = "Review app.py for security issues."
    # Default on: no variable set at all.
    rc, msg = run(SUBSTANTIVE, "s1")
    check(rc == 0 and "capability-scout" in msg, "default (variable unset): substantive prompt gets the assessment request")
    rc, msg = run(SUBSTANTIVE, "s2", hook="")
    check("capability-scout" in msg, "empty CAPABILITY_SCOUT_HOOK counts as default on")
    for v in ("on", "1", "ON", "yes", "anything-else"):
        rc, msg = run(SUBSTANTIVE, "s-" + v, hook=v)
        check("capability-scout" in msg, f"CAPABILITY_SCOUT_HOOK={v!r} leaves the hook on")
    # Opt-out.
    for v in ("off", "0", "OFF", " Off ", "0 "):
        before = state_files("optout")
        rc, msg = run(SUBSTANTIVE, "o-" + v.strip(), hook=v, data="optout")
        check(rc == 0 and msg == "", f"CAPABILITY_SCOUT_HOOK={v!r} turns the hook off (no message)")
        check(state_files("optout") == before, f"CAPABILITY_SCOUT_HOOK={v!r} writes no state")
    rc, msg = run("Go ahead and install semgrep and run it.", "o-install", hook="off", data="optout")
    check(msg == "", "opted out: no approval reminder either")
    rc, msg = run("", "o-confirm", hook="off", data="optout", confirm=True)
    check(rc == 0 and msg == "" and state_files("optout") == [], "opted out: confirm event writes no state")
    rc, msg = run(SUBSTANTIVE, "o-eval", hook="off", eval_hook="on", data="evalon")
    check("capability-scout" in msg, "EVAL_CAPABILITY_SCOUT_HOOK=on still turns it on for plugin eval")
    # Trivial and non-substantive prompts stay quiet under the default.
    QUIET = ["What is 17 x 23?", "hi", "thanks", "ok", "Good morning!", "What is the capital of France?",
             "What does HTTP stand for?", "How many days are in a leap year?", "Explain what a hook is in one sentence."]
    for i, p in enumerate(QUIET):
        rc, msg = run(p, f"q{i}", data="quiet")
        check(rc == 0 and msg == "", f"default on, non-substantive stays quiet: {p!r}")
    check(state_files("quiet") == [], "quiet prompts create no state file")
    # Known limitation, recorded rather than hidden: a short imperative with a concrete object
    # ("convert ... miles") is classified as work. 0.4.0 keeps the existing classifier unchanged.
    rc, msg = run("Convert 5 miles to kilometers.", "known1", data="known")
    check("capability-scout" in msg, "KNOWN false trigger still fires (classifier unchanged): 'Convert 5 miles to kilometers.'")
    # State storage under the default.
    rc, msg = run(SUBSTANTIVE, "st", data="store")
    files = state_files("store")
    check(len(files) == 1, "default on: one state file per session")
    d = os.path.join(root, "store", "state")
    check(stat.S_IMODE(os.stat(d).st_mode) == 0o700, "state folder is 0700")
    if files:
        f = os.path.join(d, files[0])
        check(stat.S_IMODE(os.stat(f).st_mode) == 0o600, "state file is 0600")
        st = json.load(open(f))
        check(isinstance(st, dict) and set(st) <= {"task", "requested_total", "confirmed_total", "last_kw"}
              and json.dumps(st).find("Review app.py") == -1,
              "state holds only task keywords and counters, not the prompt text")
    rc, _ = run("", "st", data="store", confirm=True)
    rc, msg = run("Also check whether the SQL in app.py is injectable.", "st", data="store")
    check("capability-scout" not in msg, "confirmed assessment: same-task follow-up is not asked again")
    rc, msg = run("", "st2", data="store", confirm=None)  # empty prompt
    check(rc == 0 and msg == "", "empty prompt: silent")
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [n for ok, n in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
for n in failed:
    print("FAIL", n)
sys.exit(1 if failed else 0)
