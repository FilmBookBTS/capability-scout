#!/usr/bin/env python3
"""Generate results/RESULTS.md and the chart from results/ledger.csv. Nothing else feeds them.

Usage: python3 -I tools/summarize.py [--check]

Inputs (all in results/):
  ledger.csv        one row per session (append-only)
  superseded.csv    batch,reason  -> those batches are labeled SUPERSEDED (never removed)
  claims.csv        figures stated in earlier reports, with the recomputed value and a status
  annotations.csv   later findings about imported rows (rows themselves are never edited)
  chat-runs.csv     rows recorded by hand with docs/CHAT_PROTOCOL.md (edition=chat); optional
  chart.json        which ledger rows make each bar of the chart

--check regenerates in memory and exits 1 if RESULTS.md or the chart on disk differ, so the
committed summary can never disagree with the ledger.

Rates use the Wilson score interval at 95%. Repeated runs of the same task are not independent,
so the interval is narrower than it should be; RESULTS.md says so next to every table.
"""
import csv
import json
import math
import os
import sys
from collections import OrderedDict, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger_schema import LEDGER_COLUMNS, validate_row  # noqa: E402

REPO = os.path.dirname(HERE)
RES = os.path.join(REPO, "results")
Z = 1.959964


def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(x):
    return "n/a" if x != x else f"{100 * x:.0f}%"


def read_csv(name, required=True):
    path = os.path.join(RES, name)
    if not os.path.exists(path):
        if required:
            raise SystemExit(f"missing {path}")
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def batch_of(r):
    return r["run_id"].split(":")[0]


def round_of(r):
    """Legacy rows carry their test round in notes ("round=r2-default; ..."). New runs have one round."""
    n = r["notes"]
    if n.startswith("round="):
        return n.split(";")[0][len("round="):] or "-"
    return "-"


def frac_or_na(rs, col):
    vals = [r[col] for r in rs if r[col] in ("true", "false")]
    return f"{sum(v == 'true' for v in vals)}/{len(vals)}" if vals else "not recorded"


def load_rows():
    rows = read_csv("ledger.csv")
    for r in rows:
        p = validate_row(r)
        if p:
            raise SystemExit(f"ledger row {r.get('run_id')} invalid: {p}")
    chat = []
    for i, x in enumerate(read_csv("chat-runs.csv", required=False), 1):
        if not any(x.values()) or not x.get("run_id"):
            continue  # blank template line
        r = {c: x.get(c, "") for c in LEDGER_COLUMNS}
        r["edition"] = "chat"
        p = validate_row(r)
        if p:
            raise SystemExit(f"chat-runs.csv line {i + 1} invalid: {p}")
        chat.append(r)
    return rows, chat


def short_model(m):
    return m.split(" ")[0]


def group(rows, keyf):
    g = OrderedDict()
    for r in rows:
        g.setdefault(keyf(r), []).append(r)
    return g


def rate_cell(rs, col):
    k = sum(r[col] == "true" for r in rs)
    n = len(rs)
    lo, hi = wilson(k, n)
    return k, n, f"{k}/{n}", pct(k / n if n else float("nan")), f"{pct(lo)} to {pct(hi)}"


def bar_rows(rows, flt):
    out = []
    for r in rows:
        if flt.get("batch") and batch_of(r) != flt["batch"]:
            continue
        if flt.get("batch_contains") and flt["batch_contains"] not in batch_of(r):
            continue
        if flt.get("task_set") and r["task_set_version"] != flt["task_set"]:
            continue
        if flt.get("arm") and r["arm"] != flt["arm"]:
            continue
        if flt.get("model_prefix") and not r["model_id"].startswith(flt["model_prefix"]):
            continue
        if flt.get("notes_contains") and flt["notes_contains"] not in r["notes"]:
            continue
        if r["activated"] not in ("true", "false") or r["false_trigger"] != "":
            continue
        out.append(r)
    return out


TRIVIAL_KINDS = {"greeting", "arithmetic", "single-fact"}
NAMED_KINDS = {"names-other-tool"}


def task_kinds():
    """task_set_version -> {task_id: kind}, from every tests/live/tasks*.json."""
    d = os.path.join(REPO, "tests", "live")
    out = {}
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not (name.startswith("tasks") and name.endswith(".json")):
            continue
        t = json.load(open(os.path.join(d, name)))
        kinds = {x["id"]: "substantive" for x in t["substantive"]}
        kinds.update({x["id"]: x["kind"] for x in t["non_substantive"]})
        out[t["task_set_version"]] = kinds
    return out


