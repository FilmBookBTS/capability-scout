# Analysis plan for the 0.4.6 held-out test (task set ts-10)

The 0.4.6 hook was committed (8120752) before ts-10 existed. ts-10 was then written by a separate agent
that saw only a description of the fixture files and of the prompt groups, never the hook, its rules
or earlier task sets. This plan and [`tests/live/tasks-ts10.json`](../tests/live/tasks-ts10.json) were
committed before any ts-10 prompt was run through any hook. Everything not stated here is as in
[`ANALYSIS_PLAN_0.4.5.md`](ANALYSIS_PLAN_0.4.5.md).

## Question

0.4.5 (two levels of reminder) passed the look-up and real-task criteria on the held-out set ts-9
but missed the controls criterion on one prompt, "run /code-review on my current changes". 0.4.6
recognizes a slash command after a verb as naming its tool and treats "pls" as a polite opener. It
was developed on ts-1 to ts-9. On prompts written by someone who never saw the hook, does 0.4.6 keep quick look-ups quiet
while real work still starts an assessment?

## Task set ts-10

- 16 quick look-ups (`L01` to `L16`), 4 handed to an agent. Not substantive.
- 12 real tasks (`T01` to `T12`), at least 8 starting with a retrieval word (check, show, find,
  list, grab, get, look at, look into, read, pull up, open, go through, tell me, what, how, can
  you, pls); 3 handed to an agent.
  Substantive.
- 4 controls (`C11` to `C14`): thanks, a fact, arithmetic, a request to run a slash command. The controls
  happen to include another "run /command" request, the case 0.4.6 changed; this is noted, not
  corrected.

## Runs

Arm C only (plugin 0.4.6, hook on). `claude-sonnet-5-5` and `claude-opus-5-5`, requested by name.
3 repeats. 32 prompts x 2 models x 3 = 192 sessions, one run, shuffled with a recorded seed.
Claude Code 2.1.323.

## Pass criteria

Set before the run. For each model:

1. False triggers on the quick look-ups in at most 5 of 48 sessions.
2. Activation on the real tasks in at least 33 of 36 sessions.
3. False triggers on the controls in at most 1 of 12 sessions.
4. No Capability Scout reminder on any `UserPromptSubmit` event after a session's first, counted with
   `tools/score_hook_events.py`.
5. Offline, before the run: on ts-1 to ts-9, every substantive prompt the 0.4.5 hook (11b9c74) treats as work
   still gets a reminder (either level), and no non-substantive prompt the 0.4.5 hook (11b9c74) leaves quiet
   gets the directive reminder. Prompts that newly get the conditional reminder are listed, not
   counted as misses.

## Cost and budget

As estimated for ts-7 (same sizes, ts-6 means): $20.81. Hard budget $30. Spent on this fix so far: $20.10 (ts-9).

## Changes to this plan

None yet.
