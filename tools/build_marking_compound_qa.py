"""Package execution-only evidence; never present old images as new visual proof."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu"
OUT = ROOT / "docs/design/qa/marking-menu-v2"
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text())


results = []
launches = []
for suffix in ("", "-51"):
    for label in ("runtime", "compound", "general"):
        summary = read(BUILD / (label + suffix) / "summary.json")
        assert all(r["passed"] and "--background" in r["command"] for r in summary)
        launches.extend(summary)
    data = read(BUILD / ("compound" + suffix) / "result-0.json")
    for name, digest in data["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert data["visual_verified"] is False
    shutil.copy2(
        BUILD / ("compound" + suffix) / "result-0.json",
        OUT / ("runtime" + suffix + ".json"),
    )
    results.append(data)
focus = read(BUILD / "focus-compound.json")
test_pids = {r["pid"] for r in launches}
assert focus["child_exit"] == 0
assert not test_pids.intersection(focus["sampled_frontmost_pids"])
assert not test_pids.intersection(e["pid"] for e in focus["events"])
shutil.copy2(BUILD / "focus-compound.json", OUT / "focus.json")
(OUT / "launches.json").write_text(json.dumps(launches, indent=2) + "\n")
report = dict(
    passed=True,
    visual_verified=False,
    exact_match=False,
    windowed_tests="blocked",
    background_focus_passed=True,
    checks=results[0]["checks"],
    runtimes=[
        dict(
            version=r["version"],
            event_timings=r["event_timings"],
            preferences=r["preferences"],
        )
        for r in results
    ],
    remaining=[
        "Full compound layout API/sizing semantics",
        "Nested radial definitions",
        "Native circular placement and edge equivalence",
        "Full native button-type apply behavior",
        "Additional runtime/platform/scale/theme coverage",
        "GPU resource and warm-render comparison for new effects",
        "Generated-reference and visual/motion acceptance",
    ],
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
checks = "".join("<li>" + s + "</li>" for s in report["checks"])
(OUT / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>Beyond UI · Compound pie execution</title>
<style>body{font:16px system-ui;line-height:1.6;background:#181b1e;color:#e5e8ea;margin:40px;max-width:1000px}a{color:#9dd9f3}.note{border-left:3px solid #dfac68;padding:14px;background:#29251e}h1{font-size:27px}li{margin:12px 0}</style>
<h1>Compound pie slots, timing and liquid motion</h1>
<p>Implemented: nested rows/columns/boxes, exact child property/actions/context menus, preference-based tap/hold/recenter/confirmation, growth from the opening pointer, spring-driven surface tension, proximity highlight and an origin guide.</p>
<p class="note">Execution evidence only. Windowed tests remain blocked after the confirmed focus steal. No new Blender screenshot/GIF, generated-reference match or visual acceptance is claimed. The v1 gallery depicts the previous implementation.</p>
<h2>Passed in background on Blender 5.1.2 and 5.2.2</h2><ul>"""
    + checks
    + """</ul>
<p>All six regression processes ran with --background. The focus audit observed no owned Blender PID becoming active. Event timings measure CPU input work only, not GPU rendering.</p>
<p><a href="report.json">Results and remaining gaps</a> · <a href="focus.json">Focus audit</a> · <a href="../../../MARKING_MENUS.md">Integration guide</a> · <a href="../marking-menu-v1/index.html">Historical v1 capture</a></p>"""
)
print(OUT)
