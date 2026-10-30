"""Host-owned identity and edit transactions. Never write from paint/layout."""

from dataclasses import dataclass
from copy import deepcopy
from .rna_owner import identity, readonly, guarded


@dataclass
class Binding:
    get: object
    set: object
    valid: object = lambda: True
    commit: object = lambda before, after: None
    context: object = None
    context_target: object = None
    snapshot: object = None

    def frozen(self):
        """Capture dynamic selection ownership once before edits or menus."""
        return self.snapshot() if self.snapshot is not None else self

    def read(self):
        if not self.valid():
            raise ReferenceError("The control owner is no longer valid")
        return self.get()

    def write(self, value):
        if not self.valid():
            raise ReferenceError("The control owner is no longer valid")
        self.set(value)


class Edit:
    def __init__(self, binding):
        self.binding = binding.frozen()
        self.before = deepcopy(self.binding.read())
        self.closed = False

    def update(self, value):
        if self.closed:
            raise RuntimeError("Edit is already closed")
        self.binding.write(value)

    def finish(self, cancel=False):
        if self.closed:
            return
        self.closed = True
        if not self.binding.valid():
            return  # Owner disappeared; never redirect a deferred edit.
        if cancel:
            self.binding.write(self.before)
        else:
            after = deepcopy(self.binding.read())
            if self.before != after:
                try:
                    self.binding.commit(self.before, after)
                except Exception:
                    if self.binding.valid():
                        self.binding.write(self.before)
                    raise


def rna_binding(
    resolve,
    property_name,
    *,
    index=None,
    commit=lambda before, after: None,
    source=None,
):
    """resolve() must reacquire a stable owner, never search by mutable name/index.

    The initial RNA pointer is checked on every access. Undo/load invalidates the
    binding; rebuild it after those events. Host owns undo and invalidation.
    """
    resolve = guarded(resolve)
    owner = resolve()
    if owner is None:
        raise ReferenceError("RNA owner is unavailable")
    pointer = identity(owner)

    def current():
        obj = resolve()
        if obj is None or identity(obj) != pointer:
            raise ReferenceError("RNA owner changed")
        return obj

    def valid():
        try:
            obj = current()
            return property_name in obj.bl_rna.properties and not readonly(
                obj, property_name
            )
        except (ReferenceError, AttributeError, RuntimeError):
            return False

    def get():
        value = getattr(current(), property_name)
        if index is not None:
            return value[index]
        # RNA arrays cannot be retained or deep-copied safely across undo.
        return (
            tuple(value)
            if getattr(current().bl_rna.properties[property_name], "is_array", False)
            else value
        )

    def set_value(value):
        obj = current()
        if index is None:
            setattr(obj, property_name, value)
        else:
            getattr(obj, property_name)[index] = value

    from .context_rna import Property

    return Binding(
        get,
        set_value,
        valid,
        commit,
        Property(resolve, property_name, index, commit, source=source),
    )
