"""Disposable real-RNA action/presentation fixture, never part of the library."""

import bpy
from beyond_ui import Layout

calls = []
draws = polls = action_polls = 0
allowed = True
cancel_default = False
result = "FINISHED"
config = item = None


class BUI_OT_parity_action(bpy.types.Operator):
    bl_idname = "bui.parity_action"
    bl_label = "Apply Changes"
    tag: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        global action_polls
        action_polls += 1
        return allowed

    def execute(self, context):
        calls.append(self.tag)
        return {result}


class BUI_MT_parity_hold(bpy.types.Menu):
    bl_label = "More Actions"

    @classmethod
    def poll(cls, context):
        return allowed

    def draw(self, context):
        global draws
        draws += 1
        self.layout.operator_context = "EXEC_DEFAULT"
        self.layout.operator("bui.parity_action", text="Secondary action").tag = 2
        self.layout.prop(context.scene.render, "film_transparent", text="Transparent")


class BUI_PT_parity_confirm(bpy.types.Panel):
    bl_label = "Apply Output Changes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Beyond UI QA"
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
        ui.prop(context.scene.render, "filepath", text="Output", icon="FILE_FOLDER")
        ui.prop(
            context.scene.render,
            "film_transparent",
            text="Transparent",
            icon="HIDE_OFF",
        )
        ui.operator_context = "EXEC_DEFAULT"
        ui.template_popup_confirm(
            "bui.parity_action",
            text="Apply Changes",
            cancel_text="Keep Editing",
            cancel_default=cancel_default,
        ).tag = 3


classes = (BUI_OT_parity_action, BUI_MT_parity_hold, BUI_PT_parity_confirm)


def register():
    global config, item
    calls.clear()
    for cls in classes:
        bpy.utils.register_class(cls)
    config = bpy.context.window_manager.keyconfigs.new(
        "Beyond action parity disposable"
    )
    km = config.keymaps.new("Beyond action parity", space_type="EMPTY")
    item = km.keymap_items.new("bui.parity_action", "J", "PRESS", ctrl=True, shift=True)


def unregister():
    global config
    if config:
        bpy.context.window_manager.keyconfigs.remove(config)
        config = None
    for cls in reversed(classes):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)


def build(context):
    ui = Layout(context=context)
    ui.canvas.menu_commit = lambda action: None
    ui.title(text="Presentation and action parity")
    ui.prop(context.scene.render, "resolution_percentage", text="Normal field")
    plain = ui.column()
    plain.emboss = "NONE"
    plain.prop(context.scene.render, "resolution_percentage", text="Unembossed field")
    warning = ui.column()
    warning.alert = True
    warning.prop(context.scene.render, "filepath", text="Alert field")
    status = ui.column()
    status.emboss = "NONE_OR_STATUS"
    status.prop(context.active_object, "location", index=0, text="Animated status")
    ui.prop(
        context.scene.render, "film_transparent", text="Transparent", icon="HIDE_OFF"
    )
    ui.operator_context = "EXEC_DEFAULT"
    ui.operator_menu_hold(
        "bui.parity_action", text="Apply · hold for more", menu="BUI_MT_parity_hold"
    ).tag = 1
    ui.popover("BUI_PT_parity_confirm", text="Review Changes")
    ui.template_event_from_keymap_item(item, text="Shortcut")
    ui.template_component_menu(
        context.active_object,
        "location",
        name="Transform Components",
        icon="EMPTY_ARROWS",
    )
    ui.template_component_menu(
        context.scene.render.image_settings, "file_format", name="Format Components"
    )
    ui.canvas.arrange(560)
    return ui
