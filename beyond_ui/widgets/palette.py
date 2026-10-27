"""Virtualized palette swatches, stable host identities, host-owned undo/editing."""

from dataclasses import dataclass
from .base import Widget, Painter, contains
from ..gpu import skin, style
from ..editing import to_display


@dataclass
class PaletteSource:
    count: object
    color: object
    active: object
    select: object
    valid: object = lambda: True
    add: object = None
    remove: object = None
    edit: object = None
    value: object = None


class Palette(Widget):
    width = 630.0
    height = 436.0
    columns = 6
    visible_rows = 3
    grid = (27.0, 79.0, 566.0, 267.0)
    add_rect = (38.0, 371.0, 54.0, 44.0)
    remove_rect = (104.0, 371.0, 54.0, 44.0)
    swatch_rect = (325.0, 374.0, 189.0, 37.0)

    def __init__(
        self,
        source,
        *,
        linear=True,
        show_colors=True,
        title="Palette",
        selected_text="Selected",
        unavailable_text="Palette unavailable",
    ):
        super().__init__()
        self.source = source
        self.title = title
        self.selected_text = selected_text
        self.unavailable_text = unavailable_text
        self.linear = linear
        self.show_colors = show_colors
        self.row_offset = 0
        self.focused = False

    def visible(self):
        count = self.source.count()
        start = (
            min(
                self.row_offset,
                max(0, (count + self.columns - 1) // self.columns - self.visible_rows),
            )
            * self.columns
        )
        return range(start, min(count, start + self.columns * self.visible_rows))

    def cell(self, index):
        local = index % 18
        return (27 + (local % 6) * 97, 79 + (local // 6) * 95, 79, 79)

    def event(self, event, x, y, *, clipboard=None):
        if not self.source.valid():
            return False
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"} and contains(self.grid, x, y):
            limit = max(0, (self.source.count() + 5) // 6 - 3)
            self.row_offset = max(
                0, min(limit, self.row_offset + (-1 if kind == "WHEELUPMOUSE" else 1))
            )
            return True
        if kind == "LEFTMOUSE" and press:
            if contains(self.add_rect, x, y) and self.source.add:
                self.source.add()
                return True
            if contains(self.remove_rect, x, y) and self.source.remove:
                self.source.remove()
                return True
            if contains(self.swatch_rect, x, y) and self.source.edit:
                index = self.source.active()
                if 0 <= index < self.source.count():
                    self.source.edit(index)
                    return True
            start = next(iter(self.visible()), 0)
            for index in self.visible():
                if contains(self.cell(index - start), x, y):
                    if getattr(event, "ctrl", False) and self.source.edit:
                        self.source.edit(index)
                    else:
                        self.source.select(index)
                    self.focused = True
                    return True
        if (
            self.focused
            and kind in {"LEFT_ARROW", "RIGHT_ARROW", "UP_ARROW", "DOWN_ARROW"}
            and press
        ):
            delta = {
                "LEFT_ARROW": -1,
                "RIGHT_ARROW": 1,
                "UP_ARROW": -6,
                "DOWN_ARROW": 6,
            }[kind]
            index = max(0, min(self.source.count() - 1, self.source.active() + delta))
            if self.source.count():
                self.source.select(index)
            self.row_offset = max(
                0, min(index // 6, max(self.row_offset, index // 6 - 2))
            )
            return True
        return False

    def display(self, index):
        if not self.show_colors:
            value = (
                self.source.value(index)
                if self.source.value
                else self.source.color(index)[0]
            )
            return (value, value, value, 1.0)
        color = tuple(self.source.color(index))
        rgb = tuple(to_display(c) for c in color[:3]) if self.linear else color[:3]
        return (*rgb, color[3] if len(color) > 3 else 1.0)

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        p.card(self.title, title_inset=76)
        if not self.source.valid():
            p.text((27, 79, 566, 52), self.unavailable_text, role="muted")
            return
        active = self.source.active()
        start = next(iter(self.visible()), 0)
        for index in self.visible():
            r = self.cell(index - start)
            if index == active:
                x, y, w, h = r
                with p.deform(("swatch", index), r, circular=True):
                    p.surface((x - 3, y - 3, w + 6, h + 6), skin.TEXT, 11, 0)
            color = self.display(index)
            with p.deform(("swatch", index), r, circular=True):
                skin.draw(
                    p.map(r),
                    style.shade(color, -0.012),
                    style.shade(color, 0.012),
                    radius=8 * p.scale,
                    border=0.7 * p.scale,
                )
        p.surface((27, 364, 577, 56), "input", 10, 1)
        for r, icon in ((self.add_rect, "+"), (self.remove_rect, "−")):
            p.surface(r, "button", 6, 0.6)
            p.icon(icon, r, 22)
        p.line(((179, 377), (179, 407)), skin.EDGE, 1.2 * p.scale)
        p.text((204, 364, 120, 56), self.selected_text, inset=0, size=21)
        if 0 <= active < self.source.count():
            p.surface(self.swatch_rect, self.display(active), 6, 0.6)
