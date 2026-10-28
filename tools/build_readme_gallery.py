"""Crop actual Blender animation frames into reproducible README panel previews."""

from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PANELS = (
    ("curve-mapping", "Curve Mapping"),
    ("color-ramp", "Color Ramp"),
    ("data-picker", "Data Picker"),
    ("color-picker", "Color Picker"),
    ("palette", "Palette"),
    ("matrix", "Matrix decomposition"),
    ("progress-bar", "Progress Bar"),
    ("progress-ring", "Progress Ring"),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, default=ROOT / "build/motion-final")
    args = parser.parse_args()
    provenance = json.loads((args.frames / "capture.json").read_text())
    assert provenance["passed"], "Capture must pass before publication"
    paths = sorted(args.frames.glob("frame-*.png"))
    assert paths, "Run tests/capture_motion.py first"
    output = ROOT / "docs/media/panels"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for i, (slug, title) in enumerate(PANELS):
        bounds = ((i % 4) * 340, (i // 4) * 280, (i % 4 + 1) * 340, (i // 4 + 1) * 280)
        frames = []
        for path in paths:
            with Image.open(path) as im:
                frames.append(im.convert("RGB").crop(bounds))
        palette = frames[0].quantize(colors=256)
        encoded = [
            frame.quantize(palette=palette, dither=Image.Dither.NONE)
            for frame in frames
        ]
        dest = output / f"{slug}.gif"
        # GIF delays are centiseconds: 30/30/40ms totals exactly one second/30 frames.
        durations = [30 if n % 3 != 2 else 40 for n in range(len(encoded))]
        encoded[0].save(
            dest,
            save_all=True,
            append_images=encoded[1:],
            duration=durations,
            loop=0,
            optimize=False,
            disposal=2,
        )
        with Image.open(dest) as im:
            assert im.size == (340, 280)
            assert im.n_frames > 1, f"{slug} has no actual animation"
            duration = sum(
                (im.seek(n) or im.info["duration"]) for n in range(im.n_frames)
            )
            assert duration == sum(durations)
        records.append(
            dict(
                panel=title,
                file=dest.name,
                crop=bounds,
                sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                duration_ms=duration,
            )
        )
    (output / "provenance.json").write_text(
        json.dumps(
            dict(
                source="Actual Blender Canvas GPU captures; only cropping and GIF palette encoding",
                capture_version=provenance["version"],
                capture_build=provenance["build"],
                source_sha256=provenance["source_sha256"],
                source_frame_sha256={
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
                },
                panels=records,
            ),
            indent=2,
        )
        + "\n"
    )
    print(f"Published {len(records)} panel GIFs to {output}")


if __name__ == "__main__":
    main()
