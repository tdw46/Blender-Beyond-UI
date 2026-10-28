"""Verify native-batched menu text against every unbatched motion frame."""

from pathlib import Path
import hashlib, json, shutil, re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/menu-motion-v6"
OUT = ROOT / "docs/design/qa/context-menu-v6"
OUT.mkdir(parents=True, exist_ok=True)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(name):
    source = BASE / name
    result = json.loads((source / "capture.json").read_text())
    assert result["passed"] and result["stable_resources"], name
    for p, digest in result["source_sha256"].items():
        assert sha(ROOT / p) == digest, p
    assert result["fixture_sha256"] == sha(ROOT / "tests/capture_context_menu.py")
    batch = result["native_batch_fixture"]
    if batch.get("native_text_batch"):
        assert batch["helper_sha256"] == sha(ROOT / "tests/menu_motion_batch.py")
    shutil.copy2(source / "capture.json", OUT / f"{name}.json")
    shutil.copy2(BASE / (name + "-run") / "blender-0.log", OUT / f"{name}.log")
    return result


before = read("batched-before")
assert before["native_batch_fixture"]["baseline_sha256"] == sha(
    BASE / "menus-before.py"
)
shutil.copy2(BASE / "menus-before.py", OUT / "menus-before.py")
shutil.copy2(
    ROOT / "build/menu-motion-source/audit.json", OUT / "blf-source-audit.json"
)
checks = {}
for suffix in ["", "-51"]:
    plain = read("after" + suffix)
    batched = read("batched-after" + suffix)
    frames = [
        n
        for n in plain["hashes"]
        if re.fullmatch(r"(?:frame|mode|shortcut|field)-[0-9]{3}", n)
    ]
    assert len(frames) >= 153
    for name in frames:
        assert plain["hashes"][name] == batched["hashes"][name], (suffix, name)
    assert (
        plain["hashes"]["root"]
        == plain["hashes"]["settled"]
        == plain["hashes"]["disabled"]
    )
    checks["51" if suffix else "52"] = dict(
        matching_animation_frames=len(frames),
        batched_pixels_equal_unbatched=True,
        settled_and_disabled_equal_rest=True,
        stable_resources=batched["stable_resources"],
        timings=batched["timings"],
        retained_resources=batched["retained_resources"],
    )
current = json.loads((OUT / "batched-after.json").read_text())
changed = [
    n
    for n in before["hashes"]
    if n.startswith("frame-") and before["hashes"][n] != current["hashes"][n]
]
assert changed, "The baseline must reproduce the defect"
assert before["hashes"]["root"] == current["hashes"]["root"]
checks.update(
    baseline_defect_reproduced_frames=changed,
    rest_pixels_unchanged=True,
    baseline_timings=before["timings"],
    exact_reference_acceptance=False,
)
(OUT / "verification.json").write_text(json.dumps(checks, indent=2) + "\n")
frames = []
pairs = []
for i in range(45):
    old = Image.open(BASE / "batched-before" / f"frame-{i:03}.png").convert("RGB")
    new = Image.open(BASE / "batched-after" / f"frame-{i:03}.png").convert("RGB")
    frames.append(new)
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(old, (0, 32))
    board.paste(new, (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((12, 10), "Before: deferred text escapes menu transform", fill="white")
    draw.text(
        (672, 10), "Fixed: every label and shortcut follows the menu", fill="white"
    )
    pairs.append(board)
pairs[0].save(
    OUT / "motion-comparison.gif",
    save_all=True,
    append_images=pairs[1:],
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
media = ROOT / "docs/media/panels/context-menu-motion-v6.gif"
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
            source="Actual production Blender frames with enclosing native BLF batch",
            capture="../../design/qa/context-menu-v6/batched-after.json",
            sha256=sha(media),
        ),
        indent=2,
    )
    + "\n"
)
for name in ["root", "nested", "tooltip", "field-edit", "frame-002"]:
    p = BASE / "batched-after" / (name + ".png")
    if p.exists():
        shutil.copy2(p, OUT / p.name)
(OUT / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>Menu motion · every option</title><style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}</style><h1>Every menu option follows the bounce · QA v6</h1><p>The test explicitly enables Blender's native deferred text batch. The old painter could submit its final labels after the animated menu matrix was popped. The fix submits text under its owning transform for the finite animation window; resting menus keep the existing batching path.</p><img src="motion-comparison.gif"><p>Left: original painter under native batching. Right: fixed painter, same input, dimensions, theme and cached liquid-glass backdrop. This is actual implementation comparison, not generated-reference acceptance.</p><h2>All text, fields and menu states</h2><img src="../../../media/panels/context-menu-motion-v6.gif"><p>153 animation frames per Blender version cover root/nested/back navigation, capture modes, shortcut capture and inline fields. Every batched frame equals its unbatched counterpart pixel for pixel on Blender 5.1.2 and 5.2.2 Metal. Disabled options and shortcut hints share the same scoped text path. Rest, settle and disable pixels are unchanged.</p><p>No new offscreen, backdrop capture, blur or permanent timer. The fix uses public font APIs; exact-build private batching calls exist only in the test fixture.</p><p><a href="verification.json">Pixel checks, resource counts and timings</a> · <a href="blf-source-audit.json">Exact official font implementation sources</a> · <a href="../numeric-props-v2/index.html">Wide numeric fields at 15% bounce</a> · <a href="../event-props-v1/index.html">New event properties</a></p>"""
)
print(OUT)
print(
    json.dumps(
        {
            k: v.get("matching_animation_frames")
            for k, v in checks.items()
            if isinstance(v, dict) and "matching_animation_frames" in v
        }
    )
)
