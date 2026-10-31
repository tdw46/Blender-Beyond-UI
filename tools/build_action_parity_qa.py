"""Publish verified action/component evidence; visual acceptance stays explicit."""

import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/action-parity-v1"
OUT = ROOT / "docs/design/qa/action-parity-v1"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
focus = read(BUILD / "focus.json")
assert focus["child_exit"] == 0
observed = set(focus["sampled_frontmost_pids"])
launches = []
for label in (
    "actions",
    "popup",
    "standalone",
    "general",
    "actions-51",
    "popup-51",
    "standalone-51",
    "general-51",
    "run-1x",
    "run-15x",
    "run-2x",
    "run-51",
):
    record = read(BUILD / label / "summary.json")[0]
    assert record["passed"], label
    assert (
        "--background" in record["command"] or "--no-window-focus" in record["command"]
    )
    record["focus_passed"] = record["pid"] not in observed
    launches.append(record)
    if label.startswith("run-"):
        data = record["result"]
        assert data["stable_resources"]
        assert (
            data["retained_resources"]["productions"]
            == data["retained_resources"]["blur"]
            == 1
        )
        for path, digest in data["source_sha256"].items():
            assert sha(ROOT / path) == digest, path
        assert sha(ROOT / "tests/capture_action_parity.py") == data["fixture_sha256"]
        assert (
            sha(ROOT / "tests/action_parity_fixture.py")
            == data["fixture_helper_sha256"]
        )
        scale = label[4:]
        capture = BUILD / ("capture-" + scale)
        for frame in range(60):
            assert (capture / f"frame-{frame:03}.png").read_bytes() == (
                capture / f"batch-{frame:03}.png"
            ).read_bytes()
        for state in (
            "rest",
            "keyed",
            "changed",
            "hold-menu",
            "hold-context",
            "popover",
            "cancel-context",
            "components",
            "component-enums",
            "component-filtered",
            "narrow",
            "disabled",
        ):
            shutil.copy2(
                capture / (state + ".png"), OUT / (scale + "-" + state + ".png")
            )
        shutil.copy2(capture / "capture.json", OUT / (scale + "-capture.json"))
    else:
        (OUT / (label + ".json")).write_text(
            json.dumps(record["result"], indent=2) + "\n"
        )
performance = read(BUILD / "paired-run/summary.json")[0]
assert performance["passed"] and performance["result"]["stable_resources"]
for path in ("beyond_ui/gpu/paint.py", "beyond_ui/canvas.py"):
    assert sha(ROOT / path) == performance["result"]["source_sha256"][path]
# The paired workload uses ordinary Canvas buttons and menus, not component
# popups. Verify the exact measured painter/culling source independently.
performance_focus = read(BUILD / "focus-performance.json")
assert performance_focus["child_exit"] == 0
performance["focus_passed"] = (
    performance["pid"] not in performance_focus["sampled_frontmost_pids"]
)
launches.append(performance)
(OUT / "paired-performance.json").write_text(json.dumps(performance, indent=2) + "\n")
(OUT / "focus-performance.json").write_text(
    json.dumps(performance_focus, indent=2) + "\n"
)
frames = []
frame_hashes = {}
(OUT / "frames").mkdir(exist_ok=True)
for path in sorted((BUILD / "capture-1x").glob("frame-*.png")):
    frame_hashes[path.name] = sha(path)
    shutil.copy2(path, OUT / "frames" / path.name)
    with Image.open(path) as image:
        frames.append(image.convert("RGB"))
assert len(frames) == 60
frames[0].save(
    MEDIA / "action-parity-v1.gif",
    save_all=True,
    append_images=frames[1:],
    duration=1000 / 30,
    loop=0,
    optimize=False,
)
report = dict(
    exact_match=False,
    full_custom_parity=False,
    execution_passed=True,
    launches=len(launches),
    native_text_batching_equal_frames=240,
    focus_passed=all(r["focus_passed"] for r in launches),
    focus_failures=[r["pid"] for r in launches if not r["focus_passed"]],
    limitations=[
        "Generated-reference equality and broader theme/platform acceptance remain open.",
        "Blender 4.2 source path is preserved; no installed 4.2 execution evidence.",
        "CPU paint submission timings are not end-to-end GPU latency or source-level performance parity.",
        "No-focus launch authorization remains distinct from focus safety; activation was observed.",
    ],
    frame_sha256=frame_hashes,
    source_sha256=launches[-2]["result"]["source_sha256"],
)
for name, data in (
    ("report.json", report),
    ("launches.json", launches),
    ("focus.json", focus),
):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")
(MEDIA / "action-parity-v1.json").write_text(
    json.dumps(
        dict(
            source="Actual Blender GPU frames",
            sha256=sha(MEDIA / "action-parity-v1.gif"),
            frames=frame_hashes,
            exact_match=False,
        ),
        indent=2,
    )
    + "\n"
)
sections = []
for title, states in (
    ("Presentation states", ("rest", "keyed", "changed")),
    (
        "Hold and confirmation",
        ("hold-menu", "hold-context", "popover", "cancel-context"),
    ),
    (
        "Persistent component editors",
        ("components", "component-enums", "component-filtered"),
    ),
    ("Narrow host and disabled animation", ("narrow", "disabled")),
):
    figures = "".join(
        f'<figure><figcaption>{s}</figcaption><img loading="lazy" src="1x-{s}.png" data-state="{s}" alt="Blender {s}"></figure>'
        for s in states
    )
    sections.append(f'<h2>{title}</h2><div class="grid">{figures}</div>')
html = (
    """<!doctype html><meta charset="utf-8"><title>Beyond UI · Action and component parity</title>
<style>body{background:#17191d;color:#e8e9ec;font:16px system-ui;margin:32px}h1{font-size:26px}h2{font-size:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:16px}figure{margin:0}img{max-width:100%;height:auto;border-radius:8px}figcaption{padding:10px}a{color:#9ccaff}select{padding:8px}p{max-width:1000px;line-height:1.5}</style>
<h1>Action and component parity · v1</h1>
<p>Actual Blender production renderer: hold menus, popup confirmation, shortcut display, persistent component editors and field status. Shared glass, active-theme colors and source motion. These are execution captures, not generated references; exact-match acceptance remains open.</p>
<p>13 passing Blender processes including the paired performance probe; 240 pixel-identical text batching pairs; retained backdrop/blur resources. All five windowed launches activated Blender despite --no-window-focus. No deliberate focus action was used.</p>
<label>Capture scale <select id="scale"><option value="1x">5.2.2 · 1×</option><option value="15x">5.2.2 · 1.5×</option><option value="2x">5.2.2 · 2×</option><option value="51">5.1.2 · 1×</option></select></label>
<p><a href="report.json">Acceptance and source hashes</a> · <a href="launches.json">Runtime records</a> · <a href="focus.json">Focus audit</a> · <a href="paired-performance.json">Paired performance</a> · <a href="focus-performance.json">Performance focus audit</a></p>
<img src="../../../media/panels/action-parity-v1.gif" alt="Actual held-menu and confirmation animation">
"""
    + "".join(sections)
    + """<script>document.querySelector('#scale').onchange=e=>document.querySelectorAll('img[data-state]').forEach(i=>i.src=e.target.value+'-'+i.dataset.state+'.png')</script>"""
)
(OUT / "index.html").write_text(html)
print(
    json.dumps(
        {k: v for k, v in report.items() if k not in {"frame_sha256", "source_sha256"}},
        indent=2,
    )
)
