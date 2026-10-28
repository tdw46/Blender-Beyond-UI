"""Production menu captures, deterministic motion and warm render/input timings."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from mathutils import Matrix
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png, make_widgets
from next_fixtures import widgets as next_widgets
from beyond_ui import Canvas, Theme, MenuEntry
from beyond_ui.context_menu import default_entries
from beyond_ui.bindings import rna_binding
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts
from beyond_ui.gpu import style, skin, glass
from beyond_ui.widgets.base import _LINE_CACHE

OUT = Path(
    os.environ.get("BEYOND_UI_CAPTURE_DIR", ROOT / "build/context-menu-v1/capture")
)
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = fonts = underlay = None
    try:
        width, height = 640, 560
        fonts = Fonts()
        off = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        underlay = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        canvas = Canvas(Theme(palette="REFERENCE"), menu_commit=lambda key: None)
        control = canvas.number(
            "location",
            "Location Y",
            rna_binding(lambda: bpy.context.active_object, "location", index=1),
        )
        canvas.title("title", "Context Menu")
        for i in range(17):
            canvas.label(str(i), "")
        canvas.arrange(width)
        clip = (0, 0, width, height)
        children = lambda t, c: (
            MenuEntry(
                "COPY",
                "Copy Value",
                lambda t, c: setattr(
                    c.window_manager, "clipboard", repr(t.binding.read())
                ),
            ),
            MenuEntry(
                "DISABLED",
                "Unavailable action",
                enabled=False,
                tip="Fixture disabled state",
            ),
        )
        canvas.context_provider = lambda t, c: [
            MenuEntry("MORE", "More", children=children),
            *default_entries(t, c),
        ]
        canvas.open_context(control, 170, 65, clip, context=bpy.context)
        assert canvas.context_menu is not None, canvas.menu_error
        menu = canvas.context_menu
        now = [0.0]
        menu.motion.clock = lambda: now[0]
        menu.motion.clear()
        hashes = {}
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

            # Completed host backdrop: actual GPU text and colored geometry.
            # The same production blur producer is shared by every menu and frame.
            with underlay.bind():
                gpu.state.viewport_set(0, 0, width, height)
                gpu.state.scissor_set(0, 0, width, height)
                gpu.state.active_framebuffer_get().clear(color=(0.10, 0.13, 0.16, 1))
                skin.draw(
                    (0, 0, 260, height), (0.16, 0.28, 0.36, 1), radius=0, border=0
                )
                skin.draw(
                    (360, 0, 280, height), (0.30, 0.20, 0.15, 1), radius=0, border=0
                )
                for row in range(11):
                    style.draw(
                        40, 35 + row * 42, 560, 30, (0.18, 0.21, 0.24, 1), radius=5
                    )
                    from beyond_ui.gpu.menus import text_run
                    from beyond_ui.gpu.typography import face

                    text_run(
                        face(fonts, "body"),
                        f"Underlying UI field {row:02}     0.750",
                        14,
                        (0.85, 0.88, 0.91, 1),
                        (55, 44 + row * 42),
                        ((0, 0, width, height),),
                    )
            assert glass.prepare_texture(
                "menu-fixture", 1, underlay.texture_color, (0, 0, width, height)
            ), glass.error

            def render(name=None, contrast=False, useglass=True, ratio=1):
                fb.clear(color=(22 / 255, 25 / 255, 27 / 255, 1))
                glass._draw(
                    underlay.texture_color,
                    (0, 0, width, height),
                    (0, 0, 1, 1),
                    (0, 0, 2, 0),
                    (0, 0, 0, 0),
                    gpu.matrix.get_projection_matrix()
                    @ gpu.matrix.get_model_view_matrix(),
                )
                canvas.paint(
                    (
                        0,
                        height - canvas.height * ratio,
                        width * ratio,
                        canvas.height * ratio,
                    ),
                    (0, 0, width, height),
                    font=fonts,
                    backdrop="menu-fixture" if useglass else None,
                    preferences=bpy.context.preferences,
                )
                if name:
                    data = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                    data.dimensions = width * height * 4
                    raw = bytes(data)
                    hashes[name] = hashlib.sha256(raw).hexdigest()
                    png(OUT / (name + ".png"), width, height, raw)

            render()
            render()
            render("root")
            assert menu.glass_ready
            render("tint-fallback", useglass=False)
            render("contrast", True)
            # Warm both pages and their icon glyphs before resource admission.
            menu.choose(0, bpy.context)
            menu.motion.clear()
            render()
            menu.back()
            menu.motion.clear()
            render()

            def resources():
                return dict(
                    skin_shader=id(skin._shader),
                    skin_batch=id(skin._batch),
                    style_shader=id(style._shader),
                    style_batch=id(style._batch),
                    icon_shader=id(style._icon_shader),
                    icons={k: id(v) for k, v in style._icons.items()},
                    glass_shader=id(glass._lens_shader),
                    glass_batches={k: id(v) for k, v in glass._lens_batches.items()},
                    backdrop_productions=glass._owners["menu-fixture"]["productions"],
                    blur_productions=glass._owners["menu-fixture"][
                        "strong_productions"
                    ],
                    backdrop_allocations=glass._owners["menu-fixture"]["allocations"],
                )

            before = resources()
            menu.motion.pulse("reveal", 0.12)
            for frame in range(45):
                now[0] = frame / 30
                if frame == 8:
                    menu.event(
                        NS(type="MOUSEMOVE", value="NOTHING"), 200, 100, bpy.context
                    )
                if frame == 15:
                    menu.choose(0, bpy.context)
                if frame == 30:
                    menu.back()
                render(f"frame-{frame:03}")
                canvas.advance_animations()
            now[0] = 3
            canvas.advance_animations()
            menu.page.highlight = 0
            render("settled")
            assert hashes["root"] == hashes["settled"]
            menu.motion.pulse("reveal", 0.12)
            canvas.animation.enabled = False
            render("disabled")
            assert hashes["root"] == hashes["disabled"]
            canvas.animation.enabled = True
            menu.choose(0, bpy.context)
            menu.motion.clear()
            menu.page.highlight = 1
            render("nested")
            rect = next(r for i, r, row in menu.visible_rows() if row.key == "DISABLED")
            menu.hover_tip(2, rect[0] + 10, rect[1] + 10, bpy.context)
            now[0] += 0.6
            menu.reveal_tip(bpy.context)
            menu.motion.clear()
            render("tooltip")
            menu.back()
            menu.motion.clear()
            timing = {}
            for mode in ("closed", "tint-fallback", "open", "nested", "scroll"):
                canvas.context_menu = None if mode == "closed" else menu
                if mode == "nested":
                    menu.choose(0, bpy.context)
                    menu.motion.clear()
                elif menu.parents:
                    menu.back()
                    menu.motion.clear()
                times = []
                for i in range(120):
                    if mode == "scroll":
                        menu.event(
                            NS(type="DOWN_ARROW", value="PRESS"), 200, 100, bpy.context
                        )
                    start = time.perf_counter()
                    render(useglass=mode != "tint-fallback")
                    elapsed = (time.perf_counter() - start) * 1000
                    if i >= 20:
                        times.append(elapsed)
                timing[mode] = dict(
                    median_ms=statistics.median(times),
                    p95_ms=sorted(times)[94],
                    max_ms=max(times),
                )
            input_times = []
            for i in range(100):
                start = time.perf_counter()
                menu.event(
                    NS(type="UP_ARROW" if i % 2 else "DOWN_ARROW", value="PRESS"),
                    200,
                    100,
                    bpy.context,
                )
                input_times.append((time.perf_counter() - start) * 1000)
            timing["navigation"] = dict(
                median_ms=statistics.median(input_times), p95_ms=sorted(input_times)[94]
            )
            after = resources()
            assert before == after, "Menu motion/input rebuilt line geometry"
            canvas.context_menu = menu
            canvas.close_context()
            canvas.advance_animations()
            assert not canvas._moving
            # Default menu routing for all existing compound cards, real production canvas.
            widgets, _ = make_widgets()
            widgets += next_widgets()
            points = [
                (260, 430),
                (316, 300),
                (130, 230),
                (400, 140),
                (140, 100),
                (240, 260),
                (200, 200),
                (200, 200),
            ]
            # Shortcut assignment shares the same painter and backdrop owner.
            from beyond_ui.context_shortcuts import Action
            from beyond_ui.context_menu import Menu, Target

            with bpy.context.temp_override(
                area=next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
            ):
                shortcut = Action(
                    "wm.context_toggle", {"data_path": "object.show_name"}, bpy.context
                )
                canvas.context_menu = Menu(
                    Target("shortcut"),
                    (shortcut.entry(bpy.context),),
                    (170, 100),
                    clip,
                    context=bpy.context,
                )
                canvas.context_menu.choose(0, bpy.context)
                canvas.context_menu.motion.clear()
                render("capture-mode-picker")
                canvas.context_menu.motion.clock = lambda: now[0]
                now[0] = 0
                canvas.context_menu.motion.pulse("reveal", 0.12)
                mode_resources = resources()
                for frame in range(36):
                    now[0] = frame / 30
                    render(f"mode-{frame:03}")
                    canvas.advance_animations()
                assert resources() == mode_resources
                modes = canvas.context_menu.page.rows
                canvas.context_menu.choose(1, bpy.context)
                canvas.context_menu.motion.clear()
                render("shortcut-capture")
                assert canvas.context_menu.glass_ready
                capture_menu = canvas.context_menu
                capture_menu.motion.clock = lambda: now[0]
                now[0] = 0
                capture_menu.motion.pulse("reveal", 0.12)
                capture_resources = resources()
                for frame in range(36):
                    now[0] = frame / 30
                    render(f"shortcut-{frame:03}")
                    canvas.advance_animations()
                assert resources() == capture_resources
                capture_menu.back()
                capture_menu.start_capture(modes[2], bpy.context, replace_mode=True)
                capture_menu.motion.clear()
                render("mouse-capture")
                capture_menu.start_capture(modes[3], bpy.context, replace_mode=True)
                capture_menu.event(NS(type="B", value="PRESS"), 200, 200, bpy.context)
                capture_menu.motion.clear()
                render("chord-capture")
                canvas.close_context()

                from beyond_ui.context_fields import property_row
                from beyond_ui.context_rna import Property
                from beyond_ui.hosts.menu_native import property_favorite

                owner = bpy.context.active_object
                source = Property(lambda: owner, "show_name")
                target = Target("contribution", commit=lambda key: None)
                canvas.context_menu = Menu(
                    target,
                    (
                        property_row(owner, "show_name"),
                        property_row(owner, "rotation_mode"),
                    ),
                    (170, 100),
                    clip,
                    context=bpy.context,
                )
                canvas.context_menu.motion.clear()
                render("contributed-fields")
                canvas.context_menu.choose(1, bpy.context)
                canvas.context_menu.motion.clear()
                render("enum-choices")
                canvas.close_context()
                canvas.context_menu = Menu(
                    target,
                    (
                        property_row(owner, "name"),
                        property_row(owner, "location", index=1),
                        property_row(owner, "location"),
                    ),
                    (170, 100),
                    clip,
                    context=bpy.context,
                )
                canvas.context_menu.motion.clear()
                render("scalar-fields")
                canvas.context_menu.choose(1, bpy.context)
                canvas.context_menu.event(
                    NS(type="TEXTINPUT", value="PRESS", unicode="2+3"),
                    200,
                    200,
                    bpy.context,
                )
                canvas.context_menu.motion.clear()
                render("scalar-edit")
                edit_menu = canvas.context_menu
                now[0] = 0
                edit_menu.motion.clock = lambda: now[0]
                edit_menu.motion.clear()
                edit_menu.motion.pulse("reveal", 0.12)
                edit_resources = resources()
                for frame in range(36):
                    now[0] = frame / 30
                    render(f"field-{frame:03}")
                assert resources() == edit_resources
                for _ in range(20):
                    render()
                samples = []
                for _ in range(100):
                    started = time.perf_counter()
                    render()
                    samples.append((time.perf_counter() - started) * 1000)
                timing["inline-edit"] = dict(
                    median_ms=statistics.median(samples),
                    p95_ms=sorted(samples)[94],
                    max_ms=max(samples),
                )
                from dataclasses import replace

                original_theme = canvas.theme
                canvas.theme = replace(canvas.theme, palette="BLENDER")
                render("field-native-theme")
                ui = bpy.context.preferences.themes[0].user_interface
                fields = [
                    (name, attr)
                    for name in ("wcol_regular", "wcol_num", "wcol_radio", "wcol_tool")
                    for attr in ("inner", "inner_sel", "text", "text_sel")
                ]
                original_colors = {
                    (name, attr): tuple(getattr(getattr(ui, name), attr))
                    for name, attr in fields
                }
                try:
                    for theme_name, fill, accent, ink in (
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
                    ):
                        for name, attr in fields:
                            value = (
                                fill
                                if attr == "inner"
                                else accent
                                if attr == "inner_sel"
                                else ink
                                if attr == "text"
                                else (1, 1, 1)
                            )
                            setattr(getattr(ui, name), attr, value)
                        render("field-" + theme_name + "-theme")
                        render("field-" + theme_name + "-scale-150", ratio=1.5)
                        assert resources() == edit_resources
                finally:
                    for (name, attr), value in original_colors.items():
                        setattr(getattr(ui, name), attr, value)
                    canvas.theme = original_theme
                edit_menu.event(
                    NS(type="A", value="PRESS", ctrl=True), 200, 200, bpy.context
                )
                edit_menu.event(
                    NS(type="TEXTINPUT", value="PRESS", unicode="invalid"),
                    200,
                    200,
                    bpy.context,
                )
                edit_menu.event(NS(type="RET", value="PRESS"), 200, 200, bpy.context)
                assert edit_menu.error and edit_menu.tooltip is not None
                edit_menu.motion.clear()
                render("field-invalid")
                edit_menu.event(NS(type="ESC", value="PRESS"), 200, 200, bpy.context)
                edit_menu.choose(2, bpy.context)
                edit_menu.motion.clear()
                render("array-fields")
                canvas.close_context()
                from beyond_ui.context_shortcuts import property_entry

                canvas.context_menu = Menu(
                    target,
                    (
                        property_entry(
                            Property(lambda: owner, "rotation_mode"), bpy.context
                        ),
                    ),
                    (170, 100),
                    clip,
                    context=bpy.context,
                )
                canvas.context_menu.choose(0, bpy.context)
                canvas.context_menu.motion.clear()
                render("enum-shortcuts")
                canvas.close_context()
                for favorite in (False, True):
                    if favorite:
                        from beyond_ui.hosts.menu_native import add_property_favorite

                        add_property_favorite(source, bpy.context)
                    canvas.open_context(control, 170, 65, clip, context=bpy.context)
                    # Use the exact property being displayed by this fixture.
                    shown_source = control.binding.context
                    if favorite:
                        add_property_favorite(shown_source, bpy.context)
                        canvas.close_context()
                        canvas.open_context(control, 170, 65, clip, context=bpy.context)
                    canvas.context_menu.motion.clear()
                    render("favorite-remove" if favorite else "favorite-add")
                    canvas.close_context()
                    if favorite:
                        property_favorite(shown_source, bpy.context, remove=True)
                        property_favorite(source, bpy.context, remove=True)
            targets = {}
            for (slug, title, widget), (px, py) in zip(widgets, points):
                canvas = Canvas(Theme(palette="REFERENCE"))
                c = canvas.widget(slug, widget)
                canvas.arrange(width)
                a, b, w, h = c.rect
                assert canvas.open_context(
                    c,
                    a + px * w / widget.width,
                    b + py * h / widget.height,
                    (0, 0, width, height),
                    context=bpy.context,
                ), slug
                canvas.context_menu.motion.clear()
                targets[slug] = canvas.context_menu.target.part
                render("control-" + slug)
                canvas.cancel()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            build=bpy.app.build_hash.decode(),
            backend=gpu.platform.backend_type_get(),
            dimensions=[width, height],
            scale=1,
            theme="explicit REFERENCE",
            transparency="Production BVT lens, blur=0.7, untinted refracted body; one GPU backdrop revision shared by all menus and motion frames",
            frames=45,
            additional_field_states={
                "themes": ["native Blender", "synthetic light", "synthetic purple"],
                "render_scales": [1, 1.5],
                "acceptance": "Execution/capture fixtures; not approved references or a system-DPI matrix",
            },
            timings=timing,
            retained_resources=before,
            stable_resources=before == after,
            compound_targets=targets,
            hashes=hashes,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            acceptance="Unapproved; generated reference and motion QA required",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        glass.release("menu-fixture")
        assert not glass._owners and not glass._views and not glass._lens_batches
        assert glass._lens_shader is None and glass._shader is None
        if underlay:
            underlay.free()
        if off:
            off.free()
        if fonts:
            fonts.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("MENU_CAPTURE", result.get("passed"), result.get("error", ""), flush=True)
    # Release local GPU wrappers before Blender destroys its drawing context.
    bpy.app.timers.register(quit_after_capture, first_interval=0.1)


def quit_after_capture():
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
