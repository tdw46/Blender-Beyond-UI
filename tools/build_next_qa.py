"""Compare untouched generated crops with raw Blender framebuffer captures."""

import json, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/design/qa/next-v1"
REF = ROOT / "docs/design/references/next-controls-v2.png"
CARDS = [
    ("palette", "Palette", (45, 36, 750, 523)),
    ("matrix", "Matrix", (787, 36, 1492, 523)),
    ("progress-bar", "Progress Bar", (45, 549, 750, 986)),
    ("progress-ring", "Progress Ring", (787, 549, 1492, 986)),
]
ref = Image.open(REF).convert("RGB")
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
boards = []
transparency = []
records = []
for slug, title, bounds in CARDS:
    actual = Image.open(OUT / (slug + ".png")).convert("RGB")
    expected = ref.crop(bounds)
    assert actual.size == expected.size
    w, h = actual.size
    board = Image.new("RGB", (w * 2 + 36, h + 64), (20, 22, 24))
    d = ImageDraw.Draw(board)
    d.text((12, 12), title + " — generated reference", font=font, fill="white")
    d.text(
        (w + 24, 12), "Blender implementation — awaiting QA", font=font, fill="white"
    )
    board.paste(expected, (12, 52))
    board.paste(actual, (w + 24, 52))
    board.save(OUT / (slug + "-comparison.png"))
    boards.append(board)
    diff = ImageChops.difference(expected, actual)
    diff.save(OUT / (slug + "-difference.png"))
    Image.blend(expected, actual, 0.5).save(OUT / (slug + "-overlay.png"))
    records.append(
        {
            "control": title,
            "bounds": bounds,
            "exact_match": diff.getbbox() is None,
            "mean_absolute_rgb_error": sum(ImageStat.Stat(diff).mean) / 3,
            "capture_sha256": hashlib.sha256(
                (OUT / (slug + ".png")).read_bytes()
            ).hexdigest(),
        }
    )
    transparency.append(Image.open(OUT / (slug + "-contrast.png")).convert("RGB"))
contact = Image.new("RGB", (1446, sum(b.height for b in boards)), (20, 22, 24))
y = 0
for b in boards:
    contact.paste(b, (0, y))
    y += b.height
contact.save(OUT / "all-controls-comparison.png")
proof = Image.new("RGB", (1410, 924), (20, 22, 24))
for i, img in enumerate(transparency):
    proof.paste(img, ((i % 2) * 705, 0 if i < 2 else 487))
proof.save(OUT / "transparency.png")
report = {
    "reference": str(REF.relative_to(ROOT)),
    "reference_sha256": hashlib.sha256(REF.read_bytes()).hexdigest(),
    "exact_match": all(r["exact_match"] for r in records),
    "controls": records,
    "acceptance": "Awaiting Tyler QA. Numerical image difference is not a visual-acceptance claim.",
}
(OUT / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
(OUT / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>Next controls — QA</title><style>body{background:#141618;color:#edf0f4;font:16px system-ui;margin:24px}img{max-width:100%;height:auto}a{color:#79caff}</style><h1>Next parity controls</h1><p>Generated reference left · actual Blender capture right. Awaiting QA.</p>'
    + "".join(
        f'<h2>{title}</h2><img src="{slug}-comparison.png" alt="{title} comparison">'
        for slug, title, _ in CARDS
    )
    + '<h2>Transparency</h2><img src="transparency.png" alt="Contrasting backdrop"><h2>Actual source-spring motion</h2><p>Eight implemented cards. Motion matching awaits QA.</p><img src="motion.gif" alt="Actual Blender animation captures"><p><a href="../v2/index.html">Previous four comparisons</a> · <a href="NOTES.md">Implementation and validation notes</a></p>'
)
print(json.dumps(report, indent=2))
