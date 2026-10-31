"""Disposable RNA definitions for pie/menu-release execution and GPU evidence."""

import bpy
from beyond_ui import Layout

calls = []
draws = 0


class BUI_OT_pie_test(bpy.types.Operator):
    bl_idname = "bui.pie_test"
    bl_label = "Pie Test"
    slot: bpy.props.IntProperty()

    def execute(self, context):
        calls.append(self.slot)
        return {"FINISHED"}


class BUI_MT_pie_more(bpy.types.Menu):
    bl_label = "More Actions"

    def draw(self, context):
        self.layout.operator_context = "EXEC_DEFAULT"
        for i in range(20):
            self.layout.operator("bui.pie_test", text=f"Action {i:02}").slot = i + 100


class BUI_MT_pie_test(bpy.types.Menu):
    bl_label = "Marking Menu"

    def draw(self, context):
        global draws
        draws += 1
        pie = self.layout.menu_pie()
        pie.operator_context = "EXEC_DEFAULT"
        pie.operator("bui.pie_test", text="Move", icon="TRANSFORM_MOVE").slot = 0
        pie.operator("bui.pie_test", text="Rotate", icon="TRANSFORM_ROTATE").slot = 1
        pie.operator("bui.pie_test", text="Scale", icon="TRANSFORM_SCALE").slot = 2
        pie.menu("BUI_MT_pie_more")
        pie.prop(context.scene.render, "film_transparent", text="Transparent")
        pie.prop(context.scene.render, "resolution_percentage", text="Resolution")
        pie.separator()
        pie.operator("bui.pie_test", text="Duplicate", icon="DUPLICATE").slot = 7


classes = (BUI_OT_pie_test, BUI_MT_pie_more, BUI_MT_pie_test)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)


def build(context):
    ui = Layout(context=context)
    ui.title(text="Marking Menu")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    ui.menu("BUI_MT_pie_test")
    ui.canvas.arrange(640)
    button = next(c for c in ui.canvas.controls.values() if c.options.get("menu_model"))
    return ui.canvas, button
