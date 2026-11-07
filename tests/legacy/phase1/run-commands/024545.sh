S=<SESSION_TEMP_FOLDER>/scratchpad; ls ~/.claude/plugins/; ls -d $S/venv 2>&1; rmdir ~/.claude/plugins/data/capability-scout-inline ~/.claude/plugins/data 2>/dev/null; rm -f /tmp/capability-scout-*; $S/snapshot.sh > $S/snapshot-final.txt; diff <(grep -v "claude.json " $S/snapshot-before.txt) <(grep -v "claude.json " $S/snapshot-final.txt) && echo "NO STATE CHANGE (final)"; cp $S/snapshot.sh <PROJECT_FOLDER>/prototype/tests/; cp $S/snapshot-before.txt $S/snapshot-final.txt <PROJECT_FOLDER>/prototype/test-evidence/; cp -r $S/fixture <PROJECT_FOLDER>/prototype/tests/fixture; O=<PROJECT_FOLDER>/prototype/test-evidence; python3 - <<EOF
import json,glob
rows=json.load(open('$O/all-runs.json'))
for d,label,model in [('runs-r3-default-a','r3-default','default (claude-sonnet-5-5)'),('runs-r3-default-b','r3-default-rep2','default (claude-sonnet-5-5)'),('runs-r3-opus','r3-opus','opus')]:
  for f in sorted(glob.glob('$S/'+d+'/*/summary.json')):
    r=json.load(open(f)); r['set']=label; r['model']=model; rows.append(r)
json.dump(rows,open('$O/all-runs.json','w'),indent=1)
import csv
cols=['set','model','prompt','cond','scout_skill','probe_runs','probe_search','scout_before_work','hook_nudge_fired','skills_used','install_attempts','permission_denials','first_turn_context_tokens','cost_usd','turns','duration_s']
with open('$O/all-runs.csv','w',newline='') as fh:
  w=csv.writer(fh); w.writerow(cols)
  for r in rows: w.writerow([json.dumps(r[c]) if isinstance(r[c],(list,dict)) else r[c] for c in cols])
print(len(rows), round(sum(r['cost_usd'] or 0 for r in rows),2))
EOF

#### RESULT (is_error=False)
data
plugin-catalog-cache.json
plugin-directory-cache-v2.json
synced
ls: cannot access '<SESSION_TEMP_FOLDER>/scratchpad/venv': No such file or directory
NO STATE CHANGE (final)
96 12.21