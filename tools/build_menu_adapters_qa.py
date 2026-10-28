"""Package versioned menu-adapter evidence without altering rendered pixels."""

from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/context-menu-v2"
SOURCE = BASE / "capture"
OUT = ROOT / "docs/design/qa/context-menu-v2"
OUT.mkdir(parents=True, exist_ok=True)
record = json.loads((SOURCE / "capture.json").read_text())
assert record["passed"] and record["stable_resources"]
for name, digest in record["source_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
assert (
    record["fixture_sha256"]
    == hashlib.sha256((ROOT / "tests/capture_context_menu.py").read_bytes()).hexdigest()
)
for path in SOURCE.glob("*.png"):
    if (
        not path.stem.startswith("frame-")
        and not path.stem.removeprefix("shortcut-").isdigit()
    ):
        shutil.copy2(path, OUT / path.name)
shutil.copy2(SOURCE / "capture.json", OUT / "capture.json")
shutil.copy2(BASE / "capture-deferred-quit/blender-0.log", OUT / "capture.log")
shutil.copy2(
    BASE / "capture-diagnostic/blender.log", OUT / "metal-shutdown-diagnostic.log"
)
for slug, folder in (
    ("adapters", "adapters-final"),
    ("rna", "rna"),
    ("modal", "modal-final"),
    ("regression", "regression"),
):
    for index, version in enumerate(("52", "51")):
        path = BASE / folder / f"result-{index}.json"
        assert json.loads(path.read_text())["passed"]
        shutil.copy2(path, OUT / f"{slug}-{version}.json")


def pair(first, second, name, left, right):
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(Image.open(first), (0, 32))
    board.paste(Image.open(second), (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((10, 10), left, fill="white")
    draw.text((670, 10), right, fill="white")
    board.save(OUT / name)


pair(
    OUT / "tint-fallback.png",
    OUT / "root.png",
    "glass-comparison.png",
    "Degraded tint fallback",
    "Required BVT liquid glass",
)
pair(
    OUT / "nested.png",
    OUT / "shortcut-capture.png",
    "capture-comparison.png",
    "Shared nested menu material",
    "Shortcut capture uses the same material",
)
media = ROOT / "docs/media/panels/context-menu-shortcut.gif"
frames = [
    Image.open(p).convert("RGBA") for p in sorted(SOURCE.glob("shortcut-[0-9]*.png"))
]
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:] + [frames[-1]] * 15,
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
provenance = {
    "source": "Actual Blender Canvas frames; source glass and spring; no generated pixels",
    "capture": "../../design/qa/context-menu-v2/capture.json",
    "gif_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
    "source_frame_sha256": {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(SOURCE.glob("shortcut-[0-9]*.png"))
    },
}
media.with_name("context-menu-shortcut-provenance.json").write_text(
    json.dumps(provenance, indent=2) + "\n"
)
previous = json.loads(
    (ROOT / "docs/design/qa/context-menu-v1/capture.json").read_text()
)
comparison = {
    "exact_match": False,
    "reference_status": "No accepted generated liquid-glass reference; v1 rejected and retained",
    "reference_matched": False,
    "theme": record["theme"],
    "dimensions": record["dimensions"],
    "warm_cpu_submission_before_ms": previous["timings"],
    "warm_cpu_submission_after_ms": record["timings"],
    "capture_shutdown_warning": "One 65,624-byte MTLSafeFreeList allocation reported by Blender Metal at capture shutdown; also present in historical v1 capture logs. Owned glass caches are explicitly empty after release. Backend cause remains unresolved.",
    "scope": "Same 640x560 root/nested/scroll fixture, 20 warmups, 100 samples; no GPU completion fence. Navigation includes new native capability checks; not an end-to-end latency or cross-platform speed claim.",
}
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
cards = "".join(
    f'<figure><img src="control-{slug}.png"><figcaption>{slug} · {part}</figcaption></figure>'
    for slug, part in record["compound_targets"].items()
)
(OUT / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>Beyond UI menu adapters · QA v2</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1000px;line-height:1.6}.grid{display:grid;grid-template-columns:repeat(2,minmax(300px,640px));gap:20px}figure{margin:0}figcaption{padding:8px;color:#bdc5cc}h2{margin-top:36px}</style>
<h1>Menu adapters · liquid-glass QA v2</h1>
<p>Blender 5.2.2 / Metal, 640×560, explicit REFERENCE theme. Real driver clipboard, property/operator Quick Favorites, keyboard shortcut assignment/change/removal, Edit Source and Python tooltip text are execution-tested on exact macOS arm64 5.1.2/5.2.2 builds. Private adapters fail closed elsewhere. Tyler owns visual acceptance.</p>
<h2>Required glass versus degraded fallback</h2><img src="glass-comparison.png">
<h2>Shortcut capture · shared material and motion</h2><img src="capture-comparison.png"><p><img src="../../../media/panels/context-menu-shortcut.gif"></p>
<p>Actual rendered frames, with one shared backdrop preparation, one strong blur and five retained offscreens. No capture/blur passes added per animation frame. Resting/disabled main menu pixels remain identical.</p>
<h2>Existing compound controls</h2><div class="grid">"""
    + cards
    + """</div>
<p>The capture process still reports a 65,624-byte Metal MTLSafeFreeList shutdown allocation, also seen in historical v1 captures. Owned glass caches clear after release. <a href="metal-shutdown-diagnostic.log">Diagnostic log</a>; the backend cause remains unresolved.</p>
<h2>Reference gate remains open</h2><p>No exact generated-reference acceptance is claimed. The <a href="../context-menu-v1/index.html">rejected v1 generation and comparisons</a> remain immutable. These captures document source-material reuse, not a new approved generated reference.</p>
<h2>Execution and performance evidence</h2><p><a href="capture.json">Render, resource and timing record</a> · <a href="comparison.json">Before/after and acceptance status</a> · <a href="adapters-51.json">Adapters 5.1.2</a> · <a href="adapters-52.json">Adapters 5.2.2</a> · <a href="modal-51.json">Actual window input 5.1.2</a> · <a href="modal-52.json">Actual window input 5.2.2</a></p>
<p><a href="../../../CONTEXT_MENUS.md">Supported cases and explicit remaining gaps</a></p>"""
)
print(OUT)
