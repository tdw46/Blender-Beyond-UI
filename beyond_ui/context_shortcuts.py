"""Custom glass key capture backed by real Blender user keymaps.

No persistent timer/operator registration or native shortcut dialog. A consumer
can supply an exact public keymap name; otherwise the admitted Blender helper
chooses the same keymap as a native operator button. Unsupported cases stay off.
"""

from copy import deepcopy
from .context_menu import Entry

MODIFIERS = {
    "LEFT_SHIFT",
    "RIGHT_SHIFT",
    "LEFT_CTRL",
    "RIGHT_CTRL",
    "LEFT_ALT",
    "RIGHT_ALT",
    "OSKEY",
    "HYPER",
}


def frozen(value):
    if isinstance(value, set):
        return tuple(sorted(value))
    if isinstance(value, (str, bool, int, float, type(None))):
        return value
    if isinstance(value, (tuple, list)) or type(value).__name__ == "bpy_prop_array":
        return tuple(frozen(v) for v in value)
    raise TypeError("Shortcut arguments must be scalar values, arrays or enum sets")


def portable(properties):
    try:
        for value in properties.values():
            frozen(value)
        return True
    except TypeError:
        return False


def properties_match(item, properties):
    try:
        actual = {
            p.identifier: frozen(getattr(item.properties, p.identifier))
            for p in item.properties.bl_rna.properties
            if p.identifier != "rna_type"
            and item.properties.is_property_set(p.identifier)
        }
        return actual == {k: frozen(v) for k, v in properties.items()}
    except TypeError:
        return False


def item_signature(item):
    return (
        item.as_pointer(),
        item.idname,
        item.type,
        item.value,
        item.active,
        item.any,
        item.shift,
        item.ctrl,
        item.alt,
        item.oskey,
        getattr(item, "hyper", 0),
        item.key_modifier,
        item.repeat,
    )


