#!/bin/bash
# Records state that an install, enable, marketplace add, MCP add, settings change or
# package install would change. Diff a snapshot taken before tests with one taken after.
# Usage: snapshot.sh [WORK_DIR ...]   (work dirs: also record their .claude/settings*.json)
C=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
# sha256sum on Linux, shasum on macOS.
sha() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi; }
h() { [ -f "$1" ] && echo "$1 $(sha < "$1" | cut -c1-16)" || echo "$1 absent"; }
{
  echo "## claude plugin list --json"; claude plugin list --json
  echo "## claude plugin marketplace list"; claude plugin marketplace list
  echo "## claude mcp list (names only)"; claude mcp list 2>/dev/null | sed -n 's/^\([^:]*\(:[^:]*:[^:]*\)\?\): .*/\1/p' | sort
  echo "## settings and plugin registry files"
  for f in "$C/settings.json" "$C/settings.local.json" "$C/plugins/installed_plugins.json" \
           "$C/plugins/known_marketplaces.json" "$C/plugins/config.json"; do h "$f"; done
  for w in "$@"; do h "$w/.claude/settings.json"; h "$w/.claude/settings.local.json"; h "$w/.mcp.json"; done
  echo "## ~/.claude.json relevant keys (usage counters excluded; they change on every start)"
  python3 -c "
import json,os,hashlib
p=os.path.expanduser('~/.claude.json')
d=json.load(open(p)) if os.path.exists(p) else {}
keep={k: d.get(k) for k in ('mcpServers','enabledPlugins','permissions') if k in d}
keep['projects']={k: {f: v.get(f) for f in ('mcpServers','enabledMcpjsonServers','disabledMcpjsonServers','allowedTools') if f in v}
                  for k, v in (d.get('projects') or {}).items()}
print(hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:16], sorted(d))"
  echo "## plugin dirs"; ls "$C/plugins" "$C/plugins/data" "$C/plugins/synced"/* 2>/dev/null
  echo "## user-level packages"
  python3 -m pip list --user --format=freeze 2>/dev/null | sort | sha | cut -c1-16
  python3 -m pip list --format=freeze 2>/dev/null | sort | sha | cut -c1-16
  npm ls -g --depth=0 2>/dev/null | sha | cut -c1-16
} 2>&1
