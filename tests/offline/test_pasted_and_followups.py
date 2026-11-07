"""Offline tests for v0.3.3: pasted material, prohibitions and follow-ups (no model calls).

These cover the v0.3.2 live trial's known limitations 1 and 2. The trial transcript itself
was not available, so the pasted prompts are rebuilt from LIVE-TRIAL.md (the text that was
pasted) and from the user's own later instruction messages, quoted verbatim.
Run: python3 -I test_pasted_and_followups.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True  # keep the plugin folder free of __pycache__

here = os.path.dirname(os.path.abspath(__file__))
plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "plugins", "capability-scout")
loader = importlib.machinery.SourceFileLoader("scout_activate", os.path.join(plugin, "hooks", "scout-activate"))
spec = importlib.util.spec_from_loader("scout_activate", loader)
hook = importlib.util.module_from_spec(spec)
loader.exec_module(hook)

trial = open(os.path.join(here, "..", "trial", "LIVE-TRIAL.md"), encoding="utf-8").read()


def section(start, end):
    return trial[trial.index(start):trial.index(end)]


SETUP_PASTE = section("## 1. Set up", "## 2. Start the session")
RULES_PASTE = section("## 3. How to approve", "## 5. After the session")
CLEANUP_PASTE = section("**b. Remove only", "**c. Compare")
NEEDS_PASTE = section("## What you need", "## 2. Start the session")

# the user's own messages from later threads, verbatim. They forbid installs.
NO_INSTALL_1 = """CAPABILITY SCOUT — FRESH LOCAL THREAD VERIFICATION
Start a NEW Work locally thread connected to ~/scout-pilot/project. Do not reuse any existing thread.
The purpose is to verify that Capability Scout loads automatically through the project-local plugin mechanism.
Check whether capability-scout@skills-dir is available, whether its skill loads, and whether its activation hook executes on a relevant task.
Perform one harmless, read-only capability assessment.
Do not install software, modify files, change permissions, or repeat previous acceptance tests.
Report PASS, FAIL, or INCOMPLETE with supporting evidence. Stop when finished."""
NO_INSTALL_2 = """Capability Scout appears to have loaded successfully. Preserve that result.
The comparison command was denied because it attempted to write temporary files outside the authorized pilot directory.
Use a simpler, read-only comparison:
diff -rq ~/scout-pilot/plugin/capability-scout ~/scout-pilot/project/.claude/skills/capability-scout
Do not create temporary files or modify configuration.
Then finish confirming how Capability Scout loaded in this fresh local thread, whether its activation hook executed, and whether the skill was actually invoked.
Report the final integration result and stop. No additional tests are necessary."""

# the user's own long request that opened the live trial, verbatim except sections 3-5 left out.
LONG_REQUEST = """CAPABILITY SCOUT v0.3.2 — AUTONOMOUS LIVE-TRIAL PREPARATION AND EXECUTION
The Capability Scout ZIP has already been extracted onto my computer, and `claude plugin validate` returned Validation passed.
The files are located under `~/scout-live-trial/`.
I want you to take responsibility for completing the remaining trial preparation, execution, evidence collection, and verification with as little manual involvement from me as possible.
1. Use existing capabilities
Check whether you can access my Mac through the already established Remote Control connection.
Reuse the existing environment, tools, and authorized folder access. Do not create another infrastructure system or require me to repeat completed setup.
2. Automate the remaining preparation
Where supported, independently complete:

* Verification of the existing test files.
* Baseline configuration snapshots.
* Preparation of the isolated Claude Code session.
* Verification of the session-specific permission rules.
* Preparation of the existing seven-prompt test sequence.

Use the procedures in `LIVE-TRIAL.md`.
Do not install Capability Scout globally, enable it in unrelated Projects, or change persistent account settings.
6. Report
Once all feasible autonomous work is complete, tell me:

* What you completed.
* Whether Capability Scout passed the applicable checks.
* What, if anything, still requires my participation.
* Whether the candidate is ready for a limited Project installation.

