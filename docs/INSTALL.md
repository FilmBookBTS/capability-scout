# Installing Capability Scout

There are two editions. Pick the one for the product you use.

| Edition | For | What it contains |
|---|---|---|
| Chat edition | claude.ai chat (web, desktop or mobile app) | one instruction file, `SKILL.md` |
| Claude Code plugin | Claude Code, the command-line tool | the instructions, a read-only check script (`scout-probe`) and an activation hook |

A **skill** is a set of written instructions Claude reads when a task matches its description.
A **plugin** is a package for Claude Code that can hold skills, scripts and hooks. A **hook** is
a small program Claude Code runs at fixed moments, for example each time you send a message.

## Chat edition (no coding)

1. Download this repository as a ZIP file (on GitHub: the green **Code** button, then
   **Download ZIP**) and unzip it.
2. Find the folder `chat-edition/capability-scout`. It holds one file, `SKILL.md`.
3. Make a ZIP file of that `capability-scout` folder (on a Mac: right-click the folder, then
   **Compress**; on Windows: right-click, then **Send to**, then **Compressed (zipped) folder**).
4. In claude.ai, open **Settings**, then **Capabilities**, and add the ZIP file as a skill.
5. Make sure the Capability Scout skill is switched on.

To turn it off, switch it off in the same place.

These steps were not tested from the build machine, which has no claude.ai browser session. The
menu names are as of November 2026 and may change.

## Claude Code plugin

You need Claude Code installed. In a terminal:

1. Add this repository as a plugin marketplace:

   ```
   claude plugin marketplace add FilmBookBTS/capability-scout
   ```

2. Install the plugin:

   ```
   claude plugin install capability-scout@capability-scout
   ```

3. Start a new Claude Code session. The skill and the hook load at startup.

The same two steps work inside a Claude Code session as `/plugin marketplace add
FilmBookBTS/capability-scout` and `/plugin install capability-scout@capability-scout`.

To try it for one session without installing, clone the repository and run
`claude --plugin-dir plugins/capability-scout` from its folder.

### The hook

The hook is on by default. It adds a short reminder to run the skill when a message looks like
substantive work. To turn it off, add this to your Claude Code `settings.json`:

```json
{ "env": { "CAPABILITY_SCOUT_HOOK": "off" } }
```

Exactly what the hook adds and stores: [HOOK.md](HOOK.md).

### Requirements

| Need | Required? | Without it |
|---|---|---|
| Claude Code | required for the plugin | use the chat edition instead |
| `python3` on the PATH | required for the hook and `scout-probe` | the hook and the probe do not run; the skill still works from its instructions |
| Network access to the plugin marketplace | optional | `scout-probe search` finds nothing, so the skill cannot suggest new plugins |

## Files the plugin creates

| File | Created by | When | Safe to delete |
|---|---|---|---|
| `$CLAUDE_PLUGIN_DATA/state/state-*.json` and `.lock` | the hook | first substantive message of a session | yes, when no session is running; deleted after 7 days |
| `<plugin data or temp folder>/capability-scout-<user id>/catalog.json` | `scout-probe search` | first search, refreshed after 6 hours | yes |
| `~/.claude/plugins/plugin-catalog-cache.json` | Claude Code itself, when `scout-probe search` runs `claude plugin list --available --json` | first marketplace search on a machine without this cache | yes; Claude Code rebuilds it. It is Claude Code's own file |
| `~/.claude/plugins/plugin-directory-cache-v2.json` | Claude Code itself, same command | same; seen with Claude Code 2.1.311 | same |

The plugin writes no settings, permissions, plugin records or marketplace entries.

## Uninstall

- Chat edition: delete the skill in **Settings**, **Capabilities**.
- Plugin: `claude plugin uninstall capability-scout`. This deletes the plugin's data folder.
  Also delete `<temp folder>/capability-scout-<user id>` if it exists (the probe's cache when run
  from a shell).
