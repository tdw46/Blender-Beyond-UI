"""Owner-checked RNA pointer selection. Candidate/poll policy belongs to the host."""

from dataclasses import dataclass, replace
from contextlib import nullcontext
from .context_menu import Entry


@dataclass(frozen=True)
class PointerItems:
    """Authoritative candidate collection and acceptance callback (owner, candidate)."""

    items: object
    poll: object = lambda owner, candidate: True
    allow_none: bool = True
    revision: object = None  # Callable returning an immutable host generation token.
    transaction: object = None  # (owner, before, after) -> rollback context manager.


def automatic(source):
    """Only policies recoverable from public metadata or explicitly supported RNA."""
    import bpy

    owner = source.owner()
    meta = owner.bl_rna.properties[source.name]
    policy = None
    if isinstance(owner, bpy.types.Scene) and source.name == "camera":
        policy = PointerItems(lambda: bpy.data.objects, lambda o, c: c.type == "CAMERA")
    elif isinstance(owner, bpy.types.Object) and source.name == "parent":

        def parent_ok(o, candidate):
            seen = set()
            while candidate is not None:
                key = candidate.as_pointer()
                if candidate == o or key in seen:
                    return False
                seen.add(key)
                candidate = candidate.parent
            return True

        policy = PointerItems(lambda: bpy.data.objects, parent_ok)
    else:
        # Registered Python PointerProperty annotations retain their exact poll.
        # Never guess a built-in C/RNA poll from just the target type.
        for cls in type(owner).__mro__:
            definition = cls.__dict__.get("__annotations__", {}).get(source.name)
            keywords = getattr(definition, "keywords", None)
            if (
                keywords is not None
                and keywords.get("type") is not None
                and meta.is_runtime
            ):
                target = keywords["type"]
                collections = [
                    p.identifier
                    for p in bpy.data.bl_rna.properties
                    if p.type == "COLLECTION"
                    and p.fixed_type.identifier == target.bl_rna.identifier
                ]
                if len(collections) == 1 and issubclass(target, bpy.types.ID):
                    name = collections[0]
                    policy = PointerItems(
                        lambda: getattr(bpy.data, name),
                        keywords.get("poll") or (lambda o, c: True),
                    )
                break
    if policy is None:
        raise ValueError(
            "Pointer requires an explicit PointerItems policy for its native poll"
        )
    return policy


