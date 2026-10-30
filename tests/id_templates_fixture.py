"""Disposable data-block controls. No user files or preferences are saved."""

import bpy
from beyond_ui import Canvas, Layout

calls = []


class BUI_IDSlots(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(type=bpy.types.Material)
    other: bpy.props.PointerProperty(type=bpy.types.Material)


class BUI_OT_id_new(bpy.types.Operator):
    bl_idname = "bui.id_new"
    bl_label = "Create Fixture Material"

    @classmethod
    def poll(cls, context):
        return getattr(context, "template_id_ptr", None) is not None

    def execute(self, context):
        owner, prop = context.template_id_ptr, context.template_id_prop
        calls.append((owner.as_pointer(), prop, getattr(context, "id", None)))
        setattr(owner, prop, bpy.data.materials.new("Created Material"))
        return {"FINISHED"}

    def invoke(self, context, event):
        calls.append("INVOKED")
        return self.execute(context)


def register():
    bpy.utils.register_class(BUI_IDSlots)
    bpy.utils.register_class(BUI_OT_id_new)
    bpy.types.Scene.bui_ids = bpy.props.PointerProperty(type=BUI_IDSlots)
    slots = bpy.context.scene.bui_ids
    if slots.material is None:
        slots.material = bpy.data.materials.new("Glass Surface")
        slots.other = slots.material
        bpy.data.materials.new("Accent Surface")
        bpy.data.materials.new(".Hidden Surface")
    return slots


def unregister():
    if hasattr(bpy.types.Scene, "bui_ids"):
        del bpy.types.Scene.bui_ids
    for cls in (BUI_OT_id_new, BUI_IDSlots):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)


def build(context, **kwargs):
    canvas = Canvas()
    ui = Layout(canvas, context, **kwargs)
    ui.title(text="Data-blocks")
    ui.template_ID(context.scene.bui_ids, "material", new="bui.id_new", text="Material")
    controls = list(canvas.controls.values())
    picker = next(c for c in controls if c.kind == "pointer")
    name = next(c for c in controls if c.kind == "text")
    fake = next(c for c in controls if c.kind == "toggle")
    ui.title(text="Material Tabs")
    ui.template_ID_tabs(context.scene.bui_ids, "material")
    ui.title(text="Ordinary Fields")
    ui.prop(context.scene.render, "resolution_percentage", text="Scale", slider=True)
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    return ui, picker, name, fake
