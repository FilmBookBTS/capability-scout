# Analysis plan for the 0.4.4 live test (task set ts-5)

This plan and [`tests/live/tasks-ts5.json`](../tests/live/tasks-ts5.json) were committed before any
change to the hook for 0.4.4, and before any ts-5 prompt was run through any version of the hook.
Everything not stated here is as in [`ANALYSIS_PLAN_0.4.3.md`](ANALYSIS_PLAN_0.4.3.md) and the
earlier plans.

## Question

The 0.4.3 test (ts-4) missed its main criterion: false triggers on small jobs handed to an agent
were 6 of 24 sessions on each model, against a limit of 2. All 6 came from two prompts, `D05-size`
("... shows the size of para.txt") and `D07-title-tag` ("... check whether landing.html has a title
tag"), and both are treated as work by the hook even without the agent wording. The cause is the
hook's general word rules: a verb such as "check", "show", "list" or "find" plus a file name reads
as work.

Version 0.4.4 changes only the hook, so that a quick look-up on one named file stays quiet. Does it
stop these false triggers on new prompts, while real work that starts with the same verbs still
starts an assessment?

The project owner chose not to publish 0.4.3 and to fix this first. 0.4.4 includes the 0.4.3
changes.

## Task set ts-5

- 10 quick look-ups on one named file (`L01` to `L10`): check whether, show, get, list, find. Two
  are handed to an agent or phrased as "Check that ...". Not substantive.
- 8 real tasks that start with the same verbs (`S01` to `S08`): check and fix, check and list
  fixes, find and explain, show and suggest, list and rewrite. One is handed to a background agent.
  Substantive.
- 4 controls (`K11` to `K14`): a greeting, a fact, arithmetic, a request naming another skill.

## Runs

- Arm C only (plugin 0.4.4 as published, hook on). `claude-sonnet-5-5` and `claude-opus-5-5`,
  requested by name. 3 repeats. 22 prompts x 2 models x 3 = 132 sessions, one run, shuffled with a
  recorded seed. Web tools are not allowed, as before.

## Pass criteria

Set before the run. For each model:

1. False triggers on the quick look-ups in at most 3 of 30 sessions.
2. Activation on the real tasks in at least 21 of 24 sessions.
3. False triggers on the controls in at most 1 of 12 sessions.
4. No Capability Scout reminder on any `UserPromptSubmit` event after a session's first, counted with
   `tools/score_hook_events.py` from the raw transcripts.
5. Offline, before the run: on ts-1 to ts-4, the 0.4.4 hook treats as work every substantive prompt
   the 0.4.3 hook treats as work, and treats as work no non-substantive prompt that the 0.4.3 hook
   leaves quiet. A difference is a miss.

## Cost and budget

From the ts-4 ledger rows (arm C), using its means per session as an upper guide, since most ts-5
prompts start no agent:

| Part | Sonnet | Opus |
|---|---|---|
| Quick look-ups, 30 sessions | 30 x $0.063 = $1.89 | 30 x $0.134 = $4.02 |
| Real tasks, 24 sessions | 24 x $0.141 = $3.38 | 24 x $0.345 = $8.28 |
| Controls, 12 sessions | 12 x $0.042 = $0.50 | 12 x $0.067 = $0.80 |
| Sum | $5.77 | $13.10 |

Estimate $18.87. The hard budget is set by the project owner before the run starts.

## Changes to this plan

- 2026-11-13, after the 0.4.4 hook was committed, before any live session: offline pre-check
  (`tests/offline/test_precheck_ts5.py`). The 0.4.4 hook treats all 8 real tasks as work and none of
  the 10 quick look-ups or 4 controls (the 0.4.3 hook: 8, 10 and 0). No ts-1 to ts-4 regression
  (125 of 125); the ts-4 prompts `D05-size` and `D07-title-tag` are now quiet. Disclosure: the same
  person wrote ts-5 and the 0.4.4 rule, from the two ts-4 misses, so a clean offline result here is
  weak evidence. The live test measures what the models do with the hook's answer, and the offline
  classifier tests add 15 prompts that are not in ts-5.
