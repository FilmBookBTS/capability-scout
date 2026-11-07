# Phase-1 prototype files (recovered)

These are the files used for the phase-1 activation test on 2026-10-17: the experimental
activation hook (`scout-nudge`), the skill text, the probe script, the test harness
(`run_matrix.py`) with prompts P1 to P8, and the fixture folder. The results of that test are
the `legacy-phase1` rows in [`results/ledger.csv`](../../../results/ledger.csv).

Status: **RECOVERED**, not reconstructed. Nothing here was rewritten from memory. Two fixture
files were changed for publication; they are listed below.

## Where the files came from

The phase-1 session wrote these files and then changed them in place during later work, so the
copies on disk no longer show the phase-1 state. (The `run_matrix.py` in the phase-1 archive is
the later version used for the 0.2.0 refinement. It has different prompts and conditions, and it
is not the phase-1 harness.)

The session's own record keeps the full input of every tool call it made. The files were rebuilt
by replaying, in time order, every call that wrote or changed one of them:

- a `Write` call gives the whole file;
- an edit made with a Python string replacement or `sed` was replayed with the same command
  text. Each replacement had to match exactly once, or the replay stopped. Every replay step
  passed.

The record used is the Claude Code session that ran phase 1 on 2026-10-17, read without
changing it. The steps are listed in [`replay-log.txt`](replay-log.txt). The main ones (times in
UTC):

| File | Time | What it did |
|---|---|---|
| `skills/capability-scout/SKILL.md` | 02:29:03 | first version |
| | 02:34:05 | revised description (round 2) |
| | 02:43:54 | round-3 fixes |
| `hooks/scout-nudge`, `hooks/hooks.json`, `plugin.json` | 02:29:18 | first hook (nudge only) |
| `hooks/scout-nudge` | 02:33:49 | rewrite: nudge, directive and digest modes |
| `bin/scout-probe` | 02:28 to 02:33 | probe script, then `digest` subcommand |
| `run_matrix.py` | 02:30:29 | harness, conditions A to C, prompts P1 to P7 |
| | 02:31 to 02:44 | model flag, P8 and conditions D and E, extra denials |
| `fixture/`, `snapshot.sh` | 02:30:00 | fixture and state snapshot script |

The record's own event identifiers are not included here. They are kept with the private test
evidence.

## Snapshots

Each folder under [`snapshots/`](snapshots) is the state of the files when a set of runs started.

| Folder | Runs that used it | Ledger rows (`round=` in notes) |
|---|---|---|
| `smoke-0230` | one smoke run (P1, hook on); not in the results | none |
| `round1-0231` | first default-model round, conditions A, B, C | `r1-default (v1 description)` |
| `round2-0234` | round 2, default model twice and Opus once, conditions A to E | `r2-default`, `r2-default-rep2`, `r2-opus` |
| `round3-0244` | round 3, condition D only | `r3-default`, `r3-default-rep2`, `r3-opus` |

The hashes of these files are recorded against the ledger rows in
[`results/annotations.csv`](../../../results/annotations.csv). The ledger rows themselves are not
edited.

[`run-commands/`](run-commands) holds the exact shell commands that ran each set and that built
`all-runs.csv` and `all-runs.json`, each followed by the output the session saw. Each file is
named by the time (UTC, HHMMSS) the command ran. The scoring commands were typed inline and never
saved as files at the time. Two folder paths in them are replaced with placeholders (see below).

## How we know these are the originals

1. **Replay, not rewrite.** Every byte comes from a recorded tool input, applied in the recorded
   order, with each edit matching exactly once.
2. **Fixture match.** `fixture/app.py`, `fixture/para.txt` and `snapshot.sh` as rebuilt are
   byte-identical to the copies the session later placed in the phase-1 archive
   (`capability-scout-phase1-final.zip`).
3. **Prompt and condition keys.** The prompt keys (P1 to P8) and condition keys (A to E) in the
   rebuilt harness are exactly the keys in the phase-1 results file `all-runs.json`.
4. **Result fields.** The fields returned by `analyze()` in the rebuilt harness are exactly the
   fields of each record in `all-runs.json`.
5. **Hook behavior.** Run offline, the rebuilt hooks fire on the P1 prompt only in the modes
   each round used and never on P6 (`What is 17 times 23?`). That matches the
   `hook_nudge_fired` values in `all-runs.json`: true for every non-P6 session with the hook on,
   false for every P6 session and for every session with the hook off.

What is still missing: the per-session transcripts (`stream.jsonl`) and per-session summaries
(`summary.json`) were kept only in a temporary folder and are gone. The results rest on the
summary rows in `all-runs.csv`, which these files cannot re-check.

## Changes made for publication

[`SHA256SUMS.recovered`](SHA256SUMS.recovered) lists every file as recovered.
[`SHA256SUMS`](SHA256SUMS) lists the files as published. They differ only in these files:

- `snapshots/*/fixture/app.py`: the fake API key, which had the format of a live payment key,
  was replaced with `hardcoded-demo-key-not-real`. The test asks the model to find a hard-coded
  secret, so the replacement keeps the test's meaning but is not identical to what the model saw.
- `snapshots/*/fixture/para.txt`: two product words in the sample paragraph were replaced with
  neutral ones (the same change as in `tests/fixture/para.txt`).
- `run-commands/*.sh`: the original container's temporary folder for that session is shown as
  `<SESSION_TEMP_FOLDER>`, and the project folder as `<PROJECT_FOLDER>`. Nothing else in these
  files was changed.
- `replay-log.txt`: the record's event identifiers were removed from the end of each line.

The unchanged files are kept with the private test evidence, not in this repository.

## Running them again

These files are kept as a record. They need Claude Code 2.1.302-era flags, and the hook is the
experimental phase-1 hook, not the published one. Do not use them to support new results; new
results come from the current harness and are recorded in the ledger.
