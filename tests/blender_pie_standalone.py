"""Real RNA execution for unregistered pies and compound flags."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout
from beyond_ui.gpu import style
import pie_standalone_fixture as fixture
import pie_fixture


def run():
    checks = []
    try:
        fixture.register()
        context = bpy.context
        clip, anchor = (0, 0, 1200, 900), (600, 450)
        ui = Layout(context=context)
        commits = []
        ui.canvas.menu_commit = commits.append
        pie = ui.menu_pie()
        fixture.contents(pie, context, initialize=True)
        menu = pie.open(anchor=anchor, clip=clip)
        assert menu.editor and menu.editor.row.label == "Location X"
        menu.editor.text.text = "2.5"
        menu.event(NS(type="RET", value="PRESS"), *anchor, context)
        assert context.active_object.location.x == 2.5
        assert not menu.editor
        assert any(r.alert for r in menu.page.rows)
        assert (
            next(r for r in menu.page.rows if r.label == "Unembossed").emboss == "NONE"
        )
        assert next(r for r in menu.page.rows if r.label == "Location Y").label_split
        assert sum(r.decorator is not None for r in menu.page.rows) == 1
        i = next(i for i, r in enumerate(menu.page.rows) if r.decorator is not None)
        assert menu.page.values[i] == "EMPTY"
        assert menu.open_row_context(i, context)
        assert any(r.key == "FULL_PATH" for r in menu.page.rows)
        menu.back(context)
        menu.choose(i, context)
        assert commits
        # Same exact component now has an actual key, not just a glyph change.
        menu = pie.open(anchor=anchor, clip=clip)
        assert menu.page.values[i] == "KEYED", menu.page.values[i]
        menu.event(
            NS(type="ESC", value="PRESS"), *anchor, context
        )  # Cancel initial edit.
        assert not menu.editor
        menu.choose(i, context)
        menu = pie.open(anchor=anchor, clip=clip)
        assert menu.page.values[i] == "EMPTY"
        ui.canvas.cancel()
        checks.append(
            "Standalone compound fields, initial edit, split labels, optional exact-component key decorators and owner-aware right-click"
        )
        # Default selection executes only on explicit Return, not during open.
        plain = Layout(context=context)
        default = plain.menu_pie()
        default.operator_context = "EXEC_DEFAULT"
        default.operator("bui.pie_test", text="First").slot = 900
        col = default.column()
        col.active_default = True
        col.operator("bui.pie_test", text="Default").slot = 901
        m = default.open(anchor=anchor, clip=clip)
        assert m.page.rows[m.page.highlight].label == "Default"
        m.event(NS(type="RET", value="PRESS"), *anchor, context)
        assert pie_fixture.calls[-1] == 901
        checks.append(
            "Initial default operator selected, then exactly one explicit Return dispatch"
        )
        canvas, authored = fixture.build(context)
        m = authored.open(anchor=anchor, clip=clip)
        m.choose(0, context)
        child = canvas.context_menu
        assert child.navigation_parent is m
        fixture.allowed = False
        assert not child.refresh(context)
        fixture.allowed = True
        canvas.cancel()
        assert not canvas.advance_animations(context=context)
        checks.append(
            "Standalone-to-registered nesting, live child poll invalidation and quiescent teardown"
        )
        colors = style.menu_status_palette(context.preferences)
        assert "wcol_state.error/info.info_error" not in colors["fallback_roles"], dict(
            colors
        )
        state = context.preferences.themes[0].user_interface.wcol_state
        old_error = tuple(state.error)
        try:
            state.error = (0.2, 0.7, 0.4, 1)
            changed = style.menu_status_palette(context.preferences)["ALERT"]
            assert changed[:3] == tuple(state.error)[:3] and changed != colors["ALERT"]
        finally:
            state.error = old_error
        checks.append(
            "Active semantic error and animation theme roles; theme change invalidates color cache"
        )
        api = {
            n: bpy.types.UILayout.bl_rna.properties[n].description
            for n in (
                "alert",
                "emboss",
                "use_property_split",
                "use_property_decorate",
                "active_default",
                "activate_init",
            )
        }
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            checks=checks,
            theme_status_source=dict(colors),
            theme_ui_roles=[
                p.identifier
                for p in context.preferences.themes[0].user_interface.bl_rna.properties
            ],
            native_flag_descriptions=api,
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


run()
