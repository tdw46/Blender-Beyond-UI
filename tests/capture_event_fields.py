"""Actual event-field rendering using retained production BVT glass and fonts."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas, Layout, Theme
from beyond_ui.gpu import glass, skin
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run

OUT = Path(os.environ["BEYOND_UI_EVENT_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        ctx = bpy.context
        config = ctx.window_manager.keyconfigs.new("Event rendering fixture")
        km = config.keymaps.new("Event rendering fixture", space_type="EMPTY")
        item = km.keymap_items.new("wm.context_toggle", "F5", "PRESS", ctrl=True)
        canvas = Canvas(Theme(palette="REFERENCE"))
        ui = Layout(canvas, context=ctx)
        ui.title(text="Event Properties")
        full = ui.prop(item, "type", full_event=True, text="Shortcut")
        ui.prop(item, "type", event=True, text="Event key")
        for text in (
            "Existing KeyMapItem",
            "Keyboard, mouse and held-key capture",
            "Right-click for property actions",
        ):
            ui.label(text=text)
        for i in range(9):
            ui.label(text="")
        canvas.arrange(560)
        width, height = 640, 560
        clip = (0, 0, 560, 520)
        fonts = Fonts()
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
                    (0, 0, 260, height), (0.16, 0.28, 0.36, 1), radius=0, border=0
                )
                skin.draw(
                    (360, 0, 280, height), (0.30, 0.20, 0.15, 1), radius=0, border=0
                )
                for row in range(11):
                    text_run(
                        face(fonts, "body"),
                        f"Underlying UI text {row:02}    0.750",
                        14,
                        (0.85, 0.88, 0.91, 1),
                        (55, 44 + row * 42),
                        ((0, 0, width, height),),
                    )
            assert glass.prepare_texture(
                "event-fixture", 1, under.texture_color, (0, 0, width, height)
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
                canvas.paint(
                    (40, height - 20 - canvas.height, 560, canvas.height),
                    (40, 20, 560, 520),
                    font=fonts,
                    preferences=ctx.preferences,
                    backdrop="event-fixture",
                )
                if name is None:
                    return
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / (name + ".png"), width, height, bytes(pixels))

            def resources():
                owner = glass._owners["event-fixture"]
                return dict(
                    productions=owner["productions"],
                    blur=owner["strong_productions"],
                    offscreens=owner["allocations"],
                    layout=canvas.layout_count,
                )

            render("rest")
            for _ in range(20):
                render()
            samples = []
            for _ in range(100):
                start = time.perf_counter()
                render()
                samples.append((time.perf_counter() - start) * 1000)
            timings = dict(
                median_ms=statistics.median(samples),
                p95_ms=sorted(samples)[94],
                max_ms=max(samples),
            )
            x, y, w, h = full.rect

            # Warm the capture/menu geometry once before testing stable resources.
            def open_field():
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    x + 40,
                    y + 10,
                    clip,
                    context=ctx,
                )
                assert canvas.context_menu is not None, canvas.menu_error
                canvas.context_menu.motion.clock = lambda: clock[0]
                canvas.context_menu.motion.clear()

            open_field()
            render("modes")
            canvas.context_menu.choose(1, ctx)
            render("capture")
            assert canvas.context_menu.glass_ready
            canvas.close_context()
            for c in canvas.controls.values():
                c.motion.clear()
            before = resources()
            for frame in range(90):
                clock[0] = frame / 30
                if frame == 3:
                    canvas._motion_input(
                        NS(type="MOUSEMOVE", value="NOTHING"), x + 40, y + 10, clip
                    )
                if frame == 12:
                    open_field()
                if frame == 30:
                    canvas.context_menu.choose(1, ctx)
                if frame == 65:
                    canvas.event(
                        NS(type="F8", value="PRESS", ctrl=True, shift=True),
                        x + 40,
                        y + 10,
                        clip,
                        context=ctx,
                    )
                    assert item.type == "F8", canvas.menu_error
                if frame == 75:
                    canvas.open_context(full, x + 40, y + 10, clip, context=ctx)
                    canvas.context_menu.motion.clock = lambda: clock[0]
                    canvas.context_menu.motion.clear()
                render(f"frame-{frame:03}")
                canvas.advance_animations()
            render("context")
            assert resources() == before
            canvas.close_context()
            canvas.animation.enabled = False
            assert not canvas.advance_animations()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            dimensions=[width, height],
            theme="REFERENCE",
            timings=timings,
            workload="Two event fields, 20 warmups and 100 CPU paint submission samples; framebuffer readback excluded",
            stable_resources=True,
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
        glass.release("event-fixture")
        if off:
            off.free()
        if under:
            under.free()
        if fonts:
            fonts.close()
        if config:
            bpy.context.window_manager.keyconfigs.remove(config)
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("EVENT_CAPTURE", result.get("passed"), result.get("error", ""))
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )
    return None


bpy.app.timers.register(run, first_interval=1)
