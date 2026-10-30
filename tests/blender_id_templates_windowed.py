"""Real N-panel mouse, text, picker and context input for custom ID templates."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from id_templates_fixture import build as build_fixture, register, unregister

register()

layouts = {}
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui, picker, name, fake = build_fixture(bpy.context)
    layouts[key] = (ui, picker, name, fake)
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
            state["before"] = bpy.context.scene.bui_ids.material.use_fake_user
            emit("LEFTMOUSE", where="toggle")
        elif n == 2:
            assert bpy.context.scene.bui_ids.material.use_fake_user != state["before"]
            emit("RIGHTMOUSE", where="toggle")
        elif n == 3:
            assert current()[1].context_menu is not None, current()[1].menu_error
            assert (
                current()[1].context_menu.target.binding.context.name == "use_fake_user"
            )
            emit("ESC", where="toggle")
        elif n == 4:
            emit("LEFTMOUSE", where="text")
        elif n == 5:
            assert current()[1].editor is not None
            emit("A", where="text", oskey=True)
            for char in "Renamed from N-panel":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 6:
            emit("RET", where="text")
        elif n == 7:
            assert bpy.context.scene.bui_ids.material.name == "Renamed from N-panel"
            emit("LEFTMOUSE", where="pointer")
        elif n == 8:
            assert current()[1].overlay is not None, current()[1].menu_error
            emit("END", where="pointer")
            emit("RET", where="pointer")
        elif n == 9:
            assert current()[1].overlay is None
            emit("LEFTMOUSE", where="text")
        elif n == 10:
            assert current()[1].editor is not None
            emit("RIGHTMOUSE", where="text")
        elif n == 11:
            assert current()[1].editor is None and current()[1].context_menu is None
            canvas = current()[1]
            canvas.animation.enabled = False
            canvas.cancel()
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Real N-panel Fake User toggle writes its selected material",
                "Right-click field menu resolves the selected material and exact property",
                "Native text input renames the selected ID and keyboard picker selection closes the overlay",
                "Right-click cancels editing before opening a menu",
                "Disabled animation and teardown leave no host timers or bridge errors",
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
