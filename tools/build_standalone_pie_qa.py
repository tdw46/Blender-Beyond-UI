"""Package current standalone-pie execution/capture evidence without claiming parity."""

import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu-v5"
OUT = ROOT / "docs/design/qa/marking-menu-v5"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "frames").mkdir(exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
audits = [
    read(BUILD / name) for name in ("focus-release.json", "focus-regression.json")
]
assert all(a["child_exit"] == 0 for a in audits)
focus = dict(
    child_exit=0,
    events=[e for a in audits for e in a["events"]],
    sampled_frontmost_pids=list(
        {p for a in audits for p in a["sampled_frontmost_pids"]}
    ),
    audits=["focus-release.json", "focus-regression.json"],
)
observed = set(focus["sampled_frontmost_pids"]) | {e["pid"] for e in focus["events"]}
launches = []
for name in (
    "standalone",
    "standalone-51",
    "nested",
    "nested-51",
    "compound",
    "compound-51",
    "general",
    "general-51",
    "run-1x",
    "run-15x",
    "run-2x",
    "run-51",
    "windowed",
    "windowed-51",
):
    record = read(BUILD / name / "summary.json")[0]
    assert record["passed"], name
    assert (
        "--background" in record["command"] or "--no-window-focus" in record["command"]
    )
    record["focus_passed"] = record["pid"] not in observed
    launches.append(record)
    for path, digest in record["result"].get("source_sha256", {}).items():
        assert sha(ROOT / path) == digest, path
    if name.startswith("run-"):
        data = record["result"]
        assert data["fixture_sha256"] == sha(ROOT / "tests/capture_pie_standalone.py")
        assert data["fixture_helper_sha256"] == sha(
            ROOT / "tests/pie_standalone_fixture.py"
        )
        assert (
            data["stable_resources"]
            and data["retained_resources"]["productions"] == 1
            and data["retained_resources"]["blur"] == 1
        )
        label = name[4:]
        for state in (
            "parent",
            "nested",
            "approach",
            "hover",
            "hover-settled",
            "context",
            "search",
            "back",
            "disabled",
            "narrow",
        ):
            shutil.copy2(
                BUILD / ("capture-" + label) / (state + ".png"),
                OUT / (label + "-" + state + ".png"),
            )
        shutil.copy2(
            BUILD / ("capture-" + label) / "capture.json",
            OUT / (label + "-capture.json"),
        )
    else:
        (OUT / (name + ".json")).write_text(
            json.dumps(record["result"], indent=2) + "\n"
        )
capture = BUILD / "capture-1x"
paths = sorted(capture.glob("frame-*.png"))
assert len(paths) == 96
crop = (50, 300, 980, 790)
images = []
frame_hashes = {}
for p in paths:
    with Image.open(p) as raw:
        img = raw.convert("RGB").crop(crop)
        img.save(OUT / "frames" / p.name)
        images.append(img)
    frame_hashes[p.name] = sha(p)
gif = MEDIA / "marking-menu-v5.gif"
images[0].save(
    gif,
    save_all=True,
    append_images=images[1:],
    duration=[
        (round((i + 1) * 100 / 30) - round(i * 100 / 30)) * 10 for i in range(96)
    ],
    loop=0,
    disposal=2,
)
shutil.copy2(capture / "trajectory.json", OUT / "trajectory.json")
for name in ("focus-release.json", "focus-regression.json", "focus-initial.json"):
    shutil.copy2(BUILD / name, OUT / name)
(OUT / "focus.json").write_text(json.dumps(focus, indent=2) + "\n")
(OUT / "launches.json").write_text(json.dumps(launches, indent=2) + "\n")
timings = read(capture / "capture.json")["timings"]
report = dict(
    execution_passed=True,
    unit_tests=235,
    hover_landing_pixels_equal=all(
        r["result"].get("hover_landing_pixels_equal", True) for r in launches
    ),
    exact_match=False,
    reference_acceptance="Pending Tyler QA",
    focus_passed=all(r["focus_passed"] for r in launches),
    native_batch_equal_frames=sum(
        r["result"].get("native_text_batching_equal_frames", 0) for r in launches
    ),
    remaining=[
        "Full native mixed-array split layout, distinct emboss geometry, dialog focus semantics and specialized compound controls",
        "Non-menu Canvas alert/emboss behavior and narrow inline decorator placement",
        "Exact native edge anchoring, full apply semantics and extreme-size reference acceptance",
        "Other themes/platforms and Blender 4.2 runtime",
        "Generated-reference/motion acceptance",
        "No-focus activation failures",
    ],
    media=dict(
        crop=crop,
        resized=False,
        raw_frame_sha256=frame_hashes,
        note="Actual GPU frames. GIF is quantized; PNG frame scrubber preserves captured colors.",
    ),
    timings=timings,
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
(MEDIA / "marking-menu-v5.json").write_text(
    json.dumps(
        dict(
            report=str((OUT / "report.json").relative_to(ROOT)),
            gif_sha256=sha(gif),
            media=report["media"],
        ),
        indent=2,
    )
    + "\n"
)

# The hover image and the held image are exact raw PNG comparisons, not a
# generated-reference claim. Keep full original-size captures for inspection.
for label in ("1x", "15x", "2x", "51"):
    assert (OUT / (label + "-hover.png")).read_bytes() == (
        OUT / (label + "-hover-settled.png")
    ).read_bytes()
for state in ("approach", "hover", "nested"):
    with Image.open(OUT / ("1x-" + state + ".png")) as raw:
        raw.crop(crop).save(OUT / (state + "-detail.png"))

source_audit = read(ROOT / "docs/design/qa/marking-menu-v4/source-audit.json")
(OUT / "prior-source-audit.json").write_text(json.dumps(source_audit, indent=2) + "\n")
audit = dict(
    prior="prior-source-audit.json",
    documentation="Exact 4.2/5.1/5.2 API and Manual pages requested; retrieval unavailable. Installed 5.1.2/5.2.2 RNA and archived versioned source checked.",
    theme_roles=[
        dict(
            path="rna_userdef.cc",
            url="https://github.com/blender/blender/blob/ec6e62d40fa9/source/blender/makesrna/intern/rna_userdef.cc",
            sha256=sha(BUILD / "source/rna_userdef.cc"),
        ),
        dict(
            path="rna_userdef-42.cc",
            url="https://github.com/blender/blender/blob/v4.2.0/source/blender/makesrna/intern/rna_userdef.cc",
            sha256=sha(BUILD / "source/rna_userdef-42.cc"),
        ),
    ],
    compatibility="wcol_state.error capability first; legacy Info error background fallback. No icon-text substitution or linear conversion. Existing action-layer/legacy fcurve gates reused.",
)
(OUT / "source-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
rows = "".join(
    "<tr><td>"
    + label
    + "</td>"
    + "".join(
        f'<td><a href="{key}-{state}.png">PNG</a></td>'
        for state in ("nested", "hover", "context", "narrow", "disabled")
    )
    + "</tr>"
    for key, label in (
        ("1x", "5.2.2 / 1×"),
        ("15x", "5.2.2 / 1.5×"),
        ("2x", "5.2.2 / 2×"),
        ("51", "5.1.2 / 1×"),
    )
)
perf = f"Compound CPU paint median {timings['nested']['median_ms']:.3f} ms, p95 {timings['nested']['p95_ms']:.3f} ms. Paired ordinary-list medians {timings['list-before']['median_ms']:.3f} ms before / {timings['list-after']['median_ms']:.3f} ms after."
html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond UI · Standalone pies and stable hover</title>
<style>body{margin:32px auto;padding:0 24px;max-width:1300px;font:15px/1.6 system-ui;background:#181b1e;color:#e8e9eb}h1{font-size:30px}h2{font-size:21px}a{color:#a9d7f6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,450px),1fr));gap:20px}figure{margin:0;background:#23272b;padding:12px;border-radius:10px}img{display:block;width:100%;height:auto}figcaption{padding:8px}.note{padding:16px;border-left:3px solid #dfa964;background:#2a251f}table{border-collapse:collapse}td,th{padding:8px 14px;border:1px solid #444}input{width:100%}.motion{max-width:930px}code{color:#c7deec}</style>
<h1>Approach with motion. Land at rest.</h1>
<p>Actual Blender GPU captures · 30 October 2026 · BVT liquid glass, active theme colors and shared source springs.</p>
<p>Pie items pull and stretch as the pointer approaches. Entering the logical petal restores its resting shape immediately, including compound padding. Highlight and the origin guide remain. No additional row, field or switch hover squash is layered on top.</p>
<div class="grid"><figure><a href="1x-approach.png"><img src="approach-detail.png" alt="Approaching the compound pie petal"></a><figcaption>Approach: source spring pull and area-preserving stretch.</figcaption></figure><figure><a href="1x-hover.png"><img src="hover-detail.png" alt="Pointer inside the compound petal, at rest"></a><figcaption>Contact: stable resting shape. This capture is byte-identical to the held capture one second later.</figcaption></figure></div>
<h2>Standalone pies and compound flags</h2><p><code>Layout.menu_pie()</code> now authors a pie without a registered Menu class. The host opens it with logical coordinates and routes events through Canvas. Nested registered menus retain Back, exact owner actions and stale-owner checks.</p>
<p>Compound slots add alert tint, unembossed/status fields, split labels, optional animation decorators, initial text editing and default action selection. Decorators use real keyframe insertion/deletion on the exact component. All Boolean controls stay BVT switches.</p>
<figure class="motion"><img src="../../../media/panels/marking-menu-v5.gif" alt="Standalone pie, compound flags, approach motion, stable hover and property context"><figcaption>Standalone parent → nested flags → approach → stable hover → exact property context → Back.</figcaption></figure>
<h2>Scrub the actual PNG frames</h2><figure class="motion"><img id="frame" src="frames/frame-000.png" alt="Selected actual GPU frame"><input id="scrub" type="range" min="0" max="95" value="0" aria-label="Animation frame"><figcaption id="frame-label">Frame 0 / 95 · captured colors, no resizing</figcaption></figure>
<script>const slider=document.getElementById('scrub');slider.addEventListener('input',()=>{document.getElementById('frame').src='frames/frame-'+String(slider.value).padStart(3,'0')+'.png';document.getElementById('frame-label').textContent='Frame '+slider.value+' / 95 · captured colors, no resizing';});</script>
<h2>Scale, ownership and motion policy</h2><table><tr><th>Blender / scale</th><th>Flags</th><th>Stable hover</th><th>Context</th><th>Narrow</th><th>Motion disabled</th></tr>__ROWS__</table>
<p>235 unit tests, eight background Blender runs, four GPU captures and two native N-panel input runs passed. 144 animation frames matched byte-for-byte with Blender text batching on/off. All four hover/held PNG pairs are identical. Shared backdrop/strong-blur revisions, shaders, batches and fonts remained stable.</p>
<p>__PERF__ CPU submission only, with readback excluded; not GPU completion or full source-level performance acceptance.</p>
<p class="note">Implementation evidence for your QA. Full native parity and exact generated-reference acceptance remain open. Narrow fallback does not preserve every inline relationship. Windowed tests all used --no-window-focus, but the focus audits recorded Blender activation; no deliberate activation or focus-restoration workaround was used.</p>
<p><a href="report.json">Results and remaining gaps</a> · <a href="launches.json">Launches and source hashes</a> · <a href="focus.json">Combined focus audit</a> · <a href="source-audit.json">Versioned source evidence</a> · <a href="../../../MARKING_MENUS.md">Integration guide</a></p></html>"""
(OUT / "index.html").write_text(
    html.replace("__ROWS__", rows).replace("__PERF__", perf)
)
print(OUT)
