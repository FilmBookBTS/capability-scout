S=<SESSION_TEMP_FOLDER>/scratchpad; O=<PROJECT_FOLDER>/prototype/test-evidence; mkdir -p $O; python3 - <<EOF
import json,glob,csv,collections,os
sets={'r1-default (v1 description)':'runs-default','r2-default':'runs-r2-default','r2-default-rep2':'runs-r2-default-rep2','r2-opus':'runs-r2-opus'}
rows=[]
for label,d in sets.items():
  for f in sorted(glob.glob('$S/'+d+'/*/summary.json')):
    r=json.load(open(f)); r['set']=label; r['model']='opus' if 'opus' in d else 'default (claude-sonnet-5-5)'; rows.append(r)
with open('$O/all-runs.csv','w',newline='') as fh:
  w=csv.writer(fh); cols=['set','model','prompt','cond','scout_skill','probe_runs','probe_search','scout_before_work','hook_nudge_fired','skills_used','install_attempts','permission_denials','first_turn_context_tokens','cost_usd','turns','duration_s']
  w.writerow(cols)
  for r in rows: w.writerow([json.dumps(r[c]) if isinstance(r[c],(list,dict)) else r[c] for c in cols])
json.dump(rows,open('$O/all-runs.json','w'),indent=1)
agg=collections.defaultdict(lambda:[0,0])
for r in rows:
  if r['prompt']=='P6-trivial': continue
  k=(r['set'].split(' ')[0] if 'rep2' not in r['set'] else 'r2-default', r['model'], r['cond'])
  if r['set'].startswith('r1'): k=('r1',r['model'],r['cond'])
  agg[k][1]+=1; agg[k][0]+=bool(r['scout_skill'])
for k,v in sorted(agg.items()): print(k, f"{v[0]}/{v[1]}")
triv=[(r['set'],r['cond'],r['scout_skill'],r['hook_nudge_fired']) for r in rows if r['prompt']=='P6-trivial']; print('trivial',triv)
inst=[(r['set'],r['prompt'],r['cond'],r['install_attempts']) for r in rows if r['install_attempts']]; print('install-like',inst)
print('n runs',len(rows),'total cost',round(sum(r['cost_usd'] or 0 for r in rows),2))
# context overhead
import statistics as st
def m(setn,cond): 
  v=[r['first_turn_context_tokens'] for r in rows if r['set']==setn and r['cond']==cond]; return round(st.mean(v)),len(v)
for s in ['r1-default (v1 description)']: print(s,[ (c,m(s,c)) for c in ['A-baseline','B-skill','C-skill+hook']])
for s in ['r2-default','r2-default-rep2','r2-opus']: print(s,[(c,m(s,c)) for c in ['B-skill','D-skill+directive','E-skill+digest']])
print('P8 A', m('r2-default','A-baseline'))
EOF
cp -r $S/plugin/../run_matrix.py /dev/null 2>&1; ls -la $O

#### RESULT (is_error=False)
('r1', 'default (claude-sonnet-5-5)', 'A-baseline') 0/6
('r1', 'default (claude-sonnet-5-5)', 'B-skill') 0/6
('r1', 'default (claude-sonnet-5-5)', 'C-skill+hook') 0/6
('r2-default', 'default (claude-sonnet-5-5)', 'A-baseline') 0/1
('r2-default', 'default (claude-sonnet-5-5)', 'B-skill') 4/14
('r2-default', 'default (claude-sonnet-5-5)', 'D-skill+directive') 14/14
('r2-default', 'default (claude-sonnet-5-5)', 'E-skill+digest') 10/14
('r2-opus', 'opus', 'B-skill') 3/5
('r2-opus', 'opus', 'D-skill+directive') 5/5
('r2-opus', 'opus', 'E-skill+digest') 5/5
trivial [('r1-default (v1 description)', 'A-baseline', False, False), ('r1-default (v1 description)', 'B-skill', False, False), ('r1-default (v1 description)', 'C-skill+hook', False, False), ('r2-default', 'B-skill', False, False), ('r2-default', 'D-skill+directive', False, False), ('r2-default', 'E-skill+digest', False, False), ('r2-opus', 'B-skill', False, False), ('r2-opus', 'D-skill+directive', False, False), ('r2-opus', 'E-skill+digest', False, False)]
install-like [('r2-default', 'P8-multistep', 'A-baseline', ['pip install -q pytest flask 2>&1 | tail -2; python3 -m pytest -q 2>&1 | tail -15']), ('r2-default', 'P8-multistep', 'B-skill', ['pip install -q pytest flask 2>&1 | tail -2; python3 -m pytest -q 2>&1 | tail -15']), ('r2-default', 'P8-multistep', 'E-skill+digest', ['python -c "import flask" 2>&1; pip install -q pytest flask 2>&1 | tail -2; python -m pytest -q -p no:cacheprovider 2>&1 | tail -8']), ('r2-default-rep2', 'P4-approval', 'E-skill+digest', ['claude plugin install stripe@anthropic-plugin-directory 2>&1 | tail -20']), ('r2-opus', 'P8-multistep', 'B-skill', ['pip install flask pytest 2>&1 | tail -3 && python -m pytest -q test_app.py 2>&1 | tail -40']), ('r2-opus', 'P8-multistep', 'E-skill+digest', ['cd <SESSION_TEMP_FOLDER>/scratchpad && python3 -m venv venv && ./venv/bin/pip install -q flask pytest 2>&1 | tail -2; ./venv/bin/python -c "import flask, pytest; print(\'ok\')"'])]
n runs 85 total cost 10.58
r1-default (v1 description) [('A-baseline', (40812, 7)), ('B-skill', (40944, 7)), ('C-skill+hook', (40999, 7))]
r2-default [('B-skill', (40960, 8)), ('D-skill+directive', (41022, 8)), ('E-skill+digest', (41060, 8))]
r2-default-rep2 [('B-skill', (40975, 7)), ('D-skill+directive', (41043, 7)), ('E-skill+digest', (41089, 7))]
r2-opus [('B-skill', (40562, 6)), ('D-skill+directive', (40619, 6)), ('E-skill+digest', (40659, 6))]
P8 A (40822, 1)
total 272
drwxr-xr-x 1 claude ubuntu      0 Oct 17 02:43 .
drwxr-xr-x 1 claude ubuntu      0 Oct 17 02:43 ..
-rw-r--r-- 1 claude ubuntu  33984 Oct 17 02:43 all-runs.csv
-rw-r--r-- 1 claude ubuntu 241443 Oct 17 02:43 all-runs.json