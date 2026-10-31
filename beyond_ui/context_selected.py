"""Resolve supported selection domains on menu input, never during painting."""

from .rna_owner import identity


def owners(source, context):
    import bpy

    owner = source.owner()
    if isinstance(owner, bpy.types.Object):
        candidates = getattr(context, "selected_objects", ())
    elif isinstance(owner, bpy.types.PoseBone):
        candidates = getattr(context, "selected_pose_bones", ())
    elif isinstance(owner, bpy.types.Bone):
        candidates = (
            bone.bone for bone in getattr(context, "selected_pose_bones", ()) or ()
        )
    elif isinstance(owner, bpy.types.Node):
        candidates = getattr(context, "selected_nodes", ())
    elif isinstance(owner, bpy.types.ID):
        # The property belongs to object data, not to the selected object itself.
        candidates = (
            getattr(obj, "data", None)
            for obj in getattr(context, "selected_objects", ()) or ()
        )
    else:
        return ()  # Never guess a nested owner by display name or property name.

    meta = source.metadata(owner)
    signature = (meta.type, getattr(meta, "array_length", 0))
    seen = {identity(owner)}
    result = []
    for candidate in candidates or ():
        if candidate is None:
            continue
        try:
            key = identity(candidate)
            prop = source.metadata(candidate)
            if (
                key in seen
                or candidate.bl_rna.identifier != owner.bl_rna.identifier
                or prop is None
                or (prop.type, getattr(prop, "array_length", 0)) != signature
                or not getattr(candidate.id_data, "is_editable", True)
                or not source.editable(candidate)
                or (
                    source.index is not None
                    and source.index >= len(getattr(candidate, source.name))
                )
            ):
                continue
            seen.add(key)
            result.append(candidate)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, KeyError):
            continue
    return tuple(result)
