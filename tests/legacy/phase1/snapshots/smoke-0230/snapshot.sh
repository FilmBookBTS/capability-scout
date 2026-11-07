#!/bin/bash
# Records state that a plugin install, enable, marketplace add or MCP add would change.
{
  echo "## claude plugin list --json"; claude plugin list --json
  echo "## claude plugin marketplace list"; claude plugin marketplace list
  echo "## settings files"; for f in ~/.claude/settings.json ~/.claude/settings.local.json ~/.claude.json; do [ -f "$f" ] && echo "$f $(sha256sum < "$f" | cut -c1-16)" || echo "$f absent"; done
  echo "## ~/.claude.json mcpServers/enabledPlugins keys"; python3 -c "
import json,os
p=os.path.expanduser('~/.claude.json')
d=json.load(open(p)) if os.path.exists(p) else {}
print(sorted(d.get('mcpServers',{}))); print(sorted(k for k in d if 'plugin' in k.lower()))"
  echo "## plugin dirs"; ls ~/.claude/plugins ~/.claude/plugins/synced/* 2>/dev/null
} 2>&1