def manifests():
    out = {}
    base = os.path.join(RES, "runs")
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            m = os.path.join(base, d, "manifest.json")
            if os.path.exists(m):
                out[d] = json.load(open(m))
    return out


# Live batches reported on their own and left out of every rate, with the reason (see the plan named).
SEPARATE_BATCHES = {
    "20261111T190136Z-v0.4.1-ts2-s1-default": "stopped after 18 sessions: `--model` was not given and Claude Code "
    "2.1.322's default model served Opus, not Sonnet as for 0.4.0; the models were then requested by name "
    "(docs/ANALYSIS_PLAN_0.4.1.md, Changes)",
}


def separate_section(rows):
    sep = [r for r in rows if batch_of(r) in SEPARATE_BATCHES]
    if not sep:
        return []
    L = ["### Batches left out of the rates", "",
         "| Batch | Task set | Model served | Rows | Invalid | Cost (USD) | Why left out |", "|---|---|---|---|---|---|---|"]
    for bt, rs in group(sep, batch_of).items():
        L.append(f"| {bt} | {rs[0]['task_set_version']} | {', '.join(sorted({r['model_id'] for r in rs}))} | {len(rs)} | "
                 f"{sum('invalid:' in r['notes'] for r in rs)} | {sum(float(r['cost_usd'] or 0) for r in rs):.2f} | "
                 f"{SEPARATE_BATCHES[bt]} |")
    return L + [""]


