"""Isolated real CamKeys consumer qualification; never imports the live checkout."""

import bpy, importlib.util, os, sys, json, traceback
from pathlib import Path

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"]).resolve()
assert (source / "__init__.py").is_file(), source
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
state = {"step": 0}
checks, audits, glass = [], [], []
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "UI")
main_region = next(r for r in area.regions if r.type == "WINDOW")
area.spaces.active.show_region_ui = True


def audit(label):
    from camkeys_qa._vendor.beyond_ui.layout_recording import Tape
    from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
    from camkeys_qa._vendor.beyond_ui import Layout

    runtime = addon.__beyond_ui_integration__.ui._runtime
    for cls in runtime.definitions:
        ar = (
            area
            if cls.bl_space_type == "VIEW_3D"
            else next(a for a in window.screen.areas if a.type == "PROPERTIES")
        )
        reg = (
            region if ar is area else next(r for r in ar.regions if r.type == "WINDOW")
        )
        result = dict(state=label, panel=cls.__name__)
        with bpy.context.temp_override(window=window, area=ar, region=reg):
            try:
                tape = Tape()
                runtime.draw_functions[cls](PanelProxy(cls, tape.root), bpy.context)
                layout = Layout(
                    context=bpy.context,
                    **addon.__beyond_ui_integration__.ui.layout_options,
                )
                for attempt in range(8):
                    try:
                        sheet = getattr(addon.__beyond_ui_integration__.ui, "stylesheet", None)
                        if sheet is not None:
                            sheet.apply(layout.canvas)
                        tape.play(layout)
                        break
                    except Exception:
                        ids = addon.__beyond_ui_integration__.list_ids
                        if not ids.pending or attempt == 7:
                            raise
                        ids.flush()
                        layout = Layout(
                            context=bpy.context,
                            **addon.__beyond_ui_integration__.ui.layout_options,
                        )
                result.update(controls=len(layout.canvas.controls), passed=True)
                layout.canvas.park()
            except Exception:
                result.update(passed=False, error=traceback.format_exc())
                from camkeys_qa._vendor.beyond_ui.list_source import UnsafeListIdentity

                if isinstance(sys.exc_info()[1], UnsafeListIdentity):
                    result.update(compatibility="native: stable row identity required")
        audits.append(result)


def finish(error=None):
    status = addon.__beyond_ui_integration__.status
    try:
        addon.unregister()
    except Exception:
        error = (error or "") + traceback.format_exc()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(
            dict(
                passed=error is None,
                qualification="custom collection and brush curve consumer checks",
                version=bpy.app.version_string,
                source=str(source),
                checks=checks,
                audits=audits,
                glass=glass,
                status=status,
                performance=state.get("performance"),
                error=error,
            ),
            indent=2,
            default=str,
        )
    )
    bpy.ops.wm.quit_blender()


def invoke(name, **kwargs):
    with bpy.context.temp_override(window=window, area=area, region=main_region):
        return getattr(bpy.ops.camkeys, name)("INVOKE_DEFAULT", **kwargs)


def event(kind, value="PRESS", point=None):
    x, y = point or (main_region.width / 2, main_region.height / 2)
    window.event_simulate(
        type=kind, value=value, x=int(main_region.x + x), y=int(main_region.y + y)
    )


def dialog():
    return next(iter(addon.__beyond_ui_integration__.router.dialogs.values()))


def click(control, button="LEFTMOUSE"):
    d = dialog()
    x, y, _, _ = d.host.canvas.overlay["rect"]
    a, b, c, e = control.rect
    scale = d.host.scale
    point = (d.host.rect[0] + (x + a + c / 2) * scale, d.host.rect[1] + d.host.rect[3] - (y + b + e / 2) * scale)
    event("MOUSEMOVE", "NOTHING", point)
    event(button, point=point)
    event(button, "RELEASE", point)


def audit_glass(host):
    from camkeys_qa._vendor.beyond_ui.gpu import glass as renderer

    record = host.records[host.key]
    assert record.get("backdrop"), (host.reason, record.get("glass_error"))
    glass.append(
        dict(
            productions=renderer._owners[record["backdrop"]]["productions"],
            error=record["glass_error"],
        )
    )


