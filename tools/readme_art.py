#!/usr/bin/env python3
"""Draw the animated SVG graphics used by README.md.

Usage: python3 -I tools/readme_art.py          write docs/images/readme/*.svg
       python3 -I tools/readme_art.py --check  exit 1 if a committed file differs from what this script draws

The results graphic is drawn from results/ledger.csv (task set ts-10, the 0.4.6 held-out test), with the
same row selection as the README table that tools/summarize.py writes, one dot per session. The demo
graphic replays the text of results/examples/ts1-stage1-default-ABC-0328.txt; it reads that file and
fails if a quoted line is not in it. Every animation stops under prefers-reduced-motion, and the
still frame is the finished picture.
"""
import os
import sys
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import summarize as S  # noqa: E402

REPO = S.REPO
OUT = os.path.join(REPO, "docs", "images", "readme")

BG, PANEL, EDGE = "#0B1220", "#111B2E", "#24324F"
TEXT, MUTED, DIM = "#E9EEF7", "#93A3BF", "#56657F"
MINT, AMBER, CORAL = "#5EE6C8", "#F5B544", "#FF7A6B"
SANS = "ui-sans-serif,'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,'SF Mono','Cascadia Code',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
REDUCE = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(w, h, title, desc, style, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n'
            f'<desc id="d">{escape(desc)}</desc>\n<style>{style}{REDUCE}</style>\n{body}\n</svg>\n')


def t(x, y, s, size, fill, family=SANS, weight=None, anchor=None, extra=""):
    a = f' font-weight="{weight}"' if weight else ""
    a += f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}"{a}{extra}>'
            f'{escape(s)}</text>')


def appear(name, period, at, hold_to=None):
    """Keyframes: hidden until `at` seconds, shown until `hold_to` (default: 92% of the period), then hidden.
    The element's own opacity is 1, so with animation off it is simply shown."""
    a = round(at / period * 100, 2)
    b = round(a + 0.5 / period * 100, 2)
    end = round((hold_to / period * 100) if hold_to else 92, 2)
    return (f".{name}{{animation:{name} {period}s linear infinite}}"
            f"@keyframes {name}{{0%,{a}%{{opacity:0;transform:translateY(6px)}}"
            f"{b}%,{end}%{{opacity:1;transform:none}}{min(end + 3, 100)}%,100%{{opacity:0;transform:none}}}}")


def typed(name, period, start, dur, chars, width):
    """A cover box slides off the text in `chars` steps. Its resting place is past the text, so with
    animation off the text is shown."""
    a, b = round(start / period * 100, 2), round((start + dur) / period * 100, 2)
    return (f".{name}{{animation:{name} {period}s infinite}}"
            f"@keyframes {name}{{0%,{a}%{{transform:translateX(-{width}px);animation-timing-function:steps({chars},end)}}"
            f"{b}%,100%{{transform:translateX(0)}}}}")


# ---------------------------------------------------------------- hero

