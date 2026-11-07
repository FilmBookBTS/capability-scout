O=<PROJECT_FOLDER>/prototype/test-evidence; python3 - <<EOF
import json
rows=json.load(open('$O/all-runs.json'))
sc=[r for r in rows if r['scout_skill']]
print('scout runs',len(sc),'with plan',sum('apability plan' in r['final'] for r in sc))
# P2: unavailable recognized
for p,kw in [('P2-unavailable','403'),('P3-missing','sentry@'),('P4-approval','stripe')]:
  for grp in ['scout','noscout']:
    rs=[r for r in rows if r['prompt']==p and (r['scout_skill'] if grp=='scout' else not r['scout_skill'])]
    print(p,grp,len(rs),'kw',sum(kw.lower() in r['final'].lower() for r in rs))
# P3 marketplace recommendation of sentry plugin
rs=[r for r in rows if r['prompt']=='P3-missing']
for r in rs: print(r['set'][:10],r['cond'][:12],r['scout_skill'],'plugin-rec' if 'sentry@' in r['final'] or '/plugin install sentry' in r['final'] else ('connector-rec' if 'connector' in r['final'].lower() else 'none'))
# P5 humanizer usage
for r in [r for r in rows if r['prompt']=='P5-redundant']: print('P5',r['set'][:14],r['cond'][:12],r['skills_used'])
# P7 improvements / P1 competing tools
for r in [r for r in rows if r['prompt'] in('P1-security','P7-testing') and r['scout_skill']]: print(r['prompt'],r['set'][:10],r['cond'][:10],r['skills_used'], 'mentions-plugin' if '@anthropic-plugin-directory' in r['final'] else '')
EOF

#### RESULT (is_error=False)
scout runs 41 with plan 21
P2-unavailable scout 6 kw 6
P2-unavailable noscout 6 kw 6
P3-missing scout 8 kw 5
P3-missing noscout 4 kw 0
P4-approval scout 9 kw 9
P4-approval noscout 3 kw 3
r1-default A-baseline False connector-rec
r1-default B-skill False connector-rec
r1-default C-skill+hook False connector-rec
r2-default B-skill True connector-rec
r2-default D-skill+dire True connector-rec
r2-default E-skill+dige True plugin-rec
r2-default B-skill False connector-rec
r2-default D-skill+dire True connector-rec
r2-default E-skill+dige True plugin-rec
r2-opus B-skill True plugin-rec
r2-opus D-skill+dire True plugin-rec
r2-opus E-skill+dige True plugin-rec
P5 r1-default (v1 A-baseline ['humanizer:humanizer']
P5 r1-default (v1 B-skill ['humanizer:humanizer']
P5 r1-default (v1 C-skill+hook ['humanizer:humanizer']
P5 r2-default B-skill ['humanizer:humanizer']
P5 r2-default D-skill+dire ['capability-scout:capability-scout']
P5 r2-default E-skill+dige ['humanizer:humanizer']
P5 r2-default-rep B-skill ['humanizer:humanizer']
P5 r2-default-rep D-skill+dire ['capability-scout:capability-scout', 'humanizer:humanizer']
P5 r2-default-rep E-skill+dige ['humanizer:humanizer']
P1-security r2-default D-skill+di ['capability-scout:capability-scout'] 
P7-testing r2-default D-skill+di ['capability-scout:capability-scout'] 
P7-testing r2-default E-skill+di ['capability-scout:capability-scout'] 
P1-security r2-default D-skill+di ['capability-scout:capability-scout'] 
P7-testing r2-default D-skill+di ['capability-scout:capability-scout'] 
P7-testing r2-default E-skill+di ['capability-scout:capability-scout'] 
P1-security r2-opus D-skill+di ['capability-scout:capability-scout'] 
P1-security r2-opus E-skill+di ['capability-scout:capability-scout']