def live_section(rows):
    sep_lines = separate_section(rows)
    rows = [r for r in rows if batch_of(r) not in SEPARATE_BATCHES]
    live = [r for r in rows if r["task_set_version"].startswith("ts-")]
    if not live:
        return []
    kinds_by_ts = task_kinds()
    mans = manifests()
    L = ["## Live test with the current harness", "",
         "Definitions, arms and pass criteria: [`docs/ANALYSIS_PLAN.md`](../docs/ANALYSIS_PLAN.md). Invalid sessions "
         "are left out of every rate and counted below.", ""]
    valid = [r for r in live if "invalid:" not in r["notes"]]
    sub = [r for r in valid if r["false_trigger"] == "" and r["activated"] in ("true", "false")]
    non = [r for r in valid if r["false_trigger"] in ("true", "false")]
    key = lambda r: (r["task_set_version"], r["edition"], short_model(r["model_id"]), r["arm"])  # noqa: E731
    L += ["### Activation on substantive tasks", "",
          "| Task set | Edition | Model | Arm | Activated | Rate | 95% interval | Scout before work (all) | "
          "Scout before work (of activated) |", "|---|---|---|---|---|---|---|---|---|"]
    for (ts, ed, mod, arm), rs in sorted(group(sub, key).items()):
        _, _, frac, rate, ci = rate_cell(rs, "activated")
        act = [r for r in rs if r["activated"] == "true"]
        L.append(f"| {ts} | {ed} | {mod} | {arm} | {frac} | {rate} | {ci} | {frac_or_na(rs, 'scout_before_work')} | "
                 f"{frac_or_na(act, 'scout_before_work') if act else 'none activated'} |")
    L.append("")
    L += ["### False triggers on non-substantive prompts", "",
          "Plainly trivial: greetings, arithmetic and single facts. Names another tool: the prompt asks for a "
          "specific other skill or tool. Pooled: all non-substantive prompts.", "",
          "| Task set | Edition | Model | Arm | Prompts | False triggers | Rate | 95% interval |",
          "|---|---|---|---|---|---|---|---|"]
    for (ts, ed, mod, arm), rs in sorted(group(non, key).items()):
        kinds = kinds_by_ts.get(ts, {})
        for label, sel in (("plainly trivial", lambda r: kinds.get(r["task_id"]) in TRIVIAL_KINDS),
                           ("names another tool", lambda r: kinds.get(r["task_id"]) in NAMED_KINDS),
                           ("pooled", lambda r: True)):
            part = [r for r in rs if sel(r)]
            if not part:
                continue
            _, _, frac, rate, ci = rate_cell(part, "false_trigger")
            L.append(f"| {ts} | {ed} | {mod} | {arm} | {label} ({len({r['task_id'] for r in part})} prompts) | "
                     f"{frac} | {rate} | {ci} |")
    L.append("")
    L += ["### False triggers by prompt", "", "| Task set | Model | Arm | Prompt | Kind | False triggers |",
          "|---|---|---|---|---|---|"]
    for (ts, mod, arm, task), rs in sorted(group(non, lambda r: (r["task_set_version"], short_model(r["model_id"]),
                                                                  r["arm"], r["task_id"])).items()):
        L.append(f"| {ts} | {mod} | {arm} | {task} | {kinds_by_ts.get(ts, {}).get(task, '?')} | "
                 f"{sum(r['false_trigger'] == 'true' for r in rs)}/{len(rs)} |")
    L.append("")
    inv = [r for r in live if "invalid:" in r["notes"]]
    L += ["### Invalid sessions", ""]
    if not inv:
        L += ["None.", ""]
    else:
        L += ["| Batch | Model | Arm | Reason | Sessions |", "|---|---|---|---|---|"]
        for (bt, mod, arm, why), rs in sorted(group(inv, lambda r: (batch_of(r), short_model(r["model_id"]), r["arm"],
                                                                     r["notes"].split("invalid: ")[1])).items()):
            L.append(f"| {bt} | {mod} | {arm} | {why} | {len(rs)} |")
        L.append("")
    L += ["### Cost by model and arm", "",
          "Cost as reported by Claude Code for each valid session, in US dollars.", "",
          "| Task set | Model | Arm | Substantive sessions | Mean per substantive session | All sessions | "
          "Mean per session | Total |", "|---|---|---|---|---|---|---|---|"]
    for (ts, mod, arm), rs in sorted(group(valid, lambda r: (r["task_set_version"], short_model(r["model_id"]),
                                                             r["arm"])).items()):
        cs = [float(r["cost_usd"]) for r in rs if r["cost_usd"]]
        ss = [float(r["cost_usd"]) for r in rs if r["cost_usd"] and r["false_trigger"] == ""]
        L.append(f"| {ts} | {mod} | {arm} | {len(ss)} | {sum(ss) / len(ss):.3f} | {len(cs)} | "
                 f"{sum(cs) / len(cs):.3f} | {sum(cs):.2f} |" if ss and cs else f"| {ts} | {mod} | {arm} | 0 | n/a | {len(cs)} | n/a | n/a |")
    L.append("")
    L += ["### Completeness and cost by batch", "",
          "| Batch | Status | Planned | Recorded | Invalid | Cost (USD) | Mean per recorded session |",
          "|---|---|---|---|---|---|---|"]
    missing_cells = []
    by_batch = group(live, batch_of)
    children = defaultdict(list)  # interrupted run -> runs that finished it (manifest "resumes")
    for bt in by_batch:
        if mans.get(bt, {}).get("resumes"):
            children[mans[bt]["resumes"]].append(bt)
    for bt, rs in by_batch.items():
        m = mans.get(bt, {})
        planned = m.get("sessions_planned", "?")
        cost = sum(float(r["cost_usd"]) for r in rs if r["cost_usd"])
        status = m.get("status", "no manifest")
        if children.get(bt):
            status = f"interrupted; finished by {', '.join(children[bt])}"
        elif m.get("resumes"):
            status = f"{status}; finishes {m['resumes']}"
        L.append(f"| {bt} | {status} | {planned} | {len(rs)} | "
                 f"{sum('invalid:' in r['notes'] for r in rs)} | {cost:.2f} | {cost / len(rs):.4f} |")
        if m.get("order") and not m.get("resumes"):
            rs = rs + [r for c in children.get(bt, []) for r in by_batch[c]]
            want = defaultdict(int)
            for _, task, arm, model, _rep in m["order"]:
                want[(task, arm, model)] += 1
            got = defaultdict(int)
            arm_label = {k: v["label"] for k, v in m.get("arms", {}).items()}
            for r in rs:
                got[(r["task_id"], r["arm"])] += 1
            for (task, arm, model), n in sorted(want.items()):
                g = got[(task, arm_label.get(arm, arm))]
                if g < n:
                    missing_cells.append(f"| {bt} | {model} | {arm_label.get(arm, arm)} | {task} | {g} of {n} |")
    L.append("")
    if missing_cells:
        L += ["Incomplete cells (fewer sessions recorded than planned):", "",
              "| Batch | Model | Arm | Task | Recorded |", "|---|---|---|---|---|"] + missing_cells + [""]
    else:
        L += ["Every planned session in these batches has a ledger row.", ""]
    return L + sep_lines


