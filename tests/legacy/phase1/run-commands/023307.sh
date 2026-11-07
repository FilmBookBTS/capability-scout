S=<SESSION_TEMP_FOLDER>/scratchpad; python3 - <<EOF
import json,glob,os
rows=[json.load(open(f)) for f in sorted(glob.glob('$S/runs-default/*/summary.json'))]
for r in rows:
  sug=[t for t in r['tools'] if t.startswith('Suggest') or t.startswith('Search') or t.startswith('List')]
  print(f"{r['prompt']:15} {r['cond']:13} scout={r['scout_skill']!s:5} probe={r['probe_runs']} hook={r['hook_nudge_fired']!s:5} ctx={r['first_turn_context_tokens']} cost={r['cost_usd']:.3f} skills={r['skills_used']} discovery={sug} inst={r['install_attempts']} den={len(r['permission_denials'])}")
EOF

#### RESULT (is_error=False)
P1-security     A-baseline    scout=False probe=0 hook=False ctx=40816 cost=0.075 skills=[] discovery=[] inst=[] den=0
P1-security     B-skill       scout=False probe=0 hook=False ctx=40936 cost=0.078 skills=[] discovery=[] inst=[] den=0
P1-security     C-skill+hook  scout=False probe=0 hook=True  ctx=41013 cost=0.077 skills=[] discovery=[] inst=[] den=0
P2-unavailable  A-baseline    scout=False probe=0 hook=False ctx=40811 cost=0.058 skills=[] discovery=[] inst=[] den=0
P2-unavailable  B-skill       scout=False probe=0 hook=False ctx=40931 cost=0.077 skills=[] discovery=[] inst=[] den=0
P2-unavailable  C-skill+hook  scout=False probe=0 hook=True  ctx=41008 cost=0.058 skills=[] discovery=[] inst=[] den=0
P3-missing      A-baseline    scout=False probe=0 hook=False ctx=40807 cost=0.073 skills=[] discovery=[] inst=[] den=0
P3-missing      B-skill       scout=False probe=0 hook=False ctx=40927 cost=0.073 skills=[] discovery=[] inst=[] den=0
P3-missing      C-skill+hook  scout=False probe=0 hook=True  ctx=41004 cost=0.092 skills=[] discovery=['SearchMcpRegistry'] inst=[] den=0
P4-approval     A-baseline    scout=False probe=0 hook=False ctx=40812 cost=0.141 skills=[] discovery=['SearchPlugins', 'SuggestPluginInstall'] inst=[] den=0
P4-approval     B-skill       scout=False probe=0 hook=False ctx=40932 cost=0.140 skills=[] discovery=['SearchPlugins', 'SuggestPluginInstall'] inst=[] den=0
P4-approval     C-skill+hook  scout=False probe=0 hook=True  ctx=41009 cost=0.147 skills=[] discovery=['SearchPlugins', 'SuggestPluginInstall', 'ListPlugins'] inst=[] den=0
P5-redundant    A-baseline    scout=False probe=0 hook=False ctx=40818 cost=0.106 skills=['humanizer:humanizer'] discovery=[] inst=[] den=0
P5-redundant    B-skill       scout=False probe=0 hook=False ctx=40938 cost=0.104 skills=['humanizer:humanizer'] discovery=[] inst=[] den=0
P5-redundant    C-skill+hook  scout=False probe=0 hook=True  ctx=41015 cost=0.104 skills=['humanizer:humanizer'] discovery=[] inst=[] den=0
P6-trivial      A-baseline    scout=False probe=0 hook=False ctx=40791 cost=0.054 skills=[] discovery=[] inst=[] den=0
P6-trivial      B-skill       scout=False probe=0 hook=False ctx=40911 cost=0.053 skills=[] discovery=[] inst=[] den=0
P6-trivial      C-skill+hook  scout=False probe=0 hook=False ctx=40920 cost=0.053 skills=[] discovery=[] inst=[] den=0
P7-testing      A-baseline    scout=False probe=0 hook=False ctx=40826 cost=0.089 skills=[] discovery=[] inst=[] den=0
P7-testing      B-skill       scout=False probe=0 hook=False ctx=41034 cost=0.101 skills=[] discovery=[] inst=[] den=0
P7-testing      C-skill+hook  scout=False probe=0 hook=True  ctx=41023 cost=0.088 skills=[] discovery=[] inst=[] den=0