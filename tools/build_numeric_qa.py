"""Package actual property-unit evidence without changing earlier QA galleries."""

from pathlib import Path
import hashlib, json, shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/prop-numeric"
SOURCE = BASE / "capture"
OUT = ROOT / "docs/design/qa/numeric-props-v1"
OUT.mkdir(parents=True, exist_ok=True)
record = json.loads((SOURCE / "capture.json").read_text())
assert record["passed"] and record["stable_resources"]
for name, digest in record["source_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
assert (
    record["fixture_sha256"]
    == hashlib.sha256((ROOT / "tests/capture_numeric.py").read_bytes()).hexdigest()
)
for p in SOURCE.glob("*.png"):
    if not p.name.startswith("frame-"):
        shutil.copy2(p, OUT / p.name)
for name in ["capture.json"]:
    shutil.copy2(SOURCE / name, OUT / name)
shutil.copy2(BASE / "capture-run/blender-0.log", OUT / "capture.log")
shutil.copy2(BASE / "api-evidence/audit.json", OUT / "api-source-audit.json")
for folder in ["runtime", "regression", "menus", "modal"]:
    for i, v in enumerate(["52", "51"]):
        p = BASE / folder / f"result-{i}.json"
        assert json.loads(p.read_text())["passed"]
        shutil.copy2(p, OUT / f"{folder}-{v}.json")
        shutil.copy2(BASE / folder / f"blender-{i}.log", OUT / f"{folder}-{v}.log")
board = Image.new("RGB", (1300, 592), "#17191b")
draw = ImageDraw.Draw(board)
for x, p, title in [
    (0, "raw-baseline.png", "Raw stored numbers (same renderer)"),
    (660, "units.png", "RNA-aware units; same shared glass and spring"),
]:
    board.paste(Image.open(OUT / p), (x, 32))
    draw.text((x + 10, 10), title, fill="white")
board.save(OUT / "comparison.png")
frames = [Image.open(p).convert("RGBA") for p in sorted(SOURCE.glob("frame-*.png"))]
media = ROOT / "docs/media/panels/numeric-props-v1.gif"
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
            capture="../../design/qa/numeric-props-v1/capture.json",
            sha256=hashlib.sha256(media.read_bytes()).hexdigest(),
        ),
        indent=2,
    )
    + "\n"
)
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Beyond UI · Numeric properties</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}</style>
<h1>Numeric property support · QA v1</h1><p>Actual Blender 5.2.2 Metal renders. This extends the existing control painter and BVT shared glass, spring and theme roles. No generated-reference or motion acceptance is claimed.</p>
<h2>Stored values and displayed units</h2><img src="comparison.png"><p>The baseline disables only numeric formatting in the same renderer; it is not a historical binary or a generated reference. RNA values stay unchanged. Angle, length, percentage, and preferred-unit presentation update without rebuilding layout or glass.</p>
<h2>Shared motion</h2><img src="../../../media/panels/numeric-props-v1.gif"><p>Hover, press, drag and release use the existing source motion. Settled and animation-disabled pixels equal the resting frame. One backdrop, one strong-blur production and five retained offscreens serve all frames.</p>
<h2>Editing and right-click ownership</h2><img src="edit.png"><img src="context.png"><p>Click to type; Enter confirms. Safe unit arithmetic, Shift precision, Ctrl snapping, soft drag limits and hard text limits share the original RNA binding. Right-click cancels edits first, then targets the exact property/component. Unit-setting changes during an edit reject stale interpretation.</p>
<h2>Live scene units and theme</h2><img src="imperial-radians.png"><p>The active Blender theme and imperial/radians settings are read at runtime. Bound values are not rewritten. Full theme/DPI/platform and generated-reference qualification remain separate.</p>
<h2>Evidence and remaining scope</h2><p><a href="capture.json">Rendering/resources/timing/source hashes</a> · <a href="runtime-51.json">Blender 5.1.2 cases</a> · <a href="runtime-52.json">Blender 5.2.2 cases</a> · <a href="api-source-audit.json">Official API implementation sources</a> · <a href="../../../NUMERIC_PROPERTIES.md">Integration and remaining prop gaps</a></p>
""")
print(OUT)
