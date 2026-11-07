#!/usr/bin/env python3
"""Offline tests for the scoring and isolation rules in tests/live/run_live.py, on made-up transcripts.

No model is called. Run: python3 -I tests/offline/test_live_scoring.py [IGNORED_PLUGIN_PATH]
"""
import json
import os
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(here))
sys.path.insert(0, os.path.join(repo, "tests", "live"))
sys.dont_write_bytecode = True
import run_live as rl  # noqa: E402

results = []


def check(ok, name):
    results.append((bool(ok), name))


def stream(tools, skills=("capability-scout:capability-scout",), hook=False, result=True, error=False):
    lines = [{"type": "system", "subtype": "init", "model": "claude-test-model", "claude_code_version": "9.9.9",
              "skills": list(skills)}]
    if hook:
        lines.append({"type": "system", "subtype": "hook_response",
                      "output": json.dumps({"hookSpecificOutput": {"additionalContext": "Capability Scout: run it"}})})
    for name, inp in tools:
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})
    if result:
        lines.append({"type": "result", "is_error": error, "total_cost_usd": 0.1, "num_turns": 3,
                      "modelUsage": {"claude-test-model": {}}, "result": "done"})
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    f.close()
    r = rl.analyze(f.name)
    os.remove(f.name)
    return r


SK = ("Skill", {"skill": "capability-scout:capability-scout"})
READ = ("Read", {"file_path": "app.py"})

r = stream([SK, READ])
check(r["activated"] and r["scout_before_work"], "skill then Read: activated, scout before work")
r = stream([READ, SK])
check(r["activated"] and not r["scout_before_work"], "Read then skill: activated, not before work")
r = stream([("ToolSearch", {"query": "x"}), SK, READ])
check(r["scout_before_work"], "ToolSearch before the skill does not count as work")
r = stream([("Bash", {"command": "scout-probe digest x"}), READ])
check(not r["activated"] and r["scout_before_work"], "probe only: not activated (Skill call needed), but scout ran first")
r = stream([READ])
check(not r["activated"] and not r["scout_before_work"], "no scout: neither")
r = stream([("Skill", {"skill": "code-review"}), SK])
check(not r["scout_before_work"], "another skill first counts as work")
r = stream([("Skill", {"skill": "capability-scout-chat-text:capability-scout"})], skills=("capability-scout-chat-text:capability-scout",))
check(r["activated"], "chat-text namespace counts as activation")
r = stream([SK], hook=True)
check(r["hook_fired"], "hook reminder detected")
r = stream([SK])
check(not r["hook_fired"], "no hook event: hook_fired false")
check(r["init_model"] == "claude-test-model" and r["model_usage"] == ["claude-test-model"], "model id taken from the session")
check(r["claude_code_version"] == "9.9.9", "Claude Code version taken from the session")
r = stream([SK], result=False)
check(not r["has_result"], "missing result event is detected")

# Isolation rules
check(rl.isolation_problem("A", ["debug", "code-review"]) == "", "arm A with no scout skill: OK")
check("isolation failed" in rl.isolation_problem("A", ["anthropic-skills:capability-scout"]), "arm A with a synced copy: invalid")
check("isolation failed" in rl.isolation_problem("C", ["capability-scout:capability-scout", "anthropic-skills:capability-scout"]),
      "arm C with an extra synced copy: invalid")
check("not loaded" in rl.isolation_problem("B", ["debug"]), "arm B without the plugin skill: invalid")
check(rl.isolation_problem("T", ["capability-scout-chat-text:capability-scout"]) == "", "arm T with the chat text only: OK")
check("isolation failed" in rl.isolation_problem("T", ["capability-scout-chat-text:capability-scout", "capability-scout:capability-scout"]),
      "arm T with the plugin skill too: invalid")

# Schedule: same seed, same order; every combination present once per repeat
a = rl.schedule(["default", "m2"], ["A", "B", "C", "T"], 3, 7)
b = rl.schedule(["default", "m2"], ["A", "B", "C", "T"], 3, 7)
c = rl.schedule(["default", "m2"], ["A", "B", "C", "T"], 3, 8)
key = lambda s: (s["task"]["id"], s["arm"], s["model"], s["rep"])  # noqa: E731
check([key(x) for x in a] == [key(x) for x in b], "same seed gives the same order")
check([key(x) for x in a] != [key(x) for x in c], "a different seed gives a different order")
check(len(set(map(key, a))) == len(a), "no duplicate sessions in the schedule")
_, items = rl.load_tasks()
check(len(a) == len(items) * 4 * 2 * 3, "schedule size = tasks x arms x models x repeats")
check(sum(x["substantive"] for x in items) >= 30 and sum(not x["substantive"] for x in items) >= 10,
      "task set has at least 30 substantive and 10 non-substantive prompts")
ids = {x["id"] for x in items}
check({"P1-security", "P2-unavailable", "P3-missing", "P4-approval", "P5-redundant", "P7-testing", "P8-multistep"} <= ids,
      "the seven substantive phase-1 tasks are included")

# The session command never carries the hook variable in arm C and always isolates the config.
with tempfile.TemporaryDirectory() as d:
    if os.path.exists(rl.CREDENTIALS):
        e = rl.session_env("C", d)
        check("CAPABILITY_SCOUT_HOOK" not in e and e["CLAUDE_CONFIG_DIR"].startswith(d), "arm C: hook variable unset, config isolated")
        check(not any(k in e for k in rl.SYNC_VARS), "arm C: synced skills and plugins turned off")
        with tempfile.TemporaryDirectory() as d2:
            check(rl.session_env("B", d2).get("CAPABILITY_SCOUT_HOOK") == "off", "arm B: hook variable is off")
    else:
        check(True, "credentials not present here; environment checks skipped")
cmd = rl.session_cmd("A", "hi", "default", {"plugin": "/p", "chat": "/c"})
check("--plugin-dir" not in cmd and "--model" not in cmd, "arm A, default model: no plugin, no --model")
cmd = rl.session_cmd("T", "hi", "claude-opus-5-5", {"plugin": "/p", "chat": "/c"})
check(cmd[cmd.index("--plugin-dir") + 1] == "/c" and cmd[cmd.index("--model") + 1] == "claude-opus-5-5",
      "arm T, Opus: chat plugin and exact model id")

failed = [n for ok, n in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
for n in failed:
    print("FAIL", n)
sys.exit(1 if failed else 0)
