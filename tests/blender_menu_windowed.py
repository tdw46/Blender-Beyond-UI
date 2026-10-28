"""Actual host modal right-click/keyboard/cancellation and finite menu motion."""

import bpy
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, MenuEntry, Shortcut
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import default_entries

spec = importlib.util.spec_from_file_location("menu_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
called = []


def provider(target, context):
    return [
        MenuEntry(
            "nested",
            "More",
            tip="Additional actions for this field",
            children=lambda t, c: [
                MenuEntry(
                    "action",
                    "Fixture Action",
                    lambda t, c: called.append(t.key),
                    shortcut="Ctrl C",
                    bindings=(Shortcut("C", ctrl=True),),
                )
            ],
        ),
        *default_entries(target, context),
    ]


def build(key):
    canvas = Canvas(context_provider=provider, menu_commit=called.append)
    canvas.number(
        "value",
        "Resolution",
        rna_binding(lambda: bpy.context.scene.render, "resolution_percentage"),
    )
    for i in range(12):
        canvas.label(str(i), "Menu fixture space")
    return canvas


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


def emit(kind, value="PRESS", outside=False, logical=None, **mods):
    if outside:
        x, y = area.x + 30, area.y + 30
    else:
        record, canvas = current()
        a, b, w, h = canvas.controls["value"].rect
        rx, ry, rw, rh = record["rect"]
        lx, ly = logical if logical else (a + w / 2, b + h / 2)
        x = int(region.x + rx + lx * rw / canvas._width)
        y = int(region.y + ry + rh - ly * rh / canvas.height)
    window.event_simulate(type=kind, value=value, x=x, y=y, **mods)


def finish(passed, error=""):
    try:
        demo.unregister()
        assert demo._host is None
    except Exception:
        passed = False
        error += traceback.format_exc()
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
        called=called,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("MENU_WINDOWED", result, flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        stage = state["stage"]
        if stage == 0:
            region.active_panel_category = "Beyond UI"
        elif stage == 1:
            assert demo._host.bridge is not None, demo._host.reason
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            emit("MOUSEMOVE", "NOTHING")
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif stage == 2:
            _, canvas = current()
            assert canvas.context_menu is not None, canvas.menu_error
            assert canvas.context_menu.target.key == "value"
            record, _ = current()
            assert record["backdrop"] is not None, record.get("glass_error")
            assert canvas.context_menu.glass_ready
            from beyond_ui.gpu import glass

            owner = glass._owners[record["backdrop"]]
            assert owner["productions"] > 0 and owner["strong_productions"] > 0
            state["checks"].append(
                "production default uses shared BVT liquid glass and strong blur"
            )
            emit("HOME")
            emit("RIGHT_ARROW")
        elif stage == 3:
            _, canvas = current()
            assert len(canvas.context_menu.parents) == 1, canvas.menu_error
            emit("LEFT_ARROW")
        elif stage == 4:
            _, canvas = current()
            assert not canvas.context_menu.parents
            emit("RIGHT_ARROW")
            emit("C", ctrl=True)
        elif stage == 5:
            _, canvas = current()
            assert called == ["value"], called
            assert canvas.context_menu is None
            state["checks"].append(
                "right-click owner, nested/back navigation and current shortcut execution"
            )
            emit("F10", shift=True)
        elif stage == 6:
            _, canvas = current()
            assert canvas.context_menu is not None, canvas.menu_error
            emit("ESC")
            emit("LEFTMOUSE")
        elif stage == 7:
            _, canvas = current()
            assert canvas.edit is not None
            emit("RIGHTMOUSE")
        elif stage == 8:
            _, canvas = current()
            assert canvas.edit is None and canvas.context_menu is None
            state["checks"].append(
                "Shift F10 and right-click cancel edit before opening"
            )
            emit("RIGHTMOUSE")
        elif stage == 9:
            _, canvas = current()
            assert canvas.context_menu is not None
            emit("LEFTMOUSE", outside=True)
            emit("LEFTMOUSE", "RELEASE", outside=True)
        elif stage == 10:
            _, canvas = current()
            assert canvas.context_menu is None
            # Clear host focus also when a menu consumed the outside dismissal.
            emit("LEFTMOUSE", outside=True)
            emit("LEFTMOUSE", "RELEASE", outside=True)
        elif stage == 11:
            _, canvas = current()
            assert canvas.context_focus is None
            state["checks"].append(
                "outside click dismisses and clears keyboard context focus"
            )
            emit("RIGHTMOUSE")
        elif stage == 12:
            _, canvas = current()
            assert canvas.context_menu is not None
            state["menu"] = canvas.context_menu
            menu = canvas.context_menu
            rect = next(r for i, r, row in menu.visible_rows() if row.key == "nested")
            emit("MOUSEMOVE", "NOTHING", logical=(rect[0] + 10, rect[1] + rect[3] / 2))
        elif stage == 13:
            _, canvas = current()
            assert canvas.context_menu.tooltip is not None
            assert not demo._host._tooltip_keys
            assert not bpy.app.timers.is_registered(demo._host._tooltip_callback)
            state["checks"].append(
                "delayed description reveals once and tooltip timer stops"
            )
            canvas.animation.enabled = False
        elif stage == 14:
            _, canvas = current()
            assert not canvas._moving
            canvas.animation.enabled = True
            canvas.invalidate()
            assert canvas.context_menu is None
        elif stage == 15:
            assert not demo._host._animation_keys
            assert not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"].append(
                "host animation disable, invalidation, finite idle and clean teardown"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.65
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1.0)
