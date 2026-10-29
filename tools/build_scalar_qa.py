"""Package source screenshots, production scalar captures and checked evidence."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/scalar-layout"
OUT = ROOT / "docs/design/qa/scalar-layout-v1"
OUT.mkdir(parents=True, exist_ok=True)
STATES = {
    "rest": "Active Blender theme",
    "red-reference-theme": "Explicit red comparison palette",
    "number-entry": "Separate numeric entry",
    "boolean-menu": "Boolean property menu rows",
    "color-alpha": "Hue and alpha sliders",
    "settled": "After motion settles",
    "disabled": "Motion disabled; glass retained",
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(record, fixture, source=ROOT):
    assert record["passed"] and record["stable_resources"]
    assert record["fixture_sha256"] == sha(ROOT / "tests" / fixture)
    for name, digest in record["source_sha256"].items():
        assert sha(source / name) == digest, name


for suffix in ("", "-51"):
    for dpi in ("1", "1.5", "2"):
        folder = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        data = read(BUILD / folder / "capture.json")
        verify(data, "capture_scalar_layout.py")
        assert data["native_text_batching_equal_frames"] == 150
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
        for name in STATES:
            shutil.copy2(
                BUILD / folder / (name + ".png"),
                OUT / (name + suffix + "-" + dpi + "x.png"),
            )
    for label in (
        "runtime",
        "windowed",
        "numeric",
        "menu-regression",
        "context-regression",
        "general",
    ):
        index = 1 if suffix else 0
        assert all(r["passed"] for r in read(BUILD / label / "summary.json"))
        for source, extension in (
            (f"result-{index}.json", ".json"),
            (f"blender-{index}.log", ".log"),
        ):
            shutil.copy2(
                BUILD / label / source,
                OUT / (label + ("-51" if suffix else "-52") + extension),
            )
    for revision in ("before", "after"):
        folder = "benchmark-" + revision + suffix
        data = read(BUILD / folder / "capture.json")
        source = ROOT if revision == "after" else BUILD / "baseline"
        verify(data, "benchmark_scalar_layout.py", source)
        assert Path(data["loaded_package"]).parent == source / "beyond_ui"
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
        for name in ("rest", "scalar"):
            shutil.copy2(
                BUILD / folder / (name + ".png"), OUT / (folder + "-" + name + ".png")
            )

frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 150
media = ROOT / "docs/media/panels/scalar-layout-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=[30, 30, 40] * 50,
    loop=0,
    optimize=False,
    disposal=2,
)
with Image.open(media) as preview:
    duration_ms = 0
    for frame in range(preview.n_frames):
        preview.seek(frame)
        duration_ms += preview.info["duration"]
    assert duration_ms == 5000
    encoded_frames = preview.n_frames
media.with_suffix(".json").write_text(
    json.dumps(
        {
            "source": "Actual production Blender frames; no generated pixels",
            "capture": "../../design/qa/scalar-layout-v1/capture.json",
            "sha256": sha(media),
            "source_frames": 150,
            "encoded_frames": encoded_frames,
            "duration_ms": duration_ms,
            "encoding": "Duplicate static frames share a longer duration; 30 fps source timing preserved at GIF centisecond resolution",
        },
        indent=2,
    )
    + "\n"
)
comparison = {
    "exact_match": False,
    "baseline_commit": "f048ce0bab12beae99a7906176a38b10499d87c4",
    "reference": "../../references/bvt-scalars-v1/reference.json",
    "acceptance": "Source geometry and behavior reused. Screenshot UI scale, exact theme and backdrop are unknown; this is not a pixel-match claim. Tyler owns visual acceptance.",
    "states": list(STATES),
}
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
rows = "".join(
    f'<figure><figcaption>{title}</figcaption><a class="capture" data-name="{name}" href="{name}-1x.png"><img src="{name}-1x.png" alt="{title}"></a></figure>'
    for name, title in STATES.items()
)
(OUT / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BVT sliders and switches · QA</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}p{max-width:1050px;line-height:1.6}img{max-width:100%;height:auto;display:block}figure{margin:0}figcaption{padding:10px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,640px));gap:16px}select{font:inherit;padding:6px;background:#292c30;color:white;border:1px solid #777;border-radius:6px}h2{margin-top:36px}.reference img{margin-bottom:22px}</style>
<h1>BVT sliders and switches</h1>
<p>Sliders now have a label, a thin track with a squash-and-stretch bubble, and a separate number field. Narrow rows stack the label above the controls. Boolean properties use the source glass switches, including contributed menu rows. Hue and alpha use the same slider treatment; hue retains its rainbow track.</p>
<h2>Your screenshots / actual Blender implementation</h2>
<div class="grid"><figure class="reference"><figcaption>Original user-provided BVT screenshots, unmodified</figcaption><img src="../../references/bvt-scalars-v1/slider.png" alt="BVT opacity slider reference"><img src="../../references/bvt-scalars-v1/switches.png" alt="BVT boolean switches reference"></figure><figure><figcaption>Production renderer · explicit red comparison palette</figcaption><img src="red-reference-theme-1x.png" alt="Actual BVT sliders and switches over shared glass"></figure></div>
<p>The source geometry, shaders and spring behavior are reused. These screenshots have unknown UI scale, exact theme and background, so this comparison does not establish exact pixel matching. The red palette is an explicit test fixture; production follows Blender’s active theme. <a href="comparison.json">Acceptance record</a>.</p>
<h2>Actual motion</h2><img src="../../../media/panels/scalar-layout-v1.gif" alt="Real Blender slider dragging, switch retargeting, numeric entry, menu reveal and hue/alpha interaction">
<p>Wide numeric controls retain the requested 15% amplitude. Switches use 0.36-second eased travel plus the source’s finite spring. Global/per-control motion settings still apply. No animation changes logical hit targets.</p>
<h2>Runtime and scale captures</h2>
<label for="dpi">Capture scale </label><select id="dpi"><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>
<label for="runtime"> Blender </label><select id="runtime"><option value="">5.2.2</option><option value="-51">5.1.2</option></select><div class="grid">"""
    + rows
    + """</div>
<p>900 motion frames match with native text batching enabled/disabled. One backdrop production, one strong blur, five offscreens and recorded font/shader/batch/layout identities remain stable. Window input covers track drag, number entry, switches, exact owner menus, rollback and idle teardown. <a href="runtime-52.json">RNA tests</a> · <a href="windowed-52.json">Window tests</a> · <a href="capture.json">Capture record</a>.</p>
<h2>Equivalent workload / before and after</h2><div class="grid"><figure><figcaption>Previous published revision f048ce0</figcaption><img src="benchmark-before-rest.png" alt="Previous scalar layout"></figure><figure><figcaption>Current implementation</figcaption><img src="benchmark-after-rest.png" alt="New BVT scalar layout"></figure></div>
<p>Eight sliders and three switches, then the same property context menu; 20 warmups and 100 CPU submission samples. The added bubble geometry and separate field/label draws have a measured cost; no extra backdrop capture or blur is introduced. These measurements do not establish GPU/input latency or source-equivalent speed. <a href="benchmark-before.json">Before</a> · <a href="benchmark-after.json">After</a> · <a href="../../../VALIDATION.md">Measured results and limits</a>.</p>
<p>Blender 4.2 fallbacks are retained but not runtime-qualified here. Exact screenshot/reference matching, broader theme/platform coverage and full API parity remain open. <a href="../../../SCALAR_CONTROLS.md">Behavior and integration</a>.</p>
<script>function updateCaptures(){const dpi=document.getElementById('dpi').value;const runtime=document.getElementById('runtime').value;for(const link of document.querySelectorAll('a.capture')){const path=`${link.dataset.name}${runtime}-${dpi}x.png`;link.href=path;link.querySelector('img').src=path;}}for(const id of ['dpi','runtime'])document.getElementById(id).addEventListener('change',updateCaptures);</script></html>"""
)
print(OUT)
