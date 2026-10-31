"""Owned object/active-pose navigation, with selection rollback on rejected undo."""

from .context_menu import Entry
from .rna_owner import identity


def entries(resolve):
    import bpy

    item = resolve()
    if not isinstance(item, (bpy.types.Object, bpy.types.PoseBone, bpy.types.Bone)):
        return ()
    key = identity(item)

    def destination(t, c):
        value = resolve()
        if not t.valid() or t.commit is None or identity(value) != key:
            return None
        if isinstance(value, bpy.types.Object):
            return (
                (value, None)
                if c.mode == "OBJECT"
                and value.name in c.view_layer.objects
                and value.visible_get(view_layer=c.view_layer)
                and not value.hide_select
                else None
            )
        obj = c.active_object
        if c.mode != "POSE" or obj is None or obj.type != "ARMATURE":
            return None
        bone = value.bone if isinstance(value, bpy.types.PoseBone) else value
        if bone.id_data != obj.data or bone.hide or bone.hide_select:
            return None
        pose = obj.pose.bones.get(bone.name)
        return (obj, pose) if pose else None

    def execute(t, c):
        resolved = destination(t, c)
        if resolved is None:
            raise ReferenceError("Target is unavailable in this view layer or mode")
        obj, pose = resolved
        if pose:

            def selection(b):
                return b if hasattr(b, "select") else b.bone

            states = [(selection(b), selection(b).select) for b in obj.pose.bones]
            active = obj.data.bones.active
            try:
                for bone, _ in states:
                    bone.select = False
                selection(pose).select = True
                obj.data.bones.active = pose.bone
                t.commit("JUMP_TARGET")
            except Exception:
                for bone, selected in states:
                    bone.select = selected
                obj.data.bones.active = active
                raise
        else:
            states = [
                (o, o.select_get(view_layer=c.view_layer)) for o in c.view_layer.objects
            ]
            active = c.view_layer.objects.active
            try:
                for other, _ in states:
                    other.select_set(other == obj, view_layer=c.view_layer)
                c.view_layer.objects.active = obj
                t.commit("JUMP_TARGET")
            except Exception:
                for other, selected in states:
                    other.select_set(selected, view_layer=c.view_layer)
                c.view_layer.objects.active = active
                raise

    return (
        Entry(
            "JUMP_TARGET",
            "Jump to Target",
            execute,
            lambda t, c: destination(t, c) is not None,
            tip="Visible objects in Object Mode, or bones on the active pose rig. Hidden/excluded owners and mode transitions require host routing.",
        ),
    )
