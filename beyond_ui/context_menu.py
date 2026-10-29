"""Bounded, host-extensible context menus. No bpy or GPU work on import.

Source behavior: BVT VRM_ShoostContextMenu / VRM_ShoostCanvas. Actions and
capabilities are rechecked on input; painting only consumes prepared rows.
"""

from dataclasses import dataclass, replace
from itertools import islice
from .animation import Motion


@dataclass(frozen=True)
class Target:
    key: str
    part: tuple = ()
    binding: object = None
    valid: object = lambda: True
    value: object = None
    payload: object = None
    commit: object = None
    editable: object = lambda: True


@dataclass(frozen=True)
class Shortcut:
    type: str
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    oskey: bool = False
    any: bool = False
    key_modifier: str = "NONE"

    hyper: int = 0

    def matches(self, event, held=()):
        return (
            event.value == "PRESS"
            and event.type == self.type
            and (self.key_modifier == "NONE" or self.key_modifier in held)
            and (
                self.any
                or all(
                    getattr(self, name) == -1
                    or bool(getattr(event, name, False)) == bool(getattr(self, name))
                    for name in ("shift", "ctrl", "alt", "oskey", "hyper")
                )
            )
        )


@dataclass(frozen=True)
class Entry:
    key: str
    label: str
    action: object = None  # (target, current_context) -> result
    enabled: object = True  # bool or (target, current_context) -> bool
    children: object = None  # on-demand (target, current_context) -> entries
    icon: str = ""
    tip: str = ""
    divider: bool = False
    shortcut: str = ""
    bindings: tuple = ()
    capture: object = None  # True accepts; a string updates the capture prompt.
    capture_prompt: str = "Press a key…"
    capture_options: object = None  # on-demand alternate capture modes
    capture_mouse: bool = False
    checked: object = False  # prepared on open/input, never read from paint
    field: object = None  # context_edit.Field
    heading: bool = False
    toggle: bool = False  # Boolean property; enum selections retain their checks.


@dataclass
class Page:
    rows: tuple
    available: tuple
    rect: tuple
    highlight: int = 0
    offset: int = 0
    title: str = ""
    checked: tuple = ()
    values: tuple = ()
    search: object = None


def inside(rect, x, y):
    a, b, w, h = rect
    return a <= x < a + w and b <= y < b + h


