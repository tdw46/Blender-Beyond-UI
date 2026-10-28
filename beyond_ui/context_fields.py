"""Boolean and enum contributions rendered by the shared context-menu painter."""

from .context_menu import Entry
from .context_rna import Property


def property_row(data, name, *, text="", index=-1, value=None, permitted=True):
    source = Property(lambda: data, name, None if index < 0 else index)
    meta = source.owner().bl_rna.properties[name]
    label = text or meta.name

    def enabled(target, context):
        return (
            permitted
            and target.editable()
            and target.commit is not None
            and source.valid()
            and source.editable()
            and (
                value is None
                or value in source.owner().bl_rna.properties[name].enum_items
            )
        )

    def selected(target, context):
        current = source.read()
        if meta.type == "BOOLEAN":
            return bool(current[source.index] if source.index is not None else current)
        return value in current if meta.is_enum_flag else value == current

    def execute(target, context):
        if not enabled(target, context):
            raise ReferenceError("Menu property is unavailable")
        owner = source.owner()
        before = source.read()
        if meta.type == "BOOLEAN":
            if source.index is None:
                after = not before
            else:
                after = list(before)
                after[source.index] = not after[source.index]
        elif meta.is_enum_flag:
            after = set(before) ^ {value}
        else:
            after = value
        try:
            source.assign(owner, after)
            target.commit("PROPERTY")
        except Exception:
            source.assign(owner, before)
            raise

    if meta.type == "BOOLEAN" and not (getattr(meta, "is_array", False) and index < 0):
        return Entry(
            name, label, execute, enabled, checked=selected, tip=meta.description
        )
    if meta.type == "ENUM":
        if value is not None:
            return Entry(
                name + ":" + value,
                label,
                execute,
                enabled,
                checked=selected,
                tip=meta.description,
            )

        def children(target, context):
            from itertools import islice

            owner = source.owner()
            items = owner.bl_rna.properties[name].enum_items
            return tuple(
                property_row(
                    owner,
                    name,
                    text=item.name,
                    value=item.identifier,
                    permitted=permitted,
                )
                for item in islice((i for i in items if i.identifier), 63)
            )

        return Entry(
            name, label, enabled=enabled, children=children, tip=meta.description
        )
    return Entry(
        name,
        label,
        enabled=False,
        tip="This contributed field requires an inline host control; scalar editors are not flattened into menu commands.",
    )
