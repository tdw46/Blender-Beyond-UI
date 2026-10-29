"""Package actual compact search evidence without replacing earlier galleries."""

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/search-popover"
OUT = ROOT / "docs/design/qa/search-popover-v1"
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for suffix in ("", "-51"):
    record = json.loads((BUILD / f"capture{suffix}/capture.json").read_text())
    assert record["passed"] and record["stable_resources"]
    assert record["native_text_batching_equal_frames"] == 100
    assert record["fixture_sha256"] == sha(ROOT / "tests/capture_search_popover.py")
    for name, digest in record["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    shutil.copy2(BUILD / f"capture{suffix}/capture.json", OUT / f"capture{suffix}.json")
    shutil.copy2(
        BUILD / f"capture-run{suffix}/blender-0.log", OUT / f"capture{suffix}.log"
    )
for name in ("rest", "picker", "filtered", "field-context", "disabled"):
    shutil.copy2(BUILD / "capture" / f"{name}.png", OUT / f"{name}.png")
frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 100
media = ROOT / "docs/media/panels/search-popover-v1.gif"
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
        {
            "source": "Actual production Blender frames; no generated pixels",
            "capture": "../../design/qa/search-popover-v1/capture.json",
            "sha256": sha(media),
        },
        indent=2,
    )
    + "\n"
)
for folder in (
    "runtime",
    "windowed",
    "card-regression",
    "pointer-regression",
    "regression",
    "card-windowed",
    "pointer-windowed",
):
    for i, version in enumerate(("52", "51")):
        path = BUILD / folder / f"result-{i}.json"
        assert json.loads(path.read_text())["passed"], str(path)
        shutil.copy2(path, OUT / f"{folder}-{version}.json")
        shutil.copy2(
            BUILD / folder / f"blender-{i}.log", OUT / f"{folder}-{version}.log"
        )
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Compact search · QA v1</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}.pair{display:flex;gap:16px;flex-wrap:wrap}.pair figure{margin:0;max-width:640px}figcaption{padding:8px 0}</style>
<h1>Compact search fields and owned popovers</h1>
<p>Actual Blender output: compact prop_search and template_search fields open the shared custom picker. Closed fields read only the current property; opening snapshots the candidates. Type immediately, navigate, select, or cancel. Successful selection closes the popover; a rejected host commit leaves it open for correction.</p>
<img src="../../../media/panels/search-popover-v1.gif" alt="Actual search popover opening, filtering, selection and candidate menu animation">
<h2>Closed / open</h2><div class="pair"><figure><img src="rest.png" alt="Compact resting fields"><figcaption>Closed fields · no candidate scan</figcaption></figure><figure><img src="picker.png" alt="Open liquid glass picker"><figcaption>503 candidates · visible rows only</figcaption></figure></div>
<h2>Filtering / field actions</h2><div class="pair"><figure><img src="filtered.png" alt="Filtered search results"><figcaption>Immediate typing</figcaption></figure><figure><img src="field-context.png" alt="Exact property context menu"><figcaption>Owner-aware field actions</figcaption></figure></div>
<p>The picker inherits the field's shared BVT spring settings and strong glass; menus retain their own strong blur. The fixture reproduces PanelHost's existing base-glass pass before the canvas tint. It adds no production capture or blur pass. Across all 100 frames on each tested version, native BLF batching matches standalone submission exactly. One backdrop production, one strong blur, five offscreens and recorded font/shader/batch identities remain stable.</p>
<p>Blender 5.1.2 and 5.2.2 pass runtime and real-window checks, including immediate typing, row context menus, selection, cancellation, stale values, rejected commits, motion disable and teardown. Full-card search remains available with <code>ui.search_popovers = False</code>; its existing window and RNA regressions pass alongside pointer/decorator checks.</p>
<p><strong>Parity remains partial.</strong> These are actual implementation captures, not generated-reference approval. Exact theme/DPI/motion matching, non-ID pointer targets, ranking/icon variants and full focus traversal remain open. Blender 4.2 and non-macOS runtime validation remain open. CPU timing records describe this workload only, not source-equivalent speed or GPU completion latency.</p>
<p><a href="capture.json">5.2 capture and timings</a> · <a href="capture-51.json">5.1 capture and timings</a> · <a href="runtime-52.json">RNA behavior</a> · <a href="windowed-52.json">Actual window input</a> · <a href="../collection-search-v1/api-source-audit.json">Official source audit</a> · <a href="../../../SEARCH_PROPERTIES.md">Integration and remaining gaps</a> · <a href="../collection-search-v1/index.html">Previous full-card evidence</a></p>""")
print(OUT)
