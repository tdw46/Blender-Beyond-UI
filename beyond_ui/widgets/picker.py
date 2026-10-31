"""Searchable custom data picker; identity snapshots are revalidated on commit."""

from .base import Widget, Painter, contains
from ..components import matches
from ..virtual import VirtualList
from ..editing import Text
from .metrics import PICKER, PICKER_SIZE


class DataPicker(Widget):
    design_font_size = 22.0
    width, height = PICKER_SIZE
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
        self.rows = VirtualList([PICKER["row_height"]] * len(self.filtered))
        self.scroll_drag = None
        self.focused = False
        self.cursor = None

    def _filter(self):
        self.filtered = tuple(
            item
            for item in self.items
            if matches(self.query, item[1])
            and (not hasattr(self, "filter_item") or self.filter_item(item, self.query))
        )
        self.rows.replace([PICKER["row_height"]] * len(self.filtered))
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
        total = max(viewport, self.rows.height)
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
        r = (16, 128 + top - self.rows.offset, 416, PICKER["row_height"])
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
        accept_text = getattr(self, "accept_text", None)
        if (
            accept_text is not None
            and self.cursor is None
            and self.text_edit is not None
        ):
            if accept_text(self.text_edit.text) is False:
                return False
            self.text_edit = None
            self.capturing = False
            return True
        if not self.filtered:
            return False
        index = self.cursor if self.cursor is not None else 0
        key = self.filtered[index][0]
        if not self.valid(key):
            return False
        if self.select(key) is False:
            return False
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
        if (
            self.focused
            and self.text_edit is None
            and press
            and getattr(self, "type_to_search", False)
            and getattr(event, "unicode", "")
            and not (getattr(event, "ctrl", False) or getattr(event, "oskey", False))
        ):
            self.text_edit = Text(self.query)
            self.capturing = True
        if self.text_edit:
            if kind == "RIGHTMOUSE" and press:
                self.text_edit = None
                self.capturing = False
                self.query = ""
                self._filter()
                return True
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
            self.rows.scroll(delta, PICKER["list"][3])
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
                self.rows.scroll(
                    -PICKER["list"][3] if y < thumb[1] else PICKER["list"][3],
                    PICKER["list"][3],
                )
            return True
        for r, action in zip(PICKER["actions"], self.actions):
            if contains(r, x, y):
                if action:
                    action()
                return bool(action)
        if contains(PICKER["list"], x, y):
            for i, top, height in self.rows.visible(PICKER["list"][3]):
                if top <= y - PICKER["list"][1] < top + height:
                    self.focus()
                    self.cursor = i
                    self._accept()
                    return True
        return False

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        from ..gpu import glass
        from ..gpu.menus import search_field
        from ..gpu.typography import face
        from ..menu_metrics import Metrics

        if not glass.lens(
            backdrop,
            rect,
            16 * p.scale,
            palette.get("menu_glass", (0, 0, 0, 0)),
            blur=0.7,
        ):
            p.surface((0, 0, self.width, self.height), "card", 16, motion_key=False)
        p.text(
            PICKER["title"],
            getattr(self, "title", "Data Picker"),
            size=2 * Metrics.TITLE_SIZE,
            inset=0,
            weight="title",
        )
        with p.deform("search", PICKER["search"]):
            search_field(
                face(font, "body"),
                p.map(PICKER["search"]),
                2 * p.scale,
                palette,
                backdrop,
                self.text_edit.text if self.text_edit else self.query,
                self.text_edit,
                lambda bounds: (bounds,),
                placeholder="Search…",
            )
        self.motion.region("search", PICKER["search"])
        active = self.selected()
        with p.clip(PICKER["list"]):
            for i, top, height in self.rows.visible(PICKER["list"][3]):
                key, label, icon = self.filtered[i]
                r = (16, 128 + top, 416, PICKER["row_height"])
                highlighted = (
                    i == self.cursor
                    if self.focused and self.cursor is not None
                    else key == active
                )
                with p.deform(("row", key), r):
                    if highlighted:
                        p.surface(
                            Metrics.highlight(r, 2), "selected", 14, motion_key=False
                        )
                    self.motion.region(
                        ("row", key),
                        (
                            16,
                            max(128, 128 + top),
                            416,
                            max(
                                0,
                                min(308, 128 + top + PICKER["row_height"])
                                - max(128, 128 + top),
                            ),
                        ),
                    )
                    p.text(
                        (
                            66 if icon else 20,
                            128 + top,
                            350 if icon else 396,
                            PICKER["row_height"],
                        ),
                        label,
                        role="selected_text" if highlighted else "text",
                        inset=16,
                    )
                    if not icon:
                        continue
                    # Four retained icon slots cover the clipped viewport. At rest,
                    # use the approved coordinates exactly (no extra matrix rounding).
                    import gpu

                    anchor = (i % 4) * PICKER["row_height"]
                    if top == anchor:
                        p.icon(
                            "○" if icon == "material" else icon,
                            (32, 128 + anchor, 30, PICKER["row_height"]),
                            28,
                            role="selected_text" if highlighted else "text",
                        )
                    else:
                        with gpu.matrix.push_pop():
                            gpu.matrix.translate((0, -(top - anchor) * p.sy, 0))
                            p.icon(
                                "○" if icon == "material" else icon,
                                (32, 128 + anchor, 30, PICKER["row_height"]),
                                28,
                                role="selected_text" if highlighted else "text",
                            )
        p.surface(PICKER["scroll"], "track", 5, 0)
        thumb, _, _ = self.scrollbar()
        p.surface(thumb, "thumb", 5, 0.6, motion_key="scroll")
        self.motion.region("scroll", PICKER["scroll"])
        p.surface(PICKER["toolbar"], "field", 8)
        for x in (154, 294):
            p.line(((x, 330), (x, 356)), palette["toolbar_divider"], p.scale)
        for r, icon, action in zip(
            PICKER["actions"], ("+", "duplicate", "unlink"), self.actions
        ):
            with p.deform(("action", icon), r):
                p.icon(
                    icon,
                    r,
                    26,
                    role="muted"
                    if getattr(self, "disabled_actions", False) and action is None
                    else "text",
                )