def chart_alt(spec, bars):
    return spec["alt_prefix"] + " " + " ".join(
        f"{l}: {k} of {n} sessions ({pct(k / n) if n else 'no data'})." for l, k, n in bars)


def svg_chart(spec, rows):
    bars = []
    for b in spec["bars"]:
        rs = bar_rows(rows, b["filter"])
        k = sum(r["activated"] == "true" for r in rs)
        bars.append((b["label"], k, len(rs)))
    W, H, left, bottom, top = spec.get("width", 640), 400, 70, 70, 70
    plot_h = H - bottom - top
    bw = 140 if len(bars) > 2 else 120
    gap = (W - left - 30 - bw * len(bars)) / (len(bars) + 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d">',
             f'<title id="t">{spec["title"]}</title>',
             f'<desc id="d">{"; ".join(f"{l}: {k} of {n} sessions activated" for l, k, n in bars)}.</desc>',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             f'<text x="{W / 2}" y="28" font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" '
             f'fill="#111">{spec["title"]}</text>']
    for t in range(0, 101, 25):
        y = top + plot_h * (1 - t / 100)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W - 30}" y2="{y:.1f}" stroke="#ddd"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="12" '
                     f'text-anchor="end" fill="#444">{t}%</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#444"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{W - 30}" y2="{top + plot_h}" stroke="#444"/>')
    for i, (label, k, n) in enumerate(bars):
        x = left + gap * (i + 1) + bw * i
        rate = k / n if n else 0
        h = plot_h * rate
        y = top + plot_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{h:.1f}" fill="{"#4a6fa5" if i % 2 else "#9aa9bf"}"/>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{y - 8:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="14" '
                     f'text-anchor="middle" fill="#111">{pct(rate) if n else "no data"}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{top + plot_h + 20}" font-family="Helvetica, Arial, sans-serif" '
                     f'font-size="13" text-anchor="middle" fill="#111">{label}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{top + plot_h + 38}" font-family="Helvetica, Arial, sans-serif" '
                     f'font-size="12" text-anchor="middle" fill="#444">{k} of {n} sessions</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" font-family="Helvetica, Arial, sans-serif" font-size="12" '
                 f'text-anchor="middle" fill="#444" transform="rotate(-90 18 {top + plot_h / 2})">Sessions where the skill ran</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n", bars


