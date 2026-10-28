"""Searchable custom data picker; identity snapshots are revalidated on commit."""

from .base import Widget, Painter, contains
from ..components import matches
from ..virtual import VirtualList
from ..editing import Text
from .metrics import PICKER, SIZE


class DataPicker(Widget):
    width, height = SIZE
    focusable = True
    navigation_keys = {"UP_ARROW", "DOWN_ARROW", "HOME", "END", "PAGE_UP", "PAGE_DOWN"}

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
        self.focused = False
        self.cursor = None

    def _filter(self):
        self.filtered = tuple(
            item for item in self.items if matches(self.query, item[1])
        )
        self.rows.replace([70] * len(self.filtered))
        self.rows.offset = 0
        self.cursor = None

    def cancel(self):
        self.scroll_drag = None
        self.focused = False
        self.cursor = None
        super().cancel()

    def focus(self):
        self.focused = True

    def blur(self):
        # Filtering is presentation state; leaving search preserves the query.
        self.cancel()

    def scrollbar(self):
        x, y, w, _ = PICKER["scroll"]
        viewport = PICKER["list"][3]
        total = max(280, self.rows.height)  # Preserve approved resting geometry.
        height = max(12.0, viewport * viewport / total)
        travel = viewport - height
        limit = max(0.0, self.rows.height - viewport)
        top = travel * self.rows.offset / limit if limit else 0.0
        return (x, y + top, w, height), travel, limit

    def _reveal_cursor(self):
        if self.cursor is None:
            return
        top, bottom = self.rows.edges[self.cursor : self.cursor + 2]
        viewport = PICKER["list"][3]
        if top < self.rows.offset:
            self.rows.scroll(top - self.rows.offset, viewport)
        elif bottom > self.rows.offset + viewport:
            self.rows.scroll(bottom - self.rows.offset - viewport, viewport)
        r = (25, 147 + top - self.rows.offset, 560, 65)
        self.motion.region(("row", self.filtered[self.cursor][0]), r)
        self.motion.pulse(("row", self.filtered[self.cursor][0]), 0.10)

    def _navigate(self, kind):
        if not self.filtered:
            return
        if self.cursor is None:
            selected = self.selected()
            current = next(
                (i for i, item in enumerate(self.filtered) if item[0] == selected), -1
            )
        else:
            current = self.cursor
        page = max(1, int(PICKER["list"][3] / PICKER["row_height"]))
        target = {
            "HOME": 0,
            "END": len(self.filtered) - 1,
            "UP_ARROW": current - 1,
            "DOWN_ARROW": current + 1,
            "PAGE_UP": current - page,
            "PAGE_DOWN": current + page,
        }[kind]
        self.cursor = max(0, min(len(self.filtered) - 1, target))
        self._reveal_cursor()

    def _accept(self):
        if not self.filtered:
            return False
        index = self.cursor if self.cursor is not None else 0
        key = self.filtered[index][0]
        if not self.valid(key):
            return False
        self.select(key)
        self.cursor = index
        self.text_edit = None
        self.capturing = False
        return True

    def event(self, event, x, y, *, clipboard=None):
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        kind = event.type
        if kind == "WINDOW_DEACTIVATE":
            self.cancel()
            return False
        if self.scroll_drag is not None:
            if kind in {"ESC", "RIGHTMOUSE"} and press:
                self.rows.offset = self.scroll_drag[1]
                self.scroll_drag = None
                self.capturing = False
                return True
            if kind == "MOUSEMOVE":
                _, travel, limit = self.scrollbar()
                self.rows.offset = max(
                    0,
                    min(
                        limit,
                        self.scroll_drag[1]
                        + (y - self.scroll_drag[0]) * limit / max(1, travel),
                    ),
                )
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self.scroll_drag = None
                self.capturing = False
            return True
        if self.focused or self.text_edit:
            if self.text_edit and self.query != self.text_edit.text:
                self.query = self.text_edit.text
                self._filter()
            if (
                press
                and kind in self.navigation_keys
                and not (self.text_edit and kind in {"HOME", "END"})
            ):
                self._navigate(kind)
                return True
            if press and kind in {"RET", "NUMPAD_ENTER"}:
                self._accept()
                return True
            if press and kind == "ESC" and not self.text_edit:
                self.blur()
                return True
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
            if kind == "LEFTMOUSE" and press and not contains(PICKER["search"], x, y):
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
        if not contains((0, 0, self.width, self.height), x, y):
            self.blur()
            return False
        if contains(PICKER["search"], x, y):
            self.focus()
            self.text_edit = Text(self.query)
            self.capturing = True
            return True
        if contains(PICKER["scroll"], x, y):
            self.focus()
            thumb, travel, limit = self.scrollbar()
            if limit and contains(thumb, x, y):
                self.scroll_drag = (y, self.rows.offset)
                self.capturing = True
            elif limit:
                self.rows.scroll(-206 if y < thumb[1] else 206, 206)
            return True
        for r, action in zip(PICKER["actions"], self.actions):
            if contains(r, x, y):
                if action:
                    action()
                return bool(action)
        if contains(PICKER["list"], x, y):
            for i, top, height in self.rows.visible(206):
                if top <= y - 147 < top + height:
                    self.focus()
                    self.cursor = i
                    self._accept()
                    return True
        return False

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        p.card(
            getattr(self, "title", "Data Picker"), blur=getattr(self, "glass_blur", 0.4)
        )
        p.surface(PICKER["search"], "input", border=1)
        p.text(
            (76, 74, 510, 57),
            self.text_edit.text if self.text_edit else self.query or "Search",
            role="text" if self.query else "muted",
            inset=16,
        )
        p.icon("search", (38, 84, 40, 37), 29)
        active = self.selected()
        with p.clip(PICKER["list"]):
            for i, top, height in self.rows.visible(206):
                key, label, icon = self.filtered[i]
                r = (25, 147 + top, 560, 65)
                highlighted = (
                    i == self.cursor
                    if self.focused and self.cursor is not None
                    else key == active
                )
                p.surface(
                    r,
                    "selected" if highlighted else "field",
                    7,
                    motion_key=("row", key),
                )
                self.motion.region(
                    ("row", key),
                    (
                        25,
                        max(147, 147 + top),
                        560,
                        max(0, min(353, 147 + top + 65) - max(147, 147 + top)),
                    ),
                )
                p.text(
                    (117, 147 + top, 460, 65),
                    label,
                    role="selected_text" if highlighted else "text",
                    inset=16,
                )
                # Four retained icon slots cover the clipped viewport. At rest,
                # use the approved coordinates exactly (no extra matrix rounding).
                import gpu

                anchor = (i % 4) * PICKER["row_height"]
                if top == anchor:
                    p.icon(
                        "○" if icon == "material" else icon,
                        (49, 156 + anchor, 52, 45),
                        37,
                        role="selected_text" if highlighted else "text",
                    )
                else:
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((0, -(top - anchor) * p.sy, 0))
                        p.icon(
                            "○" if icon == "material" else icon,
                            (49, 156 + anchor, 52, 45),
                            37,
                            role="selected_text" if highlighted else "text",
                        )
        p.surface(PICKER["scroll"], "track", 5, 0)
        thumb, _, _ = self.scrollbar()
        p.surface(thumb, "thumb", 5, 0.6, motion_key="scroll")
        self.motion.region("scroll", PICKER["scroll"])
        p.surface(PICKER["toolbar"], "field", 8)
        for x in (211, 417):
            p.line(((x, 394), (x, 430)), palette["toolbar_divider"], p.scale)
        for r, icon, action in zip(
            PICKER["actions"], ("+", "duplicate", "unlink"), self.actions
        ):
            p.icon(
                icon,
                r,
                31,
                role="muted"
                if getattr(self, "disabled_actions", False) and action is None
                else "text",
            )