class PointerField:
    def __init__(self, binding, policy=None):
        self.binding, self.source = binding, binding.context
        meta = self.source.owner().bl_rna.properties[self.source.name]
        if meta.type != "POINTER":
            raise ValueError("Expected a pointer property")
        import bpy

        self.type = getattr(bpy.types, meta.fixed_type.identifier, None)
        if self.type is None:
            raise ValueError("Pointer target RNA type is unavailable")
        self.stable_ids = issubclass(self.type, bpy.types.ID)
        name = getattr(meta.fixed_type, "name_property", None)
        self.name = name.identifier if name is not None else "name"
        if self.name not in meta.fixed_type.properties:
            raise ValueError("Pointer target requires an RNA name property")
        if not self.stable_ids and (
            policy is None
            or not callable(policy.revision)
            or not callable(policy.transaction)
        ):
            raise ValueError(
                "Non-ID pointers require PointerItems with host revision and transaction callbacks"
            )
        self.policy = policy or automatic(self.source)
        self.allow_none = self.policy.allow_none and not meta.is_never_none

    def label(self):
        try:
            value = getattr(self.source.owner(), self.source.name)
            return self.item_label(value)
        except (ReferenceError, RuntimeError):
            return "Unavailable"

    def item_label(self, value):
        return getattr(value, self.name) if value is not None else "None"

    def revision(self):
        return self.policy.revision() if self.policy.revision is not None else None

    def signature(self, values):
        """Only on opening/actions; never enumerate candidates during painting."""
        return tuple(
            (
                self.identity(v),
                v.id_data.as_pointer() if v.id_data is not None else None,
                v.bl_rna.identifier,
                self.item_label(v),
            )
            for v in values
        )

    @staticmethod
    def identity(value):
        return value.as_pointer() if value is not None else 0

    def assign(self, before, chosen):
        if (
            not self.binding.valid()
            or not self.source.editable()
            or self.identity(self.binding.read()) != self.identity(before)
        ):
            raise ReferenceError("Pointer owner or value changed")
        if chosen is None and not self.allow_none:
            raise ValueError("This pointer cannot be cleared")
        if chosen is not None and (
            not isinstance(chosen, self.type)
            or not self.policy.poll(self.source.owner(), chosen)
        ):
            raise ValueError("Pointer candidate is no longer eligible")
        if self.identity(before) == self.identity(chosen):
            return
        transaction = (
            self.policy.transaction(self.source.owner(), before, chosen)
            if self.policy.transaction is not None
            else nullcontext()
        )
        # Restore the bound pointer before the host restores related setter state.
        with transaction:
            try:
                self.binding.write(chosen)
                if self.identity(self.binding.read()) != self.identity(chosen):
                    raise ValueError("The property rejected this pointer")
                self.binding.commit(before, chosen)
            except Exception:
                if self.binding.valid():
                    self.binding.write(before)
                raise

    def clear_entry(self):
        before = self.binding.read()
        identity = self.identity(before)
        revision = self.revision()

        def clear(t, c):
            if self.revision() != revision:
                raise ReferenceError("Pointer collection revision changed")
            self.assign(before, None)

        return Entry(
            "CLEAR_POINTER",
            "Clear",
            clear,
            lambda t, c: t.editable()
            and self.allow_none
            and before is not None
            and self.binding.valid()
            and self.source.editable()
            and self.identity(self.binding.read()) == identity
            and self.revision() == revision,
            icon="unlink",
        )

    def picker(self, canvas, control):
        from .widgets.picker import DataPicker

        before = self.binding.read()
        before_id = self.identity(before)
        revision = self.revision()
        collection = tuple(self.policy.items())
        signature = None if self.stable_ids else self.signature(collection)
        values = {
            self.identity(v): v
            for v in collection
            if isinstance(v, self.type) and self.policy.poll(self.source.owner(), v)
        }
        if self.allow_none:
            values = {0: None, **values}

        def current():
            return (
                self.binding.valid()
                and self.source.editable()
                and canvas.controls.get(control.key) is control
                and control.enabled
                and self.identity(self.binding.read()) == before_id
                and self.revision() == revision
            )

        def valid(key):
            try:
                return current() and key in values and self.identity(values[key]) == key
            except (ReferenceError, RuntimeError):
                return False

        def candidate(key):
            if not valid(key):
                raise ReferenceError(
                    "Pointer owner or candidate changed; reopen the picker"
                )
            collection = tuple(self.policy.items())
            if signature is not None and self.signature(collection) != signature:
                raise ReferenceError("Pointer collection changed; reopen the picker")
            chosen = values[key]
            if chosen is not None and (
                not any(self.identity(v) == key for v in collection)
                or not self.policy.poll(self.source.owner(), chosen)
            ):
                raise ReferenceError("Pointer candidate is no longer eligible")
            return chosen

        def attempt(action):
            try:
                action()
                return True
            except (ReferenceError, RuntimeError, ValueError, TypeError) as error:
                canvas.menu_error = str(error)
                return False

        def select(key):
            def apply():
                chosen = candidate(key)
                self.assign(before, chosen)
                canvas.cancel()

            return attempt(apply)

        def copy_name(key, context):
            return attempt(
                lambda: setattr(
                    context.window_manager, "clipboard", self.item_label(candidate(key))
                )
            )

        widget = DataPicker(
            ((key, self.item_label(v), "object") for key, v in values.items()),
            select,
            selected=lambda: before_id,
            valid=valid,
            unlink=(lambda: select(0)) if self.allow_none else None,
        )
        widget.title = control.label
        widget.disabled_actions = True
        widget.binding = self.binding
        widget.focus()
        widget.type_to_search = True

        # Rows act on the hovered candidate; property actions retain the owner.
        def target(hit):
            if hit.part[0] == "row":
                key = hit.part[1]

                def rows(t, c):
                    return (
                        Entry(
                            "SELECT_POINTER",
                            "Select",
                            lambda t, c: select(key),
                            lambda t, c: valid(key),
                        ),
                        Entry(
                            "COPY_NAME",
                            "Copy Name",
                            lambda t, c: copy_name(key, c),
                            lambda t, c: valid(key),
                        ),
                    )

                return replace(hit, payload=rows)
            return hit

        widget.context_target = target
        return widget
