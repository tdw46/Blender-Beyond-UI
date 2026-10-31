"""Publish measured menu geometry and actual GPU evidence; never imply acceptance."""

import hashlib
import html
import json
import shutil
import os
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("BEYOND_UI_QA_VERSION", "v1")
BUILD = ROOT / os.environ.get("BEYOND_UI_QA_BUILD", "build/menu-spacing-final")
REF_BUILD = ROOT / os.environ.get(
    "BEYOND_UI_QA_REFERENCE", "build/menu-reference-final"
)
OUT = ROOT / f"docs/design/qa/menu-spacing-{VERSION}"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
focus = read(BUILD / "focus.json")
records = []
for label in ("1x", "15x", "2x", "51", "scalar"):
    r = read(BUILD / f"run-{label}/summary.json")[0]
    assert r["passed"] and r["result"]["stable_resources"]
    for name, digest in r["result"]["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    r["focus_passed"] = r["pid"] not in focus["sampled_frontmost_pids"] and not any(
        e.get("pid") == r["pid"] for e in focus["events"]
    )
    assert r["focus_passed"] and r["launch"]["restore_requests"] == 0
    records.append(r)
    for p in (BUILD / f"capture-{label}").glob("*.png"):
        if p.stem.startswith(("frame-", "batch-", "core-")):
            continue
        shutil.copy2(p, OUT / f"{label}-{p.name}")
ref = read(REF_BUILD / "run/summary.json")[0]
assert ref["passed"]
for name, digest in ref["result"]["source_sha256"].items():
    assert sha(ROOT / name) == digest, name
shutil.copy2(REF_BUILD / "capture/reference-menu.png", OUT / "implementation.png")
shutil.copy2(
    ROOT / "docs/design/references/macos-controls-v1/approved-format-crop.png",
    OUT / "reference.png",
)


def movie(folder, pattern, key):
    paths = sorted(folder.glob(pattern))
    assert paths
    frames = [Image.open(p).convert("RGB") for p in paths]
    file = MEDIA / f"menu-spacing-{key}-{VERSION}.gif"
    frames[0].save(
        file,
        save_all=True,
        append_images=frames[1:],
        duration=33,
        loop=0,
        optimize=False,
    )
    data = dict(
        source="Actual Blender GPU frames",
        frames=len(paths),
        frame_sha256={p.name: sha(p) for p in paths},
        sha256=sha(file),
        exact_match=False,
    )
    file.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n")
    return data


movies = {
    "components": movie(BUILD / "capture-1x", "core-*.png", "components"),
    "actions": movie(BUILD / "capture-1x", "frame-*.png", "actions"),
    "scalars": movie(BUILD / "capture-scalar", "frame-*.png", "scalars"),
}
background = {
    p.parent.name: read(p)
    for p in BUILD.glob(
        "blender_*/summary.json"
        if VERSION == "v1"
        else "blender_*-verified/summary.json"
    )
}
for rows in background.values():
    assert all(r["passed"] for r in rows)
