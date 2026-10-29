"""Retained enum labels and transactional choices; callbacks never run in paint."""

from copy import deepcopy
from dataclasses import dataclass
from itertools import islice

_UNSET = object()
LIMIT = 4096  # Same admission bound as the existing dynamic-RNA adapter.


@dataclass(frozen=True)
class Item:
    identifier: object
    name: str
    description: str = ""
    value: object = None


class EnumField:
    def __init__(self, binding, items, *, flag=False, translate=lambda text: text):
        self.binding, self.items = binding, items
        self.flag, self.translate = flag, translate
        self.labels = {}

    def snapshot(self):
        rows = tuple(islice(self.items(), LIMIT + 1))
        if len(rows) > LIMIT:
            raise ValueError("Enum exceeds the bounded 4096-item limit")
        result = tuple(
            Item(
                i.identifier,
                self.translate(i.name or str(i.identifier)),
                self.translate(getattr(i, "description", "")),
                getattr(i, "value", None),
            )
            for i in rows
        )
        choices = tuple(i for i in result if i.identifier != "")
        if len({i.identifier for i in choices}) != len(choices):
            raise ValueError("Enum identifiers must be unique")
        self.labels = {i.identifier: i.name for i in choices}
        return result

    def format(self, value):
        if self.flag:
            return (
                ", ".join(self.labels.get(key, key) for key in sorted(value)) or "None"
            )
        return self.labels.get(value, str(value))

    def selected(self, identifier, value=None):
        value = self.binding.read() if value is None else value
        return identifier in value if self.flag else identifier == value

    def choose(self, item, *, original=_UNSET, exclusive=False):
        if item.identifier == "":
            raise ValueError("Enum headings and separators cannot be selected")
        before = deepcopy(self.binding.read())
        if original is not _UNSET and before != original:
            raise ReferenceError("Enum value changed; reopen the menu")
        current = next(
            (i for i in self.snapshot() if i.identifier == item.identifier), None
        )
        if current is None or current.value != item.value:
            raise ReferenceError("Enum choice changed; reopen the menu")
        # Dynamic callbacks are host code: reject a value change during evaluation.
        if self.binding.read() != before:
            raise ReferenceError("Enum value changed while resolving choices")
        after = (
            ({item.identifier} if exclusive else set(before) ^ {item.identifier})
            if self.flag
            else item.identifier
        )
        if before == after:
            return
        try:
            self.binding.write(after)
            if self.binding.read() != after:
                raise ValueError("Enum setter rejected the selected value")
            self.binding.commit(before, deepcopy(after))
        except Exception:
            if self.binding.valid():
                self.binding.write(before)
            raise
