"""Boolean action presentation preserves RNA ownership and input semantics."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import Layout

try:
    bpy.types.Scene.bui_help = bpy.props.BoolProperty(default=False)
    ui = Layout(context=bpy.context)
    controls = []
    for alignment in ("LEFT", "CENTER", "RIGHT", "EXPAND"):
        row = ui.row()
        row.alignment = alignment
        c = row.prop(bpy.context.scene, "bui_help", text="HOW TO", emboss=False)
        assert c.kind == "toggle" and c.options["bool_button"]
        assert c.options["text_alignment"] == alignment and not c.motion.toggle
        controls.append(c)
    ordinary = ui.prop(bpy.context.scene, "bui_help", text="Enabled")
    assert ordinary.motion.toggle and not ordinary.options.get("bool_button")
    ui.canvas.arrange(400)
    c = controls[1]
    x, y, w, h = c.rect
    clip = (0, 0, 400, ui.canvas.height)
    assert not c.binding.read()
    for value in ("PRESS", "RELEASE"):
        ui.canvas.event(
            NS(type="LEFTMOUSE", value=value),
            x + w / 2,
            y + h / 2,
            clip,
            context=bpy.context,
        )
    assert bpy.context.scene.bui_help
    assert ui.canvas.open_context(c, x + w / 2, y + h / 2, clip, context=bpy.context)
    assert ui.canvas.context_focus is c
    assert any(row.label for row in ui.canvas.context_menu.page.rows)
    ui.canvas.cancel()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Explicit unembossed Boolean action uses centered/aligned button presentation",
            "Ordinary Boolean remains a BVT switch",
            "Click writes original RNA binding; right click resolves the same control",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
finally:
    if hasattr(bpy.types.Scene, "bui_help"):
        del bpy.types.Scene.bui_help
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
