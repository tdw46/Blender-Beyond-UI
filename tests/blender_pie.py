"""Background-safe registered pie and release execution against real RNA."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import pie_fixture as fixture
from beyond_ui.pie_menu import PieMenu


def run():
    checks = []
    try:
        fixture.register()
        canvas, button = fixture.build(bpy.context)
        canvas.arrange(900)
        clip = (0, 0, 900, 600)
        assert "menu_pie" in bpy.types.UILayout.bl_rna.functions
        assert len(bpy.types.UILayout.bl_rna.functions["menu_pie"].parameters) == 1

        def open():
            assert canvas.open_operator_menu(button, clip, bpy.context), (
                canvas.menu_error
            )
            assert isinstance(canvas.context_menu, PieMenu)
            return canvas.context_menu

        def at(menu, index):
            _, (x, y, w, h), _ = next(v for v in menu.visible_rows() if v[0] == index)
            return x + w / 2, y + h / 2

        def click(menu, index):
            p = at(menu, index)
            canvas.event(
                NS(type="LEFTMOUSE", value="PRESS"), *p, clip, context=bpy.context
            )
            assert canvas.context_menu is menu and not menu.closed
            canvas.event(
                NS(type="LEFTMOUSE", value="RELEASE"), *p, clip, context=bpy.context
            )

        menu = open()
        assert menu.layout_mode == "PIE" and len(tuple(menu.visible_rows())) == 7
        p = at(menu, 0)
        canvas.event(NS(type="LEFTMOUSE", value="PRESS"), *p, clip, context=bpy.context)
        assert not fixture.calls
        canvas.event(
            NS(type="LEFTMOUSE", value="RELEASE"), *p, clip, context=bpy.context
        )
        assert fixture.calls == [0] and canvas.context_menu is None
        checks.append(
            "Registered menu_pie keeps eight Blender-order slots including empty separators; operator runs only on release"
        )
        menu = open()
        before = bpy.context.scene.render.film_transparent
        click(menu, 4)
        assert bpy.context.scene.render.film_transparent != before
        menu = open()
        click(menu, 5)
        assert menu.editor is not None
        menu.editor.text.text = "63"
        menu.event(NS(type="RET", value="PRESS"), 0, 0, bpy.context)
        assert bpy.context.scene.render.resolution_percentage == 63
        checks.append(
            "Pie toggle and numeric field retain exact RNA ownership and editing"
        )
        menu = open()
        click(menu, 3)
        assert len(menu.page.rows) == 21 and menu.page.search is not None
        menu.page.search.text.text = "Action 19"
        menu.filter_search(bpy.context)
        index = next(i for i, r in enumerate(menu.page.rows) if r.label == "Action 19")
        click(menu, index)
        assert fixture.calls[-1] == 119
        checks.append(
            "Nested menus keep all rows and searchable capacity beyond eight radial slots"
        )
        for slot in (0, 1, 2, 7):
            menu = open()
            menu.trigger = "Q"
            p = at(menu, slot)
            canvas.event(
                NS(type="MOUSEMOVE", value="NOTHING"), *p, clip, context=bpy.context
            )
            canvas.event(NS(type="Q", value="RELEASE"), *p, clip, context=bpy.context)
            assert fixture.calls[-1] == slot and canvas.context_menu is None
        checks.append(
            "Marking release over visible petals resolves the displayed operator even when wide labels or clamping differ from angular sectors"
        )
        menu = open()
        assert menu.open_row_context(5, bpy.context)
        assert any(
            r.key == "COPY_FULL_DATA_PATH" or "Full Data Path" in r.label
            for r in menu.page.rows
        )
        menu.back()
        assert menu.radial()
        p = at(menu, 0)
        canvas.event(NS(type="LEFTMOUSE", value="PRESS"), *p, clip, context=bpy.context)
        count = len(fixture.calls)
        bpy.utils.unregister_class(fixture.BUI_MT_pie_test)
        canvas.event(
            NS(type="LEFTMOUSE", value="RELEASE"), *p, clip, context=bpy.context
        )
        assert len(fixture.calls) == count and canvas.context_menu is None
        checks.append(
            "Exact-row property context actions survive radial navigation; removed registration rejects pending release"
        )
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, checks=checks, error=traceback.format_exc())
    finally:
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("PIE_RUNTIME", result, flush=True)


if bpy.app.background:
    run()
else:

    def window_run():
        run()
        bpy.app.timers.register(
            lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
        )

    bpy.app.timers.register(window_run, first_interval=1)
