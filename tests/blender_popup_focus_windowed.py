"""Real N-panel mouse, text, picker and context input for custom panel popovers."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from popup_focus_fixture import build as build_fixture, register, unregister

register()
import popup_focus_fixture as fixture

probes = {}


class BUI_PT_native_focus_probe(bpy.types.Panel):
    bl_label = "Native Focus Probe"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Beyond UI"

    def draw(self, context):
        row = self.layout.row()
        probes["defaults"] = (row.activate_init, row.active_default)
        row.activate_init = row.active_default = True
        probes["setters"] = (row.activate_init, row.active_default)
        child = row.column()
        probes["children"] = (child.activate_init, child.active_default)
        child.label(text="Native local flag probe")


bpy.utils.register_class(BUI_PT_native_focus_probe)

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
    bpy.utils.unregister_class(BUI_PT_native_focus_probe)
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
        native_probes=probes,
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
            opener = next(
                c
                for c in current()[1].controls.values()
                if c.label == "Output Settings"
            )
            emit("LEFTMOUSE", where=opener)
        elif n == 2:
            child = current()[1].overlay["widget"].canvas
            assert child.active.label == "Output" and child.editor is not None
            for char in "//keyboard-output/":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 3:
            emit("RET")
        elif n == 4:
            assert bpy.context.scene.render.filepath == "//keyboard-output/"
            assert not fixture.calls and current()[1].overlay is not None
            emit("RET")
        elif n == 5:
            assert fixture.calls[-1][0] == "text" and current()[1].overlay is None
            opener = next(
                c
                for c in current()[1].controls.values()
                if c.label == "Resolution Settings"
            )
            emit("LEFTMOUSE", where=opener)
        elif n == 6:
            child = current()[1].overlay["widget"].canvas
            assert child.active.label == "Scale" and child.editor is not None
            for char in "63":
                window.event_simulate(type="TEXTINPUT", value="PRESS", unicode=char)
        elif n == 7:
            emit("RET")
        elif n == 8:
            assert bpy.context.scene.render.resolution_percentage == 63
            child_click("Scale", "RIGHTMOUSE")
        elif n == 9:
            assert current()[1].active_menu() is not None
            assert any(
                r.label == "Copy Full Data Path"
                for r in current()[1].active_menu().page.rows
            )
            emit("ESC")
        elif n == 10:
            emit("NUMPAD_ENTER")
        elif n == 11:
            assert len(fixture.calls) == 2 and fixture.calls[-1][0] == "number"
            assert current()[1].overlay is None
            current()[1].animation.enabled = False
            current()[1].cancel()
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            assert probes == {
                "defaults": (False, False),
                "setters": (True, True),
                "children": (False, False),
            }, probes
            state["checks"] = [
                "Actual no-focus N-panel input opens a preselected text/numeric edit without clicking the field",
                "Typing replaces the selection; Return commits before a second Return invokes the exact default operator",
                "Right-click retains exact owner actions; keypad Return, native local-flag probes and timer teardown pass",
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
