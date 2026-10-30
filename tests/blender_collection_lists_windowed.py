"""Real N-panel mouse, text, picker and context input for collection lists."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from lists_fixture import build as build_fixture, register, unregister

register()

layouts = {}
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui, commits = build_fixture(bpy.context)
    layouts[key] = (ui, commits)
    return ui.canvas


demo.build_canvas = build
demo.register()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
state = {"stage": 0, "checks": []}


def current():
    r = next(r for r in demo._host.records.values() if r["valid"])
    return r, r["canvas"]


def control(kind):
    return next(c for c in current()[1].controls.values() if c.kind == kind)


def emit(kind, value="PRESS", where="button", logical=None, **mods):
    record, canvas = current()
    c = where if not isinstance(where, str) else control(where)
    a, b, w, h = c.rect
    lx, ly = logical or (a + w / 2, b + h / 2)
    rx, ry, rw, rh = record["rect"]
    x = int(region.x + rx + lx * rw / canvas._width)
    y = int(region.y + ry + rh - ly * rh / canvas.height)
    window.event_simulate(type=kind, value=value, x=x, y=y, **mods)


def finish(passed, error=""):
    demo.unregister()
    unregister()
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("OPERATOR_ENUM_WINDOWED", result, flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["stage"]
        if n == 0:
            region.active_panel_category = "Beyond UI"
        elif n == 1:
            assert demo._host.bridge is not None, demo._host.reason
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            c = control("widget")
            state["point"] = (c.rect[0] + 30, c.rect[1] + 40)
            emit("LEFTMOUSE", where=c, logical=state["point"])
            emit("LEFTMOUSE", "RELEASE", where=c, logical=state["point"])
        elif n == 2:
            assert bpy.context.scene.bui_list_active == 1
            emit(
                "LEFTMOUSE", where=control("widget"), logical=state["point"], ctrl=True
            )
        elif n == 3:
            widget = control("widget").options["widget"]
            assert widget.text_edit is not None
            emit("A", where=control("widget"), oskey=True)
            for char in "Windowed Layer":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 4:
            emit("RET", where=control("widget"))
        elif n == 5:
            assert bpy.context.scene.bui_list_items[1].name == "Windowed Layer"
            emit("RIGHTMOUSE", where=control("widget"), logical=state["point"])
        elif n == 6:
            assert current()[1].context_menu is not None, current()[1].menu_error
            assert any(
                r.label == "Copy Full Data Path"
                for r in current()[1].context_menu.page.rows
            )
            emit("ESC", where=control("widget"))
        elif n == 7:
            assert current()[1].context_menu is None
            emit("DOWN_ARROW", where=control("widget"))
        elif n == 8:
            assert bpy.context.scene.bui_list_active == 2
            current()[1].animation.enabled = False
            current()[1].cancel()
        elif n == 9:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual N-panel mouse selects collection rows; Ctrl-click starts rename and keyboard commits",
                "Exact row context actions use the shared menu; keyboard navigation changes original active index",
                "Host animation timers settle; unregister releases all owned runtime state",
            ]
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.65
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
