---
name: capability-scout
description: Run first, before other tools, when a task depends on an outside service or integration (code hosts, chat, issue trackers, error monitoring, payments, analytics, docs), asks for a review, tests, an audit or a multi-step build, or asks which tools, plugins or connectors exist or should be added. Checks which skills, plugins and MCP servers actually work here, picks the best for the task, and flags missing or materially better ones without installing anything. Skip for quick questions and small edits.
---

# Capability Scout

Goal: before substantial work, spend a little effort to make sure the work uses the best capabilities that actually work here, and tell the user about a worthwhile gap. Keep it short. Do this once per task, not on every message.

## Skip when

- The request is a quick answer, a small edit, or conversation.
- You already ran this assessment for the same task in this conversation.

## 1. Inventory (cheapest source first)

Label every finding with its **scope**, because scopes disagree:

| Scope | Source | Authoritative for |
|---|---|---|
| Session | Your own tool list, skill list, and MCP connection notices in context | What you can call right now |
| Execution environment | `scout-probe inventory` (wraps `claude plugin list --json` and `claude mcp list`) | What this machine or container has loaded and whether its MCP servers connect |
| Account / Project | `ListSkills`, `ListConnectors`, `ListPlugins`, `SearchPlugins` when those tools exist | What is enabled on claude.ai. Advisory only |
| Marketplace | `scout-probe search <terms>`; `SearchPlugins` / `SearchMcpRegistry` when they exist | What could be added |

Rules:
- Start from the session. Run `scout-probe inventory` only if a shell exists and the task depends on plugins, MCP servers or outside services. Run it at most once per conversation and reuse the result.
- Installed or "loaded" does not mean working. An MCP server that failed, needs auth, is blocked by the network or has no URL is **unavailable**. Do not plan around it.
- An empty `ListPlugins` result does not mean no plugins are loaded. Check the session's skill list and `scout-probe inventory` before concluding anything.
- Discover by task, not by name. Match the task against skill and tool descriptions; the user will not tell you which resources exist.

## 2. Select

For each part of the task, pick one capability. Prefer, in order:
1. Verified working in this session over merely installed.
2. Correctness and reliability for this task over convenience.
3. Least privilege and least setup (read-only, already connected, no new auth).
4. First-party or well-maintained over unknown sources.
5. Lower context and time cost.

When two capabilities do the same job (for example two code-review skills, or a skill installed both standalone and via a plugin), use one and say which. Don't stack overlapping tools.

If an installed skill matches the task (for example a writing, review or testing skill), invoke it after this assessment. This assessment never replaces the specialist skill.

## 3. Marketplace check (gated)

Search only when one of these is true:
- A material part of the task has no working capability (missing or unavailable).
- The task is a review, audit, test or security job, or touches a specific product. In those cases always check once whether an installed or marketplace capability would materially improve correctness, reliability, testing, security or efficiency (for example a security-scanning plugin for a security review, a testing plugin for test work, the vendor's own plugin for a named product). Recommending nothing is a valid outcome; say so in one line.

Then:
- One search per gap, 2 to 4 specific terms. Never search "just in case".
- Recommend at most 3, only with a concrete benefit for this task. Say what it adds and any setup it needs (auth, network access).
- Do not repeat a recommendation the user already declined or that you already made in this conversation.

## 4. Approval boundary

Never install, enable, configure or connect anything yourself, even when the user's request says to install something. Show what you would install and why, then stop and wait for the user to confirm that specific item. That includes `claude plugin install/enable`, `claude mcp add`, `/plugin install`, editing settings files, or adding marketplaces. When an approval card tool exists (`SuggestPluginInstall`, `SuggestConnectors`), you may use it, since the user approves there. Otherwise give the exact command for the user to run. Then continue the task with what is available.

## 5. Report, then work

Give the user a short capability plan (5 lines or fewer) before starting:

```
Capability plan
- Using: <capability> for <part of task> (<scope>, verified/unverified)
- Unavailable: <capability> (<reason>), doing <fallback> instead
- Worth adding (optional): <plugin or connector> because <benefit>. Install: <command or card>
```

Omit lines that don't apply. Then do the task.
