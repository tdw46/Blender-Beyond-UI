"""Real input and lifecycle checks for one-line popup and keymap routes."""

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

class TEST_OT_keymap_dispatch(bpy.types.Operator):
    """Inactive windows do not run top-level keymaps; use Blender's RNA matcher.

    Only test-owned events are forwarded. This does not activate the window and
    is NOT evidence of ordinary foreground keymap dispatch.
    """
    bl_idname = "test.beyond_keymap_dispatch"
    bl_label = "Fixture Keymap Dispatch"

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "F7" and event.value == "RELEASE":
            return {"CANCELLED"}
        if event.type in {"F6", "F7"} and event.value == "PRESS":
            km = context.window_manager.keyconfigs.user.keymaps["3D View"]
            item = km.keymap_items.match_event(event)
            assert item is not None, "Blender keymap matcher found no shortcut"
            router = addon.__beyond_ui_integration__.router
            assert item.idname == router.idname, item.idname
            namespace, key = item.idname.split(".")
            result = getattr(getattr(bpy.ops, namespace), key)("INVOKE_DEFAULT", menu_name=item.properties.menu_name, pie=item.properties.pie)
            assert result == {"RUNNING_MODAL"}, result
            return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}


def invoke(name):
    with bpy.context.temp_override(window=window, area=area, region=region):
        return getattr(bpy.ops.route, name)("INVOKE_DEFAULT")


def event(kind, value="PRESS", point=None, **kw):
    point = point or (region.width / 2, region.height / 2)
    window.event_simulate(type=kind, value=value, x=int(region.x + point[0]), y=int(region.y + point[1]), **kw)


def dialog():
    return next(iter(addon.__beyond_ui_integration__.router.dialogs.values()))


