"""Actual operator instance, menu routing, custom glass, input and teardown."""

import bpy, importlib, json, os, sys, traceback
from pathlib import Path

sys.path.insert(0, os.environ["BEYOND_UI_CONSUMER_ROOT"])
addon = importlib.import_module("dialog_addon")
checks, glass = [], []
state = {"step": 0}
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
area.spaces.active.show_region_ui = False
original = addon.ROUTE_OT_dialog.invoke


def invoke(name, origin=None):
    with bpy.context.temp_override(window=window, area=area, region=origin or region):
        return getattr(bpy.ops.route, name)("INVOKE_DEFAULT")


def event(kind, value="PRESS", point=None):
    point = point or (region.width / 2, region.height / 2)
    window.event_simulate(
        type=kind, value=value, x=int(region.x + point[0]), y=int(region.y + point[1])
    )


def dialog():
    return next(iter(addon.__beyond_ui_integration__.router.dialogs.values()))


def click(control, button="LEFTMOUSE"):
    d = dialog()
    x, y, w, h = d.host.canvas.overlay["rect"]
    a, b, c, e = control.rect
    scale = d.host.scale
    pt = (d.host.rect[0] + (x + a + c / 2) * scale, d.host.rect[1] + d.host.rect[3] - (y + b + e / 2) * scale)
    event("MOUSEMOVE", "NOTHING", pt)
    event(button, point=pt)
    event(button, "RELEASE", pt)


def audit(host):
    record = host.records[host.key]
    assert record.get("backdrop"), (host.reason, record.get("glass_error"))
    from dialog_addon._vendor.beyond_ui.gpu import glass as renderer

    owner = renderer._owners[record["backdrop"]]
    glass.append(dict(productions=owner["productions"], error=record["glass_error"]))


def finish(error=None):
    try:
        addon.unregister()
    except Exception:
        error = (error or "") + traceback.format_exc()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(
            dict(
                passed=error is None,
                version=bpy.app.version_string,
                checks=checks,
                glass=glass,
                calls=addon.calls,
                error=error,
            ),
            indent=2,
        )
    )
    bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["step"]
        router = addon.__beyond_ui_integration__.router
        if n == 0:
            addon.register()
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.ed.undo_push(message="Before custom dialog")
            state["before"] = bpy.context.scene.render.resolution_percentage
            result = invoke("dialog")
            assert result == {"RUNNING_MODAL"}, (result, addon.calls, addon.__beyond_ui_integration__.status)
        elif n == 1:
            d = dialog()
            assert d.operator.value == 7
            audit(d.host)
            toggle = next(c for c in d.canvas.controls.values() if c.kind == "toggle")
            click(toggle)
        elif n == 2:
            assert dialog().operator.enabled
            assert any(
                c.label == "Extra options" for c in dialog().canvas.controls.values()
            ), "Operator.check did not rebuild conditional controls"
            click(dialog().canvas.controls["confirm"])
        elif n == 3:
            assert addon.calls == [("execute", 7, True)], addon.calls
            assert bpy.context.scene.render.resolution_percentage == 7
            assert not router.dialogs
            with bpy.context.temp_override(window=window, area=area, region=region):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert bpy.context.scene.render.resolution_percentage == state["before"]
            result = invoke("dialog")
            assert result == {"RUNNING_MODAL"}, (result, addon.calls, addon.__beyond_ui_integration__.status)
        elif n == 4:
            number = next(
                c for c in dialog().canvas.controls.values() if c.kind == "number"
            )
            click(number, "RIGHTMOUSE")
        elif n == 5:
            menu = dialog().canvas.context_menu
            assert menu and menu.target.binding.context.name == "value", (
                dialog().canvas.menu_error,
                dialog().host.canvas.menu_error,
                menu,
            )
            assert menu.target.binding.read() == 7
            event("ESC")
        elif n == 6:
            assert router.dialogs and not dialog().canvas.context_menu
            event("ESC")
        elif n == 7:
            assert addon.calls[-1] == ("cancel", 7), addon.calls
            assert not router.dialogs
            checks.append(
                "Original invoke state and edited operator properties reach execute exactly once; Escape cancels exactly once"
            )
            invoke("menu", origin=next(r for r in area.regions if r.type == "UI"))
        elif n == 8:
            host = next(iter(router.menus.values()))
            audit(host)
            assert host.canvas.context_menu
            event("HOME")
            event("RET")
        elif n == 9:
            assert addon.calls[-1] == ("menu",), addon.calls
            assert not router.menus
            invoke("popup")
        elif n == 10:
            host = next(iter(router.menus.values()))
            audit(host)
            event("ESC")
        elif n == 11:
            assert not router.menus
            invoke("pie")
        elif n == 12:
            host = next(iter(router.menus.values()))
            audit(host)
            assert type(host.canvas.context_menu).__name__ == "PieMenu"
            event("ESC")
        elif n == 13:
            assert not router.menus
            checks.append(
                "Direct owned wm.call_menu, wm.call_menu_pie and WindowManager.popup_menu use custom menu engine with real shared glass"
            )
            checks.append(
                "Native operator undo, check-driven conditional controls and exact operator-property right-click ownership pass"
            )
            invoke("dialog")
        elif n == 14:
            addon.unregister()
            assert addon.ROUTE_OT_dialog.invoke is original
            event("MOUSEMOVE", "NOTHING")
        elif n == 15:
            assert addon.bpy is bpy
            assert addon.calls[-1] == ("cancel", 7), addon.calls
            assert sum(c[0] == "cancel" for c in addon.calls) == 2
            checks.append(
                "Original callbacks restored and lifecycle unregister completes"
            )
            finish()
            return None
        state["step"] += 1
        return 0.65
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