def hero():
    W, H, P = 1280, 480, 12
    st = [".sweep{transform-origin:1010px 240px;animation:spin 6s linear infinite}",
          "@keyframes spin{to{transform:rotate(360deg)}}",
          ".caret{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"]
    b = [f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>',
         '<defs><radialGradient id="glow" cx="1010" cy="240" r="260" gradientUnits="userSpaceOnUse">'
         f'<stop offset="0" stop-color="{MINT}" stop-opacity=".10"/><stop offset="1" stop-color="{MINT}" stop-opacity="0"/>'
         '</radialGradient><linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">'
         f'<stop offset="0" stop-color="{MINT}" stop-opacity="0"/><stop offset="1" stop-color="{MINT}" stop-opacity=".38"/>'
         '</linearGradient></defs>',
         f'<circle cx="1010" cy="240" r="260" fill="url(#glow)"/>']
    # scope
    for r in (60, 120, 180):
        b.append(f'<circle cx="1010" cy="240" r="{r}" fill="none" stroke="{EDGE}" stroke-width="1.5"/>')
    b.append(f'<path d="M830 240H1190M1010 60V420" stroke="{EDGE}" stroke-width="1.5"/>')
    # beam: a 40-degree wedge whose leading edge points up, sweeping clockwise
    b.append(f'<g class="sweep"><path d="M1010 240L{1010 - 180 * 0.6428:.1f} {240 - 180 * 0.7660:.1f}'
             f'A180 180 0 0 1 1010 60Z" fill="url(#beam)"/>'
             f'<path d="M1010 240V60" stroke="{MINT}" stroke-width="2" stroke-opacity=".8"/></g>')
    # blips: (clockwise angle from up, radius, colour, style, label, label dx, anchor)
    import math
    blips = [(38, 120, MINT, "fill", "skill", 16, None),
             (112, 150, MINT, "fill", "built-in tool", 16, None),
             (200, 100, CORAL, "ring", "connector: needs sign-in", -16, "end"),
             (292, 140, MINT, "fill", "plugin", -16, "end"),
             (332, 205, AMBER, "dash", "worth adding", -16, "end")]
    for i, (ang, r, col, sty, lab, dx, anc) in enumerate(blips):
        x = 1010 + r * math.sin(math.radians(ang))
        y = 240 - r * math.cos(math.radians(ang))
        d = round(ang / 360 * 6, 2)
        st.append(f".p{i}{{transform-origin:{x:.1f}px {y:.1f}px;animation:ping 6s ease-out {d}s infinite}}")
        b.append(f'<circle class="p{i}" cx="{x:.1f}" cy="{y:.1f}" r="9" fill="none" stroke="{col}" stroke-width="2"/>')
        if sty == "fill":
            b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{col}"/>')
        elif sty == "ring":
            b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{BG}" stroke="{col}" stroke-width="2.5"/>')
        else:
            b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{BG}" stroke="{col}" stroke-width="2.5" stroke-dasharray="3 3"/>')
        b.append(t(round(x + dx, 1), round(y + 5, 1), lab, 15, MUTED, anchor=anc))
    st.append("@keyframes ping{0%{transform:scale(.6);opacity:.9}18%{transform:scale(2.4);opacity:0}100%{transform:scale(2.4);opacity:0}}")
    b.append(f'<circle cx="1010" cy="240" r="5" fill="{MINT}"/>')

    # words
    b.append(t(72, 92, "A SKILL FOR CLAUDE  ·  A PLUGIN FOR CLAUDE CODE", 15, AMBER, weight="600",
               extra=' letter-spacing="2"'))
    b.append(t(68, 170, "Capability Scout", 74, TEXT, weight="800", extra=' letter-spacing="-1.5"'))
    b.append(t(72, 214, "Checks what actually works here. Then does the work.", 25, MINT, weight="500"))
    # prompt pill
    prompt = "Review app.py for security vulnerabilities"
    b.append(f'<rect x="72" y="244" width="600" height="46" rx="12" fill="{PANEL}" stroke="{EDGE}"/>')
    b.append(t(92, 274, "›", 20, AMBER, MONO, "700"))
    b.append(t(116, 274, prompt, 18, TEXT, MONO))
    tw = len(prompt) * 11 + 14
    st.append(typed("ty", P, 0.3, 2.2, len(prompt), tw))
    b.append('<clipPath id="pill"><rect x="73" y="245" width="598" height="44" rx="11"/></clipPath>')
    b.append(f'<g clip-path="url(#pill)"><g class="ty"><rect x="{116 + tw}" y="252" width="{tw + 20}" height="32" fill="{PANEL}"/>'
             f'<rect class="caret" x="{116 + tw}" y="258" width="10" height="21" rx="2" fill="{MINT}"/></g></g>')
    # plan lines
    st.append(appear("h0", P, 2.8))
    b.append(f'<g class="h0">{t(72, 328, "Capability plan", 16, AMBER, MONO, "700")}</g>')
    lines = [(MINT, "Using", "my own read-only review of app.py"),
             (AMBER, "Worth adding", "a first-party security plugin"),
             (MUTED, "Not installed", "it asks for your approval first")]
    for i, (col, head, rest) in enumerate(lines):
        y = 362 + i * 32
        st.append(appear(f"l{i}", P, 3.3 + i * 0.55))
        b.append(f'<g class="l{i}"><rect x="72" y="{y - 12}" width="10" height="10" rx="2" fill="{col}"/>'
                 f'<text x="94" y="{y - 2}" font-family="{MONO}" font-size="16">'
                 f'<tspan fill="{col}" font-weight="700">{escape(head)}:</tspan>'
                 f'<tspan fill="{TEXT}"> {escape(rest)}</tspan></text></g>')
    desc = ("Capability Scout. A radar sweeps over the capabilities in a session: a skill, a built-in tool and "
            "a plugin that work, a connector that needs sign-in, and one worth adding. Beside it, a request is "
            "typed and Claude answers with a short capability plan before doing the work.")
    return svg(W, H, "Capability Scout", desc, "".join(st), "\n".join(b))


