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

            def render(name=None, contrast=False, useglass=True):
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
                    (0, height - canvas.height, width, canvas.height),
                    (0, 0, width, height),
                    font=fonts,
                    backdrop="menu-fixture" if useglass else None,
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
            timings=timing,
            retained_resources=before,
            stable_resources=before == after,
            compound_targets=targets,
            hashes=hashes,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            acceptance="Unapproved; generated reference and motion QA required",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        glass.release("menu-fixture")
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
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=1)
