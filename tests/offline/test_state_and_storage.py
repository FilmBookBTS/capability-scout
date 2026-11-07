"""Offline tests for assessment state, retry, and private storage (no model calls).

Run: python3 -I test_state_and_storage.py PATH_TO_PLUGIN
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

plugin = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins", "capability-scout"))
sys.path.insert(0, os.path.join(plugin, "lib"))
import scout_store  # noqa: E402


def load(name, rel):
    loader = importlib.machinery.SourceFileLoader(name, os.path.join(plugin, rel))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


hook = load("scout_activate", "hooks/scout-activate")
probe = load("scout_probe", "bin/scout-probe")
results = []


def check(ok, name):
    results.append((bool(ok), name))


OK = {"tool_name": "Skill", "tool_input": {"skill": "capability-scout:capability-scout"}, "tool_response": {"success": True}}

# --- State semantics: a request is not an assessment -----------------------------------------
m1, s = hook.decide("Review app.py for security issues.", {})
check("before any other tool call" in m1 and s["task"]["confirmed"] is False, "first request is recorded as unconfirmed")
m2, s = hook.decide("Check app.py for SQL injection too.", s)
check(m2 is not None and "has not run yet" in m2, "unconfirmed request is retried on the next same-task prompt")
m3, s = hook.decide("And look at app.py command injection.", s)
check(m3 is None and s["task"]["requests"] == hook.MAX_REQUESTS, "retries stop after MAX_REQUESTS")
s2 = hook.confirm(OK, s)
check(s2["task"]["confirmed"] and s2["confirmed_total"] == 1, "PostToolUse Skill event confirms the assessment")
check(hook.confirm({"tool_name": "Skill", "tool_input": {"skill": "humanizer:humanizer"}}, s) == s, "other skills do not confirm")
check(hook.confirm({"tool_name": "Skill", "tool_input": {"skill": "capability-scout"},
                    "tool_response": {"success": False}}, s) == s, "a failed Skill call does not confirm")
check(hook.confirm({"tool_name": "Skill", "tool_input": {"skill": "evil-capability-scout"},
                    "tool_response": {"success": True}}, s) == s, "name must match exactly")

# Only an explicit success from the actual capability-scout Skill event confirms (v0.3.0 review).
BASE = {"tool_name": "Skill", "tool_input": {"skill": "capability-scout:capability-scout"}}
RESPONSES = {
    "successful response": ({"success": True, "commandName": "capability-scout:capability-scout"}, True),
    "successful response without commandName": ({"success": True}, True),
    "failed response": ({"success": False}, False),
    "missing response": (None, False),  # key absent, see below
    "null response": ("__null__", False),
    "empty response": ({}, False),
    "response with success null": ({"success": None}, False),
    "response with success as string": ({"success": "true"}, False),
    "response with success as 1": ({"success": 1}, False),
    "malformed response (string)": ("ok", False),
    "malformed response (list)": ([{"success": True}], False),
    "success for a different command": ({"success": True, "commandName": "humanizer:humanizer"}, False),
}
for label, (resp, want) in RESPONSES.items():
    ev = dict(BASE)
    if label != "missing response":
        ev["tool_response"] = None if resp == "__null__" else resp
    try:
        got = hook.confirm(ev, s)
    except Exception:
        got = {"crashed": True}
    check(bool(got.get("task", {}).get("confirmed")) == want and (got != s) == want,
          f"confirm: {label} -> {'confirmed' if want else 'not confirmed'}")
for label, ti in {"tool_input missing": None, "tool_input null": "__null__", "tool_input string": "capability-scout",
                  "skill not a string": {"skill": ["capability-scout"]}}.items():
    ev = {"tool_name": "Skill", "tool_response": {"success": True}}
    if ti is not None:
        ev["tool_input"] = None if ti == "__null__" else ti
    try:
        ok = hook.confirm(ev, s) == s
    except Exception:  # a crash on malformed input is a failure too
        ok = False
    check(ok, f"confirm: {label} -> not confirmed")
check(hook.confirm({"tool_name": "Bash", "tool_input": {"command": "capability-scout"}}, s) == s, "non-Skill tools never confirm")
_, sp = hook.decide("Draft release notes from CHANGELOG.md.", {})
sp = hook.confirm(OK, sp)
m, _ = hook.decide("Make the release notes from CHANGELOG.md shorter.", sp)
check(m is None, "confirmed task: same-task follow-up does not fire")
_, quiet = hook.decide("thanks", {})
_, req = hook.decide("Audit our dependencies in requirements.txt", {})
spont = hook.confirm(OK, req)
check(spont["task"]["confirmed"], "an assessment for the current task confirms it")
bare = hook.confirm(OK, {})
check(bare.get("task") is None and bare["confirmed_total"] == 1,
      "an assessment with no current task only counts; it doesn't invent a task")

# --- Storage --------------------------------------------------------------------------------
root = tempfile.mkdtemp(prefix="scout-test-")
try:
    os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(root, "data")
    d = scout_store.private_dir()
    check(d and stat.S_IMODE(os.lstat(d).st_mode) == 0o700, "state folder is created 0700")

    target = os.path.join(root, "elsewhere")
    os.makedirs(target)
    os.makedirs(os.path.join(root, "linked"))
    os.symlink(target, os.path.join(root, "linked", "state"))
    os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(root, "linked")
    check(scout_store.private_dir() is None, "a symlinked state folder is refused")

    os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(root, "loose")
    os.makedirs(os.path.join(root, "loose", "state"), mode=0o777)
    os.chmod(os.path.join(root, "loose", "state"), 0o777)
    d2 = scout_store.private_dir()
    check(d2 and stat.S_IMODE(os.lstat(d2).st_mode) == 0o700, "a group/world-accessible folder is tightened to 0700")

    os.environ.pop("CLAUDE_PLUGIN_DATA")
    tmp_env = os.path.join(root, "tmp")
    os.makedirs(tmp_env)
    tempfile.tempdir = tmp_env
    d3 = scout_store.private_dir()
    check(d3 == os.path.join(tmp_env, f"capability-scout-{os.getuid()}"), "fallback is a per-user folder in the temp dir")
    tempfile.tempdir = None

    p = os.path.join(d, "x.json")
    check(scout_store.write_json(p, {"a": 1}) and scout_store.read_json(p) == {"a": 1}, "atomic write and read round-trip")
    check(stat.S_IMODE(os.stat(p).st_mode) == 0o600, "written files are 0600")
    check(not [n for n in os.listdir(d) if n.startswith(".tmp-")], "no temp files left behind")
    os.chmod(p, 0o666)
    check(scout_store.read_json(p) is None, "a world-writable state file is ignored")
    for mode in (0o640, 0o604, 0o620, 0o602):
        os.chmod(p, mode)
        check(scout_store.read_json(p) is None, f"a {oct(mode)} state file is ignored (owner-only policy)")
    os.chmod(p, 0o600)
    check(scout_store.read_json(p) == {"a": 1}, "a 0600 state file is read")
    os.chmod(p, 0o400)
    check(scout_store.read_json(p) == {"a": 1}, "a 0400 state file is read")
    os.chmod(p, 0o600)

    # Locking fails closed (v0.3.0 review).
    import fcntl as _fcntl
    ran = []
    real_flock = scout_store.fcntl.flock

    def failing_flock(fd, op):
        raise OSError("simulated lock failure")

    scout_store.fcntl.flock = failing_flock
    try:
        try:
            with scout_store.locked(d):
                ran.append(True)
            raised = False
        except scout_store.LockUnavailable:
            raised = True
    finally:
        scout_store.fcntl.flock = real_flock
    check(raised and not ran, "locked() raises before the protected block when flock fails")
    ld = tempfile.mkdtemp(dir=root)
    os.symlink(os.path.join(root, "nowhere"), os.path.join(ld, ".lock"))
    try:
        with scout_store.locked(ld):
            ran.append(True)
        raised = False
    except scout_store.LockUnavailable:
        raised = True
    check(raised and not ran, "locked() refuses a symlinked lock file")
    with scout_store.locked(d):
        ran.append(True)
    check(ran == [True], "locked() runs the block when the lock is held")
    evil = os.path.join(root, "evil.json")
    with open(evil, "w") as f:
        json.dump({"task": {"confirmed": True}}, f)
    os.symlink(evil, os.path.join(d, "link.json"))
    check(scout_store.read_json(os.path.join(d, "link.json")) is None, "symlinked state files are not followed")
    check(scout_store.session_key("s1", "/a") != scout_store.session_key("s1", "/b"),
          "same session id with different transcripts gets separate state")

    # Catalog cache poisoning: malformed cache is rejected.
    check(not probe.valid_catalog({"installed": [], "available": [{"id": 1}]}), "malformed catalog cache is rejected")
    check(probe.valid_catalog({"installed": [], "available": [{"id": "x@y", "d": "", "src": ""}]}), "well-formed catalog accepted")

    # End to end: real hook processes, concurrent sessions sharing a session id.
    env = dict(os.environ, CAPABILITY_SCOUT_HOOK="on", CLAUDE_PLUGIN_DATA=os.path.join(root, "e2e"))
    exe = os.path.join(plugin, "hooks", "scout-activate")

    def fire(i):
        ev = {"session_id": "shared", "transcript_path": f"/t/{i % 4}.jsonl", "prompt": "Review app.py for security issues."}
        return subprocess.run([sys.executable, "-I", exe], input=json.dumps(ev), capture_output=True, text=True, env=env).stdout

    with ThreadPoolExecutor(8) as ex:
        outs = list(ex.map(fire, range(16)))
    sd = os.path.join(root, "e2e", "state")
    states = [scout_store.read_json(os.path.join(sd, n)) for n in os.listdir(sd) if n.startswith("state-")]
    check(len(states) == 4, "four transcripts sharing one session id get four state files")
    check(all(s and s["requested_total"] == min(4, hook.MAX_REQUESTS) for s in states),
          "concurrent writes lose no updates (lock + atomic replace)")
    check(sum("Capability Scout" in o for o in outs) == 4 * hook.MAX_REQUESTS, "each session asked at most MAX_REQUESTS times")
    ev = {"session_id": "shared", "transcript_path": "/t/0.jsonl", "hook_event_name": "PostToolUse", **OK}
    subprocess.run([sys.executable, "-I", exe, "confirm"], input=json.dumps(ev), text=True, env=env, check=True)
    st0 = scout_store.read_json(os.path.join(sd, "state-" + scout_store.session_key("shared", "/t/0.jsonl") + ".json"))
    check(st0["task"]["confirmed"] is True, "confirm subprocess marks only its own session")
    # End to end: when the lock can't be taken, the hook changes no state and says nothing.
    st_path = os.path.join(sd, "state-" + scout_store.session_key("shared", "/t/1.jsonl") + ".json")
    before = open(st_path, "rb").read()
    before_mtime = os.stat(st_path).st_mtime_ns
    lock = os.path.join(sd, ".lock")
    os.unlink(lock)
    os.symlink(os.path.join(root, "nowhere"), lock)  # makes lock acquisition fail
    outs2 = []
    for args, ev in (([], {"session_id": "shared", "transcript_path": "/t/1.jsonl", "prompt": "Write release notes from CHANGELOG.md."}),
                     (["confirm"], {"session_id": "shared", "transcript_path": "/t/1.jsonl", **OK})):
        r = subprocess.run([sys.executable, "-I", exe, *args], input=json.dumps(ev), capture_output=True, text=True, env=env)
        outs2.append((r.returncode, r.stdout))
    check(open(st_path, "rb").read() == before and os.stat(st_path).st_mtime_ns == before_mtime,
          "lock failure: protected state is unchanged")
    check(outs2 == [(0, ""), (0, "")], "lock failure: hook exits 0 with no message")
    new_session = os.path.join(sd, "state-" + scout_store.session_key("shared", "/t/9.jsonl") + ".json")
    subprocess.run([sys.executable, "-I", exe], input=json.dumps({"session_id": "shared", "transcript_path": "/t/9.jsonl",
                   "prompt": "Review app.py for security issues."}), capture_output=True, text=True, env=env)
    check(not os.path.exists(new_session), "lock failure: no new state file is created")
    os.unlink(lock)
    # End to end: a request to install or download gets the approval reminder, in the hook's real output.
    def out_for(prompt, tp):
        r = subprocess.run([sys.executable, "-I", exe], input=json.dumps({"session_id": "shared", "transcript_path": tp,
                           "prompt": prompt}), capture_output=True, text=True, env=env)
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout.strip() else ""
    trial5 = "Go ahead and install whichever Sentry plugin you recommend, then download semgrep and run it against app.py."
    o1 = out_for(trial5, "/t/0.jsonl")  # same task as /t/0's confirmed review: no assessment request
    check("approval check" in o1 and "has not run yet" not in o1 and "different task" not in o1,
          "install request on an assessed task: approval reminder only")
    o2 = out_for(trial5, "/t/20.jsonl")
    check("approval check" in o2 and "before any other tool call" in o2, "install request as a first task: both messages")
    check("approval check" not in out_for("Review app.py for security issues.", "/t/21.jsonl"),
          "no approval reminder for ordinary work")
    off = subprocess.run([sys.executable, "-I", exe], input=json.dumps({"session_id": "off-check", "transcript_path": "/t/off.jsonl",
                         "prompt": "Review app.py."}), capture_output=True, text=True, env=dict(env, CAPABILITY_SCOUT_HOOK="off")).stdout
    check(off == "", "hook is silent when turned off")
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [n for ok, n in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
for n in failed:
    print("FAIL", n)
sys.exit(1 if failed else 0)
