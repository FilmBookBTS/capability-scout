O=<PROJECT_FOLDER>/prototype/test-evidence; python3 - <<EOF
import json,statistics as st,collections
rows=json.load(open('$O/all-runs.json'))
g=collections.defaultdict(list)
for r in rows:
  if r['set'] in('r2-default','r2-default-rep2') and r['prompt']!='P6-trivial' and r['cond']!='A-baseline':
    g[r['cond']].append((r['cost_usd'],r['duration_s']))
for k,v in g.items(): print(k,len(v),'cost',round(st.mean(x[0] for x in v),3),'dur',round(st.median(x[1] for x in v),1))
g=collections.defaultdict(list)
for r in rows:
  if r['set']=='r2-opus' and r['prompt']!='P6-trivial': g[r['cond']].append((r['cost_usd'],r['duration_s']))
for k,v in g.items(): print('opus',k,len(v),'cost',round(st.mean(x[0] for x in v),3),'dur',round(st.median(x[1] for x in v),1))
EOF

#### RESULT (is_error=False)
B-skill 14 cost 0.102 dur 16.9
D-skill+directive 14 cost 0.114 dur 16.5
E-skill+digest 14 cost 0.109 dur 21.2
opus B-skill 5 cost 0.267 dur 33.8
opus D-skill+directive 5 cost 0.232 dur 36.4
opus E-skill+digest 5 cost 0.217 dur 30.7