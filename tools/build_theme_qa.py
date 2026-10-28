"""Assemble theme captures and reference-conflict evidence without retouching pixels."""

from pathlib import Path
import argparse
import hashlib
import json
import shutil
from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--evidence", type=Path, default=ROOT / "build/theme-v1")
args = parser.parse_args()
source = args.evidence
out = ROOT / "docs/design/qa/theme-v1"
out.mkdir(parents=True, exist_ok=True)
names = ("native-dark", "synthetic-light", "synthetic-purple")
actual = Image.new("RGBA", (1360, 1680))
for i, name in enumerate(names):
    path = source / "runtime52-final" / (name + ".png")
    shutil.copy2(path, out / path.name)
    with Image.open(path) as im:
        assert im.size == (1360, 560)
        actual.paste(im, (0, i * 560))
actual.save(out / "actual.png")
reference_path = ROOT / "docs/design/references/theme-states-v1.png"
with Image.open(reference_path) as raw:
    original_size = raw.size
    reference = raw.convert("RGBA").resize(actual.size, Image.Resampling.LANCZOS)
board = Image.new("RGB", (2740, 1720), "#141618")
board.paste(reference, (0, 40))
board.paste(actual, (1380, 40))
draw = ImageDraw.Draw(board)
draw.text(
    (12, 12),
    "Generated v1 - conflict: proportions, text and cropped bottom row",
    fill="white",
)
draw.text(
    (1392, 12),
    "Actual Blender 5.2.2 - native dark, synthetic light, synthetic purple",
    fill="white",
)
board.save(out / "comparison.png")
Image.blend(reference, actual, 0.5).save(out / "overlay.png")
difference = ImageChops.difference(reference, actual)
difference.save(out / "difference.png")
records = []
for version in ("51", "52"):
    path = source / f"runtime{version}-final/result.json"
    record = json.loads(path.read_text())
    assert (
        record["passed"]
        and record["rna_restored"]
        and record["bound_data_pixels_unchanged"]
    )
    for name, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    shutil.copy2(path, out / f"runtime-{version}.json")
    records.append(record)
for name in ("baseline", "after", "native-bench"):
    path = source / (name + ".json")
    record = json.loads(path.read_text())
    assert record["passed"] and record["warm_resources_unchanged"]
    shutil.copy2(path, out / (name + ".json"))
rest = []
for path in sorted((source / "reference-final").glob("*.png")):
    old = ROOT / "docs/design/qa/v2" / path.name
    assert path.read_bytes() == old.read_bytes(), path.name
    rest.append(path.name)
assert len(rest) == 12
shutil.copy2(source / "reference-final/capture.json", out / "reference-capture.json")
# One capture contains all eight cards through the production Canvas path.
motion_result = json.loads((source / "motion-final/capture.json").read_text())
assert motion_result["passed"]
prior_frames = json.loads((ROOT / "docs/media/panels/provenance.json").read_text())[
    "source_frame_sha256"
]
assert len(prior_frames) == 75
for name, digest in prior_frames.items():
    assert (
        hashlib.sha256((source / "motion-final" / name).read_bytes()).hexdigest()
        == digest
    ), name
shutil.copy2(source / "motion-final/capture.json", out / "motion-capture.json")
reference_meta = {
    "version": 1,
    "tool": "built-in image_gen",
    "prompt": "theme-states-v1.prompt.txt",
    "requested_size": [1360, 1680],
    "generated_size": list(original_size),
    "sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
    "supporting_inputs": [
        {
            "file": f"../qa/theme-v1/{n}.png",
            "sha256": hashlib.sha256((out / (n + ".png")).read_bytes()).hexdigest(),
        }
        for n in names
    ],
    "states": list(names),
    "status": "reference conflict; not adopted or approved",
    "conflicts": [
        "Changed panel proportions and row spacing",
        "Cropped/compressed purple bottom row",
        "Altered numeric text; generated color values must not replace bound values",
    ],
    "resolution": "Pending explicit reference correction and Tyler QA. Preserve source-driven theme semantics and prior geometry; no exact-match claim.",
}
(ROOT / "docs/design/references/theme-states-v1.json").write_text(
    json.dumps(reference_meta, indent=2) + "\n"
)
summary = {
    "reference": "../../references/theme-states-v1.png",
    "reference_normalization": {
        "from": list(original_size),
        "to": list(actual.size),
        "method": "Lanczos; QA copy only, original immutable",
    },
    "exact_match": False,
    "reference_status": reference_meta["status"],
    "mean_absolute_rgba_difference": ImageStat.Stat(difference).mean,
    "unchanged_prior_captures": rest,
    "unchanged_prior_animation_frames": len(prior_frames),
    "note": "The sheet does not align because generation changed geometry. Difference metrics are diagnostics, not acceptance; no image data is used by production painters.",
}
(out / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
(out / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Beyond UI theme QA</title><style>body{margin:24px;background:#141618;color:#edf0f4;font:16px system-ui}img{max-width:100%;height:auto}a{color:#9bd6ff}p{max-width:85ch}</style><h1>Blender theme colors</h1><p>Actual production painters: native dark, synthetic light and synthetic purple. Source BVT semantic roles supply RGB; existing glass materials supply opacity. Bound colors are unchanged.</p><p>The generated sheet changed proportions, text and cropped its bottom row. This remains an explicit reference conflict; no exact visual acceptance is claimed.</p><p><a href="NOTES.md">Validation notes</a> · <a href="overlay.png">Overlay</a> · <a href="difference.png">Difference</a> · <a href="../../references/theme-states-v1.prompt.txt">Built-in generation prompt</a></p><img src="comparison.png" alt="Generated reference versus actual Blender output"><h2>Actual native dark theme</h2><img src="native-dark.png" alt="Eight custom panels in the native dark theme"><h2>Actual synthetic light theme</h2><img src="synthetic-light.png" alt="Eight custom panels in a synthetic light theme"><h2>Actual synthetic purple theme</h2><img src="synthetic-purple.png" alt="Eight custom panels in a synthetic purple theme"></html>"""
)
print(json.dumps(summary, indent=2))