keying = {
    name: read(ROOT / f"build/macos-controls-v1/{name}/summary.json")
    for name in ("keying", "availability", "actions")
}
report = dict(
    exact_match=False,
    visual_acceptance=False,
    full_custom_parity=False,
    gpu_runs=records,
    reference_capture=ref,
    focus=focus,
    reference_focus=read(REF_BUILD / "focus.json"),
    native_batch_equal_frames=sum(
        r["result"]["native_text_batching_equal_frames"] for r in records
    )
    + ref["result"]["native_text_batching_equal_frames"],
    background=background,
    keying_and_animation=keying,
    movies=movies,
    fonts={p.name: sha(p) for p in (ROOT / "beyond_ui/assets/fonts").glob("*.woff2")},
    geometry=dict(
        reference_inner_bounds=[8, 5, 752, 626],
        host_width=224,
        row_height=22.5,
        outer_inset=8,
        title_height=18,
        title_gap=5.5,
        search_height=24.5,
        search_to_rows=8,
        option_text_inset=10,
        title_text_inset=7,
        search_inset=4.5,
        search_text_origin=28,
    ),
    limitations=[
        "Reference and implementation use different backdrops; colors/refraction are not pixel-identical.",
        "Generated row pitches and glyph shapes vary; remaining pixel differences stay open for visual review.",
        "Standalone reference capture shows rest, not approval of every animated state.",
        "No new 4.2 or cross-platform runtime qualification; historical QA pages remain historical.",
    ],
)
if (BUILD / "picker-windowed/summary.json").exists():
    report["picker_input"] = read(BUILD / "picker-windowed/summary.json")
    report["picker_focus"] = read(BUILD / "picker-focus.json")
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
states = [
    "component-enums",
    "component-filtered",
    "hold-menu",
    "hold-context",
    "components",
    "popover",
    "rest",
    "disabled",
]
gallery = "".join(
    f'<figure><img data-state="{s}" src="1x-{s}.png"><figcaption>{html.escape(s)}</figcaption></figure>'
    for s in states
)
page = """<!doctype html><meta charset="utf-8"><title>Beyond UI · Measured menu spacing</title>
<style>body{font:16px system-ui;background:#191b20;color:#eceef2;margin:30px;line-height:1.5}a{color:#acd0ff}h1{font-size:28px}h2{font-size:20px}section{margin:28px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}figure{margin:0;padding:16px;background:#252930;border-radius:12px}img{display:block;width:100%;height:auto}figcaption{padding-top:10px;color:#bdc5d2}.notice{background:#293444;padding:18px;border-radius:12px}button,select,input{font:inherit} .comparison{max-width:1540px}.crop{position:relative;aspect-ratio:752/626;overflow:hidden}.crop img{position:absolute;width:102.394%;max-width:none;left:-1.064%;top:-.799%}.overlay{position:relative;max-width:752px;aspect-ratio:752/626;overflow:hidden}.overlay .crop{position:absolute;inset:0}.overlay>img{position:absolute;top:0;width:100%;opacity:.5}.gallery{max-width:1400px}textarea{display:block;width:95%;height:90px;font:inherit;margin:12px 0}</style>
<h1>Measured menu spacing · current Blender implementation</h1>
<p class="notice">Fixed the popup host overwriting compact menu metrics. Shared spacing now covers enum, registered, nested/context menus and pointer/search pickers. Search magnifiers share text/caret insets with collection-list filters. Bold titles, darker inputs, larger switches, source glass and bounce remain in the renderer. <strong>Reference acceptance remains open.</strong> This is a fresh page; the previous core-review page is historical.</p>
<p><a href="../overview/index.html">Overview and updated 2–7 turn estimate</a> · <a href="report.json">Runtime, geometry, focus and source evidence</a> · <a href="../../references/macos-controls-v1/metadata.json">Immutable reference provenance</a></p>
<section><h2>Approved crop versus actual Blender GPU capture</h2><p>Equal menu width, same five labels, PNG selected and unfocused search. The reference's exterior margin is clipped only in this viewer. The implementation is a direct framebuffer crop, with no retouching. Backdrop, glyph and small spacing differences remain visible; this is not a pixel-exact acceptance claim.</p><div class="grid comparison"><figure><div class="crop"><img src="reference.png"></div><figcaption>Approved generated reference</figcaption></figure><figure><img src="implementation.png"><figcaption>Current production PropertyPopover · Blender 5.2.2 · 752-pixel capture width</figcaption></figure></div></section>
<section><h2>Overlay comparison</h2><label>Implementation opacity <input id="opacity" type="range" min="0" max="100" value="50"></label><div class="overlay"><div class="crop"><img src="reference.png"></div><img id="over" src="implementation.png"></div></section>
<section><h2>All shared menu paths</h2><label>Capture scale <select id="scale"><option value="1x">5.2 · 1×</option><option value="15x">5.2 · 1.5×</option><option value="2x">5.2 · 2×</option><option value="51">5.1 · 1×</option></select></label><div class="grid gallery">GALLERY</div><div class="grid"><figure><img src="1x-normalized-picker.png"><figcaption>Pointer/collection picker · shared compact rows and search</figcaption></figure><figure><img src="1x-theme-light-menu.png"><figcaption>Light theme · readable menu text and theme-derived selection</figcaption></figure><figure><img src="scalar-rest.png"><figcaption>BVT scalars · larger switches and inset value fields</figcaption></figure></div></section>
<section><h2>Actual motion captures</h2><div class="grid">MOVIES</div></section>
<section><h2>QA notes</h2><p>Check title size/weight, title→search and search→options gaps, text indent, highlighted row bounds, search icon, glass and light-theme contrast.</p><textarea id="notes" placeholder="Your visual QA notes…"></textarea><button id="export">Export notes</button><p id="saved"></p></section>
<script>document.querySelector('#opacity').oninput=e=>document.querySelector('#over').style.opacity=e.target.value/100;document.querySelector('#scale').onchange=e=>document.querySelectorAll('[data-state]').forEach(i=>i.src=e.target.value+'-'+i.dataset.state+'.png');const n=document.querySelector('#notes');try{n.value=localStorage.getItem('bui-menu-spacing-v1')||''}catch(e){}n.oninput=()=>{try{localStorage.setItem('bui-menu-spacing-v1',n.value);document.querySelector('#saved').textContent='Saved locally'}catch(e){document.querySelector('#saved').textContent='Use Export to preserve notes'}};document.querySelector('#export').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify({page:'menu-spacing-v1',notes:n.value},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='menu-spacing-qa.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};</script>"""
movie_html = "".join(
    f'<figure><img src="../../../media/panels/menu-spacing-{name}-{VERSION}.gif"><figcaption>{name}</figcaption></figure>'
    for name in movies
)
if VERSION != "v1":
    for name in (
        "popover-detail",
        "components-detail",
        "external-color-fields",
        "external-curve-fields",
        "external-ramp-fields",
    ):
        shutil.copy2(REF_BUILD / "capture" / (name + ".png"), OUT / (name + ".png"))
    shutil.copy2(
        ROOT / "docs/design/references/external-labels-icons-v1/reference.png",
        OUT / "field-reference.png",
    )
    page = page.replace(
        "<h1>Measured menu spacing · current Blender implementation</h1>",
        "<h1>Field labels, icons and menu refinements</h1>",
    )
    page = page.replace(
        "Fixed the popup host overwriting compact menu metrics.",
        "New: labels outside editable fields, optional label icons, centered action buttons, smaller search text, fine inset outlines and taller visual highlights without moving rows.",
    )
    page = page.replace("2–7 turn estimate", "2–6 turn estimate")
    extra = """<section><h2>macOS-style external labels and optional icons</h2><figure><img src="field-reference.png"><figcaption>New generated reference · icons are optional · not production artwork</figcaption></figure><div class="grid"><figure><img src="components-detail.png"><figcaption>Actual component editor: external labels, axes icons and value-only fields</figcaption></figure><figure><img src="popover-detail.png"><figcaption>Actual confirmation: external Output label/folder, centered button text</figcaption></figure></div><p>Blender controls retain host scale and authored popup widths. Generated backdrop, exact aspect ratios and glyph differences remain open; the comparison is evidence for review, not a claim of pixel-identical rendering.</p><p><a href="../../../FIELD_LABELS.md">Label/icon API and renderer contract</a></p></section><section><h2>Specialized field coverage</h2><div class="grid"><figure><img src="external-color-fields.png"><figcaption>Color channel labels outside values</figcaption></figure><figure><img src="external-curve-fields.png"><figcaption>Curve component fields</figcaption></figure><figure><img src="external-ramp-fields.png"><figcaption>Ramp position field</figcaption></figure></div></section>"""
    page = page.replace(
        "<section><h2>All shared menu paths</h2>",
        extra + "<section><h2>All shared menu paths</h2>",
    )
    report["refinements"] = {
        "search_font_size": 10,
        "body_font_size": 11,
        "highlight_bleed_each_edge": 1.25,
        "entry_label_fraction": 0.36,
        "entry_gap": 8,
        "label_icon_size": 12,
        "label_icon_gap": 6,
        "pure_tests": 248,
    }
    report["geometry"]["editable_components_use_host_rows"] = True
    report["references"] = [
        "external-labels-v1",
        "external-labels-icons-v1",
        "macos-confirm-v1",
        "macos-controls-v1",
    ]
    report["browser_validation"] = (
        "Local links verified separately; interactive overlay remains for user QA."
    )
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(OUT / "index.html").write_text(
    page.replace("GALLERY", gallery)
    .replace("MOVIES", movie_html)
    .replace("menu-spacing-v1", "menu-spacing-" + VERSION)
)
print("Published menu-spacing-v1; visual acceptance open")
