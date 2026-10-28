"""Package collection search captures without changing historical QA galleries."""

import hashlib, json, shutil
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/prop-search"
OUT = ROOT / "docs/design/qa/collection-search-v1"
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for suffix in ("", "-51"):
    record = json.loads((BUILD / f"capture{suffix}/capture.json").read_text())
    assert (
        record["passed"]
        and record["resting_pixels_equal"]
        and record["stable_resources"]
    )
    assert record["native_text_batching_equal_frames"] == 100
    assert record["fixture_sha256"] == sha(ROOT / "tests/capture_collection_search.py")
    assert record["baseline_sha256"] == sha(BUILD / "baseline/picker.py")
    for name, digest in record["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    shutil.copy2(BUILD / f"capture{suffix}/capture.json", OUT / f"capture{suffix}.json")
    shutil.copy2(
        BUILD / f"capture-run{suffix}/blender-0.log", OUT / f"capture{suffix}.log"
    )
for name in ("rest", "rest-before", "row-context", "disabled"):
    shutil.copy2(BUILD / "capture" / f"{name}.png", OUT / f"{name}.png")
shutil.copy2(BUILD / "baseline/picker.py", OUT / "baseline-picker.py")
shutil.copy2(BUILD / "source/audit.json", OUT / "api-source-audit.json")
frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
paired = []
for i, current in enumerate(frames):
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(Image.open(BUILD / "capture" / f"before-{i:03}.png"), (0, 32))
    board.paste(current, (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((12, 10), "Before: row background animates alone", fill="white")
    draw.text(
        (672, 10), "Now: background, icon and text animate together", fill="white"
    )
    paired.append(board)
for path, sequence in (
    (ROOT / "docs/media/panels/collection-search-v1.gif", frames),
    (OUT / "row-motion-comparison.gif", paired),
):
    sequence[0].save(
        path,
        save_all=True,
        append_images=sequence[1:],
        duration=33,
        loop=0,
        optimize=False,
        disposal=2,
    )
(ROOT / "docs/media/panels/collection-search-v1.json").write_text(
    json.dumps(
        dict(
            source="Actual production Blender frames; no generated pixels",
            capture="../../design/qa/collection-search-v1/capture.json",
            sha256=sha(ROOT / "docs/media/panels/collection-search-v1.gif"),
        ),
        indent=2,
    )
    + "\n"
)
for folder in (
    "runtime",
    "windowed",
    "pointer-regression",
    "regression",
    "pointer-windowed",
):
    for i, version in enumerate(("52", "51")):
        p = BUILD / folder / f"result-{i}.json"
        assert json.loads(p.read_text())["passed"]
        shutil.copy2(p, OUT / f"{folder}-{version}.json")
        shutil.copy2(
            BUILD / folder / f"blender-{i}.log", OUT / f"{folder}-{version}.log"
        )
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Collection search · QA v1</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}</style>
<h1>Collection search & component decorators</h1>
<p>Actual Blender output with 503 candidates, virtual scrolling and three standalone component decorators. The shared BVT glass, theme, typography and source spring remain in use. Search now validates the source, candidate and property value before committing, with rollback on host rejection.</p>
<img src="../../../media/panels/collection-search-v1.gif" alt="Collection search and context menu motion">
<h2>Before / after: whole-row motion</h2>
<img src="row-motion-comparison.gif" alt="Previous and current implementation side by side">
<p>Both sides are actual Blender renders under identical input, theme, scale and backdrop. The current implementation moves the row icon and label with its background. Resting pixels are byte-identical. This is an implementation comparison, not a generated-reference approval.</p>
<h2>Candidate right-click target</h2><img src="row-context.png" alt="Exact candidate context menu">
<p>Real window tests cover End/Enter selection, typed suggestions, right-click cancellation, candidate context menus and component keying. Both tested versions match all 100 sampled frames with native BLF batching enabled and disabled. Capture, strong blur, offscreen, font and recorded shader/batch resources remain stable.</p>
<p><strong>Parity remains partial.</strong> Non-ID pointer targets, compact search fields, native ranking/icon variants, complete focus traversal and exact generated-reference/theme/DPI acceptance remain open. Non-ID collection changes require host refresh; no polling timer is added.</p>
<p><a href="capture.json">5.2 capture and timing</a> · <a href="capture-51.json">5.1 capture and timing</a> · <a href="runtime-52.json">RNA behavior</a> · <a href="windowed-52.json">Actual window input</a> · <a href="api-source-audit.json">Official source audit</a> · <a href="../../../SEARCH_PROPERTIES.md">Integration and remaining gaps</a> · <a href="../pointer-decorators-v1/index.html">Earlier pointer/decorator pass</a></p>""")
print(OUT)
