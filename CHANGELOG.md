# Changelog

Versions of the Claude Code plugin. Dates are UTC. Earlier versions were not published; their dates come from the project's verification reports.

## 0.4.6 - unreleased

- A request to run a slash command with a verb in front ("run /code-review on my current changes") is recognized as naming its tool, like "/code-review" alone.
- "pls" and "please" at the start are treated as a polite opener, as "Could you" already was.
- Includes the 0.4.3 to 0.4.5 changes below.

## 0.4.5 - not released

- Quick look-ups are recognized more broadly: ones that start with "which", "what" or "how many" ("check which port app.py runs on"), ones that end by asking for the answer ("... and tell me its src", "... and report back"), and ones handed to an agent. An answer clause that asks for a judgement or a change ("... and tell me how to fix it") still counts as work.
- Two levels of reminder. Clear work (long, several steps, or a request that is not a question and asks for a judgement or for something to be made, such as fix, write or review) gets the directive reminder as before. A question, or a request that only retrieves something ("Get the error logs from the staging server"), gets a conditional reminder when the word rules count it as work: run the skill if this is substantive work, skip it for a quick look-up. So does a request to make something that the word rules miss ("grab notes.txt and turn it into a postmortem"). No retry reminder follows a conditional one.
- Includes the 0.4.3 and 0.4.4 changes below.
- Live test on the held-out set ts-9 (192 sessions): quick look-ups 3 and 2 of 48 (limit 5), real tasks 36 of 36 on both models, but controls 3 of 12 on both (limit 1), all from "run /code-review on my current changes". Not released; see [docs/ANALYSIS_PLAN_0.4.5-TS9.md](docs/ANALYSIS_PLAN_0.4.5-TS9.md).

## 0.4.4 - not released

- A quick look-up on one named file ("Show the size of CHANGELOG.md.", "Check whether app.py imports os.") is not treated as work. It must be short, one step, and name one file and nothing else; a request that asks for a judgement ("Check whether app.py is secure") or about all of something still counts.
- Includes the 0.4.3 changes below.
- Live tests: passed all criteria on ts-5 (132 sessions), but on the held-out set ts-6 (168 sessions), written separately from the rule, false triggers on quick look-ups were 9 of 36 sessions on Sonnet and 7 of 36 on Opus, against a limit of 4. Not released; see [docs/ANALYSIS_PLAN_0.4.4-HELDOUT.md](docs/ANALYSIS_PLAN_0.4.4-HELDOUT.md).

## 0.4.3 - not released

- A request to hand a job to a background agent or subagent ("Launch a background agent to count the words in para.txt ...") is judged by the job itself, as if the user had asked for it directly. Real work handed to an agent still counts.
- "Report back" no longer counts as naming a report.
- Live test on a new task set (ts-4), 120 sessions: 4 of 5 criteria passed. False triggers on small jobs handed to an agent were 6 of 24 sessions per model, against a limit of 2, all from two quick file look-ups. Not released; fixed in 0.4.4. Details in [docs/ANALYSIS_PLAN_0.4.3.md](docs/ANALYSIS_PLAN_0.4.3.md).

## 0.4.2 - 2026-11-11

- The hook ignores messages that Claude Code delivers on its own through the prompt hook, such as a background agent's result (`<task-notification>`). Before, it could ask for an assessment on one (seen once in the 0.4.1 test, with Claude Code 2.1.322).
- Requests that start with "Search", "Look up" or "Browse" now count as work, so "Search the web for ... and tell me whether app.py is affected" starts an assessment.
- Retested live on 2026-11-11 on a new task set, ts-3, for these two cases only (102 sessions, Claude Code 2.1.322, Sonnet 5.5 and Opus 5.5 requested by name, hook on). Web-research tasks: the skill ran in 24 of 24 sessions on each model. Messages from background agents: none of 24 got a reminder. Controls: 0 of 18 false triggers on each model. All four criteria set before the run were met. Short requests to start a background agent are still treated as work (6 of 9 sessions on each model). See [docs/ANALYSIS_PLAN_0.4.2.md](docs/ANALYSIS_PLAN_0.4.2.md).

## 0.4.1 - 2026-11-11

- The hook no longer treats a unit conversion ("Convert 5 miles to kilometers.") as work.
- The hook no longer treats a short, single-step request that names the skill, tool or slash command to use ("Use the code-review skill on app.py.", "Use Grep to find ...", "/simplify utils.py") as work, since the user has already picked the capability. Longer or multi-step requests that mention a tool still count.
- These were the only prompts the 0.4.0 hook fired on among the non-substantive prompts of its live test, and all 16 of its false triggers were on them.
- Tested live on 2026-11-11 on a new task set, ts-2 (576 sessions, Claude Code 2.1.322, Sonnet 5.5 and Opus 5.5 requested by name). With the hook on, the skill ran in 69 of 72 substantive sessions on each model and on 0 of 72 non-substantive prompts on each model. All six pass criteria set before the run were met on both models. See [docs/ANALYSIS_PLAN_0.4.1.md](docs/ANALYSIS_PLAN_0.4.1.md) and [results/RESULTS.md](results/RESULTS.md).

## 0.4.0 - 2026-11-05

- **Changed default: the activation hook is now on.** Before 0.4.0 it did nothing unless `CAPABILITY_SCOUT_HOOK` was set to `on`. Now it runs unless `CAPABILITY_SCOUT_HOOK` is `off` or `0`. To turn it off, add `"env": {"CAPABILITY_SCOUT_HOOK": "off"}` to your Claude Code `settings.json`, or set the variable before starting Claude Code. See [docs/HOOK.md](docs/HOOK.md).
- The rules for which messages count as substantive work are unchanged.
- `plugin.json` now has `author`, `homepage`, `repository` and `license`.
- New offline tests for the default, opting out, quiet prompts and state storage (`tests/offline/test_default_on.py`).
- Tested live on 2026-11-05 and 2026-11-06 (1,008 sessions, Claude Code 2.1.318). With the hook on, the skill ran in 90 of 90 substantive sessions on each model. It also ran on 11 of 36 non-substantive prompts with the default model and 5 of 36 with Opus, which misses the 10% limit set before the test. See [results/RESULTS.md](results/RESULTS.md).

## 0.3.3 - 2026-10-27

- Pasted material (code, commands, quotes, tables, long documents) no longer triggers the hook.
- Messages that forbid installs no longer trigger the approval reminder.
- Approving or acting on items already proposed counts as a follow-up, not a new task.
- Documented the cache files Claude Code itself writes during a marketplace search.
- Tested offline only.

## 0.3.2 - 2026-10-17

- "Get", "list", "show" and "pull up" requests that name something concrete now start an assessment.
- The skill defines approval as two steps: propose one named item, then act only after the user confirms that item.
- The hook adds an approval reminder when a message asks to install, download, enable or connect something.

## 0.3.1 - 2026-10-17

- An assessment is recorded only when Claude Code reports an explicitly successful capability-scout skill call.
- State locking fails closed, and state files must be readable by the owner only.

## 0.3.0 - 2026-10-17

- An assessment request is no longer treated as a completed assessment; the hook retries at most twice per task.
- Private, owner-only state storage with atomic writes and locking (`lib/scout_store.py`).
- The skill splits a task into parts and picks one specialist per part, and always checks the directory once for review, audit, test or security tasks.

## 0.2.0 - 2026-10-17

- Replaced the 8-word rule with a classifier for short but substantive requests.
- The hook can ask for a new assessment when a different task starts in the same session.
- Removed the experimental "nudge" and "digest" hook modes.
