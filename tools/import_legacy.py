#!/usr/bin/env python3
"""Build the legacy part of results/ledger.csv from the earlier test evidence.

This runs once. It refuses to touch a ledger that already has rows unless every row it would write
is already there, byte for byte, in the same order (so re-running it is a check, not a rewrite).

Usage:
  python3 -I tools/import_legacy.py EVIDENCE_ROOT ZIP_DIR [--check]

EVIDENCE_ROOT  the project's capability-scout folder (holds prototype/test-evidence/ and the reports)
ZIP_DIR        folder with the candidate zips, used to hash the skill and hook of each packaged version

In evidence_path, "#row=N" is the CSV record number counting the header as row 1.

Nothing here re-scores a session. Each value is copied from the evidence file named in the row's
evidence_path, and the row's notes say how good that evidence is.
"""
import csv
import json
import os
import re
import sys
import zipfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger_schema import LEDGER_COLUMNS, header_line, row_to_csv_line, sha256_text, validate_row  # noqa: E402

REPO = os.path.dirname(HERE)
LEDGER = os.path.join(REPO, "results", "ledger.csv")
CLOUD_ENV = "Claude Code Projects (Beta) cloud container; non-interactive claude -p; plugin loaded with --plugin-dir"
DEFAULT_MODEL_NOTE = "claude-sonnet-5-5 (container default; row says 'default'; ID taken from same-day session logs)"
OPUS_NOTE = "opus (alias only; exact model ID not recorded)"

ZIPS = {  # packaged version -> zip file name
    "0.2.0": "capability-scout-phase1-final.zip",
    "0.3.0": "capability-scout-v0.3.0-candidate.zip",
    "0.3.1": "capability-scout-v0.3.1-candidate.zip",
    "0.3.2": "capability-scout-v0.3.2-candidate.zip",
    "0.3.3": "capability-scout-v0.3.3-candidate.zip",
}
SKILL = "capability-scout/prototype/capability-scout/skills/capability-scout/SKILL.md"
HOOK = "capability-scout/prototype/capability-scout/hooks/scout-activate"
HARNESS = "capability-scout/prototype/tests/run_matrix.py"


def zip_hashes(zip_dir, version):
    with zipfile.ZipFile(os.path.join(zip_dir, ZIPS[version])) as z:
        names = set(z.namelist())
        def h(n):
            return sha256_text(z.read(n).decode("utf-8")) if n in names else ""
        prompts = {}
        if HARNESS in names:
            src = z.read(HARNESS).decode("utf-8")
            for m in re.finditer(r'^\s*"([A-Z]\d-[\w-]+)":\s*"((?:[^"\\]|\\.)*)",\s*$', src, re.M):
                prompts[m.group(1)] = json.loads('"' + m.group(2) + '"')
        return h(SKILL), h(HOOK), prompts


def b(v):
    if v in (True, "True", "true", 1, "1"):
        return "true"
    if v in (False, "False", "false", 0, "0"):
        return "false"
    return ""


def row(**kw):
    r = {c: "" for c in LEDGER_COLUMNS}
    r.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    return r


def phase1(ev):
    path = "prototype/test-evidence/all-runs.csv"
    rows = []
    with open(os.path.join(ev, path), newline="") as f:
        for line_no, x in enumerate(csv.DictReader(f), start=2):
            trivial = x["prompt"].startswith("P6")
            act = b(x["scout_skill"])
            rows.append(row(
                run_id=f"legacy-phase1:{line_no - 1:03d}",
                date_utc="2026-10-17",
                edition="plugin",
                plugin_version="pre-0.2.0 prototype (version not recorded)",
                task_set_version="phase1-P1-P8 (prompt text not preserved)",
                task_id=x["prompt"],
                arm=x["cond"],
                model_id=DEFAULT_MODEL_NOTE if x["model"].startswith("default") else OPUS_NOTE,
                claude_code_version="2.1.302 (from phase1-results.md; not in the row)",
                environment=CLOUD_ENV,
                activated=act,
                scout_before_work=b(x["scout_before_work"]),
                false_trigger=(act if trivial else ""),
                cost_usd=x["cost_usd"],
                evidence_path=f"evidence:capability-scout/{path}#row={line_no}",
                notes=(f"round={x['set']}; summary row only, transcript not kept; harness, hook and prompts not "
                       f"preserved; skill text differed by round" + ("; trivial prompt" if trivial else "")),
            ))
    return rows


