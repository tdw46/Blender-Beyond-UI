"""Production numeric property captures; one retained BVT glass backdrop."""

import bpy, gpu, json, os, sys, hashlib, traceback, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from beyond_ui import Canvas, Layout, Theme
from beyond_ui.gpu import glass, style, skin
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run
from beyond_ui.numeric import _unit_text, _unit_factor

OUT = Path(os.environ["BEYOND_UI_NUMERIC_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    off = under = fonts = None
    try:
        ctx = bpy.context
        obj = ctx.active_object
        scene = ctx.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 0.1
        scene.unit_settings.length_unit = "CENTIMETERS"
        scene.unit_settings.system_rotation = "DEGREES"
        ctx.preferences.view.factor_display_type = "PERCENTAGE"
        bpy.types.Scene.beyond_numeric_factor = bpy.props.FloatProperty(
            subtype="FACTOR", min=0, max=1, default=0.25
        )
        obj.location = (1.25, 2.5, 0.75)
        obj.rotation_euler = (0.5235987756, 1.570796327, 0.7853981634)
        canvas = Canvas(Theme(palette="REFERENCE"))
        ui = Layout(canvas, context=ctx)
        ui.title(text="Numeric Properties")
        ui.prop(obj, "rotation_euler", index=1, text="Rotation Y")
        ui.prop(obj, "location", index=0, text="Distance X")
        ui.prop(scene, "beyond_numeric_factor", text="Factor", slider=True)
        ui.prop(scene.render, "resolution_percentage", text="Resolution", slider=True)
        for i in range(12):
            ui.prop(obj, "location", index=i % 3, text=f"Distance {i + 1}")
        canvas.arrange(560)
        controls = [c for c in canvas.controls.values() if c.kind == "number"]
        width, height = 640, 560
        clip = (0, 0, 560, 520)
        fonts = Fonts()
        off = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        under = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        hashes = {}
        times = {}
        clock = [0.0]
        for c in controls:
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
                "numeric-fixture", 1, under.texture_color, (0, 0, width, height)
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
                    backdrop="numeric-fixture",
                )
                if name:
                    pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                    pixels.dimensions = width * height * 4
                    raw = bytes(pixels)
                    hashes[name] = hashlib.sha256(raw).hexdigest()
                    png(OUT / (name + ".png"), width, height, raw)

            def resources():
                return dict(
                    shader=id(style._shader),
                    batch=id(style._batch),
                    skin=id(skin._batch),
                    glass=id(glass._lens_shader),
                    lens={k: id(v) for k, v in glass._lens_batches.items()},
                    productions=glass._owners["numeric-fixture"]["productions"],
                    blur=glass._owners["numeric-fixture"]["strong_productions"],
                    offscreens=glass._owners["numeric-fixture"]["allocations"],
                    layout=canvas.layout_count,
                )

            def bench(name):
                for _ in range(20):
                    render()
                samples = []
                for _ in range(100):
                    start = time.perf_counter()
                    render()
                    samples.append((time.perf_counter() - start) * 1000)
                times[name] = dict(
                    median_ms=statistics.median(samples),
                    p95_ms=sorted(samples)[94],
                    max_ms=max(samples),
                )

            render("units")
            bench("units")
            saved = [c.options.pop("numeric") for c in controls]
            render("raw-baseline")
            bench("raw-baseline")
            for c, n in zip(controls, saved):
                c.options["numeric"] = n
            first = controls[0]
            x, y, w, h = first.rect
            canvas.open_context(first, x + 40, y + 20, clip, context=ctx)
            canvas.context_menu.motion.clear()
            render("context")
            canvas.close_context()
            render()
            before = resources()
            misses = (_unit_text.cache_info().misses, _unit_factor.cache_info().misses)
            for frame in range(60):
                clock[0] = frame / 30
                if frame in (0, 8, 13, 16):
                    kind, value = (
                        ("MOUSEMOVE", "NOTHING")
                        if frame in (0, 13)
                        else ("LEFTMOUSE", "PRESS" if frame == 8 else "RELEASE")
                    )
                    canvas._motion_input(
                        NS(type=kind, value=value),
                        x + 40 + (8 if frame == 13 else 0),
                        y + 10,
                        clip,
                    )
                if frame == 20:
                    canvas._motion_input(
                        NS(type="MOUSEMOVE", value="NOTHING"), -10, -10, clip
                    )
                render(f"frame-{frame:03}")
                canvas.advance_animations()
            clock[0] = 5
            canvas.advance_animations()
            render("settled")
            assert not canvas.advance_animations()
            assert hashes["settled"] == hashes["units"]
            assert before == resources()
            assert misses == (
                _unit_text.cache_info().misses,
                _unit_factor.cache_info().misses,
            )
            canvas.animation.enabled = False
            render("motion-disabled")
            assert hashes["motion-disabled"] == hashes["units"]
            canvas.animation.enabled = True
            canvas.event(
                NS(type="LEFTMOUSE", value="DOUBLE_CLICK"),
                x + 40,
                y + 10,
                clip,
                context=ctx,
            )
            canvas.event(
                NS(type="TEXTINPUT", value="PRESS", unicode="45°"),
                x + 40,
                y + 10,
                clip,
                context=ctx,
            )
            for c in controls:
                c.motion.clear()
            render("edit")
            canvas.cancel()
            from dataclasses import replace

            canvas.theme = replace(canvas.theme, palette="BLENDER")
            render("native-theme")
            ctx.preferences.themes[0].user_interface.wcol_radio.inner_sel = (
                0.66,
                0.24,
                0.78,
                1,
            )
            scene.unit_settings.system_rotation = "RADIANS"
            scene.unit_settings.system = "IMPERIAL"
            scene.unit_settings.length_unit = "FEET"
            render("imperial-radians")
            assert before == resources()
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            dimensions=[width, height],
            theme="REFERENCE then active Blender",
            timings=times,
            workload="16 numeric properties; clipped rows culled, 20 warmups and 100 CPU submission samples; raw formatter baseline in the same renderer, not a historical binary",
            retained_resources=before,
            stable_resources=True,
            hashes=hashes,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            exact_match=False,
            acceptance="Actual implementation evidence; no new approved generated reference or motion acceptance",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        if hasattr(bpy.types.Scene, "beyond_numeric_factor"):
            del bpy.types.Scene.beyond_numeric_factor
        glass.release("numeric-fixture")
        if under:
            under.free()
        if off:
            off.free()
        if fonts:
            fonts.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("NUMERIC_CAPTURE", result.get("passed"), result.get("error", ""))
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )
    return None


bpy.app.timers.register(run, first_interval=1)
