"""Isolated real CamKeys consumer qualification; never imports the live checkout."""
import bpy, importlib.util, os, sys, json, traceback
from pathlib import Path

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"]).resolve()
assert (source / "__init__.py").is_file(), source
spec = importlib.util.spec_from_file_location("camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)])
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
        ar = area if cls.bl_space_type == "VIEW_3D" else next(a for a in window.screen.areas if a.type == "PROPERTIES")
        reg = region if ar is area else next(r for r in ar.regions if r.type == "WINDOW")
        result = dict(state=label, panel=cls.__name__)
        with bpy.context.temp_override(window=window, area=ar, region=reg):
            try:
                tape = Tape()
                runtime.draw_functions[cls](PanelProxy(cls, tape.root), bpy.context)
                layout = Layout(context=bpy.context)
                tape.play(layout)
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
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(dict(passed=error is None, qualification="mixed custom/native compatibility; not full custom migration", version=bpy.app.version_string, source=str(source), checks=checks, audits=audits, glass=glass, status=status, performance=state.get("performance"), error=error), indent=2, default=str))
    bpy.ops.wm.quit_blender()


def invoke(name, **kwargs):
    with bpy.context.temp_override(window=window, area=area, region=main_region):
        return getattr(bpy.ops.camkeys, name)("INVOKE_DEFAULT", **kwargs)


def event(kind, value="PRESS", point=None):
    x, y = point or (main_region.width / 2, main_region.height / 2)
    window.event_simulate(type=kind, value=value, x=int(main_region.x+x), y=int(main_region.y+y))


def dialog():
    return next(iter(addon.__beyond_ui_integration__.router.dialogs.values()))


def click(control, button="LEFTMOUSE"):
    d = dialog()
    x, y, _, _ = d.host.canvas.overlay["rect"]
    a, b, c, e = control.rect
    scale = d.host.scale
    point = ((x+a+c/2)*scale, main_region.height-(y+b+e/2)*scale)
    event("MOUSEMOVE", "NOTHING", point)
    event(button, point=point)
    event(button, "RELEASE", point)


