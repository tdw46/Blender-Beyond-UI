"""Package immutable CamKeys GPU captures; never paint replacement UI into media."""

import hashlib
import html
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build/camkeys-visual-v2/verified"
OUT = ROOT / "docs/design/qa/camkeys-visual-v2"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
report = json.loads((SOURCE / "capture.json").read_text())
assert report["passed"] and report["frames"] == 195
runtime = json.loads(
    (ROOT / "build/camkeys-visual-v2/verified-run/summary.json").read_text()
)
assert runtime[0]["passed"]
report["focus"] = runtime[0]["launch"]
report["validation"] = (
    json.loads((OUT / "report.json").read_text()).get("validation", {})
    if (OUT / "report.json").exists()
    else {}
)
report["api_evidence"] = (
    "Official versioned docs retrieval unavailable; 5.1.2/5.2.2 installed runtime checks used."
)
report["source_hashes"] = {}
for path in (ROOT / "beyond_ui").rglob("*.py"):
    report["source_hashes"][str(path.relative_to(ROOT))] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
consumer = Path(report["consumer"])
report["consumer_hashes"] = {
    str(p.relative_to(consumer)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in consumer.rglob("*.py")
    if ".git" not in p.parts and "__pycache__" not in p.parts
}
report["resolved_visual_gaps"] = [
    "Explicit empty RNA labels remain empty; compact label-free switches and fixed row separators leave room for object names.",
    "All six curve preset icons use cached vector geometry, centered with theme tint and existing motion/context ownership.",
    "Untitled registered popovers omit the blank title row; titled popovers keep their normal heading.",
]
report["known_visual_gaps"] = [
    "Exact generated-reference matching and Tyler visual acceptance remain pending.",
    "One width at 2x is recorded; broader scale/theme acceptance is not implied.",
]
report["coverage"] = [
    "Actual CamKeys registered tracked-object UIList: selection, wheel scrolling, list context menu",
    "Actual mesh brush popover: opening motion, point drag and handle context menu",
    "Actual distance and flatten brush popover stills",
    "Factory dark plus synthetic light and purple theme-role fixtures",
]
report["limits"] = [
    "Controlled GPU offscreen, not a screenshot of the whole Blender application or installed live addon.",
    "One logical width (560), 2x framebuffer scale; no new 1x/1.5x/narrow qualification.",
    "Visual fixture preserves existing renderer and interactions; it is not a new functional parity test.",
    "CPU paint timings exclude readback and GPU completion; not a source-performance equivalence benchmark.",
]
report["media"] = []
current = []
for kind, count, crop, title in [
    (
        "lists",
        90,
        (0, 0, 1280, 600),
        "CamKeys tracked-object list: selection, scrolling and context menu",
    ),
    (
        "brush",
        105,
        (0, 0, 1280, 1520),
        "CamKeys brush falloff: opening bounce, point edit and context menu",
    ),
]:
    frames = []
    for i in range(count):
        with Image.open(SOURCE / f"{kind}-{i:03}.png") as im:
            frames.append(
                im.crop(crop)
                .resize((640, crop[3] // 2), Image.Resampling.LANCZOS)
                .convert("RGB")
            )
    # One retained palette per movie avoids color flicker between matching pixels.
    sheet = Image.new("RGB", (640 * 4, frames[0].height))
    for n, i in enumerate((0, count // 3, count // 2, count * 3 // 4)):
        sheet.paste(frames[i], (640 * n, 0))
    palette = sheet.quantize(colors=256)
    encoded = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    path = MEDIA / f"camkeys-{kind}-v2.gif"
    durations = [30 if i % 3 != 2 else 40 for i in range(count)]
    encoded[0].save(
        path,
        save_all=True,
        append_images=encoded[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=1,
    )
    with Image.open(path) as gif:
        duration = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            duration += gif.info["duration"]
        assert duration == round(count / 30 * 1000)
        media = dict(
            path=str(path.relative_to(ROOT)),
            captured_frames=count,
            encoded_frames=gif.n_frames,
            duration_ms=duration,
            crop=crop,
            playback_dimensions=list(gif.size),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    report["media"].append(media)
    current.append(dict(title=title, path=str(path.relative_to(ROOT))))
    (path.with_suffix(".json")).write_text(json.dumps(media, indent=2) + "\n")
stills = [
    "lists-rest",
    "lists-context",
    "brush-rest",
    "brush-context",
    "brush-theme-light",
    "brush-theme-purple",
    "brush-distance",
    "brush-flatten",
]
for name in stills:
    shutil.copy2(SOURCE / (name + ".png"), OUT / (name + ".png"))
for name in ("lists-046", "brush-002", "brush-030"):
    shutil.copy2(SOURCE / (name + ".png"), OUT / (name + ".png"))
# Keep full-resolution unmodified source sequences available beside the readable GIFs.
import zipfile

with zipfile.ZipFile(
    OUT / "raw-frames.zip", "w", compression=zipfile.ZIP_STORED
) as archive:
    for prefix, count in [("lists", 90), ("brush", 105)]:
        for i in range(count):
            p = SOURCE / f"{prefix}-{i:03}.png"
            archive.write(p, p.name)
(OUT / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(OUT / "current-media.json").write_text(json.dumps(current, indent=2) + "\n")


def still(name, caption):
    return f'<figure><a href="{name}.png"><img loading="lazy" src="{name}.png" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)} · <a href="{name}.png">full-resolution PNG</a></figcaption></figure>'


movies = "".join(
    f'<article><h2>{html.escape(r["title"])}</h2><img class="movie" src="../../../../{r["path"]}" alt="{html.escape(r["title"])}"><p>{"3 seconds: select → scroll → open menu → close." if i == 0 else "3.5 seconds: reveal → drag point → open handle menu → close."}</p></article>'
    for i, r in enumerate(current)
)
page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CamKeys · Visual QA v2</title>
<style>body{background:#171b22;color:#edf1f7;font:16px/1.55 system-ui;margin:0}main{max-width:1320px;margin:auto;padding:32px}h1{font-size:32px;line-height:1.2}h2{font-size:20px}a{color:#a6caff}.note{padding:18px 24px;background:#283446;border:1px solid #536d8c;border-radius:14px}.gaps{background:#352e25;border-color:#88704c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px}article,figure{margin:0;padding:16px;background:#222832;border-radius:14px;overflow:hidden}img{width:100%;height:auto;display:block}figcaption{padding-top:12px;color:#bfc9d8}button{font:inherit;color:#edf1f7;background:#35445c;border:1px solid #6882a7;border-radius:8px;padding:8px 14px;cursor:pointer}section{margin-top:30px}li{margin:6px 0}small{color:#bfc9d8}</style><main>
<p><a href="../overview/index.html">← Feature overview</a> · <a href="../core-review-v2/index.html">Core controls review</a></p><h1>CamKeys · Lists & brush curves</h1>
<p>Current implementation captures from the isolated CamKeys branch. Ready for your visual review; the three requested presentation defects are corrected.</p>
<div class="note"><strong>Real Blender GPU rendering · 5.2.2 LTS · macOS</strong><p>These use the actual registered CamKeys list and popover bodies, production BVT glass and motion, native text batching, and owner-aware right-click menus. The background is a controlled text/contrast fixture. This is an offscreen render, not a screenshot of the installed live add-on.</p><p>PNG originals are 1280 × 1520 at 2× scale. GIFs are reduced to 640px wide; the list movie is cropped to its content. Use PNGs for color, typography and edge inspection.</p><small>Single-line integration unchanged. Tested code installed on the dedicated CamKeys test branch for next launch; current unsaved scene not reloaded or saved. Final capture run: no owned test-window activation or focus-restore requests. Other app events, if any, remain in the audit. One shared glass production across the capture sequence.</small></div>
<section><h2>Motion review</h2><p>Watch the opening bounce, point movement, and context-menu labels together. Static frames below make it easier to inspect details.</p><button id="motion">Hide moving demos</button><div class="grid" id="movies">MOVIES</div></section>
<section class="note gaps"><h2>Corrected in this review</h2><ul>GAPS</ul><p>The original captures are preserved below for comparison. Exact generated-reference acceptance remains pending; these corrections are not a claim of universal parity.</p></section>
<section><h2>List & right-click detail</h2><div class="grid">LISTS</div></section>
<section><h2>Before / after · same capture scale</h2><div class="grid"><figure><img loading="lazy" src="../camkeys-visual-v1/lists-rest.png" alt="Previous crowded list"><figcaption>Before · extra labels and separators crowd the list</figcaption></figure><figure><img loading="lazy" src="lists-rest.png" alt="Corrected list"><figcaption>After · external names, label-free switches and object icons</figcaption></figure><figure><img loading="lazy" src="../camkeys-visual-v1/brush-rest.png" alt="Previous brush popover"><figcaption>Before · blank header and truncated preset labels</figcaption></figure><figure><img loading="lazy" src="brush-rest.png" alt="Corrected brush popover"><figcaption>After · compact header and six centered preset glyphs</figcaption></figure></div></section><section><h2>All three consumer brush popovers</h2><div class="grid">BRUSHES</div></section>
<section><h2>Owner menu & motion frames</h2><div class="grid">STATES</div></section>
<section><h2>Theme roles</h2><p>Factory dark is used above. The following are synthetic light and purple theme inputs through the normal extraction path, not installed Blender theme presets. Compare readable text, highlights, field contrast and glass.</p><div class="grid">THEMES</div></section>
<section><h2>Your review checklist</h2><ul><li>List density, name readability, icons and switch size.</li><li>Brush point motion, curve thickness, field alignment and preset buttons.</li><li>Glass blur/rims over the contrasting text background, including nested context menus.</li><li>Menu text and icons moving together during opening; resting geometry after settling.</li><li>Dark/light/purple theme contrast and consistent control scale.</li></ul><p>Generated-reference matching and your acceptance remain pending. The captures do not requalify every context action, platform or UI scale.</p></section>
<section class="note"><h2>Ready on your next Blender 5.2 launch</h2><p>The canonical CamKeys install is on <code>codex/camkeys-beyond-ui-test</code> with the tested source and vendor package. CamKeys is enabled in saved preferences. A fresh no-focus process read a copy of those preferences and registered that installed module successfully. Your current unsaved scene and running add-on were not reloaded.</p><p><a href="launch-runtime.json">Installed-module and saved-preference check</a> · <a href="consumer-runtime.json">5.1.2 / 5.2.2 consumer regressions</a> · <a href="labels-runtime.json">RNA label/layout checks</a></p></section><p><a href="raw-frames.zip">Full-resolution raw motion frames (ZIP)</a> · <a href="report.json">Provenance, source hashes and coverage</a> · <a href="runtime.json">Runtime and focus audit</a> · <a href="../camkeys-custom-v1/runtime.json">Earlier functional checks</a></p>
<script>document.querySelector('#motion').onclick=()=>{const e=document.querySelector('#movies');e.hidden=!e.hidden;document.querySelector('#motion').textContent=e.hidden?'Show moving demos':'Hide moving demos'}</script></main></html>"""
for token, value in {
    "MOVIES": movies,
    "GAPS": "".join(
        "<li>" + html.escape(s) + "</li>" for s in report["resolved_visual_gaps"]
    ),
    "LISTS": still("lists-rest", "Tracked objects · initial selection")
    + still("lists-context", "Scrolled rows · list-level context menu"),
    "BRUSHES": still("brush-rest", "Mesh falloff · resting appearance")
    + still("brush-distance", "Distance falloff · resting appearance")
    + still("brush-flatten", "Flatten falloff · resting appearance"),
    "STATES": still("brush-context", "Handle owner context · after point edit")
    + still("brush-002", "Opening motion · frame 2")
    + still("brush-030", "Point drag · frame 30")
    + still("lists-046", "List menu opening · frame 46"),
    "THEMES": still("brush-theme-light", "Synthetic light theme roles")
    + still("brush-theme-purple", "Synthetic purple theme roles"),
}.items():
    page = page.replace(token, value)
(OUT / "index.html").write_text(page)
print(json.dumps(report["media"], indent=2))
