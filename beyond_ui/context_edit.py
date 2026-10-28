"""Deferred inline menu edits; reuse the shared text buffer, never write on paint."""

from dataclasses import dataclass
from .editing import Text


@dataclass(frozen=True)
class Field:
    read: object
    apply: object  # (text, original, target, context) -> None, transactional
    format: object = lambda value, context: str(value)
    state: object = lambda target, context: None


class Editor:
    def __init__(self, row, index, target, context):
        self.row, self.index = row, index
        self.original = row.field.read(target, context)
        self.state = row.field.state(target, context)
        formatted = row.field.format(self.original, context)
        if len(formatted) > 4096:
            raise ValueError("Field exceeds the inline editing limit")
        self.text = Text(formatted)
        self.error = None
        self.dragging = False

    def pointer(self, event, x, rect, measure):
        """Caret/selection in logical row space, matching the shared field painter."""
        left = rect[0] + rect[2] * 0.45 + 5
        right = rect[0] + rect[2] - 9
        text = self.text
        cursor = measure(text.text[: text.cursor], 11)
        origin = left - max(0, cursor - max(0, right - left - 2))
        offset = max(0, x - origin)
        lo, hi = 0, len(text.text)
        while lo < hi:
            mid = (lo + hi) // 2
            if measure(text.text[:mid], 11) < offset:
                lo = mid + 1
            else:
                hi = mid
        if lo and abs(measure(text.text[: lo - 1], 11) - offset) < abs(
            measure(text.text[:lo], 11) - offset
        ):
            lo -= 1
        if event.value == "DOUBLE_CLICK":
            start = end = min(lo, max(0, len(text.text) - 1))
            while start > 0 and text.text[start - 1].isalnum():
                start -= 1
            while end < len(text.text) and text.text[end].isalnum():
                end += 1
            text.anchor, text.cursor = start, end
        else:
            text.move(lo, event.type == "MOUSEMOVE" or getattr(event, "shift", False))
        self.dragging = event.value in {"PRESS", "DOUBLE_CLICK"} or self.dragging

    def event(self, event, clipboard=None):
        if event.value != "PRESS":
            return
        kind, text = event.type, self.text

        def insert(value):
            a, b = sorted((text.anchor, text.cursor))
            capacity = 4096 - (len(text.text) - (b - a))
            text.insert(value[: max(0, capacity)])

        command = getattr(event, "ctrl", False) or getattr(event, "oskey", False)
        if command and kind == "A":
            text.anchor, text.cursor = 0, len(text.text)
        elif command and kind in {"C", "X"} and clipboard is not None:
            a, b = sorted((text.anchor, text.cursor))
            clipboard.clipboard = text.text[a:b]
            if kind == "X":
                text.erase()
        elif command and kind == "V" and clipboard is not None:
            insert(clipboard.clipboard)
        elif kind in {"BACK_SPACE", "DEL"}:
            text.erase(kind == "BACK_SPACE")
        elif kind in {"LEFT_ARROW", "RIGHT_ARROW", "HOME", "END"}:
            position = {
                "LEFT_ARROW": text.cursor - 1,
                "RIGHT_ARROW": text.cursor + 1,
                "HOME": 0,
                "END": len(text.text),
            }[kind]
            text.move(position, getattr(event, "shift", False))
        elif getattr(event, "unicode", "") and not command:
            insert(event.unicode)
        text.text = text.text[:4096]
        text.cursor = min(text.cursor, len(text.text))
        text.anchor = min(text.anchor, len(text.text))
