"""Capture the actual widget painters in Blender, without altering a user scene."""

import bpy
import blf
import gpu
from mathutils import Matrix
from pathlib import Path
import json
import os
import struct
import sys
import traceback
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import Binding
from beyond_ui.widgets import ColorPicker, ColorRamp, CurveMapping, DataPicker
from beyond_ui.gpu import style
from beyond_ui.gpu.paint import gpu_state

OUTPUT = Path(os.environ["BEYOND_UI_CAPTURE_DIR"])
OUTPUT.mkdir(parents=True, exist_ok=True)


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


def run():
    font = -1
    target = None
    try:
        fonts = Path(bpy.utils.resource_path("LOCAL")) / "datafiles/fonts"
        path = next(iter(fonts.glob("Inter*.woff2")), None) or next(
            iter(fonts.glob("bfont*")), None
        )
        assert path, "No Blender font"
        font = blf.load(str(path))
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
                    (0.0, (0.0, 0.03, 0.4, 1.0)),
                    (0.5, (0.0, 0.6, 0.9, 1.0)),
                    (1.0, (0.8, 0.95, 1.0, 1.0)),
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
        width, height = 630, 472
        palette = style.theme_palette(bpy.context.preferences)
        target = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        records = []
        for slug, title, widget in widgets:
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
                    color=(0.085, 0.09, 0.095, 1.0)
                )
                # The frame is an actual GPU component, not reference pixels.
                style.draw(
                    0, 0, width, height, (0.12, 0.13, 0.14, 1.0), radius=12, border=1.0
                )
                style.draw(
                    1,
                    height - 60,
                    width - 2,
                    59,
                    (0.16, 0.17, 0.18, 0.8),
                    radius=10,
                    border=0.5,
                )
                style.icon("▾", 30, height - 30, 18, palette["text"])
                blf.size(font, 26)
                blf.color(font, *palette["text"])
                blf.position(font, 66, height - 40, 0)
                blf.draw(font, title)
                widget.paint((18, 18, width - 36, height - 88), font, palette)
                buffer = gpu.state.active_framebuffer_get().read_color(
                    0, 0, width, height, 4, 0, "UBYTE"
                )
                buffer.dimensions = width * height * 4
                png(OUTPUT / f"{slug}.png", width, height, buffer)
                records.append(
                    {
                        "control": title,
                        "file": slug + ".png",
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
            "font": path.name,
            "captures": records,
            "source": "Actual Blender GPUOffScreen, stock theme, library painters; no reference pixels used",
            "acceptance": "Unapproved; Tyler performs visual QA",
        }
    except Exception:
        result = {"passed": False, "error": traceback.format_exc()}
    finally:
        if target is not None:
            target.free()
        if font >= 0:
            blf.unload(str(path))
    (OUTPUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print("BEYOND_UI_CAPTURE", json.dumps(result), flush=True)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1.0)
