"""Enum property menus using retained production glass, motion, fonts and theme."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas, Layout, Theme
from beyond_ui.gpu import glass, skin, style
from beyond_ui.scalar_geometry import slider_parts, switch_rect
from beyond_ui.bindings import Binding
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run

OUT = Path(os.environ["BEYOND_UI_SCALAR_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        from menu_motion_batch import configure

        batch, batch_info = configure()
        ctx = bpy.context
        bpy.types.Scene.scalar_opacity = bpy.props.FloatProperty(
            default=1.0, min=0.0, max=1.0
        )
        bpy.types.Scene.scalar_count = bpy.props.IntProperty(default=6, min=0, max=10)
        bpy.types.Scene.scalar_background = bpy.props.BoolProperty(default=False)
        bpy.types.Scene.scalar_viewport = bpy.props.BoolProperty(default=True)
        bpy.types.Scene.scalar_render = bpy.props.BoolProperty(default=True)
        commits = []
        canvas = Canvas(menu_commit=commits.append)
        ui = Layout(canvas, context=ctx, commit=lambda a, b: commits.append((a, b)))
        ui.title(text="BVT Sliders and Switches")
        opacity = ui.prop(ctx.scene, "scalar_opacity", text="Opacity", slider=True)
        count = ui.prop(ctx.scene, "scalar_count", text="Count", slider=True)
        background = ui.prop(ctx.scene, "scalar_background", text="Background")
        ui.prop(ctx.scene, "scalar_viewport", text="Viewport")
        ui.prop(ctx.scene, "scalar_render", text="Render")
        row = ui.row()
        row.prop(ctx.scene, "scalar_opacity", text="Compact slider", slider=True)
        row.prop(ctx.scene, "scalar_count", text="Compact count", slider=True)
        disabled = ui.row()
        disabled.enabled = False
        disabled.prop(ctx.scene, "scalar_opacity", text="Disabled", slider=True)
        disabled.prop(ctx.scene, "scalar_render", text="Disabled switch")
        color = ui.prop(ctx.scene.world, "color", text="Color")
        for i in range(3):
            ui.label(text="")
        canvas.arrange(560)
        preferences = ctx.preferences
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
                "scalar-layout-fixture", 1, under.texture_color, (0, 0, width, height)
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
                    "scalar-layout-fixture",
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
                    preferences=preferences,
                    backdrop="scalar-layout-fixture",
                )
                if name is None:
                    return
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / (name + ".png"), width, height, bytes(pixels))

            def resources():
                owner = glass._owners["scalar-layout-fixture"]
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
            from beyond_ui.context_menu import Menu, Target
            from beyond_ui.context_fields import property_row
            from beyond_ui.widgets import ColorPicker

            rgba = [(0.2, 0.4, 0.6, 0.75)]
            picker = ColorPicker(
                Binding(lambda: rgba[0], lambda v: rgba.__setitem__(0, v)), linear=False
            )
            picker.motion.clock = lambda: clock[0]
            canvas.open_widget(picker, color, clip)
            render("color-alpha")
            canvas.cancel()

            def open_bool_menu():
                menu = Menu(
                    Target("bools", commit=commits.append),
                    [
                        property_row(ctx.scene, name, text=label)
                        for name, label in [
                            ("scalar_background", "Background"),
                            ("scalar_viewport", "Viewport"),
                            ("scalar_render", "Render"),
                        ]
                    ],
                    (160, 125),
                    clip,
                    context=ctx,
                )
                menu.motion.clock = lambda: clock[0]
                menu.motion.bind((canvas.animation,), canvas._wake_motion)
                canvas.context_menu = menu
                return menu

            menu = open_bool_menu()
            render("boolean-menu")
            canvas.close_context()
            _, (tx, ty, tw), field = slider_parts(opacity.rect)

            def event(kind, x, y, value="PRESS", **kw):
                return canvas.event(
                    NS(type=kind, value=value, **kw), x, y, clip, context=ctx
                )

            event("LEFTMOUSE", field[0] + 10, field[1] + 12)
            event("LEFTMOUSE", field[0] + 10, field[1] + 12, "RELEASE")
            assert canvas.editor is not None
            render("number-entry")
            canvas.cancel()
            # Explicit red reference-theme fixture; never write Blender preferences.
            theme_ui = ctx.preferences.themes[0].user_interface
            names = (
                "wcol_radio",
                "wcol_regular",
                "wcol_tool",
                "wcol_num",
                "wcol_tab",
                "wcol_numslider",
                "wcol_toggle",
            )
            palette_ui = NS(
                **{
                    n: NS(
                        **{
                            k: tuple(getattr(getattr(theme_ui, n), k))
                            for k in ("inner", "inner_sel", "text", "text_sel", "item")
                        }
                    )
                    for n in names
                }
            )
            palette_ui.wcol_numslider.item = (0.95, 0.08, 0.14, 1.0)
            palette_ui.wcol_toggle.inner_sel = (0.85, 0.08, 0.12, 1.0)
            preferences = NS(themes=[NS(user_interface=palette_ui)])
            render("red-reference-theme")
            preferences = ctx.preferences
            before = resources()
            equal = []
            sx, sy, sw, sh = switch_rect(background.rect)
            for frame in range(150):
                clock[0] = frame / 30
                if frame == 3:
                    event("MOUSEMOVE", tx + tw * 0.8, ty, "NOTHING")
                if frame == 6:
                    event("LEFTMOUSE", tx + tw * 0.7, ty)
                if 7 <= frame <= 14:
                    event(
                        "MOUSEMOVE", tx + tw * (0.7 - (frame - 6) * 0.04), ty, "NOTHING"
                    )
                if frame == 15:
                    event("LEFTMOUSE", tx + tw * 0.38, ty, "RELEASE")
                if frame == 23:
                    event("LEFTMOUSE", sx + sw / 2, sy + sh / 2)
                if frame == 24:
                    event("LEFTMOUSE", sx + sw / 2, sy + sh / 2, "RELEASE")
                if frame == 28:
                    event("LEFTMOUSE", sx + sw / 2, sy + sh / 2)
                if frame == 29:
                    event("LEFTMOUSE", sx + sw / 2, sy + sh / 2, "RELEASE")
                if frame == 39:
                    event("LEFTMOUSE", field[0] + 20, field[1] + 12)
                    event("LEFTMOUSE", field[0] + 20, field[1] + 12, "RELEASE")
                if frame == 44:
                    event("TEXTINPUT", field[0], field[1], unicode="0.8")
                if frame == 48:
                    event("RET", field[0], field[1])
                if frame == 58:
                    menu = open_bool_menu()
                    menu.motion.pulse("reveal", 0.12)
                if frame == 80:
                    canvas.cancel()
                if frame == 83:
                    canvas.open_widget(picker, color, clip)
                    canvas._bind_motion(picker.motion, color)
                    picker.motion.pulse("reveal", 0.12)
                if frame in (88, 89, 90, 96, 97, 98):
                    from beyond_ui.widgets.metrics import COLOR

                    part = "hue" if frame < 94 else "alpha"
                    a, b, w, h = COLOR[part + "_track"]
                    px, py = a + w * (0.3 if frame in (88, 96) else 0.6), b + h / 2
                    ox, oy, ow, oh = canvas.overlay["rect"]
                    lx, ly = ox + px * ow / picker.width, oy + py * oh / picker.height
                    kind = "MOUSEMOVE" if frame in (89, 97) else "LEFTMOUSE"
                    state = (
                        "NOTHING"
                        if kind == "MOUSEMOVE"
                        else "RELEASE"
                        if frame in (90, 98)
                        else "PRESS"
                    )
                    event(kind, lx, ly, state)
                if frame == 105:
                    canvas.cancel()
                render(f"frame-{frame:03}")
                with batch():
                    render()
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / f"batch-{frame:03}.png", width, height, bytes(pixels))
                equal.append(
                    (OUT / f"batch-{frame:03}.png").read_bytes()
                    == (OUT / f"frame-{frame:03}.png").read_bytes()
                )
                canvas.advance_animations()
            assert all(equal), [i for i, v in enumerate(equal) if not v]
            assert before == resources(), (before, resources())
            clock[0] = 10
            canvas.cancel()
            canvas.advance_animations()
            render("settled")
            canvas.animation.enabled = False
            render("disabled")
            assert not canvas.advance_animations()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            dimensions=[width, height],
            dpi=dpi,
            theme="Factory Blender active theme; Standard viewport fixture, raw display-space capture",
            timings=timings,
            workload="Shared BVT scalar sliders/switches, compact and disabled rows, numeric entry, boolean menu and alpha picker. Paint: 20 warmups and 100 CPU samples; readback excluded",
            stable_resources=True,
            native_text_batching_equal_frames=len(equal),
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
        glass.release("scalar-layout-fixture")
        if off:
            off.free()
        if under:
            under.free()
        if fonts:
            fonts.close()
        for name in (
            "scalar_opacity",
            "scalar_count",
            "scalar_background",
            "scalar_viewport",
            "scalar_render",
        ):
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
