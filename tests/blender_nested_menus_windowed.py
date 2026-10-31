"""Real N-panel mouse, text, picker and context input for custom registered menus."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from pie_nested_fixture import build as build_fixture, register, unregister
import pie_fixture

register()

layouts = {}
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    canvas, opener = build_fixture(bpy.context)
    for i in range(12):
        canvas.label(f"space-{i}", "Nested menu input fixture")
    layouts[key] = canvas
    return canvas


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
    if kind == "LEFTMOUSE":
        emit(kind, "RELEASE", logical=(rect[0] + rect[2] / 2, rect[1] + rect[3] / 2))


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
            emit("LEFTMOUSE", where="button")
        elif n == 2:
            click_row("Transform…")
        elif n == 3:
            child = current()[1].context_menu
            assert child.navigation_parent is not None
            assert child.glass_ready
            click_row("Transparent", "RIGHTMOUSE")
        elif n == 4:
            child = current()[1].context_menu
            assert any(r.key == "FULL_PATH" for r in child.page.rows)
            emit("LEFT_ARROW")
        elif n == 5:
            assert current()[1].context_menu.navigation_parent is not None
            emit("LEFT_ARROW")
        elif n == 6:
            assert current()[1].context_menu.navigation_parent is None
            click_row("Transform…")
        elif n == 7:
            state["before"] = len(pie_fixture.calls)
            click_row("Rotate")
        elif n == 8:
            assert (
                pie_fixture.calls[-1] == 202
                and len(pie_fixture.calls) == state["before"] + 1
            )
            assert current()[1].context_menu is None
            emit("LEFTMOUSE", where="button")
        elif n == 9:
            click_row("Transform…")
        elif n == 10:
            current()[1].animation.enabled = False
            emit("ESC")
        elif n == 11:
            assert current()[1].context_menu.navigation_parent is None
            current()[1].cancel()
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Native N-panel events navigate into a nested definition and restore its parent",
                "Exact child property right-click actions retain glass and keyboard Back",
                "Matching release dispatches the compound child operator once and closes the chain",
                "Global animation disable and teardown leave no host animation/tooltip callbacks",
                "Narrow N-panel uses the explicit custom list fallback; radial pixels are covered by GPU fixtures",
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
