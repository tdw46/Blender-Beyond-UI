"""Pie menus using retained production glass, motion, fonts and theme."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas, Layout, Theme
from beyond_ui.gpu import glass, skin, style
from pie_standalone_fixture import build, register, unregister
import pie_standalone_fixture as fixture
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run

OUT = Path(os.environ["BEYOND_UI_PIE_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        from menu_motion_batch import configure

        batch, batch_info = configure()
        ctx = bpy.context
        register()
        canvas, opener = build(ctx)
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
        canvas.arrange(1200)
        dpi = float(os.environ.get("BEYOND_UI_CAPTURE_DPI", "1"))
        width, height = int(1280 * dpi), int(940 * dpi)
        clip = (0, 0, 1200, 900)
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
                for row in range(22):
                    text_run(
                        face(fonts, "body"),
                        f"Underlying UI text {row:02}    0.750     Material settings     Roughness 0.500     Background contrast",
                        14 * dpi,
                        (0.85, 0.88, 0.91, 1),
                        (55 * dpi, (44 + row * 42) * dpi),
                        ((0, 0, width, height),),
                    )
            assert glass.prepare_texture(
                "enum-property-fixture", 1, under.texture_color, (0, 0, width, height)
            ), glass.error

            def render(name=None):
                reads = fixture.draws
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
                    (40 * dpi, 20 * dpi, canvas._width * dpi, 900 * dpi),
                    font=fonts,
                    preferences=ctx.preferences,
                    backdrop="enum-property-fixture",
                )
                assert fixture.draws == reads, "Painting called registered menu draw"
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

            def open():
                canvas.cancel()
                menu = opener.open(anchor=(600, 450), clip=clip, context=ctx)
                menu.motion.clock = lambda: clock[0]
                menu.started = clock[0]
                menu.motion.clear()
                return menu

            timings = {}

            def timed(label):
                for _ in range(20):
                    render()
                before = resources()
                samples = []
                for _ in range(100):
                    started = time.perf_counter()
                    render()
                    samples.append((time.perf_counter() - started) * 1000)
                assert resources() == before
                timings[label] = dict(
                    median_ms=statistics.median(samples),
                    p95_ms=sorted(samples)[94],
                    max_ms=max(samples),
                )

            def choose(label):
                menu = canvas.context_menu
                i, rect, row = next(
                    v for v in menu.visible_rows() if v[2].label == label
                )
                x, y, w, h = rect
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    x + w / 2,
                    y + h / 2,
                    clip,
                    context=ctx,
                )
                canvas.event(
                    NS(type="LEFTMOUSE", value="RELEASE"),
                    x + w / 2,
                    y + h / 2,
                    clip,
                    context=ctx,
                )
                return canvas.context_menu

            render("rest")
            menu = open()
            clock[0] += 1
            render("parent")
            timed("parent")
            menu = choose("Transform…")
            clock[0] += 1
            canvas.advance_animations(context=ctx)
            render("nested")
            timed("nested")
            assert menu.glass_ready and menu.radial()
            # Hold just outside the petal, then enter its logical landing zone.
            x, y, w, h = menu.rectangles[0]
            menu.event(NS(type="MOUSEMOVE", value="NOTHING"), x + w + 1, y + h / 2, ctx)
            clock[0] += 1
            render("approach")
            assert menu.pull(0) != (0, 0)
            menu.event(NS(type="MOUSEMOVE", value="NOTHING"), x + w - 5, y + h / 2, ctx)
            assert menu.pull(0) == (0, 0)
            render("hover")
            clock[0] += 1
            canvas.advance_animations(context=ctx)
            render("hover-settled")
            assert (OUT / "hover.png").read_bytes() == (
                OUT / "hover-settled.png"
            ).read_bytes()
            menu.event(NS(type="MOUSEMOVE", value="NOTHING"), *menu.origin, ctx)
            clock[0] += 1
            index = next(
                i for i, r in enumerate(menu.page.rows) if r.label == "Resolution"
            )
            assert menu.open_row_context(index, ctx)
            clock[0] += 1
            canvas.advance_animations(context=ctx)
            render("context")
            timed("context")
            menu.back(ctx)
            menu = choose("More Actions")
            clock[0] += 1
            canvas.advance_animations(context=ctx)
            render("search")
            menu.back(ctx)
            menu.back(ctx)
            render("back")
            menu = open()
            render()
            before = resources()
            equal_frames = []
            trajectories = []
            count = int(os.environ.get("BEYOND_UI_PIE_FRAMES", "96"))
            start = clock[0]
            for frame in range(count):
                tick = frame * 96 // count
                clock[0] = start + frame * 3.2 / count
                if tick == 12:
                    menu = choose("Transform…")
                if 18 <= tick < 42:
                    _, (x, y, w, h), _ = next(
                        v for v in menu.visible_rows() if v[2].label == "Rotate"
                    )
                    amount = min(1, (tick - 18) / 14)
                    px = menu.origin[0] + (x + w * 0.6 - menu.origin[0]) * amount
                    py = menu.origin[1] + (y + h * 0.5 - menu.origin[1]) * amount
                    menu.event(NS(type="MOUSEMOVE", value="NOTHING"), px, py, ctx)
                if tick == 42:
                    index = next(
                        i
                        for i, r in enumerate(menu.page.rows)
                        if r.label == "Resolution"
                    )
                    menu.open_row_context(index, ctx)
                if tick == 54:
                    menu.back(ctx)
                if tick == 66:
                    menu.back(ctx)
                    menu = canvas.context_menu
                if tick == 78:
                    menu = choose("Transform…")
                canvas.advance_animations(context=ctx)
                render(f"frame-{frame:03}")
                with batch():
                    render()
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / "batch.png", width, height, bytes(pixels))
                equal_frames.append(
                    (OUT / "batch.png").read_bytes()
                    == (OUT / f"frame-{frame:03}.png").read_bytes()
                )
                trajectories.append(
                    dict(
                        frame=frame,
                        navigation_depth=menu.navigation_depth(),
                        radial=menu.radial(),
                        origin=menu.origin,
                        opening=menu.opening(),
                    )
                )
            assert all(equal_frames), [i for i, v in enumerate(equal_frames) if not v]
            assert resources() == before, (resources(), before)
            clock[0] += 10
            canvas.advance_animations(context=ctx)
            assert not canvas.advance_animations(context=ctx)
            (OUT / "trajectory.json").write_text(
                json.dumps(trajectories, indent=2) + "\n"
            )
            canvas.animation.enabled = False
            menu = open()
            menu = choose("Transform…")
            assert menu.motion.strength == 0
            render("disabled")
            assert menu.glass_ready
            canvas.cancel()
            canvas.arrange(280)
            opener.open(anchor=(140, 200), clip=(0, 0, 280, 900), context=ctx)
            # A simple parent may fit; the compound child must fall back naturally.
            child_index = next(
                i
                for i, r in enumerate(canvas.context_menu.page.rows)
                if r.label == "Transform…"
            )
            canvas.context_menu.choose(child_index, ctx)
            assert canvas.context_menu.layout_mode == "LIST_FALLBACK"
            render("narrow")
            canvas.cancel()
            canvas.arrange(1200)
            # Alternate exact pre-change and current menu painters in one process.
            # Same rows, fonts, theme, backdrop and viewport; no GPU readback in timings.
            baseline = ROOT / "build/marking-menu/baseline/beyond_ui/gpu/menus.py"
            if baseline.exists():
                import beyond_ui.gpu.menus as menus
                from beyond_ui.context_menu import Menu, Entry, Target

                namespace = {
                    "__name__": "beyond_ui.gpu.menu_baseline",
                    "__package__": "beyond_ui.gpu",
                }
                exec(compile(baseline.read_bytes(), str(baseline), "exec"), namespace)
                current = menus.context_menu
                canvas.cancel()
                canvas.context_menu = Menu(
                    Target("benchmark"),
                    tuple(Entry(str(i), f"Action {i}") for i in range(8)),
                    (180, 120),
                    clip,
                )
                results = {"before": [], "after": []}
                try:
                    for block in range(10):
                        for label, painter in (
                            (("before", namespace["context_menu"]), ("after", current))
                            if block % 2 == 0
                            else (
                                ("after", current),
                                ("before", namespace["context_menu"]),
                            )
                        ):
                            menus.context_menu = painter
                            for _ in range(10):
                                render()
                            for _ in range(25):
                                t = time.perf_counter()
                                render()
                                results[label].append((time.perf_counter() - t) * 1000)
                            render("list-" + label)
                finally:
                    menus.context_menu = current
                for label, samples in results.items():
                    timings["list-" + label] = dict(
                        median_ms=statistics.median(samples),
                        p95_ms=sorted(samples)[int(len(samples) * 0.95) - 1],
                        max_ms=max(samples),
                    )
                assert (OUT / "list-before.png").read_bytes() == (
                    OUT / "list-after.png"
                ).read_bytes()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            dpi=dpi,
            dimensions=[width, height],
            timings=timings,
            hover_landing_pixels_equal=True,
            workload="Standalone pie and nested compound flags; immediate stable hover landing; shared glass/decorators/right-click. 20 warmups/100 CPU paint samples; paired list painter 10 alternating blocks of 25 samples. Readback excluded.",
            theme="Factory active Blender theme, raw display-space GPU captures",
            stable_resources=True,
            retained_resources=before,
            native_text_batching_equal_frames=len(equal_frames),
            batch_admission=batch_info,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            fixture_helper_sha256=hashlib.sha256(
                (ROOT / "tests/pie_standalone_fixture.py").read_bytes()
            ).hexdigest(),
            exact_match=False,
            acceptance="Production menu surfaces arranged radially; generated-reference and visual/motion acceptance remain open for Tyler's QA.",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        unregister()
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
    print("PIE_CAPTURE", result.get("passed"), result.get("error", ""), flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )


bpy.app.timers.register(run, first_interval=1)
