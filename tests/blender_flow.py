"""Disposable RNA and retained-layout checks; no scene or preference saves."""

import bpy, sys, os, json, unittest, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_flow import Flow
from flow_fixture import build

try:
    assert (
        unittest.TextTestRunner()
        .run(unittest.defaultTestLoader.loadTestsFromTestCase(Flow))
        .wasSuccessful()
    )
    ui, toggles, disabled, calls = build(bpy.context)
    canvas = ui.canvas
    value = bpy.context.scene.render.film_transparent
    for width in (280, 560, 900):
        canvas.arrange(width)
        control = toggles[0]
        x, y, w, h = control.rect
        assert canvas.hit(x + w / 2, y + h / 2, (0, 0, width, 2000)) is control
        assert all(c.rect[2] >= 0 and c.rect[3] >= 0 for c in canvas.controls.values())
    canvas._begin(toggles[0])
    canvas.edit.update(not value)
    ui.enabled = False
    assert bpy.context.scene.render.film_transparent == value
    assert canvas.active is None and not any(
        c.enabled for c in canvas.controls.values()
    )
    ui.enabled = True
    assert toggles[0].enabled
    assert not disabled.group.children[0].enabled
    canvas.cancel()
    assert not canvas.advance_animations()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=[
            "unit suite in Blender Python",
            "real RNA grid owner hit after reflow",
            "ancestor disable rolls back RNA edit",
            "descendant active state retained",
            "teardown quiescent",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("FLOW_RUNTIME", result)
