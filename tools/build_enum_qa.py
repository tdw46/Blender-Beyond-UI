"""Package actual enum captures and checked runtime evidence, preserving prior galleries."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/enum-properties"
OUT = ROOT / "docs/design/qa/enum-properties-v1"
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for suffix in ("", "-51"):
    for dpi in ("1", "1.5", "2"):
        folder = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        record = read(BUILD / folder / "capture.json")
        assert record["passed"] and record["stable_resources"]
        assert record["native_text_batching_equal_frames"] == 100
        assert record["fixture_sha256"] == sha(
            ROOT / "tests/capture_enum_properties.py"
        )
        for name, digest in record["source_sha256"].items():
            assert sha(ROOT / name) == digest, name
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
        # Retain raw static images for both runtimes, with motion at 1x in the README.
        for name in ("rest", "scalar", "flags", "long", "field-context", "disabled"):
            shutil.copy2(
                BUILD / folder / (name + ".png"),
                OUT / (name + suffix + "-" + dpi + "x.png"),
            )
    for label in (
        "runtime",
        "windowed",
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
        assert data["passed"] and data["stable_resources"]
        expected = ROOT if revision == "after" else BUILD / "baseline"
        assert Path(data["loaded_package"]).parent == expected / "beyond_ui"
        assert data["fixture_sha256"] == sha(
            ROOT / "tests/benchmark_enum_properties.py"
        )
        for name, digest in data["source_sha256"].items():
            base = ROOT if revision == "after" else BUILD / "baseline"
            assert sha(base / name) == digest
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
# Retain resting equality and the deliberate change to below-field menu anchoring.
comparison = {
    "exact_match": False,
    "baseline_commit": "44f055a12d71bccf62168fca2ddccbd708b978e2",
    "differences": "Resting controls are unchanged. Enum menus now anchor below the field; original shared shortcut menu anchored at the field top.",
    "pairs": {},
}
for name in ("rest", "scalar"):
    a, b = [
        BUILD / ("benchmark-" + rev) / (name + ".png") for rev in ("before", "after")
    ]
    same = (
        ImageChops.difference(
            Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        ).getbbox()
        is None
    )
    comparison["pairs"][name] = {
        "rgb_pixels_equal": same,
        "before_sha256": sha(a),
        "after_sha256": sha(b),
    }
    for path, rev in ((a, "before"), (b, "after")):
        shutil.copy2(path, OUT / ("benchmark-" + rev + "-" + name + ".png"))
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 100
media = ROOT / "docs/media/panels/enum-properties-v1.gif"
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
            "capture": "../../design/qa/enum-properties-v1/capture.json",
            "sha256": sha(media),
        },
        indent=2,
    )
    + "\n"
)
rows = "".join(
    f'<figure><figcaption>{title}</figcaption><a class="capture" data-name="{name}" href="{name}-1x.png"><img src="{name}-1x.png" alt="{title}"></a></figure>'
    for name, title in [
        ("rest", "Resting fields and expanded choices"),
        ("scalar", "Scalar enum menu"),
        ("flags", "Enum flags with current checks"),
        ("long", "Last item of 200 choices"),
        ("field-context", "Exact property right-click menu"),
        ("disabled", "Motion disabled; glass retained"),
    ]
)
(OUT / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Enum properties · QA v1</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}p{max-width:1050px;line-height:1.6}img{max-width:100%;height:auto;display:block}figure{margin:0}figcaption{padding:10px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,640px));gap:16px}select{font:inherit;padding:6px;background:#292c30;color:white;border:1px solid #777;border-radius:6px}h2{margin-top:36px}</style>
<h1>Enum properties: shared glass menus and safe choices</h1>
<p>Scalar enum clicks now open the same BVT strong-glass menu as shortcuts and context actions. Flag menus stay compact. Expanded choices and menu selections share rollback when a host commit fails. Dynamic choices refresh on opening and are rechecked at selection; stale choices and concurrent value changes are rejected.</p>
<img src="../../../media/panels/enum-properties-v1.gif" alt="Actual enum menu opening, flag selection, long-list scrolling and expanded-choice context menu motion">
<h2>Runtime and scale captures</h2>
<p>100 motion frames per scale on Blender 5.1.2 and 5.2.2 match with native text batching enabled/disabled (600 frames total). Images display at a constant logical width; click for raw pixels. Large menus paint only visible rows and keep ordinary field typography.</p>
<label for="dpi">Capture scale </label><select id="dpi"><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>
<div class="grid">"""
    + rows
    + """</div>
<h2>Equivalent short-menu benchmark · before / after</h2>
<div class="grid"><figure><img src="benchmark-before-scalar.png" alt="Prior shared short enum menu"><figcaption>Previous revision 44f055a · shared shortcut menu route</figcaption></figure><figure><img src="benchmark-after-scalar.png" alt="Current shared short enum menu"><figcaption>Current implementation · common mouse and shortcut route</figcaption></figure></div>
<p>Same three-choice scalar and three expanded buttons, 20 warmups and 100 CPU submission samples per workload. <a href="comparison.json">Pixel comparison</a> and <a href="benchmark-before.json">before</a>/<a href="benchmark-after.json">after timing records</a> are included. Resting pixels match; open-menu position intentionally moves below the field. These are process-level regression checks, not GPU latency or source-equivalent BVT speed claims.</p>
<p>Real window input verifies the 200th choice via End/Enter, current-choice reveal, exact property right-click routing, cancellation and quiescent teardown. One shared backdrop production, one blur, five offscreens and retained font/shader/batch identities stay stable through the capture sequence. No new generated artwork or visual approval is claimed.</p>
<p><strong>Parity remains partial.</strong> Native Shift/multi-toggle persistence, headings/separators, every icon variant, fuzzy popup search, specialized tab semantics, full focus traversal and broader theme/platform validation remain open. Blender 4.2 fallback is retained but not executed. Tyler owns visual QA.</p>
<p><a href="capture.json">5.2 captures and timings</a> · <a href="capture-51.json">5.1 captures and timings</a> · <a href="runtime-52.json">RNA cases</a> · <a href="windowed-52.json">Real window input</a> · <a href="../../../ENUM_PROPERTIES.md">Integration and exact remaining gaps</a></p>
<script>document.getElementById('dpi').addEventListener('change',event=>{for(const link of document.querySelectorAll('a.capture')){const path=`${link.dataset.name}-${event.target.value}x.png`;link.href=path;link.querySelector('img').src=path;}});</script></html>"""
)
print(OUT)
