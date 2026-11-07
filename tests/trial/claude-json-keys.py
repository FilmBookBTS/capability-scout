#!/usr/bin/env python3
"""Print the persistent ~/.claude.json settings a trial could change, in readable form.

Read-only. Prints the account-level MCP servers, enabled plugins and permissions, plus each
project's MCP and allowed-tool fields. The trial folder's own project entry is printed separately,
because opening a new folder in Claude Code can add an entry for it; that entry is expected and
must not be mistaken for a change elsewhere. Run it before and after the trial and diff the output.
Usage: claude-json-keys.py TRIAL_FOLDER
"""
import json
import os
import sys

FIELDS = ("mcpServers", "enabledMcpjsonServers", "disabledMcpjsonServers", "allowedTools")
trial = {os.path.abspath(os.path.expanduser(sys.argv[1])), os.path.realpath(os.path.expanduser(sys.argv[1]))}
path = os.path.expanduser("~/.claude.json")
d = json.load(open(path)) if os.path.exists(path) else {}
out = {k: d.get(k) for k in ("mcpServers", "enabledPlugins", "permissions") if k in d}
out["projects"], out["trial_folder_entry"] = {}, None
for k, v in (d.get("projects") or {}).items():
    fields = {f: v.get(f) for f in FIELDS if f in v} if isinstance(v, dict) else v
    if k in trial:
        out["trial_folder_entry"] = fields
    else:
        out["projects"][k] = fields
print(json.dumps(out, indent=1, sort_keys=True))
