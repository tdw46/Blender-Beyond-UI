"""Real window input for retained grid layouts and inherited state."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from flow_fixture import build as build_fixture

layouts = {}
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def build(key):
    ui, toggles, disabled, calls = build_fixture(bpy.context)
    layouts[key] = (ui, toggles, disabled, calls)
    return ui.canvas


native_directions = {}
original_draw = demo.BEYONDUIDEMO_PT_panel.draw


def probe_draw(self, context):
    raw = self.layout
    native_directions.update(
        root=raw.direction,
        row=raw.row().direction,
        column=raw.column().direction,
        split=raw.split().direction,
        grid=raw.grid_flow().direction,
        flow=raw.column_flow().direction,
        box=raw.box().direction,
    )
    original_draw(self, context)


demo.BEYONDUIDEMO_PT_panel.draw = probe_draw
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
            probe = Layout()
            custom = dict(
                root=probe.direction,
                row=probe.row().direction,
                column=probe.column().direction,
                split=probe.split().direction,
                grid=probe.grid_flow().direction,
                flow=probe.column_flow().direction,
                box=probe.box().direction,
            )
            assert custom == native_directions, (custom, native_directions)
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            state["before"] = bpy.context.scene.render.film_transparent
            emit("LEFTMOUSE", where="toggle")
        elif n == 2:
            assert bpy.context.scene.render.film_transparent != state["before"]
            emit("RIGHTMOUSE", where="toggle")
        elif n == 3:
            assert current()[1].context_menu is not None, current()[1].menu_error
            assert (
                current()[1].context_menu.target.binding.context.name
                == "film_transparent"
            )
            emit("ESC", where="toggle")
        elif n == 4:
            canvas = current()[1]
            ui = next(v[0] for v in layouts.values() if v[0].canvas is canvas)
            ui.enabled = False
            state["value"] = bpy.context.scene.render.film_transparent
            emit("LEFTMOUSE", where="toggle")
        elif n == 5:
            assert bpy.context.scene.render.film_transparent == state["value"]
            canvas = current()[1]
            ui = next(v[0] for v in layouts.values() if v[0].canvas is canvas)
            ui.enabled = True
            emit("LEFTMOUSE", where="toggle")
        elif n == 6:
            assert bpy.context.scene.render.film_transparent == state["before"]
            canvas = current()[1]
            canvas.animation.enabled = False
            canvas.cancel()
        elif n == 7:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Custom layout direction matches live native RNA for root, row, column, split, grid, flow and box",
                "Real N-panel grid toggle mouse input writes its exact RNA property",
                "Right-click menu resolves the clicked grid cell owner",
                "Runtime ancestor disable blocks input and reenable restores input",
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
