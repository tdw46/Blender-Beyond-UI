"""Strict comparison gate: no pixel mismatch is silently accepted.

Inputs must depict the same dimensions, scale, theme, background and state.
Output files are diagnostics, never replacements for the immutable reference.
"""

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.reference.resolve() == args.capture.resolve():
        parser.error("Capture must be a separate actual Blender render")
    ref = Image.open(args.reference).convert("RGBA")
    actual = Image.open(args.capture).convert("RGBA")
    if ref.size != actual.size:
        parser.error(f"Dimensions differ: reference {ref.size}, capture {actual.size}")
    args.output.mkdir(parents=True, exist_ok=True)
    diff = ImageChops.difference(ref, actual)
    changed = sum(any(pixel) for pixel in diff.getdata())
    diff.save(args.output / "difference.png")
    Image.blend(ref, actual, 0.5).save(args.output / "overlay.png")
    side = Image.new("RGBA", (ref.width * 2, ref.height))
    side.paste(ref, (0, 0))
    side.paste(actual, (ref.width, 0))
    side.save(args.output / "side-by-side.png")
    result = {
        "reference": str(args.reference),
        "capture": str(args.capture),
        "size": list(ref.size),
        "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        "capture_sha256": hashlib.sha256(args.capture.read_bytes()).hexdigest(),
        "changed_pixels": changed,
        "total_pixels": ref.width * ref.height,
        "exact_match": changed == 0,
    }
    (args.output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if changed == 0 else 1)


if __name__ == "__main__":
    main()
