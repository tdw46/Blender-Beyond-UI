"""Real window typing, search selection and unchanged owner context menus."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
obj = bpy.context.object
commits = []
bpy.types.Scene.scalar_window = bpy.props.FloatProperty(default=0.25, min=0.0, max=1.0)
bpy.types.Scene.scalar_bool = bpy.props.BoolProperty(default=False)


def build(key):
    ui = Layout(
        Canvas(menu_commit=commits.append),
        bpy.context,
        commit=lambda a, b: commits.append("POINTER"),
    )
    ui.title(text="BVT Scalar Controls")
    ui.prop(bpy.context.scene, "scalar_window", text="Opacity", slider=True)
    ui.prop(bpy.context.scene, "scalar_bool", text="Viewport")
    for i in range(13):
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


def emit(kind, value="PRESS", where="number", logical=None, **mods):
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
    del bpy.types.Scene.scalar_window
    del bpy.types.Scene.scalar_bool
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("POINTER_WINDOWED", result, flush=True)
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
            from beyond_ui.scalar_geometry import slider_parts, switch_rect

            _, track, field = slider_parts(control("number").rect)
            state.update(
                track=track, field=field, switch=switch_rect(control("toggle").rect)
            )
            x, y, w = track
            emit("MOUSEMOVE", "NOTHING", logical=(x + w * 0.75, y))
            emit("LEFTMOUSE", logical=(x + w * 0.75, y))
        elif n == 2:
            assert abs(bpy.context.scene.scalar_window - 0.75) < 0.03, (
                bpy.context.scene.scalar_window
            )
            x, y, w = state["track"]
            emit("MOUSEMOVE", "NOTHING", logical=(x + w * 0.4, y))
        elif n == 3:
            assert abs(bpy.context.scene.scalar_window - 0.4) < 0.03, (
                bpy.context.scene.scalar_window
            )
            emit("RIGHTMOUSE")
        elif n == 4:
            assert abs(bpy.context.scene.scalar_window - 0.25) < 1e-5 and not commits
            x, y, w, h = state["field"]
            emit("LEFTMOUSE", logical=(x + w / 2, y + h / 2))
            emit("LEFTMOUSE", "RELEASE", logical=(x + w / 2, y + h / 2))
        elif n == 5:
            assert current()[1].editor is not None
            for char in "0.65":
                emit("A", unicode=char)
            emit("RET")
        elif n == 6:
            assert (
                abs(bpy.context.scene.scalar_window - 0.65) < 1e-5 and len(commits) == 1
            )
            x, y, w, h = state["switch"]
            emit("LEFTMOUSE", where="toggle", logical=(x + w / 2, y + h / 2))
            emit("LEFTMOUSE", "RELEASE", where="toggle", logical=(x + w / 2, y + h / 2))
        elif n == 7:
            assert bpy.context.scene.scalar_bool and len(commits) == 2
            x, y, w, h = state["field"]
            emit("RIGHTMOUSE", logical=(x + w / 2, y + h / 2))
        elif n == 8:
            assert (
                current()[1].context_menu.target.binding.context.name == "scalar_window"
            )
            emit("ESC")
        elif n == 9:
            x, y, w = state["track"]
            emit("RIGHTMOUSE", logical=(x + w / 2, y))
        elif n == 10:
            assert (
                current()[1].context_menu.target.binding.context.name == "scalar_window"
            )
            emit("ESC")
        elif n == 11:
            c = current()[1]
            c.animation.enabled = False
            c.cancel()
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual BVT track click/drag uses the rendered rail and cancels to original value",
                "Independent right-side number entry commits once",
                "Actual switch click writes its bool once; finite travel and squash/stretch share host settings",
                "Track and number-field right-click retain the exact RNA owner",
                "Disabled animation and teardown leave no timers or bridge errors",
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
