"""Sizing policy execution with real RNA and disposable data."""

import bpy, sys, os, json, traceback, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_layout_sizing import Sizing
from sizing_fixture import build

try:
    assert (
        unittest.TextTestRunner()
        .run(unittest.defaultTestLoader.loadTestsFromTestCase(Sizing))
        .wasSuccessful()
    )
    ui, toggles, groups, commits = build(bpy.context)
    canvas = ui.canvas
    for width in (280, 560, 900):
        canvas.arrange(width)
        for control in toggles:
            x, y, w, h = control.rect
            assert canvas.hit(x + w / 2, y + h / 2, (0, 0, width, 2000)) is control
            assert h == 48
        compound = next(c for c in canvas.controls.values() if c.kind == "widget")
        widget = compound.options["widget"]
        assert (
            abs(compound.rect[2] / compound.rect[3] - widget.width / widget.height)
            < 1e-8
        )
    canvas.arrange(560)
    c = toggles[0]
    value = c.binding.read()
    canvas._begin(c)
    canvas.edit.update(not value)
    groups["tall"].scale_y = 2
    assert c.binding.read() == value and not commits and canvas.edit is None
    canvas.arrange(560)
    assert c.rect[3] == 64
    x, y, w, h = c.rect
    assert canvas.open_context(
        c, x + w / 2, y + h / 2, (0, 0, 560, 1000), context=bpy.context
    )
    assert canvas.context_menu.target.binding.context.name == "film_transparent"
    groups["fixed"].ui_units_x = 6
    assert canvas.context_menu is None
    canvas.cancel()
    assert not canvas.advance_animations()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=[
            "Sizing geometry suite in Blender Python",
            "Real RNA hit mapping at narrow/normal/wide bounds",
            "Compound aspect retained inside fixed height",
            "Live sizing cancels edits with rollback and closes stale menus",
            "Source motion teardown remains quiescent",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("SIZING", result)
