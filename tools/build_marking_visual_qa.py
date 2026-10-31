"""Publish current GPU evidence with source fingerprints and honest focus results."""
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu-v3"
RUNS = ROOT / "build/marking-menu"
OUT = ROOT / "docs/design/qa/marking-menu-v3"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
MEDIA.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
focus = read(BUILD / "focus-windowed.json")
observed = set(focus["sampled_frontmost_pids"]) | {e["pid"] for e in focus["events"]}
launches = []
for name in ("capture-1x", "capture-15x", "capture-2x", "capture-51", "windowed", "windowed-51"):
    run = read(RUNS / name / "summary.json")[0]
    assert run["passed"] and "--no-window-focus" in run["command"], name
    run["focus_passed"] = run["pid"] not in observed
    launches.append(run)
    if name.startswith("capture"):
        result = run["result"]
        assert result["fixture_sha256"] == sha(ROOT / "tests/capture_pie_compound.py")
        for path, digest in result["source_sha256"].items():
            assert sha(ROOT / path) == digest, path
        assert result["stable_resources"]
        assert result["retained_resources"]["productions"] == 1
        assert result["retained_resources"]["blur"] == 1
        shutil.copy2(BUILD / name / "capture.json", OUT / (name + ".json"))
        for state in ("simple-near", "compound-near", "narrow", "disabled"):
            shutil.copy2(BUILD / name / (state + ".png"), OUT / (name + "-" + state + ".png"))
    else:
        (OUT / (name + ".json")).write_text(json.dumps(run["result"], indent=2)+"\n")
for name in ("runtime", "compound", "general", "runtime-51", "compound-51", "general-51"):
    run = read(RUNS / name / "summary.json")[0]
    assert run["passed"] and "--background" in run["command"]
    launches.append(run)

capture = BUILD / "capture-1x"
crop = (280, 240, 960, 790)
frames = {}
for mode in ("simple", "compound"):
    paths = sorted(capture.glob(mode + "-frame-*.png"))
    assert len(paths) == 60
    frames[mode] = {p.name:sha(p) for p in paths}
    imgs = [Image.open(p).convert("RGB").crop(crop) for p in paths]
    dest = MEDIA / ("marking-menu-v3-" + mode + ".gif")
    imgs[0].save(dest, save_all=True, append_images=imgs[1:], duration=[(round((i+1)*100/30)-round(i*100/30))*10 for i in range(len(imgs))], loop=0, disposal=2)
    for state in ("far", "near", "settled"):
        Image.open(capture / (mode + "-" + state + ".png")).crop(crop).save(OUT / (mode + "-" + state + ".png"))
for state in ("compound-context", "nested-search", "numeric-edit", "pie"):
    shutil.copy2(capture / (state + ".png"), OUT / (state + ".png"))
