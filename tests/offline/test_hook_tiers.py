"""How sure the hook is (0.4.5): 'clear' work gets the directive reminder, 'maybe' gets a conditional
one that lets Claude skip a quick look-up, None gets nothing. No model calls.
Run: python3 -I test_hook_tiers.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(HERE)), "plugins", "capability-scout")
loader = importlib.machinery.SourceFileLoader("hook", os.path.join(plugin, "hooks", "scout-activate"))
spec = importlib.util.spec_from_loader("hook", loader)
hook = importlib.util.module_from_spec(spec)
loader.exec_module(hook)

CASES = [
    ("Review utils.py for security issues.", "clear"),
    ("Write pytest tests for the parser in utils.py.", "clear"),
    ("Have a background agent refactor db.py into one module.", "clear"),
    ("Open a PR with these changes.", "clear"),
    ("Send the outage summary to the team.", "clear"),
    ("Check server.py for SQL injection.", "clear"),
    ("find the config loader in main.py and tell me why it's slow", "clear"),
    ("Get the error logs from the staging server.", "maybe"),
    ("Show me the failing tests in CI.", "maybe"),
    ("grab report.txt and turn it into a summary of the root cause", "maybe"),
    ("Check whether utils.py imports re.", None),
    ("have a subagent check whether verbose is set to True in cli.py and report back", None),
    ("how many functions are in utils.py?", None),
    ("thanks!", None),
    ("what port does server.py listen on?", None),
    ("Can you rewrite utils.py so the parser is pure? Keep the API the same.", "clear"),
    ("do a full review of server.py and report back with patches", "clear"),
    ("pull up notes.md and turn it into a status update for execs", "clear"),
    ("Morning! Hope you're well.", None),
    ("Explain what a hook is in one sentence.", None),
]


def main():
    fails = 0
    for prompt, want in CASES:
        got = hook.tier(prompt)
        if got != want:
            fails += 1
            print(f"FAIL {prompt!r}: {got} (want {want})")
    msg, st = hook.decide("Get the error logs from the staging server.", {})
    checks = [(msg == hook.MAYBE_MSG, "maybe gets the conditional reminder"),
              (hook.decide("Now get the error logs from the staging server again.", st)[0] is None,
               "no retry reminder after a conditional one"),
              (hook.decide("Review utils.py for security issues.", {})[0] == hook.FIRST_MSG, "clear gets the directive")]
    for ok, label in checks:
        if not ok:
            fails += 1
            print("FAIL", label)
    n = len(CASES) + len(checks)
    print(f"{n - fails}/{n} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