class Menu:
    limit = 64
    depth_limit = 3
    row_height = 23.0
    padding = 4.0

    def __init__(
        self,
        target,
        rows,
        anchor,
        clip,
        *,
        context=None,
        measure=None,
        scope=lambda context: None,
        on_error=None,
        on_tip=None,
        row_limit=64,
        search_threshold=12,
    ):
        if not 1 <= row_limit <= 4096:
            raise ValueError("Menu row limit must be between 1 and 4096")
        self.limit = row_limit
        if not isinstance(search_threshold, int) or search_threshold < 1:
            raise ValueError("Search threshold must be a positive integer")
        self.search_threshold = search_threshold
        self.target, self.anchor, self.clip = target, anchor, clip
        self.scope, self.scope_id = scope, scope(context)
        self.measure = measure or (lambda text, size: len(text) * size * 0.6)
        self.on_error = on_error or (lambda error: None)
        self.motion = Motion()
        self.parents = []
        self.editor = None
        self.capture_row = None
        self.capture_picker = self.capture_return = None
        self.held_keys = set()
        self.closed = False
        self.glass_ready = False
        self.error = None
        self.on_tip = on_tip or (lambda delay: None)
        self.tooltip = None
        self.tip_pending = None
        self.page = self._page(rows, context)

    def _page(self, rows, context, title="", max_width=None):
        rows = tuple(islice(rows, self.limit))
        if title and rows:
            rows = (replace(rows[0], divider=True),) + rows[1:]
        if title:
            rows = (Entry("__back__", title, icon="‹"),) + rows[: self.limit - 1]
        if not rows:
            raise ValueError("Empty context menu")
        from .menu_search import Search

        search = (
            Search(rows)
            if sum(not r.heading and r.key != "__back__" for r in rows)
            >= self.search_threshold
            else None
        )
        available = tuple(self._enabled(row, context) for row in rows)
        cx, cy, cw, ch = self.clip
        width = min(
            cw,
            max(
                260.0,
                max(
                    self.measure(r.label, 11) + self.measure(r.shortcut, 10) + 64
                    for r in rows
                ),
            ),
        )
        if max_width is not None:
            width = min(width, max_width)
        height = min(
            ch,
            sum(self.row_height + (8 if r.divider else 0) for r in rows[:18])
            + 2 * self.padding,
            # The search stays pinned above the scrolling result rows.
        )
        if search is not None:
            height = min(ch, height + 28)
        x, y = self.anchor
        rect = (
            max(cx, min(x, cx + cw - width)),
            max(cy, min(y, cy + ch - height)),
            width,
            height,
        )
        if search is not None:
            search.rect = rect
        return Page(
            rows,
            available,
            rect,
            title=title,
            checked=tuple(self._checked(row, context) for row in rows),
            values=tuple(self._value(row, context) for row in rows),
            search=search,
        )

    def search_rect(self, page=None):
        p = page or self.page
        if p.search is None:
            return None
        x, y, w, h = p.rect
        return (
            x + self.padding,
            y + self.padding,
            w - 2 * self.padding,
            min(28, max(0, h - 2 * self.padding - self.row_height)),
        )

    def filter_search(self, context=None):
        p = self.page
        rows = p.search.filtered()
        if not any(not r.heading and r.key != "__back__" for r in rows):
            rows = (
                *rows,
                Entry("__no_matches__", "No matches", enabled=False, heading=True),
            )
        p.rows = rows
        x, y, w, h = p.search.rect
        p.rect = (
            x,
            y,
            w,
            min(
                h,
                28
                + 2 * self.padding
                + sum(self.row_height + (8 if r.divider else 0) for r in rows[:18]),
            ),
        )
        p.offset = 0
        self.refresh(context)
        p.highlight = next(
            (
                i
                for i, ok in enumerate(p.available)
                if ok and p.rows[i].key != "__back__"
            ),
            0,
        )
        self.hide_tip()
        # Row indices now refer to different options. Retire their tracks while
        # preserving the current reveal/search springs during rapid typing.
        for key in tuple(self.motion.tracks):
            if isinstance(key, tuple) and key[0] == "row":
                del self.motion.tracks[key]
        self.motion.regions.clear()
        self.motion.hover = self.motion.pressed = None
        self.motion.pulse("search", 0.06)

    def search_event(self, event, x, y, context):
        """Handle text before shortcuts; navigation and actions keep normal routing."""
        search = self.page.search
        if search is None:
            return False
        rect = self.search_rect()
        field = (rect[0], rect[1], max(0, rect[2] - 22), rect[3])
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        command = getattr(event, "ctrl", False) or getattr(event, "oskey", False)
        if press and kind in {"ESC", "RIGHTMOUSE"} and search.text.text:
            if kind == "RIGHTMOUSE" and not inside(self.clip, x, y):
                return False
            from .editing import Text

            search.text = Text("")
            search.focused = search.dragging = False
            self.filter_search(context)
            return True
        if kind == "LEFTMOUSE" and event.value == "RELEASE":
            dragging, search.dragging = search.dragging, False
            return dragging
        if kind == "MOUSEMOVE" and search.dragging:
            search.pointer(event, x, field, self.measure)
            return True
        if kind == "LEFTMOUSE" and press:
            search.focused = inside(rect, x, y)
            if search.focused:
                if x >= field[0] + field[2]:
                    from .editing import Text

                    search.text = Text("")
                    self.filter_search(context)
                else:
                    search.pointer(event, x, field, self.measure)
                self.motion.pulse("search", 0.08)
                return True
        if press and kind in {"UP_ARROW", "DOWN_ARROW", "PAGE_UP", "PAGE_DOWN"}:
            search.focused = False
            return False
        if not press:
            return False
        if command and kind == "F":
            search.focused = True
            search.text.anchor, search.text.cursor = 0, len(search.text.text)
            return True
        if command and not search.focused:
            if any(
                self.page.available[i]
                and any(s.matches(event, self.held_keys) for s in row.bindings)
                for i, row in enumerate(self.page.rows)
            ):
                return False
        typing = (
            bool(getattr(event, "unicode", ""))
            and event.unicode.isprintable()
            and not command
            and not getattr(event, "alt", False)
        )
        editing = search.focused and kind in {
            "LEFT_ARROW",
            "RIGHT_ARROW",
            "HOME",
            "END",
        }
        editing |= (
            bool(search.focused or search.text.text) and kind in {"BACK_SPACE", "DEL"}
        ) or (
            command and (kind in {"A", "V"} or (search.focused and kind in {"C", "X"}))
        )
        if typing or editing:
            before = search.text.text
            search.focused = True
            search.event(event, getattr(context, "window_manager", None))
            if before != search.text.text:
                self.filter_search(context)
            return True
        return False

    def _enabled(self, row, context):
        if row.heading:
            return False
        try:
            return bool(
                row.enabled(self.target, context)
                if callable(row.enabled)
                else row.enabled
            )
        except Exception as error:
            self._error(error)
            return False

    def _checked(self, row, context):
        try:
            return bool(
                row.checked(self.target, context)
                if callable(row.checked)
                else row.checked
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    def _value(self, row, context):
        if row.field is None:
            return ""
        try:
            return row.field.format(row.field.read(self.target, context), context)[
                :4096
            ]
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return "Unavailable"

    def _error(self, error):
        self.error = str(error)
        try:
            self.on_error(error)
        except Exception:
            pass  # A reporting callback cannot kill the host's modal.

    def valid(self, context):
        try:
            return (
                not self.closed
                and self.target.valid()
                and self.scope(context) == self.scope_id
            )
        except Exception as error:
            self._error(error)
            return False

    def refresh(self, context):
        if not self.valid(context):
            self.close()
            return False
        self.page.available = tuple(
            self._enabled(row, context) for row in self.page.rows
        )
        self.page.checked = tuple(self._checked(row, context) for row in self.page.rows)
        self.page.values = tuple(self._value(row, context) for row in self.page.rows)
        return True

    @property
    def capacity(self):
        search = self.search_rect()
        return max(
            1,
            int(
                max(
                    0,
                    self.page.rect[3] - 2 * self.padding - (search[3] if search else 0),
                )
                // self.row_height
            ),
        )

    def visible_rows(self, page=None):
        p = page or self.page
        a, b, w, h = p.rect
        top = b + self.padding
        search = self.search_rect(p)
        if search:
            top += search[3]
        bottom = b + h - self.padding
        for i in range(p.offset, min(len(p.rows), p.offset + 18)):
            divider = 8 if p.rows[i].divider else 0
            if top + divider + self.row_height > bottom and i > p.offset:
                break
            top += divider if top + divider + self.row_height <= bottom else 0
            height = min(self.row_height, max(0, bottom - top))
            if height <= 0:
                break
            yield i, (a + self.padding, top, w - 2 * self.padding, height), p.rows[i]
            top += height

    def reveal(self):
        p = self.page
        p.offset = max(0, min(p.offset, p.highlight))
        while p.offset < p.highlight and p.highlight not in {
            i for i, _, _ in self.visible_rows()
        }:
            p.offset += 1

    @property
    def tip(self):
        return self.page.rows[self.page.highlight].tip

    def hide_tip(self):
        changed = self.tooltip is not None or self.tip_pending is not None
        self.tooltip = self.tip_pending = None
        if changed:
            self.on_tip(None)

    def hover_tip(self, index, x, y, context):
        prefs = getattr(getattr(context, "preferences", None), "view", None)
        text = self.page.rows[index].tip if index is not None else ""
        if not text or not getattr(prefs, "show_tooltips", True):
            self.hide_tip()
            return
        old = self.tip_pending
        if old and old[:2] == (index, text) and abs(old[2] - x) + abs(old[3] - y) < 4:
            return
        self.hide_tip()
        self.tip_pending = (index, text, x, y, self.motion.clock() + 0.55)
        self.on_tip(0.55)

    def reveal_tip(self, context):
        """One delayed host callback; no polling once the description is visible."""
        pending = self.tip_pending
        if pending is None or not self.valid(context):
            self.hide_tip()
            return None
        prefs = getattr(getattr(context, "preferences", None), "view", None)
        if not getattr(prefs, "show_tooltips", True):
            self.hide_tip()
            return None
        remaining = pending[4] - self.motion.clock()
        if remaining > 0:
            return remaining
        from textwrap import wrap

        index, text, _, _, _ = pending
        row = next((r for i, r, _ in self.visible_rows() if i == index), None)
        if row is None:
            self.hide_tip()
            return None
        cx, cy, cw, ch = self.clip
        width = min(320.0, cw)
        chars = max(12, int((width - 20) / 6.5))
        lines = tuple(
            line
            for para in text.splitlines()
            for line in wrap(para, chars, break_on_hyphens=False)
        )
        count = min(len(lines), max(0, int((ch - 12) / 16)))
        if not count:
            self.hide_tip()
            return None
        width = min(
            width, max(48.0, max(self.measure(line, 11) for line in lines) + 20)
        )
        height = count * 16 + 12
        x = max(cx, min(row[0], cx + cw - width))
        above, below = row[1] - height - 6, row[1] + row[3] + 6
        y = max(cy, min(above if above >= cy else below, cy + ch - height))
        shown = list(lines[:count])
        if len(lines) > count:
            shown[-1] += "…"
        self.tooltip = ((x, y, width, height), tuple(shown))
        self.motion.pulse("tooltip", 0.12)
        return None

    def close(self):
        self.hide_tip()
        self.closed = True
        self.motion.clear()
        self.parents.clear()
        self.held_keys.clear()
        self.editor = None
        self.capture_row = None
        self.capture_picker = self.capture_return = None
        self.page.search = None

    def back(self):
        if self.capture_return is not None:
            self.hide_tip()
            self.page, self.capture_return = self.capture_return, None
            self.capture_row = None
            self.held_keys.clear()
            self.motion.clear()
            self.motion.pulse("reveal", 0.12)
            return True
        if not self.parents:
            return False
        self.hide_tip()
        self.capture_row = None
        self.held_keys.clear()
        self.page = self.parents.pop()
        self.capture_picker = None
        self.motion.clear()
        self.motion.pulse("reveal", 0.12)
        return True

    def start_capture(self, row, context, *, replace_mode=False):
        # Pick a mode using ordinary menu navigation before arming capture.
        # Navigation keys remain assignable once capture is explicitly armed.
        replace_mode = replace_mode or self.page is self.capture_picker
        if replace_mode:
            if self.page is self.capture_picker:
                self.capture_return = self.page
        else:
            if len(self.parents) >= self.depth_limit:
                return
            self.parents.append(self.page)
        if row.capture_options is not None:
            options = row.capture_options(self.target, context)
            self.page = self._page(
                (
                    replace(row, label="Keyboard…", capture_options=None),
                    *islice(options, self.limit - 2),
                ),
                context,
                "Capture mode",
            )
            self.page.highlight = 1
            self.capture_picker = self.page
            self.capture_row = None
        else:
            self.page = self._page(
                (Entry("__capture__", row.capture_prompt, enabled=False),),
                context,
                "Cancel",
            )
            self.capture_row = row
        self.held_keys.clear()
        self.motion.clear()
        self.motion.pulse("reveal", 0.12)

    def capture_prompt(self, text):
        self.page.rows = (
            self.page.rows[0],
            replace(self.page.rows[1], label=text[:64]),
            *self.page.rows[2:],
        )

    def choose(self, index, context):
        if not self.refresh(context) or not 0 <= index < len(self.page.rows):
            return
        self.hide_tip()
        row = self.page.rows[index]
        if not self.page.available[index]:
            return
        if row.key == "__back__":
            self.back()
            return
        try:
            if row.field is not None:
                from .context_edit import Editor

                self.editor = Editor(row, index, self.target, context)
                self.page.highlight = index
                self.motion.pulse(("row", index), 0.12)
            elif row.capture is not None:
                self.start_capture(row, context)
            elif row.children is not None:
                if len(self.parents) >= self.depth_limit:
                    return
                old_anchor = self.anchor
                self.anchor = (self.page.rect[0] + 12, self.page.rect[1] + 34)
                child = self._page(
                    row.children(self.target, context),
                    context,
                    row.label,
                    max(164, self.page.rect[2] - 12),
                )
                self.anchor = old_anchor
                self.parents.append(self.page)
                self.page = child
                self.motion.clear()
                self.motion.pulse("reveal", 0.12)
            elif row.action is not None:
                # Close before invoking arbitrary host code; validate once more.
                if not self.valid(context) or not self._enabled(row, context):
                    self.close()
                    return
                self.close()
                row.action(self.target, context)
        except Exception as error:
            self.close()
            self._error(error)

    def event(self, event, x, y, context=None):
        if event.type.startswith("TIMER"):
            return False
        if not self.refresh(context):
            return False
        kind, press = event.type, event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind != "MOUSEMOVE":
            self.hide_tip()
        over = inside(self.page.rect, x, y)
        if kind == "WINDOW_DEACTIVATE":
            self.close()
            return False
        self.motion.input(event, x, y)
        if event.value == "RELEASE":
            self.held_keys.discard(kind)
        elif press and len(self.held_keys) < 64:
            self.held_keys.add(kind)
        if self.editor is not None:
            editor = self.editor
            if not self._enabled(editor.row, context):
                self.editor = None
                return True
            if press and kind in {"ESC", "RIGHTMOUSE"}:
                self.editor = None
                self.error = None
                return inside(self.clip, x, y) if kind == "RIGHTMOUSE" else True
            if press and kind in {"RET", "NUMPAD_ENTER"}:
                try:
                    if editor.state != editor.row.field.state(self.target, context):
                        raise ValueError(
                            "Field settings changed; cancel and reopen the field"
                        )
                    editor.row.field.apply(
                        editor.text.text, editor.original, self.target, context
                    )
                    self.editor = None
                    self.error = None
                    self.refresh(context)
                except Exception as error:
                    editor.error = str(error)
                    self._error(error)
                    self.tip_pending = (
                        editor.index,
                        str(error),
                        x,
                        y,
                        self.motion.clock(),
                    )
                    self.reveal_tip(context)
                return True
            row_rect = next(
                (r for i, r, _ in self.visible_rows() if i == editor.index), None
            )
            if kind == "LEFTMOUSE" and event.value == "RELEASE":
                editor.dragging = False
                return inside(self.clip, x, y)
            if press and kind == "LEFTMOUSE" and row_rect and inside(row_rect, x, y):
                editor.pointer(event, x, row_rect, self.measure)
                return True
            if kind == "MOUSEMOVE" and editor.dragging and row_rect:
                editor.pointer(event, x, row_rect, self.measure)
                return True
            if press and kind == "LEFTMOUSE":
                self.editor = None
                if not over:
                    self.close()
                return inside(self.clip, x, y)
            if kind == "MOUSEMOVE":
                return inside(self.clip, x, y)
            editor.event(event, getattr(context, "window_manager", None))
            return True
        if self.capture_row is not None:
            hit = next((i for i, r, _ in self.visible_rows() if inside(r, x, y)), None)
            if press and kind in {"ESC", "RIGHTMOUSE"}:
                if kind == "RIGHTMOUSE" and not inside(self.clip, x, y):
                    self.close()
                    return False
                self.back()
                return True
            if kind == "MOUSEMOVE":
                if hit is not None:
                    self.page.highlight = hit
                self.hover_tip(hit, x, y, context)
                return over
            if kind == "LEFTMOUSE" and press:
                if hit == 0:
                    self.back()
                    return True
                if (
                    hit is not None
                    and self.page.rows[hit].capture
                    and self.page.available[hit]
                ):
                    try:
                        self.start_capture(
                            self.page.rows[hit], context, replace_mode=True
                        )
                    except Exception as error:
                        self.close()
                        self._error(error)
                    return True
                if not self.capture_row.capture_mouse:
                    if not over:
                        self.close()
                    return inside(self.clip, x, y)
            if not inside(self.clip, x, y) and kind.endswith("MOUSE"):
                self.close()
                return False
            try:
                row = self.capture_row
                if not self._enabled(row, context):
                    self.close()
                else:
                    outcome = row.capture(self.target, context, event)
                    if outcome is True:
                        self.error = None
                        self.close()
                    elif isinstance(outcome, str):
                        self.capture_prompt(outcome)
            except Exception as error:
                self._error(error)
                self.capture_prompt(str(error))
            return True
        if self.search_event(event, x, y, context):
            return True
        if press and kind in {"ESC", "LEFT_ARROW"} and self.back():
            return True
        if press and kind in {"ESC", "RIGHTMOUSE"}:
            self.close()
            return inside(self.clip, x, y) if kind == "RIGHTMOUSE" else True
        if press:
            for i, row in enumerate(self.page.rows):
                if self.page.available[i] and any(
                    s.matches(event, self.held_keys) for s in row.bindings
                ):
                    self.choose(i, context)
                    return True
        if kind == "LEFTMOUSE" and press and not over:
            for depth in reversed(range(len(self.parents))):
                if inside(self.parents[depth].rect, x, y):
                    self.page = self.parents[depth]
                    del self.parents[depth:]
                    self.motion.clear()
                    self.motion.pulse("reveal", 0.12)
                    return True
        hit = next((i for i, r, _ in self.visible_rows() if inside(r, x, y)), None)
        if kind == "LEFTMOUSE" and press:
            if hit is not None:
                self.choose(hit, context)
            elif not over:
                self.close()
            return inside(self.clip, x, y)
        if press and kind in {"RET", "NUMPAD_ENTER", "RIGHT_ARROW"}:
            self.choose(self.page.highlight, context)
            return True
        if (
            press
            and kind
            in {"UP_ARROW", "DOWN_ARROW", "HOME", "END", "PAGE_UP", "PAGE_DOWN"}
        ) or (over and kind in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"}):
            delta = -1 if kind in {"UP_ARROW", "WHEELUPMOUSE"} else 1
            if kind == "TRACKPADPAN":
                delta = (
                    -1
                    if getattr(event, "mouse_y", 0) > getattr(event, "mouse_prev_y", 0)
                    else 1
                )
            if kind.startswith("PAGE_"):
                delta = (-1 if kind == "PAGE_UP" else 1) * self.capacity
            p = self.page
            p.highlight = (
                0
                if kind == "HOME"
                else len(p.rows) - 1
                if kind == "END"
                else max(0, min(len(p.rows) - 1, p.highlight + delta))
            )
            step = -1 if kind in {"END", "UP_ARROW", "PAGE_UP", "WHEELUPMOUSE"} else 1
            while 0 <= p.highlight < len(p.rows) and p.rows[p.highlight].heading:
                p.highlight += step
            if not 0 <= p.highlight < len(p.rows):
                p.highlight = max(0, min(len(p.rows) - 1, p.highlight))
                while 0 <= p.highlight < len(p.rows) and p.rows[p.highlight].heading:
                    p.highlight -= step
                p.highlight = max(0, min(len(p.rows) - 1, p.highlight))
            self.reveal()
            return True
        if kind == "MOUSEMOVE":
            self.hover_tip(hit, x, y, context)
            if hit is not None:
                self.page.highlight = hit
            return over
        return over


def default_entries(target, context):
    """RNA actions where an adapter exists; generic values only expose real copy."""
    binding = target.binding
    source = getattr(binding, "context", None)
    if source is not None:
        return source.entries(target, context)
    getter = target.value or (binding.read if binding is not None else None)
    if getter is None or context is None or not hasattr(context, "window_manager"):
        return ()

    def copy(target, context):
        context.window_manager.clipboard = repr(getter())

    return (Entry("COPY_VALUE", "Copy Value", copy, icon="COPYDOWN"),)
