"""Package actual embedded-host evidence and source captures, without repainting UI."""

from pathlib import Path
import hashlib, json, shutil
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/camkeys-lists-v3"
OUT = ROOT / "docs/design/qa/camkeys-visual-v3"
OUT.mkdir(parents=True, exist_ok=True)
embedded = json.loads((BUILD / "verified-run/summary.json").read_text())[0]
media = json.loads((BUILD / "verified-media-run/summary.json").read_text())[0]
consumer = json.loads((BUILD / "consumer/summary.json").read_text())
assert embedded["passed"] and media["passed"] and all(r["passed"] for r in consumer)
for name in ("idle", "hover", "settled", "scrolled"):
    shutil.copy2(BUILD / "verified" / f"{name}.png", OUT / f"{name}.png")
shutil.copy2(BUILD / "embedded2/idle.png", OUT / "before.png")
shutil.copy2(
    ROOT / "docs/design/references/camkeys-lists-v1/reference.png",
    OUT / "reference.png",
)
for name in ("lists-rest", "lists-context", "brush-rest", "brush-context"):
    shutil.copy2(BUILD / "verified-media" / f"{name}.png", OUT / f"{name}.png")
for kind, count, height in [("lists", 90, 600), ("brush", 105, 1520)]:
    frames = []
    for i in range(count):
        with Image.open(BUILD / "verified-media" / f"{kind}-{i:03}.png") as im:
            frames.append(
                im.crop((0, 0, 1280, height))
                .resize((640, height // 2), Image.Resampling.LANCZOS)
                .convert("RGB")
            )
    palette = frames[0].quantize(colors=256)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    target = ROOT / f"docs/media/panels/camkeys-{kind}-v3.gif"
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=[30 if i % 3 != 2 else 40 for i in range(count)],
        loop=0,
        optimize=False,
    )
# Text areas outside the deliberate hover target must retain identical pixels.
idle = Image.open(OUT / "idle.png").convert("RGB")
settled = Image.open(OUT / "settled.png").convert("RGB")
checks = {}
for label, rect in {
    "camera_and_viewport": (140, 346, 423, 378),
    "lock_label": (190, 438, 371, 469),
    "lens_label": (70, 612, 198, 642),
    "object_names": (169, 909, 310, 1285),
}.items():
    a, b = idle.crop(rect), settled.crop(rect)
    delta = ImageChops.difference(a, b)
    checks[label] = {"identical": delta.getbbox() is None}
assert all(c["identical"] for c in checks.values()), checks
report = dict(
    embedded=embedded,
    consumer=consumer,
    offscreen=media,
    text_stability=checks,
    exact_match=False,
    reference_conflicts=[
        "Consumer-authored No Armature status is retained on a second line in narrow rows; reference omits it.",
        "Reference search is expanded; actual consumer filter is initially collapsed.",
        "Consumer supplies OBJECT_DATA glyph, not the concept cube; original icon preserved.",
    ],
    remaining=[
        "Tyler visual acceptance and exact reference reconciliation",
        "Broad icons beyond the 53 source glyphs in this consumer audit",
        "Other consumer-authored layouts and platform/4.2 visual qualification",
    ],
    source_hashes={
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "beyond_ui").rglob("*.py")
    },
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>CamKeys UIList and embedded text repair</title>
<style>body{margin:32px;background:#191b20;color:#e6e7ea;font:16px system-ui}h1{font-size:28px}h2{font-size:20px}p{max-width:1000px;line-height:1.5}a{color:#a9ccff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#23262c;padding:16px;border-radius:14px}img{max-width:100%;height:auto}.host img{max-height:1100px}label{display:block;margin:16px}#wipe{position:relative;max-width:561px}#wipe img{display:block;width:100%}#old{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}</style>
<h1>CamKeys: embedded text, source icons and list layout</h1>
<p>Actual Blender 5.2.2 N-panel captures now complement the controlled offscreen demos. Body text and native headers are flushed before GPU clipping/transforms change. Original Blender glyphs use one retained atlas. The list owns most of its row; action rails remain compact.</p>
<p><strong>Reference match remains open.</strong> The generated concept omits CamKeys’ “No Armature” status and uses a cube instead of its OBJECT_DATA icon. The implementation preserves those authored semantics. Narrow rows retain secondary status on a second line. This is a functional correction, not a claim of pixel-exact concept acceptance.</p>
<div class="grid"><article><h2>Generated target</h2><img src="reference.png"></article><article><h2>Actual list at a wide width</h2><img src="lists-rest.png"><h2>List actions, motion and right click</h2><img src="../../../media/panels/camkeys-lists-v3.gif"></article></div>
<h2>Actual embedded N-panel: before / corrected</h2><p>Drag the divider. Before capture already includes the icon atlas and compact action rail; it exposes the remaining native text-batching failure before the final repair.</p>
<label>Comparison <input type="range" min="0" max="100" value="50" oninput="document.querySelector('#old').style.clipPath='inset(0 '+(100-this.value)+'% 0 0)'"></label>
<div id="wipe"><img src="idle.png"><img id="old" src="before.png"></div>
<div class="grid host"><article><h2>After hover has settled</h2><img src="settled.png"></article><article><h2>After scrolling</h2><img src="scrolled.png"></article></div>
<h2>Brush curves and original preset glyphs</h2><img src="../../../media/panels/camkeys-brush-v3.gif">
<p>283 unit tests; 5.1.2/5.2.2 consumer action and context checks. No activation events in recorded test launches. Captures retain BVT glass and active theme roles; factory viewport background differs from your live scene. Timing excludes readback and GPU completion. <a href="report.json">Runtime, focus, pixel-stability and timing evidence</a> · <a href="../overview/index.html">Overview and remaining work</a></p>""")
print(OUT)
