"""Context-aware enum items with an explicit public-RNA compatibility fallback."""


def items(owner, name, context, *, include_separators=False):
    meta = owner.bl_rna.properties[name]
    if context is not None:
        from .hosts.menu_native import enum_items

        resolved = enum_items(
            owner, name, context, include_separators=include_separators
        )
        if resolved is not None:
            return resolved
    return tuple(i for i in meta.enum_items if include_separators or i.identifier)


def contains(owner, name, identifier, context):
    return any(item.identifier == identifier for item in items(owner, name, context))


def operator_items(idname, name, context, properties=None):
    """Evaluate operator enums only on explicit menu opening, using typed scratch RNA."""
    from .context_extensions import operator
    from .hosts.menu_native import api

    if context is None or api() is None:
        return tuple(operator(idname).get_rna_type().properties[name].enum_items)
    from uuid import uuid4

    config = context.window_manager.keyconfigs.new("Beyond UI enum " + uuid4().hex)
    try:
        keymap = config.keymaps.new(name="Beyond UI enum", space_type="EMPTY")
        item = keymap.keymap_items.new(idname, "NONE", "PRESS")
        for key, value in (properties or {}).items():
            setattr(item.properties, key, value)
        return items(item.properties, name, context)
    finally:
        context.window_manager.keyconfigs.remove(config)
