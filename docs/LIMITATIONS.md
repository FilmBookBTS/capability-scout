# Limitations

Plain statements of what the tests do and do not show, and what Capability Scout does not do.

## What the tests show

- **One setting.** All live sessions ran in one Linux cloud container, with Claude Code 2.1.318
  (0.4.0, task set `ts-1`) or 2.1.322 (0.4.1, task set `ts-2`), in November 2026. Each session had an empty configuration folder. No connector's tools were
  loaded, and the only skills were those built into Claude Code plus four plugins that loaded in
  every setup on that machine. Claude Code's `ListConnectors` tool could still list the
  connectors of the signed-in account, and some replies mention that list. Most people's setups
  have more skills and working connectors. Results may differ there.
- **Two models.** Sonnet (`claude-sonnet-5-5`) and Opus (`claude-opus-5-5`). For 0.4.0, Sonnet
  was the installation's default model; for 0.4.1 both were requested by name, because Claude
  Code 2.1.322's default model served Opus. Other models, and later versions of these, were not tested.
- **Two task sets, written by the author.** Task set `ts-1` has 30 substantive tasks and 12
  non-substantive prompts; `ts-2` has 24 and 24, and was written by the same person who wrote the
  0.4.1 fix, before the fix. They are all in English, all single messages. Each ran 3 times per arm and
  model. Repeated runs of the same task are not independent, so the 95% intervals are narrower
  than they should be.
- **Activation, not quality.** The live test measures whether the skill ran, and whether it ran
  before other work. It does not grade whether the capability plan was right or whether the task
  was done well.
- **No web tools in the live test.** Research tasks were tested for activation only.
- **One conversation turn.** The live test does not cover follow-up messages or a new task later
  in the same conversation. An earlier multi-turn check was small; see the ledger row
  `legacy-v0.3.1-continuity:001`.

## The hook

- **It decides with word rules, not a model, and it misfires.** In the live test, the published
  default (hook on) ran the skill on 11 of 36 non-substantive sessions with the default model and
  5 of 36 with Opus. With the default model that was "Convert 5 miles to kilometers." every time,
  and requests that name another skill or tool ("Use the code-review skill to review app.py.")
  most of the time; with Opus it was only requests that name another skill or tool. Both missed
  the plan's limit of 10%. See
  [`results/RESULTS.md`](../results/RESULTS.md#false-triggers-on-non-substantive-prompts). The
  word rules were not changed for 0.4.0. Version 0.4.1 changed them and was tested on new prompts
  (`ts-2`): 0 of 72 non-substantive sessions on each model. Word rules can still be wrong both
  ways.
- **Near-miss tasks passed at exactly the limit.** In the 0.4.1 test, 21 of 24 near-miss sessions
  ran the skill on each model, the minimum the plan allowed. All misses were "Search the web for
  ...": the hook does not treat a request that starts with "Search" as work.
- **Background-agent messages.** In Claude Code 2.1.322, a message from a background agent also
  passes through the hook as if it were a new prompt, and the hook can ask for an assessment on
  it. This happened once in the 0.4.1 test; the skill did not run.
- **Without the hook, the skill often does not run.** With the hook off, the skill ran in 35 of
  90 substantive sessions on each model.
- The hook runs only in Claude Code. claude.ai chat ignores plugin hooks.

## The chat edition

- **Not formally tested in claude.ai chat.** Its text was tested inside Claude Code (arm T),
  which is a different product. The protocol for a chat test is in
  [CHAT_PROTOCOL.md](CHAT_PROTOCOL.md). Until results from it are in the ledger, how the chat
  edition behaves in chat is not measured.
- When its text was run inside Claude Code, with no hook, the skill ran in 29 of 90 substantive
  sessions with the default model and 63 of 90 with Opus.
- It has no script and no hook, so it relies on Claude choosing the skill from its description.

## Earlier results

- **Phase 1 (October 2026) is weak evidence.** Only one summary row per session survives; the
  transcripts were not kept. The skill text and the hook were changed between rounds after
  results were seen, and the same tasks were reused. The phase-1 hook fired only on prompts of 8
  or more words, and only 9 of the 96 sessions used a trivial prompt, so phase 1 says nothing
  reliable about false triggers.
- Later rows (versions 0.2.0 to 0.3.3) have the evidence quality written in their `notes`
  column.

## What it does not do

- It does not install, enable, connect or download anything by itself, and it does not take
  outward-facing actions without approval. This is enforced by instructions to the model. The
  host's permission rules are what actually block a command; the skill is not a security
  boundary.
- It does not check that a recommended plugin or connector is safe or good. It reports what the
  marketplace lists.
- It adds cost. In the live test with the default model, the mean cost per substantive session
  was $0.059 without the plugin, $0.065 with the skill and the hook off, and $0.073 with the
  published default. With Opus: $0.135, $0.145 and $0.171. See
  [`results/RESULTS.md`](../results/RESULTS.md#cost-by-model-and-arm).
- `scout-probe` and the hook need `python3`.
