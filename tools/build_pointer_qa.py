"""Package actual pointer/decorator frames and immutable execution records."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/prop-pointer"
OUT = ROOT / "docs/design/qa/pointer-decorators-v1"
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(folder, suffix, run):
    source = BUILD / folder
    data = json.loads((source / "capture.json").read_text())
    assert data["passed"] and data["stable_resources"]
    assert data["native_text_batching_equal_frames"] == 100
    assert data["fixture_sha256"] == sha(ROOT / "tests/capture_pointer_decorators.py")
    for path, digest in data["source_sha256"].items():
        assert sha(ROOT / path) == digest, path
    shutil.copy2(source / "capture.json", OUT / f"capture{suffix}.json")
    shutil.copy2(BUILD / run / "blender-0.log", OUT / f"capture{suffix}.log")
    return data


current = capture("capture", "", "capture-run")
capture("capture-51", "-51", "capture-run-51")
for name in ("rest", "picker", "filtered", "decorator-context", "disabled"):
    shutil.copy2(BUILD / "capture" / f"{name}.png", OUT / f"{name}.png")
frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
media = ROOT / "docs/media/panels/pointer-decorators-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
media.with_suffix(".json").write_text(
    json.dumps(
        dict(
            source="Actual Blender 5.2.2 production frames; no generated pixels",
            capture="../../design/qa/pointer-decorators-v1/capture.json",
            sha256=sha(media),
        ),
        indent=2,
    )
    + "\n"
)
for name in (
    "runtime-final",
    "pointer-windowed-final",
    "menu-windowed-final",
    "event-windowed-final",
    "regression",
    "numeric",
    "events",
):
    for i, version in enumerate(("52", "51")):
        p = BUILD / name / f"result-{i}.json"
        assert json.loads(p.read_text())["passed"]
        label = "runtime" if name == "runtime-final" else name.replace("-final", "")
        shutil.copy2(p, OUT / f"{label}-{version}.json")
        shutil.copy2(BUILD / name / f"blender-{i}.log", OUT / f"{label}-{version}.log")
shutil.copy2(BUILD / "source/audit.json", OUT / "api-source-audit.json")
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Pointer pickers & decorators · QA v1</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto;border-radius:12px}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}.pair{display:flex;gap:20px;flex-wrap:wrap}.pair img{max-width:min(640px,100%)}</style>
<h1>Pointer pickers & animation decorators</h1>
<p>Actual Blender 5.2.2 Metal output. Compact ID pointer fields open the shared searchable picker. Decorators show empty, keyed, changed, animated and driven states, using the active Blender theme. Strong liquid glass, source springs, title typography and owner-aware right-click menus are shared with existing controls.</p>
<img src="../../../media/panels/pointer-decorators-v1.gif" alt="Actual pointer selection and decorator animation">
<h2>Property states and filtered picker</h2><div class="pair"><img src="rest.png" alt="Five animation states"><img src="filtered.png" alt="Filtered ID pointer popover"></div>
<h2>Exact property/component context</h2><img src="decorator-context.png" alt="Decorator property context menu">
<p>Real window tests also cover pointer-row Select/Copy Name context, keyboard selection, Escape dismissal, key insertion/deletion and host motion disable. Every one of 100 sampled frames matches between native-batched and standalone text rendering on each tested Blender version. Underlying field text is flushed before overlays; body and title text follow their owning transform.</p>
<p>The warm capture retains one backdrop, one strong blur, five offscreens, the same shaders/batches/fonts and one layout. No backdrop capture or blur is added during animation. Timing records measure CPU paint submission for this small workload; they do not establish all-platform source-level performance.</p>
<p><strong>Visual acceptance remains open.</strong> These are implementation captures using the existing control family, not an exact generated-reference comparison. Unexposed native pointer polls require a host policy. Non-ID pointers, eyedroppers, drag/drop, NLA/layer blending and complete property/layout semantics remain open.</p>
<p><a href="capture.json">5.2 capture/timing/hashes</a> · <a href="capture-51.json">5.1 capture/timing/hashes</a> · <a href="runtime-52.json">5.2 RNA checks</a> · <a href="runtime-51.json">5.1 RNA checks</a> · <a href="pointer-windowed-52.json">5.2 actual window input</a> · <a href="pointer-windowed-51.json">5.1 actual window input</a> · <a href="api-source-audit.json">Official source audit</a> · <a href="../../../POINTERS_AND_DECORATORS.md">Supported behavior and remaining gaps</a> · <a href="../context-menu-v6/index.html">Previous menu motion QA</a></p>""")
print(OUT)
