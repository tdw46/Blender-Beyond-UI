import bpy, sys, os, json, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import registered_lists_fixture as fixture
from beyond_ui import Layout, UnsupportedControl


def run():
    checks = []
    try:
        fixture.register()
        ui, commits = fixture.build(bpy.context)
        canvas = ui.canvas
        canvas.arrange(560)
        control = next(c for c in canvas.controls.values() if c.kind == "widget")
        widget = control.options["widget"]
        clip = (0, 0, 560, 640)

        def send(kind, point, value="PRESS", **kw):
            a, b, w, h = control.rect
            result = canvas.event(
                NS(type=kind, value=value, **kw),
                a + point[0] * w / widget.width,
                b + point[1] * h / widget.height,
                clip,
                context=bpy.context,
                clipboard=bpy.context.window_manager,
            )

            return result

        def field(name):
            child, rect, item = widget.row_map[bpy.context.scene.bui_list_active]
            c = next(c for c in child.controls.values() if c.label == name)
            a, b, w, h = c.rect
            return child, c, (rect[0] + a + w / 2, rect[1] + b + h / 2)

        send("LEFTMOUSE", (30, 46))
        assert (
            bpy.context.scene.bui_list_active == 1
            and bpy.context.scene.bui_list_items[1].enabled
        )
        child, c, point = field("Enabled")
        send("LEFTMOUSE", point)
        assert not bpy.context.scene.bui_list_items[1].enabled, widget.error
        assert commits == [(0, 1), (True, False)], commits
        child, c, point = field("Enabled")
        assert c.motion.tracks, "Row rebuild lost the source spring"
        send("RIGHTMOUSE", point)
        assert canvas.active_menu() is not None, canvas.menu_error
        menu = canvas.active_menu()
        menu.choose(
            next(
                i
                for i, r in enumerate(menu.page.rows)
                if r.label == "Copy Full Data Path"
            ),
            bpy.context,
        )
        assert ".enabled" in bpy.context.window_manager.clipboard
        child.close_context()
        send("ESC", point)
        checks.append(
            "First click only selects; active row switches commit once and retain springs; menus target the clicked property"
        )
        child, c, point = field("Mode")
        send("LEFTMOUSE", point)
        menu = canvas.active_menu()
        assert menu is not None, widget.error
        send("DOWN_ARROW", point)
        send("RET", point)
        assert bpy.context.scene.bui_list_items[1].mode == "B"
        child, c, point = field("Name")
        send("LEFTMOUSE", point)
        assert child.edit is not None
        send("A", point, ctrl=True)
        send("A", point, unicode="Changed")
        bpy.context.scene.bui_list_items.move(1, 2)
        send("RET", point)
        assert bpy.context.scene.bui_list_items[1].name == "Layer 002"
        assert bpy.context.scene.bui_list_items[2].name == "Layer 001"
        widget.refresh()
        checks.append(
            "Embedded enum menus use host bounds; moving a row during text edit prevents commit and rollback to the replacement"
        )
        widget.state["show_filter"] = True
        canvas._dirty = True
        canvas.arrange(560)
        child = widget.filter_canvas
        c = next(
            c
            for c in child.controls.values()
            if c.options.get("list_setting") == "only_enabled"
        )
        a, b, w, h = c.rect
        send("LEFTMOUSE", (4 + a + w / 2, widget.viewport + 28 + b + h / 2))
        assert widget.proxy.only_enabled and all(
            widget.source.collection()[item.index].enabled for item in widget.filtered
        ), widget.error
        before = (fixture.draws, fixture.filter_draws, fixture.filters)
        for _ in range(10):
            canvas.arrange(560)
        assert before == (fixture.draws, fixture.filter_draws, fixture.filters)
        checks.append(
            "Custom draw_filter state commits recompute filter_items; cached layouts do not repeat callbacks"
        )
        # Search routes to the actual custom filter field, including cancellation.
        send("F", (30, 45), ctrl=True)
        assert widget.filter_canvas.edit is not None, widget.error
        send("A", (30, 45), ctrl=True)
        send("A", (30, 45), unicode="Layer 01")
        send("RET", (30, 45))
        assert widget.proxy.filter_name == "Layer 01" and widget.filtered, (
            widget.proxy.filter_name,
            len(widget.filtered),
            widget.error,
            canvas.menu_error,
            widget.filter_canvas.menu_error,
        )
        assert all("Layer 01" in item.name for item in widget.filtered)
        send("F", (30, 45), ctrl=True)
        send("A", (30, 45), ctrl=True)
        send("A", (30, 45), unicode="No match")
        send("RIGHTMOUSE", (30, 45))
        assert widget.proxy.filter_name == "Layer 01" and canvas.active_menu() is None
        widget.proxy.filter_name = ""
        widget.refresh()
        checks.append(
            "Ctrl-F edits custom filter_name; right-click cancels without opening a menu or retaining the draft query"
        )
        saved = widget.row_map[bpy.context.scene.bui_list_active][0]
        prop = next(c for c in saved.controls.values() if c.binding)
        assert prop.binding.valid()
        control.options["enabled"] = False
        assert not widget.available(bpy.context)
        assert not prop.binding.valid()
        widget.cancel()
        assert (
            not widget.cache
            and not widget.live_canvases
            and widget.filter_canvas is None
        )
        control.options["enabled"] = True
        widget.refresh()
        checks.append(
            "Disabling the parent invalidates row bindings and releases retained child canvases"
        )
        for name in ("BUI_UL_bad", "BUI_UL_invalid_filter"):
            prior = tuple(canvas.controls)
            try:
                ui.template_list(
                    name,
                    "bad",
                    bpy.context.scene,
                    "bui_list_items",
                    bpy.context.scene,
                    "bui_list_active",
                )
            except (UnsupportedControl, ValueError):
                pass
            else:
                raise AssertionError("Invalid callback admitted")
            assert tuple(canvas.controls) == prior
        for kind in ("GRID", "COMPACT"):
            other = Layout(
                context=bpy.context, list_identity=lambda owner, prop, item: item.uid
            )
            cc = other.template_list(
                "BUI_UL_registered",
                "registered",
                bpy.context.scene,
                "bui_list_items",
                bpy.context.scene,
                "bui_list_active",
                type=kind,
                rows=3,
                columns=3,
            )
            other.canvas.arrange(560)
            ww = cc.options["widget"]
            assert ww.proxy.layout_type == kind
            assert len(ww.row_map) == (1 if kind == "COMPACT" else 9)
            if kind == "COMPACT":
                ww.state["show_filter"] = True
                other.canvas._dirty = True
                other.canvas.arrange(560)
                assert ww.filter_canvas is None and ww.height == ww.row_height
            other.canvas.park()
        checks.append(
            "Registered callbacks retain original items in grid/compact layouts; compact mode omits the filter"
        )
        child, c, point = field("Mode")
        before_mode = bpy.context.scene.bui_list_items[
            bpy.context.scene.bui_list_active
        ].mode
        send("LEFTMOUSE", point)
        deferred = canvas.active_menu()
        assert deferred is not None
        old = fixture.BUI_UL_registered.draw_item
        fixture.BUI_UL_registered.draw_item = lambda *a: None
        assert not widget.available(bpy.context)
        deferred.choose(1, bpy.context)
        assert deferred.closed
        assert (
            bpy.context.scene.bui_list_items[bpy.context.scene.bui_list_active].mode
            == before_mode
        )
        fixture.BUI_UL_registered.draw_item = old
        checks.append(
            "Deferred child menu actions recheck callback registration even without another mouse event"
        )
        canvas.cancel()
        assert canvas.active_menu() is None and not canvas.advance_animations()
        fixture.unregister()
        result = dict(
            passed=True,
            checks=checks,
            version=bpy.app.version_string,
            build=bpy.app.build_hash.decode(),
        )
    except Exception:
        result = dict(passed=False, checks=checks, error=traceback.format_exc())
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("REGISTERED_LISTS", result, flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=0.5)
