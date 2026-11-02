"""GPU shader/glass qualification in an isolated window; no native host required."""

import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import bpy
import gpu
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Canvas, Theme
from beyond_ui.gpu import glass
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts
from capture_controls import make_widgets


def run():
    backend = gpu.platform.backend_type_get()
    expected = os.environ.get("BEYOND_UI_EXPECT_BACKEND")
    assert not expected or backend == expected, (backend, expected)
    width, height = 680, 560
    source = gpu.types.GPUOffScreen(width, height, format="RGBA8")
    target = gpu.types.GPUOffScreen(width, height, format="RGBA8")
    font = Fonts()
    key = ("backend-qa", backend)
    texture = source.texture_color
    try:
        with source.bind():
            gpu.state.active_framebuffer_get().clear(color=(0.08, 0.25, 0.5, 1))
        assert glass.prepare_texture(key, 1, texture, (0, 0, width, height)), (
            glass.error
        )
        items, _ = make_widgets()
        canvases = []
        for slug, _, widget in items[:4]:
            canvas = Canvas(Theme(padding=10, palette="REFERENCE"))
            canvas.widget(slug, widget)
            canvas.arrange(width / 2)
            canvases.append(canvas)
        hashes = []
        with (
            target.bind(),
            gpu_state(),
            gpu.matrix.push_pop(),
            gpu.matrix.push_pop_projection(),
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
            for phase in (0.7, 1.0):
                gpu.state.active_framebuffer_get().clear(color=(0.02, 0.03, 0.04, 1))
                assert glass.lens(
                    key,
                    (10, 10, width - 20, height - 20),
                    18,
                    (0.1, 0.12, 0.15, 0.12),
                    phase=phase,
                    stretch=0.03,
                    blur=0.7,
                ), glass._lens_error
                for i, canvas in enumerate(canvases):
                    x = (i % 2) * width / 2
                    y = height - (i // 2 + 1) * height / 2
                    canvas.paint(
                        (x, y, width / 2, canvas.height),
                        (x, y, width / 2, height / 2),
                        font=font,
                    )
                pixels = gpu.state.active_framebuffer_get().read_color(
                    0, 0, width, height, 4, 0, "UBYTE"
                )
                pixels.dimensions = width * height * 4
                raw = bytes(pixels)
                assert len(set(raw)) > 32, "Empty or flat shader output"
                hashes.append(hashlib.sha256(raw).hexdigest())
            counts = (
                glass._owners[key]["productions"],
                glass._owners[key]["allocations"],
            )
            for _ in range(10):
                assert glass.prepare_texture(key, 1, texture, (0, 0, width, height))
                assert glass.lens(
                    key, (10, 10, width - 20, height - 20), 18, (0, 0, 0, 0.1), blur=0.7
                )
            assert counts == (
                glass._owners[key]["productions"],
                glass._owners[key]["allocations"],
            )
        return dict(
            passed=True,
            version=bpy.app.version_string,
            backend=backend,
            renderer=gpu.platform.renderer_get(),
            glass=True,
            retained_resources=True,
            hashes=hashes,
            host_integration=False,
            visual_acceptance=False,
        )
    finally:
        glass.release(key)
        font.close()
        target.free()
        source.free()


def timer():
    try:
        result = run()
    except Exception:
        traceback.print_exc()
        result = dict(passed=False, error=traceback.format_exc())
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print("BEYOND_UI_BACKEND", json.dumps(result))
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
