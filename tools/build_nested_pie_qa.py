"""Package current nested-pie execution/capture evidence without claiming parity."""

import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu-v4"
OUT = ROOT / "docs/design/qa/marking-menu-v4"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "frames").mkdir(exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
focus = read(BUILD / "focus-release.json")
assert focus["child_exit"] == 0
observed = set(focus["sampled_frontmost_pids"]) | {e["pid"] for e in focus["events"]}
launches = []
for name in (
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
        assert data["fixture_sha256"] == sha(ROOT / "tests/capture_pie_nested.py")
        assert data["fixture_helper_sha256"] == sha(
            ROOT / "tests/pie_nested_fixture.py"
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
crop = (120, 260, 1000, 790)
images = []
frame_hashes = {}
for p in paths:
    with Image.open(p) as raw:
        img = raw.convert("RGB").crop(crop)
        img.save(OUT / "frames" / p.name)
        images.append(img)
    frame_hashes[p.name] = sha(p)
gif = MEDIA / "marking-menu-v4.gif"
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
shutil.copy2(BUILD / "focus-release.json", OUT / "focus.json")
(OUT / "launches.json").write_text(json.dumps(launches, indent=2) + "\n")
timings = read(capture / "capture.json")["timings"]
report = dict(
    execution_passed=True,
    exact_match=False,
    reference_acceptance="Pending Tyler QA",
    focus_passed=all(r["focus_passed"] for r in launches),
    native_batch_equal_frames=sum(
        r["result"].get("native_text_batching_equal_frames", 0) for r in launches
    ),
    remaining=[
        "Standalone Layout.menu_pie authoring",
        "Specialized controls and remaining layout flags in registered compound menus",
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
(MEDIA / "marking-menu-v4.json").write_text(
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
rows = "".join(
    "<tr><td>"
    + label
    + "</td>"
    + "".join(
        f'<td><a href="{key}-{state}.png">PNG</a></td>'
        for state in ("nested", "context", "narrow", "disabled")
    )
    + "</tr>"
    for key, label in (
        ("1x", "5.2.2 / 1×"),
        ("15x", "5.2.2 / 1.5×"),
        ("2x", "5.2.2 / 2×"),
        ("51", "5.1.2 / 1×"),
    )
)
perf = f"Nested compound CPU paint: median {timings['nested']['median_ms']:.3f} ms; p95 {timings['nested']['p95_ms']:.3f} ms. Paired ordinary-list medians: {timings['list-before']['median_ms']:.3f} ms baseline / {timings['list-after']['median_ms']:.3f} ms current."
(OUT / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond UI · Nested pie menus</title>
<style>body{margin:32px auto;padding:0 24px;max-width:1300px;font:15px/1.6 system-ui;background:#181b1e;color:#e8e9eb}h1{font-size:30px}h2{font-size:21px}a{color:#a9d7f6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,450px),1fr));gap:20px}figure{margin:0;background:#23272b;padding:12px;border-radius:10px}img{display:block;width:100%;height:auto}figcaption{padding:8px}.note{padding:16px;border-left:3px solid #dfa964;background:#2a251f}table{border-collapse:collapse}td,th{padding:8px 14px;border:1px solid #444}input{width:100%}.motion{max-width:880px}</style>
<h1>Nested pies and compound layouts</h1><p>Actual Blender GPU captures · 30 October 2026 · shared source glass, theme and spring motion.</p>
<p>Open a nested ring from a pie or ordinary menu. The child grows from the selection point, keeps exact property contexts, and returns through the center Back button, Left Arrow or Escape. Split, column-flow and grid-flow groups share the retained panel layout engine, with alignment, logical sizing, scaling, line/space separators and elastic row spacers.</p>
<p class="note">Implementation evidence for your QA; exact reference matching and full parity remain open. Every windowed launch used --no-window-focus, but the audit still recorded Blender activation. No deliberate activation or focus-restoration workaround was used.</p>
<figure class="motion"><img src="../../../media/panels/marking-menu-v4.gif" alt="Parent pie, nested compound ring, exact property context and Back"><figcaption>Parent → nested ring → liquid stretch → property context → Back → reopen.</figcaption></figure>
<h2>Scrub the actual PNG frames</h2><figure class="motion"><img id="frame" src="frames/frame-000.png" alt="Selected actual GPU frame"><input id="scrub" type="range" min="0" max="95" value="0" aria-label="Animation frame"><figcaption id="frame-label">Frame 0 / 95 · original capture colors, no resizing</figcaption></figure>
<script>const slider=document.getElementById('scrub');slider.addEventListener('input',()=>{document.getElementById('frame').src='frames/frame-'+String(slider.value).padStart(3,'0')+'.png';document.getElementById('frame-label').textContent='Frame '+slider.value+' / 95 · original capture colors, no resizing';});</script>
<h2>Parent and child</h2><div class="grid"><figure><a href="1x-parent.png"><img src="1x-parent.png"></a><figcaption>Parent ring at the opening point.</figcaption></figure><figure><a href="1x-nested.png"><img src="1x-nested.png"></a><figcaption>Nested compound ring with a separate center Back control.</figcaption></figure><figure><a href="1x-context.png"><img src="1x-context.png"></a><figcaption>Resolution's exact owner actions use the same menu/glass stack.</figcaption></figure><figure><a href="1x-narrow.png"><img src="1x-narrow.png"></a><figcaption>Small hosts retain a searchable custom list fallback and Back.</figcaption></figure></div>
<h2>Scale and motion policy</h2><table><tr><th>Blender / scale</th><th>Nested</th><th>Context</th><th>Narrow</th><th>Motion disabled</th></tr>"""
    + rows
    + """</table>
<h2>Verification</h2><p>Six background RNA/regression processes, four GPU fixtures and two native N-panel input fixtures passed. 144 animation frames matched byte-for-byte with native text batching on/off. Shared backdrop/strong-blur revisions and retained shader/batch/font resources stayed stable. Native N-panel tests exercise the narrow fallback; radial presentation is covered by the GPU fixtures.</p><p>"""
    + perf
    + """ These are CPU submission timings without readback, not GPU completion or full performance acceptance.</p>
<p><a href="report.json">Results and remaining gaps</a> · <a href="launches.json">Launches and source fingerprints</a> · <a href="focus.json">Focus audit</a> · <a href="trajectory.json">Navigation trajectory</a> · <a href="../../../MARKING_MENUS.md">Integration guide</a></p></html>"""
)
print(OUT)
