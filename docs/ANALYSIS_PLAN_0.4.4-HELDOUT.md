# Analysis plan for the 0.4.4 held-out test (task set ts-6)

This plan and [`tests/live/tasks-ts6.json`](../tests/live/tasks-ts6.json) were committed before any
ts-6 prompt was run through any version of the hook. The hook is the 0.4.4 hook already tested on
ts-5 (commit 79b9b7a) and is not changed for this test. Everything not stated here is as in
[`ANALYSIS_PLAN_0.4.4.md`](ANALYSIS_PLAN_0.4.4.md).

## Question

ts-5 and the 0.4.4 rule were written in the same working session, so its clean result (0 of 30
false triggers, 24 of 24 activation per model) may flatter the rule. Does 0.4.4 hold up on prompts
written by someone who never saw the rule? And do the two ts-4 prompts behind the 0.4.3 miss stay
quiet in live sessions?

## Task set ts-6

- 12 quick look-ups (`Q01` to `Q12`), 3 of them handed to an agent. Not substantive.
- 10 real tasks (`W01` to `W10`), at least 6 starting with check, show, find, list, look at or
  tell me; 2 handed to an agent. Substantive.
- 4 controls (`X01` to `X04`): a greeting, a fact, arithmetic, a request naming another skill.
- 2 repeats (`R01`, `R02`): the ts-4 prompts `D05-size` and `D07-title-tag`, verbatim.

The Q, W and X prompts were written by a separate agent, given only a description of the five
fixture files and of the three groups, with no access to the hook, its rules, earlier task sets or
any file. They are used exactly as returned. The groups are as that agent labelled them.

## Runs

Arm C only (plugin 0.4.4, hook on). `claude-sonnet-5-5` and `claude-opus-5-5`, requested by name.
3 repeats. 28 prompts x 2 models x 3 = 168 sessions, one run, shuffled with a recorded seed.

## Pass criteria

Set before the run. For each model:

1. False triggers on the quick look-ups in at most 4 of 36 sessions.
2. Activation on the real tasks in at least 27 of 30 sessions.
3. False triggers on the controls in at most 1 of 12 sessions.
4. False triggers on the two ts-4 repeats in at most 1 of 6 sessions.
5. No Capability Scout reminder on any `UserPromptSubmit` event after a session's first, counted with
   `tools/score_hook_events.py`.

The offline result of the hook on ts-6 is recorded after the commit of this plan and before the run,
and does not change the hook.

## Cost and budget

From the ts-5 and ts-4 ledger rows (arm C), rounded up for the agent prompts:

| Part | Sonnet | Opus |
|---|---|---|
| Quick look-ups, 36 sessions | 36 x $0.045 = $1.62 | 36 x $0.09 = $3.24 |
| Repeats, 6 sessions | 6 x $0.063 = $0.38 | 6 x $0.134 = $0.80 |
| Real tasks, 30 sessions | 30 x $0.10 = $3.00 | 30 x $0.22 = $6.60 |
| Controls, 12 sessions | 12 x $0.044 = $0.53 | 12 x $0.093 = $1.12 |
| Sum | $5.53 | $11.76 |

Estimate $17.29. Hard budget $30, as approved by the project owner for 0.4.4 testing.

## Changes to this plan

- 2026-11-13, after this plan was committed, before the run: offline, the 0.4.4 hook treats all 10
  real tasks as work, and 3 of the 12 quick look-ups: `Q06` ("find the img tag in landing.html and
  tell me its src"), `Q10` ("can you spin up a background agent to check which port app.py runs
  on") and `Q11` ("have a subagent grab the deploy version number from outage-notes.txt and report
  back"). The two repeats and the 4 controls are quiet. The hook is not changed because of this.
  Criterion 1 allows 4 of 36, so it can pass only if the skill runs in at most 4 of the 9 sessions
  of each model on those three prompts. Hard budget: $30.
