"""Execute registered menu API routes against real Blender RNA in a disposable profile."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout, UnsupportedControl
import registered_menus_fixture as fixture


def run():
    checks = []
    try:
        fixture.register()
        ui, settings, many, attached, commits = fixture.build(bpy.context)
        canvas = ui.canvas
        canvas.arrange(560)
        clip = (0, 0, 560, 600)

        def open(c=settings):
            assert canvas.open_operator_menu(c, clip, bpy.context), canvas.menu_error
            return canvas.context_menu

        def choose(menu, label):
            index = next(i for i, r in enumerate(menu.page.rows) if r.label == label)
            menu.choose(index, bpy.context)
            assert menu.error is None, menu.error

        menu = open()
        assert fixture.draws == 1
        assert not menu.page.available[-1]
        before = bpy.context.scene.render.film_transparent
        choose(menu, "Transparent")
        assert bpy.context.scene.render.film_transparent != before and len(commits) == 1
        menu = open()
        choose(menu, "Scale")
        menu.editor.text.text = "73"
        menu.event(NS(type="RET", value="PRESS"), 0, 0, bpy.context)
        assert (
            bpy.context.scene.render.resolution_percentage == 73 and len(commits) == 2
        )
        canvas.cancel()
        menu = open()
        choose(menu, "Nested Actions")
        choose(menu, "Nested Action")
        assert fixture.calls[-1][0] == 42
        menu = open()
        choose(menu, "Run Action")
        assert fixture.calls[-1] == (7, "A", bpy.context.scene)
        menu = open()
        choose(menu, "Choose Action")
        choose(menu, "Beta")
        assert fixture.calls[-1][:2] == (9, "B")
        checks.append(
            "Scalar/toggle edits commit once; nested Python draw helpers, operator arguments and context pointers execute correctly"
        )
        menu = open()
        choose(menu, "Many Actions")
        assert len(menu.page.rows) == 101 and menu.page.search is not None
        canvas.cancel()
        menu = open(many)
        assert len(menu.page.rows) == 100 and menu.page.search is not None
        before_polls = fixture.operator_polls
        menu.event(NS(type="MOUSEMOVE", value="NOTHING"), 30, 80, bpy.context)
        assert fixture.operator_polls - before_polls <= 19
        menu.page.search.text.text = "Action 099"
        menu.filter_search(bpy.context)
        choose(menu, "Action 099")
        assert fixture.calls[-1][0] == 99
        menu = open(attached)
        choose(menu, "Wire")
        assert bpy.context.object.display_type == "WIRE"
        checks.append(
            "100-row menus remain searchable without truncation; prop_with_menu exposes the exact property context"
        )
        menu = open()
        index = next(i for i, r in enumerate(menu.page.rows) if r.label == "Scale")
        assert menu.open_row_context(index, bpy.context)
        choose(menu, "Copy Full Data Path")
        assert (
            bpy.context.window_manager.clipboard
            == "bpy.data.scenes['Scene'].render.resolution_percentage"
        ), bpy.context.window_manager.clipboard
        bpy.context.preferences.view.show_developer_ui = True
        menu = open()
        index = next(i for i, r in enumerate(menu.page.rows) if r.label == "Run Action")
        assert menu.open_row_context(index, bpy.context)
        choose(menu, "Copy Python Command")
        assert "amount=7" in bpy.context.window_manager.clipboard
        menu = open()
        choose(menu, "Scale")
        menu.editor.text.text = "22"
        menu.event(NS(type="RIGHTMOUSE", value="PRESS"), 10, 10, bpy.context)
        assert (
            menu.editor is None
            and not menu.closed
            and bpy.context.scene.render.resolution_percentage == 73
        )
        checks.append(
            "Per-row context menus copy exact property paths/operator arguments; right-click cancels pending edits before menu navigation"
        )
        menu = open()
        disabled_index = next(
            i for i, r in enumerate(menu.page.rows) if r.label == "Unavailable"
        )
        assert not menu.page.available[disabled_index]
        assert menu.open_row_context(disabled_index, bpy.context)
        choose(menu, "Copy Python Command")
        assert "bpy.ops.bui.menu_action" in bpy.context.window_manager.clipboard
        menu = open()
        fixture.allowed = False
        choose_index = next(
            i for i, r in enumerate(menu.page.rows) if r.label == "Run Action"
        )
        count = len(fixture.calls)
        menu.choose(choose_index, bpy.context)
        assert menu.closed and len(fixture.calls) == count
        inline = next(c for c in canvas.controls.values() if c.label == "Inline Action")
        try:
            inline.action()
        except ReferenceError:
            pass
        else:
            raise AssertionError("Inactive inline menu executed")
        fixture.allowed = True
        inline.action()
        assert fixture.calls[-1][0] == 11
        original = tuple(canvas.controls)
        original_children = tuple(canvas.children)
        try:
            ui.menu_contents("BUI_MT_bad")
        except UnsupportedControl:
            pass
        else:
            raise AssertionError("Unsupported draw silently admitted")
        assert (
            tuple(canvas.controls) == original
            and tuple(canvas.children) == original_children
        )
        bad = Layout(context=bpy.context)
        bad.menu("BUI_MT_bad")
        bad.canvas.arrange(560)
        assert not bad.canvas.open_operator_menu(
            next(iter(bad.canvas.controls.values())), clip, bpy.context
        )
        assert bad.canvas.context_menu is None
        checks.append(
            "Poll changes prevent deferred and inline actions; unsupported draw aborts atomically instead of retaining a partial menu"
        )
        from beyond_ui.registered_menu import MenuLayout

        model = settings.options["menu_model"]
        from beyond_ui.operator_enum import context_key

        collector = MenuLayout(model, bpy.context, context_key(bpy.context), 0)
        collector.menu("BUI_MT_nested")
        row = collector.rows[0]
        collector.enabled = False
        target = open().target
        actions = row.context(target, bpy.context)
        assert not actions[0].enabled(target, bpy.context)
        collector.enabled = True
        children = row.children(target, bpy.context)
        pending = next(r for r in children if r.label == "Nested Action")
        count = len(fixture.calls)
        collector.enabled = False
        assert not pending.enabled(target, bpy.context)
        try:
            pending.action(target, bpy.context)
        except ReferenceError:
            pass
        else:
            raise AssertionError("Disabled parent executed nested action")
        assert len(fixture.calls) == count
        collector.enabled = True
        collector.operator_menu_enum("bui.menu_action", "choice")
        enum_rows = collector.rows[-1].children(target, bpy.context)
        pending = next(r for r in enum_rows if r.label == "Beta")
        collector.enabled = False
        assert not pending.enabled(target, bpy.context)
        try:
            pending.action(target, bpy.context)
        except ReferenceError:
            pass
        else:
            raise AssertionError("Disabled parent executed nested operator enum")
        assert len(fixture.calls) == count
        checks.append(
            "Disabled parent layouts gate submenu right-click opening and pending nested/operator-enum execution"
        )
        menu = open()
        bpy.utils.unregister_class(fixture.BUI_MT_settings)
        menu.choose(choose_index, bpy.context)
        assert menu.closed
        checks.append("Unregistered definitions invalidate open menus before execution")
        fixture.many_count = 4100
        assert not canvas.open_operator_menu(many, clip, bpy.context)
        assert "4096" in canvas.menu_error
        fixture.many_count = 100
        checks.append(
            "Long nested menus retain all rows; hover polls only visible rows; row bounds fail explicitly"
        )
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("REGISTERED_MENUS", result, flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.2
    )


bpy.app.timers.register(run, first_interval=1)
