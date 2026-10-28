"""Package raw Blender evidence and diagnostic comparisons; never retouch renders."""

from pathlib import Path
import hashlib, json, shutil
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "build/context-menu-v1/capture"
out = ROOT / "docs/design/qa/context-menu-v1"
out.mkdir(parents=True, exist_ok=True)
record = json.loads((source / "capture.json").read_text())
assert record["passed"] and record["stable_resources"]
for name, digest in record["source_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
for path in source.glob("*.png"):
    if not path.name.startswith("frame-"):
        shutil.copy2(path, out / path.name)
shutil.copy2(source / "capture.json", out / "capture.json")
for slug, folder in [
    ("rna", "rna-final"),
    ("modal", "modal-admitted"),
    ("regression-window", "regression-window"),
    ("regression-rna", "regression-rna"),
]:
    for i, version in enumerate(("52", "51")):
        path = ROOT / f"build/context-menu-v1/{folder}/result-{i}.json"
        assert json.loads(path.read_text())["passed"]
        shutil.copy2(path, out / f"{slug}-{version}.json")


def pair(a, b, path, left, right):
    board = Image.new("RGB", (1300, 592), "#17191b")
    board.paste(a, (0, 32))
    board.paste(b, (660, 32))
    draw = ImageDraw.Draw(board)
    draw.text((10, 10), left, fill="white")
    draw.text((670, 10), right, fill="white")
    board.save(path)


actual = Image.open(out / "root.png").convert("RGBA")
fallback = Image.open(out / "tint-fallback.png").convert("RGBA")
pair(
    fallback,
    actual,
    out / "liquid-glass-comparison.png",
    "Before: tint fallback / underlying text legible",
    "After: actual BVT shared blur and refraction",
)
ref = Image.open(ROOT / "docs/design/references/context-menu-v1.png").convert("RGBA")
raw_size = ref.size
ref = ref.resize((640, 560), Image.Resampling.LANCZOS)
original = Image.open(out / "reference-input.png").convert("RGBA")
pair(
    ref,
    original,
    out / "rejected-reference-comparison.png",
    "Rejected generated v1, normalized for inspection",
    "Original tint implementation used as generation input",
)
ImageChops.difference(ref, original).save(out / "rejected-reference-difference.png")
Image.blend(ref, original, 0.5).save(out / "rejected-reference-overlay.png")
comparison = dict(
    exact_match=False,
    reference_status="rejected; not adopted",
    generated_dimensions=raw_size,
    input_dimensions=[640, 560],
    reference_normalized_for_diagnostics_only=True,
    liquid_glass_reference_matched=False,
    notes="Generated v1 changed disabled contrast, texture and dimensions. User rejected tint-only material. New liquid-glass captures use source BVT semantics, not this rejected image; reference and motion acceptance remain open.",
)
(out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
frames = (
    [actual.copy()] * 6
    + [Image.open(p).convert("RGBA") for p in sorted(source.glob("frame-*.png"))]
    + [Image.open(out / "settled.png").convert("RGBA")] * 12
)
media = ROOT / "docs/media/panels/context-menu.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
provenance = dict(
    source="Production Blender Canvas frames with BVT liquid glass; no generated pixels",
    source_frame_sha256={
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(source.glob("frame-*.png"))
    },
    gif_sha256=hashlib.sha256(media.read_bytes()).hexdigest(),
    capture="../../design/qa/context-menu-v1/capture.json",
)
(media.parent / "context-menu-provenance.json").write_text(
    json.dumps(provenance, indent=2) + "\n"
)
controls = record["compound_targets"]
cards = "".join(
    f'<figure><img src="control-{slug}.png"><figcaption>{slug}: {part}</figcaption></figure>'
    for slug, part in controls.items()
)
(out / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>Beyond UI — context menu QA</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}h1{font-size:26px}h2{margin-top:36px}a{color:#7ac9fa}img{max-width:100%;height:auto}figure{margin:0}figcaption{padding:8px;color:#bdc5cc}.grid{display:grid;grid-template-columns:repeat(2,minmax(300px,640px));gap:20px}.wide{max-width:1300px}p{max-width:1000px;line-height:1.6}button{padding:9px}#overlay{position:relative;width:640px;height:560px}#overlay img{position:absolute;inset:0;width:640px;height:560px}</style>
<h1>Right-click menus · liquid-glass QA</h1><p>Actual Blender 5.2.2 / Metal, 640×560, explicit reference theme. Original BVT lens/strong blur functions retained. One shared backdrop preparation and one strong-blur preparation; no per-menu/frame captures. Tyler owns visual acceptance.</p>
<h2>Tint versus real liquid glass</h2><img class="wide" src="liquid-glass-comparison.png">
<h2>Motion</h2><img src="../../../media/panels/context-menu.gif"><p>Actual production frames. Static generated art does not establish motion parity.</p>
<h2>Nested menus and delayed descriptions</h2><div class="grid"><img src="nested.png"><img src="tooltip.png"></div>
<h2>All existing compound targets</h2><p>Menus address the hovered component, stop, swatch or row. Generic callback values expose Copy Value; RNA-backed controls and host providers supply applicable property/data actions.</p><div class="grid">"""
    + cards
    + """</div>
<h2>Rejected generated reference v1</h2><p>This generation changed typography, texture, dimensions and disabled contrast. Its tint-only input was superseded by the user's liquid-glass requirement. It is preserved for provenance and must not count as accepted reference matching. It does not specify the corrected glass implementation.</p><img class="wide" src="rejected-reference-comparison.png"><p><a href="rejected-reference-difference.png">Difference</a> · <a href="rejected-reference-overlay.png">50% overlay</a> · <a href="comparison.json">Comparison status</a></p>
<h2>Evidence</h2><p><a href="capture.json">Capture/resource/timing record</a> · <a href="rna-51.json">RNA 5.1.2</a> · <a href="rna-52.json">RNA 5.2.2</a> · <a href="modal-51.json">Windowed 5.1.2</a> · <a href="modal-52.json">Windowed 5.2.2</a></p>"""
)
print("Packaged menu QA", out)
