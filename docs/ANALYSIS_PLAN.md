# Analysis plan for the live activation test

This plan is committed before any live session runs. The harness records the plan's SHA-256
in each run's manifest. If the plan changes after a run, the run is reported against the version
it recorded, and the change is listed at the end of this file.

## Question

When Capability Scout is installed, does it run at the start of substantive work, and stay out
of the way on prompts that do not need it? How much of that is due to the activation hook, which
is on by default from version 0.4.0?

## Definitions

- **Session.** One non-interactive Claude Code process (`claude -p`), started in a fresh copy of
  [`tests/fixture`](../tests/fixture), with a new, empty Claude Code configuration folder and no
  saved history. One prompt per session.
- **Substantive task.** A prompt in the `substantive` list of
  [`tests/live/tasks.json`](../tests/live/tasks.json). Each is real work: a review, tests, an audit,
  writing, research, a multi-step change, or work that needs an outside service.
- **Non-substantive prompt.** A prompt in the `non_substantive` list: greetings, arithmetic,
  single-fact questions, and requests that name a different tool or skill.
- **Activation.** The session made a `Skill` tool call whose input names `capability-scout` (in
  any namespace). Running only the `scout-probe` script does not count as activation.
- **Scout before work.** The first Capability Scout call (a `Skill` call naming
  `capability-scout`, or a `Bash` call running `scout-probe`) came before the first work tool call.
  Work tools are `Read`, `Grep`, `Glob`, `Bash`, `WebFetch`, `WebSearch`, `Agent`, `Task`, any
  `mcp__` tool, and any other `Skill`. `ToolSearch` does not count as work. These are the same rules
  as phase 1.
- **False trigger.** Activation in a session on a non-substantive prompt.
- **Hook fired.** The session's hook events contain a Capability Scout reminder. Recorded for
  every session, and used only to explain results.
- **Invalid session.** A session that timed out, ended without a result, ended with an error
  result, or whose startup event shows the wrong skills for its arm (see Isolation). Invalid
  sessions are recorded in the ledger with blank result fields and the reason in `notes`. They
  are left out of rates and counted separately. They are not re-run.

## Arms

| Arm | What is loaded | Ledger `edition` |
|---|---|---|
| A | nothing added | plugin (arm `A-no-plugin`) |
| B | the plugin, with `CAPABILITY_SCOUT_HOOK=off` | plugin |
| C | the plugin as published (variable unset, so the hook is on) | plugin |
| T | the chat edition's `SKILL.md`, wrapped in a minimal plugin with no hook and no scripts | chat-text-in-code |

Arms B and C use the same skill text. Arm T is the chat edition's text run inside Claude Code. It
is not a claude.ai chat test, and its results are reported apart from the plugin arms. Arm A
cannot activate (there is no Capability Scout skill), so it gives the baseline for cost and for
how sessions behave without the skill.

## Isolation

The machine used for testing has an account-level copy of the chat skill
(`anthropic-skills:capability-scout`) and many other plugins, which would load in every session.
To keep the arms apart, each session gets a new, empty configuration folder
(`CLAUDE_CONFIG_DIR`), holding only a copy of the sign-in credentials, and the variables that load
account skills and plugins (`CLAUDE_CODE_SYNC_SKILLS`, `CLAUDE_CODE_SYNC_PLUGINS`) are removed.
The credentials copy is deleted after the session and is never kept with the evidence.

Before the test, `run_live.py isolation-check` showed what loads in each arm (2026-11-05): 21
built-in skills in arm A and no Capability Scout skill; the same plus
`capability-scout:capability-scout` in arms B and C; the same plus
`capability-scout-chat-text:capability-scout` in arm T. Four other plugins (`cc-plugin-agents-md`,
`cc-plugin-telemetry`, `cc-plugin-privacy`, `cc-plugin-plugin-authoring`) loaded in every arm, even
with the empty configuration folder. During the run, each session's startup event is checked again.
A session that sees any Capability Scout skill other than its arm's own is invalid.

A consequence: sessions have no connectors and few other skills. That makes the arms clean, but
it is not the setting most users have. Results describe this setting.

## Tasks, repeats and order

- Task set `ts-1`: 30 substantive tasks and 12 non-substantive prompts. The substantive set
  includes the seven substantive phase-1 prompts, P1 to P5, P7 and P8, word for word. P6
  ("What is 17 times 23?") is in the non-substantive set.
- Each task runs 3 times in each arm and on each model, each time in a new session.
- The run has four stages, in this order:
  1. default model, arms A, B and C (378 sessions);
  2. default model, arm T (126 sessions);
  3. Opus, arms A, B and C (378 sessions);
  4. Opus, arm T (126 sessions).

  Within each stage, the order of all sessions is shuffled across arms, tasks and repeats with a
  seed that is recorded in the stage's manifest, so a stop at the budget cannot leave one arm much
  smaller than another. Up to 4 sessions run at once.
- After stage 1, the invalid sessions are counted and the startup events are checked for the
  right skills in each arm. If more than 5% of stage-1 sessions are invalid, or any arm had the
  wrong skills, the run stops there and is reported.
- Models: the default model of the Claude Code installation (requested by passing no `--model`)
  and Opus (`--model claude-opus-5-5`). The exact model ID that served each session is taken from
  the session itself and stored in `model_id`.
