"""Offline tests for the activation hook's decisions (no model calls).

Prompt set follows skill-creator's trigger-eval advice: realistic should-fire
prompts, including short ones, plus near-miss should-not-fire prompts.
Run: python3 -I test_hook_classifier.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import os
import sys

plugin = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins", "capability-scout")
loader = importlib.machinery.SourceFileLoader("scout_activate", os.path.join(plugin, "hooks", "scout-activate"))
spec = importlib.util.spec_from_loader("scout_activate", loader)
hook = importlib.util.module_from_spec(spec)
loader.exec_module(hook)

SHOULD_FIRE = [
    "Review app.py for security issues.",          # 5 words: missed by the old 8-word rule
    "Fix the failing tests.",
    "Set up Sentry for this repo.",
    "Triage today's PagerDuty incidents.",
    "Add CI to this project.",
    "Audit our dependencies.",
    "Draft release notes from the last 20 commits.",
    "Debug the 500 error on /orders.",
    "Write unit tests for parse_amount in app.py.",
    "Open a PR with these changes.",
    "Pull our open Linear issues and summarize the blocked ones.",
    "Make the landing page copy clearer and check it for accessibility problems.",
    "Migrate the database schema to Postgres.",
    "Find the best plugin for Stripe and install it.",
    "Rewrite para.txt so it sounds less like AI wrote it.",
    "Download and run the latest semgrep binary against app.py.",  # missed in live run 2; fixed
    "Send the outage summary to the team.",
    "Delete the stale branches.",
    # From the v0.2.0 source review: false negatives.
    "Find bugs in utils.c",
    "Look through server logs and tell me why checkout failed",
    "Figure out why refunds in app.py come out wrong for some amounts.",
    "How should we test parse_amount in app.py?",
    # From the v0.3.0 re-review: polite requests and "the <artifact>" questions.
    "Could you fix the failing tests?",
    "Can you set up Sentry for the project?",
    "Can you triage the open incidents?",
    "Should we migrate the database to Postgres?",
    # From the v0.3.1 interactive trial: retrieval verbs (turn 4 was missed).
    "Get the latest unresolved Sentry errors for this project and group them by likely root cause.",
    "Get the error logs from the staging server.",
    "List all open pull requests in the repo.",
    "List the dependencies in package.json.",
    "Show me the failing tests in CI.",
    "Show the slowest endpoints in the API.",
    "Pull up last week's incident reports.",
    "Can you list the open tickets in Linear?",
    "Could you get the crash reports for the iOS app?",
    # 0.4.1: real work that mentions a tool, a skill, units or "convert" still counts. Written for
    # 0.4.1; none of these is a ts-2 prompt, which stays held out for the live test.
    "Use the Grep tool to find every TODO in the repo, then turn each one into a ticket.",
    "Use Read on CHANGELOG.md and write release notes for customers.",
    "Run the linter on app.py and fix every warning it reports.",
    "Convert the build pipeline from Jenkins to GitHub Actions.",
    "Convert this CSV export to JSON and add a test for it.",
    "Add unit conversion for kilograms to pounds in the shipping service.",
    "Use the code-review skill on app.py; then fix whatever it finds and open a PR.",
    "Review app.py with Grep and Read, and explain each security problem you find.",
    # 0.4.2: requests to search or look things up count as work. None of these is a ts-3 prompt.
    "Search the web for the best Python linters and recommend one for this repo.",
    "Search for breaking changes in Django 5 and list what our app needs to change.",
    "Look up the latest Django release and check our requirements.",
    "Browse the docs for pytest fixtures and suggest how to restructure our tests.",
    # 0.4.3: real work handed to an agent still counts. None of these is a ts-4 prompt.
    "Launch a background agent to review the API for auth bugs and write fixes.",
    "Have a subagent draft the quarterly report from data.csv.",
    "Have two agents: one reviews utils.py for bugs, the other writes tests for it.",
    "Use agents to migrate the database schema to Postgres.",
    "Write the weekly report for the team.",
    "Report back when the deploy finishes and summarize the logs.",
]
SHOULD_NOT_FIRE = [
    "What is 17 times 23?",
    "thanks!",
    "ok, go ahead",
    "yes",
    "What's the capital of France?",
    "Explain what a closure is.",
    "Who wrote Dune?",
    "2+2",
    "What does HTTP 404 mean?",
    "hello there",
    # From the v0.2.0 source review: false positives.
    "How do I write a test in pytest?",
    "Compare Python and Go",
    "What are the main differences between optimistic and pessimistic locking, and when would a team "
    "reasonably prefer one approach over the other in a typical web application?",
    # Retrieval verbs on their own are follow-ups, not new work.
    "Show me again.",
    "Show me that.",
    "List them.",
    "Get it?",
    "Can you show me again?",
    "Show me what you mean.",
    "List them all please.",
    "Get that for me.",
    "Pull it up again.",
    "ok, show me",
    "Show the rest.",
    "How do I get started?",
    "What does list comprehension mean?",
    # 0.4.1: unit conversions and short requests that name the capability to use. The first five
    # are the ts-1 prompts the 0.4.0 hook fired on (false triggers in the 0.4.0 live test).
    "Convert 5 miles to kilometers.",
    "Use the code-review skill to review app.py.",
    "Use the Grep tool to find every line in app.py that contains SELECT.",
    "Use the Read tool to show me para.txt.",
    "Use the simplify skill on app.py.",
    "Convert 2.5 liters to cups.",
    "convert 30 C to F",
    "Use the frontend-design skill on index.html.",
    "Use Glob to list the Python files.",
    "/simplify utils.py",
    "Could you use the Bash tool to print the working directory?",
    # 0.4.3: a small job handed to an agent is judged as the job itself. The first two are the ts-3
    # prompts the 0.4.2 hook treated as work.
    "Launch a background agent to count the words in para.txt and tell me the number when it finishes.",
    "Have a background agent list the files in this folder and report back.",
    "List the files in this folder and report back.",
    "Start a background agent that prints today's date.",
    "Spin up a subagent to tell me how many TODOs are in utils.py.",
]

# Requests to obtain something get the approval reminder; other prompts don't.
APPROVAL_FIRE = [
    "Go ahead and install whichever Sentry plugin you recommend, then download semgrep and run it against app.py.",
    "Just get a scanner and run it on app.py.",
    "Install the Sentry plugin.",
    "Can you download semgrep?",
    "Add the Sentry connector.",
    "pip install requests",
    "Set up the GitHub MCP for this repo.",
    "Grab whatever linter you think is best and run it.",
]
APPROVAL_SILENT = [
    "How do I install semgrep?",
    "Review app.py for security issues.",
    "Get the latest unresolved Sentry errors for this project and group them by likely root cause.",
    "List the dependencies in package.json.",
    "Add CI to this project.",
    "Add unit tests for parse_amount in app.py.",
    "Add a new server route for refunds.",
    "ok",
    "Don't change anything yet.",
]


def main():
    failures = []
    for p in SHOULD_FIRE:
        if not hook.is_substantive(p):
            failures.append(("should fire", p))
    for p in SHOULD_NOT_FIRE:
        if hook.is_substantive(p):
            failures.append(("should not fire", p))

    approval_check = getattr(hook, "approval_check", lambda p: None)  # absent before v0.3.2
    for p in APPROVAL_FIRE:
        if approval_check(p) is None:
            failures.append(("approval reminder should fire", p))
    for p in APPROVAL_SILENT:
        if approval_check(p) is not None:
            failures.append(("approval reminder should stay silent", p))

    # Session continuity (assessment confirmed by the PostToolUse event each time it is requested).
    ok_event = {"tool_name": "Skill", "tool_input": {"skill": "capability-scout:capability-scout"},
                "tool_response": {"success": True}}
    state = {}
    m1, state = hook.decide("Review app.py for security issues.", state)
    state = hook.confirm(ok_event, state)
    m2, state = hook.decide("Also review app.py for SQL injection issues specifically.", state)
    m2b, state = hook.decide("Now check the SQL queries for injection.", state)
    m3, state = hook.decide("Now write release notes for version 2.0 from the changelog.", state)
    state = hook.confirm(ok_event, state)
    m4, state = hook.decide("thanks", state)
    m5, state = hook.decide("Write a postmortem for the checkout outage.", state)
    state = hook.confirm(ok_event, state)
    # The v0.3.1 trial sequence: a retrieval request after a review is a new task; "ok" is not.
    t = {}
    t1, t = hook.decide("Review app.py for security issues.", t)
    t = hook.confirm(ok_event, t)
    t2, t = hook.decide("Get the latest unresolved Sentry errors for this project and group them by likely root cause.", t)
    t = hook.confirm(ok_event, t)
    t3, t = hook.decide("Show me the full stack trace again.", t)
    t4, t = hook.decide("ok", t)
    checks = [
        (m1 is not None and "before any other tool call" in m1, "first substantive prompt fires"),
        (m2 is None, "follow-up on a confirmed task does not re-fire"),
        (m2b is None, "drifting follow-up (low word overlap) does not re-fire"),
        (m3 is not None and "different task" in m3, "a materially different task re-fires"),
        (m4 is None, "acknowledgement never fires"),
        (m5 is not None, "a new task sharing only a verb with the last one re-fires"),
        (state.get("confirmed_total") == 3 and state.get("requested_total") == 3, "requests and confirmations counted"),
        (t1 is not None and t2 is not None and "different task" in t2, "trial turn 4 (Get ... Sentry errors) re-fires as a new task"),
        (t3 is None, "a retrieval follow-up on the same task does not re-fire"),
        (t4 is None, "trial turn 6 (ok) does not fire"),
    ]
    for ok, name in checks:
        if not ok:
            failures.append(("continuity", name))

    total = len(SHOULD_FIRE) + len(SHOULD_NOT_FIRE) + len(APPROVAL_FIRE) + len(APPROVAL_SILENT) + len(checks)
    print(f"{total - len(failures)}/{total} passed")
    for kind, item in failures:
        print(f"FAIL [{kind}] {item}")
    old_rule_misses = [p for p in SHOULD_FIRE if len(p.split()) < 8]
    print(f"Old 8-word rule would have missed {len(old_rule_misses)}/{len(SHOULD_FIRE)} should-fire prompts")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
