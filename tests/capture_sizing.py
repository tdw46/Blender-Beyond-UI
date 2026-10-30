"""Responsive layouts using retained production glass, motion, fonts and theme."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas, Layout, Theme
from beyond_ui.gpu import glass, skin, style
from sizing_fixture import build
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run

OUT = Path(os.environ["BEYOND_UI_FLOW_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        from menu_motion_batch import configure

        batch, batch_info = configure()
        ctx = bpy.context
        ui, toggles, groups, calls = build(ctx)
        canvas = ui.canvas
        full = toggles[0]
        fonts = Fonts()
        from beyond_ui.gpu.paint import measure

        canvas.set_text_measure(
            lambda text, role: measure(
                face(fonts, role),
                canvas.theme.font_size * (12 / 11 if role == "title" else 1),
                text,
            )[0],
            "fixture-font",
        )
        canvas.arrange(560)
        dpi = float(os.environ.get("BEYOND_UI_CAPTURE_DPI", "1"))
        width, height = int(980 * dpi), int(760 * dpi)
        clip = (0, 0, 560, 720)
        off = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        under = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        clock = [0.0]
        for c in canvas.controls.values():
            c.motion.clock = lambda: clock[0]
        with (
            off.bind(),
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
            fb = gpu.state.active_framebuffer_get()
            with under.bind():
                gpu.state.viewport_set(0, 0, width, height)
                gpu.state.scissor_set(0, 0, width, height)
                gpu.state.active_framebuffer_get().clear(color=(0.1, 0.13, 0.16, 1))
                skin.draw(
                    (0, 0, 260 * dpi, height), (0.16, 0.28, 0.36, 1), radius=0, border=0
                )
                skin.draw(
                    (360 * dpi, 0, 280 * dpi, height),
                    (0.30, 0.20, 0.15, 1),
                    radius=0,
                    border=0,
                )
                for row in range(11):
                    text_run(
                        face(fonts, "body"),
                        f"Underlying UI text {row:02}    0.750",
                        14 * dpi,
                        (0.85, 0.88, 0.91, 1),
                        (55 * dpi, (44 + row * 42) * dpi),
                        ((0, 0, width, height),),
                    )
            assert glass.prepare_texture(
                "enum-property-fixture", 1, under.texture_color, (0, 0, width, height)
            ), glass.error

            def render(name=None):
                fb.clear(color=(0.09, 0.1, 0.11, 1))
                glass._draw(
                    under.texture_color,
                    (0, 0, width, height),
                    (0, 0, 1, 1),
                    (0, 0, 2, 0),
                    (0, 0, 0, 0),
                    gpu.matrix.get_projection_matrix()
                    @ gpu.matrix.get_model_view_matrix(),
                )
                # PanelHost draws the shared base glass before the canvas tint.
                # Reproduce that host pass using the fixture's retained backdrop.
                assert glass.lens(
                    "enum-property-fixture",
                    (
                        40 * dpi,
                        height - (20 + canvas.height) * dpi,
                        canvas._width * dpi,
                        canvas.height * dpi,
                    ),
                    canvas.theme.radius * dpi,
                    (0, 0, 0, 0),
                    blur=0.3,
                )
                canvas.paint(
                    (
                        40 * dpi,
                        height - (20 + canvas.height) * dpi,
                        canvas._width * dpi,
                        canvas.height * dpi,
                    ),
                    (40 * dpi, 20 * dpi, canvas._width * dpi, 720 * dpi),
                    font=fonts,
                    preferences=ctx.preferences,
                    backdrop="enum-property-fixture",
                )
                if name is None:
                    return
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / (name + ".png"), width, height, bytes(pixels))

            def resources():
                owner = glass._owners["enum-property-fixture"]
                return dict(
                    productions=owner["productions"],
                    blur=owner["strong_productions"],
                    offscreens=owner["allocations"],
                    layout=canvas.layout_count,
                    font_handles=[int(fonts), fonts.title],
                    style_shader=id(style._shader),
                    style_batch=id(style._batch),
                    skin_shader=id(skin._shader),
                    skin_batch=id(skin._batch),
                    glass_batches={
                        str(k): id(v) for k, v in glass._lens_batches.items()
                    },
                )

            eligibility_reads = [0]

            def eligible():
                eligibility_reads[0] += 1
                return True

            full.options["enabled"] = eligible
            render("rest")
            reads_before = eligibility_reads[0]
            render()
            assert eligibility_reads[0] == reads_before + 1
            samples = []
            for _ in range(20):
                render()
            before = resources()
            for _ in range(100):
                started = time.perf_counter()
                render()
                samples.append((time.perf_counter() - started) * 1000)
            assert resources() == before
            timings = dict(
                median_ms=statistics.median(samples),
                p95_ms=sorted(samples)[94],
                max_ms=max(samples),
            )
            canvas.arrange(900)
            render("wide")
            canvas.arrange(320)
            render("narrow")
            canvas.arrange(560)
            groups["tall"].scale_y = 2
            groups["fixed"].ui_units_x = 6
            canvas.arrange(560)
            render("resized")
            groups["tall"].scale_y = 1.5
            groups["fixed"].ui_units_x = 8
            canvas.arrange(560)
            ui.alignment = "RIGHT"
            canvas.arrange(560)
            render("aligned")
            ui.alignment = "EXPAND"
            canvas.arrange(560)
            x, y, w, h = full.rect
            assert canvas.open_context(full, x + w / 2, y + h / 2, clip, context=ctx), (
                canvas.menu_error
            )
            canvas.context_menu.motion.clock = lambda: clock[0]
            canvas.context_menu.motion.clear()
            render("owner-menu")
            canvas.cancel()
            render()
            before = resources()
            batched_equal = []
            for frame in range(60):
                clock[0] = frame / 30
                x, y, w, h = full.rect
                if frame == 3:
                    canvas.event(
                        NS(type="MOUSEMOVE", value="NOTHING"),
                        x + w - 18,
                        y + h / 2,
                        clip,
                        context=ctx,
                    )
                if frame == 6:
                    canvas.event(
                        NS(type="LEFTMOUSE", value="PRESS"),
                        x + w - 18,
                        y + h / 2,
                        clip,
                        context=ctx,
                    )
                if frame == 8:
                    canvas.event(
                        NS(type="LEFTMOUSE", value="RELEASE"),
                        x + w - 18,
                        y + h / 2,
                        clip,
                        context=ctx,
                    )
                if frame == 20:
                    canvas.open_context(full, x + w / 2, y + h / 2, clip, context=ctx)
                    canvas.context_menu.motion.clock = lambda: clock[0]
                    canvas.context_menu.motion.clear()
                    canvas.context_menu.motion.pulse("reveal", 0.12)
                if frame == 45:
                    canvas.cancel()
                render(f"frame-{frame:03}")
                with batch():
                    render()
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / f"batch-{frame:03}.png", width, height, bytes(pixels))
                batched_equal.append(
                    (OUT / f"batch-{frame:03}.png").read_bytes()
                    == (OUT / f"frame-{frame:03}.png").read_bytes()
                )
                canvas.advance_animations()
            assert all(batched_equal), [i for i, v in enumerate(batched_equal) if not v]
            assert resources() == before, (resources(), before)
            canvas.cancel()
            canvas.animation.enabled = False
            assert not canvas.advance_animations()
            render("disabled")
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            dimensions=[width, height],
            dpi=dpi,
            theme="Factory Blender active theme; Standard viewport fixture, raw display-space capture",
            timings=timings,
            workload="Relative-width numerics, taller switches, fixed-width/height fields, proportional compound control. 20 warmups and 100 CPU paint samples; readback excluded.",
            fixture_helper_sha256=hashlib.sha256(
                (ROOT / "tests/sizing_fixture.py").read_bytes()
            ).hexdigest(),
            stable_resources=True,
            native_text_batching_equal_frames=len(batched_equal),
            batch_admission=batch_info,
            retained_resources=before,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            exact_match=False,
            acceptance="Actual production frames; existing shared field/menu styling. Generated-reference and motion acceptance remain open.",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        glass.release("enum-property-fixture")
        if off:
            off.free()
        if under:
            under.free()
        if fonts:
            fonts.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("ENUM_CAPTURE", result.get("passed"), result.get("error", ""))
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )
    return None


bpy.app.timers.register(run, first_interval=1)