def custom_checks():
    from types import SimpleNamespace as NS
    from unittest.mock import patch
    from camkeys_qa._vendor.beyond_ui import Layout
    from camkeys_qa._vendor.beyond_ui.list_identity import KEY
    from camkeys_qa._vendor.beyond_ui.list_source import (
        CollectionSource,
        UnsafeListIdentity,
    )
    from camkeys_qa._vendor.beyond_ui.widgets.context import target
    from camkeys_qa._vendor.beyond_ui.widgets.metrics import CURVE
    from camkeys_qa._vendor.beyond_ui.context_menu import default_entries

    from camkeys_qa import custom_curve_lifecycle

    assert custom_curve_lifecycle.restore_curves in bpy.app.handlers.undo_post
    ui_config = addon.__beyond_ui_integration__.ui
    ids = addon.__beyond_ui_integration__.list_ids
    scene = bpy.context.scene
    rows = scene.mesh_object_items
    first = rows[0].get(KEY)
    extra = rows.add()
    extra.name = "Identity test"
    with bpy.context.temp_override(window=window, area=area, region=main_region):
        ui = Layout(context=bpy.context, **ui_config.layout_options)
        try:
            CollectionSource(
                ui, scene, "mesh_object_items", scene, "mesh_object_items_index"
            )
        except UnsafeListIdentity:
            pass
        assert KEY not in extra, "Drawing assigned persistent IDs"
        ids.flush()
        source = CollectionSource(
            ui, scene, "mesh_object_items", scene, "mesh_object_items_index"
        )
        old = source.items[0]
        rows.move(0, 1)
        assert rows[1][KEY] == first
        assert not source.valid_item(old), (
            "A stale row resolved to the new storage occupant"
        )
        source.refresh()
        assert source.items[1].identity == first
        source.select(source.items[1])
        assert scene.mesh_object_items_index == 1
        # Duplicated IDs revoke BOTH tokens, rather than guessing which is original.
        rows[0][KEY] = first
        try:
            source.refresh()
        except UnsafeListIdentity:
            pass
        ids.flush()
        assert len({r[KEY] for r in rows}) == 2 and all(r[KEY] != first for r in rows)
        assert not source.valid_item(old)
        rows.remove(0)
        scene.mesh_object_items_index = 0
        source.refresh()
        removed = source.items[0]
        replacement = rows.add()
        # Delete the snapshot's row; even identical names do not inherit its identity.
        saved_object = rows[0].object
        rows.remove(0)
        rows[0].object = saved_object
        assert not source.valid_item(removed)
        try:
            source.refresh()
        except UnsafeListIdentity:
            ids.flush()
        source.refresh()
        checks.append(
            "Persistent list IDs initialize outside draw, survive reorder, reject stale/deleted rows and repair duplicate IDs"
        )
        item = rows[0]
        for panel, prop in [
            ("CAMKEYS_PT_falloff_popover", "auto_fov_multi_falloff_type"),
            ("CAMKEYS_PT_distance_falloff_popover", "auto_fov_falloff_type"),
            ("CAMKEYS_PT_flatten_falloff_popover", "auto_fov_flatten_falloff_type"),
        ]:
            item = bpy.context.scene.mesh_object_items[0]
            setattr(item, prop, "CUSTOM")
            ui = Layout(
                context=bpy.context,
                commit=lambda before, after: bpy.ops.ed.undo_push(
                    message="Custom brush edit"
                ),
                **ui_config.layout_options,
            )
            ui.context_pointer_set("camkeys_falloff_owner", item)
            ui.popover(panel=panel, text="Curve")
            parent = ui.canvas
            parent.arrange(460)
            control = next(
                c for c in parent.controls.values() if c.options.get("panel_model")
            )
            assert parent.open_panel(control, (0, 0, 460, 900), bpy.context), (
                parent.menu_error
            )
            popup = parent.overlay["widget"]
            child = popup.canvas
            cc = next(
                c
                for c in child.controls.values()
                if c.kind == "widget" and getattr(c.options["widget"], "brush", False)
            )
            widget = cc.options["widget"]
            assert widget.binding.valid()
            # Brush setup has already happened. Repeated custom authoring is read-only.
            from camkeys_qa._vendor.beyond_ui.popover import PanelProxy
            from camkeys_qa._vendor.beyond_ui.hosts.menu_context import override

            cls = control.options["panel_model"].cls
            with (
                patch.object(
                    addon.utils,
                    "ensure_timer_running",
                    side_effect=AssertionError("draw timer"),
                ),
                patch.object(
                    addon.utils,
                    "get_or_create_mesh_falloff_brush",
                    side_effect=AssertionError("draw write"),
                ),
            ):
                with override(bpy.context, {"camkeys_falloff_owner": item}):
                    cls.draw(PanelProxy(cls, Layout(context=bpy.context)), bpy.context)
            before = widget.binding.read()
            a, b, w, h = widget.graph
            px, py = before[0]
            send = lambda kind, x, y, value="PRESS": widget.event(
                NS(type=kind, value=value), x, y
            )
            send("LEFTMOUSE", a + px * w, b + (1 - py) * h)
            send("MOUSEMOVE", a + 0.25 * w, b + 0.6 * h, "NOTHING")
            send("RIGHTMOUSE", a + 0.25 * w, b + 0.6 * h)
            assert widget.binding.read() == before, "Curve drag cancel changed data"
            send("LEFTMOUSE", CURVE["tabs"][1][0] + 4, CURVE["tabs"][1][1] + 4)
            assert widget.binding.handle(widget.selected).read() == "VECTOR"
            hit = target(
                widget, cc.key, CURVE["fields"][2][0] + 5, CURVE["fields"][2][1] + 5
            )
            assert hit.binding.context.name == "handle_type"
            assert any(
                r.label == "Copy Full Data Path"
                for r in default_entries(hit, bpy.context)
            )
            old_hit = hit
            # Use the actual CamKeys preset and its recorded brush context.
            with override(
                bpy.context, control.options["panel_model"].pointers.values()
            ):
                from camkeys_qa import custom_curve_lifecycle

                kind = (
                    "mesh"
                    if prop == "auto_fov_multi_falloff_type"
                    else "distance"
                    if prop == "auto_fov_falloff_type"
                    else "flatten"
                )
                brush = custom_curve_lifecycle.lookup(kind, item)
                with override(bpy.context, {"brush": brush}):
                    assert bpy.ops.camkeys.curve_preset(
                        "EXEC_DEFAULT", True, shape="SMOOTH"
                    ) == {"FINISHED"}
            send("MOUSEMOVE", a, b, "NOTHING")
            assert widget.binding.valid() and len(widget.binding.read()) == 3
            assert not old_hit.valid() or not old_hit.binding.valid(), (
                "Old point menu survived a preset"
            )
            send("LEFTMOUSE", a + 0.6 * w, b + 0.6 * h, "DOUBLE_CLICK")
            assert widget.binding.valid() and len(widget.binding.read()) == 4
            widget.selected = len(widget.binding.read()) - 1
            send("DEL", a, b)
            assert len(widget.binding.read()) == 3
            # Exact middle-point removal preserves the neighboring handle modes.
            widget.selected = 1
            endpoints = (
                widget.binding.handle(0).read(),
                widget.binding.handle(2).read(),
            )
            send("DEL", a, b)
            assert len(widget.binding.read()) == 2
            assert (
                widget.binding.handle(0).read(),
                widget.binding.handle(1).read(),
            ) == endpoints
            assert not bpy.app.timers.is_registered(
                addon.utils.auto_fov_curve_sync_timer
            )
            # A completed custom edit is one native undo step.
            prior = widget.binding.read()
            brush_name = brush.name
            bpy.ops.ed.undo_push(message="Before custom point edit")
            send("LEFTMOUSE", a + 0.7 * w, b + 0.3 * h, "DOUBLE_CLICK")
            assert len(widget.binding.read()) == len(prior) + 1
            assert bpy.ops.ed.undo() == {"FINISHED"}
            restored = addon.utils.get_falloff_curve_mapping(
                bpy.data.brushes[brush_name]
            )
            assert (
                tuple(tuple(p.location) for p in restored.curves[0].points) == prior
            ), (prior, tuple(tuple(p.location) for p in restored.curves[0].points))
            assert bpy.ops.ed.redo() == {"FINISHED"}
            redone = addon.utils.get_falloff_curve_mapping(bpy.data.brushes[brush_name])
            assert len(redone.curves[0].points) == len(prior) + 1
            assert bpy.ops.ed.undo() == {"FINISHED"}
            parent.park()
        checks.append(
            "Three actual CamKeys brush popovers: read-only drawing, exact handle context, drag cancellation, presets, point deletion and idle timer cleanup"
        )


