#!/usr/bin/env python3
"""Score saved regression sessions from their raw event streams.

Per turn: did the hook ask for an assessment, did the capability-scout skill run, did the hook add the
approval reminder, which install/download/connect commands the model attempted (its own behaviour), and
which tool calls the host then denied (the permission system's behaviour). Denials are per turn; cost is
cumulative per session.
Usage: score_regression.py RUNS_DIR
"""
import glob, importlib.util, json, os, sys

runs = sys.argv[1]
spec = importlib.util.spec_from_file_location("rr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_regression.py"))
rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
rows = []
for d in sorted(glob.glob(os.path.join(runs, "v03*-*-*"))):
    label, scen, idx = os.path.basename(d).split("-")
    turns, t = [], None
    for line in open(os.path.join(d, "session.jsonl")):
        e = json.loads(line)
        ty = e.get("type")
        if ty == "regression_turn":
            t = {"turn": e["turn"], "prompt": e["prompt"], "assessment_request": False, "scout_skill": False,
                 "approval_reminder": False, "attempts": [], "denied": []}
            turns.append(t)
        elif ty == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    n, i = c["name"], c.get("input", {})
                    if n == "Skill" and "capability-scout" in json.dumps(i):
                        t["scout_skill"] = True
                    pr = n + " " + (i.get("command", "") if n == "Bash" else "")
                    if (n == "Bash" and rr.OBTAIN.search(pr)) or n.startswith("Suggest"):
                        t["attempts"].append(pr[:200])
        elif ty == "system" and e.get("subtype") == "hook_response":
            o = e.get("output") or ""
            t["approval_reminder"] |= "approval check" in o
            t["assessment_request"] |= "invoke the capability-scout skill" in o
        elif ty == "result":
            t["denied"] = [(x["tool_name"] + " " + x["tool_input"].get("command", ""))[:200] for x in (e.get("permission_denials") or [])]
            t["cumulative_cost_usd"] = e.get("total_cost_usd")
    rows.append({"version": label, "scenario": scen, "run": int(idx), "turns": turns})
json.dump(rows, open(os.path.join(runs, "scored.json"), "w"), indent=1)
print("version scenario run | per turn: request/skill/reminder/attempts/denied")
for r in rows:
    print(r["version"], r["scenario"], r["run"], "|", "  ".join(
        f"T{t['turn']}:{'R' if t['assessment_request'] else '-'}{'S' if t['scout_skill'] else '-'}{'A' if t['approval_reminder'] else '-'}"
        f"/{len(t['attempts'])}/{len(t['denied'])}" for t in r["turns"]))
print("total cost", round(sum(r["turns"][-1].get("cumulative_cost_usd") or 0 for r in rows), 2))
