"""RNA search transactions and shared generic-menu behavior in a disposable profile."""

import bpy, json, os, sys, traceback, unittest
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Canvas, Layout
from test_menu_search import SearchMenus


def run():
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SearchMenus)
        assert unittest.TextTestRunner().run(suite).wasSuccessful()
        choices = [(f"I{i}", f"Option {i:03}", f"Item {i}") for i in range(200)]
        bpy.types.Scene.menu_search_test = bpy.props.EnumProperty(items=choices)
        commits = []
        ui = Layout(Canvas(), bpy.context, commit=lambda a, b: commits.append((a, b)))
        field = ui.prop(bpy.context.scene, "menu_search_test")
        ui.canvas.arrange(560)
        assert ui.canvas.open_enum_menu(field, (0, 0, 560, 520), bpy.context)
        menu = ui.canvas.context_menu
        for char in "Option 199":
            menu.event(NS(type="A", value="PRESS", unicode=char), 20, 20, bpy.context)
        assert [r.key for r in menu.page.rows] == ["enum:I199"]
        assert not commits and bpy.context.scene.menu_search_test == "I0"
        menu.event(NS(type="RET", value="PRESS", unicode="\r"), 20, 20, bpy.context)
        assert bpy.context.scene.menu_search_test == "I199" and len(commits) == 1
        assert ui.canvas.open_enum_menu(field, (0, 0, 560, 520), bpy.context)
        menu = ui.canvas.context_menu
        for char in "198":
            menu.event(NS(type="A", value="PRESS", unicode=char), 20, 20, bpy.context)
        bpy.context.scene.menu_search_test = "I10"
        menu.event(NS(type="RET", value="PRESS"), 20, 20, bpy.context)
        assert (
            menu.closed
            and bpy.context.scene.menu_search_test == "I10"
            and len(commits) == 1
        )
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            checks=[
                "Shared menu search tests: grouped, nested, empty, disabled, stale, clipboard, cancellation, clipping, flag ownership",
                "RNA enum type-to-search makes no writes until Enter; exact identifier commits once",
                "Enter control characters do not become query text",
                "Concurrent RNA changes reject stale filtered selection",
            ],
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        if hasattr(bpy.types.Scene, "menu_search_test"):
            del bpy.types.Scene.menu_search_test
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("MENU_SEARCH_RUNTIME", result)


run()
