"""Real N-panel or Properties host: event simulation, context and lifecycle."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout
import action_parity_fixture as fixture

fixture.register()
spec = importlib.util.spec_from_file_location(
    "core_host_demo", ROOT / "examples/demo.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui = Layout(context=bpy.context)
    ui.canvas.menu_commit = lambda action: None
    ui.title(text="Core host verification")
    ui.prop(bpy.context.scene.render, "film_transparent", text="Transparent")
    ui.prop(bpy.context.scene.render, "filepath", text="Output")
    ui.prop(
        bpy.context.scene.render, "resolution_percentage", text="Scale", slider=True
    )
    ui.popover("BUI_PT_parity_confirm", text="Review Changes")
    return ui.canvas


demo.build_canvas = build
mode = os.environ.get("BEYOND_UI_CORE_HOST", "N_PANEL")


class CORE_PT_properties(bpy.types.Panel):
    bl_label = "Beyond UI Core"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    draw = demo.BEYONDUIDEMO_PT_panel.draw


demo.register()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
if mode == "PROPERTIES":
    bpy.utils.register_class(CORE_PT_properties)
    area.type = "PROPERTIES"
    region = next(r for r in area.regions if r.type == "WINDOW")
else:
    area.spaces.active.show_region_ui = True
    region = next(r for r in area.regions if r.type == "UI")
state = {"stage": 0, "checks": []}


def current():
    r = demo._host.records[
        (window.as_pointer(), area.as_pointer(), region.as_pointer())
    ]
    assert r["valid"] and r.get("backdrop") is not None, r
    return r, r["canvas"]


def named(label):
    return next(c for c in current()[1].controls.values() if c.label == label)


def emit(kind, value="PRESS", label="Transparent"):
    r, c = current()
    a, b, w, h = named(label).rect
    x, y, rw, rh = r["rect"]
    window.event_simulate(
        type=kind,
        value=value,
        x=int(region.x + x + (a + w / 2) * rw / c._width),
        y=int(region.y + y + rh - (b + h / 2) * rh / c.height),
    )


def finish(passed, error=""):
    try:
        demo.unregister()
        if mode == "PROPERTIES":
            bpy.utils.unregister_class(CORE_PT_properties)
        fixture.unregister()
    except Exception:
        passed = False
        error += traceback.format_exc()
    result = dict(
        passed=passed,
        error=error,
        host=mode,
        version=bpy.app.version_string,
        checks=state["checks"],
        visual_acceptance=False,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result), flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["stage"]
        if n == 0:
            if mode == "N_PANEL":
                region.active_panel_category = "Beyond UI"
            else:
                with bpy.context.temp_override(window=window, area=area, region=region):
                    area.spaces.active.context = "SCENE"
        elif n == 1:
            assert demo._host.bridge is not None, demo._host.reason
            r, c = current()
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["before"] = bpy.context.scene.render.film_transparent
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            emit("MOUSEMOVE", "NOTHING")
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 2:
            assert bpy.context.scene.render.film_transparent != state["before"]
            state["checks"].append(
                "Real host GPU anchor and simulated modal toggle input"
            )
            emit("RIGHTMOUSE", label="Output")
        elif n == 3:
            r, c = current()
            assert c.context_menu, c.menu_error
            assert c.context_menu.target.binding.context.name == "filepath"
            state["checks"].append(
                "Real right-click reaches exact property context menu"
            )
            emit("ESC")
        elif n == 4:
            assert current()[1].context_menu is None
            emit("LEFTMOUSE", label="Review Changes")
            emit("LEFTMOUSE", "RELEASE", label="Review Changes")
        elif n == 5:
            r, c = current()
            assert c.overlay, c.menu_error
            state["checks"].append(
                "Registered confirmation popup opens through real host input"
            )
            emit("ESC")
        elif n == 6:
            r, c = current()
            assert c.overlay is None
            x, y, w, h = r["clip"]
            rx, ry, rw, rh = r["rect"]
            assert w > 0 and h > 0 and x >= rx - 1 and x + w <= rx + rw + 1
            canvas_count = c.layout_count
            c.arrange(c._width)
            assert c.layout_count == canvas_count
            demo._host.animation.enabled = False
            assert not c.advance_animations()
            state["checks"].append(
                "Host clip bounds, retained warm layout and runtime motion disable"
            )
            c._begin(named("Output"))
            old = bpy.context.scene.render.filepath
            c._write("//transient/")
            demo._host.invalidate()
            assert bpy.context.scene.render.filepath == old
            demo._host.close()
            emit_dummy = window.event_simulate(
                type="MOUSEMOVE", value="NOTHING", x=10, y=10
            )
        elif n == 7:
            assert not demo._running
            state["checks"].append(
                "Host invalidation rolls back editing and stops owned modal input"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.5
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
