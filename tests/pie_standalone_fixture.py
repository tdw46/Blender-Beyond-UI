"""Shared standalone/registered compound definition for disposable QA."""

import bpy
from beyond_ui import Layout
import pie_nested_fixture
import pie_fixture

allowed = True
draws = 0


def contents(pie, context, *, initialize=False):
    pie.operator_context = "EXEC_DEFAULT"
    col = pie.box().column(heading="Transform")
    col.ui_units_x = 17
    split = col.split(factor=0.4)
    split.operator("bui.pie_test", text="Move").slot = 301
    split.operator("bui.pie_test", text="Rotate").slot = 302
    col.separator(type="LINE")
    col.prop(context.scene.render, "film_transparent", text="Transparent")
    row = col.row()
    row.alert = True
    row.operator("bui.pie_test", text="Reset transform").slot = 303
    col.prop(context.scene.render, "resolution_percentage", text="Resolution")
    plain = col.column()
    plain.emboss = "NONE"
    plain.prop(context.scene.render, "resolution_percentage", text="Unembossed")
    decorated = col.column()
    decorated.use_property_split = True
    decorated.activate_init = initialize
    decorated.prop(context.active_object, "location", index=0, text="Location X")
    undecorated = col.column()
    undecorated.use_property_split = True
    undecorated.use_property_decorate = False
    undecorated.prop(context.active_object, "location", index=1, text="Location Y")
    pie.menu("BUI_MT_pie_more")
    default = pie.column()
    default.active_default = True
    default.operator("bui.pie_test", text="Finish").slot = 304


class BUI_MT_standalone_child(bpy.types.Menu):
    bl_label = "Compound Flags"

    @classmethod
    def poll(cls, context):
        return allowed

    def draw(self, context):
        global draws
        draws += 1
        contents(self.layout.menu_pie(), context)


def register():
    pie_nested_fixture.register()
    bpy.utils.register_class(BUI_MT_standalone_child)


def unregister():
    if BUI_MT_standalone_child.is_registered:
        bpy.utils.unregister_class(BUI_MT_standalone_child)
    pie_nested_fixture.unregister()


def build(context):
    ui = Layout(context=context)
    ui.canvas.menu_commit = lambda action: None  # Disposable host owns undo.
    ui.title(text="Standalone pies · compound flags")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    pie = ui.menu_pie()
    pie.operator_context = "EXEC_DEFAULT"
    pie.menu("BUI_MT_standalone_child", text="Transform…")
    pie.operator("bui.pie_test", text="Duplicate").slot = 300
    pie.menu("BUI_MT_pie_more")
    ui.canvas.arrange(1200)
    return ui.canvas, pie
