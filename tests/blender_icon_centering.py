"""Framebuffer proof of centered source and fallback icons at host scales."""

import bpy, gpu, os, sys, json, traceback, math
from pathlib import Path
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas
from beyond_ui.gpu import icons
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts

OUT = Path(os.environ["BEYOND_UI_TEST_RESULT"]).parent


def run():
    fonts = None
    try:
        fonts = Fonts()
        names = sorted(icons._entries) + ["▾", "‹", "›", "search", "reset", "✓"]
        results = []
        for scale in (1, 1.5, 2):
            canvas = Canvas()
            canvas.panel_layout = True
            # Exact production button painter, including narrow icon-only bounds.
            for start in range(0, len(names), 8):
                row = canvas.row()
                for i, name in enumerate(names[start : start + 8], start):
                    row.button(str(i), "", lambda: None, icon=name, width=22, height=22)
            canvas.arrange(8 * 26 + 12)
            width, height = int(canvas._width * scale), math.ceil(canvas.height * scale)
            off = gpu.types.GPUOffScreen(width, height)
            try:
                with (
                    off.bind(),
                    gpu_state(),
                    gpu.matrix.push_pop(),
                    gpu.matrix.push_pop_projection(),
                ):
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
                    gpu.state.viewport_set(0, 0, width, height)
                    gpu.state.scissor_set(0, 0, width, height)
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0, 0, 0, 1))
                    canvas.paint(
                        (0, 0, width, height), (0, 0, width, height), font=fonts
                    )
                    pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                    pixels.dimensions = width * height * 4
                    raw = bytes(pixels)
                    png(OUT / f"icons-{scale:g}x.png", width, height, raw)
                for control in canvas.controls.values():
                    x, y, w, h = control.rect
                    cx, cy = (x + w / 2) * scale, height - (y + h / 2) * scale
                    points = []
                    for py in range(
                        max(0, int(cy - 8 * scale)),
                        min(height, math.ceil(cy + 8 * scale)),
                    ):
                        for px in range(
                            max(0, int(cx - 8 * scale)),
                            min(width, math.ceil(cx + 8 * scale)),
                        ):
                            offset = (py * width + px) * 4
                            if min(raw[offset : offset + 3]) > 95:
                                points.append((px + 0.5, py + 0.5))
                    assert points, control.options["icon"]
                    actual = tuple(
                        (min(p[i] for p in points) + max(p[i] for p in points)) / 2
                        for i in (0, 1)
                    )
                    error = max(abs(actual[0] - cx), abs(actual[1] - cy))
                    results.append(
                        dict(
                            icon=control.options["icon"],
                            scale=scale,
                            error_pixels=error,
                        )
                    )
                    assert error <= 1.0, results[-1]
            finally:
                off.free()
                canvas.park()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            checks=results,
            max_error_pixels=max(r["error_pixels"] for r in results),
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        if fonts:
            fonts.close()
        Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
            json.dumps(result, indent=2)
        )
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
