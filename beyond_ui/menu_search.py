"""Retained menu search text; filtering runs on input, never while painting."""

from .context_edit import Editor
from .editing import Text


class Search:
    def __init__(self, rows):
        self.text = Text("")
        self.dragging = False
        self.focused = False
        self.rows = rows
        # Cache names once per open page. Never invoke child providers to search.
        group = ""
        labels = []
        for row in rows:
            if row.heading:
                group = row.label
            labels.append((row.label + " " + group).casefold())
        self.labels = tuple(labels)

    event = Editor.event

    def pointer(self, event, x, rect, measure):
        Editor.pointer(self, event, x, rect, measure, full_width=True)

    def filtered(self):
        words = self.text.text.casefold().split()
        if not words:
            return self.rows
        result = []
        heading = None
        emitted = False
        for row, label in zip(self.rows, self.labels):
            if row.key == "__back__":
                result.append(row)
            elif row.heading:
                heading, emitted = row, False
            elif all(word in label for word in words):
                if heading is not None and not emitted:
                    result.append(heading)
                    emitted = True
                result.append(row)
        return tuple(result)
