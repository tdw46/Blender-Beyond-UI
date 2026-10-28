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


def conflict_maps(context, selected):
    """Only called when committing a chord; never scans keymaps on paint/move."""
    config = context.window_manager.keyconfigs.user
    names = {"Window", "Screen", "User Interface", selected.name}
    area = getattr(context, "area", None)
    if area and area.type == "VIEW_3D":
        names.update(("3D View", "Object Non-modal"))
        mode = getattr(context, "mode", "")
        name = {
            "OBJECT": "Object Mode",
            "EDIT_MESH": "Mesh",
            "POSE": "Pose",
            "SCULPT": "Sculpt",
        }.get(mode)
        if name:
            names.add(name)
    maps = [selected]
    for name in sorted(names):
        km = config.keymaps.get(name)
        if km is not None and km.as_pointer() != selected.as_pointer():
            maps.append(km)
    return maps


class Action:
    def __init__(
        self,
        idname,
        properties,
        context,
        *,
        valid=lambda c: True,
        keymap=None,
        check=None,
        conflict_keymaps=None,
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
        self.check = check
        self.conflict_keymaps = conflict_keymaps
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

    def capture(self, target, context, event, *, mouse=False, key_modifier="NONE"):
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
        # Device bindings require an explicit capture mode; cancellation stays reserved.
        device = "MOUSE" in event.type or event.type.startswith("NDOF_BUTTON")
        if event.type.startswith(("TIMER", "TRACKPAD")) or event.type in {
            "NDOF_MOTION",
            "ESC",
            "RIGHTMOUSE",
        }:
            return False
        if device != mouse:
            return False
        if self.check is not None and not self.check(context):
            raise ReferenceError("Shortcut target changed; reopen the menu")
        km, old = self.current(context)
        modifiers = {
            k: bool(getattr(event, k, False)) for k in ("shift", "ctrl", "alt", "oskey")
        }
        if "hyper" in bpy.types.KeyMapItem.bl_rna.properties:
            modifiers["hyper"] = bool(getattr(event, "hyper", False))
        maps = conflict_maps(context, km)
        if self.conflict_keymaps is not None:
            from itertools import islice

            known = {scope.as_pointer() for scope in maps}
            for scope in islice(self.conflict_keymaps(context, km), 64):
                if scope is not None and scope.as_pointer() not in known:
                    maps.append(scope)
                    known.add(scope.as_pointer())
        for item in (item for scope in maps for item in scope.keymap_items):
            if (
                item == old
                or not item.active
                or item.type != event.type
                or item.value not in {"PRESS", "ANY"}
            ):
                continue
            if key_modifier != "NONE" and item.key_modifier not in {
                "NONE",
                key_modifier,
            }:
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
            item = km.keymap_items.new(
                self.idname, event.type, "PRESS", key_modifier=key_modifier, **modifiers
            )
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
                    key_modifier,
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

    def capture_entry(self, label="Assign Shortcut"):
        return capture_entry(self.capture, self.enabled, label)

    def entry(self, context):
        if self.existing is None:
            return self.capture_entry()
        _, item = self.current(context)
        chord = item.to_string()
        return Entry(
            "SHORTCUT",
            "Shortcut: " + chord,
            enabled=self.enabled,
            icon="shortcut",
            children=lambda t, c: (
                self.capture_entry("Change Shortcut"),
                Entry("REMOVE_SHORTCUT", "Remove Shortcut", self.remove, self.enabled),
            ),
        )


def property_entry(source, context):
    from .context_paths import property_path
    from dataclasses import replace
    from itertools import islice
    from .context_enums import items, contains

    path = property_path(source, context)
    meta = source.owner().bl_rna.properties[source.name]

    def valid(c):
        return source.valid() and source.editable() and property_path(source, c) == path

    if path is None or (getattr(meta, "is_array", False) and source.index is None):
        return Entry(
            "SHORTCUT",
            "Assign Shortcut",
            enabled=False,
            icon="shortcut",
            tip="Requires a scalar/component with an exact context-relative path.",
        )
    if meta.type == "BOOLEAN":
        return Action(
            "wm.context_toggle", {"data_path": path}, context, valid=valid
        ).entry(context)
    if meta.type == "ENUM":

        def value_entry(value, label, c):
            def current(ctx):
                return valid(ctx)

            def check(ctx):
                return contains(source.owner(), source.name, value, ctx)

            if meta.is_enum_flag:
                # Blender's context_set_value supplies its normal property undo.
                # Only a validated RNA path plus a quoted enum identifier enters
                # the expression; no arbitrary host expression is evaluated here.
                import ast

                tree = ast.parse("context." + path, mode="eval")
                allowed = (
                    ast.Expression,
                    ast.Attribute,
                    ast.Name,
                    ast.Load,
                    ast.Subscript,
                    ast.Constant,
                )
                if not all(isinstance(node, allowed) for node in ast.walk(tree)):
                    return Entry("SHORTCUT", label, enabled=False)
                op = "wm.context_set_value"
                props = {
                    "data_path": path,
                    "value": f"(context.{path}) ^ {{{value!r}}}",
                }
            else:
                op, props = "wm.context_set_enum", {"data_path": path, "value": value}
            row = Action(op, props, c, valid=current, check=check).entry(c)
            return replace(row, label=label) if label else row

        if source.enum_value is not None:
            item = next(
                (
                    i
                    for i in items(source.owner(), source.name, context)
                    if i.identifier == source.enum_value
                ),
                None,
            )
            return value_entry(
                source.enum_value,
                None if item else "Unavailable enum item",
                context,
            )

        def choices(t, c):
            current = source.owner().bl_rna.properties[source.name]
            return tuple(
                value_entry(item.identifier, item.name, c)
                for item in islice(
                    (i for i in items(source.owner(), source.name, c) if i.identifier),
                    63,
                )
            )

        return Entry(
            "SHORTCUT",
            "Shortcut to Value",
            children=choices,
            enabled=lambda t, c: valid(c) and t.editable(),
            icon="shortcut",
            tip="Choose the enum value to assign, change or remove a shortcut for.",
        )
    return Entry(
        "SHORTCUT",
        "Assign Shortcut",
        enabled=False,
        icon="shortcut",
        tip="This property has no direct shortcut action; a host dispatcher can provide one.",
    )


def capture_entry(capture, enabled, label="Assign Shortcut", *, allow_chord=True):
    def modes(target, context):
        held = [None]

        def chord(t, c, e):
            if e.type in MODIFIERS:
                return False
            if e.value == "RELEASE" and e.type == held[0]:
                held[0] = None
                return "Hold one key, then press another…"
            if (
                e.value != "PRESS"
                or "MOUSE" in e.type
                or e.type.startswith(("NDOF", "TIMER", "TRACKPAD"))
            ):
                return False
            if held[0] is None:
                held[0] = e.type
                return f"Hold {e.type}; press the shortcut key…"
            if e.type == held[0]:
                return False
            return capture(t, c, e, key_modifier=held[0])

        rows = (
            Entry(
                "MOUSE_CAPTURE",
                "Mouse / NDOF button…",
                enabled=enabled,
                capture=lambda t, c, e: capture(t, c, e, mouse=True),
                capture_mouse=True,
                capture_prompt="Click below, or use a device button…",
                tip="Escape or right-click cancels. Click outside the menu inside this panel to bind left mouse.",
            ),
            Entry(
                "CHORD_CAPTURE",
                "Key modifier chord…",
                enabled=enabled,
                capture=chord,
                capture_prompt="Hold one key, then press another…",
            ),
        )

        return rows if allow_chord else rows[:1]

    return Entry(
        "SHORTCUT",
        label,
        enabled=enabled,
        capture=capture,
        capture_options=modes,
        icon="shortcut",
        tip="Assign a key; alternate capture modes are available inside.",
    )
