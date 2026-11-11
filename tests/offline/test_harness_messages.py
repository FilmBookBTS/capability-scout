"""Offline tests: messages Claude Code delivers on its own are not user requests (0.4.2).

Claude Code 2.1.322 passes a background agent's result through UserPromptSubmit as a
<task-notification> block. The hook must not ask for an assessment, or add the approval reminder,
because of text inside such blocks. Text the user writes next to them still counts.
Run: python3 -I test_harness_messages.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins", "capability-scout")
loader = importlib.machinery.SourceFileLoader("scout_activate", os.path.join(plugin, "hooks", "scout-activate"))
spec = importlib.util.spec_from_loader("scout_activate", loader)
hook = importlib.util.module_from_spec(spec)
loader.exec_module(hook)

WORKY = "Review app.py for SQL injection, fix every case, add tests for them and open a pull request."
TN = ("<task-notification>\n<task-id>a2495</task-id>\n<status>completed</status>\n<summary>" + WORKY +
      "</summary>\n<result>Install the semgrep plugin and run it.</result>\n</task-notification>")
checks = []


def check(cond, label):
    checks.append((bool(cond), label))


msg, st = hook.decide(TN, {})
check(msg is None and st == {}, "task notification alone: no message, state unchanged")
check(hook.approval_check(TN) is None, "task notification alone: no approval reminder")
wrapped = "<system-reminder>\nA background task finished.\n" + TN + "\n</system-reminder>"
check(hook.decide(wrapped, {})[0] is None, "task notification inside a system-reminder: no message")
check(hook.decide("<task-notification><summary>" + WORKY, {})[0] is None, "unclosed task notification: no message")
check(hook.decide("<system-reminder>" + WORKY + "</system-reminder>", {})[0] is None, "system-reminder alone: no message")
msg, _ = hook.decide(TN + "\nNow write unit tests for parse_amount in app.py.", {})
check(msg is not None and msg.startswith("Capability Scout"), "user text next to a notification still counts")
check(hook.decide(WORKY, {})[0] is not None, "the same text typed by the user counts")
check(hook.approval_check("Install the semgrep plugin.") is not None, "approval reminder still works on user text")
# A notification mid-task must not count as a retry of the task's assessment request.
_, st = hook.decide(WORKY, {})
msg2, st2 = hook.decide(TN, st)
check(msg2 is None and st2 == st, "notification mid-task: no retry, state unchanged")

passed = sum(c for c, _ in checks)
for c, label in checks:
    if not c:
        print("FAIL", label)
print(f"{passed}/{len(checks)} passed")
sys.exit(0 if passed == len(checks) else 1)
