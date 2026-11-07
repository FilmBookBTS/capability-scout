# Analysis plan for the 0.4.1 live test (task set ts-2)

This plan and the task set [`tests/live/tasks-ts2.json`](../tests/live/tasks-ts2.json) were committed
before any change to the hook's classifier for 0.4.1. The harness records this plan's SHA-256 in each
run's manifest. Changes made after a run starts are listed at the end of this file.

Everything not stated here is as in [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) (the 0.4.0 plan):
definitions of session, activation, scout before work, false trigger, hook fired and invalid
session; isolation; tools allowed and denied; per-session limits; scoring; Wilson intervals and
their caveat.

## Question

Version 0.4.0 met its activation criteria but missed the false-trigger limit with the hook on:
11 of 36 non-substantive sessions on the default model and 5 of 36 on Opus (ts-1, arm C). In the
ledger, every one of those 16 false triggers is in a session where the hook fired, and the hook
fired on exactly four ts-1 prompts: `N06-convert`, `N10-named-skill`, `N11-named-tool` and
`N12-named-tool`. With the hook off (arm B) there were none.

Version 0.4.1 changes only the hook's classifier, so that it stays quiet on (1) simple unit
conversions and (2) short requests that tell Claude to use a specific other skill, tool or slash
command. Does 0.4.1 bring false triggers within the limit on prompts it was not built from, without
losing activation on substantive work?

## Task set ts-2

New prompts, none copied from ts-1, same fixture (`tests/fixture`).

- 24 substantive tasks:
  - 16 ordinary tasks (reviews, tests, writing, research, planning, and work that needs an outside
    service);
  - 8 near-miss tasks (`NM01` to `NM08`): real work that mentions a tool or skill by name, uses the
    word "convert" on code, or mentions units. They check that the fix does not silence real work.
- 24 non-substantive prompts:
  - 12 plainly trivial: 3 greetings, 5 arithmetic (including 2 unit conversions), 4 single facts;
  - 12 that name a different skill, tool or slash command (`O01` to `O12`).

Prompts are never edited after a run uses them. Any later classifier change is tested on a new set.

## Offline pre-check (no model)

After the 0.4.1 classifier is committed, and before any live session, both the 0.4.0 and the 0.4.1
hook are run on every ts-2 prompt, and the results are recorded in the ledger as an offline row. The
classifier is not changed after it sees ts-2. If the pre-check shows a problem, it is reported, and
a fix would be 0.4.2 on a new task set.

## Arms, models, repeats, order

- Arm C (plugin 0.4.1 as published, hook on) and arm B (plugin 0.4.1, `CAPABILITY_SCOUT_HOOK=off`).
  Arms A and T are not run: 0.4.1 changes nothing they load.
- Models: default (no `--model`) and Opus (`--model claude-opus-5-5`).
- 3 repeats: 48 prompts x 2 arms x 3 = 288 sessions per model, 576 in all.
- Stage 1: default model, arms B and C. Stage 2: Opus, arms B and C. Shuffled within each stage
  with a seed recorded in the manifest. Up to 4 sessions at once.
- After stage 1, if more than 5% of sessions are invalid or any arm saw the wrong skills, the run
  stops and is reported.

## Pass criteria

Set before the run. For arm C, separately for each model, on ts-2:

1. Activation on all 24 substantive tasks of at least 90%, with the lower end of the 95% interval
   at or above 80%.
2. Activation on the 8 near-miss tasks in at least 21 of 24 sessions.
3. Scout before work in at least 90% of the activated sessions.
4. False triggers on at most 10% of all non-substantive sessions (at most 7 of 72).
5. False triggers on at most 10% of the sessions that name another skill or tool (at most 3 of 36).
6. Activation in arm C at least 20 percentage points above arm B, or arm B already at 90% or more.

False triggers are also reported for the 12 plainly trivial prompts on their own line. A missed
criterion is reported as a miss, in the same place and with the same detail as a pass.

## Cost and budget

Estimate from the ts-1 ledger rows of the same arms and models (isolated setup, so no extra factor):

| Arm, model | Mean per substantive session | Mean per non-substantive session | 72 + 72 sessions |
|---|---|---|---|
| C, default | $0.0732 | $0.0422 | 72 x 0.0732 + 72 x 0.0422 = $8.31 |
| C, Opus | $0.1707 | $0.0950 | 72 x 0.1707 + 72 x 0.0950 = $19.13 |
| B, default | $0.0654 | $0.0323 | 72 x 0.0654 + 72 x 0.0323 = $7.04 |
| B, Opus | $0.1453 | $0.0708 | 72 x 0.1453 + 72 x 0.0708 = $15.56 |
| **Total** | | | **$50.04** |

The hard budget is set by the project owner before the run starts and recorded in each manifest.
When it is reached, no new session starts and the report lists every incomplete cell.

## Changes to this plan

None yet.
