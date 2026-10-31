"""Copy into your add-on as panels.py after running tools/vendor.py.

Call panels.register() after your RNA/operators and panels.unregister() first.
"""

import bpy
from ._vendor.beyond_ui import AddonUI

ui = AddonUI(__package__)


class MYADDON_PT_settings(bpy.types.Panel):
    bl_label = "My Settings"
    bl_idname = "MYADDON_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "My Add-on"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.render, "film_transparent", text="Transparent")
        layout.prop(
            context.scene.render, "resolution_percentage", text="Scale", slider=True
        )
        layout.prop(context.scene.render, "filepath", text="Output", icon="FILE_FOLDER")
        layout.prop(context.scene.render.image_settings, "file_format", text="Format")
        layout.operator("render.render", text="Render", icon="RENDER_STILL")


def register():
    ui.register(MYADDON_PT_settings)


def unregister():
    ui.unregister()
