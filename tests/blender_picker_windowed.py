"""Actual modal focus and scrollbar input in an isolated Blender window."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas
from beyond_ui.widgets import DataPicker

spec = importlib.util.spec_from_file_location("picker_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
selected = []
valid = set(range(10000))
widget = DataPicker(
    tuple((i, f"Object {i}", "object") for i in range(10000)),
    selected.append,
    valid=lambda key: key in valid,
)


def build(key):
    canvas = Canvas()
    canvas.widget("picker", widget)
    return canvas


demo.build_canvas = build
demo.register()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
state = {"stage": 0, "checks": []}


def emit(kind, value="PRESS", logical=None, outside=False):
    if outside:
        x, y = area.x + 20, area.y + 20
    elif logical is not None:
        record = next(r for r in demo._host.records.values() if r["valid"])
        canvas = record["canvas"]
        control = canvas.controls["picker"]
        a, b, w, h = control.rect
        rx, ry, rw, rh = record["rect"]
        lx, ly = logical
        x = int(region.x + rx + (a + lx * w / widget.width) * rw / canvas._width)
        y = int(region.y + ry + rh - (b + ly * h / widget.height) * rh / canvas.height)
        state["pointer"] = (x, y)
    else:
        x, y = state["pointer"]
    window.event_simulate(type=kind, value=value, x=x, y=y)


def finish(passed, error=""):
    try:
        demo.unregister()
    except Exception:
        passed = False
        error += traceback.format_exc()
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
        selected=selected,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("PICKER_WINDOWED", result, flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        stage = state["stage"]
        if stage == 0:
            region.active_panel_category = "Beyond UI"
        elif stage == 1:
            assert demo._host.bridge is not None, demo._host.reason
            assert any(r["valid"] for r in demo._host.records.values())
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            emit("MOUSEMOVE", "NOTHING", (100, 175))
            emit("LEFTMOUSE", logical=(100, 175))
            emit("LEFTMOUSE", "RELEASE")
        elif stage == 2:
            assert selected == [0], selected
            emit("MOUSEMOVE", "NOTHING", outside=True)
            emit("DOWN_ARROW", outside=True)
            emit("RET", outside=True)
        elif stage == 3:
            assert selected == [0, 1], selected
            state["checks"].append(
                "keyboard selection survives pointer leaving owned region"
            )
            thumb, _, _ = widget.scrollbar()
            emit("MOUSEMOVE", "NOTHING", (603, thumb[1] + thumb[3] / 2))
            emit("LEFTMOUSE", logical=(603, thumb[1] + thumb[3] / 2))
            emit("MOUSEMOVE", "NOTHING", (603, 340))
            emit("LEFTMOUSE", "RELEASE")
        elif stage == 4:
            assert widget.rows.offset > 100000, widget.rows.offset
            assert not widget.capturing
            state["checks"].append(
                "actual scrollbar drag moves virtualized list and releases capture"
            )
            emit("END")
            valid.remove(9999)
            emit("RET")
        elif stage == 5:
            assert selected == [0, 1], selected
            state["checks"].append("keyboard confirmation revalidates stale identity")
            emit("LEFTMOUSE", outside=True)
            emit("LEFTMOUSE", "RELEASE", outside=True)
        elif stage == 6:
            assert not widget.focused
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"].append(
                "outside click clears focus without stealing viewport input"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.6
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
