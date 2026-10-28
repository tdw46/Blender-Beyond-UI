"""Package v4 rendered menu evidence, preserving prior QA artifacts."""

from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/context-menu-v4"
SOURCE = BASE / "capture"
OUT = ROOT / "docs/design/qa/context-menu-v4"
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
        not path.stem.startswith(("frame-", "mode-"))
        and not path.stem.removeprefix("shortcut-").isdigit()
    ):
        shutil.copy2(path, OUT / path.name)
shutil.copy2(SOURCE / "capture.json", OUT / "capture.json")
shutil.copy2(BASE / "capture-run/blender-0.log", OUT / "capture.log")
for kind, folder in (
    ("adapters", "adapters"),
    ("parity", "parity-complete"),
    ("modal", "modal"),
    ("regression", "regression"),
):
    for index, version in enumerate(("52", "51")):
        path = BASE / folder / f"result-{index}.json"
        assert json.loads(path.read_text())["passed"]
        shutil.copy2(path, OUT / f"{kind}-{version}.json")
        shutil.copy2(
            BASE / folder / f"blender-{index}.log", OUT / f"{kind}-{version}.log"
        )


def pair(first, second, name, left, right):
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(Image.open(OUT / first), (0, 32))
    board.paste(Image.open(OUT / second), (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((10, 10), left, fill="white")
    draw.text((670, 10), right, fill="white")
    board.save(OUT / name)


pair(
    "favorite-add.png",
    "favorite-remove.png",
    "favorites.png",
    "Before adding a favorite",
    "Exact property after adding: Remove",
)
pair(
    "mouse-capture.png",
    "chord-capture.png",
    "capture-modes.png",
    "Mouse / NDOF capture",
    "Held-key chord capture",
)
pair(
    "enum-choices.png",
    "enum-shortcuts.png",
    "enum-menus.png",
    "Contributed enum: current choice marked",
    "Shortcut to an exact enum value",
)
pair(
    "tint-fallback.png",
    "root.png",
    "glass-comparison.png",
    "Degraded tint fallback",
    "Required BVT liquid glass",
)
media = ROOT / "docs/media/panels/context-menu-shortcut-v4.gif"
frames = [Image.open(p).convert("RGBA") for p in sorted(SOURCE.glob("mode-[0-9]*.png"))]
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:] + [frames[-1]] * 15,
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
media.with_suffix(".json").write_text(
    json.dumps(
        {
            "source": "Actual Blender Canvas frames; unchanged BVT glass and spring; no generated pixels",
            "capture": "../../design/qa/context-menu-v4/capture.json",
            "gif_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
            "source_frame_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(SOURCE.glob("mode-[0-9]*.png"))
            },
        },
        indent=2,
    )
    + "\n"
)
previous = json.loads(
    (ROOT / "docs/design/qa/context-menu-v3/capture.json").read_text()
)
comparison = {
    "exact_match": False,
    "reference_status": "No accepted generated liquid-glass reference; rejected v1 retained unchanged",
    "reference_matched": False,
    "theme": record["theme"],
    "dimensions": record["dimensions"],
    "warm_cpu_submission_before_ms": previous["timings"],
    "warm_cpu_submission_after_ms": record["timings"],
    "scope": "Equivalent 640x560 root/nested/scroll fixture, 20 warmups and 100 samples; CPU submission only, no GPU completion fence or end-to-end latency claim.",
    "capture_shutdown": "Current capture log has no allocation warning. Historical v1/v2 MTLSafeFreeList warning remains an unresolved intermittent backend observation, not a demonstrated fix.",
}
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Beyond UI context menus · QA v4</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}</style>
<h1>Right-click menu parity · QA v4</h1>
<p>Actual Blender 5.2.2 Metal renders at 640×560, explicit REFERENCE theme. Behavior tests pass on exact macOS arm64 5.1.2/5.2.2 builds. These are implementation captures for Tyler's QA; no generated-reference acceptance is claimed.</p>
<h2>Quick Favorites add/remove</h2><img src="favorites.png">
<p>Exact properties/components and operator arguments are looked up again before removal. Querying never marks preferences dirty; changes never save preferences.</p>
<h2>Keyboard-accessible capture modes</h2><img src="capture-mode-picker.png"><p>Arrows and Enter select a mode before capture starts. Cancel returns to the mode chooser; navigation keys remain assignable during capture. The mode chooser shares the existing menu depth budget.</p><h2>Shortcut capture and bounce</h2><img src="capture-modes.png"><p><img src="../../../media/panels/context-menu-shortcut-v4.gif"></p>
<p>Keyboard, explicit mouse/NDOF-button and held-key modes share the existing painter, spring and glass. Escape/right-click cancel. Common global and View3D keymap conflicts are rejected.</p>
<h2>Contributed enum fields and value shortcuts</h2><img src="enum-menus.png">
<p>Boolean/enum contribution rows preserve owner identity, disabled state and host commit rollback. Enum flags toggle the requested flag only. Operator choice rows retain invocation, arguments and pointer context. Inline nested menus preserve disabled state and invocation. Bounded deep snapshots isolate mutable arguments; stale registered operators and invalid pointer arguments cannot execute. Unsupported arguments and failing nested callbacks are isolated.</p>
<h2>Glass remains shared</h2><img src="glass-comparison.png">
<p>One backdrop production, one strong-blur production and five retained offscreens serve the captured menus and animation. No per-frame capture or blur. Resting and animation-disabled root pixels are equal.</p>
<h2>Open acceptance and integration cases</h2>
<p>Custom-popup shortcut dispatch, arbitrary editor/modal keymap hierarchy, scalar inline editors, dynamic enum callbacks, string contexts, broader platforms/themes/DPI/windows, and exact generated motion/reference acceptance remain open. <a href="../../../CONTEXT_MENUS.md">Integration contract and limitations</a>.</p>
<p>Historical <a href="../context-menu-v1/index.html">rejected generation v1</a> and <a href="../context-menu-v3/index.html">v3 evidence</a> remain unchanged. Current capture has no allocation warning; this does not establish a fix for the prior intermittent Metal shutdown warning.</p>
<h2>Evidence</h2><p><a href="capture.json">Source hashes, resources, timings</a> · <a href="capture.log">Capture log</a> · <a href="comparison.json">Before/after metrics</a> · <a href="parity-51.json">New cases 5.1.2</a> · <a href="parity-52.json">New cases 5.2.2</a> · <a href="modal-51.json">Window input 5.1.2</a> · <a href="modal-52.json">Window input 5.2.2</a></p>
""")
print(OUT)
