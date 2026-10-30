"""Package checked production layout captures, comparisons and motion overview."""

import hashlib
import html
import json
import shutil
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/layout-sizing"
OUT = ROOT / "docs/design/qa/layout-sizing-v1"
OUT.mkdir(parents=True, exist_ok=True)
STATES = {
    "rest": "Relative widths, taller rows and fixed logical-unit slots",
    "wide": "Wide host bounds preserve normal fonts and compound aspect",
    "narrow": "Narrow host width; unchanged font scale",
    "resized": "Live height and fixed-width changes",
    "aligned": "Right alignment using intrinsic widths",
    "owner-menu": "Right-click a sized control",
    "disabled": "Motion disabled; shared glass retained",
}


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(data, fixture, source=ROOT):
    assert data["passed"] and data["stable_resources"]
    assert data["fixture_sha256"] == sha(ROOT / "tests" / fixture)
    for name, digest in data["source_sha256"].items():
        assert sha(source / name) == digest, name


comparisons = []
for suffix in ("", "-51"):
    for dpi in ("1", "1.5", "2"):
        folder = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        data = read(BUILD / folder / "capture.json")
        verify(data, "capture_sizing.py")
        assert data["fixture_helper_sha256"] == sha(ROOT / "tests/sizing_fixture.py")
        assert data["native_text_batching_equal_frames"] == 60
        assert data["retained_resources"]["productions"] == 1
        assert data["retained_resources"]["blur"] == 1
        for name in STATES:
            shutil.copy2(
                BUILD / folder / (name + ".png"),
                OUT / (name + suffix + "-" + dpi + "x.png"),
            )
        shutil.copy2(
            BUILD / folder / "frame-022.png",
            OUT / ("motion" + suffix + "-" + dpi + "x.png"),
        )
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
    for label in (
        "runtime",
        "windowed",
        "operators",
        "general",
        "flow",
        "lists",
        "default-lists",
        "menus",
        "popovers",
        "pointer",
        "id-templates",
        "context",
    ):
        folder = label + suffix
        assert all(r["passed"] for r in read(BUILD / folder / "summary.json"))
        for name, extension in (("result-0.json", ".json"), ("blender-0.log", ".log")):
            shutil.copy2(BUILD / folder / name, OUT / (folder + extension))
    for workload, fixture, states in (
        ("benchmark", "benchmark_operator_enums.py", ("rest", "scalar")),
        ("dense", "benchmark_flow_dense.py", ("rest", "scalar", "scrolled")),
    ):
        for revision in ("before", "after"):
            folder = workload + "-" + revision + suffix
            source = BUILD / "baseline" if revision == "before" else ROOT
            data = read(BUILD / folder / "capture.json")
            verify(data, fixture, source)
            assert Path(data["loaded_package"]).parent == source / "beyond_ui"
            shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
            shutil.copy2(
                BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
            )
            for name in states:
                shutil.copy2(
                    BUILD / folder / (name + ".png"),
                    OUT / (folder + "-" + name + ".png"),
                )
        for name in states:
            a = Image.open(
                OUT / (workload + "-before" + suffix + "-" + name + ".png")
            ).convert("RGB")
            b = Image.open(
                OUT / (workload + "-after" + suffix + "-" + name + ".png")
            ).convert("RGB")
            equal = ImageChops.difference(a, b).getbbox() is None
            assert equal, (workload, suffix, name)
            comparisons.append(
                dict(
                    runtime="5.1.2" if suffix else "5.2.2",
                    workload=workload,
                    state=name,
                    rgb_equal=equal,
                )
            )
layout_timings = []
for suffix in ("", "-51"):
    for revision in ("before", "after"):
        folder = "layout-" + revision + suffix
        data = read(BUILD / folder / "result-0.json")
        assert data["passed"]
        assert data["fixture_sha256"] == sha(ROOT / "tests/benchmark_sizing_layout.py")
        source = BUILD / "baseline" if revision == "before" else ROOT
        for path, digest in data["source_sha256"].items():
            assert sha(source / path) == digest
        shutil.copy2(BUILD / folder / "result-0.json", OUT / (folder + ".json"))
        shutil.copy2(BUILD / folder / "blender-0.log", OUT / (folder + ".log"))
        layout_timings.append(
            dict(runtime=data["version"], revision=revision, timings=data["timings"])
        )

focus = read(ROOT / "build/focus-audit/final-qa-focus.json")
assert focus["child_exit"] == 0
observed = set(focus["sampled_frontmost_pids"]) | {
    event["pid"] for event in focus["events"]
}
launches = []
for path in sorted(BUILD.glob("*/summary.json")):
    for record in read(path):
        assert record["passed"] and record["pid"] not in observed, path
        command = record["command"]
        assert "--background" in command or "--no-window-focus" in command, path
        launches.append(
            dict(label=path.parent.name, pid=record["pid"], policy=record["focus_policy"])
        )
assert len(launches) == 42
focus["events"] = [
    {key: value for key, value in event.items() if key != "bundle"}
    for event in focus["events"]
]
(OUT / "focus.json").write_text(
    json.dumps(dict(passed=True, monitor=focus, launches=launches), indent=2) + "\n"
)

frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 60
media = ROOT / "docs/media/panels/layout-sizing-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=[30, 30, 40] * 20,
    loop=0,
    optimize=False,
    disposal=2,
)
with Image.open(media) as gif:
    duration = 0
    for i in range(gif.n_frames):
        gif.seek(i)
        duration += gif.info["duration"]
    assert duration == 2000
media.with_suffix(".json").write_text(
    json.dumps(
        dict(
            source="Actual production Blender frames; no generated pixels",
            capture="../../design/qa/layout-sizing-v1/capture.json",
            sha256=sha(media),
            source_frames=60,
            duration_ms=duration,
        ),
        indent=2,
    )
    + "\n"
)
audit = []
for revision in ("v4.2.0", "ec6e62d40fa9", "d13f752e3b9c"):
    for relative, folder in (
        ("source/blender/editors/interface/interface_layout.cc", "prop-pointer/source"),
        ("source/blender/makesrna/intern/rna_ui.cc", "registered-lists-source"),
    ):
        path = ROOT / "build" / folder / revision / Path(relative).name
        audit.append(
            dict(
                url=f"https://raw.githubusercontent.com/blender/blender/{revision}/{relative}",
                sha256=sha(path),
            )
        )
(OUT / "source-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
comparison = dict(
    exact_match=False,
    reference_acceptance="Open; existing BVT controls reused. Tyler owns visual QA.",
    baseline="d3d6565",
    unchanged_shared_renderer=comparisons,
    scale_factors=[1, 1.5, 2],
    batching_equal_frames=360,
    layout_timings=layout_timings,
    remaining="82 API members unimplemented; 55 partial; no reference-matched members",
)
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
options = "".join(
    f'<option value="{k}">{html.escape(v)}</option>' for k, v in STATES.items()
)
page = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retained layout QA</title><style>
body{background:#191b20;color:#e8e9ec;font:15px system-ui;margin:32px auto;max-width:1420px;padding:0 24px}h1{font-size:28px}p{max-width:1000px;line-height:1.6}select{background:#292c34;color:inherit;border:1px solid #666;padding:9px;margin:6px}a{color:#a6caff}.compare{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:12px 0}img{max-width:100%;height:auto;border:1px solid #3f444f}figcaption{padding:10px}small{color:#b6bac7}@media(max-width:800px){.compare{grid-template-columns:1fr}}</style></head><body>
<h1>Explicit layout scales and fixed units</h1>
<p>Actual production Blender rendering, shared BVT glass and springs. Controls retain their logical font sizes as layouts change width. Compare the two installed runtimes; exact generated-reference acceptance remains open. These captures are for Tyler’s visual QA.</p>
<p><a href="../../../LAYOUT_SIZING.md">Behavior and limits</a> · <a href="comparison.json">Comparison record</a> · <a href="source-audit.json">Official source audit</a> · <a href="../../../CUSTOM_PARITY.json">Full parity ledger</a></p>
<label>State <select id="state">OPTIONS</select></label><label>UI scale <select id="dpi"><option>1</option><option>1.5</option><option>2</option></select></label>
<div class="compare"><figure><img id="a"><figcaption>Blender 5.2.2</figcaption></figure><figure><img id="b"><figcaption>Blender 5.1.2</figcaption></figure></div>
<h2>Source motion and owner menu</h2><img src="../../../media/panels/layout-sizing-v1.gif" alt="Actual Blender sized switch and right-click menu animation">
<p>360 motion frames across both versions and three scales compare identically with native text batching enabled and disabled. One shared backdrop, one strong blur and retained rendering resources. Raw captures and measurement records are linked below.</p>
<h2>Unchanged renderer: before / after</h2><div class="compare"><figure><img src="dense-before-scrolled.png"><figcaption>Published d3d6565 — 144 buttons, scrolled</figcaption></figure><figure><img src="dense-after-scrolled.png"><figcaption>Current — identical RGB pixels</figcaption></figure></div>
<p><a href="capture.json">5.2 layout measurement</a> · <a href="capture-51.json">5.1 layout measurement</a> · <a href="dense-before.json">Dense before</a> · <a href="dense-after.json">Dense after</a> · <a href="windowed.json">5.2 real mouse input</a> · <a href="windowed-51.json">5.1 real mouse input</a></p>
<p><strong>Parity remains incomplete:</strong> 82 API members unimplemented, 55 partial, zero reference-matched. The broader theme/platform matrix, native layout edge cases and specialized templates remain open. No native fallback is being counted as custom parity.</p>
<script>const state=document.querySelector('#state'),dpi=document.querySelector('#dpi');function update(){document.querySelector('#a').src=state.value+'-'+dpi.value+'x.png';document.querySelector('#b').src=state.value+'-51-'+dpi.value+'x.png'}state.onchange=dpi.onchange=update;update();</script></body></html>""".replace(
    "OPTIONS", options
)
(OUT / "index.html").write_text(page)
print(json.dumps(dict(qa=str(OUT), comparison=comparison), indent=2))

(OUT / "manifest.json").write_text(
    json.dumps(
        {
            str(p.relative_to(OUT)): sha(p)
            for p in sorted(OUT.iterdir())
            if p.is_file() and p.name != "manifest.json"
        },
        indent=2,
    )
    + "\n"
)
