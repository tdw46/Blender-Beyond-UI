"""Owner-checked ID pointer selection. Candidate/poll policy belongs to the host."""

from dataclasses import dataclass, replace
from .context_menu import Entry


@dataclass(frozen=True)
class PointerItems:
    """Authoritative candidate collection and acceptance callback (owner, candidate)."""

    items: object
    poll: object = lambda owner, candidate: True
    allow_none: bool = True


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
        if self.type is None or not issubclass(self.type, bpy.types.ID):
            raise ValueError(
                "Only ID pointers are supported; non-ID pointers need a separate adapter"
            )
        self.policy = policy or automatic(self.source)
        self.allow_none = self.policy.allow_none and not meta.is_never_none

    def label(self):
        try:
            value = getattr(self.source.owner(), self.source.name)
            return value.name if value is not None else "None"
        except (ReferenceError, RuntimeError):
            return "Unavailable"

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
        return Entry(
            "CLEAR_POINTER",
            "Clear",
            lambda t, c: self.assign(before, None),
            lambda t, c: t.editable()
            and self.allow_none
            and before is not None
            and self.binding.valid()
            and self.source.editable()
            and self.identity(self.binding.read()) == identity,
            icon="unlink",
        )

    def picker(self, canvas, control):
        from .widgets.picker import DataPicker

        before = self.binding.read()
        before_id = self.identity(before)
        collection = self.policy.items()
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
            )

        def valid(key):
            try:
                return current() and key in values and self.identity(values[key]) == key
            except (ReferenceError, RuntimeError):
                return False

        def select(key):
            try:
                if not valid(key):
                    raise ReferenceError(
                        "Pointer owner or candidate changed; reopen the picker"
                    )
                chosen = values[key]
                if chosen is not None and (
                    not any(self.identity(v) == key for v in self.policy.items())
                    or not self.policy.poll(self.source.owner(), chosen)
                ):
                    raise ReferenceError("Pointer candidate is no longer eligible")
                if key == before_id:
                    canvas.cancel()
                    return
                self.assign(before, chosen)
                canvas.cancel()
            except (ReferenceError, RuntimeError, ValueError, TypeError) as error:
                canvas.menu_error = str(error)

        widget = DataPicker(
            (
                (key, v.name if v is not None else "None", "object")
                for key, v in values.items()
            ),
            select,
            selected=lambda: before_id,
            valid=valid,
            unlink=(lambda: select(0)) if self.allow_none else None,
        )
        widget.title = control.label
        widget.disabled_actions = True
        widget.binding = self.binding
        widget.focus()

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
                            lambda t, c: setattr(
                                c.window_manager,
                                "clipboard",
                                values[key].name if key else "None",
                            ),
                            lambda t, c: valid(key),
                        ),
                    )

                return replace(hit, payload=rows)
            return hit

        widget.context_target = target
        return widget
