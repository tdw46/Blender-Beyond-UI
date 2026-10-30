"""Disposable popup keyboard fixture; registration stays outside the library."""

import bpy
from beyond_ui import Layout

allowed = True
draws = polls = action_polls = 0
calls = []


class BUI_OT_focus_apply(bpy.types.Operator):
    bl_idname = "bui.focus_apply"
    bl_label = "Apply Output"
    tag: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        global action_polls
        action_polls += 1
        return allowed

    def execute(self, context):
        calls.append(
            (
                self.tag,
                context.scene.render.filepath,
                context.scene.render.resolution_percentage,
            )
        )
        return {"FINISHED"}


class BUI_PT_focus_text(bpy.types.Panel):
    bl_label = "Output Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BUI Focus Fixture"
    bl_ui_units_x = 18

    @classmethod
    def poll(cls, context):
        global polls
        polls += 1
        return allowed

    def draw(self, context):
        global draws
        draws += 1
        ui = self.layout
        ui.activate_init = True
        ui.prop(context.scene.render, "filepath", text="Output")
        ui.activate_init = False
        ui.prop(context.scene.render, "film_transparent", text="Transparent")
        ui.popover("BUI_PT_focus_number", text="Resolution")
        ui.operator_context = "EXEC_DEFAULT"
        ui.active_default = True
        ui.operator("bui.focus_apply", text="Apply Output").tag = "text"


class BUI_PT_focus_number(BUI_PT_focus_text):
    bl_idname = "BUI_PT_focus_number"
    bl_label = "Resolution Settings"
    bl_ui_units_x = 16

    def draw(self, context):
        global draws
        draws += 1
        ui = self.layout
        ui.activate_init = True
        ui.prop(
            context.scene.render, "resolution_percentage", text="Scale", slider=True
        )
        ui.activate_init = False
        ui.operator_context = "EXEC_DEFAULT"
        ui.active_default = True
        ui.operator("bui.focus_apply", text="Apply Resolution").tag = "number"


classes = (BUI_OT_focus_apply, BUI_PT_focus_text, BUI_PT_focus_number)


def register():
    calls.clear()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if getattr(cls, "is_registered", False):
            bpy.utils.unregister_class(cls)


def build(context):
    commits = []
    ui = Layout(context=context, commit=lambda a, b: commits.append((a, b)))
    ui.title(text="Popup Keyboard Actions")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    ui.prop(context.scene.render, "resolution_percentage", text="Scale", slider=True)
    ui.popover("BUI_PT_focus_text", text="Output Settings")
    ui.popover("BUI_PT_focus_number", text="Resolution Settings")
    return ui, commits
