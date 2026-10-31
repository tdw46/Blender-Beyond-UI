"""Actual CamKeys authored controls, rendered with production GPU glass in a disposable window."""

import bpy, gpu, os, sys, json, traceback, importlib.util, ctypes, time, statistics, hashlib
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from menu_motion_batch import configure

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"]).resolve()
assert source.name == "CamKeys-beyond-ui"
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
from camkeys_qa._vendor.beyond_ui import Layout
from camkeys_qa._vendor.beyond_ui.gpu import glass, skin
from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state, measure
from camkeys_qa._vendor.beyond_ui.gpu.typography import Fonts, face
from camkeys_qa._vendor.beyond_ui.gpu.menus import text_run
from camkeys_qa._vendor.beyond_ui.list_source import UnsafeListIdentity

OUT = Path(os.environ["BEYOND_UI_CAMKEYS_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)
clock = [0.0]
canvases = []


def bind(canvas):
    for c in canvas.controls.values():
        c.motion.clock = lambda: clock[0]
        widget = c.options.get("widget")
        if widget:
            widget.motion.clock = lambda: clock[0]
            if hasattr(widget, "all_children"):
                for child, _, _ in widget.all_children():
                    bind(child)
    if canvas.overlay:
        widget = canvas.overlay["widget"]
        widget.motion.clock = lambda: clock[0]
        if hasattr(widget, "canvas"):
            bind(widget.canvas)
    menu = canvas.active_menu()
    if menu:
        menu.motion.clock = lambda: clock[0]


def run():
    off = under = fonts = None
    result = {}
    try:
        addon.register()
        bpy.context.window_manager.EnableCamKeys = False
        batch, batch_info = configure()
        window = bpy.context.window
        area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        with bpy.context.temp_override(window=window, area=area, region=region):
            ctx = bpy.context
            scene = ctx.scene
            # Real consumer data and UIList classes, with recognizable demo names.
            for name in (
                "Hero mesh",
                "Hair strands",
                "Jacket folds",
                "Eyes",
                "Accessories",
                "Shoes",
            ):
                obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
                scene.collection.objects.link(obj)
                item = scene.mesh_object_items.add()
                item.object = obj
                item.name = name
            scene.mesh_object_items_index = 0
            ids = addon.__beyond_ui_integration__.list_ids
            try:
                ids.prepare(scene, "mesh_object_items")
            except UnsafeListIdentity:
                ids.flush()
            fonts = Fonts()
            dpi = float(os.environ.get("BEYOND_UI_CAPTURE_DPI", "2"))
            W, H = 640, 760
            width, height = round(W * dpi), round(H * dpi)
            clip = (0, 0, 560, 720)
            off = gpu.types.GPUOffScreen(width, height, format="RGBA8")
            under = gpu.types.GPUOffScreen(width, height, format="RGBA8")

            def make(title):
                ui = Layout(
                    context=ctx, **addon.__beyond_ui_integration__.ui.layout_options
                )
                ui.title(text=title)
                canvas = ui.canvas
                canvases.append(canvas)
                canvas.set_text_measure(
                    lambda t, r: measure(
                        face(fonts, r),
                        canvas.theme.font_size * (12 / 11 if r == "title" else 1),
                        t,
                    )[0],
                    "camkeys-font",
                )
                return ui

            ui = make("CamKeys · Tracked objects")
            ui.template_list(
                "CAMKEYS_UL_mesh_object_items",
                "",
                scene,
                "mesh_object_items",
                scene,
                "mesh_object_items_index",
                rows=4,
            )
            canvas = ui.canvas
            canvas.arrange(560)
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
                    gpu.state.active_framebuffer_get().clear(
                        color=(0.10, 0.13, 0.16, 1)
                    )
                    skin.draw(
                        (0, 0, 260 * dpi, height),
                        (0.16, 0.28, 0.36, 1),
                        radius=0,
                        border=0,
                    )
                    skin.draw(
                        (360 * dpi, 0, 280 * dpi, height),
                        (0.30, 0.20, 0.15, 1),
                        radius=0,
                        border=0,
                    )
                    for row in range(17):
                        text_run(
                            face(fonts, "body"),
                            f"Underlying controls {row:02}   0.750",
                            14 * dpi,
                            (0.85, 0.88, 0.91, 1),
                            (50 * dpi, (30 + row * 43) * dpi),
                            ((0, 0, width, height),),
                        )
                assert glass.prepare_texture(
                    "camkeys-qa", 1, under.texture_color, (0, 0, width, height)
                ), glass.error

                def render(name=None, preferences=None):
                    bind(canvas)
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
                    rect = (
                        40 * dpi,
                        height - (20 + canvas.height) * dpi,
                        canvas._width * dpi,
                        canvas.height * dpi,
                    )
                    assert glass.lens(
                        "camkeys-qa",
                        rect,
                        canvas.theme.radius * dpi,
                        (0, 0, 0, 0),
                        blur=0.3,
                    )
                    with batch():
                        canvas.paint(
                            rect,
                            (40 * dpi, 20 * dpi, 560 * dpi, 720 * dpi),
                            font=fonts,
                            preferences=preferences or ctx.preferences,
                            backdrop="camkeys-qa",
                        )
                    if name:
                        pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                        pixels.dimensions = width * height * 4
                        png(OUT / (name + ".png"), width, height, bytes(pixels))

                control = next(
                    c for c in canvas.controls.values() if c.kind == "widget"
                )
                widget = control.options["widget"]
                for child, _, _ in widget.all_children():
                    assert all(
                        not c.label
                        for c in child.controls.values()
                        if c.kind in {"toggle", "pointer"}
                    )
                render("lists-rest")
                for frame in range(90):
                    clock[0] = frame / 30
                    if frame == 10:
                        widget.source.select(widget.source.items[1])
                        widget.refresh()
                        canvas.invalidate()
                        canvas.arrange(560)
                    if frame in (30, 34):
                        assert widget.event(
                            NS(type="WHEELDOWNMOUSE", value="PRESS"), 20, 20
                        )
                        assert {item.index for item, _ in widget.visible()} == set(
                            widget.row_map
                        )
                    if frame == 45:
                        x, y, w, h = control.rect
                        assert canvas.open_context(
                            control, x + 45, y + 35, clip, context=ctx
                        ), canvas.menu_error
                        bind(canvas)
                        canvas.active_menu().motion.clear()
                        canvas.active_menu().motion.pulse("reveal", 0.12)
                    if frame == 70:
                        render("lists-context")
                    if frame == 82:
                        canvas.close_context()
                    render(f"lists-{frame:03}")
                    canvas.advance_animations()
                canvas.cancel()
                # Actual registered CamKeys popover body, including presets and export/import.
                item = scene.mesh_object_items[0]
                item.auto_fov_multi_falloff_type = "CUSTOM"
                ui = make("CamKeys · Brush falloff")
                ui.context_pointer_set("camkeys_falloff_owner", item)
                ui.popover(panel="CAMKEYS_PT_falloff_popover", text="Mesh falloff")
                canvas = ui.canvas
                canvas.arrange(560)
                button = next(
                    c for c in canvas.controls.values() if c.options.get("panel_model")
                )
                assert canvas.open_panel(button, clip, ctx), canvas.menu_error
                popup = canvas.overlay["widget"]
                child = popup.canvas
                cc = next(
                    c
                    for c in child.controls.values()
                    if c.kind == "widget"
                    and getattr(c.options["widget"], "brush", False)
                )
                curve = cc.options["widget"]
                bind(canvas)
                popup.motion.clear()
                clock[0] = 5
                render("brush-rest")
                assert not any(
                    c.options.get("text_role") == "title"
                    for c in child.controls.values()
                )
                preset_buttons = [
                    c
                    for c in child.controls.values()
                    if c.options.get("icon", "").endswith("CURVE")
                ]
                assert len(preset_buttons) == 6 and all(
                    not c.label for c in preset_buttons
                )
                from camkeys_qa._vendor.beyond_ui.gpu import style

                from camkeys_qa._vendor.beyond_ui.gpu import icons

                assert all(c.options["icon"] in icons._entries for c in preset_buttons)
                initial_points = curve.binding.read()

                def curve_event(kind, px, py, value="PRESS"):
                    a, b, w, h = cc.rect
                    child.event(
                        NS(type=kind, value=value),
                        a + px * w / curve.width,
                        b + py * h / curve.height,
                        popup.clip,
                        context=ctx,
                    )

                for frame in range(105):
                    clock[0] = 5 + frame / 30
                    if frame == 0:
                        popup.motion.pulse("reveal", 0.12)
                    a, b, w, h = curve.graph
                    if frame == 22:
                        point = curve.binding.read()[3]
                        curve_event(
                            "LEFTMOUSE", a + point[0] * w, b + (1 - point[1]) * h
                        )
                    if 23 <= frame <= 42:
                        curve_event(
                            "MOUSEMOVE",
                            a + (frame - 22) / 20 * 0.23 * w,
                            b + (0.15 + (frame - 22) / 20 * 0.25) * h,
                            "NOTHING",
                        )
                    if frame == 43:
                        curve_event("LEFTMOUSE", a + 0.23 * w, b + 0.4 * h, "RELEASE")
                    if frame == 50:
                        assert curve.binding.read() != initial_points, (
                            "No curve drag captured",
                            child.menu_error,
                            cc.rect,
                            popup.clip,
                        )
                    if frame == 53:
                        from camkeys_qa._vendor.beyond_ui.widgets.metrics import CURVE

                        x, y, rw, rh = CURVE["fields"][2]
                        a0, b0, cw, ch = cc.rect
                        assert child.open_context(
                            cc,
                            a0 + (x + rw / 2) * cw / curve.width,
                            b0 + (y + rh / 2) * ch / curve.height,
                            popup.clip,
                            context=ctx,
                        ), child.menu_error
                        bind(canvas)
                        child.active_menu().motion.clear()
                        child.active_menu().motion.pulse("reveal", 0.12)
                    if frame == 78:
                        render("brush-context")
                    if frame == 92:
                        child.close_context()
                    render(f"brush-{frame:03}")
                    canvas.advance_animations()
                # Theme fixtures use the same active-theme extraction path, no production overrides.
                from capture_core_extra import NS as ThemeNS

                theme = ctx.preferences.themes[0].user_interface
                for label, fill, accent, ink in [
                    (
                        "light",
                        (0.8, 0.82, 0.85, 1),
                        (0.12, 0.34, 0.72, 1),
                        (0.06, 0.07, 0.09),
                    ),
                    (
                        "purple",
                        (0.15, 0.11, 0.19, 1),
                        (0.66, 0.24, 0.78, 1),
                        (0.94, 0.89, 0.98),
                    ),
                ]:
                    theme_ui = NS(wcol_state=theme.wcol_state)
                    for role in (
                        "wcol_regular",
                        "wcol_radio",
                        "wcol_tool",
                        "wcol_num",
                        "wcol_tab",
                        "wcol_numslider",
                        "wcol_toggle",
                    ):
                        setattr(
                            theme_ui,
                            role,
                            NS(
                                inner=fill,
                                inner_sel=accent,
                                text=ink,
                                text_sel=(1, 1, 1),
                                item=accent,
                            ),
                        )
                    render(
                        "brush-theme-" + label, NS(themes=[NS(user_interface=theme_ui)])
                    )
                for label, panel, prop in [
                    (
                        "distance",
                        "CAMKEYS_PT_distance_falloff_popover",
                        "auto_fov_falloff_type",
                    ),
                    (
                        "flatten",
                        "CAMKEYS_PT_flatten_falloff_popover",
                        "auto_fov_flatten_falloff_type",
                    ),
                ]:
                    canvas.cancel()
                    setattr(item, prop, "CUSTOM")
                    ui = make("CamKeys · " + label.title() + " falloff")
                    ui.context_pointer_set("camkeys_falloff_owner", item)
                    ui.popover(panel=panel, text=label.title() + " falloff")
                    canvas = ui.canvas
                    canvas.arrange(560)
                    button = next(
                        c
                        for c in canvas.controls.values()
                        if c.options.get("panel_model")
                    )
                    assert canvas.open_panel(button, clip, ctx), canvas.menu_error
                    bind(canvas)
                    canvas.overlay["widget"].motion.clear()
                    render("brush-" + label)
                # Interleaved same-context CPU submission comparison isolates six new glyphs.
                icons = [
                    c
                    for c in canvas.overlay["widget"].canvas.controls.values()
                    if c.options.get("icon", "").endswith("CURVE")
                ]
                saved_icons = [c.options["icon"] for c in icons]
                icon_cost = {"mapped": [], "unmapped": []}
                for trial in range(40):
                    for mode in (
                        ("mapped", "unmapped") if trial % 2 else ("unmapped", "mapped")
                    ):
                        for c, glyph in zip(icons, saved_icons):
                            c.options["icon"] = (
                                glyph if mode == "mapped" else "UNMAPPED_CURVE"
                            )
                        start = time.perf_counter()
                        render()
                        if trial >= 10:
                            icon_cost[mode].append((time.perf_counter() - start) * 1000)
                for c, glyph in zip(icons, saved_icons):
                    c.options["icon"] = glyph
                samples = []
                for _ in range(10):
                    render()
                before = dict(glass._owners["camkeys-qa"])
                for _ in range(30):
                    started = time.perf_counter()
                    render()
                    samples.append((time.perf_counter() - started) * 1000)
                assert (
                    glass._owners["camkeys-qa"]["productions"]
                    == before["productions"]
                    == 1
                )
                result = dict(
                    passed=True,
                    version=bpy.app.version_string,
                    dimensions=[width, height],
                    dpi=dpi,
                    frames=195,
                    native_text_batching=batch_info,
                    glass_productions=1,
                    icon_cpu_comparison={
                        k: statistics.median(v) for k, v in icon_cost.items()
                    },
                    retained_icon_batches=len(style._icons),
                    paint_cpu_median_ms=statistics.median(samples),
                    paint_cpu_p95_ms=sorted(samples)[28],
                    fixture="Actual consumer UIList and registered falloff popover in controlled GPU offscreen; synthetic contrasting backdrop. Dark = active factory theme; light/purple = synthetic theme fixtures.",
                    exact_match=False,
                    visual_acceptance="Pending Tyler review",
                    consumer=str(source),
                    fixture_sha256=hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        for canvas in canvases:
            canvas.park()
        addon.unregister()
        glass.release("camkeys-qa")
        if off:
            off.free()
        if under:
            under.free()
        if fonts:
            fonts.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2))
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
