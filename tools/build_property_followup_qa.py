"""Package numeric v2 and event v1 evidence; preserve all earlier galleries."""

from pathlib import Path
import hashlib, json, shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(base, version, fixture):
    source = ROOT / "build" / base / "capture"
    out = ROOT / "docs/design/qa" / version
    out.mkdir(parents=True, exist_ok=True)
    record = json.loads((source / "capture.json").read_text())
    assert record["passed"] and record["stable_resources"]
    for name, digest in record["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    assert record["fixture_sha256"] == sha(ROOT / "tests" / fixture)
    for p in source.glob("*.png"):
        if not p.name.startswith("frame-"):
            shutil.copy2(p, out / p.name)
    shutil.copy2(source / "capture.json", out / "capture.json")
    shutil.copy2(
        ROOT / "build" / base / "capture-run/blender-0.log", out / "capture.log"
    )
    frames = [Image.open(p).convert("RGBA") for p in sorted(source.glob("frame-*.png"))]
    media = ROOT / "docs/media/panels" / f"{version}.gif"
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
            dict(
                source="Actual production Blender frames; no generated pixels",
                capture=f"../../design/qa/{version}/capture.json",
                sha256=sha(media),
            ),
            indent=2,
        )
        + "\n"
    )
    return out, record, frames


numeric, record, frames = package(
    "prop-numeric-v2", "numeric-props-v2", "capture_numeric.py"
)
old = ROOT / "docs/design/qa/numeric-props-v1"
assert (
    Image.open(old / "units.png").tobytes()
    == Image.open(numeric / "units.png").tobytes()
)
old_record = json.loads((old / "capture.json").read_text())
paired = []
for i, frame in enumerate(frames):
    prior = Image.open(
        ROOT / "build/prop-numeric/capture" / f"frame-{i:03}.png"
    ).convert("RGBA")
    # Confirm the historical source frames against the immutable v1 raw capture hashes.
    assert (
        hashlib.sha256(
            prior.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
        ).hexdigest()
        == old_record["hashes"][f"frame-{i:03}"]
    )
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(prior, (0, 32))
    board.paste(frame, (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((12, 10), "Before: 100% amplitude", fill="white")
    draw.text((672, 10), "Now: 15% amplitude; identical spring timing", fill="white")
    paired.append(board)
paired[0].save(
    numeric / "motion-comparison.gif",
    save_all=True,
    append_images=paired[1:],
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
(numeric / "comparison.json").write_text(
    json.dumps(
        dict(
            resting_pixels_equal_v1=True,
            old_capture="../numeric-props-v1/capture.json",
            new_capture="capture.json",
            historical_frames_verified=True,
            motion_comparison_sha256=sha(numeric / "motion-comparison.gif"),
            amplitude_multiplier=0.15,
            exact_reference_acceptance=False,
        ),
        indent=2,
    )
    + "\n"
)
events, _, _ = package("prop-events", "event-props-v1", "capture_event_fields.py")
shutil.copy2(
    ROOT / "build/prop-events/source/audit.json", events / "api-source-audit.json"
)
for folder in [
    "runtime",
    "numeric",
    "regression",
    "menus",
    "windowed",
    "menu-windowed",
]:
    for i, v in enumerate(["52", "51"]):
        base = ROOT / "build/prop-events" / folder
        p = base / f"result-{i}.json"
        assert json.loads(p.read_text())["passed"]
        shutil.copy2(p, events / f"{folder}-{v}.json")
        shutil.copy2(base / f"blender-{i}.log", events / f"{folder}-{v}.log")
style = "<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}</style>"
(numeric / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>Numeric motion · 15%</title>'
    + style
    + """<h1>Wide numeric motion · QA v2</h1><p>The same recorded input, dimensions, theme and backdrop. Wide fields now multiply the resolved animation amplitude by 0.15; spring timing and logical hit targets are unchanged. Compact fields and menu animations keep their current strength.</p><img src="motion-comparison.gif"><p>Resting pixels are byte-identical to v1. Both recordings are actual Blender frames; this is an implementation comparison, not generated-reference approval.</p><h2>Current field motion</h2><img src="../../../media/panels/numeric-props-v2.gif"><p>One shared capture and strong blur, five retained offscreens; no extra capture or layout rebuild during animation. Settled and disabled pixels equal rest.</p><p><a href="capture.json">Timing/resources/source hashes</a> · <a href="comparison.json">Comparison checks</a> · <a href="../event-props-v1/index.html">Next property support: event fields</a> · <a href="../context-menu-v6/index.html">Every menu option follows the bounce</a></p>"""
)
(events / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>Event properties · QA v1</title>'
    + style
    + """<h1>Custom event properties · QA v1</h1><p>Actual Blender 5.2.2 Metal frames using the existing BVT field/menu skin, shared liquid glass, theme roles and finite springs. No new visual design or generated-reference acceptance is claimed.</p><img src="../../../media/panels/event-props-v1.gif"><h2>Keyboard, mouse and held-key capture</h2><img src="modes.png"><img src="capture.png"><h2>Exact property right-click target</h2><img src="context.png"><p>Full-event editing preserves the existing KeyMapItem's activation settings; conflicts, stale owners and host commit failures are rejected. Escape/right-click cancel before any write.</p><p><a href="runtime-52.json">5.2 RNA cases</a> · <a href="runtime-51.json">5.1 RNA cases</a> · <a href="windowed-52.json">Real 5.2 window events</a> · <a href="windowed-51.json">Real 5.1 window events</a> · <a href="capture.json">Resources, timing and source hashes</a> · <a href="api-source-audit.json">Official API source audit</a> · <a href="../../../EVENT_PROPERTIES.md">Supported semantics and open gaps</a> · <a href="../numeric-props-v2/index.html">15% numeric motion comparison</a></p>"""
)
print(numeric)
print(events)
