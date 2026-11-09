"""Compare popup glyph pixels with/without Blender's native UI text batch."""

import json
import os
from pathlib import Path
import sys
import traceback
from contextlib import nullcontext

import bpy
import gpu
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui.gpu import typography
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.animation import Motion
from menu_motion_batch import configure


def run():
    font = typography.Fonts()
    target = gpu.types.GPUOffScreen(1024, 360)
    try:
        from types import SimpleNamespace
        import blf

        batch, _ = configure()
        motion = SimpleNamespace(tracks={"reveal": True}, strength=1)
        fb_width = 1024
        with (
            target.bind(),
            gpu_state(),
            gpu.matrix.push_pop(),
            gpu.matrix.push_pop_projection(),
        ):
            gpu.state.viewport_set(0, 0, 1024, 360)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(
                Matrix(
                    (
                        (2 / 1024, 0, 0, -1),
                        (0, 2 / 360, 0, -1),
                        (0, 0, 1, 0),
                        (0, 0, 0, 1),
                    )
                )
            )
            fb = gpu.state.active_framebuffer_get()

            def frame(batched, stretch):
                fb.clear(color=(0, 0, 0, 1))
                with batch() if batched else nullcontext():
                    with typography.motion_text(font, motion):
                        with Motion._deformed(
                            (740, 160, 220, 100), (stretch, 1 / stretch), 0
                        ):
                            for handle, pos, label in (
                                (font.title, (756, 216), "Falloff"),
                                (int(font), (756, 184), "Curve options"),
                            ):
                                # Same interleaving as a child draw and its composited
                                # backdrop flush while the outer reveal is still active.
                                with typography.motion_text(font, motion):
                                    typography.flush_text(font)
                                blf.size(handle, 18)
                                blf.position(handle, *pos, 0)
                                blf.color(handle, 1, 1, 1, 1)
                                blf.draw(handle, label)
                pixels = fb.read_color(0, 0, 1024, 360, 4, 0, "UBYTE")
                pixels.dimensions = 1024 * 360 * 4
                return {i for i, v in enumerate(bytes(pixels)[::4]) if v > 96}

            samples = []
            for stretch in (0.86, 1.14, 1.0):
                reference = frame(False, stretch)
                actual = frame(True, stretch)
                assert len(reference) > 200 and actual, (len(reference), len(actual))
                score = len(actual & reference) / len(actual | reference)
                assert score > 0.98, (stretch, score)
                assert all(
                    715 <= i % fb_width < 985 and 140 < i // fb_width < 278
                    for i in actual
                )
                samples.append(
                    {"stretch": stretch, "ink_pixels": len(actual), "overlap": score}
                )
            return samples
    finally:
        target.free()
        font.close()


def check():
    try:
        result = dict(passed=True, phases=run())
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(check, first_interval=0.4)
