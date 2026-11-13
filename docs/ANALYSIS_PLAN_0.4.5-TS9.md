# Analysis plan for the 0.4.5 held-out test (task set ts-9)

The 0.4.5 hook was committed (11b9c74) before ts-9 existed. ts-9 was then written by a separate agent
that saw only a description of the fixture files and of the prompt groups, never the hook, its rules
or earlier task sets. This plan and [`tests/live/tasks-ts9.json`](../tests/live/tasks-ts9.json) were
committed before any ts-9 prompt was run through any hook. Everything not stated here is as in
[`ANALYSIS_PLAN_0.4.5.md`](ANALYSIS_PLAN_0.4.5.md).

## Question

0.4.5 adds a second, conditional reminder: questions and requests that only retrieve something get
at most that one, which tells Claude to run the skill for substantive work and to skip it for a
quick look-up. The directive reminder is kept for clear work (long, several steps, or a request to
make something or judge something). It was developed on ts-1 to ts-8; ts-7 and ts-8 were looked at
and used for development. On prompts written by someone who never saw the hook, does 0.4.5 keep quick look-ups quiet
while real work still starts an assessment?

## Task set ts-9

- 16 quick look-ups (`U01` to `U16`), 4 handed to an agent. Not substantive.
- 12 real tasks (`J01` to `J12`), at least 8 starting with a retrieval word (check, show, find,
  list, grab, get, look at, look into, read, pull up, open, go through, tell me, what, how, can
  you); 3 handed to an agent.
  Substantive.
- 4 controls (`V01` to `V04`): thanks, a fact, arithmetic, a request to run a slash command.

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
5. Offline, before the run: on ts-1 to ts-6, every substantive prompt the 0.4.4 hook treats as work
   still gets a reminder (either level), and no non-substantive prompt the 0.4.4 hook leaves quiet
   gets the directive reminder. Prompts that newly get the conditional reminder are listed, not
   counted as misses.

## Cost and budget

As estimated for ts-7 (same sizes, ts-6 means): $20.81. Hard budget $30. Spent on 0.4.5 so far: $0 (the ts-7 and ts-8 runs were not made).

## Changes to this plan

None yet.
