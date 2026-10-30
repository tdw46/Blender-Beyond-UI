"""Disposable registered menus, operator and property owners for custom UI QA."""

import bpy
from beyond_ui import Canvas, Layout

calls = []
allowed = True
draws = 0
polls = 0
operator_polls = 0
many_count = 100


class BUI_OT_menu_action(bpy.types.Operator):
    bl_idname = "bui.menu_action"
    bl_label = "Menu Action"
    amount: bpy.props.IntProperty(default=1)
    choice: bpy.props.EnumProperty(items=[("A", "Alpha", ""), ("B", "Beta", "")])

    @classmethod
    def poll(cls, context):
        global operator_polls
        operator_polls += 1
        return True

    def execute(self, context):
        calls.append((self.amount, self.choice, getattr(context, "menu_owner", None)))
        return {"FINISHED"}


class BUI_MT_nested(bpy.types.Menu):
    bl_label = "Nested Actions"

    def helper(self, context):
        self.layout.operator_context = "EXEC_DEFAULT"
        self.layout.operator("bui.menu_action", text="Nested Action").amount = 42

    def draw(self, context):
        self.helper(context)


class BUI_MT_settings(bpy.types.Menu):
    bl_label = "Render Settings"

    @classmethod
    def poll(cls, context):
        global polls
        polls += 1
        return allowed

    def draw(self, context):
        global draws
        draws += 1
        ui = self.layout
        ui.label(text="Rendering")
        ui.prop(context.scene.render, "film_transparent", text="Transparent")
        ui.prop(context.scene.render, "resolution_percentage", text="Scale")
        ui.prop(context.scene.render, "filepath", text="Output")
        ui.separator()
        ui.menu("BUI_MT_nested")
        ui.menu("BUI_MT_many")
        ui.operator_context = "EXEC_DEFAULT"
        ui.context_pointer_set("menu_owner", context.scene)
        ui.operator("bui.menu_action", text="Run Action").amount = 7
        ui.operator_menu_enum(
            "bui.menu_action", "choice", text="Choose Action"
        ).amount = 9
        disabled = ui.column()
        disabled.operator("bui.menu_action", text="Unavailable")
        disabled.enabled = False


class BUI_MT_many(bpy.types.Menu):
    bl_label = "Many Actions"

    def draw(self, context):
        self.layout.operator_context = "EXEC_DEFAULT"
        for i in range(many_count):
            self.layout.operator("bui.menu_action", text=f"Action {i:03}").amount = i


class BUI_MT_enum(bpy.types.Menu):
    bl_label = "Display Type"

    def draw(self, context):
        assert context.button_pointer == context.object
        assert context.button_prop.identifier == "display_type"
        self.layout.props_enum(context.button_pointer, "display_type")


class BUI_MT_inline(bpy.types.Menu):
    bl_label = "Inline Contents"

    @classmethod
    def poll(cls, context):
        global polls
        polls += 1
        return allowed

    def draw(self, context):
        ui = self.layout
        ui.prop(context.scene.render, "film_transparent", text="Transparent")
        ui.prop(
            context.scene.render, "resolution_percentage", text="Scale", slider=True
        )
        ui.operator_context = "EXEC_DEFAULT"
        ui.operator("bui.menu_action", text="Inline Action").amount = 11


class BUI_MT_bad(bpy.types.Menu):
    bl_label = "Unsupported Contents"

    def draw(self, context):
        self.layout.label(text="This must not leak")
        self.layout.template_list("BUI_UL_UNSUPPORTED", "", "objects", "objects", None, "")


classes = (
    BUI_OT_menu_action,
    BUI_MT_nested,
    BUI_MT_settings,
    BUI_MT_many,
    BUI_MT_enum,
    BUI_MT_inline,
    BUI_MT_bad,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)


def build(context):
    canvas = Canvas()
    commits = []
    ui = Layout(canvas, context, commit=lambda a, b: commits.append((a, b)))
    ui.title(text="Registered Menus")
    ui.menu("BUI_MT_settings")
    settings = list(canvas.controls.values())[-1]
    ui.menu("BUI_MT_many")
    many = list(canvas.controls.values())[-1]
    ui.prop_with_menu(
        context.object, "display_type", text="Display", menu="BUI_MT_enum"
    )
    attached = list(canvas.controls.values())[-1]
    ui.title(text="Inline Menu Contents")
    ui.menu_contents("BUI_MT_inline")
    return ui, settings, many, attached, commits
