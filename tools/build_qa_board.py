"""Pair immutable generated-reference crops with actual Blender captures."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ref = Image.open(ROOT / "docs/design/references/specialized-controls-v1.png").convert(
    "RGB"
)
out = ROOT / "docs/design/qa/v1"
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
