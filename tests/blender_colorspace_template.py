"""Disposable input-color-space template binding/ownership regression."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout

image = None
try:
    image = bpy.data.images.new("Beyond UI isolated colorspace", width=8, height=8)
    commits = []
    ui = Layout(context=bpy.context, commit=lambda a, b: commits.append((a, b)))
    ui.template_colorspace_settings(image, "colorspace_settings")
    ui.canvas.arrange(400)
    control = next(iter(ui.canvas.controls.values()))
    assert control.kind == "enum" and control.label == "Color Space"
    assert ui.canvas.open_enum_menu(control, (0, 0, 400, 500), bpy.context), (
        ui.canvas.menu_error
    )
    field = control.options["enum_field"]
    before = image.colorspace_settings.name
    choices = field.snapshot()
    choice = next(i for i in choices if i.identifier and i.identifier != before)
    field.choose(choice)
    assert image.colorspace_settings.name == choice.identifier and len(commits) == 1
    ui.canvas.cancel()
    assert ui.canvas.open_context(
        control, 20, 20, (0, 0, 400, 500), context=bpy.context
    )
    target = ui.canvas.context_menu.target
    assert target.binding.context.owner() == image.colorspace_settings
    ui.canvas.cancel()
    bpy.data.images.remove(image)
    image = None
    assert not control.enabled and not target.valid()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Custom searchable enum changes exact input color-space RNA with host commit",
            "Exact settings owner context menu",
            "Image deletion invalidates selector and existing target",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
finally:
    if image is not None:
        bpy.data.images.remove(image)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
