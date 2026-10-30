"""Default RNA collection list, built from the shared source skin and motion."""

from math import ceil
from .base import Widget, Painter, contains
from ..list_source import ordered
from ..context_menu import Target, Entry, default_entries
from ..editing import Text


class CollectionList(Widget):
    focusable = True
    row_height = 28.0
    navigation_keys = {
        "UP_ARROW",
        "DOWN_ARROW",
        "LEFT_ARROW",
        "RIGHT_ARROW",
        "HOME",
        "END",
        "PAGE_UP",
        "PAGE_DOWN",
    }

    def __init__(
        self,
        source,
        state,
        *,
        rows=5,
        maxrows=5,
        type="DEFAULT",
        columns=9,
        sort_lock=False,
        changed=lambda: None,
    ):
        super().__init__()
        self.source, self.state = source, state
        self.type, self.columns, self.sort_lock = type, columns, sort_lock
        self.minimum, self.maximum = max(1, rows or 5), max(1, maxrows or rows or 5)
        self.maximum = max(self.minimum, self.maximum)
        self.changed = changed
        self.focused = False
        self.drag = None
        self.edit_item = None
        self.error = None
        self.begin_capture = lambda: None
        self.filtered = ()
        self.reorder()

    def dimensions(self, font_size, available_width, available_height=None):
        scale = max(0.01, font_size / self.design_font_size)
        self.width = max(1, min(560, available_width / scale))
        self.visible_rows = (
            1
            if self.type == "COMPACT"
            else max(
                self.minimum, min(self.maximum, self.state.get("rows", self.minimum))
            )
        )
        self.grid_columns = (
            max(1, min(self.columns, int(self.width / 76)))
            if self.type == "GRID"
            else 1
        )
        self.viewport = self.visible_rows * self.row_height
        self.height = self.viewport + (
            0
            if self.type == "COMPACT"
            else 26 + (106 if self.state.get("show_filter") else 0)
        )
        self.scroll_to(self.state.get("scroll", 0))
        return self.width * scale, self.height * scale

    def reorder(self):
        self.filtered = ordered(
            self.source.items,
            self.state.get("query", ""),
            invert=self.state.get("invert", False),
            alpha=self.state.get("alpha", False),
            reverse=self.state.get("reverse", False),
        )
        if hasattr(self, "viewport"):
            self.scroll_to(self.state.get("scroll", 0))

    def refresh(self):
        self.cancel()
        self.source.refresh()
        self.reorder()

    @property
    def offset(self):
        return self.state.get("scroll", 0.0)

    @property
    def limit(self):
        return max(
            0,
            ceil(len(self.filtered) / self.grid_columns) * self.row_height
            - self.viewport,
        )

    def scroll_to(self, offset):
        self.state["scroll"] = max(0.0, min(self.limit, offset))

    def selected(self):
        try:
            return self.source.active.get()
        except (ReferenceError, RuntimeError, AttributeError):
            return -1

    def visible(self, top=0.0, bottom=None):
        bottom = self.viewport if bottom is None else min(self.viewport, bottom)
        if bottom <= top:
            return
        if self.type == "COMPACT":
            index = self.selected()
            if 0 <= index < len(self.source.items):
                yield (
                    self.source.items[index],
                    (2, 2, max(0, self.width - 64), self.row_height - 4),
                )
            return
        first = int((self.offset + top) // self.row_height) * self.grid_columns
        last = min(
            len(self.filtered),
            ceil((self.offset + bottom) / self.row_height) * self.grid_columns,
        )
        width = max(1, self.width - 12) / self.grid_columns
        for index in range(first, last):
            yield (
                self.filtered[index],
                (
                    2 + (index % self.grid_columns) * width,
                    (index // self.grid_columns) * self.row_height - self.offset + 2,
                    max(0, width - 4),
                    self.row_height - 4,
                ),
            )

    def row_at(self, x, y):
        if not contains(
            (0, 0, self.width - (64 if self.type == "COMPACT" else 12), self.viewport),
            x,
            y,
        ):
            return None
        return next(
            (item for item, rect in self.visible() if contains(rect, x, y)), None
        )

    def scrollbar(self):
        track = (self.width - 6, 2, 3, max(0, self.viewport - 4))
        total = self.viewport + self.limit
        height = min(track[3], max(12, track[3] * self.viewport / max(1, total)))
        travel = track[3] - height
        return (
            (track[0], track[1] + travel * self.offset / max(1, self.limit), 3, height),
            track,
            travel,
        )

    def filters(self):
        top = self.viewport + 28
        yield "query", "Search", (4, top, max(0, self.width - 8), 26)
        for i, (key, label) in enumerate(
            (
                ("invert", "Invert Filter"),
                ("alpha", "Sort by Name"),
                ("reverse", "Reverse"),
            )
        ):
            if not self.sort_lock or key == "invert":
                yield key, label, (4, top + 28 + i * 24, max(0, self.width - 8), 24)

    def focus(self):
        self.focused = True

    def wants_key(self, event):
        return (
            event.type == "F"
            and self.type != "COMPACT"
            and (getattr(event, "ctrl", False) or getattr(event, "oskey", False))
        )

    def blur(self):
        self.cancel()

    def cancel(self):
        if self.text_edit is not None and self.field == "query":
            self.state["query"] = self.query_before
            self.reorder()
        self.focused = False
        self.drag = self.edit_item = None
        super().cancel()

    def search(self):
        self.state["show_filter"] = True
        self.focus()
        self.field = "query"
        self.text_edit = Text(self.state.get("query", ""))
        self.query_before = self.text_edit.text
        self.capturing = True
        self.changed()
        self.begin_capture()

    def rename(self, item):
        binding = self.source.name_binding(item)
        if binding is None or not binding.valid():
            return
        self.edit_item = item
        self.field = "name"
        self.text_edit = Text(str(binding.read()))
        self.capturing = True
        self.focus()
        self.begin_capture()

    def toggle(self, key):
        if self.sort_lock and key in {"alpha", "reverse"}:
            return
        before = self.state.get(key, False)
        self.state[key] = not before
        self.reorder()
        self.motion.retarget(("filter", key), before, not before)
        self.changed()

    def reveal(self, item):
        if item not in self.filtered:
            return
        index = self.filtered.index(item)
        top = (index // self.grid_columns) * self.row_height
        if top < self.offset:
            self.scroll_to(top)
        elif top + self.row_height > self.offset + self.viewport:
            self.scroll_to(top + self.row_height - self.viewport)
        self.motion.pulse(("row", item.identity), 0.1)

    def navigate(self, kind):
        rows = self.source.items if self.type == "COMPACT" else self.filtered
        if not rows:
            return
        current = next(
            (i for i, item in enumerate(rows) if item.index == self.selected()), -1
        )
        page = self.visible_rows * self.grid_columns
        target = {
            "HOME": 0,
            "END": len(rows) - 1,
            "UP_ARROW": current - self.grid_columns,
            "DOWN_ARROW": current + self.grid_columns,
            "LEFT_ARROW": current - 1,
            "RIGHT_ARROW": current + 1,
            "PAGE_UP": current - page,
            "PAGE_DOWN": current + page,
        }[kind]
        item = rows[max(0, min(len(rows) - 1, target))]
        self.source.select(item)
        self.reveal(item)

    def event(self, event, x, y, *, clipboard=None):
        try:
            return self._event(event, x, y, clipboard=clipboard)
        except (ReferenceError, RuntimeError, ValueError, AttributeError) as error:
            self.error = str(error)
            self.cancel()
            return True

    def _event(self, event, x, y, *, clipboard=None):
        kind, press = event.type, event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind == "WINDOW_DEACTIVATE":
            self.cancel()
            return False
        if self.drag:
            mode, start, before = self.drag
            if kind in {"ESC", "RIGHTMOUSE"} and press:
                self.state[mode] = before
                self.drag = None
                self.capturing = False
                self.changed()
            elif kind == "MOUSEMOVE":
                if mode == "scroll":
                    self.scroll_to(
                        before + (y - start) * self.limit / max(1, self.scrollbar()[2])
                    )
                else:
                    self.state["rows"] = max(
                        self.minimum,
                        min(
                            self.maximum, round(before + (y - start) / self.row_height)
                        ),
                    )
                    self.changed()
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self.drag = None
                self.capturing = False
            return True
        if self.text_edit:
            if self.field == "name" and not self.source.valid_item(self.edit_item):
                raise ReferenceError("Edited list row changed")
            field, item = self.field, self.edit_item
            if press and kind in {"ESC", "RIGHTMOUSE"}:
                if field == "query":
                    self.state["query"] = self.query_before
                    self.reorder()
                self.text_edit = self.edit_item = self.field = None
                self.capturing = False
                return True
            result = self.edit_text(event, clipboard=clipboard)
            if self.text_edit is not None:
                self.text_edit.text = self.text_edit.text[:4096]
                self.text_edit.cursor = min(
                    self.text_edit.cursor, len(self.text_edit.text)
                )
                self.text_edit.anchor = min(
                    self.text_edit.anchor, len(self.text_edit.text)
                )
            if isinstance(result, str) and field == "name":
                self.source.rename(item, result)
                self.reorder()
                self.edit_item = self.field = None
            elif field == "query":
                self.state["query"] = (
                    self.text_edit.text if self.text_edit else str(result or "")
                )
                self.reorder()
                self.scroll_to(0)
            return True
        if (
            press
            and self.focused
            and kind == "F"
            and (getattr(event, "ctrl", False) or getattr(event, "oskey", False))
            and self.type != "COMPACT"
        ):
            self.search()
            return True
        if press and self.focused and kind in self.navigation_keys:
            self.navigate(kind)
            return True
        if press and kind == "ESC" and self.focused:
            self.blur()
            return True
        if kind in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"} and contains(
            (0, 0, self.width, self.viewport), x, y
        ):
            if self.type == "COMPACT":
                self.navigate("UP_ARROW" if kind == "WHEELUPMOUSE" else "DOWN_ARROW")
            else:
                delta = (
                    -self.row_height
                    if kind == "WHEELUPMOUSE"
                    else self.row_height
                    if kind == "WHEELDOWNMOUSE"
                    else getattr(event, "mouse_prev_y", 0)
                    - getattr(event, "mouse_y", 0)
                )
                self.scroll_to(self.offset + delta)
            return True
        if not press or kind != "LEFTMOUSE":
            return False
        self.focus()
        if self.type == "COMPACT" and x >= self.width - 60:
            self.navigate("UP_ARROW" if x < self.width - 30 else "DOWN_ARROW")
            return True
        if contains((self.width - 12, 0, 12, self.viewport), x, y) and self.limit:
            thumb, _, _ = self.scrollbar()
            if contains((self.width - 12, thumb[1], 12, thumb[3]), x, y):
                self.drag = ("scroll", y, self.offset)
                self.capturing = True
            else:
                self.scroll_to(
                    self.offset + (-self.viewport if y < thumb[1] else self.viewport)
                )
            return True
        item = self.row_at(x, y)
        if item:
            active = item.index == self.selected()
            if not active:
                self.source.select(item)
            if active and (
                event.value == "DOUBLE_CLICK" or getattr(event, "ctrl", False)
            ):
                self.rename(item)
            return True
        if self.type != "COMPACT" and contains(
            (0, self.viewport, self.width, 26), x, y
        ):
            if self.maximum > self.minimum and abs(x - self.width / 2) < 28:
                self.drag = ("rows", y, self.visible_rows)
                self.capturing = True
            else:
                self.state["show_filter"] = not self.state.get("show_filter", False)
                self.changed()
            return True
        if self.state.get("show_filter"):
            for key, _, rect in self.filters():
                if contains(rect, x, y):
                    self.search() if key == "query" else self.toggle(key)
                    return True
        return False

    def target_at(self, key, x, y):
        item = self.row_at(x, y)
        if item:
            binding = self.source.name_binding(item)
            return Target(
                key,
                ("row", item.index, item.identity),
                binding,
                lambda: self.source.valid_item(item),
                lambda: item.name,
                item,
            )
        part = "body"
        if x >= self.width - 12 and y < self.viewport:
            part = "scroll"
        elif self.state.get("show_filter"):
            part = next(
                (name for name, _, rect in self.filters() if contains(rect, x, y)),
                "body",
            )
        return Target(key, (part,), valid=self.source.valid, payload=self)

    def entries(self, target, context):
        rows = []
        if target.part[0] == "row":
            item = target.payload
            rows.append(
                Entry(
                    "LIST_SELECT",
                    "Select",
                    lambda t, c: self.source.select(item),
                    enabled=lambda t, c: t.editable() and self.source.active.valid(),
                )
            )
            if target.binding:
                rows.append(
                    Entry(
                        "LIST_RENAME",
                        "Rename",
                        lambda t, c: self.rename(item),
                        enabled=lambda t, c: t.editable() and target.binding.valid(),
                    )
                )
            rows.extend(default_entries(target, context))
        else:
            rows.append(
                Entry("LIST_REFRESH", "Refresh List", lambda t, c: self.refresh())
            )
            if self.type != "COMPACT":
                rows.extend(
                    (
                        Entry(
                            "LIST_SEARCH",
                            "Search",
                            lambda t, c: self.search(),
                            shortcut="Ctrl F",
                        ),
                        Entry(
                            "LIST_TOP", "Scroll to Top", lambda t, c: self.scroll_to(0)
                        ),
                        Entry(
                            "LIST_BOTTOM",
                            "Scroll to Bottom",
                            lambda t, c: self.scroll_to(self.limit),
                        ),
                    )
                )
                for name, label in (
                    ("invert", "Invert Filter"),
                    ("alpha", "Sort by Name"),
                    ("reverse", "Reverse"),
                ):
                    if not self.sort_lock or name == "invert":
                        rows.append(
                            Entry(
                                "LIST_" + name.upper(),
                                label,
                                lambda t, c, name=name: self.toggle(name),
                                checked=lambda t, c, name=name: self.state.get(
                                    name, False
                                ),
                                toggle=True,
                            )
                        )
        provider = self.source.layout.canvas.context_provider
        if provider:
            rows.extend(provider(target, context))
        return tuple(rows)

    def paint(self, rect, font, palette, *, backdrop=None):
        from ..gpu import glass, style

        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        if backdrop is None or not glass.lens(
            backdrop,
            rect,
            7 * p.scale,
            palette["surfaces"]["card"][0],
            blur=getattr(self, "glass_blur", 0.4),
        ):
            p.surface((0, 0, self.width, self.height), "card", 7, motion_key=False)
        selected = self.selected()
        with p.clip((0, 0, self.width, self.viewport)):
            clip_top = max(0, (rect[1] + rect[3] - p._clip[3]) / p.sy)
            clip_bottom = min(self.viewport, (rect[1] + rect[3] - p._clip[1]) / p.sy)
            for item, r in self.visible(clip_top, clip_bottom):
                active = item.index == selected
                key = ("row", item.identity)
                with p.deform(key, r):
                    p.surface(
                        r, "selected" if active else "field", 5, 0.5, motion_key=False
                    )
                    editing = (
                        self.text_edit is not None
                        and self.field == "name"
                        and self.edit_item == item
                    )
                    if editing:
                        self.paint_editor(
                            p, r, role="selected_text" if active else "text"
                        )
                    else:
                        p.text(
                            r,
                            item.name,
                            "selected_text" if active else "text",
                            11,
                            inset=8,
                        )
                self.motion.region(
                    key,
                    (
                        r[0],
                        max(0, r[1]),
                        r[2],
                        max(0, min(self.viewport, r[1] + r[3]) - max(0, r[1])),
                    ),
                )
        if self.type == "COMPACT":
            for direction, x in (("left", self.width - 56), ("right", self.width - 28)):
                r = (x, 2, 24, self.row_height - 4)
                with p.deform(direction, r):
                    p.surface(r, "button", 5, motion_key=False)
                    p.icon("‹" if direction == "left" else "›", r, 10)
            return
        thumb, track, _ = self.scrollbar()
        if self.limit:
            p.surface(track, "track", 2, 0, motion_key=False)
            with p.deform("scroll", thumb):
                p.surface(thumb, "thumb", 2, 0.6, motion_key=False)
            self.motion.region("scroll", (self.width - 12, 0, 12, self.viewport))
        footer = (2, self.viewport + 1, self.width - 4, 24)
        with p.deform("filter-reveal", footer):
            p.icon(
                "▾" if self.state.get("show_filter") else "▸",
                (8, self.viewport + 3, 16, 20),
                8,
                role="muted",
            )
            p.text(
                (25, self.viewport + 1, max(0, self.width - 110), 24),
                "Filter",
                size=11,
                inset=0,
            )
            p.text(
                (self.width - 82, self.viewport, 74, 26),
                f"{len(self.filtered)} / {len(self.source.items)}",
                "muted",
                11,
                align="right",
                inset=4,
            )
        if self.maximum > self.minimum:
            with p.deform("resize", (self.width / 2 - 24, self.viewport, 48, 24)):
                for dx in (-7.5, -2.5, 2.5, 7.5):
                    p.circle(
                        (self.width / 2 + dx, self.viewport + 12), 0.9, palette["muted"]
                    )
        if self.state.get("show_filter"):
            for key, label, r in self.filters():
                with p.deform(("filter", key), r):
                    if key == "query":
                        p.surface(r, "input", 5, motion_key=False)
                        if self.text_edit is not None and self.field == "query":
                            self.paint_editor(p, r)
                        else:
                            p.text(
                                r,
                                self.state.get("query") or label,
                                "text" if self.state.get("query") else "muted",
                                11,
                                inset=8,
                            )
                    else:
                        p.text(
                            (r[0], r[1], max(0, r[2] - 38), r[3]),
                            label,
                            size=11,
                            inset=8,
                        )
                        switch = p.map((max(r[0], r[0] + r[2] - 34), r[1] + 4, 28, 16))
                        style.switch(
                            *switch,
                            self.motion.position(
                                ("filter", key), bool(self.state.get(key, False))
                            ),
                            scale=p.scale,
                            palette=palette,
                            backdrop=backdrop,
                        )

    def paint_editor(self, p, rect, *, role="text"):
        from ..gpu.paint import measure
        from ..gpu.typography import face

        edit = self.text_edit
        font = face(p.font, "body")
        width = lambda text: measure(font, 11 * p.scale, text)[0] / p.scale
        x, y, w, h = rect
        caret = width(edit.text[: edit.cursor])
        shift = max(0, caret - max(1, w - 18))
        a, b = sorted((edit.anchor, edit.cursor))
        with p.clip((x + 4, y, max(0, w - 8), h)):
            if a != b:
                left, right = width(edit.text[:a]), width(edit.text[:b])
                p.surface(
                    (x + 8 + left - shift, y + 5, right - left, h - 10),
                    "selected",
                    0,
                    0,
                    motion_key=False,
                )
            p.text((x - shift, y, w + shift, h), edit.text, role=role, size=11, inset=8)
            p.surface(
                (x + 8 + caret - shift, y + 5, 1, h - 10),
                p.palette[role],
                0,
                0,
                motion_key=False,
            )