def audit_glass(host):
    from camkeys_qa._vendor.beyond_ui.gpu import glass as renderer
    record = host.records[host.key]
    assert record.get("backdrop"), (host.reason, record.get("glass_error"))
    glass.append(dict(productions=renderer._owners[record["backdrop"]]["productions"], error=record["glass_error"]))


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
            assert addon.__beyond_ui_integration__.status["host"]["native_fallbacks"]
            from camkeys_qa._vendor.beyond_ui.bindings import rna_binding
            from camkeys_qa._vendor.beyond_ui.context_extensions import collect
            from camkeys_qa._vendor.beyond_ui.context_menu import Target
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                bpy.ops.ed.undo_push(message="Before CamKeys contribution")
                binding = rna_binding(lambda: bpy.context.scene.camera.data, "lens")
                entries = collect(bpy.context, binding.context, (addon.utils.draw_camprop_context_menu,))
                row = next(r for r in entries if r.label == "Add to CamProps")
                target = Target("lens", binding=binding, valid=binding.valid)
                assert row.enabled(target, bpy.context)
                assert row.action(target, bpy.context) == {"FINISHED"}
            prop = bpy.context.scene.mesh_object_items[0].cam_prop_items[0]
            assert prop.prop_identifier == "lens"
            assert prop.target_full_datapath.endswith('.lens'), prop.target_full_datapath
            assert bpy.context.scene.camera.data.name in prop.target_full_datapath
            checks.append("Actual Add to CamProps contribution executes against the exact clicked camera lens")
            region.tag_redraw()
        elif n == 3:
            audit("camprop-populated")
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert len(bpy.context.scene.mesh_object_items[0].cam_prop_items) == 0
            scene = bpy.context.scene
            rig = bpy.data.objects.new("Consumer Rig", bpy.data.armatures.new("Consumer Rig"))
            scene.collection.objects.link(rig)
            for obj in bpy.context.selected_objects: obj.select_set(False)
            rig.select_set(True)
            bpy.context.view_layer.objects.active = rig
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                bpy.ops.object.mode_set(mode="EDIT")
                for name, z in (("head", 2), ("pivot", 0)):
                    bone = rig.data.edit_bones.new(name)
                    bone.head = (0, 0, z)
                    bone.tail = (0, 0, z+1)
                bpy.ops.object.mode_set(mode="OBJECT")
            mesh = bpy.data.objects["Cube"]
            mesh.modifiers.new("Consumer Rig", "ARMATURE").object = rig
            bpy.context.view_layer.objects.active = mesh
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                bpy.ops.ed.undo_push(message="Before Billboard Groups")
            assert invoke("billboard_groups", action="DEFAULTS", item_index=0, root_bone="head", body_bone="pivot") == {"RUNNING_MODAL"}
        elif n == 4:
            d = dialog()
            audit_glass(d.host)
            assert d.operator.root_bone == "head" and d.operator.body_bone == "pivot"
            assert len([c for c in d.canvas.controls.values() if c.kind == "search"]) == 2
            click(d.canvas.controls["confirm"])
        elif n == 5:
            assert not addon.__beyond_ui_integration__.router.dialogs
            groups = bpy.context.scene.mesh_object_items[0].stepped_turnaround.billboard_groups
            assert len(groups) == 2 and any(g.root_bone == "head" for g in groups)
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert len(bpy.context.scene.mesh_object_items[0].stepped_turnaround.billboard_groups) == 0
            checks.append("Real Billboard Groups dialog retains prefilled bone search fields, executes once and supports native undo")
            assert invoke("export_curve") == {"RUNNING_MODAL"}
        elif n == 6:
            d = dialog()
            audit_glass(d.host)
            field = next(c for c in d.canvas.controls.values() if c.binding and getattr(c.binding.context, "name", "") == "curve_name")
            click(field, "RIGHTMOUSE")
        elif n == 7:
            assert dialog().canvas.context_menu.target.binding.context.name == "curve_name"
            event("ESC")
        elif n == 8:
            assert not dialog().canvas.context_menu
            event("ESC")
        elif n == 9:
            router = addon.__beyond_ui_integration__.router
            assert not router.dialogs
            checks.append("Real export dialog exposes exact operator-property context actions and cancels without writing files")
            with bpy.context.temp_override(window=window, area=area, region=main_region):
                router.menu(bpy.context, None, name="CAMKEYS_MT_mesh_object_items_menu")
        elif n == 10:
            host = next(iter(addon.__beyond_ui_integration__.router.menus.values()))
            audit_glass(host)
            assert host.canvas.context_menu.page.rows
            event("ESC")
        elif n == 11:
            assert not addon.__beyond_ui_integration__.router.menus
            checks.append("Real registered CamKeys menu opens through the custom engine and dismisses cleanly")
            bpy.context.window_manager.EnableCamKeys = True
            audit("enabled")
            bpy.context.window_manager.EnableCamKeys = False
            scene = bpy.context.scene
            lattice = bpy.data.objects.new("Consumer Lattice", bpy.data.lattices.new("Consumer Lattice"))
            scene.collection.objects.link(lattice)
            bpy.data.objects["Cube"].modifiers.new("Consumer Lattice", "LATTICE").object = lattice
            item = scene.mesh_object_items.add()
            item.object = lattice
            scene.mesh_object_items_index = 1
            bpy.context.view_layer.objects.active = lattice
            props = next(a for a in window.screen.areas if a.type == "PROPERTIES")
            props.spaces.active.context = "MODIFIER"
            props.tag_redraw()
        elif n == 12:
            audit("lattice-properties")
            assert all(r["passed"] or r.get("compatibility") for r in audits), audits
            assert not addon.__beyond_ui_integration__.status["host"]["draw_errors"]
            checks.append("Six panel definitions audited across empty, mesh, CamProp, enabled and lattice contexts; unsafe lists explicitly use native compatibility")
            state["old_runtime"] = addon.__beyond_ui_integration__.ui._runtime
            addon.unregister()
            assert not state["old_runtime"].active and not state["old_runtime"].hosts
            assert not bpy.app.timers.is_registered(addon.utils.delayed_start)
            addon.register()
            bpy.context.window_manager.EnableCamKeys = False
            region.tag_redraw()
        elif n == 13:
            assert addon.__beyond_ui_integration__.running
            assert not addon.__beyond_ui_integration__.status["host"]["draw_errors"]
            checks.append("CamKeys disable/re-enable restores original classes and closes custom hosts, without retaining its startup timer")
            finish()
            return None
        state["step"] += 1
        return 0.8
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