def render(rows, chat):
    superseded = {x["batch"]: x["reason"] for x in read_csv("superseded.csv", required=False)}
    claims = read_csv("claims.csv", required=False)
    spec = json.load(open(os.path.join(RES, "chart.json")))
    allrows = rows + chat
    L = ["# Results", "",
         "Generated by `tools/summarize.py` from [`ledger.csv`](ledger.csv). Do not edit by hand; run the script.", "",
         "How to read these tables:", "",
         "- A **session** is one fresh Claude Code (or chat) conversation. Counts are sessions, not tasks.",
         "- **Activated** means the Capability Scout skill ran in that session. **Scout before work** means it ran "
         "before any other work tool. Definitions: [`docs/ANALYSIS_PLAN.md`](../docs/ANALYSIS_PLAN.md).",
         "- The 95% interval is a Wilson score interval. Repeated runs of the same task are not independent, so the "
         "interval is narrower than it should be. A rate here is a measured rate for that task set, not a promise "
         "for all tasks.",
         "- Batches whose names start with `legacy-` were imported from earlier evidence. Their `notes` column says "
         "how good that evidence is.", ""]
    # Chart
    svg, bars = svg_chart(spec, rows)
    L += ["## Chart", "", f"![{chart_alt(spec, bars)}]({spec['file']})", "", f"*{spec['caption']}*", "",
          "Text version: " + "; ".join(f"{l}: {k} of {n} sessions" for l, k, n in bars) + ".", ""]
    # Activation by batch
    L += ["## Activation on substantive tasks, by batch, version, model and arm", "",
          "Legacy rounds are kept apart because the skill text changed between rounds.", "",
          "| Batch | Round | Status | Edition | Version | Model | Arm | Activated | Rate | 95% interval | Scout before work |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    sub = [r for r in allrows if r["activated"] in ("true", "false") and r["false_trigger"] == ""]
    for (bt, rd, ed, ver, mod, arm), rs in group(sub, lambda r: (batch_of(r), round_of(r), r["edition"],
                                                                   r["plugin_version"], short_model(r["model_id"]),
                                                                   r["arm"])).items():
        _, _, frac, rate, ci = rate_cell(rs, "activated")
        status = f"SUPERSEDED: {superseded[bt]}" if bt in superseded else "current"
        L.append(f"| {bt} | {rd} | {status} | {ed} | {ver} | {mod} | {arm} | {frac} | {rate} | {ci} | "
                 f"{frac_or_na(rs, 'scout_before_work')} |")
    L.append("")
    # False triggers
    L += ["## False triggers on non-substantive prompts", "",
          "A false trigger is a session on a non-substantive prompt (greeting, arithmetic, single fact, a request "
          "that names a different tool) in which Capability Scout ran.", "",
          "| Batch | Status | Edition | Version | Model | Arm | False triggers | Rate | 95% interval |",
          "|---|---|---|---|---|---|---|---|---|"]
    ft = [r for r in allrows if r["false_trigger"] in ("true", "false")]
    for (bt, ed, ver, mod, arm), rs in group(ft, lambda r: (batch_of(r), r["edition"], r["plugin_version"],
                                                              short_model(r["model_id"]), r["arm"])).items():
        _, _, frac, rate, ci = rate_cell(rs, "false_trigger")
        status = f"SUPERSEDED: {superseded[bt]}" if bt in superseded else "current"
        L.append(f"| {bt} | {status} | {ed} | {ver} | {mod} | {arm} | {frac} | {rate} | {ci} |")
    L.append("")
    # Per task, for batches that are not legacy
    cur = [r for r in sub if not batch_of(r).startswith("legacy-")]
    L += ["## Per-task activation (batches run with the current harness)", ""]
    if not cur:
        L += ["No sessions yet.", ""]
    else:
        L += ["| Batch | Model | Arm | Task | Activated |", "|---|---|---|---|---|"]
        for (bt, mod, arm, task), rs in group(cur, lambda r: (batch_of(r), short_model(r["model_id"]), r["arm"],
                                                               r["task_id"])).items():
            L.append(f"| {bt} | {mod} | {arm} | {task} | {sum(r['activated'] == 'true' for r in rs)}/{len(rs)} |")
        L.append("")
    # Multi-turn and offline rows
    other = [r for r in allrows if r["activated"] == "" and r["false_trigger"] == "" and "invalid:" not in r["notes"]]
    L += ["## Sessions without a single activation value, and offline test runs", "",
          "| Run | Version | Task | Arm | Result |", "|---|---|---|---|---|"]
    for r in other:
        L.append(f"| {r['run_id']} | {r['plugin_version']} | {r['task_id']} | {r['arm']} | {r['notes']} |")
    L.append("")
    L += live_section(allrows)
    # Annotations to imported rows (ledger rows are never edited; corrections and later findings go here)
    notes = read_csv("annotations.csv", required=False)
    if notes:
        L += ["## Annotations to imported rows", "",
              "Ledger rows are never edited. When later work changes what is known about earlier rows, the change "
              "is recorded here and the rows stay as they were.", "",
              "| Id | Date | Applies to | Annotation |", "|---|---|---|---|"]
        for a in notes:
            L.append(f"| {a['annotation_id']} | {a['date_utc']} | {a['applies_to']} | {a['annotation']} |")
        L.append("")
    # Claims
    L += ["## Figures from earlier reports, checked against the ledger", "",
          "| Claim | Reported in | As reported | Recomputed | Status | Note |", "|---|---|---|---|---|---|"]
    for c in claims:
        L.append(f"| {c['claim_id']} | {c['source_document']} ({c['source_location']}) | {c['claim_as_reported']} | "
                 f"{c['recomputed_value']} | {c['status']} | {c['note']} |")
    L.append("")
    return "\n".join(L), svg


README = os.path.join(REPO, "README.md")
START = "<!-- results:start (generated by tools/summarize.py from results/ledger.csv; do not edit by hand) -->"
END = "<!-- results:end -->"
LIVE_A = "results/RESULTS.md#activation-on-substantive-tasks"
LIVE_F = "results/RESULTS.md#false-triggers-on-non-substantive-prompts"
LEGACY_A = "results/RESULTS.md#activation-on-substantive-tasks-by-batch-version-model-and-arm"


def kofn(rs, col):
    return f"{sum(r[col] == 'true' for r in rs)} of {len(rs)}"


def ts3_block(rows):
    """README table for the 0.4.2 retest (task set ts-3, arm C only)."""
    kinds = task_kinds().get("ts-3", {})
    live = [r for r in rows if r["task_set_version"] == "ts-3" and "invalid:" not in r["notes"]
            and batch_of(r) not in SEPARATE_BATCHES]
    if not live:
        return []
    allrows = [r for r in rows if r["task_set_version"] == "ts-3" and batch_of(r) not in SEPARATE_BATCHES]
    models = [("claude-sonnet", "Sonnet (`claude-sonnet-5-5`)"), ("claude-opus", "Opus (`claude-opus-5-5`)")]
    L = [f"**Retest, version 0.4.2:** {len(live):,} sessions, Claude Code "
         f"{', '.join(sorted({r['claude_code_version'] for r in live}))}, "
         f"{min(r['date_utc'][:10] for r in live)}, plugin as published (hook on), each model requested by name. "
         "Task set ts-3 covers only the two cases 0.4.2 changed, plus controls; each prompt ran 3 times per model. "
         f"Invalid sessions: {len(allrows) - len(live)}.", "",
         "| Sessions where the skill ran | " + " | ".join(lab for _, lab in models) + " |", "|---|---|---|"]
    spec = [
        ("Web-research tasks (\"Search ...\", \"Look up ...\")", lambda k: k == "substantive", "activated", LIVE_A),
        ("Controls: trivial prompts and prompts naming another tool", lambda k: k in TRIVIAL_KINDS | NAMED_KINDS,
         "false_trigger", LIVE_F),
        ("Requests to start a background agent (their own text)", lambda k: k == "background-agent",
         "false_trigger", LIVE_F),
    ]
    for label, sel, col, link in spec:
        cells = []
        for m, _ in models:
            rs = [r for r in live if r["model_id"].startswith(m) and sel(kinds.get(r["task_id"])) and r[col] in ("true", "false")]
            k = sum(r[col] == "true" for r in rs)
            cells.append(f"[{k} of {len(rs)}]({link}) ({pct(k / len(rs)) if rs else 'n/a'})")
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    return L + ["", "*Source: rows with task set ts-3 in results/ledger.csv. Plan and pass criteria, set before the run: "
                "[docs/ANALYSIS_PLAN_0.4.2.md](docs/ANALYSIS_PLAN_0.4.2.md). Messages from background agents are counted "
                "from the session transcripts, not the ledger: "
                "[hook-events.txt](results/runs/20261111T223611Z-v0.4.2-ts3/hook-events.txt).*", ""]


def ts2_block(rows):
    """README table for the 0.4.1 live test (task set ts-2, arms B and C)."""
    kinds = task_kinds().get("ts-2", {})
    live = [r for r in rows if r["task_set_version"] == "ts-2" and "invalid:" not in r["notes"]
            and batch_of(r) not in SEPARATE_BATCHES]
    if not live:
        return []

    def pick(arm, model, sel, col):
        return [r for r in live if r["arm"] == arm and r["model_id"].startswith(model)
                and r[col] in ("true", "false") and (r["false_trigger"] == "") == (sel is None)
                and (sel is None or sel(kinds.get(r["task_id"])))]
    models = [("claude-sonnet", "Sonnet (`claude-sonnet-5-5`)"), ("claude-opus", "Opus (`claude-opus-5-5`)")]
    allrows = [r for r in rows if r["task_set_version"] == "ts-2" and batch_of(r) not in SEPARATE_BATCHES]
    L = [f"**Live test, version 0.4.1:** {len(live):,} sessions, Claude Code "
         f"{', '.join(sorted({r['claude_code_version'] for r in live}))}, "
         f"{min(r['date_utc'][:10] for r in live)}, with each model requested by name. New task set ts-2: "
         "24 substantive tasks (8 of them near-misses that mention a tool, a skill or units) and 24 non-substantive "
         f"prompts, each run 3 times per setup. Invalid sessions: {len(allrows) - len(live)}.", "",
         "| Sessions where the skill ran | " + " | ".join(lab for _, lab in models) + " |", "|---|---|---|"]
    spec = [
        ("Substantive, plugin as published (hook on)", "C-published-default", None, LIVE_A),
        ("Near-miss substantive tasks, hook on", "C-published-default", "NM", LIVE_A),
        ("Substantive, hook off", "B-skill-hook-off", None, LIVE_A),
        ("Trivial prompts (greetings, arithmetic, facts), hook on", "C-published-default",
         lambda k: k in TRIVIAL_KINDS, LIVE_F),
        ("Prompts naming another skill or tool, hook on", "C-published-default", lambda k: k in NAMED_KINDS, LIVE_F),
        ("All non-substantive prompts, hook on", "C-published-default", lambda k: True, LIVE_F),
    ]
    for label, arm, sel, link in spec:
        cells = []
        for m, _ in models:
            if sel == "NM":
                rs = [r for r in pick(arm, m, None, "activated") if r["task_id"].startswith("NM")]
            else:
                rs = pick(arm, m, sel if link == LIVE_F else None, "activated" if link == LIVE_A else "false_trigger")
            col = "activated" if link == LIVE_A else "false_trigger"
            k = sum(r[col] == "true" for r in rs)
            cells.append(f"[{k} of {len(rs)}]({link}) ({pct(k / len(rs)) if rs else 'n/a'})")
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    return L + ["", "*Source: rows with task set ts-2 in results/ledger.csv. Plan and pass criteria, set before the run: "
                "[docs/ANALYSIS_PLAN_0.4.1.md](docs/ANALYSIS_PLAN_0.4.1.md).*", ""]


def readme_block(rows, spec, bars):
    kinds = task_kinds().get("ts-1", {})
    live = [r for r in rows if r["task_set_version"] == "ts-1" and "invalid:" not in r["notes"]]

    def sub(arm, model):
        return [r for r in live if r["arm"] == arm and r["model_id"].startswith(model) and r["false_trigger"] == ""
                and r["activated"] in ("true", "false")]

    def non(arm, model, sel):
        return [r for r in live if r["arm"] == arm and r["model_id"].startswith(model)
                and r["false_trigger"] in ("true", "false") and sel(kinds.get(r["task_id"]))]
    models = [("claude-sonnet", "Default model"), ("claude-opus", "Opus")]
    ids = sorted({short_model(r["model_id"]) for r in live})
    L = [START, ""] + ts3_block(rows) + ts2_block(rows) + [
         f"**Live test, version 0.4.0:** {len(live):,} sessions, Claude Code "
         f"{', '.join(sorted({r['claude_code_version'] for r in live}))}, "
         f"{min(r['date_utc'][:10] for r in live)} to {max(r['date_utc'][:10] for r in live)}. "
         "30 substantive tasks and 12 non-substantive prompts, each run 3 times per setup.", "",
         "| Sessions where the skill ran | " + " | ".join(
             f"{label} (`{next((i for i in ids if i.startswith(pre)), pre)}`)" for pre, label in models) + " |",
         "|---|---|---|"]
    rows_spec = [
        ("Substantive, plugin as published (hook on)", lambda m: sub("C-published-default", m), LIVE_A),
        ("Substantive, hook off", lambda m: sub("B-skill-hook-off", m), LIVE_A),
        ("Substantive, no plugin", lambda m: sub("A-no-plugin", m), LIVE_A),
        ("Substantive, chat edition text in Claude Code", lambda m: sub("T-chat-text-in-code", m), LIVE_A),
        ("Trivial prompts (greetings, arithmetic, facts), hook on",
         lambda m: non("C-published-default", m, lambda k: k in TRIVIAL_KINDS), LIVE_F),
        ("Prompts naming another skill or tool, hook on",
         lambda m: non("C-published-default", m, lambda k: k in NAMED_KINDS), LIVE_F),
        ("All non-substantive prompts, hook on", lambda m: non("C-published-default", m, lambda k: True), LIVE_F),
    ]
    for label, f, link in rows_spec:
        cells = []
        for m, _ in models:
            rs = f(m)
            col = "activated" if link == LIVE_A else "false_trigger"
            k = sum(r[col] == "true" for r in rs)
            cells.append(f"[{k} of {len(rs)}]({link}) ({pct(k / len(rs)) if rs else 'n/a'})")
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += ["", f"![{chart_alt(spec, bars)}](results/{spec['file']})", "", f"*{spec['caption']}*", ""]
    # Earlier prototype (phase 1)
    allp1 = [r for r in rows if batch_of(r) == "legacy-phase1"]
    n_triv = sum(r["false_trigger"] in ("true", "false") for r in allp1)
    ph = [r for r in allp1 if r["false_trigger"] == ""]

    def p1(rnd, arm, model):
        rs = [r for r in ph if round_of(r).startswith(rnd) and r["arm"] == arm and r["model_id"].startswith(model)]
        return f"[{kofn(rs, 'activated')}]({LEGACY_A})" if rs else "not run"

    def cnt(rnd, arm, model):
        return kofn([r for r in ph if round_of(r).startswith(rnd) and r["arm"] == arm and r["model_id"].startswith(model)],
                    "activated")
    L += ["### Earlier prototype results (phase 1, 2026-10-17)", "",
          "From an earlier prototype, not version 0.4.0. Sessions where the skill ran, on 7 or 8 substantive "
          "tasks; only a summary row per session survives.", "",
          "| Round and model | Skill only | Skill + nudge hook | Skill + directive hook | Skill + digest hook |",
          "|---|---|---|---|---|"]
    for rnd, model, label in (("r1", "claude-sonnet", "Round 1, default model"),
                              ("r2-default", "claude-sonnet", "Round 2, default model"),
                              ("r2-opus", "opus", "Round 2, Opus"),
                              ("r3-default", "claude-sonnet", "Round 3, default model"),
                              ("r3-opus", "opus", "Round 3, Opus")):
        L.append(f"| {label} | {p1(rnd, 'B-skill', model)} | {p1(rnd, 'C-skill+hook', model)} | "
                 f"{p1(rnd, 'D-skill+directive', model)} | {p1(rnd, 'E-skill+digest', model)} |")
    L += ["", "Read these with care:", "",
          f"- The {cnt('r2-default', 'D-skill+directive', 'claude-sonnet')} came from the **directive** hook. "
          f"Round 1's gentler **nudge** hook got {cnt('r1', 'C-skill+hook', 'claude-sonnet')}; the skill alone got "
          f"{cnt('r1', 'B-skill', 'claude-sonnet')}. Round 2's **digest** hook got "
          f"{cnt('r2-default', 'E-skill+digest', 'claude-sonnet')}.",
          "- The skill text and the hook were changed between rounds after results were seen, and the same tasks "
          "were reused.",
          f"- The phase-1 hook fired only on prompts of 8 or more words, and only {n_triv} of the {len(allp1)} sessions "
          "used a trivial prompt, so phase 1 says nothing about false triggers. The live test is the first test of "
          "that.", "", END]
    return "\n".join(L)


def main(argv):
    rows, chat = load_rows()
    md, svg = render(rows, chat)
    spec = json.load(open(os.path.join(RES, "chart.json")))
    md_path, svg_path = os.path.join(RES, "RESULTS.md"), os.path.join(RES, spec["file"])
    _, bars = svg_chart(spec, rows)
    readme_new = None
    if os.path.exists(README):
        cur = open(README, encoding="utf-8").read()
        if START in cur and END in cur:
            readme_new = cur[:cur.index(START)] + readme_block(rows, spec, bars) + cur[cur.index(END) + len(END):]
    if "--check" in argv:
        pairs = [(md_path, md), (svg_path, svg)] + ([(README, readme_new)] if readme_new is not None else [])
        bad = [p for p, t in pairs if not os.path.exists(p) or open(p, encoding="utf-8").read() != t]
        if bad:
            print("OUT OF DATE: " + ", ".join(os.path.relpath(p, REPO) for p in bad), file=sys.stderr)
            return 1
        print("RESULTS.md and chart match the ledger")
        return 0
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    if readme_new is not None:
        with open(README, "w", encoding="utf-8") as f:
            f.write(readme_new)
    print(f"wrote {os.path.relpath(md_path, REPO)} and {os.path.relpath(svg_path, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
