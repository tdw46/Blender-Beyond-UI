"""Real N-panel mouse, text, picker and context input for custom registered menus."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from registered_menus_fixture import build as build_fixture, register, unregister

register()

layouts = {}
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui, settings, many, attached, commits = build_fixture(bpy.context)
    layouts[key] = (ui, settings, many, attached, commits)
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


def click_row(label, kind="LEFTMOUSE"):
    menu = current()[1].context_menu
    rect = next(r for i, r, row in menu.visible_rows() if row.label == label)
    emit(kind, logical=(rect[0] + rect[2] / 2, rect[1] + rect[3] / 2))


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
            emit("LEFTMOUSE", where="button")
        elif n == 2:
            assert current()[1].context_menu is not None, current()[1].menu_error
            click_row("Transparent")
        elif n == 3:
            assert bpy.context.scene.render.film_transparent != state["before"]
            emit("LEFTMOUSE", where="enum")
        elif n == 4:
            click_row("Wire")
        elif n == 5:
            assert bpy.context.object.display_type == "WIRE"
            emit("LEFTMOUSE", where="button")
        elif n == 6:
            click_row("Scale", "RIGHTMOUSE")
        elif n == 7:
            menu = current()[1].context_menu
            assert menu.parents and any(r.key == "FULL_PATH" for r in menu.page.rows)
            emit("LEFT_ARROW")
        elif n == 8:
            click_row("Scale")
        elif n == 9:
            assert current()[1].context_menu.editor is not None
            emit("A", oskey=True)
            for char in "64":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 10:
            emit("RET")
        elif n == 11:
            assert bpy.context.scene.render.resolution_percentage == 64
            emit("ESC")
        elif n == 12:
            assert current()[1].context_menu is None
            emit("LEFTMOUSE", where="toggle")
        elif n == 13:
            assert bpy.context.scene.render.film_transparent == state["before"]
            current()[1].animation.enabled = False
            current()[1].cancel()
        elif n == 14:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Real N-panel clicks open registered and property-attached menus and apply their exact RNA values",
                "Right-click menu row opens exact property context actions; Back restores the parent",
                "Native keyboard input edits an inline menu field and commits its value",
                "Inline menu contents retain source toggle interactions and shared motion teardown",
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
