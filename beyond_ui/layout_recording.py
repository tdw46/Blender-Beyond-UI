"""Bounded native-style authoring tape; unchanged draws keep retained controls."""

from .layout import Layout, UnsupportedControl


def freeze(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "as_pointer"):
        return ("RNA", value.as_pointer())
    if isinstance(value, dict):
        return tuple((k, freeze(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(v) for v in value)
    return (type(value).__name__, id(value))


def list_arguments(args, kwargs):
    names = ("dataptr", "propname", "active_dataptr", "active_propname")
    return tuple(
        args[i + 2] if len(args) > i + 2 else kwargs.get(name)
        for i, name in enumerate(names)
    )


class Tape:
    def __init__(self, state=None):
        self.commands, self.signature = [], []
        self.display_targets = {}
        self.extra_signature = []
        self.state = state if state is not None else {}
        self.next_id = 1
        self.root = Node(self, 0)

    def record(self, command):
        if len(self.commands) >= 4096:
            raise ValueError("UI draw exceeds 4096 recorded commands")
        self.commands.append(command)
        self.signature.append(freeze(command))
        kind, _, name, args, kwargs, _ = command
        if kind == "call" and name == "template_list":
            from .list_identity import KEY

            data, prop, active_data, active_prop = list_arguments(args, kwargs)
            if data is not None and prop is not None:
                values = getattr(data, prop)
                active = (
                    getattr(active_data, active_prop)
                    if active_data is not None and active_prop is not None
                    else -1
                )
                token = ""
                if 0 <= active < len(values):
                    try:
                        token = values[active].get(KEY, "")
                    except (TypeError, AttributeError):
                        pass
                self.signature.append((len(values), active, token))
                self.extra_signature.append((len(values), active, token))

    def node(self, parent=None):
        result = Node(self, self.next_id, parent)
        self.next_id += 1
        return result

    def initialize_lists(self, provider):
        """Invoke/open paths only, after recording; never call from native draw."""
        if provider is None or not hasattr(provider, "prepare"):
            return
        from .list_identity import PendingListIdentity

        for kind, _, name, args, kwargs, _ in self.commands:
            if kind != "call" or name != "template_list":
                continue
            data, prop, _, _ = list_arguments(args, kwargs)
            if data is None or prop is None:
                continue
            meta = data.bl_rna.properties.get(prop)
            current = getattr(meta, "fixed_type", None)
            while current is not None and current.identifier != "PropertyGroup":
                current = current.base
            if current is None:
                continue
            try:
                provider.prepare(data, prop)
            except PendingListIdentity:
                provider.flush()
                provider.prepare(data, prop)

    def play(self, layout):
        values = {0: layout}
        for index, (kind, target, name, args, kwargs, outputs) in enumerate(self.commands):
            if kind == "set":
                setattr(values[target], name, args[0])
            else:
                result = getattr(values[target], name)(*args, **kwargs)
                if name in {"label", "title"} and result is not None:
                    self.display_targets[index] = (result, values[target])
                if isinstance(outputs, tuple):
                    for key, value in zip(outputs, result):
                        if key is not None:
                            values[key] = value
                elif outputs is not None:
                    values[outputs] = result

    def patch_display(self, newer):
        """Update literal label text without replacing controls or edit state.

        Called on the owner's native authoring redraw, never by GPU painting or
        an idle timer. Structural changes are explicitly rejected for rebuilding.
        """
        if (len(self.commands) != len(newer.commands)
                or self.extra_signature != newer.extra_signature):
            return False
        changes = []
        for index, (old, new) in enumerate(zip(self.commands, newer.commands)):
            if freeze(old) == freeze(new):
                continue
            if index not in self.display_targets:
                return False
            old_kw, new_kw = dict(old[4]), dict(new[4])
            old_kw.pop("text", None)
            new_kw.pop("text", None)
            if freeze((*old[:4], old_kw, old[5])) != freeze((*new[:4], new_kw, new[5])):
                return False
            changes.append((index, new[4]))
        for index, kwargs in changes:
            control, layout = self.display_targets[index]
            control.label = layout._text(kwargs.get("text", ""), kwargs.get("text_ctxt", ""), kwargs.get("translate", True))
            layout.canvas.invalidate()
        self.commands, self.signature = newer.commands, newer.signature
        return True


class Node:
    groups = {"row", "column", "box", "split", "grid_flow", "column_flow", "menu_pie"}
    operators = {"operator", "operator_menu_hold", "operator_menu_enum"}
    defaults = dict(
        enabled=True,
        active=True,
        alert=False,
        alignment="EXPAND",
        scale_x=1.0,
        scale_y=1.0,
        ui_units_x=0.0,
        ui_units_y=0.0,
        use_property_split=False,
        use_property_decorate=True,
        emboss="NORMAL",
        operator_context="INVOKE_DEFAULT",
        activate_init=False,
        active_default=False,
        direction="VERTICAL",
        is_popover=False,
        is_custom=True,
    )

    def __init__(self, tape, key, parent=None):
        object.__setattr__(self, "_tape", tape)
        object.__setattr__(self, "_key", key)
        object.__setattr__(
            self, "_values", dict(parent._values if parent else self.defaults)
        )

    def __setattr__(self, name, value):
        if name.startswith("_"):
            raise AttributeError("Private layout state is not portable")
        self._values[name] = value
        self._tape.record(("set", self._key, name, (value,), {}, None))

    def __getattr__(self, name):
        if name in self._values:
            return self._values[name]
        if name in {"enum_item_name", "enum_item_description", "enum_item_icon"}:
            return getattr(Layout, name)
        if not callable(getattr(Layout, name, None)):
            raise UnsupportedControl(name)

        def call(*args, **kwargs):
            tape = self._tape
            if name in {"panel", "panel_prop"}:
                opened = (
                    tape.state.get(args[0], not kwargs.get("default_closed", False))
                    if name == "panel"
                    else bool(getattr(args[0], args[1]))
                )
                header = tape.node(self)
                body = tape.node(self) if opened else None
                outputs = (header._key, body._key if body else None)
                tape.record(("call", self._key, name, args, kwargs, outputs))
                return header, body
            result = tape.node(self) if name in self.groups | self.operators else None
            tape.record(
                ("call", self._key, name, args, kwargs, result._key if result else None)
            )
            return result

        return call