shutil.copy2(capture / "trajectory.json", OUT / "trajectory.json")
shutil.copy2(BUILD / "focus-windowed.json", OUT / "focus-windowed.json")
shutil.copy2(ROOT / "build/marking-menu-v3-focus-1x.json", OUT / "focus-initial.json")
report = dict(
    execution_passed=True, exact_match=False, visual_acceptance="Pending Tyler review",
    focus_passed=all(r.get("focus_passed", True) for r in launches),
    native_batch_identical_frames=sum(r["result"].get("native_text_batching_equal_frames",0) for r in launches),
    media=dict(crop=list(crop), resizing=False, gif_note="Actual Blender GPU frames; GIF palette quantization is preview-only. PNGs are authoritative.", raw_frame_sha256=frames),
    remaining=["Generated-reference match and motion acceptance", "Nested radial definitions and remaining compound layout methods", "Exact native edge anchoring and button-type apply behavior", "Blender 4.2 runtime, other platforms and custom themes", "Focus safety: several no-focus launches activated Blender", "Performance acceptance: CPU submission measured, not GPU completion; 1.5x paired-list p95 outlier retained"],
)
(OUT / "report.json").write_text(json.dumps(report, indent=2)+"\n")
(OUT / "launches.json").write_text(json.dumps(launches, indent=2)+"\n")
(MEDIA / "marking-menu-v3.json").write_text(json.dumps(dict(report= str((OUT / "report.json").relative_to(ROOT)), frames=frames), indent=2)+"\n")
(OUT / "index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond UI · Liquid pie menus</title>
<style>body{margin:32px auto;padding:0 24px;max-width:1450px;font:15px/1.6 system-ui;background:#181b1e;color:#e8e9eb}h1{font-size:30px}h2{font-size:21px}a{color:#a9d7f6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,500px),1fr));gap:20px}figure{margin:0;background:#23272b;padding:12px;border-radius:10px}img{display:block;width:100%;height:auto}figcaption{padding:8px}.note{padding:16px;border-left:3px solid #dfa964;background:#2a251f}summary{cursor:pointer}table{border-collapse:collapse}td,th{padding:8px 14px;border:1px solid #444}</style>
<h1>Liquid pie menus</h1><p>Actual Blender GPU captures · 30 October 2026 · source glass, theme and spring motion.</p>
<p>The pie grows from its opening point. Moving toward a slot pulls and stretches its surface; proximity strengthens its highlight and the guide line. Natural field widths and circular spacing keep labels readable and slots apart. Hit targets remain stable.</p>
<p class="note">Rendering and interaction checks passed. Focus safety did not: some launches activated Blender despite <code>--no-window-focus</code>. No app activation or focus-restoration commands were used. These are implementation captures for your QA, not generated references or a claim of exact parity.</p>
<div class="grid"><figure><img src="../../../media/panels/marking-menu-v3-simple.gif"><figcaption>Simple pie: grow → approach → pull/highlight → return.</figcaption></figure><figure><img src="../../../media/panels/marking-menu-v3-compound.gif"><figcaption>Compound pie: the glass, title, buttons, switch and field move together.</figcaption></figure></div>
<h2>Proximity comparison</h2><div class="grid"><figure><img src="simple-far.png"><figcaption>Farther away: weaker highlight and guide.</figcaption></figure><figure><img src="simple-near.png"><figcaption>Closer: stronger highlight, guide and surface pull.</figcaption></figure><figure><img src="compound-far.png"><figcaption>Approaching a compound slot.</figcaption></figure><figure><img src="compound-near.png"><figcaption>Compound surface tension with exact child targeting.</figcaption></figure></div>
<h2>Exact property context</h2><a href="compound-context.png"><img src="compound-context.png" alt="Compound pie and Resolution right-click actions"></a>
<h2>Scale and fallback captures</h2><p>Open full-resolution PNGs; compare logical text size, not expanded image width.</p><table><tr><th>Blender / UI scale</th><th>Simple pie</th><th>Compound</th><th>Narrow fallback</th><th>Motion disabled</th></tr>'''+''.join(f'<tr><td>{label}</td>'+''.join(f'<td><a href="{key}-{state}.png">PNG</a></td>' for state in ("simple-near","compound-near","narrow","disabled"))+'</tr>' for key,label in (("capture-1x","5.2.2 / 1×"),("capture-15x","5.2.2 / 1.5×"),("capture-2x","5.2.2 / 2×"),("capture-51","5.1.2 / 1×")))+'''</table>
<h2>Verification</h2><p>Four GPU fixtures, two native N-panel input fixtures and six background regression processes passed. 192 animation frames were byte-identical with native text batching on/off. Each fixture retained one shared backdrop/strong-blur revision and stable shader/batch/font resources.</p><p>1× warm CPU paint medians: simple pie 0.211 ms, compound 0.197 ms; p95 0.248/0.229 ms. Paired ordinary-list medians: 0.140 ms baseline, 0.144 ms current. These measure CPU submission, not GPU completion or end-to-end latency. The 1.5× paired-list p95 outlier (0.474 ms) remains visible in the raw report; performance acceptance is not claimed.</p>
<p><a href="report.json">Results and open gaps</a> · <a href="launches.json">All launch/runtime/source records</a> · <a href="focus-windowed.json">Focus audit</a> · <a href="trajectory.json">Pointer/motion trajectory</a> · <a href="../../../MARKING_MENUS.md">Integration</a></p></html>''')
print(OUT)