# ---------------------------------------------------------------- how it works

def flow():
    W, H = 1280, 290
    steps = [("You send", "a request", None, None),
             ("Is it substantive", "work?", "hook", "Claude Code only"),
             ("Which capabilities", "work here?", "skill", None),
             ("A short", "capability plan", "Claude", None),
             ("Do the task", "", "Claude", "installs nothing without approval")]
    cw, gap, x0, y0, ch = 214, 37, 44, 64, 160
    period = len(steps) * 1.6
    st = [f".fl{{animation:fl 1.2s linear infinite}}@keyframes fl{{to{{stroke-dashoffset:-20}}}}"]
    b = [f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>',
         t(44, 40, "HOW IT WORKS", 15, AMBER, weight="600", extra=' letter-spacing="2"')]
    for i, (l1, l2, who, note) in enumerate(steps):
        x = x0 + i * (cw + gap)
        a = round(i / len(steps) * 100, 2)
        z = round((i + 1) / len(steps) * 100, 2)
        st.append(f".g{i}{{opacity:0;animation:g{i} {period}s linear infinite}}"
                  f"@keyframes g{i}{{0%,{a}%{{opacity:0}}{round(a + 2, 2)}%,{z}%{{opacity:1}}{round(min(z + 4, 100), 2)}%,100%{{opacity:0}}}}")
        b.append(f'<rect x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="16" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.5"/>')
        b.append(f'<rect class="g{i}" x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="16" fill="none" stroke="{MINT}" stroke-width="2.5"/>')
        b.append(f'<circle cx="{x + 30}" cy="{y0 + 32}" r="15" fill="{AMBER}"/>')
        b.append(t(x + 30, y0 + 38, str(i + 1), 16, BG, weight="800", anchor="middle"))
        if who:
            b.append(t(x + cw - 18, y0 + 37, who, 14, MUTED, MONO, anchor="end"))
        b.append(t(x + 20, y0 + 84, l1, 19, TEXT, weight="700"))
        if l2:
            b.append(t(x + 20, y0 + 109, l2, 19, TEXT, weight="700"))
        if note:
            words, lines, cur = note.split(), [], ""
            for wd in words:
                if len(cur) + len(wd) + 1 > 22 and cur:
                    lines.append(cur)
                    cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            lines.append(cur)
            for k, ln in enumerate(lines):
                b.append(t(x + 20, y0 + 134 + k * 18 - (18 if len(lines) > 1 and not l2 else 0), ln, 14,
                           AMBER if i == 1 else MINT))
        if i < len(steps) - 1:
            b.append(f'<path class="fl" d="M{x + cw + 4} {y0 + ch / 2}H{x + cw + gap - 4}" stroke="{MINT}" '
                     f'stroke-width="2.5" stroke-dasharray="6 4"/>')
    b.append(t(44, 262, "In claude.ai chat there is no hook: Claude decides from the skill's description whether to run it.",
               15, MUTED))
    desc = ("Five steps from left to right: you send a request; in Claude Code a hook checks whether it is "
            "substantive work; the skill checks which capabilities work here; Claude shows a short capability "
            "plan; Claude does the task and installs nothing without approval. In claude.ai chat there is no hook.")
    return svg(W, H, "How Capability Scout works", desc, "".join(st), "\n".join(b))


