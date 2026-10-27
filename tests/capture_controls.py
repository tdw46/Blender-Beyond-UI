"""Capture the actual widget painters in Blender, without altering a user scene."""

import bpy
import blf
import gpu
from mathutils import Matrix
from pathlib import Path
import json
import hashlib
from itertools import product
import os
import struct
import sys
import traceback
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import Binding
from beyond_ui.editing import to_linear
from beyond_ui.widgets import ColorPicker, ColorRamp, CurveMapping, DataPicker
from beyond_ui.gpu import style, skin
from beyond_ui.gpu.typography import Fonts
from beyond_ui.gpu.paint import gpu_state


def binding(value):
    values = [value]
    return Binding(lambda: values[0], lambda v: values.__setitem__(0, v))


def png(path, width, height, data):
    # Lossless raw framebuffer capture; no color grading or reference blending.
    raw = bytes(data)
    rows = b"".join(
        b"\0" + raw[y * width * 4 : (y + 1) * width * 4]
        for y in reversed(range(height))
    )

    def chunk(name, payload):
        return (
            struct.pack("!I", len(payload))
            + name
            + payload
            + struct.pack("!I", zlib.crc32(name + payload) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def make_widgets():
    curve = CurveMapping(
        binding(((0.05, 0.05), (0.5, 0.5), (0.95, 0.95))),
        channel=binding(3),
        evaluate=lambda x: 0.05
        + 0.9 * (lambda t: t * t * (3 - 2 * t))(max(0, min(1, (x - 0.05) / 0.9))),
    )
    curve.selected = 1
    ramp = ColorRamp(
        binding(
            (
                (0.0, tuple(to_linear(c) for c in (0.0, 0.26, 0.77)) + (1.0,)),
                (0.5, tuple(to_linear(c) for c in (0.10, 0.75, 0.94)) + (1.0,)),
                (1.0, tuple(to_linear(c) for c in (0.94, 0.98, 1.0)) + (1.0,)),
            )
        )
    )
    ramp.selected = 1
    picker = DataPicker(
        ((1, "Camera", "camera"), (2, "Cube", "object"), (3, "Sphere", "material")),
        lambda key: None,
        selected=lambda: 2,
    )
    color = ColorPicker(binding((0.2, 0.7, 0.9, 1.0)), linear=False)
    widgets = [
        ("curve-mapping", "Curve Mapping", curve),
        ("color-ramp", "Color Ramp", ramp),
        ("data-picker", "Data Picker", picker),
        ("color-picker", "Color Picker", color),
    ]
    next_set = os.environ.get("BEYOND_UI_CAPTURE_SET") == "next"
    if next_set:
        sys.path.insert(0, str(ROOT / "tests"))
        from next_fixtures import widgets as next_widgets

        widgets = next_widgets()
    return widgets, next_set


def run():
    OUTPUT = Path(os.environ["BEYOND_UI_CAPTURE_DIR"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font = -1
    target = None
    try:
        font = Fonts()
        widgets, next_set = make_widgets()
        width, height = (705, 487) if next_set else (630, 472)
        palette = style.theme_palette(bpy.context.preferences)
        target = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        records = []
        for (slug, title, widget), variant in product(
            widgets, ("neutral", "contrast", "alpha")
        ):
            if next_set:
                wanted = (705, 487 if widget.height == 436 else 437)
                if wanted != (width, height):
                    target.free()
                    width, height = wanted
                    target = gpu.types.GPUOffScreen(width, height, format="RGBA8")
            filename = slug + ("" if variant == "neutral" else "-" + variant) + ".png"
            with (
                target.bind(),
                gpu.matrix.push_pop(),
                gpu.matrix.push_pop_projection(),
                gpu_state(),
            ):
                gpu.state.viewport_set(0, 0, width, height)
                gpu.state.scissor_set(0, 0, width, height)
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(
                    Matrix(
                        (
                            (2 / width, 0, 0, -1),
                            (0, 2 / height, 0, -1),
                            (0, 0, 1, 0),
                            (0, 0, 0, 1),
                        )
                    )
                )
                gpu.state.active_framebuffer_get().clear(
                    color=(0, 0, 0, 0)
                    if variant == "alpha"
                    else (22 / 255, 25 / 255, 27 / 255, 1.0)
                )
                if variant == "contrast":
                    for row in range(6):
                        for col in range(8):
                            color = (
                                skin.rgba("a67c43")
                                if (row + col) % 2
                                else skin.rgba("347b9b")
                            )
                            skin.draw(
                                (col * 80, row * 80, 80, 80), color, radius=0, border=0
                            )
                widget.paint((0, 0, width, height), font, palette)
                buffer = gpu.state.active_framebuffer_get().read_color(
                    0, 0, width, height, 4, 0, "UBYTE"
                )
                buffer.dimensions = width * height * 4
                png(OUTPUT / filename, width, height, buffer)
                records.append(
                    {
                        "control": title,
                        "file": filename,
                        "background": variant,
                        "size": [width, height],
                        "painter": widget.__class__.__module__
                        + "."
                        + widget.__class__.__name__,
                    }
                )
        result = {
            "passed": True,
            "version": bpy.app.version_string,
            "build": bpy.app.build_hash.decode(),
            "backend": gpu.platform.backend_type_get(),
            "font": "Bundled Inter Regular / SemiBold",
            "captures": records,
            "source": "Actual Blender GPUOffScreen, reference skin, production library painters; no reference pixels used. Contrast/alpha fixtures test tint-only transparency; shared blur is not exercised in this offscreen fixture.",
            "source_sha256": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            "font_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui/assets/fonts").glob("*.woff2"))
            },
            "acceptance": "Unapproved; Tyler performs visual QA",
        }
    except Exception:
        result = {"passed": False, "error": traceback.format_exc()}
    finally:
        if target is not None:
            target.free()
        if font >= 0:
            font.close()
    (OUTPUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print("BEYOND_UI_CAPTURE", json.dumps(result), flush=True)
    bpy.ops.wm.quit_blender()
    return None


if __name__ == "__main__":
    bpy.app.timers.register(run, first_interval=1.0)
