S=<SESSION_TEMP_FOLDER>/scratchpad; P=$S/plugin; for m in nudge directive; do s=$(date +%s%N); echo '{"session_id":"zz'$m'","prompt":"please review this python file for security issues and suggest fixes now"}' | TMPDIR=$S CAPABILITY_SCOUT_HOOK=$m $P/hooks/scout-nudge >/dev/null; e=$(date +%s%N); echo "$m ms=$(( (e-s)/1000000 ))"; done; for i in 1 2; do s=$(date +%s%N); echo '{"session_id":"zzd'$i'","prompt":"Get the latest unresolved Sentry errors for this project and group them"}' | TMPDIR=$S CAPABILITY_SCOUT_HOOK=digest $P/hooks/scout-nudge >/dev/null; e=$(date +%s%N); echo "digest(warm cache) ms=$(( (e-s)/1000000 ))"; done; s=$(date +%s%N); echo '{"session_id":"zzoff","prompt":"please review this python file for security issues and suggest fixes now"}' | $P/hooks/scout-nudge; e=$(date +%s%N); echo "off ms=$(( (e-s)/1000000 ))"; rm -f $S/capability-scout-nudged-*

#### RESULT (is_error=False)
nudge ms=39
directive ms=36
digest(warm cache) ms=2888
digest(warm cache) ms=1753
off ms=46