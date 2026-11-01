"""Compose saved references and real captures into mobile-readable image sheets."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/design/qa/camkeys-studio-v6"
OUT = REVIEW / "mobile"
OUT.mkdir(exist_ok=True)
font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
title_font = ImageFont.truetype(font_path, 30)
label_font = ImageFont.truetype(font_path, 24)
records = json.loads((REVIEW / "implementation/report.json").read_text())["records"]
titles = {r["slug"]: r["controls"][0]["label"] for r in records}
manifest = []
for panel in json.loads((REVIEW / "panels.json").read_text()):
    reference = Image.open(REVIEW / panel["reference"]).convert("RGB")
    x, y, w, h = panel["audit"]["reference_bounds_px"]
    reference = reference.crop((x, y, x + w, y + h))
    actual = Image.open(REVIEW / panel["implementation"]).convert("RGB")
    actual = actual.crop((32, 32, actual.width - 32, actual.height - 32))
    # Equal panel width, preserved aspect ratios; no redrawing of UI pixels.
    images = [im.resize((640, round(im.height * 640 / im.width)), Image.Resampling.LANCZOS)
              for im in (reference, actual)]
    sheet = Image.new("RGB", (1340, max(im.height for im in images) + 150), "#171B20")
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 14), titles[panel["slug"]], font=title_font, fill="#F1F4F7")
    for left, label, im in zip((20, 680), ("Generated reference", "Actual Blender UI"), images):
        draw.text((left, 62), label, font=label_font, fill="#BCC8D1")
        sheet.paste(im, (left, 102))
    draw.text((20, sheet.height - 34), "Saved Studio v6 comparison · equal width · original proportions",
              font=ImageFont.truetype(font_path, 18), fill="#A9B6C0")
    path = OUT / (panel["slug"] + ".jpg")
    sheet.save(path, quality=93, subsampling=0)
    manifest.append(dict(panel=panel["slug"], image=path.name,
                         reference=panel["reference"], implementation=panel["implementation"],
                         size=list(sheet.size)))
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Created {len(manifest)} mobile comparison sheets in {OUT}")
