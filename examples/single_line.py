"""Use this as your add-on __init__.py after vendoring into its _vendor folder.

Existing add-ons only need the final integration line: keep their own classes
and registration code. Exclude _vendor from recursive auto-discovery.
"""

import bpy


class MYADDON_PT_settings(bpy.types.Panel):
    bl_label = "My Settings"
    bl_idname = "MYADDON_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "My Add-on"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.render, "film_transparent", text="Transparent")
        if context.scene.render.film_transparent:
            layout.prop(context.scene.render, "filepath", text="Output")
        layout.prop(context.scene.render, "resolution_percentage", slider=True)
        layout.operator("render.render", text="Render")


register, unregister = bpy.utils.register_classes_factory((MYADDON_PT_settings,))

from ._vendor.beyond_ui import integrate; integrate(globals())
