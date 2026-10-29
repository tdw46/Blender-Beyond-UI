"""Enum property menus using retained production glass, motion, fonts and theme."""

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

OUT = Path(os.environ["BEYOND_UI_ENUM_FOLLOWUP_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        from menu_motion_batch import configure

        batch, batch_info = configure()
        ctx = bpy.context
        items = [
            ("A", "Alpha", "First choice", 1),
            ("B", "Beta", "Second choice", 2),
            ("C", "Gamma", "Third choice", 4),
        ]
        items = [
            ("", "Main", "Main choices"),
            items[0],
            None,
            ("", "Extras", "Additional choices"),
            *items[1:],
        ]
        bpy.types.Scene.enum_capture = bpy.props.EnumProperty(items=items, default="A")
        bpy.types.Scene.enum_flags_capture = bpy.props.EnumProperty(
            items=items, options={"ENUM_FLAG"}, default={"A"}
        )
        bpy.types.Scene.enum_long_capture = bpy.props.EnumProperty(
            items=[(f"I{i}", f"Choice {i:03}", f"Description {i}") for i in range(200)]
        )
        commits = []
        canvas = Canvas(menu_commit=commits.append)
        ui = Layout(canvas, context=ctx, commit=lambda a, b: commits.append((a, b)))
        ui.title(text="Enum Properties")
        full = ui.prop(ctx.scene, "enum_capture", text="Mode")
        flags = ui.prop_menu_enum(ctx.scene, "enum_flags_capture", text="Channels")
        long = ui.prop_menu_enum(ctx.scene, "enum_long_capture", text="Long list")
        ui.title(text="Expanded choices")
        ui.props_enum(ctx.scene, "enum_capture")
        ui.prop(ctx.scene, "enum_flags_capture", text="Flag strip")
        ui.label(text="Shift adds or removes flags in the strip")
        for i in range(8):
            ui.label(text="")
        canvas.arrange(560)
        dpi = float(os.environ.get("BEYOND_UI_CAPTURE_DPI", "1"))
        width, height = int(640 * dpi), int(560 * dpi)
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
                        560 * dpi,
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
                        560 * dpi,
                        canvas.height * dpi,
                    ),
                    (40 * dpi, 20 * dpi, 560 * dpi, 520 * dpi),
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
                    skin_shader=id(skin._shader),
                    skin_batch=id(skin._batch),
                    glass_batches={
                        str(k): id(v) for k, v in glass._lens_batches.items()
                    },
                )

            def open_field(control=full):
                canvas.cancel()
                x, y, w, h = control.rect
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    x + 40,
                    y + 10,
                    clip,
                    context=ctx,
                )
                menu = canvas.context_menu
                assert menu is not None, canvas.menu_error
                menu.motion.clock = lambda: clock[0]
                menu.motion.clear()
                return menu

            render("rest")
            timings = {}

            def benchmark(name):
                for _ in range(20):
                    render()
                samples = []
                for _ in range(100):
                    start = time.perf_counter()
                    render()
                    samples.append((time.perf_counter() - start) * 1000)
                timings[name] = dict(
                    median_ms=statistics.median(samples),
                    p95_ms=sorted(samples)[94],
                    max_ms=max(samples),
                )

            benchmark("closed_fields")
            menu = open_field()
            render("scalar")
            benchmark("open_scalar")
            menu = open_field(flags)
            render("flags")
            menu = open_field(long)
            menu.event(NS(type="END", value="PRESS"), 20, 30, ctx)
            render("long")
            benchmark("open_200_rows")
            canvas.cancel()
            x, y, w, h = full.rect
            canvas.open_context(full, x, y, clip, context=ctx)
            canvas.context_menu.motion.clock = lambda: clock[0]
            canvas.context_menu.motion.clear()
            render("field-context")
            canvas.close_context()
            before = resources()
            batched_equal = []
            for frame in range(100):
                clock[0] = frame / 30
                if frame == 4:
                    menu = open_field()
                    menu.motion.pulse("reveal", 0.12)
                if frame == 22:
                    menu.choose(
                        next(
                            i
                            for i, row in enumerate(menu.page.rows)
                            if row.key == "enum:B"
                        ),
                        ctx,
                    )
                    assert ctx.scene.enum_capture == "B"
                if frame == 30:
                    menu = open_field(flags)
                    menu.motion.pulse("reveal", 0.12)
                if frame == 46:
                    menu.choose(
                        next(
                            i
                            for i, row in enumerate(menu.page.rows)
                            if row.key == "enum:B"
                        ),
                        ctx,
                    )
                    assert ctx.scene.enum_flags_capture == {"A", "B"}
                if frame == 55:
                    menu = open_field(long)
                    menu.motion.pulse("reveal", 0.12)
                    menu.event(NS(type="END", value="PRESS"), 20, 30, ctx)
                if frame == 70:
                    menu.event(NS(type="RET", value="PRESS"), 20, 30, ctx)
                    assert ctx.scene.enum_long_capture == "I199"
                if frame == 72:
                    canvas.cancel()
                    strip = [c for c in canvas.controls.values() if c.kind == "button"][
                        -3:
                    ]
                    button = strip[-1]
                    x, y, w, h = button.rect
                    canvas.event(
                        NS(type="LEFTMOUSE", value="PRESS", shift=True),
                        x + w / 2,
                        y + h / 2,
                        clip,
                        context=ctx,
                    )
                    assert ctx.scene.enum_flags_capture == {"A", "B", "C"}
                if frame == 75:
                    canvas.cancel()
                    expanded = next(
                        c for c in canvas.controls.values() if c.kind == "button"
                    )
                    x, y, w, h = expanded.rect
                    canvas.open_context(expanded, x, y, clip, context=ctx)
                    canvas.context_menu.motion.clock = lambda: clock[0]
                    canvas.context_menu.motion.clear()
                    canvas.context_menu.motion.pulse("reveal", 0.12)
                if frame == 95:
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
            workload="Grouped scalar/flag menus, a 200-choice menu, grouped props_enum and a Shift-aware expanded flag strip. Paint: 20 warmups, 100 CPU submission samples. Framebuffer readback excluded",
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
        for name in ("enum_capture", "enum_flags_capture", "enum_long_capture"):
            if hasattr(bpy.types.Scene, name):
                delattr(bpy.types.Scene, name)
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