# ---------------------------------------------------------------- results

def ts10_sessions():
    rows, _ = S.load_rows()
    live = [r for r in rows if r["task_set_version"] == "ts-10" and "invalid:" not in r["notes"]
            and S.batch_of(r) not in S.SEPARATE_BATCHES and r["arm"] != "offline"]
    kinds = S.task_kinds().get("ts-10", {})
    groups = [("Real tasks", "skill should run", lambda k: k == "substantive", "activated"),
              ("Quick look-ups on one file", "skill should stay quiet", lambda k: k == "held-out-lookup", "false_trigger"),
              ("Controls", "thanks, a fact, arithmetic, a slash command",
               lambda k: k in S.TRIVIAL_KINDS | S.NAMED_KINDS, "false_trigger")]
    out = []
    for label, sub, sel, col in groups:
        per = []
        for m in ("claude-sonnet", "claude-opus"):
            rs = [r for r in live if r["model_id"].startswith(m) and sel(kinds.get(r["task_id"]))
                  and r[col] in ("true", "false")]
            per.append([r[col] == "true" for r in rs])
        out.append((label, sub, col, per))
    dates = sorted({r["date_utc"][:10] for r in live})
    versions = sorted({r["claude_code_version"] for r in live})
    return out, len(live), dates, versions


