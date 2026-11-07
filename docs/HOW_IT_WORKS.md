# How Capability Scout works

![Five steps from left to right: you send a request; Claude Code's hook checks whether it is substantive work; the skill checks which capabilities work here; Claude shows a short capability plan; then Claude does the task, installing nothing without approval.](images/how-it-works.svg)

A **capability** is anything Claude can use for a task: a skill, a plugin, a connector to an
outside service such as email or an issue tracker, or a built-in tool. Capability Scout is a
skill that makes Claude check which capabilities actually work in the current conversation
before it starts substantive work.

## The skill

The instructions are in `SKILL.md`: one copy for Claude Code
([`plugins/capability-scout/skills/capability-scout/SKILL.md`](../plugins/capability-scout/skills/capability-scout/SKILL.md))
and one for chat
([`chat-edition/capability-scout/SKILL.md`](../chat-edition/capability-scout/SKILL.md)).
The skill's description tells Claude when to use it: before a review, an audit, tests, debugging,
research, writing, a multi-step build, work that needs an outside service, or a question about
which tools exist. It says to skip quick questions and small edits.

When it runs, it has five steps:

1. **Inventory.** List what is available, from the cheapest source first: the session's own tool
   and skill list, then (in Claude Code) the `scout-probe` script, then account-level lists when
   those tools exist. Something that is installed but failing, for example a connector that
   needs sign-in, counts as unavailable.
2. **Select.** Split the task into parts and pick one capability for each part. Prefer what is
   verified to work, then correctness, least access, well-known sources, and lower cost.
3. **Marketplace check.** Search for a missing or clearly better capability only when a part of
   the task has nothing that works, or when the task is a review, audit, test or security job or
   names a specific product. Recommend at most three, or nothing.
4. **Approval boundary.** Never install, enable, connect, download, change settings, or take an
   outward-facing action (post, push, publish, delete, spend) without the user approving that
   specific item. Approval has two steps: propose one named item with its source, purpose, access
   and effects; act only after the user confirms that item.
5. **Report, then work.** Show a capability plan of five lines or fewer, then do the task.

## The Claude Code plugin

The plugin adds two things the chat edition does not have.

- **`scout-probe`** ([`plugins/capability-scout/bin/scout-probe`](../plugins/capability-scout/bin/scout-probe))
  is a read-only script. `scout-probe inventory` lists installed plugins and checks whether
  configured MCP servers (connectors) connect. `scout-probe search <terms>` searches the plugin
  marketplace. It installs and changes nothing.
- **The activation hook** ([`plugins/capability-scout/hooks/scout-activate`](../plugins/capability-scout/hooks/scout-activate))
  runs each time you send a message. If the message looks like substantive work and no
  assessment has run for this task, it adds one sentence asking Claude to run the skill first.
  It also adds a reminder about approval when a message asks to install or connect something.
  It is on by default from version 0.4.0. What it adds and stores, word for word:
  [HOOK.md](HOOK.md).

The hook decides with word rules, not a model. It can be wrong in both directions; known cases
are in [HOOK.md](HOOK.md) and the test results.

## The chat edition

The chat edition is the same method as instructions only: no script and no hook. In chat, the
skill runs only when Claude decides from the skill's description that the task fits. It uses the
chat's own tools for the inventory, such as the lists of skills and connectors, when they exist.
