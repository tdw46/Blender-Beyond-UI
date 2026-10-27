"""Pair immutable generated-reference crops with actual Blender captures."""

import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ref = Image.open(ROOT / "docs/design/references/specialized-controls-v1.png").convert(
    "RGB"
)
parser = argparse.ArgumentParser()
parser.add_argument("--version", default="v2")
args = parser.parse_args()
out = ROOT / "docs/design/qa" / args.version
# Exact card bounds in the generated sheet; no scaling or repainting reference.
cards = [
    ("curve-mapping", "Curve Mapping", (118, 27, 748, 499)),
    ("color-ramp", "Color Ramp", (788, 27, 1418, 499)),
    ("data-picker", "Data Picker", (118, 523, 748, 995)),
    ("color-picker", "Color Picker", (788, 523, 1418, 995)),
]
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
except OSError:
    font = small = ImageFont.load_default()
frames = []
for slug, title, bounds in cards:
    actual = Image.open(out / (slug + ".png")).convert("RGB")
    expected = ref.crop(bounds)
    assert actual.size == expected.size
    board = Image.new("RGB", (1296, 544), (20, 22, 24))
    draw = ImageDraw.Draw(board)
    draw.text(
        (12, 10), title + " — generated reference", font=font, fill=(240, 242, 245)
    )
    draw.text(
        (654, 10),
        "Current Blender implementation — unapproved",
        font=font,
        fill=(240, 242, 245),
    )
    board.paste(expected, (12, 56))
    board.paste(actual, (654, 56))
    board.save(out / (slug + "-comparison.png"))
    frames.append(board)
contact = Image.new("RGB", (1296, 544 * len(frames)), (20, 22, 24))
for i, frame in enumerate(frames):
    contact.paste(frame, (0, i * 544))
contact.save(out / "all-controls-comparison.png")
(out / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Beyond UI — QA comparisons</title><style>body{margin:24px;background:#141618;color:#edf0f4;font:16px system-ui}main{max-width:1600px;margin:auto}h1{font-size:24px}p{color:#bac1c9}article{margin:32px 0}img{display:block;width:100%;height:auto;border:1px solid #45494f;border-radius:8px}a{color:#7cc7ff}</style><main><h1>Generated references vs Blender implementations</h1><p>Reference left · actual Blender 5.2.2 / Metal capture right. All four controls from the generated sheet. Unapproved prototypes; Tyler performs visual QA. No reference pixels were used to render implementations.</p>"""
    + "".join(
        f'<article><h2>{title}</h2><a href="{slug}-comparison.png"><img src="{slug}-comparison.png" alt="{title}: reference left, implementation right"></a></article>'
        for slug, title, _ in cards
    )
    + """<p><a href="capture.json">Capture provenance</a> · <a href="all-controls-comparison.png">Full-resolution contact sheet</a></p></main></html>"""
)
print(out / "all-controls-comparison.png")

# Keep strict acceptance separate from a useful measure of improvement.
from PIL import ImageChops, ImageStat
import hashlib

metrics = []
contrast = Image.new("RGB", (1296, 1088), (20, 22, 24))
for i, (slug, title, bounds) in enumerate(cards):
    expected = ref.crop(bounds)
    actual = Image.open(out / (slug + ".png")).convert("RGB")
    difference = ImageChops.difference(expected, actual)
    difference.save(out / (slug + "-difference.png"))
    Image.blend(expected, actual, 0.5).save(out / (slug + "-overlay.png"))
    old = Image.open(ROOT / "docs/design/qa/v1" / (slug + ".png")).convert("RGB")
    metrics.append(
        {
            "control": title,
            "crop": bounds,
            "exact_match": difference.getbbox() is None,
            "changed_pixels": sum(any(p) for p in difference.getdata()),
            "mean_absolute_rgb_error_v1": sum(
                ImageStat.Stat(ImageChops.difference(expected, old)).mean
            )
            / 3,
            "mean_absolute_rgb_error_v2": sum(ImageStat.Stat(difference).mean) / 3,
            "capture_sha256": hashlib.sha256(
                (out / (slug + ".png")).read_bytes()
            ).hexdigest(),
        }
    )
    tile = Image.new("RGB", (648, 544), (20, 22, 24))
    draw = ImageDraw.Draw(tile)
    draw.text((12, 10), title + " — contrast backdrop", font=font, fill="white")
    tile.paste(Image.open(out / (slug + "-contrast.png")).convert("RGB"), (12, 56))
    contrast.paste(tile, ((i % 2) * 648, (i // 2) * 544))
contrast.save(out / "transparency.png")
report = {
    "reference": "../../references/specialized-controls-v1.png",
    "reference_sha256": hashlib.sha256(
        (ROOT / "docs/design/references/specialized-controls-v1.png").read_bytes()
    ).hexdigest(),
    "exact_match": all(m["exact_match"] for m in metrics),
    "notes": "RGB error is diagnostic, not acceptance. Reference background lighting is not known; color-marker and ramp-stop positions conflict with numeric labels. No image pixels enter the renderer.",
    "controls": metrics,
}
(out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
with (out / "index.html").open("a") as stream:
    stream.write(
        '<section><h2>Transparency check</h2><p>Production translucent surfaces over a contrasting backdrop. This offscreen fixture tests the tint-only path, not the shared blur.</p><img src="transparency.png" alt="All four controls over a contrasting backdrop"><p><a href="comparison.json">Strict comparison results and measured improvement</a></p></section>'
    )
print(json.dumps(report, indent=2))
