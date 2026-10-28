"""Real window input for custom RNA event fields in the disposable panel host."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout

spec = importlib.util.spec_from_file_location("event_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
config = bpy.context.window_manager.keyconfigs.new("Beyond event fixture")
km = config.keymaps.new("Beyond event fixture", space_type="EMPTY")
item = km.keymap_items.new("wm.context_toggle", "F5", "PRESS")
commits = []


def build(key):
    ui = Layout(context=bpy.context, commit=lambda a, b: commits.append((a, b)))
    ui.prop(item, "type", full_event=True, text="Shortcut")
    for i in range(12):
        ui.label(text="Event fixture space")
    return ui.canvas


demo.build_canvas = build
demo.register()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
state = {"stage": 0, "checks": []}


def current():
    record = next(r for r in demo._host.records.values() if r["valid"])
    return record, record["canvas"]


def emit(kind, value="PRESS", **mods):
    record, canvas = current()
    c = next(c for c in canvas.controls.values() if c.kind == "event")
    a, b, w, h = c.rect
    rx, ry, rw, rh = record["rect"]
    x = int(region.x + rx + (a + w / 2) * rw / canvas._width)
    y = int(region.y + ry + rh - (b + h / 2) * rh / canvas.height)
    window.event_simulate(type=kind, value=value, x=x, y=y, **mods)


def finish(passed, error=""):
    demo.unregister()
    bpy.context.window_manager.keyconfigs.remove(config)
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("EVENT_WINDOWED", result, flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        s = state["stage"]
        if s == 0:
            region.active_panel_category = "Beyond UI"
        elif s == 1:
            assert demo._host.bridge is not None, demo._host.reason
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            emit("MOUSEMOVE", "NOTHING")
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif s == 2:
            _, c = current()
            assert c.context_menu is not None, c.menu_error
            assert c.context_menu.capture_row is None
            emit("RET")
        elif s == 3:
            record, c = current()
            assert c.context_menu.capture_row is not None
            assert c.context_menu.glass_ready, (
                "Capture must use production liquid glass"
            )
            emit("F19", ctrl=True, shift=True, alt=True)
            emit("F19", "RELEASE", ctrl=True, shift=True, alt=True)
        elif s == 4:
            _, c = current()
            assert c.context_menu is None, c.menu_error
            assert item.type == "F19" and item.ctrl and item.shift and item.alt
            assert len(commits) == 1
            state["checks"].append(
                "Real window click, keyboard mode selection, chord capture and shared liquid glass"
            )
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif s == 5:
            emit("RET")
        elif s == 6:
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif s == 7:
            _, c = current()
            assert item.type == "F19" and len(commits) == 1
            c.close_context()
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif s == 8:
            _, c = current()
            assert c.context_menu is not None
            assert (
                c.context_menu.target.binding.context.owner().as_pointer()
                == item.as_pointer()
            )
            emit("ESC")
        elif s == 9:
            _, c = current()
            c.animation.enabled = False
            c.invalidate()
        elif s == 10:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"].append(
                "Right-click cancels capture, targets exact property, and leaves no timers on invalidation"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.65
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
