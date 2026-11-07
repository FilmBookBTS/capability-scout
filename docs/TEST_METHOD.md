# How Capability Scout is tested

Every test result is a row in [`results/ledger.csv`](../results/ledger.csv), one row per
session or test suite. [`tools/summarize.py`](../tools/summarize.py) builds
[`results/RESULTS.md`](../results/RESULTS.md) and the chart from the ledger and nothing else.

## Kinds of test

| Kind | What it checks | Calls a model? | Where |
|---|---|---|---|
| Offline suites | the hook's rules, its stored state, the run guards and the live harness's scoring | no | [`tests/offline/`](../tests/offline) |
| Live activation test | whether the skill runs at the start of substantive work, and stays quiet otherwise | yes | [`tests/live/`](../tests/live), plan in [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) |
| Chat protocol | the chat edition in claude.ai, by hand | yes | [`CHAT_PROTOCOL.md`](CHAT_PROTOCOL.md) |
| Earlier tests | phase 1 and versions 0.2.0 to 0.3.3 | yes, except 0.3.3 | rows named `legacy-...` in the ledger; files in [`tests/legacy/`](../tests/legacy) and [`tests/live-legacy/`](../tests/live-legacy) |

## Offline suites

Run them all, and record the result in the ledger, with:

```
python3 -I tools/run_offline.py <label>
```

Each suite can also run on its own, for example
`python3 -I tests/offline/test_default_on.py plugins/capability-scout`.

| Suite | Checks |
|---|---|
| `test_default_on.py` | the hook is on by default; `off` and `0` turn it off; quiet prompts stay quiet; what the state file holds |
| `test_hook_classifier.py` | which messages count as work, and when a new task starts |
| `test_pasted_and_followups.py` | pasted material and follow-ups do not start a new assessment |
| `test_state_and_storage.py` | the state file's permissions, locking, retries and pruning |
| `test_guards.py` | the run guards (below), in a throwaway copy of the repository |
| `test_live_scoring.py` | the live harness's scoring and isolation rules, on made-up transcripts |
| `test_precheck_ts2.py` | reports which ts-2 prompts the hook treats as work, next to the 0.4.0 hook; it does not judge (see [`ANALYSIS_PLAN_0.4.1.md`](ANALYSIS_PLAN_0.4.1.md)) |

**Check counts can differ by machine.** `test_live_scoring.py` has three checks that need
Claude Code sign-in credentials (`~/.claude/.credentials.json`). Without them, the three are
replaced by one check that says they were skipped, so the suite reports 27 of 27 instead of 29 of
29. Both are passes.

## Live activation test

[`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) was committed before the first live session. It defines
activation, "scout before work" and false triggers, the arms, the task set and the pass
criteria.

In short:

- Each session is a new, non-interactive Claude Code process (`claude -p`) with one prompt, in a
  fresh copy of [`tests/fixture`](../tests/fixture).
- Each session has its own empty Claude Code configuration folder, so no skill or plugin from the
  test machine's own setup can load. The harness checks each session's startup event for the
  right skills and marks a session invalid if they are wrong.
- No connector's tools are loaded. Claude Code's `ListConnectors` tool can still list the
  connectors of the signed-in account, so a reply may mention them.
- File edits, installs, downloads and outward actions are denied.
- The task set is [`tests/live/tasks.json`](../tests/live/tasks.json). Its prompts are never
  edited after a run uses them; a change makes a new task set version.

Run it with `python3 -I tests/live/run_live.py run --label <label> --seed <n> --budget-usd <x>`.
`run_live.py plan` prints the session count and a cost estimate without calling a model.

## Run guards

Both harnesses use [`tools/guards.py`](../tools/guards.py):

1. **A run refuses to start** unless the working tree is clean and the plugin, task set, analysis
   plan and harness are committed. The commit is recorded in the run's manifest.
2. **Rows are never changed.** Before and after a run, the ledger must start with exactly the
   committed ledger and with every backup copy. A changed or removed row stops the run.
3. **Records before success.** Each run writes `results/runs/<run_id>/manifest.json` and its
   ledger rows before it reports success.
4. **Backups.** The ledger and the run folder are copied to every folder listed in
   `results/backup_targets.json` (kept out of the repository; see the `.example` file) and
   checked by hash. If any copy fails, the run prints `NOT BACKED UP` and exits with an error.

Raw session transcripts (`results/runs/*/raw/`) are kept in the backup folders, not in the
repository.

## Earlier tests

Rows imported from earlier tests are named `legacy-...`. Their `notes` column says how good the
evidence is. For example, phase-1 rows are summary rows only, because the session transcripts
were not kept. Later findings about these rows are in
[`results/annotations.csv`](../results/annotations.csv); the rows themselves are not edited.
Figures quoted in earlier reports are checked against the ledger in
[`results/claims.csv`](../results/claims.csv).

The phase-1 hook, skill text and harness were recovered from the record of the session that
ran them: see [`tests/legacy/phase1/README.md`](../tests/legacy/phase1/README.md).
