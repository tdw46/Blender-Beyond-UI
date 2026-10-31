"""RNA label omission versus explicit empty text and compact row semantics."""

import bpy
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import Layout


class LABELTEST_OT_action(bpy.types.Operator):
    bl_idname = "labeltest.action"
    bl_label = "Default action"

    def execute(self, context):
        return {"FINISHED"}


result = {}
try:
    bpy.utils.register_class(LABELTEST_OT_action)
    ui = Layout(context=bpy.context)
    a = ui.prop(bpy.context.scene.render, "film_transparent")
    b = ui.prop(bpy.context.scene.render, "film_transparent", text="")
    assert a.label == "Transparent" and b.label == "", (a.label, b.label)
    ui.operator("labeltest.action")
    assert ui.group.children[-1].label == "Default action"
    ui.operator("labeltest.action", text="", icon="SMOOTHCURVE")
    assert ui.group.children[-1].label == ""
    row = ui.row()
    toggle = row.prop(bpy.context.scene.render, "film_transparent", text="")
    spacer = row.separator(factor=2.8)
    field = row.prop(bpy.context.scene.render, "filepath", text="")
    for width in (280, 420, 560):
        ui.canvas.arrange(width)
        assert toggle.rect[2] == 52 and abs(spacer.rect[2] - 22.4) < 1e-6
        assert field.rect[2] > 150 and spacer.options["space"]
        assert not field.label and field.binding.valid()
    assert ui.separator(type="SPACE").options["space"]
    try:
        row.separator(factor=float("nan"))
    except ValueError:
        pass
    else:
        raise AssertionError("Nonfinite separator accepted")
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Omitted RNA labels preserved; explicit empty prop/operator labels respected",
            "Compact label-free switch and fixed horizontal separator preserve value space at three widths",
            "Bindings remain valid; invalid separator rejected",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
finally:
    bpy.utils.unregister_class(LABELTEST_OT_action)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
