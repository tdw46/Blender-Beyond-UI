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

    def matches(self, event):
        return (
            event.value == "PRESS"
            and event.type == self.type
            and self.key_modifier == "NONE"
            and (
                self.any
                or all(
                    getattr(event, name, False) == getattr(self, name)
                    for name in ("shift", "ctrl", "alt", "oskey")
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
    capture: object = None  # (target, context, event) -> True on accepted key


@dataclass
class Page:
    rows: tuple
    available: tuple
    rect: tuple
    highlight: int = 0
    offset: int = 0
    title: str = ""


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
    ):
        self.target, self.anchor, self.clip = target, anchor, clip
        self.scope, self.scope_id = scope, scope(context)
        self.measure = measure or (lambda text, size: len(text) * size * 0.6)
        self.on_error = on_error or (lambda error: None)
        self.motion = Motion()
        self.parents = []
        self.capture_row = None
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
        )
        x, y = self.anchor
        rect = (
            max(cx, min(x, cx + cw - width)),
            max(cy, min(y, cy + ch - height)),
            width,
            height,
        )
        return Page(rows, available, rect, title=title)

    def _enabled(self, row, context):
        try:
            return bool(
                row.enabled(self.target, context)
                if callable(row.enabled)
                else row.enabled
            )
        except Exception as error:
            self._error(error)
            return False

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
        return True

    @property
    def capacity(self):
        return max(
            1, int(max(0, self.page.rect[3] - 2 * self.padding) // self.row_height)
        )

    def visible_rows(self, page=None):
        p = page or self.page
        a, b, w, h = p.rect
        top = b + self.padding
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
        self.capture_row = None

    def back(self):
        if not self.parents:
            return False
        self.hide_tip()
        self.capture_row = None
        self.page = self.parents.pop()
        self.motion.clear()
        self.motion.pulse("reveal", 0.12)
        return True

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
            if row.capture is not None:
                if len(self.parents) >= self.depth_limit:
                    return
                self.parents.append(self.page)
                self.page = self._page(
                    (Entry("__capture__", "Press a key…", enabled=False),),
                    context,
                    "Cancel",
                )
                self.capture_row = row
                self.motion.clear()
                self.motion.pulse("reveal", 0.12)
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
        if self.capture_row is not None:
            if press and kind in {"ESC", "RIGHTMOUSE"}:
                self.back()
                return True
            if kind == "LEFTMOUSE" and press:
                if over:
                    self.back()
                else:
                    self.close()
                return inside(self.clip, x, y)
            if press:
                try:
                    row = self.capture_row
                    if not self._enabled(row, context):
                        self.close()
                    elif row.capture(self.target, context, event):
                        self.close()
                except Exception as error:
                    self._error(error)
                    # Keep capture active for a different key after a conflict.
                    self.page.rows = (
                        self.page.rows[0],
                        Entry("__capture__", str(error)[:48], enabled=False),
                    )
            return True
        if press and kind in {"ESC", "LEFT_ARROW"} and self.back():
            return True
        if press and kind in {"ESC", "RIGHTMOUSE"}:
            self.close()
            return inside(self.clip, x, y) if kind == "RIGHTMOUSE" else True
        self.motion.input(event, x, y)
        if press:
            for i, row in enumerate(self.page.rows):
                if self.page.available[i] and any(
                    s.matches(event) for s in row.bindings
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
