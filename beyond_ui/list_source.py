"""Collection-list snapshots. RNA traversal happens on explicit refresh, not paint."""

from dataclasses import dataclass, field, replace
from fnmatch import fnmatchcase
from .bindings import Edit, rna_binding
from .rna_owner import guarded, identity


@dataclass(frozen=True)
class Item:
    index: int
    identity: object
    name: str
    name_property: str
    owner: object = field(default=None, compare=False, repr=False)


class CollectionSource:
    limit = 100_000

    def __init__(self, layout, data, prop, active_data, active_prop):
        self.layout, self.prop = layout, prop
        self.resolve = guarded(layout.resolve(data) if layout.resolve else lambda: data)
        self.owner = identity(data)
        meta = data.bl_rna.properties.get(prop)
        active_meta = active_data.bl_rna.properties.get(active_prop)
        if meta is None or meta.type != "COLLECTION":
            raise TypeError("template_list requires a collection property")
        # IDProperty arrays can move their contents without changing slot addresses.
        # Only the consuming extension can supply a durable identity for such rows.
        self.key = layout.list_identity
        bases, current = set(), meta.fixed_type
        while current is not None:
            bases.add(current.identifier)
            current = current.base
        if self.key is None and "PropertyGroup" in bases:
            raise ValueError(
                "PropertyGroup lists require Layout(list_identity=...) with unique stable host keys"
            )
        if active_meta is None or active_meta.type != "INT" or active_meta.is_array:
            raise TypeError("template_list requires a scalar integer active property")
        self.active = rna_binding(
            layout.resolve(active_data) if layout.resolve else lambda: active_data,
            active_prop,
            commit=layout.commit,
            source=layout.source,
        )
        self.items = ()
        self.refresh()

    def collection(self):
        owner = self.resolve()
        if identity(owner) != self.owner:
            raise ReferenceError("List collection owner changed")
        return getattr(owner, self.prop)

    def valid(self):
        try:
            self.collection()
            return True
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def valid_item(self, item):
        try:
            values = self.collection()
            return (
                len(values) == len(self.items)
                and bool(item.owner.as_pointer())
                and self.item_identity(values[item.index]) == item.identity
            )
        except (ReferenceError, RuntimeError, AttributeError, IndexError):
            return False

    def item_identity(self, value):
        return (
            self.key(self.resolve(), self.prop, value) if self.key else identity(value)
        )

    def refresh(self):
        values = self.collection()
        if len(values) > self.limit:
            raise ValueError(
                "Collection list exceeds 100000 items; provide a bounded collection"
            )
        items, keys = [], set()
        for index, value in enumerate(values):
            key = self.item_identity(value)
            if key in keys:
                raise ValueError(
                    "List identity keys must be unique within the collection"
                )
            keys.add(key)
            prop = getattr(value.bl_rna, "name_property", None)
            name = prop.identifier if prop is not None else ""
            items.append(
                Item(
                    index,
                    key,
                    str(getattr(value, name)) if name else "",
                    name,
                    value,
                )
            )
        self.items = tuple(items)

    def name_binding(self, item):
        if not item.name_property:
            return None

        def resolve():
            if not self.valid_item(item):
                raise ReferenceError("List row changed; refresh the list")
            return self.collection()[item.index]

        return rna_binding(
            resolve,
            item.name_property,
            commit=self.layout.commit,
            source=self.layout.source,
        )

    def select(self, item):
        if not self.valid_item(item):
            raise ReferenceError("List row changed; refresh the list")
        edit = Edit(self.active)
        try:
            edit.update(item.index)
            edit.finish()
        except Exception:
            edit.finish(cancel=True)
            raise

    def rename(self, item, name):
        binding = self.name_binding(item)
        if binding is None:
            return
        edit = Edit(binding)
        try:
            edit.update(name)
            edit.finish()
        except Exception:
            edit.finish(cancel=True)
            raise
        # Blender may uniquify a name. Keep the actual result, not submitted text.
        updated = replace(item, name=str(binding.read()))
        self.items = tuple(
            updated if row.index == item.index else row for row in self.items
        )


def ordered(items, query="", *, invert=False, alpha=False, reverse=False):
    """Blender's case-insensitive wildcard filter and stable original-index mapping."""
    pattern = "*" + query.casefold() + "*"
    rows = [
        item
        for item in items
        if not query or (fnmatchcase(item.name.casefold(), pattern) != invert)
    ]
    if alpha:
        rows.sort(key=lambda item: item.name.casefold())
    if reverse:
        rows.reverse()
    return tuple(rows)
