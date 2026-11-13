# Analysis plan for the 0.4.5 held-out test (task set ts-7)

The 0.4.5 hook was committed (1c1345d) before ts-7 existed. ts-7 was then written by a separate agent
that saw only a description of the fixture files and of the prompt groups, never the hook, its rules
or earlier task sets, and this plan and [`tests/live/tasks-ts7.json`](../tests/live/tasks-ts7.json)
were committed before any ts-7 prompt was run through any hook. Everything not stated here is as in
[`ANALYSIS_PLAN_0.4.4-HELDOUT.md`](ANALYSIS_PLAN_0.4.4-HELDOUT.md).

## Question

0.4.4 failed its held-out test (ts-6): quick look-ups triggered the skill in 9 of 36 sessions on
Sonnet and 7 of 36 on Opus, all from three prompts the hook treated as work. 0.4.5 widens the
look-up rule, tuned on ts-1 to ts-6 only. Does it keep quick look-ups quiet on new prompts while
real work still starts an assessment?

## Task set ts-7

- 16 quick look-ups (`G01` to `G16`), 4 handed to an agent. Not substantive.
- 12 real tasks (`H01` to `H12`), at least 8 starting with check, show, find, list, grab, look at,
  read, tell me or what; 3 handed to an agent. Substantive.
- 4 controls (`Y01` to `Y04`): thanks, a fact, arithmetic, a slash command.

The groups are as the writing agent labelled them. `G01` happens to be identical to ts-6 `Q01`.

## Runs

Arm C only (plugin 0.4.5, hook on). `claude-sonnet-5-5` and `claude-opus-5-5`, requested by name.
3 repeats. 32 prompts x 2 models x 3 = 192 sessions, one run, shuffled with a recorded seed.
Claude Code 2.1.323.

## Pass criteria

Set before the run. For each model:

1. False triggers on the quick look-ups in at most 5 of 48 sessions.
2. Activation on the real tasks in at least 33 of 36 sessions.
3. False triggers on the controls in at most 1 of 12 sessions.
4. No Capability Scout reminder on any `UserPromptSubmit` event after a session's first, counted with
   `tools/score_hook_events.py`.
5. Offline, before the run: no regression on ts-1 to ts-5 against the 0.4.4 hook
   (`tests/offline/test_precheck_ts6.py`, Part 2).

## Cost and budget

From the ts-6 ledger rows (arm C):

| Part | Sonnet | Opus |
|---|---|---|
| Quick look-ups, 48 sessions | 48 x $0.046 = $2.21 | 48 x $0.099 = $4.75 |
| Real tasks, 36 sessions | 36 x $0.097 = $3.49 | 36 x $0.256 = $9.22 |
| Controls, 12 sessions | 12 x $0.03 = $0.36 | 12 x $0.065 = $0.78 |
| Sum | $6.06 | $14.75 |

Estimate $20.81. Hard budget $30. The project owner asked for the fix to be iterated without
checking in, each live run within a $30 cap, stopping at about $100 of total spend on this work.

## Changes to this plan

- 2026-11-13, after this plan was committed, before any live session: offline, the 1c1345d hook
  treats as work 3 of the 16 quick look-ups (`G07`, `G13`, `G16`), so criterion 1 could pass only if
  the skill ran in at most 5 of the 9 sessions of each model on them; on ts-6 it ran in 7 and 9 of 9
  on such prompts. It also misses one real task (`H05`). The live run was not made, to save the
  budget for a version with a chance to pass. ts-7 has been looked at and is now a development set,
  not a held-out one. The next version is tested on a new held-out set, ts-8, under its own plan.
