"""Real panel draws and simulated input in a disposable Blender process."""

import bpy
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import NativeLayout as Layout
from beyond_ui.gpu import style, glass

spec = importlib.util.spec_from_file_location(
    "beyond_ui_demo_test", ROOT / "examples/demo.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
state = {"stage": 0, "draws": 0, "checks": [], "errors": []}
inventory = json.loads((ROOT / "docs/api_inventory.json").read_text())
version = ".".join(map(str, bpy.app.version[:2]))


class TEST_PT_native(bpy.types.Panel):
    bl_idname = "TEST_PT_beyond_native"
    bl_label = "Native API coverage"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Beyond UI"

    def draw(self, context):
        try:
            ui = Layout(self.layout)
            for name in inventory[version]["UILayout"]["members"]:
                assert ui.supports(name), name
                getattr(ui, name)
            row = ui.row(align=True)
            assert isinstance(row, Layout)
            row.prop(context.scene.render, "resolution_x", text="X")
            row.prop(context.scene.render, "film_transparent", text="Alpha")
            row = ui.row()
            row.enabled = False
            row.operator("render.render").animation = False
            header, body = ui.panel("beyond_ui_test_disclosure", default_closed=True)
            assert isinstance(header, Layout)
            assert body is None or isinstance(body, Layout)
            header.label(text="Collapsible panel")
            state["draws"] += 1
        except Exception:
            state["errors"].append(traceback.format_exc())


bpy.utils.register_class(TEST_PT_native)
demo.register()
assert demo._host.bridge is not None, demo._host.reason
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")


def event(kind, value, x=10, y=10):
    window.event_simulate(type=kind, value=value, x=x, y=y)


def finish(passed, error=""):
    try:
        if demo._host is not None:
            demo.unregister()
        bpy.utils.unregister_class(TEST_PT_native)
    except Exception:
        passed = False
        error += traceback.format_exc()
    result = {
        "passed": passed,
        "version": bpy.app.version_string,
        "build": bpy.app.build_hash.decode(),
        "checks": state["checks"],
        "native_draws": state["draws"],
        "error": error,
        "platform": sys.platform,
    }
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print(
        "BEYOND_UI_WINDOW_PASS" if passed else "BEYOND_UI_WINDOW_FAIL",
        json.dumps(result),
        flush=True,
    )
    bpy.ops.wm.quit_blender()


def tick():
    try:
        assert not state["errors"], state["errors"]
        if demo._host is not None and demo._host.bridge is not None:
            assert not demo._host.bridge.errors, demo._host.bridge.errors
        stage = state["stage"]
        if stage == 0:
            region.active_panel_category = "Beyond UI"
            area.tag_redraw()
        elif stage == 1:
            assert state["draws"] > 0, "Native panel did not draw"
            records = demo._host.records
            assert records, "Custom panel did not reserve an anchor"
            key = next(iter(records))
            record = records[key]
            assert record["rect"] and record["valid"], record
            state["key"] = key
            state["rect"] = record["rect"]
            state["clip"] = record["clip"]
            state["checks"] += [
                "all documented UILayout members resolve in draw",
                "native nested layouts/operator properties",
                "custom anchor and GPU shader draw",
            ]
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            control = record["canvas"].controls["enabled"]
            a, b, w, h = control.rect
            x, y, rw, rh = record["rect"]
            sx = rw / record["canvas"]._width
            sy = rh / record["canvas"].height
            px = int(region.x + x + (a + w / 2) * sx)
            py = int(region.y + y + rh - (b + h / 2) * sy)
            state["click"] = (px, py)
            event("MOUSEMOVE", "NOTHING", px, py)
            event("LEFTMOUSE", "PRESS", px, py)
            event("LEFTMOUSE", "RELEASE", px, py)
        elif stage == 2:
            assert demo._states[state["key"]]["enabled"] is False, (
                "Custom toggle did not handle input"
            )
            state["checks"].append("real modal mouse input toggles custom binding")
            record = demo._host.records[state["key"]]
            canvas = record["canvas"]
            old = canvas.layout_count
            canvas.arrange(canvas._width)
            assert canvas.layout_count == old
            state["checks"].append("warm layout retains geometry")
            # Simulate the same event through host routing outside its clipped rect.
            from types import SimpleNamespace

            e = SimpleNamespace(
                type="LEFTMOUSE", value="PRESS", mouse_x=area.x + 1, mouse_y=area.y + 1
            )
            assert not demo._host.event(bpy.context, e)
            state["checks"].append("outside-region input passes through")
            # Cancel an active edit on owner invalidation; never save anything.
            canvas._begin(canvas.controls["strength"])
            canvas._write(0.9)
            demo._host.invalidate()
            assert demo._states[state["key"]]["strength"] == 0.5
            state["checks"].append("owner invalidation rolls back active edit")
            demo._host.close()
            event("MOUSEMOVE", "NOTHING")
        elif stage == 3:
            assert not demo._running, "Modal failed to exit"
            demo.unregister()
            demo.register()
            region.active_panel_category = "Beyond UI"
            area.tag_redraw()
        elif stage == 4:
            assert demo._host.records and any(
                r["valid"] for r in demo._host.records.values()
            )
            assert not demo._host.bridge.errors
            state["checks"].append(
                "disable/re-enable draws with independent callback ownership"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.7
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1.0)
