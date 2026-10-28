"""Bounded context-relative property paths for Blender favorites/keymaps."""

# Context-relative actions intentionally follow Blender's future active owner,
# just like native favorites. At creation, resolve the exact clicked owner.
ROOTS = (
    "object",
    "active_object",
    "scene",
    "material",
    "world",
    "collection",
    "active_pose_bone",
    "pose_bone",
    "bone",
    "edit_bone",
    "space_data",
    "tool_settings",
    "view_layer",
    "brush",
)


def owner_path(source, context):
    owner = source.owner()
    pointer = owner.as_pointer()
    for name in ROOTS:
        root = getattr(context, name, None)
        if root is None or not hasattr(root, "as_pointer"):
            continue
        if root.as_pointer() == pointer:
            return name
        identity = getattr(owner, "id_data", None)
        if identity is None or root.as_pointer() != identity.as_pointer():
            continue
        try:
            nested = owner.path_from_id()
            if nested and root.path_resolve(nested).as_pointer() == pointer:
                return name + ("" if nested.startswith("[") else ".") + nested
        except (ValueError, AttributeError, ReferenceError):
            continue
    return None


def property_path(source, context):
    path = owner_path(source, context)
    if path is None:
        return None
    path += "." + source.name
    if source.index is not None:
        path += f"[{source.index}]"
    return path
