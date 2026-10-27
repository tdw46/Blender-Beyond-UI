"""Searchable custom data picker; identity snapshots are revalidated on commit."""

from .base import Widget, Painter, contains
from ..components import matches
from ..virtual import VirtualList
from ..editing import Text
from ..gpu import skin
from .metrics import PICKER, SIZE


class DataPicker(Widget):
    width, height = SIZE

    def __init__(
        self,
        items,
        select,
        *,
        selected=lambda: None,
        valid=lambda key: True,
        create=None,
        duplicate=None,
        unlink=None,
    ):
        super().__init__()
        self.items = tuple(items)
        self.actions = (create, duplicate, unlink)
        self.select = select
        self.selected = selected
        self.valid = valid
        self.query = ""
        self.filtered = self.items
        self.rows = VirtualList([70] * len(self.filtered))
        self.scroll_drag = None

    def _filter(self):
        self.filtered = tuple(
            item for item in self.items if matches(self.query, item[1])
        )
        self.rows.replace([70] * len(self.filtered))
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
            if kind == "LEFTMOUSE" and press and y >= 147:
                self.text_edit = None
                self.capturing = False
            else:
                return True
        if kind in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"} and contains(
            PICKER["list"], x, y
        ):
            delta = (
                -24
                if kind == "WHEELUPMOUSE"
                else 24
                if kind == "WHEELDOWNMOUSE"
                else getattr(event, "mouse_prev_y", 0) - getattr(event, "mouse_y", 0)
            )
            self.rows.scroll(delta, 206)
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        if contains(PICKER["search"], x, y):
            self.text_edit = Text(self.query)
            self.capturing = True
            return True
        for r, action in zip(PICKER["actions"], self.actions):
            if contains(r, x, y):
                if action:
                    action()
                return bool(action)
        if contains(PICKER["list"], x, y):
            for i, top, height in self.rows.visible(206):
                if top <= y - 147 < top + height:
                    key = self.filtered[i][0]
                    if self.valid(key):
                        self.select(key)
                    return True
        return False

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(rect, self.width, self.height, font, palette, backdrop)
        p.card("Data Picker")
        p.surface(PICKER["search"], "input", border=1)
        p.text(
            (76, 74, 510, 57),
            self.text_edit.text if self.text_edit else self.query or "Search",
            role="text" if self.query else "muted",
            inset=16,
        )
        p.icon("search", (38, 84, 40, 37), 29)
        active = self.selected()
        for i, top, height in self.rows.visible(206):
            key, label, icon = self.filtered[i]
            if top < 0 or top + height > 210:
                continue
            r = (25, 147 + top, 560, 65)
            p.surface(r, "selected" if key == active else "field", 7)
            p.text((117, 147 + top, 460, 65), label, inset=16)
            p.icon("○" if icon == "material" else icon, (49, 156 + top, 52, 45), 37)
        p.surface(PICKER["scroll"], "track", 5, 0)
        visible = 206
        total = max(280, self.rows.height)
        height = visible * visible / total
        top = (visible - height) * self.rows.offset / max(1, total - visible)
        p.surface((598, 148 + top, 11, height), "thumb", 5, 0.6)
        p.surface(PICKER["toolbar"], "field", 8)
        for x in (211, 417):
            p.line(((x, 394), (x, 430)), skin.rgba("9da2a7", 0.40), p.scale)
        for r, icon in zip(PICKER["actions"], ("+", "duplicate", "unlink")):
            p.icon(icon, r, 31)