Do not begin another extensive testing campaign.
Do not deploy Capability Scout beyond this isolated trial.
Continue autonomously through all authorized work. Stop only when a genuine permission or technical limitation requires my involvement."""

NOT_A_REQUEST = [
    ("pasted setup script", SETUP_PASTE),
    ("pasted trial rules", RULES_PASTE),
    ("pasted cleanup steps", CLEANUP_PASTE),
    ("pasted requirements and setup", NEEDS_PASTE),
]
STILL_A_REQUEST = [
    ("long structured request (user, Oct 17, abridged)", LONG_REQUEST),
    ("ask after a pasted log", "Here is the log from last night:\n" + "\n".join(
        f"2026-10-17T03:{i:02d}:00Z ERROR checkout failed: card_declined order={1000 + i}" for i in range(15))
     + "\nFigure out why checkout failed and which orders are affected."),
    ("ask before a pasted script", "Review this setup script for anything unsafe:\n" + SETUP_PASTE),
    ("short multi-line request", "Review app.py for security issues.\nFocus on SQL injection.\nThen suggest fixes."),
    ("prose lines that start like shell words", "If the tests fail, fix them.\nThen find bugs in utils.c.\nFor each bug, add a test."),
]
APPROVAL_SILENT = [
    ("pasted setup script", SETUP_PASTE),
    ("pasted trial rules", RULES_PASTE),
    ("pasted cleanup steps", CLEANUP_PASTE),
    ("long request that forbids installs", LONG_REQUEST),
    ("forbids installs (verbatim)", NO_INSTALL_1),
    ("forbids temp files (verbatim)", NO_INSTALL_2),
    ("prohibition", "Do not download or install additional software."),
    ("prohibition with work", "Review app.py, but don't install anything."),
    ("prohibition, -ing form", "Check the dependencies without installing or downloading anything."),
    ("never", "Never add a connector without asking me."),
]
APPROVAL_FIRE = [
    ("install after a paste", SETUP_PASTE + "\nNow install semgrep with brew and run it on app.py."),
    ("prohibition then a real request", "Don't touch the config. Install the Sentry plugin."),
]


def main():
    is_request = getattr(hook, "is_request", hook.is_substantive)  # absent before v0.3.3
    failures = []
    for name, p in NOT_A_REQUEST:
        if is_request(p):
            failures.append(("pasted material should not fire", name))
    for name, p in STILL_A_REQUEST:
        if not is_request(p):
            failures.append(("request should still fire", name))
    for name, p in APPROVAL_SILENT:
        if hook.approval_check(p) is not None:
            failures.append(("approval reminder should stay silent", name))
    for name, p in APPROVAL_FIRE:
        if hook.approval_check(p) is None:
            failures.append(("approval reminder should fire", name))

    # The trial's prompts 3-7, with the assessment confirmed whenever it is requested.
    ok_event = {"tool_name": "Skill", "tool_input": {"skill": "capability-scout:capability-scout"},
                "tool_response": {"success": True}}
    s = {}
    p3, s = hook.decide("Review app.py for security issues.", s)
    s = hook.confirm(ok_event, s)
    p4, s = hook.decide("Get the latest unresolved Sentry errors for this project and group them by likely root cause.", s)
    s = hook.confirm(ok_event, s)
    p5, s = hook.decide("Go ahead and install whichever Sentry plugin you recommend, then download semgrep and run it "
                        "against app.py.", s)
    p6, s = hook.decide("Yes, I approve only semgrep@homebrew/core. Nothing else.", s)
    p7, s = hook.decide("ok", s)
    pasted, s = hook.decide(RULES_PASTE, s)
    p8, s = hook.decide("Now write release notes for version 2.0 from the changelog.", s)
    # A first message that only installs is still a new task with no assessment behind it.
    f1, _ = hook.decide("Install the Sentry plugin and set up error alerts for the checkout service.", {})
    checks = [
        (p3 is not None and p4 is not None and "different task" in p4, "prompts 3 and 4 still assess"),
        (p5 is None, "prompt 5 (install what you recommended) does not reassess"),
        (p6 is None, "prompt 6 (exact-item approval) does not reassess"),
        (p7 is None, "prompt 7 (ok) does not fire"),
        (pasted is None, "pasted trial rules mid-session do not fire"),
        (p8 is not None and "different task" in p8, "a genuinely new task still reassesses"),
        (f1 is not None, "an install request as the first task still gets an assessment"),
    ]
    for ok, name in checks:
        if not ok:
            failures.append(("continuity", name))

    total = len(NOT_A_REQUEST) + len(STILL_A_REQUEST) + len(APPROVAL_SILENT) + len(APPROVAL_FIRE) + len(checks)
    print(f"{total - len(failures)}/{total} passed")
    for kind, item in failures:
        print(f"FAIL [{kind}] {item}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