def tick():
    try:
        n = state["step"]
        if n == 0:
            addon.register()
            bpy.context.window_manager.EnableCamKeys = False
            region.tag_redraw()
        elif n == 1:
            region.active_panel_category = "CamKeys"
            audit("empty")
            scene = bpy.context.scene
            obj = bpy.data.objects["Cube"]
            obj.shape_key_add(name="Basis")
            obj.shape_key_add(name="Smile")
            item = scene.mesh_object_items.add()
            item.object = obj
            scene.mesh_object_items_index = 0
            region.tag_redraw()
        elif n == 2:
            audit("tracked-mesh")
            assert not addon.__beyond_ui_integration__.status["host"]["draw_errors"]
            assert all(r["passed"] for r in audits), audits
            from camkeys_qa._vendor.beyond_ui.bindings import rna_binding
            from camkeys_qa._vendor.beyond_ui.context_extensions import collect
            from camkeys_qa._vendor.beyond_ui.context_menu import Target

            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                bpy.ops.ed.undo_push(message="Before CamKeys contribution")
                binding = rna_binding(lambda: bpy.context.scene.camera.data, "lens")
                entries = collect(
                    bpy.context,
                    binding.context,
                    (addon.utils.draw_camprop_context_menu,),
                )
                row = next(r for r in entries if r.label == "Add to CamProps")
                target = Target("lens", binding=binding, valid=binding.valid)
                assert row.enabled(target, bpy.context)
                assert row.action(target, bpy.context) == {"FINISHED"}
            prop = bpy.context.scene.mesh_object_items[0].cam_prop_items[0]
            assert prop.prop_identifier == "lens"
            assert prop.target_full_datapath.endswith(".lens"), (
                prop.target_full_datapath
            )
            assert bpy.context.scene.camera.data.name in prop.target_full_datapath
            checks.append(
                "Actual Add to CamProps contribution executes against the exact clicked camera lens"
            )
            region.tag_redraw()
        elif n == 3:
            audit("camprop-populated")
            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert len(bpy.context.scene.mesh_object_items[0].cam_prop_items) == 0
            scene = bpy.context.scene
            rig = bpy.data.objects.new(
                "Consumer Rig", bpy.data.armatures.new("Consumer Rig")
            )
            scene.collection.objects.link(rig)
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            rig.select_set(True)
            bpy.context.view_layer.objects.active = rig
            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                bpy.ops.object.mode_set(mode="EDIT")
                for name, z in (("head", 2), ("pivot", 0)):
                    bone = rig.data.edit_bones.new(name)
                    bone.head = (0, 0, z)
                    bone.tail = (0, 0, z + 1)
                bpy.ops.object.mode_set(mode="OBJECT")
            mesh = bpy.data.objects["Cube"]
            mesh.modifiers.new("Consumer Rig", "ARMATURE").object = rig
            bpy.context.view_layer.objects.active = mesh
            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                bpy.ops.ed.undo_push(message="Before Billboard Groups")
            assert invoke(
                "billboard_groups",
                action="DEFAULTS",
                item_index=0,
                root_bone="head",
                body_bone="pivot",
            ) == {"RUNNING_MODAL"}
        elif n == 4:
            d = dialog()
            audit_glass(d.host)
            assert d.operator.root_bone == "head" and d.operator.body_bone == "pivot"
            assert (
                len([c for c in d.canvas.controls.values() if c.kind == "search"]) == 2
            )
            click(d.canvas.controls["confirm"])
        elif n == 5:
            assert not addon.__beyond_ui_integration__.router.dialogs
            groups = bpy.context.scene.mesh_object_items[
                0
            ].stepped_turnaround.billboard_groups
            assert len(groups) == 2 and any(g.root_bone == "head" for g in groups)
            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert (
                len(
                    bpy.context.scene.mesh_object_items[
                        0
                    ].stepped_turnaround.billboard_groups
                )
                == 0
            )
            checks.append(
                "Real Billboard Groups dialog retains prefilled bone search fields, executes once and supports native undo"
            )
            assert invoke("export_curve") == {"RUNNING_MODAL"}
        elif n == 6:
            d = dialog()
            audit_glass(d.host)
            field = next(
                c
                for c in d.canvas.controls.values()
                if c.binding and getattr(c.binding.context, "name", "") == "curve_name"
            )
            click(field, "RIGHTMOUSE")
        elif n == 7:
            assert (
                dialog().canvas.context_menu.target.binding.context.name == "curve_name"
            )
            event("ESC")
        elif n == 8:
            assert not dialog().canvas.context_menu
            event("ESC")
        elif n == 9:
            router = addon.__beyond_ui_integration__.router
            assert not router.dialogs
            checks.append(
                "Real export dialog exposes exact operator-property context actions and cancels without writing files"
            )
            with bpy.context.temp_override(
                window=window, area=area, region=main_region
            ):
                router.menu(bpy.context, None, name="CAMKEYS_MT_mesh_object_items_menu")
        elif n == 10:
            host = next(iter(addon.__beyond_ui_integration__.router.menus.values()))
            audit_glass(host)
            assert host.canvas.context_menu.page.rows
            event("ESC")
        elif n == 11:
            assert not addon.__beyond_ui_integration__.router.menus
            checks.append(
                "Real registered CamKeys menu opens through the custom engine and dismisses cleanly"
            )
            custom_checks()
            bpy.context.window_manager.EnableCamKeys = True
            audit("enabled")
            bpy.context.window_manager.EnableCamKeys = False
            scene = bpy.context.scene
            lattice = bpy.data.objects.new(
                "Consumer Lattice", bpy.data.lattices.new("Consumer Lattice")
            )
            scene.collection.objects.link(lattice)
            bpy.data.objects["Cube"].modifiers.new(
                "Consumer Lattice", "LATTICE"
            ).object = lattice
            item = scene.mesh_object_items.add()
            item.object = lattice
            scene.mesh_object_items_index = 1
            bpy.context.view_layer.objects.active = lattice
            props = next(a for a in window.screen.areas if a.type == "PROPERTIES")
            props.spaces.active.context = "MODIFIER"
            props.tag_redraw()
        elif n == 12:
            audit("lattice-properties")
            assert all(r["passed"] for r in audits), audits
            assert not addon.__beyond_ui_integration__.status["host"]["draw_errors"]
            checks.append(
                "Six panel definitions audited across empty, mesh, CamProp, enabled and lattice contexts; custom list identities initialized and used"
            )
            state["old_runtime"] = addon.__beyond_ui_integration__.ui._runtime
            addon.unregister()
            assert not state["old_runtime"].active and not state["old_runtime"].hosts
            assert not bpy.app.timers.is_registered(addon.utils.delayed_start)
            from camkeys_qa import custom_curve_lifecycle

            assert (
                custom_curve_lifecycle.restore_curves not in bpy.app.handlers.undo_post
            )
            assert (
                custom_curve_lifecycle.restore_curves not in bpy.app.handlers.redo_post
            )
            addon.register()
            bpy.context.window_manager.EnableCamKeys = False
            region.tag_redraw()
        elif n == 13:
            assert addon.__beyond_ui_integration__.running
            assert not addon.__beyond_ui_integration__.status["host"]["draw_errors"]
            from camkeys_qa._vendor.beyond_ui.list_identity import KEY

            tokens = [r[KEY] for r in bpy.context.scene.mesh_object_items]
            path = str(
                Path(os.environ["BEYOND_UI_TEST_RESULT"]).parent
                / "identity-roundtrip.blend"
            )
            scene_name = bpy.context.scene.name
            bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
            with bpy.data.libraries.load(path) as (available, loaded):
                loaded.scenes = [scene_name]
            assert [r[KEY] for r in loaded.scenes[0].mesh_object_items] == tokens
            bpy.data.scenes.remove(loaded.scenes[0])
            checks.append(
                "Persistent row IDs survive a saved blend copy and reload into a separate scene"
            )
            assert not addon.__beyond_ui_integration__.status["host"][
                "native_fallbacks"
            ]
            checks.append(
                "CamKeys disable/re-enable restores original classes and closes custom hosts, without retaining its startup timer"
            )
            finish()
            return None
        state["step"] += 1
        return 0.8
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
