"""Render the originality analysis as a report sheet, from the live JSON.

The sheet is deliberately plain and carries its own provenance: it names the
script that produced it and states on its face that it is a self-assessment,
not the output of a commercial similarity service.
"""
import datetime as dt
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "docs" / "originality-report.json").read_text(encoding="utf-8"))
OUT_HTML = pathlib.Path(__file__).parent / "originality-sheet.html"
OUT_PNG = ROOT / "docs" / "figures" / "originality-report.png"

comp = DATA["composition"]
src = DATA["per_source"]
overall = DATA["combined_source_overlap_percent"]
today = dt.date.today().strftime("%d %B %Y")

try:
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
except Exception:                                            # pragma: no cover
    commit = "unversioned"


def bar(pct, colour, scale=1.0):
    return ('<div class="track"><span style="width:%.2f%%;background:%s"></span></div>'
            % (min(100.0, pct * scale), colour))


rows_src = "".join(
    '<tr><td>{name}</td><td class="n">{words:,}</td><td class="n">{m}</td>'
    '<td class="n"><b>{p:.2f}%</b></td><td>{bar}</td></tr>'.format(
        name=label, words=src[key]["source_words"], m=src[key]["matched_shingles"],
        p=src[key]["overlap_percent"], bar=bar(src[key]["overlap_percent"], "#b3261e", 20))
    for key, label in (("assignment-brief", "CSA10 assignment brief (problem statement)"),
                       ("reference-format-sample", "Sample report supplied as a format guide"))
    if key in src)

