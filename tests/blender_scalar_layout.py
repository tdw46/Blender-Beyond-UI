"""Disposable runtime checks for source scalar controls and boolean menu metadata."""

import bpy, json, os, sys, traceback, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_scalar_controls import ScalarControls
from beyond_ui import Layout
from beyond_ui.context_fields import property_row
from beyond_ui.context_menu import Target, Menu

try:
    assert (
        unittest.TextTestRunner()
        .run(unittest.defaultTestLoader.loadTestsFromTestCase(ScalarControls))
        .wasSuccessful()
    )
    commits = []
    scene = bpy.context.scene
    bpy.types.Scene.scalar_test_bool = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.scalar_test_enum = bpy.props.EnumProperty(
        items=[("A", "Alpha", ""), ("B", "Beta", "")]
    )
    row = property_row(scene, "scalar_test_bool")
    assert row.toggle
    assert not property_row(scene, "scalar_test_enum", value="A").toggle
    menu = Menu(
        Target("scalar", commit=commits.append),
        [row],
        (10, 10),
        (0, 0, 400, 200),
        context=bpy.context,
    )
    menu.choose(0, bpy.context)
    assert scene.scalar_test_bool and len(commits) == 1
    ui = Layout(context=bpy.context)
    control = ui.prop(scene, "scalar_test_bool", toggle=False)
    assert control.kind == "toggle"
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Source geometry and gestures, independent number entry, narrow bounds, transaction rollback, bounded retargetable switch travel",
            "Hue/alpha sliders and numeric entries retain color components and exact context targets",
            "Contributed RNA booleans render as switches; enum checks remain enum checks; bool commit executes once",
            "All Layout boolean paths use switches, including legacy toggle=False",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
finally:
    for name in ["scalar_test_bool", "scalar_test_enum"]:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("SCALAR_LAYOUT_RUNTIME", result)
