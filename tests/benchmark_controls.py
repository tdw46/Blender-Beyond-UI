"""Disposable Blender benchmark; timing/readback never enters production paint."""

import bpy, blf, gpu
from pathlib import Path
from mathutils import Matrix
import os, sys, json, time, statistics, traceback

ROOT = Path(os.environ.get("BEYOND_UI_BENCH_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import Binding
from beyond_ui.widgets import CurveMapping, ColorRamp, ColorPicker, DataPicker
from beyond_ui.gpu import style
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.widgets import base


def binding(value):
    return Binding(lambda: value, lambda v: None)


def run():
    target = None
    font = None
    try:
        modern = (ROOT / "beyond_ui/gpu/typography.py").exists()
        if modern:
            from beyond_ui.gpu.typography import Fonts

            font = Fonts()
        else:
            font_path = next(
                (Path(bpy.utils.resource_path("LOCAL")) / "datafiles/fonts").glob(
                    "Inter*.woff2"
                )
            )
            font = blf.load(str(font_path))
        widgets = [
            CurveMapping(
                binding(((0.05, 0.05), (0.5, 0.5), (0.95, 0.95))),
                evaluate=lambda x: x * x * (3 - 2 * x),
                channel=binding(3),
            ),
            ColorRamp(
                binding(
                    (
                        (0.0, (0.0, 0.04, 0.6, 1.0)),
                        (0.5, (0.0, 0.6, 0.9, 1.0)),
                        (1.0, (1.0, 1.0, 1.0, 1.0)),
                    )
                )
            ),
            DataPicker(
                tuple((i, f"Object {i}", "object") for i in range(10000)),
                lambda k: None,
                selected=lambda: 1,
            ),
            ColorPicker(binding((0.2, 0.7, 0.9, 1.0)), linear=False),
        ]
        palette = style.theme_palette(bpy.context.preferences)
        target = gpu.types.GPUOffScreen(1260, 944, format="RGBA8")

        def render():
            for i, widget in enumerate(widgets):
                x, y = (i % 2) * 630, (i // 2) * 472
                if modern:
                    widget.paint((x, y, 630, 472), font, palette)
                else:
                    style.draw(
                        x, y, 630, 472, (0.12, 0.13, 0.14, 1), radius=12, border=1.0
                    )
                    style.draw(
                        x + 1,
                        y + 412,
                        628,
                        59,
                        (0.16, 0.17, 0.18, 0.8),
                        radius=10,
                        border=0.5,
                    )
                    blf.size(font, 26)
                    blf.color(font, *palette["text"])
                    blf.position(font, x + 66, y + 432, 0)
                    blf.draw(font, type(widget).__name__)
                    widget.paint((x + 18, y + 18, 594, 384), font, palette)

        timings = []
        complete = []
        with (
            target.bind(),
            gpu.matrix.push_pop(),
            gpu.matrix.push_pop_projection(),
            gpu_state(),
        ):
            gpu.state.viewport_set(0, 0, 1260, 944)
            gpu.state.scissor_set(0, 0, 1260, 944)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(
                Matrix(
                    (
                        (2 / 1260, 0, 0, -1),
                        (0, 2 / 944, 0, -1),
                        (0, 0, 1, 0),
                        (0, 0, 0, 1),
                    )
                )
            )
            fb = gpu.state.active_framebuffer_get()
            for i in range(120):
                fb.clear(color=(0.09, 0.10, 0.11, 1))
                start = time.perf_counter()
                render()
                submitted = time.perf_counter()
                fb.read_color(0, 0, 1, 1, 4, 0, "UBYTE")
                end = time.perf_counter()
                if i == 19:
                    cache_before = {
                        key: id(value[1]) for key, value in base._LINE_CACHE.items()
                    }
                    textures_before = tuple(id(t) for t in widgets[1]._textures)
                if i >= 20:
                    timings.append((submitted - start) * 1000)
                    complete.append((end - start) * 1000)
            cache_after = {key: id(value[1]) for key, value in base._LINE_CACHE.items()}
            stable = cache_before == cache_after and textures_before == tuple(
                id(t) for t in widgets[1]._textures
            )
            assert stable, "Warm frames rebuilt retained geometry or ramp textures"

        def stats(values):
            values = sorted(values)
            return {
                "p50_ms": statistics.median(values),
                "p95_ms": values[int(len(values) * 0.95) - 1],
                "max_ms": max(values),
            }

        result = {
            "passed": True,
            "runtime": bpy.app.version_string,
            "build": bpy.app.build_hash.decode(),
            "backend": gpu.platform.backend_type_get(),
            "device": gpu.platform.renderer_get(),
            "root": str(ROOT),
            "workload": "4 visible 630x472 compound cards in 1260x944; picker has 10000 rows; 20 warmup + 100 measured frames; tint-only backdrop",
            "cpu_submission": stats(timings),
            "submission_plus_one_pixel_sync_readback": stats(complete),
            "retained_line_batches": len(cache_after),
            "warm_resources_unchanged": stable,
            "note": "Sync readback is benchmark-only. These figures do not measure live input latency, shared blur, idle redraws, or source extension performance.",
        }
    except Exception:
        result = {"passed": False, "error": traceback.format_exc()}
    finally:
        if target:
            target.free()
        if font is not None:
            if hasattr(font, "close"):
                font.close()
            else:
                blf.unload(str(font_path))
    Path(os.environ["BEYOND_UI_BENCH_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("BEYOND_UI_BENCHMARK", json.dumps(result), flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=1.0)
