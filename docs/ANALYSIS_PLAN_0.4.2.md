# Analysis plan for the 0.4.2 live test (task set ts-3)

This plan and [`tests/live/tasks-ts3.json`](../tests/live/tasks-ts3.json) were committed before any
change to the hook for 0.4.2. Everything not stated here is as in
[`ANALYSIS_PLAN_0.4.1.md`](ANALYSIS_PLAN_0.4.1.md) and [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md).

## Question

The 0.4.1 test (ts-2) left two findings:

1. Requests to search or look things up on the web were not treated as work by the hook. All 6
   near-miss misses were the prompt "Search the web for known vulnerabilities in old Flask
   versions and tell me whether app.py is affected."
2. In Claude Code 2.1.322, a message from a background agent also reaches the hook as a prompt,
   and the hook asked for an assessment on one.

Version 0.4.2 changes only the hook, for these two cases. Does it fix them on new prompts, without
new false triggers? Only these cases are retested.

Disclosure: while writing ts-3, the 0.4.1 hook was run on its prompts to see which are quiet. It
treats 6 of the 8 web-research prompts as work, and 2 of the 3 background-agent prompts as work on
their own text.

## Task set ts-3

- 8 substantive web-research tasks (`W01` to `W08`). None is the ts-2 prompt.
- 3 background-agent prompts (`B01` to `B03`): they ask Claude to start background agents, whose
  results reach the hook as extra prompts. They are not counted as substantive.
- 6 controls (`C01` to `C06`): a greeting, a unit conversion, a fact, and three requests that name
  another tool, skill or slash command.

## Runs

- Arm C only (plugin 0.4.2 as published, hook on). Arm B is not run: 0.4.2 changes nothing it
  loads.
- `claude-sonnet-5-5` and `claude-opus-5-5`, requested by name. 3 repeats.
  17 prompts x 2 models x 3 = 102 sessions, in one run, shuffled with a recorded seed.
- Web tools are not allowed, as before, so web-research tasks are tested for activation only.

## Pass criteria

Set before the run. For each model:

1. Activation on the web-research tasks in at least 21 of 24 sessions.
2. Background-agent messages: in every session, no Capability Scout reminder on any
   `UserPromptSubmit` event after the session's first. Counted from the hook events in the raw
   transcripts. If fewer than 3 of the 9 background-agent sessions on a model actually started a
   background agent, this criterion is reported as not tested on that model, not as a pass.
3. False triggers on the 6 controls in at most 1 of 18 sessions.
4. Offline, before the run: the 0.4.2 hook treats as work every ts-1 and ts-2 substantive prompt
   that the 0.4.1 hook treats as work, and treats as work none of the ts-1 and ts-2
   non-substantive prompts. A difference is reported as a miss.

## Cost and budget

From the ts-2 ledger rows (arm C), with background-agent sessions estimated high because they
start extra agents (the one ts-2 session that did so cost $0.56 on Opus):

| Part | Sonnet | Opus |
|---|---|---|
| Web research, 24 sessions | 24 x $0.07 = $1.68 | 24 x $0.17 = $4.08 |
| Background agents, 9 sessions | 9 x $0.15 = $1.35 | 9 x $0.50 = $4.50 |
| Controls, 18 sessions | 18 x $0.03 = $0.54 | 18 x $0.07 = $1.26 |
| Sum | $3.57 | $9.84 |

Estimate $13.41. The hard budget is set by the project owner before the run starts.

## Changes to this plan

- 2026-11-11, before the run: the project owner set the hard budget at $25.
- 2026-11-11, after the run, no scoring rule changed: the pooled false-trigger line in
  `results/RESULTS.md` for ts-3 includes the 3 background-agent prompts. Two of them,
  `B02-bg-wordcount` and `B03-bg-list`, were treated as work by the hook on their own text (as the
  0.4.1 hook also did, disclosed above), and the skill then ran in all 6 sessions of each on each
  model. They were not part of a criterion. The counts behind criterion 2 are in
  `results/runs/20261111T223611Z-v0.4.2-ts3/hook-events.txt`.
