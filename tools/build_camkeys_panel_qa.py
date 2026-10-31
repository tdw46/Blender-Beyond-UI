"""Package immutable generated references and actual N-panel captures."""

import json, shutil, hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/camkeys-panel-v4"
OUT = ROOT / "docs/design/qa/camkeys-visual-v4"
OUT.mkdir(parents=True, exist_ok=True)
results = {
    name: json.loads((BUILD / f"{folder}/summary.json").read_text())
    for name, folder in [
        ("embedded", "final-panel-run"),
        ("empty", "final-empty-run"),
        ("media", "final-media-run"),
        ("boolean", "boolean-runtime"),
        ("consumer", "final-consumer-windowed"),
        ("installed", "installed-launch"),
    ]
}
assert all(run["passed"] for rows in results.values() for run in rows)
for name in ("idle", "hover", "settled", "expanded", "collapsed", "scrolled"):
    shutil.copy2(BUILD / "final-panel" / f"{name}.png", OUT / f"{name}.png")
for name in ("idle", "expanded"):
    shutil.copy2(BUILD / "final-empty" / f"{name}.png", OUT / f"empty-{name}.png")
for name in ("list", "help"):
    shutil.copy2(
        ROOT / f"docs/design/references/camkeys-panel-v2/{name}.png",
        OUT / f"reference-{name}.png",
    )
# Compare unchanged top text across a real layout rebuild (not merely hovering).
rects = {
    "header": (55, 18, 156, 42),
    "enable": (125, 139, 426, 162),
    "camera": (139, 348, 213, 374),
    "viewport": (332, 349, 422, 374),
    "lock": (193, 443, 366, 470),
}


def ink_count(im, rect):
    return sum(
        min(p) > 185 and max(p) - min(p) < 18
        for p in im.crop(rect).convert("RGB").getdata()
    )


checks = {}
a = Image.open(OUT / "idle.png")
b = Image.open(OUT / "expanded.png")
for name, rect in rects.items():
    before, after = ink_count(a, rect), ink_count(b, rect)
    checks[name] = {
        "idle_ink": before,
        "expanded_ink": after,
        "retained_fraction": after / max(1, before),
    }
    assert before > 20 and after >= before * 0.97, (name, checks[name])
# Absolute text recognition complements the relative ink comparison: two
# equally incomplete images must never count as a passing redraw regression.
ocr = json.loads((BUILD / "final-text.json").read_text())
required = [
    "Addon Enabled (Click to Disable)",
    "Select Camera",
    "Camera Lens",
    "Viewport",
    "Lock Cam to View",
    "HOW TO",
    "Hero mesh",
    "Hair strands",
    "Jacket folds",
    "Accessories",
]
for path, lines in ocr.items():
    joined = "\n".join(lines)
    assert all(label in joined for label in required), (path, lines)
assert len(ocr) == 3
(OUT / "text-recognition.json").write_text(json.dumps(ocr, indent=2) + "\n")
media = []
for kind, count, height in [("lists", 90, 600), ("brush", 105, 1520)]:
    frames = []
    for i in range(count):
        with Image.open(BUILD / "final-media" / f"{kind}-{i:03}.png") as im:
            frames.append(
                im.crop((0, 0, 1280, height))
                .resize((640, height // 2), Image.Resampling.LANCZOS)
                .convert("RGB")
            )
    pal = frames[0].quantize(colors=256)
    frames = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in frames]
    path = f"docs/media/panels/camkeys-{kind}-v4.gif"
    frames[0].save(
        ROOT / path,
        save_all=True,
        append_images=frames[1:],
        duration=[30 if i % 3 != 2 else 40 for i in range(count)],
        loop=0,
        optimize=False,
    )
    media.append(
        dict(title=f"CamKeys {kind}: current compact layout and right click", path=path)
    )
frames = [
    Image.open(OUT / f"{n}.png").convert("RGB")
    for n in ("idle", "expanded", "collapsed")
]
frames[0].save(
    ROOT / "docs/media/panels/camkeys-help-states-v4.gif",
    save_all=True,
    append_images=frames[1:],
    duration=1800,
    loop=0,
)
media.append(
    dict(
        title="CamKeys help: actual collapsed and expanded states (slideshow)",
        path="docs/media/panels/camkeys-help-states-v4.gif",
    )
)
(OUT / "current-media.json").write_text(json.dumps(media, indent=2) + "\n")
report = dict(
    results=results,
    text_rebuild_regression=checks,
    absolute_text_recognition="text-recognition.json",
    unit_tests=284,
    exact_match=False,
    reference_status="Geometry fixes implemented; exact visual match remains open.",
    reference_differences=[
        "Generated icons depict a cube and circular info glyph; implementation preserves the consumer-selected Blender OBJECT_DATA and INFO artwork.",
        "Generated glass/background/rim and help-card composition are not pixel-identical to the actual embedded host.",
        "Original consumer paragraph wording and rows=4 minimum are preserved; the concept shortens the wording.",
    ],
    source_hashes={
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "beyond_ui").rglob("*.py")
    },
    native_manifest=json.loads(
        (ROOT / "beyond_ui/_native/macos-arm64/manifest.json").read_text()
    ),
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>CamKeys panel corrections v4</title>
<style>body{font:16px system-ui;background:#191b20;color:#ecedf1;margin:32px}h1{font-size:28px}h2{font-size:20px}p{max-width:1000px;line-height:1.55}a{color:#a9ccff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#23262c;padding:16px;border-radius:14px}img{max-width:100%;height:auto}.native img{max-height:1300px}.note{padding:16px;background:#333041;border-radius:12px}</style>
<h1>Compact lists, centered help and centered menu carets</h1>
<p>The fixes are shared library behavior: compact name/status columns, centered unembossed Boolean buttons, author alignment, and one centered glyph on icon-only menus. Ordinary Boolean fields remain BVT switches. The native font queue is drained before custom framebuffer work, and owned text is submitted inside its control transform. Actual expand/collapse captures retain every checked label with glass enabled.</p>
<p class="note"><strong>Exact reference matching is still open.</strong> The generated concepts differ in original Blender icon shapes, glass rim/background and help-card composition. These differences are recorded, not counted as visual acceptance. Original consumer wording and the authored four-row minimum are retained.</p>
<div class="grid"><article><h2>Generated list reference</h2><img src="reference-list.png"></article><article><h2>Generated help states</h2><img src="reference-help.png"></article></div>
<div class="grid native"><article><h2>Actual Blender · four objects</h2><img src="idle.png"></article><article><h2>Actual Blender · help expanded</h2><img src="expanded.png"></article></div>
<div class="grid native"><article><h2>One empty item and no camera · matches reported data state</h2><img src="empty-idle.png"></article><article><h2>After collapsing again</h2><img src="collapsed.png"></article></div>
<h2>Current recorded list interaction</h2><img src="../../../media/panels/camkeys-lists-v4.gif"><h2>Help state comparison</h2><p>Recorded states, not an animation-speed demonstration.</p><img src="../../../media/panels/camkeys-help-states-v4.gif">
<p>284 unit tests, Boolean input/context checks on 5.1.2/5.2.2, actual embedded captures with original glass enabled. Headers and unchanged text retain their ink after expansion; absolute OCR checks also require all ten named labels in idle, expanded and collapsed captures. <a href="report.json">Tests, focus audit, timing, reference differences and source hashes</a> · <a href="../overview/index.html">Overview and estimate</a> · <a href="../camkeys-visual-v3/index.html">Previous implementation</a></p>""")
print(OUT)
