"""Read-only panel captures from a supplied scene, using real consumer draw callbacks."""

import bpy, gpu, os, sys, json, traceback, importlib.util, time, statistics
from pathlib import Path
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import png
from menu_motion_batch import configure

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"])
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
OUT = Path(os.environ["BEYOND_UI_STUDIO_CAPTURE"])
if not OUT.is_absolute():
    OUT = ROOT / OUT
OUT.mkdir(parents=True, exist_ok=True)
labels = {
    "camkeys_main": "CamKeys",
    "camkeys_linking": "CamKeys Linking",
    "auto_fov": "Forced Perspective",
    "camprops": "CamProps",
    "baking": "Baking",
    "lattice_auto_fov_modifier": "Lattice Perspective",
    "billboard_settings": "Billboard Emulation",
    "dolly_expressions": "Dolly Expressions",
    "lens_compensation": "Lens Compensation",
    "falloff_popover": "Object Falloff",
    "distance_falloff_popover": "Distance Falloff",
    "flatten_falloff_popover": "Lens Falloff",
}


def run():
    fonts = None
    canvases = []
    records = []
    timings = []
    feedback_benchmarks = []
    try:
        from camkeys_qa._vendor.beyond_ui import Layout
        from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
        from camkeys_qa._vendor.beyond_ui.gpu import glass, skin, typography
        from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state, measure

        if os.environ.get("BEYOND_UI_THEME_SIGNATURE_JSON"):
            from camkeys_qa._vendor.beyond_ui.gpu import style
            from camkeys_qa import ui_theme
            signature=json.loads(Path(os.environ["BEYOND_UI_THEME_SIGNATURE_JSON"]).read_text())["signature"]
            fields=(("radio","inner_sel"),("regular","inner"),("regular","text"),("tool","inner"),("num","inner"),("tab","inner_sel"),("numslider","inner"),("numslider","item"),("toggle","inner"),("toggle","inner_sel"),("radio","text_sel"))
            native=bpy.context.preferences.themes[0].user_interface
            for (widget,field),value in zip(fields,signature):
                setattr(getattr(native,"wcol_"+widget),field,value)
            ui_theme.STUDIO.replace(colors={},surfaces={},variants={},operators={})
            # Optional immutable old functions for equivalent before/after evidence.
            if os.environ.get("BEYOND_UI_THEME_BASELINE"):
                import ast
                baseline=Path(os.environ["BEYOND_UI_THEME_BASELINE"])
                for module,name in ((style,"_theme_palette"),(skin,"themed_roles")):
                    node=next(n for n in ast.parse((baseline/Path(module.__file__).name).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
                    exec(compile(ast.Module(body=[node],type_ignores=[]),str(baseline),"exec"),module.__dict__)
            style._theme_palette.cache_clear()
        fonts = typography.Fonts()
        batch, batch_info = configure()
        window = bpy.context.window
        area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        runtime = addon.__beyond_ui_integration__.ui._runtime
        item = bpy.context.scene.mesh_object_items[
            bpy.context.scene.mesh_object_items_index
        ]
        lattice = None
        if os.environ.get("BEYOND_UI_STUDIO_ONLY") == "lattice_auto_fov_modifier":
            source_object = item.object
            lattice = bpy.data.objects.new(
                "Studio Lattice QA", bpy.data.lattices.new("Studio Lattice QA")
            )
            bpy.context.scene.collection.objects.link(lattice)
            sample = bpy.context.scene.mesh_object_items.add()
            sample["object"] = lattice
            sample["auto_fov_linked"] = True
            sample["auto_fov_enabled"] = True
            target = sample.auto_fov_lattice_targets.add()
            target.object = source_object
            # Collection growth relocates PropertyGroup storage: reacquire the owner.
            item = bpy.context.scene.mesh_object_items[
                bpy.context.scene.mesh_object_items_index
            ]
        with bpy.context.temp_override(
            area=area,
            region=region,
            camkeys_falloff_owner=item,
            camkeys_billboard_owner=item,
            camkeys_dolly_item=item,
        ):
            ctx = bpy.context
            from camkeys_qa import (
                ui_lists,
                dolly_expressions,
                lens_compensation,
                billboard_emulation,
            )

            extra = (
                billboard_emulation.CAMKEYS_PT_billboard_settings,
                dolly_expressions.CAMKEYS_PT_dolly_expressions,
                lens_compensation.CAMKEYS_PT_lens_compensation,
                ui_lists.CAMKEYS_PT_falloff_popover,
                ui_lists.CAMKEYS_PT_distance_falloff_popover,
                ui_lists.CAMKEYS_PT_flatten_falloff_popover,
            )
            for cls in (*runtime.definitions, *extra):
                if (
                    os.environ.get("BEYOND_UI_STUDIO_ONLY")
                    and cls.__name__
                    not in {"CAMKEYS_PT_" + name for name in os.environ["BEYOND_UI_STUDIO_ONLY"].split(",")}
                ):
                    continue
                print("CAPTURE_START", cls.__name__, flush=True)
                prepare = getattr(cls, "beyond_ui_prepare", None)
                if prepare:
                    prepare(ctx)
                slug = cls.__name__.replace("CAMKEYS_PT_", "")
                variant_scope = None
                if slug == "dolly_expressions":
                    # Explicit alternate UI mode in the disposable scene; no source save.
                    item.dolly_expression.mode = "SHAPES"
                if slug == "lattice_auto_fov_modifier" and lattice is not None:
                    variant_scope = bpy.context.temp_override(
                        object=lattice, active_object=lattice
                    )
                    variant_scope.__enter__()

                for attempt in range(8):
                    ui = Layout(
                        context=ctx, property_options=getattr(cls, "beyond_ui_props", {}),
                        **addon.__beyond_ui_integration__.ui.layout_options
                    )
                    sheet = getattr(
                        addon.__beyond_ui_integration__.ui, "stylesheet", None
                    )
                    if sheet is not None:
                        sheet.apply(ui.canvas, variant=getattr(cls, "beyond_ui_style", ""))
                    if os.environ.get("BEYOND_UI_STUDIO_CAPTION", "1") != "0":
                        ui.title(text=labels[slug])
                    try:
                        runtime.draw_functions.get(cls, cls.draw)(
                            PanelProxy(cls, ui), ctx
                        )
                        break
                    except Exception:
                        ids = addon.__beyond_ui_integration__.list_ids
                        if ids.pending and attempt < 7:
                            ids.flush()
                        else:
                            raise
                print("LAYOUT_READY", slug, flush=True)
                canvas = ui.canvas
                canvas.panel_layout = True
                canvases.append(canvas)
                sheet = getattr(addon.__beyond_ui_integration__.ui, "stylesheet", None)
                if sheet is not None:
                    sheet.apply(canvas)
                canvas.set_text_measure(
                    lambda t, r: measure(
                        typography.face(fonts, r),
                        canvas.theme.font_size * (12 / 11 if r == "title" else 1),
                        t,
                    )[0],
                    "fixture",
                )
                width = int(os.environ.get("BEYOND_UI_STUDIO_WIDTH", "360"))
                dpi = 2
                canvas.arrange(width)
                records.append(
                    dict(
                        panel=cls.__name__,
                        slug=slug,
                        width=width,
                        height=canvas.height,
                        list_content_frames=[
                            dict(row=item.index, rim=outer, content=inner,
                                 padding=widget.row_padding,
                                 align=getattr(widget, "style_row_align", "center"))
                            for control in canvas.controls.values()
                            for widget in [control.options.get("widget")]
                            if hasattr(widget, "row_map")
                            for item, outer in widget.visible()
                            for child, inner, cached_item in [widget.row_map[item.index]]
                        ],
                        controls=[
                            dict(
                                kind=c.kind,
                                label=c.label,
                                rect=c.rect,
                                icon=c.options.get("icon"),
                            )
                            for c in canvas.controls.values()
                        ],
                    )
                )
                for dpi in tuple(
                    float(v)
                    for v in os.environ.get("BEYOND_UI_STUDIO_SCALES", "2").split(",")
                ):
                    w, h = int((width + 32) * dpi), int((canvas.height + 32) * dpi)
                    off = gpu.types.GPUOffScreen(w, h, format="RGBA8")
                    under = gpu.types.GPUOffScreen(w, h, format="RGBA8")
                    key = ("studio", slug)
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
                                if frame > 1:
                                    timings.append((time.perf_counter() - start) * 1000)
                            pixels = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
                            pixels.dimensions = w * h * 4
                            png(
                                OUT
                                / (
                                    f"{slug}-{dpi:g}x.png"
                                    if os.environ.get("BEYOND_UI_STUDIO_SCALES")
                                    else f"{slug}.png"
                                ),
                                w,
                                h,
                                bytes(pixels),
                            )
                            if os.environ.get("BEYOND_UI_STUDIO_MOTION"):
                                frames = (
                                    Path(os.environ["BEYOND_UI_STUDIO_MOTION"]) / slug
                                )
                                frames.mkdir(parents=True, exist_ok=True)
                                clock = [0.0]
                                for control in canvas.controls.values():
                                    control.motion.clock = lambda: clock[0]
                                    canvas.notify_changed(control.key)
                                for frame in range(24):
                                    clock[0] = frame / 30
                                    fb.clear(color=(0.08, 0.1, 0.12, 1))
                                    glass.lens(
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
                                    pixels = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
                                    pixels.dimensions = w * h * 4
                                    png(
                                        frames / f"{frame:03d}.png", w, h, bytes(pixels)
                                    )
                            if os.environ.get("BEYOND_UI_FEEDBACK_BENCH") and slug == "camkeys_linking":
                                groups = [canvas]
                                for node in canvas.controls.values():
                                    widget = node.options.get("widget")
                                    if hasattr(widget, "all_children"):
                                        groups.extend(child for child, _, _ in widget.all_children())
                                resources_before = (len(glass._owners), len(glass._lens_batches), id(skin._shader), id(skin._batch))
                                layouts_before = [c.layout_count for c in groups]
                                enabled_before = canvas.value_feedback.settings["enabled"]
                                samples = {False: [], True: []}
                                try:
                                    # Interleave paired warm CPU-submission samples; no readback in timing.
                                    for index in range(80):
                                        for enabled in ((False, True) if index % 2 else (True, False)):
                                            canvas.value_feedback.settings["enabled"] = enabled
                                            if enabled:
                                                for c in groups:
                                                    now = c.value_feedback.clock()
                                                    for control_key in c.value_feedback.values:
                                                        control = c.controls.get(control_key)
                                                        if control is not None:
                                                            c.value_feedback.active[control_key] = (control, now)
                                            fb.clear(color=(.08, .1, .12, 1))
                                            start = time.perf_counter()
                                            glass.lens(key, rect, canvas.theme.radius*dpi, (0,0,0,0), blur=.3)
                                            with batch():
                                                canvas.paint(rect, (0,0,w,h), font=fonts, preferences=ctx.preferences, backdrop=key)
                                            elapsed = (time.perf_counter()-start)*1000
                                            if index >= 10:samples[enabled].append(elapsed)
                                    resources_after = (len(glass._owners), len(glass._lens_batches), id(skin._shader), id(skin._batch))
                                    assert resources_after == resources_before
                                    assert layouts_before == [c.layout_count for c in groups]
                                    feedback_benchmarks.append(dict(width=width, scale=dpi, samples_per_mode=70,
                                        cpu_submission_ms={str(k): dict(median=statistics.median(v), p95=sorted(v)[int(len(v)*.95)]) for k,v in samples.items()},
                                        glass_owners=resources_after[0], retained_lens_batches=resources_after[1],
                                        resources_stable=True, layout_rebuilds=0,
                                        note="Same warmed panel, feedback disabled versus forced active; CPU submission only, not GPU completion or live scene FPS."))
                                finally:
                                    canvas.value_feedback.settings["enabled"] = enabled_before
                                    for c in groups:c.value_feedback.active.clear()
                            if os.environ.get("BEYOND_UI_FEEDBACK_DEMO") and slug == "camkeys_linking":
                                frames = Path(os.environ["BEYOND_UI_FEEDBACK_DEMO"])
                                if not frames.is_absolute():frames = ROOT / frames
                                frames.mkdir(parents=True, exist_ok=True)
                                active_angle = item.object.angle_items[item.object.angle_items_index]
                                demo_key = item.object.data.shape_keys.key_blocks[active_angle.shapekey]
                                original_value = demo_key.value
                                clock = [100.0]
                                def timed(c):
                                    c.value_feedback.clear()
                                    c.value_feedback.clock = lambda: clock[0]
                                    for node in c.controls.values():
                                        widget=node.options.get("widget")
                                        if hasattr(widget,"all_children"):
                                            for child,_,_ in widget.all_children():timed(child)
                                timed(canvas)
                                try:
                                    for frame in range(45):
                                        clock[0] = 100 + frame/30
                                        demo_key.value = min(frame,15)/15*.863
                                        for node in canvas.controls.values():
                                            widget=node.options.get("widget")
                                            if hasattr(widget,"refresh_display"):widget.refresh_display()
                                        fb.clear(color=(.08,.1,.12,1))
                                        glass.lens(key,rect,canvas.theme.radius*dpi,(0,0,0,0),blur=.3)
                                        with batch():canvas.paint(rect,(0,0,w,h),font=fonts,preferences=ctx.preferences,backdrop=key)
                                        pixels=fb.read_color(0,0,w,h,4,0,"UBYTE");pixels.dimensions=w*h*4
                                        png(frames/f"{frame:03d}.png",w,h,bytes(pixels))
                                    assert not canvas.value_feedback.advance()
                                    for node in canvas.controls.values():
                                        widget=node.options.get("widget")
                                        if hasattr(widget,"all_children"):
                                            assert not any(child.value_feedback.advance() for child,_,_ in widget.all_children())
                                finally:
                                    demo_key.value=original_value


                    finally:
                        glass.release(key)
                        off.free()
                        under.free()
                if variant_scope:
                    variant_scope.__exit__(None, None, None)
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            records=records,
            scene_loaded=bpy.data.filepath,
            paint_cpu_median_ms=statistics.median(timings),
            feedback_benchmarks=feedback_benchmarks,
            stylesheet=sheet.to_dict() if sheet else None,
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), records=records)
    finally:
        for c in canvases:
            c.park()
        if fonts:
            fonts.close()
        (OUT / "report.json").write_text(json.dumps(result, indent=2, default=str))
        Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
            json.dumps(result, indent=2, default=str)
        )
        addon.unregister()
        # Let the callback's GPU/Python locals unwind before context teardown.
        bpy.app.timers.register(
            lambda: (bpy.ops.wm.quit_blender(), None)[1], first_interval=0.2
        )
    return None


def start():
    addon.register()
    bpy.ops.wm.open_mainfile(
        filepath=os.environ["BEYOND_UI_CRASH_FILE"], load_ui=True, use_scripts=False
    )
    bpy.context.window_manager.EnableCamKeys = False
    bpy.app.timers.register(run, first_interval=2)
    return None


bpy.app.timers.register(start, first_interval=1)
