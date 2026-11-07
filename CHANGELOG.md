# Changelog

Versions of the Claude Code plugin. Dates are UTC. Earlier versions were not published; their dates come from the project's verification reports.

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
