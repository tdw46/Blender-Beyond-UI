"""Disposable registered operators shared by execution and rendering fixtures."""

import bpy

calls = []
available = True
enum_evaluations = 0
short_items = [
    ("", "Geometry", ""),
    ("A", "Cube", "Create a cube-style fixture result", 1),
    ("B", "Sphere", "Create a sphere-style fixture result", 2),
    None,
    ("", "Lighting", ""),
    ("C", "Area Light", "Create a light-style fixture result", 4),
]
long_items = [(f"I{i}", f"Action {i:03}", f"Run action {i}", i + 1) for i in range(200)]


def dynamic_items(owner, context):
    global enum_evaluations
    enum_evaluations += 1
    return long_items[: owner.count]


class BUI_OT_choice(bpy.types.Operator):
    bl_idname = "bui.choice"
    bl_label = "Choose Action"
    bl_description = "An isolated operator fixture; no scene geometry is created"
    choice: bpy.props.EnumProperty(items=short_items)
    amount: bpy.props.IntProperty(default=1)

    @classmethod
    def poll(cls, context):
        return available

    def execute(self, context):
        calls.append(
            (
                self.choice,
                self.amount,
                context.scene.as_pointer(),
                getattr(context, "fixture_object", None),
            )
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        calls.append("INVOKED")
        return self.execute(context)


class BUI_OT_long_choice(bpy.types.Operator):
    bl_idname = "bui.long_choice"
    bl_label = "Search Actions"
    choice: bpy.props.EnumProperty(items=dynamic_items)
    count: bpy.props.IntProperty(default=200, min=1, max=200)
    amount: bpy.props.IntProperty(default=1)

    def execute(self, context):
        calls.append((self.choice, self.amount, self.count))
        return {"FINISHED"}


class BUI_OT_flag_choice(bpy.types.Operator):
    bl_idname = "bui.flag_choice"
    bl_label = "Choose Channels"
    choice: bpy.props.EnumProperty(
        items=[("X", "X", "", 1), ("Y", "Y", "", 2)], options={"ENUM_FLAG"}
    )

    def execute(self, context):
        calls.append(set(self.choice))
        return {"FINISHED"}


classes = (BUI_OT_choice, BUI_OT_long_choice, BUI_OT_flag_choice)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)
