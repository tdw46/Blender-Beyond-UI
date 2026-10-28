"""RNA field contributions rendered by the shared context-menu painter."""

from .context_menu import Entry
from .context_rna import Property
from .context_enums import items, contains


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
        if meta.type == "ENUM" and not contains(owner, name, value, context):
            raise ReferenceError("Enum choice changed; reopen the menu")
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

    if getattr(meta, "is_array", False) and index < 0:

        def components(target, context):
            from itertools import islice

            return tuple(
                property_row(
                    source.owner(),
                    name,
                    text=f"{label} [{i}]",
                    index=i,
                    permitted=permitted,
                )
                for i in islice(range(len(source.read())), 63)
            )

        return Entry(
            name, label, enabled=enabled, children=components, tip=meta.description
        )
    if meta.type in {"INT", "FLOAT", "STRING"}:
        from .context_edit import Field
        from .editing import number

        def read(target, context):
            current = source.read()
            return current[source.index] if source.index is not None else current

        def apply(text, original, target, context):
            if not enabled(target, context) or read(target, context) != original:
                raise ReferenceError("Property changed; cancel and reopen the field")
            if meta.type == "STRING":
                after = text[: meta.length_max] if meta.length_max else text
            else:
                after = number(text)
                after = round(after) if meta.type == "INT" else after
                after = min(meta.hard_max, max(meta.hard_min, after))
            before = source.read()
            value = after
            if source.index is not None:
                value = list(before)
                value[source.index] = after
            try:
                source.assign(source.owner(), value)
                if read(target, context) != original:
                    target.commit("PROPERTY")
            except Exception:
                if source.valid():
                    source.assign(source.owner(), before)
                raise

        return Entry(
            name, label, enabled=enabled, field=Field(read, apply), tip=meta.description
        )

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
            choices = items(owner, name, context)
            return tuple(
                property_row(
                    owner,
                    name,
                    text=item.name,
                    value=item.identifier,
                    permitted=permitted,
                )
                for item in islice((i for i in choices if i.identifier), 63)
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
