"""Build a searchable overview from existing README demo links and explicit gaps."""

import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/design/qa/overview"
OUT.mkdir(parents=True, exist_ok=True)
readme = (ROOT / "README.md").read_text()
archive_doc = (ROOT / "docs/FEATURE_GALLERY.md").read_text()
readme += archive_doc.replace("(media/", "(docs/media/")
rows = []
seen = set()
for title, path in re.findall(
    r"!\[([^\]]+)\]\((docs/media/panels/[^)]+\.gif)\)", readme
):
    if path in seen:
        continue
    seen.add(path)
    assert (ROOT / path).is_file(), path
    rows.append(dict(title=title, path=path))
forecast = json.loads((OUT / "estimate.json").read_text())
current = json.loads(
    (ROOT / "docs/design/qa/forced-perspective-v2/current-media.json").read_text()
)
current_paths = {r["path"] for r in current}
archive = [r for r in rows if r["path"] not in current_paths]


def cards(items, historical=False):
    return "".join(
        f'<article data-search="{html.escape(r["title"].lower())}"><h2>{html.escape(r["title"])}</h2><small>{"Historical capture · older styling" if historical else "Fresh Blender capture · current styling"}</small><img loading="lazy" src="../../../../{r["path"]}" alt="{html.escape(r["title"])}"><a href="../../../../{r["path"]}">Open recorded GIF</a></article>'
        for r in items
    )


features = (
    '<h2>Current controls · freshly captured</h2><p><a href="../forced-perspective-v2/index.html">Current panels: compact browser-style grid, aligned labels, centered icons and focal slider</a></p><p><a href="../camkeys-visual-v4/index.html">Earlier CamKeys list/brush behavior evidence (before the latest icon-centering pass)</a></p><p><a href="../core-review-v2/index.html">Earlier core review and QA notes (before the latest icon-centering pass)</a></p><div class="grid">'
    + cards(current)
    + '</div><details id="archive"><summary>Historical feature archive ('
    + str(len(archive))
    + ' older recordings)</summary><p>These recordings preserve earlier behavior evidence. Their styling is outdated; use the current review above for visual QA.</p><div class="grid">'
    + cards(archive, True)
    + "</div></details>"
)
page = """<!doctype html><meta charset="utf-8"><title>Beyond UI — Feature overview</title>
<style>body{font:16px system-ui;background:#191b20;color:#ecedf1;margin:32px}a{color:#a9ccff}h1{font-size:28px}h2{font-size:17px}.estimate{background:#293443;border:1px solid #53657b;padding:20px;border-radius:14px;max-width:1100px}p,li{line-height:1.5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}article{background:#23262c;padding:16px;border-radius:12px}img{width:100%;height:auto}input{font:inherit;padding:12px;width:min(600px,90%);margin:20px 0}small{color:#b5bac5}</style>
<h1>Beyond UI · Extension panel toolkit</h1>
<section class="estimate"><h2>Remaining work estimate</h2><p><strong>TURN_RANGE implementation and QA turns before CHECKPOINT</strong></p><p>TIME_SUMMARY</p><p>ESTIMATE_REVIEW</p><p>Planning range, low confidence—not a deadline or measured throughput forecast. Excludes waiting for user review. Scope: reusable N-panel/Properties controls, popovers, invoke menus/dialogs and full applicable right-click behavior; excludes built-in Blender feature panels.</p><p><a href="../../../CAMKEYS_MIGRATION.md">Consumer qualification: tested workflows and full-custom blockers</a></p><p>Remaining work: REMAINING_WORK Multiline, preview galleries and advanced curves are deferred. <a href="../../../CORE_RELEASE_CHECKLIST.md">Audited checklist</a>. Estimate targets the next core review candidate, not universal platform qualification.</p><small>Reviewed: REVIEWED · Reassess after each project turn. No automatic countdown for discussion-only turns. <a href="estimate.json">Assumptions and update record</a></small></section>
<p>The current core demos below were recaptured from the current library. Older feature recordings are separated into the historical archive. Neither group establishes full parity or visual acceptance. Early specialized-control recordings use the documented reference palette/tint fallback and are not evidence of production liquid glass. Consult the feature QA records before treating a recording as accepted.</p>
<p><strong>Media gaps:</strong> MEDIA_GAPS</p><p><a href="../core-review-v2/index.html">Updated core visual QA: current menu, field and theme styling</a> · <a href="../../../CORE_CONTEXT_AUDIT.md">Exact remaining context actions</a> · <a href="../custom-contributions-v1/runtime.json">Latest right-click execution checks</a> · <a href="../color-alpha-v1/index.html">Latest color-picker correction</a></p>
<p><a href="../../../../README.md">README and feature notes</a> · <a href="../../../PARITY_SCOPE.md">Scope</a> · <a href="../../../CUSTOM_PARITY.json">Full inventory</a></p>
<input id="search" placeholder="Filter demos: menus, sliders, curves…"><p id="count"></p>FEATURES
<script>const cards=[...document.querySelectorAll('article')];function filter(){let q=document.querySelector('input').value.toLowerCase();if(q)document.querySelector('#archive').open=true;cards.forEach(c=>c.hidden=!c.dataset.search.includes(q));document.querySelector('#count').textContent=cards.filter(c=>!c.hidden).length+' matching demos (including the labeled archive)'}document.querySelector('input').oninput=filter;filter()</script>""".replace(
    "FEATURES", features
).replace("REVIEWED", html.escape(forecast["reviewed"]))
for token, key in (
    ("TURN_RANGE", "remaining_turns"),
    ("15–30", "implementation_turns"),
    ("5–15", "integration_qa_turns"),
):
    low, high = forecast[key]
    page = page.replace(token, str(low) if low == high else f"{low}–{high}")
page = page.replace(
    "CHECKPOINT",
    html.escape(forecast.get("checkpoint", "the next core review checkpoint")),
)
page = page.replace("TIME_SUMMARY", html.escape(forecast["time_summary"]))
page = page.replace("ESTIMATE_REVIEW", html.escape(forecast["estimate_review"]))
page = page.replace("REMAINING_WORK", html.escape(forecast["remaining_work"]))
page = page.replace(
    "MEDIA_GAPS", html.escape("; ".join(forecast["media_gaps"]) or "None recorded.")
)
page = page.replace(
    "<h1>Beyond UI · Extension panel toolkit</h1>",
    "<h1>Beyond UI · Extension panel toolkit</h1><p>Latest progress: "
    + html.escape(forecast.get("latest_progress", "See the review record."))
    + "</p>",
)
(OUT / "index.html").write_text(page)
(OUT / "media.json").write_text(json.dumps(rows, indent=2) + "\n")
print(f"{len(rows)} GIF demos indexed")
