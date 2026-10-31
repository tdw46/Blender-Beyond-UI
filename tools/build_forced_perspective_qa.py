"""Publish generated specification, actual consumer captures and explicit limits."""

import json, shutil, hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/forced-perspective-v1"
OUT = ROOT / "docs/design/qa/forced-perspective-v1"
OUT.mkdir(parents=True, exist_ok=True)
results = {
    name: json.loads((BUILD / name / "summary.json").read_text())
    for name in ("run", "run-51", "embedded-run", "consumer", "before-run", "installed-launch")
}
assert all(r["passed"] for runs in results.values() for r in runs)
for width in (260, 360, 480):
    for dpi in (1, 1.5, 2):
        name = f"{width}-{dpi:g}x.png"
        shutil.copy2(BUILD / "captures" / name, OUT / name)
    for state, folder in [("before", "before"), ("after", "captures")]:
        shutil.copy2(BUILD / folder / f"{width}-2x.png", OUT / f"{state}-{width}.png")
for name in ("idle", "context", "dismissed", "scrolled"):
    shutil.copy2(BUILD / "embedded" / f"{name}.png", OUT / f"native-{name}.png")
reference = ROOT / "docs/design/references/forced-perspective-v1/reference.png"
shutil.copy2(reference, OUT / "reference.png")
frames = [
    Image.open(OUT / f"native-{n}.png").convert("RGB")
    for n in ("idle", "context", "dismissed")
]
frames[0].save(
    ROOT / "docs/media/panels/forced-perspective-v1.gif",
    save_all=True,
    append_images=frames[1:],
    duration=1800,
    loop=0,
)
report = dict(
    results=results,
    unit_tests=288,
    exact_match=False,
    reference_conflicts=[
        "Generated extra numeric dropdown arrows are not implemented: those fields do not open menus.",
        "Generated icon artwork, panel backdrop and rim are not pixel-identical to the actual consumer capture.",
        "At 260 logical units, utility groups wrap to preserve readable labels, full switches and units; the concept depicts a wider panel.",
    ],
    source_hashes={
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "beyond_ui").rglob("*.py")
    },
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(OUT / "current-media.json").write_text(
    json.dumps(
        [
            dict(
                title="Forced Perspective: actual native panel and right click (state slideshow)",
                path="docs/media/panels/forced-perspective-v1.gif",
            )
        ],
        indent=2,
    )
    + "\n"
)
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Forced Perspective · responsive panel review</title>
<style>body{margin:32px;background:#191b20;color:#eef0f5;font:16px system-ui}p{line-height:1.55;max-width:1050px}a{color:#a9ccff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#25282f;padding:18px;border-radius:14px}img{max-width:100%;height:auto}select{font:inherit;padding:8px}.note{padding:16px;background:#34303d;border-radius:12px}button{font:inherit}</style>
<h1>Forced Perspective · hierarchy and responsive spacing</h1>
<p>Shared panel changes: structural bold headings, wrapped long titles, aligned field columns, four-unit gutters, value-baseline accessories, intrinsic switch/icon/unit widths, and percentage splits that reflow before hiding controls. No CamKeys label-name overrides or consumer source edits.</p>
<p class="note">Generated references are separated from real Blender evidence. Exact image matching remains open: the generated numeric arrows would invent menu behavior, and its icons, backdrop and rim differ. Those differences are recorded explicitly. The actual controls keep BVT glass, theming, motion and original owner menus.</p>
<div class="grid"><article><h2>Generated macOS direction</h2><img src="reference.png"></article><article><h2>Actual authored controls · 360 logical units</h2><img src="360-2x.png"></article></div>
<h2>Before and after at the same width</h2><p><label>Logical panel width <select id="width"><option>260</option><option selected>360</option><option>480</option></select></label></p>
<div class="grid"><article><h2>Previous installed library</h2><img id="before" src="before-360.png"></article><article><h2>Updated library</h2><img id="after" src="after-360.png"></article></div>
<h2>Actual native N-panel</h2><div class="grid"><article><h3>At rest · 260.5 logical units</h3><img src="native-idle.png"></article><article><h3>Focal-length right click</h3><img src="native-context.png"></article></div>
<h2>Recorded panel/menu states</h2><p>State slideshow, not a timing or bounce-speed demonstration.</p><img style="max-width:560px" src="../../../media/panels/forced-perspective-v1.gif">
<h2>Scale checks</h2><p><label>Display scale <select id="scale"><option>1</option><option>1.5</option><option selected>2</option></select></label></p><img id="scaled" style="max-width:784px" src="360-2x.png">
<p>288 unit tests; real CamKeys runtime checks on Blender 5.1.2 and 5.2.2; nine width/scale captures per version. Native capture uses a disposable dedicated category so unrelated panels do not obscure the fixture. No focus activation recorded. Warm CPU timings exclude GPU completion/readback and are not source-performance certification. <a href="report.json">Evidence and limits</a> · <a href="../overview/index.html">Overview and estimate</a> · <a href="../../../PANEL_LAYOUT.md">Reusable layout policy</a></p>
<script>const w=document.querySelector('#width'),s=document.querySelector('#scale');function update(){document.querySelector('#before').src='before-'+w.value+'.png';document.querySelector('#after').src='after-'+w.value+'.png';document.querySelector('#scaled').src=w.value+'-'+s.value+'x.png'}w.onchange=s.onchange=update;</script>""")
metadata = dict(
    tool="image_gen.imagegen",
    version=1,
    dimensions=Image.open(reference).size,
    prompt="prompt.txt",
    date="2026-10-31",
    source="User Forced Perspective screenshot; BVT liquid glass/scalar controls; approved macOS styling",
    state="Dark reference panel, Focus Object Face, focal length 250; generated toggle states differ from actual fixture",
    exact_match=False,
    conflicts=report["reference_conflicts"],
)
(reference.parent / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(OUT)
