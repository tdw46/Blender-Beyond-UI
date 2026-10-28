"""Compare the new scroll reference with actual Blender output; no acceptance inference."""

from pathlib import Path
import json, hashlib, shutil
from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/design/qa/picker-v1"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "build/picker-final-scroll"
reference = ROOT / "docs/design/references/data-picker-scroll-v1.png"
ref = Image.open(reference).convert("RGB").resize((630, 472), Image.Resampling.LANCZOS)
actual = Image.open(SOURCE / "data-picker-scroll.png").convert("RGB")
board = Image.new("RGB", (1284, 520), "#141618")
draw = ImageDraw.Draw(board)
draw.text((8, 10), "Generated scroll reference", fill="white")
draw.text((654, 10), "Actual Blender implementation", fill="white")
board.paste(ref, (8, 40))
board.paste(actual, (646, 40))
board.save(OUT / "comparison.png")
Image.blend(ref, actual, 0.5).save(OUT / "overlay.png")
difference = ImageChops.difference(ref, actual)
difference.save(OUT / "difference.png")
for p in SOURCE.glob("*.png"):
    shutil.copyfile(p, OUT / p.name)
shutil.copyfile(SOURCE / "capture.json", OUT / "capture.json")
# Draw clipping proof compares pixels outside both list and scrollbar regions.
rest = Image.open(ROOT / "docs/design/qa/v2/data-picker.png").convert("RGB")
outside = ImageChops.difference(rest, actual)
d = ImageDraw.Draw(outside)
d.rectangle((24, 146, 585, 353), fill=0)
d.rectangle((597, 147, 610, 357), fill=0)
assert outside.getbbox() is None, (
    "Scrolling affected pixels outside the owned list/scrollbar"
)
regression = []
for p in sorted((ROOT / "build/picker-final-rest").glob("*.png")):
    same = p.read_bytes() == (ROOT / "docs/design/qa/v2" / p.name).read_bytes()
    assert same, p.name
    regression.append(dict(file=p.name, identical=True))
result = dict(
    reference=str(reference.relative_to(ROOT)),
    reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
    exact_match=difference.getbbox() is None,
    mean_absolute_rgb=ImageStat.Stat(difference).mean,
    outside_list_pixels_unchanged=True,
    rest_regression=regression,
    acceptance="Awaiting Tyler QA. Generated scrollbar size/position differs from the requested fixture; do not claim an exact match.",
)
(OUT / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
for name in [
    "picker-window51",
    "picker-window52-final",
    "picker-bench-scroll",
    "picker-bench-rest",
]:
    shutil.copyfile(ROOT / "build" / f"{name}.json", OUT / f"{name}.json")
(OUT / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>Data Picker interaction QA</title><style>body{background:#141618;color:#edf0f4;font:16px system-ui;margin:24px}img{max-width:100%}a{color:#79caff}</style><h1>Data Picker interaction parity</h1><p>Generated reference left, actual Blender capture right. Awaiting QA.</p><img src="comparison.png" alt="Data Picker scroll comparison"><p><a href="NOTES.md">Behavior and verification notes</a></p>'
)
print(json.dumps(result, indent=2))