def results():
    groups, n, dates, versions = ts10_sessions()
    W = 1280
    pitch, dot, per_row = 17, 12, 18
    x_lab, x_cols = 44, (380, 820)
    st = [".pop{animation:pop .35s ease-out both}@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:none}}"]
    b = []
    y = 190
    body = []
    delay = 0.0
    for label, sub, col, per in groups:
        rows_needed = max((len(p) + per_row - 1) // per_row for p in per)
        body.append(t(x_lab, y + 4, label, 20, TEXT, weight="700"))
        body.append(t(x_lab, y + 28, sub, 15, MUTED))
        for c, flags in enumerate(per):
            xc = x_cols[c]
            k = sum(flags)
            for j, f in enumerate(flags):
                cx = xc + (j % per_row) * pitch + dot / 2
                cy = y - 8 + (j // per_row) * pitch + dot / 2
                if col == "activated":
                    fill, stroke = (MINT, MINT) if f else (BG, CORAL)
                else:
                    fill, stroke = (CORAL, CORAL) if f else (BG, DIM)
                s = f' style="animation-delay:{delay + j * 0.025:.3f}s;transform-origin:{cx}px {cy}px"'
                body.append(f'<circle class="pop"{s} cx="{cx}" cy="{cy}" r="{dot / 2 - 1}" fill="{fill}" '
                            f'stroke="{stroke}" stroke-width="2"/>')
            word = "ran" if col == "activated" else "false triggers"
            colr = MINT if col == "activated" else (CORAL if k else MINT)
            body.append(t(xc + per_row * pitch + 14, y + 4, f"{k} of {len(flags)}", 20, colr, weight="800"))
            body.append(t(xc + per_row * pitch + 14, y + 24, word, 13, MUTED))
        delay += 0.6
        y += max(rows_needed, 1) * pitch + 52
    H = y + 50
    b.append(f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>')
    b.append(t(44, 48, "HELD-OUT TEST  ·  VERSION 0.4.6", 15, AMBER, weight="600", extra=' letter-spacing="2"'))
    b.append(t(44, 84, f"{n} sessions, one dot each", 28, TEXT, weight="800"))
    b.append(t(44, 114, f"Claude Code {', '.join(versions)}  ·  {', '.join(dates)}  ·  prompts written without seeing the hook",
               15, MUTED))
    b.append(t(x_cols[0], 160, "Sonnet  (claude-sonnet-5-5)", 15, MUTED, MONO))
    b.append(t(x_cols[1], 160, "Opus  (claude-opus-5-5)", 15, MUTED, MONO))
    b += body
    ly = H - 30
    leg = [(MINT, MINT, "skill ran on a real task"), (BG, CORAL, "real task missed"),
           (BG, DIM, "stayed quiet, as it should"), (CORAL, CORAL, "false trigger")]
    lx = 44
    for fill, stroke, lab in leg:
        b.append(f'<circle cx="{lx + 6}" cy="{ly - 5}" r="5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        b.append(t(lx + 18, ly, lab, 14, MUTED))
        lx += 34 + len(lab) * 7.4
    b.append(t(W - 44, ly, "Source: results/ledger.csv, task set ts-10", 14, DIM, anchor="end"))
    summary = "; ".join(
        f"{label}: Sonnet {sum(p[0])} of {len(p[0])}, Opus {sum(p[1])} of {len(p[1])} "
        f"{'sessions where the skill ran' if col == 'activated' else 'false triggers'}"
        for label, _, col, p in groups)
    desc = (f"Held-out test of version 0.4.6, {n} sessions, one dot per session. {summary}. "
            "Source: rows with task set ts-10 in results/ledger.csv.")
    return svg(W, H, "Capability Scout held-out test results", desc, "".join(st), "\n".join(b))


# ---------------------------------------------------------------- demo

EXAMPLE = os.path.join(REPO, "results", "examples", "ts1-stage1-default-ABC-0328.txt")
PROMPT = ("Review app.py in this folder for security vulnerabilities and give me a prioritized list of fixes. "
          "Do not modify any files.")


def wrap(s, n):
    out, cur = [], ""
    for wd in s.split(" "):
        if cur and len(cur) + 1 + len(wd) > n:
            out.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd) if cur else wd
    return out + [cur]


def demo():
    src = open(EXAMPLE, encoding="utf-8").read().splitlines()
    # (line index in the example file, or None for a blank gap); "…" rows mark text left out
    picks = [0, 1, 2, None, 4, 6, 7, "…", 15, "…  (fixes 3 to 7 left out here)", None, -1]
    shown = []
    for p in picks:
        if p is None:
            shown.append(("gap", ""))
            continue
        if isinstance(p, str):
            shown.append(("dim", p))
            continue
        line = src[p]
        if not line.strip():
            raise SystemExit(f"demo picks a blank line ({p}) of {EXAMPLE}")
        if line.startswith("**") and line.endswith("**"):
            shown.append(("bold", line.strip("*")))
        elif line.startswith("## "):
            shown.append(("h2", line))
        elif line == "Capability plan":
            shown.append(("plan", line))
        else:
            shown.append(("text", line))
    for kind, s in shown:
        if kind in ("text", "bold", "h2", "plan") and s and s not in "\n".join(src) and ("**" + s + "**") not in "\n".join(src):
            raise SystemExit(f"demo line not in {EXAMPLE}: {s!r}")
    W, x0, lh, n = 1280, 48, 25, 104
    period = 18.0
    st = []
    b = []
    y = 104
    # prompt
    plines = wrap(PROMPT, n - 2)
    for i, pl in enumerate(plines):
        b.append(t(x0, y, "›" if i == 0 else " ", 17, AMBER, MONO, "700"))
        b.append(t(x0 + 22, y, pl, 17, TEXT, MONO))
        w = len(pl) * 10.3 + 12
        st.append(typed(f"pt{i}", period, 0.4 + i * 1.6, 1.6, len(pl), round(w)))
        b.append(f'<g class="pt{i}"><rect x="{x0 + 22 + w:.0f}" y="{y - 19}" width="{w + 30:.0f}" height="{lh}" fill="{PANEL}"/></g>')
        y += lh
    y += 14
    at = 0.4 + len(plines) * 1.6 + 0.8
    k = 0
    for kind, s in shown:
        if kind == "gap":
            y += 10
            continue
        segs = wrap(s, n) if kind != "dim" else [s]
        st.append(appear(f"r{k}", period, at, hold_to=period - 1.6))
        g = []
        for j, seg in enumerate(segs):
            ind = 0 if (j == 0 or not s.startswith("- ")) else 2
            seg = seg if j == 0 else seg
            if kind == "plan":
                g.append(t(x0, y, seg, 17, AMBER, MONO, "700"))
            elif kind == "h2":
                g.append(t(x0, y, seg, 17, MINT, MONO, "700"))
            elif kind == "bold":
                g.append(t(x0, y, seg, 17, TEXT, MONO, "700"))
            elif kind == "dim":
                g.append(t(x0, y, seg, 17, DIM, MONO))
            else:
                if j == 0 and s.startswith("- ") and ":" in seg:
                    head, rest = seg[2:].split(":", 1)
                    colr = MINT if head.startswith("Using") else AMBER
                    g.append(f'<text x="{x0}" y="{y}" font-family="{MONO}" font-size="17" fill="{TEXT}">'
                             f'- <tspan fill="{colr}" font-weight="700">{escape(head)}:</tspan>{escape(rest)}</text>')
                else:
                    g.append(t(x0 + ind * 10.3, y, seg, 17, TEXT, MONO))
            y += lh
        b.append(f'<g class="r{k}">' + "".join(g) + "</g>")
        at += 0.45
        k += 1
    H = y + 30
    head = [f'<rect width="{W}" height="{H}" rx="18" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.5"/>',
            f'<path d="M0 18a18 18 0 0 1 18-18h{W - 36}a18 18 0 0 1 18 18v32H0z" fill="{BG}"/>',
            f'<circle cx="30" cy="25" r="7" fill="{CORAL}"/><circle cx="54" cy="25" r="7" fill="{AMBER}"/>'
            f'<circle cx="78" cy="25" r="7" fill="{MINT}"/>',
            t(W / 2, 31, "Claude Code  ·  replayed from a real test session (ts1-stage1-default-ABC-0328)", 15, MUTED,
              anchor="middle")]
    desc = ("Replay of a real Claude Code session from the live test. The prompt asks for a security review of "
            "app.py without modifying files. Claude first answers with a capability plan: it uses its own read-only "
            "review and names a first-party security plugin worth adding, which it has not installed. Then it lists "
            "prioritized fixes, starting with command injection and an exposed debugger, and says it modified no files.")
    return svg(W, H, "Capability Scout demo", desc, "".join(st), "\n".join(head + b))


# ---------------------------------------------------------------- small mark for the footer

def mark():
    st = ".sw{transform-origin:60px 60px;animation:spin 6s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}"
    b = [f'<circle cx="60" cy="60" r="58" fill="{BG}"/>',
         f'<circle cx="60" cy="60" r="38" fill="none" stroke="{EDGE}" stroke-width="2"/>',
         f'<circle cx="60" cy="60" r="20" fill="none" stroke="{EDGE}" stroke-width="2"/>',
         f'<g class="sw"><path d="M60 60L31.7 31.7A40 40 0 0 1 60 20Z" fill="{MINT}" fill-opacity=".35"/>'
         f'<path d="M60 60V20" stroke="{MINT}" stroke-width="3"/></g>',
         f'<circle cx="84" cy="44" r="5" fill="{AMBER}"/><circle cx="44" cy="80" r="4" fill="{MINT}"/>',
         f'<circle cx="60" cy="60" r="4" fill="{MINT}"/>']
    return svg(120, 120, "Capability Scout mark", "A small radar sweep, the Capability Scout mark.", st, "\n".join(b))


FILES = {"hero.svg": hero, "how-it-works.svg": flow, "results.svg": results, "demo.svg": demo, "mark.svg": mark}


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for name, fn in FILES.items():
        path, new = os.path.join(OUT, name), fn()
        if "--check" in argv:
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != new:
                bad.append(name)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    if "--check" in argv:
        if bad:
            print("OUT OF DATE: " + ", ".join(bad), file=sys.stderr)
            return 1
        print("README graphics match the ledger and the example")
        return 0
    print("wrote " + ", ".join(FILES))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
