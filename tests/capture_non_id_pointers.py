"""Actual non-ID pointer/search rendering with retained production glass and fonts."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png

sys.path.insert(0, str(Path(__file__).resolve().parent))
from non_id_fixture import selection_transaction
from beyond_ui import Canvas, Layout, PointerItems
from beyond_ui.gpu import glass, skin
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run

OUT = Path(os.environ["BEYOND_UI_NON_ID_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = config = None
    try:
        from menu_motion_batch import configure

        batch, batch_info = configure()
        ctx = bpy.context
        tree = bpy.data.node_groups.new("CapturedPointers", "ShaderNodeTree")
        for i in range(500):
            node = tree.nodes.new("ShaderNodeValue")
            node.name = f"Node {i:03}"
        tree.nodes.active = tree.nodes[0]
        revision = [0]
        commits = []
        canvas = Canvas(menu_commit=commits.append)
        ui = Layout(
            canvas,
            context=ctx,
            commit=lambda a, b: commits.append((a, b)),
            pointer_sources=lambda o, p: PointerItems(
                lambda: tree.nodes,
                revision=lambda: revision[0],
                transaction=selection_transaction,
            ),
        )
        ui.title(text="Non-ID Pointers")
        full = ui.prop(tree.nodes, "active", text="Active Node")
        ui.prop_search(tree.nodes, "active", tree, "nodes", text="Find Node")
        ui.label(text="Immediate typing and safe selection")
        ui.label(text="Host revision rejects rebuilt collections")
        for i in range(10):
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
                "non-id-pointer-fixture", 1, under.texture_color, (0, 0, width, height)
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
                    "non-id-pointer-fixture",
                    (40, height - 20 - canvas.height, 560, canvas.height),
                    canvas.theme.radius,
                    (0, 0, 0, 0),
                    blur=0.3,
                )
                canvas.paint(
                    (40, height - 20 - canvas.height, 560, canvas.height),
                    (40, 20, 560, 520),
                    font=fonts,
                    preferences=ctx.preferences,
                    backdrop="non-id-pointer-fixture",
                )
                if name is None:
                    return
                pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                pixels.dimensions = width * height * 4
                png(OUT / (name + ".png"), width, height, bytes(pixels))

            def resources():
                owner = glass._owners["non-id-pointer-fixture"]
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

            def open_field():
                x, y, w, h = full.rect
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    x + 40,
                    y + 10,
                    clip,
                    context=ctx,
                )
                assert canvas.overlay is not None, canvas.menu_error
                widget = canvas.overlay["widget"]
                widget.motion.clock = lambda: clock[0]
                widget.motion.clear()
                return widget

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
            opening = []
            for _ in range(25):
                start = time.perf_counter()
                open_field()
                opening.append((time.perf_counter() - start) * 1000)
                canvas.cancel()
            timings["open_prepare_501_rows"] = dict(
                median_ms=statistics.median(opening),
                p95_ms=sorted(opening)[23],
                max_ms=max(opening),
            )
            widget = open_field()
            render("picker")
            benchmark("open_picker_501_rows")
            widget.query = "Node 00"
            widget._filter()
            render("filtered")
            canvas.cancel()
            x, y, w, h = full.rect
            canvas.open_context(full, x, y, clip, context=ctx)
            canvas.context_menu.motion.clock = lambda: clock[0]
            canvas.context_menu.motion.clear()
            render()
            render("field-context")
            canvas.close_context()
            before = resources()
            batched_equal = []
            for frame in range(100):
                clock[0] = frame / 30
                if frame == 4:
                    widget = open_field()
                    widget.motion.pulse("reveal", 0.12)
                if frame == 25:
                    widget.query = "Node 00"
                    widget._filter()
                    widget._navigate("DOWN_ARROW")
                if frame == 40:
                    widget._accept()
                    assert canvas.overlay is None
                if frame == 50:
                    widget = open_field()
                    canvas.event(
                        NS(type="TWO", value="PRESS", unicode="2"),
                        20,
                        20,
                        clip,
                        context=ctx,
                    )
                if frame == 60:
                    canvas.event(
                        NS(type="RET", value="PRESS"), 20, 20, clip, context=ctx
                    )
                    assert (
                        tree.nodes.active.name == "Node 002" and canvas.overlay is None
                    )
                if frame == 72:
                    widget = open_field()
                    a, b, w, h = canvas.overlay["rect"]
                    canvas.open_context(
                        full,
                        a + 40 * w / widget.width,
                        b + 160 * h / widget.height,
                        clip,
                        context=ctx,
                        overlay=canvas.overlay,
                    )
                    canvas.context_menu.motion.clock = lambda: clock[0]
                    canvas.context_menu.motion.clear()
                    canvas.context_menu.motion.pulse("reveal", 0.12)
                if frame == 92:
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
            theme="Factory Blender active theme; Standard viewport fixture, raw display-space capture",
            timings=timings,
            workload="One non-ID pointer and one compact search; 500 nodes plus None in the virtual popover. Paint: 20 warmups, 100 CPU submission samples. Opening: 25 event-preparation samples. Framebuffer readback excluded",
            stable_resources=True,
            native_text_batching_equal_frames=len(batched_equal),
            batch_admission=batch_info,
            retained_resources=before,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            consumer_fixture_sha256=hashlib.sha256(
                (ROOT / "tests/non_id_fixture.py").read_bytes()
            ).hexdigest(),
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            exact_match=False,
            acceptance="Actual production frames; existing shared field/menu styling. Generated-reference and motion acceptance remain open.",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        glass.release("non-id-pointer-fixture")
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
    print("NON_ID_POINTER_CAPTURE", result.get("passed"), result.get("error", ""))
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )
    return None


bpy.app.timers.register(run, first_interval=1)
