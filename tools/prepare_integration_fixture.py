"""Build disposable, independently vendored add-ons for blender_single_line.py."""

import argparse
from pathlib import Path
from vendor import vendor

PANEL = """import bpy

class {upper}_PT_panel(bpy.types.Panel):
    bl_idname = "{upper}_PT_panel"
    bl_label = "Legacy panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "{name}"

    def draw_hint(self):
        row = self.layout.row()
        row.enabled = False
        row.label(text="Disabled hint")

    def draw(self, context):
        ui = self.layout
        ui.prop(context.scene.render, "film_transparent", text="Transparent")
        if context.scene.render.film_transparent:
            ui.prop(context.scene.render, "filepath", text="Conditional output")
        ui.prop(context.scene.render, "resolution_percentage", slider=True)
        self.draw_hint()
        if context.scene.get("beyond_ui_test_unsupported", False):
            ui.template_curve_mapping(context.scene, "missing", brush=True)

class {upper}_OT_dialog(bpy.types.Operator):
    bl_idname = "{name}.dialog"
    bl_label = "Native dialog audit fixture"
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
        return {{"FINISHED"}}

CLASSES = ({upper}_PT_panel, {upper}_OT_dialog)
"""
MANUAL = """from bpy.utils import register_class as register_one, unregister_class as unregister_one

def register():
    for cls in CLASSES:
        register_one(cls)

def unregister():
    for cls in reversed(CLASSES):
        unregister_one(cls)
"""
LOADER = """from . import panels
import bpy

def register():
    for cls in panels.CLASSES:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(panels.CLASSES):
        bpy.utils.unregister_class(cls)
"""
HOOK = "\nfrom ._vendor.beyond_ui import integrate; integrate(globals())\n"


def prepare(root):
    for name in ("legacy_manual", "legacy_factory", "legacy_loader"):
        package = root / name
        package.mkdir(parents=True, exist_ok=True)
        vendor(package / "_vendor", replace=(package / "_vendor/beyond_ui").exists())
        panel = PANEL.format(name=name, upper=name.upper())
        if name == "legacy_factory":
            panel = (
                panel.replace(
                    'bl_space_type = "VIEW_3D"', 'bl_space_type = "PROPERTIES"'
                )
                .replace('bl_region_type = "UI"', 'bl_region_type = "WINDOW"')
                .replace(
                    'bl_category = "legacy_factory"',
                    'bl_context = "render"\n    bl_order = -1000',
                )
            )
        if name == "legacy_loader":
            (package / "panels.py").write_text(panel)
            (package / "auto_load.py").write_text(LOADER)
            source = "from . import auto_load\n\ndef register():\n    auto_load.register()\n\ndef unregister():\n    auto_load.unregister()\n"
        else:
            source = panel + (
                MANUAL
                if name == "legacy_manual"
                else "\nregister, unregister = bpy.utils.register_classes_factory(CLASSES)\n"
            )
        (package / "__init__.py").write_text(source + HOOK)
    print(root.absolute())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
