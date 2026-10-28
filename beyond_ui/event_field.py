"""Custom event property fields using the shared bounded capture menu.

No keymap creation or registration. Full-event edits target an existing,
identity-checked KeyMapItem and commit/rollback the entire changed chord.
"""

from functools import lru_cache
from types import MappingProxyType
from .context_shortcuts import MODIFIERS, capture_entry, conflict_maps, item_signature


@lru_cache(maxsize=1)
def event_types():
    import bpy

    return MappingProxyType(
        {
            i.identifier: (i.value, i.name)
            for i in bpy.types.Event.bl_rna.properties["type"].enum_items
            if i.identifier
        }
    )


@lru_cache(maxsize=1)
def event_labels():
    return MappingProxyType({code: name for code, name in event_types().values()})


class EventField:
    def __init__(self, binding, *, full=False):
        self.binding = binding
        self.source = binding.context
        self.full = full
        owner = self.source.owner()
        meta = owner.bl_rna.properties[self.source.name]
        if (
            meta.type not in {"INT", "ENUM"}
            or getattr(meta, "is_array", False)
            or getattr(meta, "is_enum_flag", False)
        ):
            raise ValueError("Event fields require a scalar integer or event enum")
        if full and (
            owner.bl_rna.identifier != "KeyMapItem" or self.source.name != "type"
        ):
            raise ValueError("Full event capture requires KeyMapItem.type")
        self.keymap_item = (
            owner.bl_rna.identifier == "KeyMapItem" and self.source.name == "type"
        )
        self.integer = meta.type == "INT"
        self.types = event_types()
        self.labels = event_labels()
        self.names = (
            tuple(
                n
                for n in (
                    "map_type",
                    "type",
                    "value",
                    "any",
                    "shift",
                    "ctrl",
                    "alt",
                    "oskey",
                    "hyper",
                    "key_modifier",
                    "repeat",
                    "direction",
                )
                if n in owner.bl_rna.properties
            )
            if self.keymap_item
            else (self.source.name,)
        )

    def snapshot(self):
        owner = self.source.owner()
        return {name: getattr(owner, name) for name in self.names}

    def format(self, value):
        if self.full:
            return self.source.owner().to_string()
        if self.integer:
            return self.labels.get(value, str(value))
        return self.types.get(value, (0, str(value)))[1]

    def writable(self):
        try:
            owner = self.source.owner()
            return self.binding.valid() and all(
                not owner.is_property_readonly(name) for name in self.names
            )
        except (ReferenceError, RuntimeError):
            return False

    def entry(self, context):
        before = self.snapshot()
        signature = item_signature(self.source.owner()) if self.keymap_item else None

        def enabled(target, ctx):
            return (
                self.writable()
                and self.snapshot() == before
                and (
                    not self.keymap_item
                    or item_signature(self.source.owner()) == signature
                )
            )

        def capture(target, ctx, event, *, mouse=False, key_modifier="NONE"):
            if event.value != "PRESS" or event.type in MODIFIERS:
                return False
            kind = event.type
            if (
                kind not in self.types
                or kind
                in {
                    "NONE",
                    "ESC",
                    "RIGHTMOUSE",
                    "TEXTINPUT",
                    "WINDOW_DEACTIVATE",
                    "MOUSEMOVE",
                    "INBETWEEN_MOUSEMOVE",
                    "NDOF_MOTION",
                }
                or kind.startswith(("TIMER", "TRACKPAD"))
            ):
                return False
            device = "MOUSE" in kind or kind.startswith(("NDOF_BUTTON", "WHEEL"))
            if device != mouse:
                return False
            if not target.valid() or not enabled(target, ctx):
                raise ReferenceError("Event owner or chord changed; reopen the field")
            owner = self.source.owner()
            meta = owner.bl_rna.properties[self.source.name]
            value = self.types[kind][0] if self.integer else kind
            if self.integer and not meta.hard_min <= value <= meta.hard_max:
                raise ValueError("Event code is outside the property limits")
            if not self.integer and kind not in meta.enum_items:
                raise ValueError("This event is not accepted by the property")
            desired = {}
            if self.keymap_item:
                desired["map_type"] = (
                    "NDOF"
                    if kind.startswith("NDOF_BUTTON")
                    else "MOUSE"
                    if device
                    else "KEYBOARD"
                )
            desired[self.source.name] = value
            if self.keymap_item:
                desired.update(
                    {
                        name: before[name]
                        for name in self.names
                        if name not in {"map_type", "type"}
                    }
                )
            if self.full:
                # `any` and `type` setters reset dependent RNA fields. Apply them
                # before the explicit modifier values and restore activation policy.
                desired["any"] = False
                desired.update(
                    {
                        name: bool(getattr(event, name, False))
                        for name in ("shift", "ctrl", "alt", "oskey", "hyper")
                        if name in self.names
                    }
                )
                desired["key_modifier"] = key_modifier
                self.check_conflicts(owner, ctx, kind, desired)
            try:
                for name, new_value in desired.items():
                    setattr(owner, name, new_value)
                after = self.snapshot()
                if after != before:
                    self.binding.commit(
                        before if self.full else before[self.source.name],
                        after if self.full else after[self.source.name],
                    )
            except Exception:
                if self.binding.valid():
                    # type can change map_type; restore in its original RNA order.
                    for name, old in before.items():
                        setattr(self.source.owner(), name, old)
                raise
            return True

        return capture_entry(capture, enabled, "Capture Event", allow_chord=self.full)

    @staticmethod
    def check_conflicts(owner, context, kind, desired):
        wm = getattr(context, "window_manager", None)
        if wm is None:
            raise ValueError("Full event capture requires its window context")
        keymap = next(
            (
                km
                for kc in wm.keyconfigs
                for km in kc.keymaps
                if any(
                    item.as_pointer() == owner.as_pointer() for item in km.keymap_items
                )
            ),
            None,
        )
        if keymap is None:
            raise ReferenceError("Keymap item is no longer registered")
        for km in conflict_maps(context, keymap):
            for item in km.keymap_items:
                if (
                    item.as_pointer() == owner.as_pointer()
                    or not item.active
                    or item.type != kind
                ):
                    continue
                if item.value not in {owner.value, "ANY"} and owner.value != "ANY":
                    continue
                modifier = desired["key_modifier"]
                if item.key_modifier not in {"NONE", modifier} and modifier != "NONE":
                    continue
                if item.any or all(
                    getattr(item, name) == -1 or bool(getattr(item, name)) == value
                    for name, value in desired.items()
                    if name in {"shift", "ctrl", "alt", "oskey", "hyper"}
                ):
                    raise ValueError("Key already used here; choose another")