def click(control, button="LEFTMOUSE"):
    d = dialog()
    x, y, w, h = d.host.canvas.overlay["rect"]
    a, b, c, e = control.rect
    scale = d.host.scale
    pt = ((x + a + c / 2) * scale, region.height - (y + b + e / 2) * scale)
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
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(dict(passed=error is None, version=bpy.app.version_string, checks=checks, glass=glass, calls=addon.calls, error=error), indent=2))
    bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["step"]
        router = addon.__beyond_ui_integration__.router
        if n == 0:
            addon.register()
            router = addon.__beyond_ui_integration__.router
            assert len(router.keymaps.items) == 2, router.keymaps.items
            assert addon.keymaps[-1][1].idname == "wm.call_menu"
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.ed.undo_push(message="Before popup variants")
            assert invoke("plain") == {"RUNNING_MODAL"}
        elif n == 1:
            d = dialog()
            audit(d.host)
            assert "confirm" not in d.canvas.controls and "cancel" not in d.canvas.controls
            click(next(c for c in d.canvas.controls.values() if c.kind == "toggle"))
        elif n == 2:
            assert dialog().operator.enabled
            assert addon.calls == [], addon.calls
            event("ESC")
        elif n == 3:
            assert not router.dialogs
            assert addon.calls == [("cancel", 3)], addon.calls
            checks.append("Property-only popup edits/check refresh without executing; Escape cancels once")
            invoke("confirm")
        elif n == 4:
            d = dialog()
            audit(d.host)
            assert not any(c.kind in {"number", "toggle"} for c in d.canvas.controls.values())
            assert any(c.label == "Keep the original instance." for c in d.canvas.controls.values())
            click(d.canvas.controls["confirm"])
        elif n == 5:
            assert addon.calls[-1] == ("execute", 3, False), addon.calls
            checks.append("Confirmation message and action execute the original instance exactly once")
            invoke("search")
        elif n == 6:
            d = dialog()
            audit(d.host)
            assert d.host.canvas.context_menu.page.search.focused
            event("J", unicode="j")
        elif n == 7:
            menu = dialog().host.canvas.context_menu
            assert [row.label for row in menu.page.rows] == ["JPEG"], menu.page.rows
            event("RET")
        elif n == 8:
            assert addon.calls[-1] == ("search", "JPEG"), addon.calls
            assert not router.dialogs
            assert bpy.context.scene.render.image_settings.file_format == "JPEG"
            with bpy.context.temp_override(window=window, area=area, region=region):
                assert bpy.ops.ed.undo() == {"FINISHED"}
            assert bpy.context.scene.render.image_settings.file_format == "PNG"
            invoke("search")
        elif n == 9:
            # Exact enum owner context actions use the same menu stack.
            menu = dialog().host.canvas.context_menu
            with bpy.context.temp_override(window=window, area=area, region=region):
                assert menu.open_row_context(0, bpy.context)
                assert menu.target.binding.context.name == "format"
                assert menu.back(bpy.context)
            event("ESC")
        elif n == 10:
            assert addon.calls[-1] == ("search-cancel",), addon.calls
            checks.append("Enum search filters real keyboard input, preserves original state, executes once, supports undo and cancels once")
            invoke("callback_pie")
        elif n == 11:
            host = next(iter(router.menus.values()))
            audit(host)
            menu = host.canvas.context_menu
            assert type(menu).__name__ == "PieMenu"
            assert len(menu.slots.roots) == 2, menu.slots.roots
            assert any(r.key == "__pie_title__" and r.label == "Actions" for r in menu.root.rows)
            event("ESC")
        elif n == 12:
            assert not router.menus
            bpy.utils.register_class(TEST_OT_keymap_dispatch)
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.test.beyond_keymap_dispatch("INVOKE_DEFAULT")
            event("MOUSEMOVE", "NOTHING")
            event("F6", ctrl=True, shift=True)
            event("F6", "RELEASE", ctrl=True, shift=True)
        elif n == 13:
            host = next(iter(router.menus.values()))
            audit(host)
            assert type(host.canvas.context_menu).__name__ == "Menu"
            event("HOME")
            event("RET")
        elif n == 14:
            assert addon.calls[-1] == ("menu",), addon.calls
            assert not router.menus
            event("F7", ctrl=True, shift=True)
        elif n == 15:
            host = next(iter(router.menus.values()))
            audit(host)
            menu = host.canvas.context_menu
            assert type(menu).__name__ == "PieMenu"
            assert menu.trigger == "F7"
            event("F7", "RELEASE", ctrl=True, shift=True)
            event("ESC")
        elif n == 16:
            assert not router.menus
            checks.append("Callback pie keeps title outside the two directional slots; Blender RNA keymap matching and test-modal dispatch open list and held-key pie menus (ordinary foreground dispatch remains untested)")
            # Changing a shortcut while integrated must survive removal of routing.
            addon.keymaps[0][1].type = "F9"
            state["keymap"] = addon.keymaps[0][1]
            router.keymaps.close()
            assert state["keymap"].idname == "wm.call_menu"
            assert state["keymap"].properties.name == "ROUTE_MT_menu"
            assert state["keymap"].type == "F9" and state["keymap"].ctrl and state["keymap"].shift
            addon.__beyond_ui_integration__.refresh()
            assert state["keymap"].idname == router.idname
            invoke("search")
        elif n == 17:
            addon.unregister()
            event("MOUSEMOVE", "NOTHING")
        elif n == 18:
            assert addon.calls[-1] == ("search-cancel",), addon.calls
            assert sum(c[0] == "search-cancel" for c in addon.calls) == 2
            checks.append("Keymap teardown restores native routes and preserves edited chords; explicit refresh re-adopts; unregister cancels pending search once")
            from dialog_addon._vendor.beyond_ui import integrate
            cls = type("ONLY_MT_fixture", (bpy.types.Menu,), dict(__module__="onlymenus", bl_label="Only Menus", draw=lambda self, context: self.layout.operator("wm.search_menu")))
            items = []
            def register_only():
                bpy.utils.register_class(cls)
                km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
                kmi = km.keymap_items.new("wm.call_menu", "F12", "PRESS", alt=True)
                kmi.properties.name = "ONLY_MT_fixture"
                items.append((km, kmi))
            def unregister_only():
                for km, kmi in items:
                    assert kmi.idname == "wm.call_menu" and kmi.properties.name == "ONLY_MT_fixture"
                    km.keymap_items.remove(kmi)
                items.clear()
                bpy.utils.unregister_class(cls)
            namespace = dict(__name__="onlymenus", register=register_only, unregister=unregister_only)
            integration = integrate(namespace)
            namespace["register"]()
            try:
                assert not integration.router.operators
                assert len(integration.router.keymaps.items) == 1
                assert items[0][1].idname == integration.router.idname
            finally:
                namespace["unregister"]()
            checks.append("Menu-only package with zero Panel/Operator subclasses gets reversible one-line keymap adoption")
            finish()
            return None
        state["step"] += 1
        return 0.65
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
