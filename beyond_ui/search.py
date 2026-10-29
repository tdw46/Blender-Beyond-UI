"""Transactional collection search; snapshot on refresh, revalidate on commit."""

from dataclasses import replace
from .context_menu import Entry, default_entries
from .pointer import PointerField, automatic
from .widgets.picker import DataPicker


class CollectionSearch:
    def __init__(
        self,
        binding,
        resolve,
        name,
        *,
        policy=None,
        label="",
        item_name="",
        suggestions=False,
        eager=True,
    ):
        self.binding, self.source = binding, binding.context
        self.resolve, self.name = resolve, name
        owner = resolve()
        self.identity = owner.as_pointer()
        meta = owner.bl_rna.properties[name]
        if meta.type != "COLLECTION":
            raise ValueError("Search source must be an RNA collection")
        target = self.source.owner().bl_rna.properties[self.source.name]
        if target.type not in {"STRING", "POINTER"}:
            raise ValueError(
                "Collection search requires a string or ID pointer property"
            )
        self.pointer = None
        if target.type == "POINTER":
            policy = policy or automatic(self.source)
            self.pointer = PointerField(binding, policy)
        if suggestions and self.pointer:
            raise ValueError("Arbitrary search suggestions require a string property")
        item_type = meta.fixed_type
        while item_type is not None and item_type.identifier != "ID":
            item_type = item_type.base
        is_id = item_type is not None
        self.stable_ids = is_id
        self.item_name = "name" if is_id else item_name or "name"
        prop = meta.fixed_type.properties.get(self.item_name)
        if prop is None or prop.type != "STRING":
            raise ValueError("Search item property must be an RNA string")
        self.widget = DataPicker(
            (), self.select, selected=self.selected, valid=self.valid
        )
        self.widget.title = label or target.name
        self.widget.disabled_actions = True
        self.widget.binding = binding
        self.widget.context_target = self.context_target
        self.widget.refresh = self.refresh
        self.widget.accept_text = self.accept_text if suggestions else None
        self.canvas = self.control = None
        self.values, self.keys_by_name = {}, {}
        if eager:
            self.refresh()

    def label(self):
        try:
            value = self.binding.get()
            return (
                (value.name if value is not None else "None") if self.pointer else value
            )
        except (ReferenceError, RuntimeError):
            return "Unavailable"

    def open(self):
        self.refresh()
        self.widget.query = ""
        self.widget._filter()
        self.widget.focus()
        self.widget.type_to_search = True
        return self.widget

    def collection(self):
        owner = self.resolve()
        if owner is None or owner.as_pointer() != self.identity:
            raise ReferenceError("Search collection owner changed")
        return getattr(owner, self.name)

    def value_identity(self, value):
        return PointerField.identity(value) if self.pointer else value

    def refresh(self):
        """Host calls after collection edits/undo; never called by paint."""
        self.widget.cancel()
        if self.canvas is not None:
            if self.canvas.overlay and self.canvas.overlay.get("owner") is self.control:
                self.canvas.cancel()
            if self.canvas.widget_capture is self.control:
                self.canvas.widget_capture = None
            if self.canvas.keyboard_focus is self.control:
                self.canvas.blur_focus()
            menu = self.canvas.context_menu
            if menu is not None and menu.target.key == self.control.key:
                self.canvas.close_context()
        self.expected = self.value_identity(self.binding.get())
        values = {}
        rows = []
        keys = {}
        allowed = (
            {v.as_pointer() for v in self.pointer.policy.items()}
            if self.pointer
            else None
        )
        for value in self.collection():
            if self.pointer and (
                value.as_pointer() not in allowed
                or not isinstance(value, self.pointer.type)
                or not self.pointer.policy.poll(self.source.owner(), value)
            ):
                continue
            key, label = value.as_pointer(), getattr(value, self.item_name)
            values[key] = value
            rows.append((key, label, "object"))
            keys[label] = key if label not in keys else None
        self.values, self.keys_by_name = values, keys
        self.snapshot = tuple((key, label) for key, label, icon in rows)
        self.widget.items = tuple(rows)
        self.widget._filter()
        self.widget.motion.clear()

    def current(self):
        if not self.source.valid():
            return False
        self.collection()
        return self.value_identity(self.binding.get()) == self.expected and (
            self.control is None
            or (
                self.canvas.controls.get(self.control.key) is self.control
                and self.canvas.visible
            )
        )

    def valid(self, key):
        try:
            return (
                self.current()
                and key in self.values
                and self.values[key].as_pointer() == key
            )
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def selected(self):
        try:
            value = self.value_identity(self.binding.get())
            return value if self.pointer else self.keys_by_name.get(value)
        except (ReferenceError, RuntimeError):
            return None

    def writable(self):
        return (
            self.current()
            and self.binding.valid()
            and self.source.editable()
            and (self.control is None or self.control.enabled)
        )

    def write(self, value):
        if not self.writable():
            raise ReferenceError("Search owner or property value changed")
        before = self.binding.read()
        if self.pointer:
            self.pointer.assign(before, value)
        elif value != before:
            try:
                self.binding.write(value)
                if self.binding.read() != value:
                    raise ValueError("Property rejected the search value")
                self.binding.commit(before, value)
            except Exception:
                if self.binding.valid():
                    self.binding.write(before)
                raise
        self.expected = self.value_identity(self.binding.get())
        if self.canvas:
            self.canvas.menu_error = None
            if self.canvas.overlay and self.canvas.overlay.get("owner") is self.control:
                self.canvas.cancel()

    def attempt(self, callback):
        try:
            callback()
            return True
        except (ReferenceError, RuntimeError, ValueError, TypeError) as error:
            if self.canvas is None:
                raise
            self.canvas.menu_error = str(error)
            return False

    def candidate(self, key):
        if not self.valid(key):
            raise ReferenceError(
                "Search owner or candidate changed; refresh the search"
            )
        if self.pointer and not any(
            v.as_pointer() == key for v in self.pointer.policy.items()
        ):
            raise ReferenceError("Pointer candidate is outside the host policy")
        # CollectionProperty removal can reuse addresses for shifted elements.
        # Non-ID searches require the complete captured structure to still match.
        if (
            not self.stable_ids
            and tuple(
                (v.as_pointer(), getattr(v, self.item_name)) for v in self.collection()
            )
            != self.snapshot
        ):
            raise ReferenceError("Search collection changed; refresh the search")
        if not any(v.as_pointer() == key for v in self.collection()):
            raise ReferenceError("Search candidate changed; refresh the search")
        return self.values[key]

    def select(self, key):
        def commit():
            item = self.candidate(key)
            value = item if self.pointer else getattr(item, self.item_name)
            self.write(value)

        return self.attempt(commit)

    def copy_name(self, key, context):
        return self.attempt(
            lambda: setattr(
                context.window_manager,
                "clipboard",
                getattr(self.candidate(key), self.item_name),
            )
        )

    def accept_text(self, text):
        return self.attempt(lambda: self.write(text))

    def context_target(self, hit):
        if hit.part[0] != "row":
            return hit
        key = hit.part[1]

        def rows(t, c):
            return (
                Entry(
                    "SELECT_SEARCH",
                    "Select",
                    lambda t, c: self.select(key),
                    lambda t, c: self.valid(key) and self.writable(),
                ),
                Entry(
                    "COPY_NAME",
                    "Copy Name",
                    lambda t, c: self.copy_name(key, c),
                    lambda t, c: self.valid(key),
                ),
            )

        return replace(hit, payload=rows)

    def entries(self, target, context):
        provider = self.canvas.context_provider
        if callable(target.payload):
            return (
                *target.payload(target, context),
                *(provider(target, context) if provider else ()),
            )
        return (provider or default_entries)(target, context)