- Tools: `Read`, `Glob`, `Grep`, `Skill` and `Bash` are allowed. File edits, installs,
  `gh`, `git push` and install cards are denied, as in earlier tests. Web tools are not allowed,
  so research tasks are tested for activation only.
- Limits per session: 25 turns, $1.50, 15 minutes. The run also has a total budget. When the
  budget is reached, no new session starts; sessions not run are listed in the manifest and the
  run is labeled as stopped. Each stage is given the budget that remains. If the cap is
  reached, the report lists every arm, model and task cell that has fewer sessions than planned.

A hook pre-check (offline, no model) on this task set: the hook's classifier marks all 30
substantive tasks as work. It also marks 4 of the 12 non-substantive prompts as work:
`N06-convert` (a known error, recorded in [`docs/HOOK.md`](HOOK.md)), `N10-named-skill`,
`N11-named-tool` and `N12-named-tool`. The hook reminder is expected to fire on those four in
arm C. Whether the model then runs the skill is what the test measures.

## What is reported

From the ledger, by `tools/summarize.py`, for each edition, arm and model:

1. Activation on substantive tasks: k of n sessions, the rate, and a 95% Wilson score interval.
2. Scout before work: k of n sessions.
3. Per-task activation rates.
4. False triggers on non-substantive prompts, in their own table, with the same statistics, and
   per prompt. They are reported on three separate lines: the 8 plainly trivial prompts
   (greetings, arithmetic, single facts), the 4 prompts that name a different skill or tool, and
   all 12 pooled.
5. Invalid sessions, by reason.
6. Cost: total and mean per session.

The three repeats of a task are not independent: they share the prompt and the fixture, and a
task that one session handles a certain way is likely to be handled the same way again. The
Wilson interval treats every session as independent, so it is narrower than it should be. It is
reported as a rough guide, not a guarantee. Rates describe this task set and this setting.

## Pass criteria

These are set before the run. A result that misses them is reported as a miss, in the same
place and with the same detail as a pass.

For arm C (the published default), separately for each model:

1. Activation on substantive tasks of at least 90%, with the lower end of the 95% interval at
   or above 80%.
2. Scout before work in at least 90% of the activated sessions.
3. False triggers on at most 10% of non-substantive sessions.
4. Activation in arm C at least 20 percentage points above arm B, or arm B already at 90% or
   more (in which case the hook is reported as adding little).

No pass criteria apply to arm T. It is reported for information.

The hook's word classifier is not changed for this run and is not tuned on the `ts-1` prompts.
A classifier change goes into a later version (0.4.1) and is tested on a new task set (`ts-2`).

## After the run

- The README's results come from the ledger through `tools/summarize.py`. Phase-1 and other
  earlier figures appear only in a separate table headed "Earlier prototype results", with their
  evidence quality.
- No result for the 0.4.0 default is published before this test has run.

## Cost

The estimate uses the 96 phase-1 rows of the ledger ($12.21 in total). Mean cost per session:

| Model | Substantive prompts | Non-substantive prompts | All prompts |
|---|---|---|---|
| Default | $0.1055 (69 sessions) | $0.0530 (6 sessions) | $0.1013 (75 sessions) |
| Opus | $0.2382 (18 sessions) | $0.1067 (3 sessions) | $0.2194 (21 sessions) |

Each model has 504 planned sessions: 30 substantive tasks x 4 arms x 3 repeats = 360, and 12
non-substantive prompts x 4 arms x 3 repeats = 144.

| Step | Default | Opus | Total |
|---|---|---|---|
| Substantive: 360 x mean | 360 x 0.1055 = $37.98 | 360 x 0.2382 = $85.75 | |
| Non-substantive: 144 x mean | 144 x 0.0530 = $7.63 | 144 x 0.1067 = $15.36 | |
| Sum | $45.61 | $101.12 | $146.73 |
| x 1.4 (isolated setup, see below) | $63.86 | $141.56 | **$205.42** |

The factor 1.4 comes from one test session in the isolated setup, which cost $0.074 against
$0.053 for the phase-1 non-substantive sessions on the default model. It is a rough adjustment
from a single session.

A simpler estimate uses one mean per model: 504 x $0.1013 + 504 x $0.2194 = $161.67 before the
factor. It is higher than $146.73 because 29% of the new sessions are non-substantive, against 9%
in phase 1, and non-substantive sessions cost about half as much.

For comparison, a flat $0.13 per session gives 1,008 x $0.13 = $131.04.

The run's hard budget is $230 across all stages. `tests/live/run_live.py plan` prints these
numbers.

## Changes to this plan

- 2026-11-06: the test machine restarted during stage 3 (Opus, arms A, B and C), after 177 of
  378 sessions had their ledger rows. Those rows are kept. A `--resume` option was added to the
  harness. It runs the sessions of the interrupted run that have no ledger row, in the original
  order and with the original seed, as a new run whose manifest names the interrupted one. The
  four sessions that were in progress at the restart have no row and were run again; any cost
  they had is not recorded. Nothing else in the plan changed.
- 2026-11-06: the machine restarted again during stage 4 (Opus, arm T), after 67 of 126 sessions
  had their ledger rows. It was finished the same way, with `--resume`.
- 2026-11-06, correction to the Isolation section, made after the run: "sessions have no
  connectors" is not exact. No connector's tools were loaded (each session's startup event lists
  no MCP servers), but Claude Code's `ListConnectors` tool was available and listed the
  connectors of the signed-in account. Some replies refer to that list. The tool was available
  in every arm, and no scoring rule depends on it.