def live_csv(ev, path, batch, version, skill_h, hook_h, prompts, round_key):
    rows = []
    with open(os.path.join(ev, path), newline="") as f:
        for line_no, x in enumerate(csv.DictReader(f), start=2):
            case = x["case"]
            multi = case.startswith("C1")
            # A continuity session has no single activation value; its per-turn result is in notes.
            act = "" if multi else b(x["scout"])
            rows.append(row(
                run_id=f"{batch}:{line_no - 1:03d}",
                date_utc="2026-10-17",
                edition="plugin",
                plugin_version=version,
                skill_sha256=skill_h, hook_sha256=hook_h,
                task_set_version=f"{batch} cases (prompts from run_matrix.py in the {version} zip)",
                task_id=case,
                task_prompt_sha256=sha256_text(prompts[case]) if case in prompts else "",
                arm=x["cond"],
                model_id=DEFAULT_MODEL_NOTE if x["model"].startswith("default") else OPUS_NOTE,
                claude_code_version="2.1.302 (from the report; not in the row)",
                environment=CLOUD_ENV,
                activated=act,
                scout_before_work="" if multi else b(x["scout_first"]),
                false_trigger="",
                cost_usd=x.get("cost", ""),
                evidence_path=f"evidence:capability-scout/{path}#row={line_no}",
                notes=(f"round={x.get(round_key, '')}; summary row, final answer kept, transcript not kept; "
                       f"skill and hook hashes are of the packaged {version}, earlier rounds may have used drafts"
                       + (f"; multi-turn continuity session: {x['scout']}" if multi else "")),
            ))
    return rows


def one_session(batch, n, version, skill_h, hook_h, task_id, arm, model, cc, path, act, before, cost, notes, date):
    return row(run_id=f"{batch}:{n:03d}", date_utc=date, edition="plugin", plugin_version=version,
               skill_sha256=skill_h, hook_sha256=hook_h, task_set_version=batch, task_id=task_id, arm=arm,
               model_id=model, claude_code_version=cc, environment=CLOUD_ENV, activated=act,
               scout_before_work=before, false_trigger="", cost_usd=cost,
               evidence_path=f"evidence:capability-scout/{path}", notes=notes)


def later(ev, zip_dir):
    out = []
    s3, h3, p3 = zip_hashes(zip_dir, "0.3.1")
    # v0.3.1: one live 4-turn continuity session.
    c = json.load(open(os.path.join(ev, "prototype/test-evidence/v0.3.1/live-continuity.json")))
    ok = sum(t.get("ok") is True for t in c["turns"])
    cost = round(sum(t.get("cost_usd") or 0 for t in c["turns"]), 4)
    out.append(one_session("legacy-v0.3.1-continuity", 1, "0.3.1", s3, h3, "C1-continuity", c["cond"],
                           DEFAULT_MODEL_NOTE, "2.1.302 (from the report)",
                           "prototype/test-evidence/v0.3.1/live-continuity.json", "", "", cost,
                           f"multi-turn; {ok}/{len(c['turns'])} turns correct; per-turn summary kept, transcript not kept",
                           "2026-10-17"))
    # v0.3.1 scripted six-turn session: the raw event stream is kept.
    out.append(one_session("legacy-v0.3.1-scripted-trial", 1, "0.3.1", s3, h3, "six scripted turns", "trial settings, hook on",
                           "claude-sonnet-5-5 (recorded in session.jsonl)", "2.1.302 (recorded in session.jsonl)",
                           "prototype/test-evidence/interactive-trial/session.jsonl", "", "", "0.42",
                           "multi-turn; verdicts per behavior are in interactive-trial-report.md (not re-scored); "
                           "full transcript kept; cost from the report", "2026-10-17"))
    # v0.3.1 vs v0.3.2 focused regression: raw session logs are kept.
    s2, h2, _ = zip_hashes(zip_dir, "0.3.2")
    scored = json.load(open(os.path.join(ev, "prototype/test-evidence/v0.3.2/scored.json")))
    for i, sess in enumerate(scored, 1):
        v = "0.3.1" if sess["version"] == "v031" else "0.3.2"
        sk, hk = (s3, h3) if v == "0.3.1" else (s2, h2)
        first = sess["turns"][0]
        log = f"prototype/test-evidence/v0.3.2/sessions/{sess['version']}-{sess['scenario']}-{sess['run']}.jsonl"
        turns = "; ".join(f"T{t['turn']}: request={t['assessment_request']}, skill={t['scout_skill']}, "
                          f"reminder={t['approval_reminder']}, attempts={len(t['attempts'])}" for t in sess["turns"])
        out.append(one_session("legacy-v0.3.2-regression", i, v, sk, hk, sess["scenario"], "trial settings, hook on",
                               "claude-sonnet-5-5 (recorded in the session log)", "2.1.302 (recorded in the session log)",
                               log, b(first["scout_skill"]), "",
                               round(sess["turns"][-1]["cumulative_cost_usd"], 4),
                               f"multi-turn; activated = skill ran on turn 1; {turns}; full transcript kept", "2026-10-17"))
    # Supervised session on a Mac: no raw data in the project.
    out.append(one_session("legacy-v0.3.2-supervised-mac", 1, "0.3.2", s2, h2, "seven scripted prompts (LIVE-TRIAL.md)",
                           "pilot settings, hook on", "not recorded in project files", "2.1.299 (from the closeout report)",
                           "scout-v0.3.2-trial-closeout.md", "", "", "",
                           "human-supervised, interactive; report only; transcript is on the user's computer and was "
                           "not verified here; the install-prompt check was INCOMPLETE",
                           "2026-10-17"))
    return out


