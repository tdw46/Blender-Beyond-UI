"""Disposable Python panel definitions; no production registration ownership."""

import bpy
from beyond_ui import Layout
import registered_menus_fixture as menus

allowed = True
draws = polls = 0


class BUI_PT_popover(bpy.types.Panel):
    bl_label = "Render Controls"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Popover Fixture"
    bl_ui_units_x = 16

    @classmethod
    def poll(cls, context):
        global polls
        polls += 1
        return allowed

    def draw_header(self, context):
        self.layout.prop(context.scene.render, "film_transparent", text="Header")

    def draw(self, context):
        global draws
        draws += 1
        assert self.is_popover and self.layout.is_popover
        ui = self.layout
        ui.prop(context.scene.render, "film_transparent", text="Transparent")
        ui.prop(
            context.scene.render, "resolution_percentage", text="Scale", slider=True
        )
        ui.prop(context.scene.render, "filepath", text="Output")
        ui.menu("BUI_MT_settings", text="Settings Menu")
        ui.popover("BUI_PT_nested", text="Nested Controls")
        ui.operator_context = "EXEC_DEFAULT"
        ui.operator("bui.menu_action", text="Run Action").amount = 17


class BUI_PT_nested(bpy.types.Panel):
    bl_label = "Nested Controls"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Popover Fixture"
    bl_ui_units_x = 14
    bl_order = 2

    def draw(self, context):
        global draws
        draws += 1
        self.layout.prop(context.scene.render, "film_transparent", text="Nested Toggle")
        self.layout.popover("BUI_PT_nested", text="Another Level")


class BUI_PT_property(bpy.types.Panel):
    bl_label = "Display Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Property Fixture"

    def draw(self, context):
        global draws
        draws += 1
        assert context.button_pointer == context.object
        assert context.button_prop.identifier == "display_type"
        self.layout.props_enum(context.button_pointer, "display_type")


class BUI_PT_color(bpy.types.Panel):
    bl_label = "Color Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Property Fixture"

    def draw(self, context):
        assert context.button_pointer == context.object
        assert context.button_prop.identifier == "color"
        self.layout.template_color_picker(context.button_pointer, "color")


class BUI_PT_long(bpy.types.Panel):
    bl_label = "Scrollable Controls"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Long Fixture"

    def draw(self, context):
        global draws
        draws += 1
        for i in range(50):
            self.layout.prop(
                context.scene.render, "film_transparent", text=f"Toggle {i:02}"
            )


class BUI_PT_bad(bpy.types.Panel):
    bl_label = "Unsupported Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Bad Fixture"

    def draw(self, context):
        self.layout.label(text="Must not leak")
        self.layout.template_list("BUI_UL_UNSUPPORTED", "", None, "", None, "")


class BUI_PT_bad_header(BUI_PT_bad):
    bl_idname = "BUI_PT_bad_header"
    bl_label = "Unsupported Header"

    def draw_header(self, context):
        self.layout.prop(context.scene.render, "film_transparent", text="Must not leak")
        self.layout.template_list("BUI_UL_UNSUPPORTED", "", None, "", None, "")


class BUI_PT_failed(BUI_PT_bad):
    bl_idname = "BUI_PT_failed"
    bl_label = "Failed Callback"

    def draw(self, context):
        self.layout.label(text="Must not leak")
        raise TypeError("Fixture callback failure")


classes = (
    BUI_PT_popover,
    BUI_PT_nested,
    BUI_PT_property,
    BUI_PT_color,
    BUI_PT_long,
    BUI_PT_bad,
    BUI_PT_bad_header,
    BUI_PT_failed,
)


def register():
    menus.register()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if getattr(cls, "is_registered", False):
            bpy.utils.unregister_class(cls)
    menus.unregister()


def build(context):
    commits = []
    ui = Layout(context=context, commit=lambda a, b: commits.append((a, b)))
    ui.title(text="Custom Panel Popovers")
    ui.prop(context.scene.render, "film_transparent", text="Background")
    ui.prop(context.scene.render, "resolution_percentage", text="Scale", slider=True)
    ui.popover("BUI_PT_popover")
    ui.prop_with_popover(
        context.object, "display_type", panel="BUI_PT_property", text="Display"
    )
    ui.prop_with_popover(context.object, "color", panel="BUI_PT_color", text="Color")
    ui.popover("BUI_PT_long")
    return ui, commits
