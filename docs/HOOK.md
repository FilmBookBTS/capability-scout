# The activation hook: what it adds and what it stores

A hook is a small program that Claude Code runs at fixed moments, for example each time you send a message. Capability Scout's hook is `plugins/capability-scout/hooks/scout-activate`, registered in `plugins/capability-scout/hooks/hooks.json`.

## On or off

Since version 0.4.0 the hook is on by default. To turn it off, set the environment variable `CAPABILITY_SCOUT_HOOK` to `off` or `0` (upper or lower case). For example, in your Claude Code `settings.json`:

```json
{ "env": { "CAPABILITY_SCOUT_HOOK": "off" } }
```

Any other value, or no value, leaves it on. `EVAL_CAPABILITY_SCOUT_HOOK=on`, used by `claude plugin eval`, turns it on even when `CAPABILITY_SCOUT_HOOK` is off. When the hook is off it prints nothing and writes nothing.

## When it runs

| Event | What runs |
|---|---|
| Each message you send (`UserPromptSubmit`) | `scout-activate` decides whether the message is substantive work and may add one of the messages below |
| After Claude uses a skill (`PostToolUse`, matcher `Skill`) | `scout-activate confirm` records that the capability-scout skill actually ran, only when Claude Code reports `"success": true` for it |

It makes no network calls and runs no other programs.

## What it adds to a message

The hook never changes your message. It can add text that Claude sees as extra context. It adds nothing to greetings, acknowledgements, conceptual questions without a specific file, and pasted material. The exact texts:

1. First substantive task in a session:
   > Capability Scout: before any other tool call for this request, invoke the capability-scout skill once, show its short capability plan, invoke any installed specialist skill the plan picks, then do the task. Never install, download or change anything, or take an outward-facing action, without the user's explicit approval.
2. A materially different task, after an assessment has run:
   > Capability Scout: this looks like a different task from the one already assessed. Before any other tool call, invoke the capability-scout skill again for this task (reuse the earlier inventory; redo selection and the marketplace check), show the plan, invoke any specialist skill it picks, then do it.
3. The same task, when the requested assessment has not run yet (at most twice per task):
   > Capability Scout: the capability assessment requested for this task has not run yet. Before any other tool call, invoke the capability-scout skill once, show its short capability plan, then continue.
4. A message that asks to install, download, enable or connect something (added on its own or after one of the above):
   > Capability Scout approval check: this message asks to install, download, enable or connect something. It approves only an item you already proposed by exact name, with its source, purpose, the access it gets and what installing it changes, and that the user has now confirmed. A generic or "whichever you recommend" instruction, an item you never proposed, or a different kind of item from the one you recommended (for example a plugin when you recommended a connector) is not approval: propose the specific item in that form and stop. The host's permission prompt, answered by the user, is still the final check.

The decision is a word-based heuristic. It can be wrong in both directions. Since 0.4.1 it also stays quiet on unit conversions ("Convert 5 miles to kilometers.") and on short, single-step requests that name the skill, tool or slash command to use ("Use the code-review skill on app.py."). Before 0.4.1 both were treated as work. Since 0.4.2 it ignores text that Claude Code adds on its own, such as a background agent's result in a `<task-notification>` block, and requests that start with "Search", "Look up" or "Browse" count as work. Since 0.4.3 a request to hand a job to a background agent or subagent is judged by the job itself. Since 0.4.4 a short look-up on one named file ("Show the size of CHANGELOG.md.") is not treated as work, unless it asks for a judgement such as whether the file is secure. Since 0.4.5 this also covers look-ups that start with "which" or "what" and ones that end by asking for the answer ("... and report back"). Also since 0.4.5, a request the hook is less sure about, such as one that only retrieves something, gets a conditional reminder that leaves the call to Claude: run the skill for substantive work, skip it for a quick look-up.

## What it stores, and where

One small JSON file per session:

- Folder: `$CLAUDE_PLUGIN_DATA/state/` (Claude Code sets `CLAUDE_PLUGIN_DATA` for plugins). When that variable is not set, `<system temp folder>/capability-scout-<your user id>/`.
- File name: `state-<hash>.json`, where the hash is made from the session id and transcript path. A `.lock` file sits next to it.
- Permissions: folder 0700, files 0600 (readable only by you). Files older than 7 days are deleted when a new one is created.
- Contents, and nothing else:
  - `task.kw`: up to 120 lowercase words taken from your messages on the current task, used to tell a new task from a follow-up;
  - `task.requests`, `task.confirmed`: how many times an assessment was requested for this task, and whether one ran;
  - `last_kw`: up to 60 lowercase words from your last substantive message;
  - `requested_total`, `confirmed_total`: counts for the session.

It does not store your full messages, file contents, tool output or credentials. If it cannot lock or write the file safely, it adds nothing and stores nothing.

The probe script `bin/scout-probe` is separate from the hook. Its marketplace search keeps a catalog cache, and the `claude plugin list --available` command it runs makes Claude Code write its own cache files. See [INSTALL.md](INSTALL.md) for the full list of files the plugin can create.
