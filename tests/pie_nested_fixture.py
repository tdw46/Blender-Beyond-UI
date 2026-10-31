"""Disposable nested-pie definitions, shared by RNA and GPU fixtures."""

import bpy
from beyond_ui import Layout
import pie_fixture

allowed = True
groups = []
draws = 0


class BUI_MT_nested_leaf(bpy.types.Menu):
    bl_label = "Nested Transform"

    @classmethod
    def poll(cls, context):
        return allowed

    def draw(self, context):
        global draws
        draws += 1
        pie = self.layout.menu_pie()
        pie.operator_context = "EXEC_DEFAULT"
        column = pie.box().column(heading="Transform")
        column.ui_units_x = 14
        split = column.split(factor=0.4)
        split.operator("bui.pie_test", text="Move").slot = 201
        split.operator("bui.pie_test", text="Rotate").slot = 202
        column.separator(factor=1.25, type="LINE")
        grid = column.grid_flow(
            columns=2, row_major=True, even_columns=True, even_rows=True
        )
        grid.prop(context.scene.render, "film_transparent", text="Transparent")
        grid.operator("bui.pie_test", text="Duplicate").slot = 203
        grid.operator("bui.pie_test", text="Apply").slot = 204
        grid.operator("bui.pie_test", text="Reset").slot = 205
        flow = column.column_flow(columns=2)
        for label in ("Position", "Rotation", "Scale", "Origin"):
            flow.label(text=label)
        row = column.row(align=True)
        row.scale_y = 1.15
        row.operator("bui.pie_test", text="Local").slot = 206
        row.separator_spacer()
        row.operator("bui.pie_test", text="Global").slot = 207
        column.prop(context.scene.render, "resolution_percentage", text="Resolution")
        groups.append(column)
        pie.menu("BUI_MT_pie_more")
        pie.operator("bui.pie_test", text="Finish").slot = 208


class BUI_MT_nested_parent(bpy.types.Menu):
    bl_label = "Nested Pie Menus"

    def draw(self, context):
        global draws
        draws += 1
        pie = self.layout.menu_pie()
        pie.operator_context = "EXEC_DEFAULT"
        pie.menu("BUI_MT_nested_leaf", text="Transform…")
        pie.operator("bui.pie_test", text="Duplicate").slot = 200
        pie.menu("BUI_MT_pie_more")


class BUI_MT_nested_list(bpy.types.Menu):
    bl_label = "List to Pie"

    def draw(self, context):
        self.layout.menu("BUI_MT_nested_leaf")


classes = (BUI_MT_nested_leaf, BUI_MT_nested_parent, BUI_MT_nested_list)


def register():
    pie_fixture.register()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)
    pie_fixture.unregister()


def build(context, name="BUI_MT_nested_parent"):
    ui = Layout(context=context)
    ui.title(text="Nested pies · retained compound layouts")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    ui.menu(name)
    ui.canvas.arrange(1200)
    opener = next(c for c in ui.canvas.controls.values() if c.options.get("menu_model"))
    return ui.canvas, opener
