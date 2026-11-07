"""Shared definitions for the results ledger. Imported by the harness, the importer and the checks."""
import csv
import hashlib
import io

LEDGER_COLUMNS = [
    "run_id", "date_utc", "edition", "plugin_version", "plugin_commit", "skill_sha256", "hook_sha256",
    "harness_commit", "task_set_version", "task_id", "task_prompt_sha256", "arm", "model_id",
    "claude_code_version", "environment", "activated", "scout_before_work", "false_trigger", "cost_usd",
    "evidence_path", "notes",
]
EDITIONS = {"plugin", "chat", "chat-text-in-code"}
BOOL_OR_BLANK = {"true", "false", ""}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_to_csv_line(row):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow([row.get(c, "") for c in LEDGER_COLUMNS])
    return buf.getvalue()


def header_line():
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(LEDGER_COLUMNS)
    return buf.getvalue()


def validate_row(row):
    """Return a list of problems with one ledger row (dict)."""
    problems = []
    missing = [c for c in LEDGER_COLUMNS if c not in row]
    if missing:
        problems.append("missing columns: " + ",".join(missing))
    if row.get("edition") not in EDITIONS:
        problems.append(f"edition {row.get('edition')!r} not in {sorted(EDITIONS)}")
    for c in ("activated", "scout_before_work", "false_trigger"):
        if row.get(c, "") not in BOOL_OR_BLANK:
            problems.append(f"{c} must be true, false or blank, got {row.get(c)!r}")
    if not row.get("run_id"):
        problems.append("empty run_id")
    if not row.get("evidence_path"):
        problems.append("empty evidence_path")
    return problems