class Action:
    def __init__(
        self, idname, properties, context, *, valid=lambda c: True, keymap=None
    ):
        from .hosts import menu_native

        from .context_extensions import operator

        self.idname, self.properties = (
            idname,
            deepcopy(properties) if portable(properties) else {},
        )
        self.operator_pointer = operator(idname).get_rna_type().as_pointer()
        self.portable = portable(properties)
        self.valid = valid
        config = context.window_manager.keyconfigs.user
        km = (
            config.keymaps.get(keymap)
            if keymap and config
            else menu_native.keymap(context, idname)
        )
        self.name = km.name if km else None
        self.space_type = km.space_type if km else None
        self.region_type = km.region_type if km else None
        self.pointer = km.as_pointer() if km else None
        self.existing = None
        self.signature = None
        if km:
            found = next(
                (
                    item
                    for item in km.keymap_items
                    if item.active
                    and item.idname == idname
                    and properties_match(item, self.properties)
                ),
                None,
            )
            if found:
                self.existing, self.signature = found.id, item_signature(found)

    def keymap(self, context):
        from .context_extensions import operator

        if self.name is None or not self.portable or not self.valid(context):
            return None
        try:
            if (
                operator(self.idname).get_rna_type().as_pointer()
                != self.operator_pointer
            ):
                return None
        except (RuntimeError, AttributeError):
            return None
        config = context.window_manager.keyconfigs.user
        if config is None:
            return None
        km = config.keymaps.find(
            self.name, space_type=self.space_type, region_type=self.region_type
        )
        return km if km and km.as_pointer() == self.pointer else None

    def current(self, context):
        km = self.keymap(context)
        if km is None:
            raise ReferenceError("Shortcut context changed")
        item = (
            km.keymap_items.from_id(self.existing)
            if self.existing is not None
            else None
        )
        if self.existing is not None and (
            item is None
            or item_signature(item) != self.signature
            or not properties_match(item, self.properties)
        ):
            raise ReferenceError("Shortcut changed; reopen the menu")
        return km, item

    def enabled(self, target, context):
        try:
            self.current(context)
            return True
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def capture(self, target, context, event):
        import bpy

        if event.value != "PRESS" or event.type in MODIFIERS:
            return False
        types = bpy.types.KeyMapItem.bl_rna.properties["type"].enum_items
        if event.type not in types or event.type in {
            "NONE",
            "TEXTINPUT",
            "WINDOW_DEACTIVATE",
        }:
            return False
        # Only keyboard events are assigned; navigation/mouse still dismisses safely.
        if "MOUSE" in event.type or event.type.startswith(
            ("TIMER", "TRACKPAD", "NDOF")
        ):
            return False
        km, old = self.current(context)
        modifiers = {
            k: bool(getattr(event, k, False)) for k in ("shift", "ctrl", "alt", "oskey")
        }
        if "hyper" in bpy.types.KeyMapItem.bl_rna.properties:
            modifiers["hyper"] = bool(getattr(event, "hyper", False))
        for item in km.keymap_items:
            if (
                item == old
                or not item.active
                or item.type != event.type
                or item.value not in {"PRESS", "ANY"}
            ):
                continue
            if item.key_modifier != "NONE":
                continue
            if item.any or all(
                getattr(item, k) == -1 or bool(getattr(item, k)) == v
                for k, v in modifiers.items()
            ):
                raise ValueError("Key already used here; choose another")
        if old is None:
            if any(
                i.active
                and i.idname == self.idname
                and properties_match(i, self.properties)
                for i in km.keymap_items
            ):
                raise ReferenceError("Shortcut was added; reopen the menu")
            item = km.keymap_items.new(self.idname, event.type, "PRESS", **modifiers)
            try:
                for key, value in self.properties.items():
                    setattr(item.properties, key, value)
                if not properties_match(item, self.properties):
                    raise RuntimeError("Shortcut properties were not retained")
            except Exception:
                km.keymap_items.remove(item)
                raise
        else:
            before = {
                k: getattr(old, k)
                for k in ("type", "value", "any", "key_modifier", *modifiers)
            }
            try:
                old.type, old.value, old.any, old.key_modifier = (
                    event.type,
                    "PRESS",
                    False,
                    "NONE",
                )
                for key, value in modifiers.items():
                    setattr(old, key, value)
            except Exception:
                for key, value in before.items():
                    setattr(old, key, value)
                raise
        context.preferences.is_dirty = True
        return True

    def remove(self, target, context):
        km, item = self.current(context)
        if item is None:
            raise ReferenceError("Shortcut no longer exists")
        km.keymap_items.remove(item)
        context.preferences.is_dirty = True

    def entry(self, context):
        reason = "Requires an applicable keymap and a context-independent operator or boolean property."
        if self.existing is None:
            return Entry(
                "SHORTCUT",
                "Assign Shortcut",
                enabled=self.enabled,
                capture=self.capture,
                icon="shortcut",
                tip=reason,
            )
        _, item = self.current(context)
        chord = item.to_string()
        return Entry(
            "SHORTCUT",
            "Shortcut: " + chord,
            enabled=self.enabled,
            icon="shortcut",
            children=lambda t, c: (
                Entry(
                    "CHANGE_SHORTCUT",
                    "Change Shortcut",
                    enabled=self.enabled,
                    capture=self.capture,
                ),
                Entry("REMOVE_SHORTCUT", "Remove Shortcut", self.remove, self.enabled),
            ),
        )


def property_entry(source, context):
    from .context_paths import property_path

    path = property_path(source, context)
    meta = source.owner().bl_rna.properties[source.name]
    if (
        path is None
        or meta.type != "BOOLEAN"
        or (meta.is_array and source.index is None)
    ):
        return Entry(
            "SHORTCUT",
            "Assign Shortcut",
            enabled=False,
            icon="shortcut",
            tip="This property has no direct custom shortcut action. Enum popup shortcuts require host dispatch.",
        )
    action = Action(
        "wm.context_toggle",
        {"data_path": path},
        context,
        valid=lambda c: source.valid()
        and source.editable()
        and property_path(source, c) == path,
    )
    return action.entry(context)
