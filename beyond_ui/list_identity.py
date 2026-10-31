"""Persistent row identities, assigned in finite deferred work, never during draw."""

from collections import Counter
from uuid import uuid4
from .list_source import UnsafeListIdentity

KEY = "_beyond_ui_row_id"


class PendingListIdentity(UnsafeListIdentity):
    pass


class StableListIDs:
    limit = 128

    def __init__(self, owner, changed):
        self.owner, self.changed = owner, changed
        self.pending = {}
        self.errors = {}
        self.active = True
        self.callback = self.flush

    def owned(self, value):
        module = type(value).__module__
        return module == self.owner or module.startswith(self.owner + ".")

    def prepare(self, owner, prop):
        values = getattr(owner, prop)
        if not values:
            return
        if not all(self.owned(row) for row in values):
            raise UnsafeListIdentity(
                "Automatic row IDs require consumer-owned PropertyGroups"
            )
        keys = [row.get(KEY, "") for row in values]
        if all(isinstance(k, str) and k for k in keys) and len(set(keys)) == len(keys):
            return
        key = (owner.as_pointer(), prop)
        if key in self.errors:
            raise UnsafeListIdentity(self.errors[key])
        if key not in self.pending:
            if len(self.pending) >= self.limit:
                raise UnsafeListIdentity(
                    "Too many pending collection identity migrations"
                )
            from .rna_owner import guarded

            self.pending[key] = (guarded(lambda: owner), prop)
        import bpy

        if self.active and not bpy.app.timers.is_registered(self.callback):
            bpy.app.timers.register(self.callback, first_interval=0.0)
        raise PendingListIdentity(
            "Initializing persistent collection row IDs outside draw"
        )

    def __call__(self, owner, prop, row):
        key = row.get(KEY, "")
        if not isinstance(key, str) or not key:
            self.prepare(owner, prop)
            raise UnsafeListIdentity("Collection row identity is unavailable")
        return key

    def flush(self):
        if not self.active:
            return None
        pending, self.pending = self.pending, {}
        for key, (resolve, prop) in pending.items():
            writes = []
            try:
                owner = resolve()
                data = getattr(owner, "id_data", None)
                if data is not None and not getattr(
                    data, "is_editable", not data.library
                ):
                    raise PermissionError(
                        "Read-only collection requires a host identity resolver"
                    )
                values = list(getattr(owner, prop))
                keys = [row.get(KEY, "") for row in values]
                counts = Counter(k for k in keys if isinstance(k, str))
                for row, token in zip(values, keys):
                    if not isinstance(token, str) or not token or counts[token] > 1:
                        if not self.owned(row):
                            raise PermissionError("Collection row owner changed")
                        writes.append((row, KEY in row, token))
                        row[KEY] = uuid4().hex
            except Exception as error:
                for row, existed, old in reversed(writes):
                    try:
                        if existed:
                            row[KEY] = old
                        elif KEY in row:
                            del row[KEY]
                    except (ReferenceError, RuntimeError):
                        pass
                if len(self.errors) >= self.limit:
                    self.errors.pop(next(iter(self.errors)))
                self.errors[key] = str(error)
        if pending:
            self.changed()
        return None

    def close(self):
        self.active = False
        import bpy

        if bpy.app.timers.is_registered(self.callback):
            bpy.app.timers.unregister(self.callback)
        self.pending.clear()
        self.errors.clear()
