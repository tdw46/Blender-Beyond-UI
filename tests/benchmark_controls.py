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
        next_set = os.environ.get("BEYOND_UI_BENCH_SET") == "next"
        color_reads = [0]
        if next_set:
            sys.path.insert(0, str(Path(__file__).parent))
            from next_fixtures import widgets as next_widgets
            from beyond_ui.gpu import progress as progress_gpu

            widgets = [w for _, _, w in next_widgets()]
            source = widgets[0].source
            original_color = source.color

            def counted_color(index):
                color_reads[0] += 1
                return original_color(index % 18)

            source.count = lambda: 10000
            source.color = counted_color

        def textures():
            return tuple(id(t) for w in widgets for t in getattr(w, "_textures", ()))

        palette = style.theme_palette(bpy.context.preferences)
        target = gpu.types.GPUOffScreen(1260, 944, format="RGBA8")

        scroll_mode = os.environ.get("BEYOND_UI_BENCH_SCROLL") == "1"
        motion_mode = os.environ.get("BEYOND_UI_BENCH_MOTION", "rest")
        motion_time = [0.0]
        if motion_mode == "active":
            for widget in widgets:
                widget.motion.clock = lambda: motion_time[0]
                widget.motion.pulse("reveal", 0.14)
            motion_time[0] = 0.08

        def render():
            for i, widget in enumerate(widgets):
                x, y = (i % 2) * 630, (i // 2) * 472
                if modern:
                    rect = (x, y, 630, widget.height if next_set else 472)
                    if motion_mode == "active":
                        with widget.motion.deform("reveal", rect):
                            widget.paint(rect, font, palette)
                    else:
                        widget.paint(rect, font, palette)
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
                if scroll_mode:
                    widgets[2].rows.scroll(1.25, 206)
                if next_set:
                    widgets[2].factor = widgets[3].factor = i / 119
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
                    textures_before = textures()
                    ring_before = id(progress_gpu._batch) if next_set else None
                if i >= 20:
                    timings.append((submitted - start) * 1000)
                    complete.append((end - start) * 1000)
            cache_after = {key: id(value[1]) for key, value in base._LINE_CACHE.items()}
            stable = cache_before == cache_after and textures_before == textures()
            if next_set:
                stable = stable and ring_before == id(progress_gpu._batch)
                assert color_reads[0] == 120 * 19, color_reads[0]
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
            "visible_palette_color_reads_per_frame": color_reads[0] / 120
            if next_set
            else None,
            "progress_changes_each_frame": next_set,
            "workload": "4 next-batch cards at 630 logical width; 10000 palette colors; progress advances every frame; 20 warmup + 100 measured; tint-only"
            if next_set
            else "4 visible 630x472 compound cards in 1260x944; picker has 10000 rows; 20 warmup + 100 measured frames; tint-only backdrop",
            "cpu_submission": stats(timings),
            "submission_plus_one_pixel_sync_readback": stats(complete),
            "retained_line_batches": len(cache_after),
            "warm_resources_unchanged": stable,
            "motion_mode": motion_mode,
            "scrolls_each_frame": scroll_mode,
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
