# Analysis plan for the 0.4.3 live test (task set ts-4)

This plan and [`tests/live/tasks-ts4.json`](../tests/live/tasks-ts4.json) were committed before any
change to the hook for 0.4.3, and before any ts-4 prompt was run through any version of the hook.
Everything not stated here is as in [`ANALYSIS_PLAN_0.4.2.md`](ANALYSIS_PLAN_0.4.2.md) and the
earlier plans.

## Question

The 0.4.2 retest left one known limitation: the hook treats a short request to hand a small job
to a background agent ("Launch a background agent to count the words in para.txt ...") as work,
from the user's own words, and the skill then ran in 6 of 9 such sessions on each model.

Version 0.4.3 changes only the hook, for this case. Does it stop these false triggers on new
prompts, while requests that hand real work to an agent still start an assessment?

## Task set ts-4

- 8 small jobs handed to an agent (`D01` to `D08`): count, list, print, check. Not substantive.
- 8 real tasks handed to an agent (`E01` to `E08`): audit, tests, review, research, postmortem,
  migration plan, release notes, refactor. Substantive.
- 4 controls (`K01` to `K04`): a greeting, a fact, arithmetic, a request naming another skill.

## Runs

- Arm C only (plugin 0.4.3 as published, hook on). `claude-sonnet-5-5` and `claude-opus-5-5`,
  requested by name. 3 repeats. 20 prompts x 2 models x 3 = 120 sessions, one run, shuffled with a
  recorded seed. Web tools are not allowed, as before.

## Pass criteria

Set before the run. For each model:

1. False triggers on the small jobs handed to an agent in at most 2 of 24 sessions.
2. Activation on the real tasks handed to an agent in at least 21 of 24 sessions.
3. No Capability Scout reminder on any `UserPromptSubmit` event after a session's first (the
   0.4.2 behavior), counted with `tools/score_hook_events.py` from the raw transcripts.
4. False triggers on the controls in at most 1 of 12 sessions.
5. Offline, before the run: on ts-1, ts-2 and ts-3, the 0.4.3 hook treats as work every
   substantive prompt the 0.4.2 hook treats as work, and treats as work no ts-1 or ts-2
   non-substantive prompt and no ts-3 control. A difference is a miss.

## Cost and budget

From the ts-3 ledger rows (arm C). Real tasks handed to an agent are estimated above the ts-3
web-research means because the agent adds work:

| Part | Sonnet | Opus |
|---|---|---|
| Small jobs, 24 sessions | 24 x $0.08 = $1.92 | 24 x $0.15 = $3.60 |
| Real tasks, 24 sessions | 24 x $0.12 = $2.88 | 24 x $0.30 = $7.20 |
| Controls, 12 sessions | 12 x $0.04 = $0.48 | 12 x $0.09 = $1.08 |
| Sum | $5.28 | $11.88 |

Estimate $17.16. The hard budget is set by the project owner before the run starts.

## Changes to this plan

None yet.