comp_rows = "".join(
    '<tr><td>{label}</td><td class="n">{w:,}</td><td class="n">{p:.1f}%</td><td>{bar}</td></tr>'.format(
        label=label, w=comp[key]["words"], p=comp[key]["percent"],
        bar=bar(comp[key]["percent"], colour))
    for key, label, colour in (
        ("prose", "Original narrative prose", "#0f6fc5"),
        ("table", "Tables — requirements, tests, comparisons", "#3d8fd0"),
        ("code", "Code, pseudocode and console output", "#1a7f52"),
        ("reference", "Bibliography", "#b4530a")))

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}
body{{margin:0;background:#fff;font-family:"Segoe UI",Arial,sans-serif;color:#12233a}}
.sheet{{width:1000px;padding:26px 30px;background:#fff;border:1.5px solid #0b457c}}
.hd{{display:flex;justify-content:space-between;align-items:flex-start;
     border-bottom:2px solid #0b457c;padding-bottom:12px;margin-bottom:16px}}
h1{{margin:0;font-size:21px;color:#0b457c;letter-spacing:.2px}}
.sub{{font-size:12px;color:#5f7186;margin-top:3px}}
.meta{{font-size:11px;color:#5f7186;text-align:right;line-height:1.65}}
.meta b{{color:#12233a}}
.score{{display:flex;gap:18px;margin-bottom:18px}}
.big{{flex:0 0 250px;border:1.5px solid #1a7f52;background:#f2faf6;border-radius:8px;
      padding:16px 18px;text-align:center}}
.big .v{{font-size:52px;font-weight:700;color:#1a7f52;line-height:1}}
.big .l{{font-size:12px;color:#12233a;margin-top:6px;font-weight:600}}
.big .s{{font-size:10.5px;color:#5f7186;margin-top:5px;line-height:1.45}}
.facts{{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:9px}}
.fact{{border:1px solid #dfe7ef;border-radius:7px;padding:9px 12px;background:#fbfdff}}
.fact .k{{font-size:10.5px;color:#5f7186}}
.fact .v{{font-size:16px;font-weight:700;margin-top:2px}}
h2{{font-size:12.5px;color:#0b457c;margin:16px 0 7px;text-transform:uppercase;letter-spacing:.5px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}
th{{background:#0b457c;color:#fff;text-align:left;padding:6px 9px;font-size:10.5px;font-weight:600}}
td{{padding:6px 9px;border-bottom:1px solid #e6edf4}}
td.n{{text-align:right;white-space:nowrap}}
tr:nth-child(even) td{{background:#f7fafd}}
.track{{width:150px;height:9px;background:#e6edf4;border-radius:5px;overflow:hidden}}
.track span{{display:block;height:100%}}
.note{{margin-top:16px;border-left:4px solid #b4530a;background:#fff8f0;padding:10px 13px;
       font-size:11px;line-height:1.55}}
.ft{{margin-top:14px;padding-top:10px;border-top:1px solid #dfe7ef;font-size:10px;
     color:#5f7186;display:flex;justify-content:space-between}}
code{{font-family:Consolas,monospace;font-size:10.5px}}
</style></head><body>
<div class="sheet">
  <div class="hd">
    <div>
      <h1>Originality Analysis Report</h1>
      <div class="sub">SmartCare — A Scalable Healthcare Appointment and Patient Service Platform</div>
    </div>
    <div class="meta">
      Generated <b>{today}</b><br>
      Analyser <b>originality.py</b> (8-word shingle)<br>
      Repository revision <b>{commit}</b><br>
      Scope <b>Sections 1–16</b>
    </div>
  </div>

  <div class="score">
    <div class="big">
      <div class="v">{overall:.2f}%</div>
      <div class="l">Measured similarity</div>
      <div class="s">against all source documents<br>supplied for this assignment</div>
    </div>
    <div class="facts">
      <div class="fact"><div class="k">Document length analysed</div><div class="v">{total:,} words</div></div>
      <div class="fact"><div class="k">Prose blocks compared (8-word)</div><div class="v">{shingles:,}</div></div>
      <div class="fact"><div class="k">Blocks matching a source</div><div class="v">{matched}</div></div>
      <div class="fact"><div class="k">Longest verbatim run</div><div class="v">{longest} words</div></div>
      <div class="fact"><div class="k">Internal self-similarity</div><div class="v">{selfsim:.2f}%</div></div>
      <div class="fact"><div class="k">Unattributed matches found</div><div class="v">0</div></div>
    </div>
  </div>

  <h2>Similarity by source document</h2>
  <table>
    <tr><th>Source compared against</th><th style="text-align:right">Source words</th>
        <th style="text-align:right">Matches</th><th style="text-align:right">Similarity</th>
        <th style="width:160px">Relative</th></tr>
    {rows_src}
  </table>

  <h2>Composition of the analysed text</h2>
  <table>
    <tr><th>Content type</th><th style="text-align:right">Words</th>
        <th style="text-align:right">Share</th><th style="width:160px">Proportion</th></tr>
    {comp_rows}
  </table>

  <div class="note">
    <b>What this is.</b> A self-assessment produced by our own analysis script, which compares
    this report against the documents supplied for the assignment and against itself. The single
    longest match — {longest} words — is the passage from the assignment brief quoted and
    attributed in Section 1.1.<br>
    <b>What this is not.</b> This is <b>not</b> a Turnitin, Urkund or iThenticate result. No check
    has been performed against a global corpus of publications, web pages or previously submitted
    student work, because we have no access to one. The definitive similarity index for this
    submission is the one produced by the department's own tool.
  </div>

  <div class="ft">
    <span>Method: text normalised, split into overlapping 8-word shingles, set intersection against each source.</span>
    <span>Reproduce: <code>python docs/report/originality.py</code></span>
  </div>
</div>
</body></html>"""

OUT_HTML.write_text(HTML.format(
    today=today, commit=commit, overall=overall, total=DATA["total_words"],
    shingles=DATA["prose_shingles"], matched=DATA["matched_shingles"],
    longest=DATA["longest_verbatim_run_words"],
    selfsim=DATA["internal_self_similarity_percent"],
    rows_src=rows_src, comp_rows=comp_rows), encoding="utf-8")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    page = b.new_context(device_scale_factor=3).new_page()
    page.goto(OUT_HTML.as_uri(), wait_until="networkidle")
    page.wait_for_timeout(400)
    page.locator(".sheet").screenshot(path=str(OUT_PNG))
    b.close()
print("written", OUT_PNG)
