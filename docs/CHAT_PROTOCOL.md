# Testing the chat edition in claude.ai

The chat edition ([`chat-edition/capability-scout/SKILL.md`](../chat-edition/capability-scout/SKILL.md))
is meant for claude.ai chat. Its live tests so far ran the same text inside Claude Code, which
is a different product, so they say little about chat. This protocol tests it in chat. A person
runs it by hand. It needs no terminal.

Until results from this protocol are in the ledger, the chat edition has not been formally
tested in claude.ai chat.

## What you need

- A claude.ai account where you can add a skill (Settings, then Capabilities).
- The chat edition's `SKILL.md` from this repository, added as a skill. Write down the date you
  added it.
- The fixture files from [`tests/fixture`](../tests/fixture), for the tasks that use a file.
- A folder on your computer for screenshots, for example `scout-chat-evidence`.
- The record sheet [`results/chat-runs.csv`](../results/chat-runs.csv). It opens in any
  spreadsheet program. Save it as CSV when you are done.

Menu names below are as of November 2026. If they differ, note that in the sheet's `notes`
column.

## Tasks

Use these prompts from task set `ts-1` ([`tests/live/tasks.json`](../tests/live/tasks.json)),
word for word. Attach the named file where the table says so.

| Task | Attach | Kind |
|---|---|---|
| P1-security | `app.py` | substantive |
| P2-unavailable | none | substantive |
| P3-missing | none | substantive |
| P4-approval | none | substantive |
| P5-redundant | `para.txt` | substantive |
| S08-postmortem | `outage-notes.txt` | substantive |
| S12-release-notes | `CHANGELOG.md` | substantive |
| S16-research-secrets | `app.py` | substantive |
| S17-calendar | none | substantive |
| S26-vendor-compare | none | substantive |
| S30-which-tools | none | substantive |
| S15-seo-review | `landing.html` | substantive |
| N01-greeting | none | non-substantive |
| P6-trivial | none | non-substantive |
| N06-convert | none | non-substantive |
| N07-fact | none | non-substantive |
| N10-named-skill | `app.py` | non-substantive |
| N12-named-tool | `para.txt` | non-substantive |

When a prompt says "in this folder" or names a file, attaching the file is the closest match in
chat. Write that in `notes` if the reply comments on it.

## Steps

1. Pick the model you will use for all runs. Write its name as shown in the model menu. Do not
   change it during the test.
2. Turn the skill **on** (Settings, Capabilities, the Capability Scout skill switch).
3. For each task in the table, in the order of the table:
   1. Start a **new chat**. Never reuse a chat: earlier messages change the result.
   2. Attach the file if the table names one, then paste the prompt exactly and send it.
   3. Wait for the reply to finish.
   4. Look at the reply and the steps shown above it, and answer:
      - **Did the skill run?** Yes if the chat shows the Capability Scout skill being used (for
        example a line saying the skill was loaded or read). A "Capability plan" heading in the
        answer also counts. Otherwise no.
      - **Did it run before other work?** Yes if the skill was used before any search, file read,
        connector call or other skill. If the skill did not run, write `false`.
   5. Take one screenshot that shows the top of the reply and any steps above it. Name it
      `<task>-<on|off>-<number>.png`, for example `P1-security-on-1.png`.
   6. Fill in one line of the record sheet (see below).
4. Turn the skill **off** and repeat step 3 for every task.
5. If you have time, repeat steps 2 to 4 once more, using `2` in the screenshot names.
6. Keep the screenshots in your folder. Do not add them to the repository: they show your
   account. The sheet names each one.

## The record sheet

One line per chat. Leave a column blank if it does not apply. Columns:

| Column | What to write |
|---|---|
| `run_id` | `chat-<date>-<your initials>:<line number>`, for example `chat-20261110-ab:001` |
| `date_utc` | the date, for example `2026-11-10` |
| `edition` | `chat` |
| `plugin_version` | `chat edition SKILL.md` |
| `skill_sha256` | the SHA-256 of the `SKILL.md` you added, if you can compute it; otherwise blank |
| `task_set_version` | `ts-1` |
| `task_id` | the task id from the table |
| `arm` | `skill-on` or `skill-off` |
| `model_id` | the model name from the model menu |
| `claude_code_version` | `not applicable (claude.ai)` |
| `environment` | `claude.ai web, new chat` (or the app you used) |
| `activated` | for substantive tasks: `true` or `false`; blank for non-substantive |
| `scout_before_work` | `true` or `false` |
| `false_trigger` | for non-substantive prompts: `true` if the skill ran, else `false`; blank for substantive |
| `cost_usd` | blank |
| `evidence_path` | `private:<screenshot file name>` |
| `notes` | anything unusual |

For a non-substantive prompt, fill `false_trigger` and leave `activated` blank, so that the
summary counts it as a false-trigger test, not an activation test.

Other columns (`plugin_commit`, `hook_sha256`, `harness_commit`, `task_prompt_sha256`) stay
blank.

## After the runs

Put the filled sheet at `results/chat-runs.csv` and run `python3 -I tools/summarize.py`.
The summary reads the sheet, checks each line, and adds the rows to the tables with
`edition=chat`. Rows with `skill-off` are the baseline for rows with `skill-on`.

What this test can and cannot show:

- It is done by hand by one person, so whether the skill "ran" depends on what the chat shows.
- Each task runs once or twice per setting, so per-task rates are rough.
- The account's other skills and connectors are part of the setting. Write down any that are on.

## Account copy of the skill

The copy of the chat skill on the test account was compared with the repository file on
2026-11-05. It differs only in formatting: the skill name is in quotes and the file has no final
newline. The wording is the same.
