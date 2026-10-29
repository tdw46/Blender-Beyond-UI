"""Real window operator selection, search, cancellation and owner menus."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import operator_choices_fixture as fixture

fixture.register()
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui = Layout(context=bpy.context)
    ui.operator_context = "EXEC_DEFAULT"
    ui.title(text="Operator Choices")
    props = ui.operator_menu_enum("bui.long_choice", "choice", text="Search Actions")
    props.amount = 7
    ui.operator_enum("bui.choice", "choice")
    for i in range(8):
        ui.label(text="")
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
    fixture.unregister()
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
            emit("LEFTMOUSE")
        elif n == 2:
            assert current()[1].context_menu is not None, current()[1].menu_error
            for char in "199":
                emit("A", unicode=char)
        elif n == 3:
            menu = current()[1].context_menu
            assert [r.key for r in menu.page.rows] == ["operator:I199"]
            assert not fixture.calls
            emit("RET")
        elif n == 4:
            assert fixture.calls == [("I199", 7, 200)], fixture.calls
            emit("LEFTMOUSE")
        elif n == 5:
            emit("ESC")
        elif n == 6:
            assert current()[1].context_menu is None
            assert len(fixture.calls) == 1
            button = next(
                c for c in current()[1].controls.values() if c.label == "Sphere"
            )
            emit("LEFTMOUSE", where=button)
        elif n == 7:
            assert fixture.calls[-1][:2] == ("B", 1), fixture.calls
            button = next(
                c for c in current()[1].controls.values() if c.label == "Sphere"
            )
            emit("RIGHTMOUSE", where=button)
        elif n == 8:
            assert current()[1].context_menu is not None, current()[1].menu_error
            assert any(
                r.key == "FAVORITES" for r in current()[1].context_menu.page.rows
            )
            emit("ESC")
        elif n == 9:
            emit("RIGHTMOUSE")
        elif n == 10:
            assert current()[1].context_menu.page.rows[0].key == "CHOICES"
            emit("ESC")
        elif n == 11:
            current()[1].animation.enabled = False
            current()[1].cancel()
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual dropdown mouse input, type-to-filter and Enter execute the 200th operator choice exactly once with supplied arguments",
                "Escape cancels without executing; expanded button uses its selected enum value",
                "Right-click covers expanded operator actions and custom popup choices",
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
