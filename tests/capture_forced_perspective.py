"""Real consumer panel at three widths/scales, isolated and read-only drawing."""

import bpy, gpu, os, sys, json, traceback, importlib.util, time, statistics
from pathlib import Path
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from menu_motion_batch import configure

source = Path(
    os.environ.get("BEYOND_UI_CAMKEYS_ROOT", "/Users/tylerwalker/dev/CamKeys-beyond-ui")
)
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
OUT = Path(os.environ["BEYOND_UI_FORCED_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    fonts = None
    canvases = []
    result = {}
    try:
        addon.register()
        bpy.context.window_manager.EnableCamKeys = False
        scene = bpy.context.scene
        obj = bpy.data.objects.new("Face", bpy.data.meshes.new("Face"))
        scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        item = scene.mesh_object_items.add()
        item.object = obj
        scene.mesh_object_items_index = 0
        # Fixture state only; bypass geometry-generation update callbacks.
        item["auto_fov_enabled"] = True
        item["auto_fov_focus_object"] = obj
        from camkeys_qa._vendor.beyond_ui import Layout
        from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
        from camkeys_qa._vendor.beyond_ui.gpu import glass, skin, typography
        from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state, measure

        fonts = typography.Fonts()
        batch, batch_info = configure()
        area = next(a for a in bpy.context.window.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        records = []
        timings = []
        with bpy.context.temp_override(area=area, region=region):
            ctx = bpy.context
            cls = next(
                c
                for c in addon.__beyond_ui_integration__.ui._runtime.definitions
                if c.__name__ == "CAMKEYS_PT_auto_fov"
            )
            draw = addon.__beyond_ui_integration__.ui._runtime.draw_functions[cls]
            for width in (260, 286, 360, 480):
                ui = Layout(
                    context=ctx, **addon.__beyond_ui_integration__.ui.layout_options
                )
                ui.title(text="Forced Perspective")
                draw(PanelProxy(cls, ui), ctx)
                canvas = ui.canvas
                canvas.panel_layout = True
                canvases.append(canvas)
                canvas.set_text_measure(
                    lambda t, r: measure(
                        typography.face(fonts, r),
                        canvas.theme.font_size * (12 / 11 if r == "title" else 1),
                        t,
                    )[0],
                    "fixture",
                )
                canvas.arrange(width)
                focal = next(
                    c
                    for c in canvas.controls.values()
                    if c.label == "Apparent Focal Length"
                )
                unit = next(c for c in canvas.controls.values() if c.label == "mm")
                toggle = next(
                    c
                    for c in canvas.controls.values()
                    if c.kind == "toggle" and not c.label
                )
                if not os.environ.get("BEYOND_UI_BASELINE"):
                    assert focal.options.get("slider") is True, focal.options
                    explicit_ui = Layout(context=ctx)
                    explicit_ui.canvas.panel_layout = True
                    explicit = explicit_ui.prop(
                        item, "auto_fov_max_strength", slider=False
                    )
                    explicit_ui.canvas.arrange(width)
                    assert explicit.options["slider"] is False
                    explicit_ui.canvas.park()
                    assert unit.rect[2] >= measure(int(fonts), 11, "mm")[0] + 11, (
                        unit.rect
                    )
                    assert toggle.rect[2] >= 46, toggle.rect
                    assert toggle.motion.toggle and not toggle.options.get(
                        "bool_button"
                    )
                    for name in (
                        "Focus FOV Around:",
                        "Camera Effect Locks",
                        "Multi-Object Falloff Settings: (0=infinite)",
                    ):
                        c = next(c for c in canvas.controls.values() if c.label == name)
                        assert c.options.get("text_role") == "title", (name, c.options)
                assert canvas.open_context(
                    focal, *focal.rect[:2], (0, 0, width, canvas.height), context=ctx
                )
                assert canvas.context_focus is focal
                canvas.cancel()
                records.append(
                    dict(
                        width=width,
                        height=canvas.height,
                        controls=[
                            dict(
                                kind=c.kind,
                                label=c.label,
                                rect=c.rect,
                                stacked=c.options.get("_entry_stacked"),
                                heading=c.options.get("text_role"),
                                slider=c.options.get("slider"),
                                label_span=c.options.get("_label_span"),
                                list_tool=c.options.get("_list_tool"),
                            )
                            for c in canvas.controls.values()
                        ],
                    )
                )
                for dpi in (1, 1.5, 2):
                    w, h = int((width + 32) * dpi), int((canvas.height + 32) * dpi)
                    off = gpu.types.GPUOffScreen(w, h, format="RGBA8")
                    under = gpu.types.GPUOffScreen(w, h, format="RGBA8")
                    key = ("forced", width, dpi)
                    try:
                        with (
                            off.bind(),
                            gpu_state(),
                            gpu.matrix.push_pop(),
                            gpu.matrix.push_pop_projection(),
                        ):
                            gpu.matrix.load_matrix(Matrix.Identity(4))
                            gpu.matrix.load_projection_matrix(
                                Matrix(
                                    (
                                        (2 / w, 0, 0, -1),
                                        (0, 2 / h, 0, -1),
                                        (0, 0, 1, 0),
                                        (0, 0, 0, 1),
                                    )
                                )
                            )
                            with under.bind():
                                gpu.state.viewport_set(0, 0, w, h)
                                gpu.state.scissor_set(0, 0, w, h)
                                gpu.state.active_framebuffer_get().clear(
                                    color=(0.08, 0.10, 0.12, 1)
                                )
                                skin.draw(
                                    (0, 0, w * 0.45, h),
                                    (0.12, 0.20, 0.26, 1),
                                    radius=0,
                                    border=0,
                                )
                                skin.draw(
                                    (w * 0.7, 0, w * 0.3, h),
                                    (0.23, 0.17, 0.13, 1),
                                    radius=0,
                                    border=0,
                                )
                            gpu.state.viewport_set(0, 0, w, h)
                            gpu.state.scissor_set(0, 0, w, h)
                            assert glass.prepare_texture(
                                key, 1, under.texture_color, (0, 0, w, h)
                            ), glass.error
                            fb = gpu.state.active_framebuffer_get()
                            rect = (
                                16 * dpi,
                                16 * dpi,
                                width * dpi,
                                canvas.height * dpi,
                            )
                            for frame in range(12):
                                fb.clear(color=(0.08, 0.1, 0.12, 1))
                                start = time.perf_counter()
                                assert glass.lens(
                                    key,
                                    rect,
                                    canvas.theme.radius * dpi,
                                    (0, 0, 0, 0),
                                    blur=0.3,
                                )
                                with batch():
                                    canvas.paint(
                                        rect,
                                        (0, 0, w, h),
                                        font=fonts,
                                        preferences=ctx.preferences,
                                        backdrop=key,
                                    )
                                if width == 360 and dpi == 2 and frame > 1:
                                    timings.append((time.perf_counter() - start) * 1000)
                            pixels = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
                            pixels.dimensions = w * h * 4
                            png(OUT / f"{width}-{dpi:g}x.png", w, h, bytes(pixels))
                    finally:
                        glass.release(key)
                        off.free()
                        under.free()
            result = dict(
                passed=True,
                version=bpy.app.version_string,
                records=records,
                native_text_batching=batch_info,
                paint_cpu_median_ms=statistics.median(timings),
                paint_cpu_p95_ms=sorted(timings)[int(0.95 * (len(timings) - 1))],
                scales=[1, 1.5, 2],
                widths=[260, 286, 360, 480],
                fixture="Actual CamKeys draw; custom production GPU glass; synthetic contrasting backdrop",
                exact_match=False,
            )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        for canvas in canvases:
            canvas.park()
        if fonts:
            fonts.close()
        try:
            addon.unregister()
        except Exception:
            pass
        (OUT / "report.json").write_text(json.dumps(result, indent=2, default=str))
        Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
            json.dumps(result, indent=2, default=str)
        )
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
