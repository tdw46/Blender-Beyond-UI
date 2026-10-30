"""Real N-panel mouse, text, picker and context input for custom panel popovers."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from popovers_fixture import build as build_fixture, register, unregister

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


def child_click(label, kind="LEFTMOUSE", number=False):
    canvas = current()[1]
    widget = canvas.overlay["widget"]
    child = widget.canvas
    c = next(c for c in child.controls.values() if c.label == label)
    rect = c.rect
    if number:
        from beyond_ui.scalar_geometry import slider_parts

        rect = slider_parts(rect)[2]
    a, b, w, h = rect
    left, top, _, _ = canvas.overlay["rect"]
    point = (left + a + w / 2, top + b + h / 2 - widget.scroll)
    emit(kind, logical=point)
    if kind == "LEFTMOUSE":
        emit(kind, "RELEASE", logical=point)


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
            state["before"] = bpy.context.scene.render.film_transparent
            opener = next(
                c
                for c in current()[1].controls.values()
                if c.label == "Render Controls"
            )
            emit("LEFTMOUSE", where=opener)
        elif n == 2:
            assert current()[1].overlay is not None, current()[1].menu_error
            child_click("Transparent")
        elif n == 3:
            assert bpy.context.scene.render.film_transparent != state["before"]
            child_click("Scale", "RIGHTMOUSE")
        elif n == 4:
            assert current()[1].active_menu() is not None
            assert any(
                r.label == "Copy Full Data Path"
                for r in current()[1].active_menu().page.rows
            )
            emit("ESC")
        elif n == 5:
            assert current()[1].active_menu() is None
            child_click("Scale", number=True)
        elif n == 6:
            child = current()[1].overlay["widget"].canvas
            assert child.editor is not None
            emit("A", oskey=True)
            for char in "64":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 7:
            emit("RET")
        elif n == 8:
            assert bpy.context.scene.render.resolution_percentage == 64
            child_click("Nested Controls")
        elif n == 9:
            assert current()[1].overlay["widget"].canvas.overlay is not None
            emit("ESC")
        elif n == 10:
            assert current()[1].overlay is not None
            assert current()[1].overlay["widget"].canvas.overlay is None
            emit("ESC")
        elif n == 11:
            assert current()[1].overlay is None
            c = next(c for c in current()[1].controls.values() if c.label == "Display")
            emit("LEFTMOUSE", where=c)
        elif n == 12:
            child_click("Wire")
        elif n == 13:
            assert bpy.context.object.display_type == "WIRE"
            current()[1].animation.enabled = False
            current()[1].cancel()
        elif n == 14:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual N-panel input opens custom panel popovers and toggles their RNA fields",
                "Right-click inside a popover exposes exact property actions; keyboard edits commit a slider number field",
                "Escape dismisses the nested child before its parent; property-attached popovers retain exact enum owners",
                "Shared animation/tooltip timers settle and teardown clears all child state",
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
