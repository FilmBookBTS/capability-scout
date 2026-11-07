# Contributing

Thank you for taking the time to help.

## Reporting a problem

Open an issue with the **Bug report** template. Say which edition you use (chat or Claude Code),
the version, the exact message you sent, what you expected and what happened. A short excerpt of
the reply helps. Remove anything private before you post it.

For a security problem, do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## Changes that are welcome

- Fixes for cases where the skill runs when it should not, or does not run when it should, with
  the message that shows the problem.
- Clearer wording in the instructions or the docs.
- New test prompts. Add them as a new task set version in `tests/live/tasks.json`; do not edit
  prompts a recorded run already used.

## Rules for test results

- Results are rows in `results/ledger.csv`. Rows are never edited or removed. Corrections go in
  `results/annotations.csv`.
- `results/RESULTS.md` and the chart are generated: run `python3 -I tools/summarize.py` and
  commit the output. `python3 -I tools/summarize.py --check` must pass.
- Run the offline tests before you send a change: `python3 -I tools/run_offline.py <label>`.

## Things to avoid

- Changes that make the skill install, download or connect anything without the user's
  approval.
- Claims in the README that the ledger does not back.