def offline(zip_dir):
    """Offline suites: not model sessions. One row per suite run, activated left blank."""
    rows = []
    s, h, _ = zip_hashes(zip_dir, "0.3.3")
    suites = [("test_pasted_and_followups", "28/28"), ("test_hook_classifier", "88/88"), ("test_state_and_storage", "59/59")]
    for i, (name, res) in enumerate(suites, 1):
        rows.append(row(run_id=f"legacy-v0.3.3-offline:{i:03d}", date_utc="2026-10-27T18:27:54Z", edition="plugin",
                        plugin_version="0.3.3", skill_sha256=s, hook_sha256=h, task_set_version="offline suites",
                        task_id=name, arm="offline", model_id="none (no model calls)",
                        claude_code_version="2.1.311 (from v0.3.3-fix-report.md)", environment="cloud container, python3",
                        evidence_path="evidence:capability-scout/capability-scout-v0.3.3-candidate.zip#"
                                      "capability-scout/prototype/test-evidence/v0.3.3/offline-tests.txt",
                        notes=f"offline suite, not a model session; result {res}"))
    return rows


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ev, zip_dir = argv[1], argv[2]
    s0, h0, p0 = zip_hashes(zip_dir, "0.2.0")
    s30, h30, p30 = zip_hashes(zip_dir, "0.3.0")
    rows = (phase1(ev)
            + live_csv(ev, "prototype/test-evidence/final-refinement/live-runs.csv", "legacy-v0.2.0-final-refinement",
                       "0.2.0", s0, h0, p0, "round")
            + live_csv(ev, "prototype/test-evidence/source-review/live-runs.csv", "legacy-v0.3.0-source-review",
                       "0.3.0", s30, h30, p30, "set")
            + later(ev, zip_dir) + offline(zip_dir))
    ids = [r["run_id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate run_id"
    for r in rows:
        p = validate_row(r)
        assert not p, (r["run_id"], p)
    text = header_line() + "".join(row_to_csv_line(r) for r in rows)
    if os.path.exists(LEDGER):
        cur = open(LEDGER, encoding="utf-8").read()
        if cur.startswith(text):
            print(f"legacy rows already present and unchanged ({len(rows)} rows)")
            return 0
        print("REFUSED: the ledger exists and does not start with exactly these legacy rows", file=sys.stderr)
        return 1
    if "--check" in argv:
        print(f"would write {len(rows)} rows")
        return 0
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"wrote {len(rows)} legacy rows to {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
