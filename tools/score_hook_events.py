#!/usr/bin/env python3
"""Count Capability Scout reminders on later UserPromptSubmit events (criterion 2 of
docs/ANALYSIS_PLAN_0.4.2.md). Reads the raw transcripts of one run, which are kept in the backup
folders, not in the repository.

Usage: python3 -I tools/score_hook_events.py RUN_FOLDER
RUN_FOLDER holds manifest.json and raw/<seq>/stream.jsonl.
For each session: how many UserPromptSubmit events there were, how many after the first carried a
Capability Scout reminder, and whether a background agent reported back (a task_notification event).
"""
import json
import os
import sys


def session(path):
    ups, later_scout, notified = 0, 0, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("type") != "system":
                continue
            if m.get("subtype") == "task_notification":
                notified += 1
            if m.get("subtype") == "hook_response" and m.get("hook_event") == "UserPromptSubmit":
                ups += 1
                if ups > 1 and "Capability Scout" in (m.get("output") or ""):
                    later_scout += 1
    return ups, later_scout, notified


def main(argv):
    run = argv[1]
    man = json.load(open(os.path.join(run, "manifest.json")))
    order = {str(seq).zfill(4): (task, arm, model) for seq, task, arm, model, _rep in man["order"]}
    totals = {}
    for seq in sorted(os.listdir(os.path.join(run, "raw"))):
        p = os.path.join(run, "raw", seq, "stream.jsonl")
        if not os.path.exists(p) or seq not in order:
            continue
        task, arm, model = order[seq]
        ups, later, notified = session(p)
        t = totals.setdefault(model, [0, 0, 0, 0, 0])
        t[0] += 1
        t[1] += later
        t[2] += max(0, ups - 1)
        if task.startswith("B"):
            t[3] += 1
            t[4] += notified > 0
        print(f"{seq} {task:<22} {model:<18} prompt-events={ups} later-with-reminder={later} notifications={notified}")
    for model, (n, later, extra, b, bstarted) in totals.items():
        print(f"\n{model}: {n} sessions; {extra} later UserPromptSubmit events, {later} with a reminder; "
              f"background-agent prompts: {bstarted} of {b} sessions had a background agent report back")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
