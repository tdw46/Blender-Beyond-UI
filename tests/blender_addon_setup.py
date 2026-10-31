"""Two real vendored consumers, retained panels, input, undo and lifecycle cleanup."""

import bpy, importlib, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = Path(os.environ["BEYOND_UI_CONSUMER_ROOT"])
sys.path.insert(0, str(PACKAGE_ROOT))
a = importlib.import_module("consumer_a.panels")
b = importlib.import_module("consumer_b.panels")


# Exercise two panels in one owner, including a Properties host.
class CONSUMER_PT_properties(bpy.types.Panel):
    bl_label = "Vendored properties"
    bl_idname = "CONSUMER_PT_properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_order = -1000

    def draw(self, context):
        self.layout.prop(context.scene.render, "film_transparent")


def register_a():
    a.ui.register(a.MYADDON_PT_settings, CONSUMER_PT_properties)


a.register = register_a
checks = []
state = {"stage": 0}
window = bpy.context.window
area = next(x for x in window.screen.areas if x.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(x for x in area.regions if x.type == "UI")


def emit(kind, value="PRESS", control=None):
    runtime = a.ui._runtime
    host = next(iter(runtime.hosts.values()))
    record = next(r for r in host.records.values() if r["valid"])
    canvas = record["canvas"]
    control = control or next(c for c in canvas.controls.values() if c.kind == "toggle")
    x, y, w, h = control.rect
    rx, ry, rw, rh = record["rect"]
    window.event_simulate(
        type=kind,
        value=value,
        x=int(region.x + rx + (x + w / 2) * rw / canvas._width),
        y=int(region.y + ry + rh - (y + h / 2) * rh / canvas.height),
    )
    return canvas


def finish(error=None):
    a.unregister()
    b.unregister()
    result = dict(
        passed=error is None, checks=checks, error=error, version=bpy.app.version_string
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    bpy.ops.wm.quit_blender()


def tick():
    global window, area, region
    try:
        n = state["stage"]
        if n == 0:
            # Different copies genuinely live under different import namespaces.
            assert a.ui.__class__.__module__ != b.ui.__class__.__module__
            a.register()
            props_area = next(x for x in window.screen.areas if x.type == "PROPERTIES")
            props_area.spaces.active.context = "RENDER"
            props_area.tag_redraw()
            b.register()
            a.register()
        elif n == 1:
            region.active_panel_category = "My Add-on"
        elif n == 2:
            props_host = a.ui._runtime.hosts[CONSUMER_PT_properties]
            assert props_host.records, "Properties panel was not anchored"
            assert all(x["available"] for x in a.ui.status["panels"].values()), (
                a.ui.status
            )
            assert a.ui._runtime.running and b.ui._runtime.running
            checks.append(
                "Two vendored packages and N-panel/Properties hosts register independently and auto-start input without draw-time timers"
            )
            state["before"] = bpy.context.scene.render.film_transparent
            emit("MOUSEMOVE", "NOTHING")
            state["canvas"] = emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 3:
            assert bpy.context.scene.render.film_transparent != state["before"]
            assert any(
                record["canvas"] is state["canvas"]
                for host in a.ui._runtime.hosts.values()
                for record in host.records.values()
            )
            emit("RIGHTMOUSE")
        elif n == 4:
            assert state["canvas"].context_menu
            assert (
                state["canvas"].context_menu.target.binding.context.name
                == "film_transparent"
            )
            emit("ESC")
            checks.append(
                "Actual custom toggle input and exact-property right-click menu; retained canvas across redraw"
            )
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.ed.undo()
        elif n == 5:
            assert bpy.context.scene.render.film_transparent == state["before"]
            checks.append(
                "Default commit creates working undo; undo invalidates old canvases"
            )
            a.ui.refresh()
            a.ui.refresh()
        elif n == 6:
            assert all(
                record["canvas"] is not state["canvas"]
                for host in a.ui._runtime.hosts.values()
                for record in host.records.values()
            )
            retired = a.ui._runtime
            a.unregister()
            a.unregister()
            assert not retired.classes and not retired.handlers and not retired.hosts
            assert not bpy.app.timers.is_registered(retired.start_callback)
            assert not bpy.app.timers.is_registered(retired.refresh_callback)
            assert b.ui.status["registered"]
            checks.append(
                "Refresh coalesces; idempotent teardown preserves the other consumer"
            )
            a.register()
        elif n == 7:
            assert a.ui._runtime.running
            checks.append("Unregister/register restores custom panel lifecycle")
        elif n == 8:
            state["generation"] = a.ui._runtime.generation
            bpy.ops.wm.read_factory_settings(use_empty=False)
        elif n == 9:
            window = bpy.context.window
            area = next(x for x in window.screen.areas if x.type == "VIEW_3D")
            area.spaces.active.show_region_ui = True
            region = next(x for x in area.regions if x.type == "UI")
            assert a.ui._runtime.generation > state["generation"]
            assert a.ui._runtime.running and b.ui._runtime.running
        elif n == 10:
            region.active_panel_category = "My Add-on"
        elif n == 11:
            assert a.ui._runtime.running
            emit("MOUSEMOVE", "NOTHING")
            checks.append(
                "Factory file load rebuilds input ownership and invalidates old generations"
            )
            finish()
            return None
        state["stage"] += 1
        return 0.6
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1, persistent=True)
