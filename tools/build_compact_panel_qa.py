"""Current compact panel evidence, comparison tools and explicit fidelity limits."""
import json, shutil, hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/forced-perspective-v2"
OUT = ROOT / "docs/design/qa/forced-perspective-v2"
OUT.mkdir(parents=True, exist_ok=True)
results = {name: json.loads((BUILD / name / "summary.json").read_text())
           for name in ("run", "run-51", "embedded-run", "list-run", "icons", "consumer", "installed-launch")}
assert all(r["passed"] for runs in results.values() for r in runs)
for width in (260,286,360,480):
    for dpi in (1,1.5,2):
        name=f"{width}-{dpi:g}x.png"
        shutil.copy2(BUILD / "captures" / name, OUT / name)
for width in (260,360,480):
    shutil.copy2(ROOT / f"build/forced-perspective-v1/captures/{width}-2x.png", OUT / f"before-{width}.png")
for name in ("idle","context","dismissed","scrolled"):
    shutil.copy2(BUILD / "embedded" / f"{name}.png", OUT / f"native-{name}.png")
for name in ("idle","expanded","collapsed"):
    shutil.copy2(BUILD / "lists" / f"{name}.png", OUT / f"list-{name}.png")
for dpi in (1,1.5,2):
    shutil.copy2(BUILD / "icons" / f"icons-{dpi:g}x.png", OUT / f"icons-{dpi:g}x.png")
shutil.copy2(BUILD / "text-recognition.json", OUT / "text-recognition.json")
ref=ROOT / "docs/design/references/forced-perspective-v2/reference.png"
shutil.copy2(ref, OUT / "reference.png")
capture=json.loads((BUILD / "captures/report.json").read_text())
record=next(r for r in capture["records"] if r["width"]==286)
last=next(c for c in record["controls"] if c["label"]=="Other Objects to Correct:")
height=round((last["rect"][1]+last["rect"][3])*2)
actual=Image.open(OUT/"286-2x.png").crop((32,32,604,32+height))
actual.save(OUT/"implementation-comparison.png")
# Derived comparison only; immutable reference stays unchanged. Normalize by
# body font size, never stretch a panel to conceal different line wrapping.
concept=Image.open(ref).crop((148,100,812,1524))
factor=22/26
concept=concept.resize((round(concept.width*factor),round(concept.height*factor)),Image.Resampling.LANCZOS)
concept.save(OUT/"reference-comparison.png")
media=[]
for name,frames in [("forced-perspective-v2",["native-idle","native-context","native-dismissed"]),
                    ("camkeys-panel-v5",["list-idle","list-expanded","list-collapsed"])]:
    ims=[Image.open(OUT/f"{s}.png").convert("RGB") for s in frames]
    path=f"docs/media/panels/{name}.gif"
    ims[0].save(ROOT/path,save_all=True,append_images=ims[1:],duration=1800,loop=0)
    media.append(dict(title=("Forced Perspective: compact grid, slider and centered icons" if name.startswith("forced") else "CamKeys: compact tool rail and centered icons/help")+" (state slideshow)",path=path))
