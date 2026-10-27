"""Searchable custom data picker; identity snapshots are revalidated on commit."""

from .base import Widget, Painter, contains
from ..components import matches
from ..virtual import VirtualList
from ..editing import Text
from ..gpu import style


class DataPicker(Widget):
    width = 320.0
    height = 232.0

    def __init__(self, items, select, *, selected=lambda: None, valid=lambda key: True):
        super().__init__()
        self.items = tuple(items)
        self.select = select
        self.selected = selected
        self.valid = valid
        self.query = ""
        self.filtered = self.items
        self.rows = VirtualList([34] * len(self.filtered))
        self.scroll_drag = None

    def _filter(self):
        self.filtered = tuple(
            item for item in self.items if matches(self.query, item[1])
        )
        self.rows.replace([34] * len(self.filtered))
        self.rows.offset = 0

    def cancel(self):
        self.scroll_drag = None
        super().cancel()

    def event(self, event, x, y, *, clipboard=None):
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        kind = event.type
        if self.text_edit:
            before = self.text_edit.text
            result = self.edit_text(event, clipboard=clipboard)
            if isinstance(result, str):
                self.query = result
                self._filter()
            elif result is False:
                self.query = ""
                self._filter()
            elif self.text_edit and before != self.text_edit.text:
                self.query = self.text_edit.text
                self._filter()
            if kind == "LEFTMOUSE" and press and y >= 42:
                self.text_edit = None
                self.capturing = False
            else:
                return True
        if kind in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"} and contains(
            (8, 48, 304, 172), x, y
        ):
            delta = (
                -24
                if kind == "WHEELUPMOUSE"
                else 24
                if kind == "WHEELDOWNMOUSE"
                else getattr(event, "mouse_prev_y", 0) - getattr(event, "mouse_y", 0)
            )
            self.rows.scroll(delta, 172)
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        if contains((8, 8, 304, 32), x, y):
            self.text_edit = Text(self.query)
            self.capturing = True
            return True
        if contains((8, 48, 296, 172), x, y):
            for i, top, height in self.rows.visible(172):
                if top <= y - 48 < top + height:
                    key = self.filtered[i][0]
                    if self.valid(key):
                        self.select(key)
                    return True
        return False

    def paint(self, rect, font, palette):
        p = Painter(rect, self.width, self.height, font, palette)
        p.surface((8, 8, 304, 32))
        p.text(
            (32, 8, 280, 32),
            self.text_edit.text if self.text_edit else self.query or "Search",
            role="text" if self.query else "muted",
        )
        x, y, w, h = p.map((12, 14, 20, 20))
        style.icon("search", x + w / 2, y + h / 2, 16 * p.scale, palette["text"])
        active = self.selected()
        for i, top, height in self.rows.visible(172):
            key, label, icon = self.filtered[i]
            r = (8, 48 + top, 296, height - 2)
            if top < 0 or top + height > 172:
                continue
            p.surface(r, "selected" if key == active else "field")
            p.text((36, 48 + top, 268, height - 2), label)
            x, y, w, h = p.map((12, 54 + top, 20, 20))
            style.icon(icon, x + w / 2, y + h / 2, 18 * p.scale, palette["text"])
        p.surface((308, 48, 4, 172), "slider_track", 2)
        if self.rows.height > 172:
            height = 172 * 172 / self.rows.height
            top = (172 - height) * self.rows.offset / (self.rows.height - 172)
            p.surface((308, 48 + top, 4, height), "muted", 2)