(OUT/"current-media.json").write_text(json.dumps(media,indent=2)+"\n")
baseline=json.loads((ROOT/"build/forced-perspective-v1/captures/report.json").read_text())
report=dict(results=results,unit_tests=292,exact_match=False,
    changes=["26-unit fields; 20-unit text buttons with authored scale; 24-unit icon buttons; 22-unit list tools; 4-unit gutters",
             "Shared external-label origin, including switches; paired caption stacking; property-owned row-spanning slider caption",
             "Conservative metadata-only automatic slider; explicit author override; original BVT track/handle/number entry",
             "53 atlas ink bounds and all vector bounds center visible artwork; original pixels and proportions preserved"],
    icon_checks=results["icons"][0]["result"],
    comparison=dict(reference_body_pixels=26,implementation_body_pixels=22,normalization=factor,reference_crop=[148,100,812,1524],implementation_width=286),
    remaining_differences=["The actual author supplies a Lens label, a distance-falloff action and separators absent from the generated concept; those controls are preserved.",
                           "Original Blender glyph shapes and the active theme/backdrop differ from the concept. Ink centering and shared geometry are verified; pixel-exact artwork/glass matching is not claimed.",
                           "Narrow panels stack paired field labels and wrap long headings instead of hiding controls."],
    warm_cpu=dict(before_median_ms=baseline["paint_cpu_median_ms"],after_median_ms=capture["paint_cpu_median_ms"],after_p95_ms=capture["paint_cpu_p95_ms"],samples=10,workload="Actual consumer at 360 logical width, 2x; GPU readback excluded; changed layout makes this a smoke comparison, not source-performance certification"),
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"beyond_ui").rglob("*.py")})
(OUT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
metadata=dict(tool="image_gen.imagegen",version=2,dimensions=Image.open(ref).size,prompt="prompt.txt",date="2026-10-31",source_reference="../forced-perspective-v1/reference.png",state="Dark macOS concept with focal slider and separate numeric field",exact_match=False)
(ref.parent/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
(OUT/"index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Compact panel grid · Beyond UI</title>
<style>body{margin:32px;background:#191b20;color:#eef0f5;font:16px system-ui}p{line-height:1.55;max-width:1100px}a{color:#a9ccff}h1{font-size:28px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#25282f;padding:18px;border-radius:14px}img{max-width:100%;height:auto}.note{padding:16px;background:#34303d;border-radius:12px}select{font:inherit;padding:8px}.comparison{position:relative;width:572px;max-width:100%;overflow:hidden;background:#16191d}.comparison>img{display:block;width:100%}.comparison .ref{position:absolute;left:0;top:0;width:98.25%;opacity:.5}table{border-collapse:collapse}td,th{padding:8px 18px;border-bottom:1px solid #454b55;text-align:left}</style>
<h1>Shared compact panel grid · current Blender captures</h1>
<p>Smaller buttons and list tools; bold aligned captions; bounded numeric sliders; matching external-label edges; coordinated narrow layouts; visible artwork centered in every icon button. Implemented in Beyond UI, with no CamKeys UI source edits.</p>
<p><a href="../overview/index.html">Overview and updated estimate</a> · <a href="../../../PANEL_LAYOUT.md">Reusable layout rules</a> · <a href="report.json">Runtime evidence and limits</a></p>
<h2>Actual native panels</h2><div class="grid"><article><h3>Forced Perspective · narrow host</h3><img src="native-idle.png"></article><article><h3>CamKeys · compact list tools</h3><img src="list-idle.png"></article></div>
<h2>Generated target and implementation</h2><p>The comparison normalizes the concept's approximate 26 px body font to the implementation's 22 px body font. Panel width is not stretched to conceal layout differences. Reference v2 adds the requested slider and removes invented numeric arrows.</p>
<div class="grid"><article><h3>Generated v2</h3><img src="reference-comparison.png"></article><article><h3>Actual Blender · 286 logical units</h3><img src="implementation-comparison.png"></article></div>
<details><summary>Overlay comparison</summary><p>Reference opacity <input type="range" id="opacity" min="0" max="100" value="50"></p><div class="comparison"><img src="implementation-comparison.png"><img id="reference-overlay" class="ref" src="reference-comparison.png"></div></details>
<p class="note">Exact reference fidelity is still an open acceptance gate. Original Blender icon artwork, the active theme/backdrop, and author-supplied Lens/curve actions and separators differ from the concept. Those differences are visible here; the source controls and their owners are preserved.</p>
<h2>What changed in sizing</h2><table><tr><th>Control</th><th>Before</th><th>Now, logical units</th></tr><tr><td>Field</td><td>32</td><td>26</td></tr><tr><td>Primary action, 1.5× authored scale</td><td>48</td><td>30</td></tr><tr><td>Icon-only action</td><td>32</td><td>24</td></tr><tr><td>List tool</td><td>32, touching neighbors</td><td>22, with 4-unit gaps</td></tr><tr><td>External label inset</td><td>Mixed 0 and 6</td><td>0 for fields, switches and colors</td></tr></table>
<h2>Same-width before and after</h2><p>Width <select id="width"><option>260</option><option selected>360</option><option>480</option></select></p><div class="grid"><article><h3>Previous library</h3><img id="before" src="before-360.png"></article><article><h3>Current library</h3><img id="after" src="360-2x.png"></article></div>
<h2>Icon centering · real button pixels</h2><p>53 original source icons + 6 vector fallbacks, at 1×/1.5×/2×. All 177 button captures pass: maximum visible-bounds offset 0.5 framebuffer pixels. Source transparent padding is excluded; original shapes and proportions are retained. Below is the 2× sheet.</p><img style="image-rendering:pixelated;width:880px" src="icons-2x.png">
<h2>Owner menus and list expansion</h2><p>These GIFs are state slideshows, not animation timing demonstrations.</p><div class="grid"><article><img src="../../../media/panels/forced-perspective-v2.gif"></article><article><img src="../../../media/panels/camkeys-panel-v5.gif"></article></div>
<h2>Scale and width checks</h2><p>Scale <select id="scale"><option>1</option><option>1.5</option><option selected>2</option></select></p><img id="scaled" src="360-2x.png">
<p>292 unit tests; Blender 5.1.2 and 5.2.2 consumer checks; twelve width/scale captures per version. Native N-panel owner-menu routing, list expansion and text retention checked. Test launch audits recorded no activation. Updated installed CamKeys vendor is ready on next launch; unrelated live scenes were not reloaded or saved.</p>
<script>const w=document.querySelector('#width'),s=document.querySelector('#scale');function update(){document.querySelector('#before').src='before-'+w.value+'.png';document.querySelector('#after').src=w.value+'-2x.png';document.querySelector('#scaled').src=w.value+'-'+s.value+'x.png'}w.onchange=s.onchange=update;document.querySelector('#opacity').oninput=e=>document.querySelector('#reference-overlay').style.opacity=e.target.value/100;</script>''')
print(OUT)
