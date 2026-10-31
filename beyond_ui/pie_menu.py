"""Bounded marking menus using the existing owner, glass, theme and motion path.

Geometry is prepared once in host logical units. No Blender import, timer,
pointer polling, GPU resources or binding reads in the layout/hit-test engine.
"""

from math import atan2, pi, hypot, isfinite, sqrt
from time import monotonic
from contextlib import contextmanager, nullcontext
from .pie_layout import Slots
from .pie_timing import PieSettings
from .context_menu import Menu, inside

# Blender construction order: W, E, S, N, NW, NE, SW, SE. Canvas Y grows down.
DIRECTIONS = ((-1, 0), (1, 0), (0, 1), (0, -1), (-1, -1), (1, -1), (-1, 1), (1, 1))
SECTORS = (1, 7, 2, 6, 0, 4, 3, 5)
KEYS = dict(
    zip(
        (
            "NUMPAD_4",
            "NUMPAD_6",
            "NUMPAD_2",
            "NUMPAD_8",
            "NUMPAD_7",
            "NUMPAD_9",
            "NUMPAD_1",
            "NUMPAD_3",
        ),
        range(8),
    )
)


def sector(origin, x, y, dead_zone=16.0):
    dx, dy = x - origin[0], y - origin[1]
    if hypot(dx, dy) <= dead_zone:
        return None
    return SECTORS[int((atan2(dy, dx) + pi / 8) // (pi / 4)) % 8]


KEYS.update(
    dict(
        zip(("FOUR", "SIX", "TWO", "EIGHT", "SEVEN", "NINE", "ONE", "THREE"), range(8))
    )
)


class PieMenu(Menu):
    """Up to eight slots. Small clips explicitly use the ordinary custom list.

    ``trigger`` is the already-held invoking key/button, or None for click mode.
    Releasing in the dead zone leaves click mode open; releasing over a direction
    executes once. Submenus and exact-row context actions use normal menu pages.
    """

    def __init__(
        self,
        target,
        rows,
        anchor,
        clip,
        *,
        trigger=None,
        dead_zone=None,
        settings=None,
        clock=monotonic,
        navigation_back=False,
        title="",
        icon="NONE",
        **kwargs,
    ):
        self.settings = settings or PieSettings.from_context(kwargs.get("context"))
        self.root = None
        self.rectangles = ()
        self.layout_mode = "PIE"
        self.trigger = trigger
        self.dead_zone = (
            self.settings.threshold if dead_zone is None else float(dead_zone)
        )
        if not isfinite(self.dead_zone) or not 0 <= self.dead_zone <= 1000:
            raise ValueError("Pie dead zone must be finite and between 0 and 1000")
        measure = kwargs.get("measure") or (lambda text, size: len(text) * size * 0.6)
        center_width = (
            min(240, max(84, measure(title, 12) + (40 if icon != "NONE" else 24)))
            if title
            else 84
        )
        self.slots = Slots(rows, measure, self.row_height)
        kwargs["row_limit"] = 4096
        super().__init__(target, self.slots.rows, anchor, clip, **kwargs)
        self.motion.clock = clock
        if self.settings.reduce_motion:
            self.motion.settings.enabled = False
        self.started = clock()
        self.event_context = kwargs.get("context")
        self.dragged = False
        self.pointer = tuple(anchor)
        self.confirm_pending = None
        self.pulls = {}
        self.proximity = {}
        self.root = self.page
        self.origin = tuple(self.anchor)
        self.center = self.origin
        self.root.highlight = -1
        cx, cy, cw, ch = clip
        sizes = [self.slots.sizes[n] for n in self.slots.roots]
        sizes = [(w + 2 * 4.0, h + 2 * 4.0) for w, h in sizes]
        vectors = tuple(
            (vx / hypot(vx, vy), vy / hypot(vx, vy))
            for vx, vy in DIRECTIONS[: len(sizes)]
        )
        gap = max(18.0, self.dead_zone * 2)
        radius = self.settings.radius
        # A shared circular radius grows only enough to keep natural rectangles
        # separated. Solve each pair once at invocation, never during painting.
        for i, ((vx, vy), (w, h)) in enumerate(zip(vectors, sizes)):
            radius = max(
                radius,
                min(
                    (
                        w / 2
                        + (
                            center_width / 2 + 4
                            if navigation_back or title
                            else self.dead_zone + 4
                        )
                    )
                    / abs(vx)
                    if vx
                    else float("inf"),
                    (h / 2 + (20 if navigation_back or title else self.dead_zone + 4))
                    / abs(vy)
                    if vy
                    else float("inf"),
                ),
            )
            for (ux, uy), (ow, oh) in zip(vectors[:i], sizes[:i]):
                radius = max(
                    radius,
                    min(
                        ((w + ow) / 2 + gap) / abs(vx - ux)
                        if vx != ux
                        else float("inf"),
                        ((h + oh) / 2 + gap) / abs(vy - uy)
                        if vy != uy
                        else float("inf"),
                    ),
                )
        self.placement_radius = radius
        relative = tuple(
            (vx * radius - w / 2, vy * radius - h / 2, w, h)
            for (vx, vy), (w, h) in zip(vectors, sizes)
        )
        left = min(r[0] for r in relative)
        top = min(r[1] for r in relative)
        right = max(r[0] + r[2] for r in relative)
        bottom = max(r[1] + r[3] for r in relative)
        if navigation_back or title:
            left, top = min(left, -center_width / 2), min(top, -15.5)
            right, bottom = max(right, center_width / 2), max(bottom, 15.5)
        total_w, total_h = right - left, bottom - top
        if total_w > cw or total_h > ch:
            self.layout_mode = "LIST_FALLBACK"
            self.root.highlight = 0
            self.trigger = None
            if navigation_back:
                self.page = self._page(self.slots.rows, kwargs.get("context"), "Back")
                self.root = self.page
            elif title:
                from .context_menu import Entry

                self.page = self._page(
                    (
                        Entry("__pie_title__", title, heading=True, icon=icon),
                        *self.slots.rows,
                    ),
                    kwargs.get("context"),
                )
                self.root = self.page
            self.initialize(kwargs.get("context"))
            return
        x = max(cx - left, min(anchor[0], cx + cw - right))
        y = max(cy - top, min(anchor[1], cy + ch - bottom))
        self.center = (x, y)
        self.root.rect = (x + left, y + top, total_w, total_h)
        self.rectangles = tuple((x + a, y + b, w, h) for a, b, w, h in relative)
        self.leaf_slots = {}
        self.slot_leaves = {}
        self.surface_slots = {}
        for slot, (node, rect) in enumerate(zip(self.slots.roots, self.rectangles)):
            x, y, w, h = rect
            start_box = len(self.slots.boxes)
            self.slots.arrange(
                node,
                (
                    x + 4.0,
                    y + 4.0,
                    w - 2 * 4.0,
                    h - 2 * 4.0,
                ),
            )
            for leaf in self.slots.leaves(node):
                self.leaf_slots[leaf] = slot
            self.slot_leaves[slot] = self.slots.leaves(node)
            if any(self.root.rows[i].label for i in self.slots.leaves(node)):
                self.surface_slots[rect] = slot
                for box in self.slots.boxes[start_box:]:
                    self.surface_slots[box] = slot
        self.row_rectangles = dict(self.slots.rectangles)
        self.root.search = None
        if navigation_back or title:
            from .context_menu import Entry

            index = len(self.root.rows)
            self.root.rows += (
                Entry("__back__", "Back", icon="‹")
                if navigation_back
                else Entry("__pie_title__", title, heading=True, icon=icon),
            )
            self.root.available += (bool(navigation_back),)
            self.root.checked += (False,)
            self.root.values += ("",)
            self.root.statuses += ("EMPTY",)
            rect = (
                self.center[0] - center_width / 2,
                self.center[1] - 15.5,
                center_width,
                31,
            )
            self.row_rectangles[index] = (
                rect[0] + 4,
                rect[1] + 4,
                center_width - 8,
                23,
            )
            self.leaf_slots[index] = None
            self.surface_slots[rect] = None

        self.initialize(kwargs.get("context"))

    def radial(self, page=None):
        return (page or self.page) is self.root and self.layout_mode == "PIE"

    def visible_rows(self, page=None):
        page = page or self.page
        if not self.radial(page):
            yield from super().visible_rows(page)
            return
        for index, rect in self.row_rectangles.items():
            row = page.rows[index]
            if row.key.endswith(":__pie_space__") or row.key == "__pie_space__":
                continue
            yield index, rect, row

    def surfaces(self, page):
        if not self.radial(page):
            return super().surfaces(page)
        return self.surface_slots

    def reveal(self):
        if not self.radial():
            super().reveal()

    def close(self):
        self.trigger = None
        self.confirm_pending = None
        self.pulls.clear()
        self.proximity.clear()
        super().close()

    def choose(self, index, context):
        self.confirm_pending = None
        super().choose(index, context)
        if self.closed or not self.radial() or self.editor is not None:
            self.trigger = None
            self.pulls.clear()
            self.proximity.clear()

    def back(self, context=None):
        self.confirm_pending = None
        self.pulls.clear()
        self.proximity.clear()
        return super().back(context)

    def open_row_context(self, index, context):
        self.trigger = None
        self.confirm_pending = None
        self.pulls.clear()
        self.proximity.clear()
        return super().open_row_context(index, context)

    def elapsed(self):
        return max(0.0, self.motion.clock() - self.started)

    def opening(self):
        if not self.motion.strength or not self.settings.animation:
            return 1.0
        factor = min(1.0, self.elapsed() / self.settings.animation)
        return 1.0 - min(1.0, self.motion.strength) * (1.0 - factor)

    def direction_origin(self):
        return self.origin if self.elapsed() <= self.settings.recenter else self.center

    def direction_leaf(self, slot):
        if slot is None or slot >= len(self.slots.roots):
            return None
        node = self.slots.roots[slot]
        # A direction into a compound slot never guesses which child to execute.
        return node if isinstance(node, int) else None

    def update_pointer(self, x, y):
        self.pointer = (x, y)
        hit = next((i for i, r, _ in self.visible_rows() if inside(r, x, y)), None)
        surface_hit = next(
            (i for i, rect in enumerate(self.rectangles) if inside(rect, x, y)), None
        )
        slot = (
            self.leaf_slots.get(hit)
            if hit is not None
            else surface_hit
            if surface_hit is not None
            else sector(self.direction_origin(), x, y, self.dead_zone)
        )
        if not inside(self.clip, x, y):
            slot = None
        distances = {}
        for number, rect in enumerate(self.rectangles):
            a, b, w, h = rect
            distance = hypot(max(a - x, 0, x - a - w), max(b - y, 0, y - b - h))
            baseline = max(
                1, hypot(a + w / 2 - self.origin[0], b + h / 2 - self.origin[1])
            )
            proximity = max(0, min(1, 1 - distance / baseline)) if number == slot else 0
            if not any(self.root.available[i] for i in self.slot_leaves[number]):
                proximity = 0.0
            distances[number] = proximity
            length = max(1, hypot(x - a - w / 2, y - b - h / 2))
            pull = (
                min(12, length * 0.12) * proximity * (x - a - w / 2) / length,
                min(12, length * 0.12) * proximity * (y - b - h / 2) / length,
            )
            # The logical petal is a stable landing zone, including compound gaps.
            # Drop the spring immediately at contact; a return spring still skews
            # an item under the pointer and stale tracks would jump on departure.
            if inside(rect, x, y):
                pull = (0.0, 0.0)
                for axis in range(2):
                    key = ("pull", number, axis)
                    self.motion.positions.pop(key, None)
                    self.motion.tracks.pop(key, None)
                for index in self.slot_leaves[number]:
                    self.motion.tracks.pop(("row", index), None)
            old = self.pulls.get(number, (0.0, 0.0))
            if old != pull and not inside(rect, x, y):
                for axis in range(2):
                    self.motion.retarget(("pull", number, axis), old[axis], pull[axis])
            self.pulls[number] = pull
        self.proximity = distances
        return hit if hit is not None else self.direction_leaf(slot)

    def pull(self, slot):
        if not self.motion.strength:
            return (0.0, 0.0)
        value = self.pulls.get(slot, (0, 0))
        return tuple(
            max(
                -18,
                min(
                    18,
                    self.motion.position(("pull", slot, axis), value[axis])
                    * self.motion.strength,
                ),
            )
            for axis in range(2)
        )

    def highlight_alpha(self, page, index):
        if not self.radial(page) or self.leaf_slots[index] is None:
            return 1.0
        return 0.15 + 0.85 * self.proximity.get(self.leaf_slots[index], 0.0)

    def surface_tint(self, page, rect, palette):
        if not self.radial(page):
            return super().surface_tint(page, rect, palette)
        alpha = self.proximity.get(self.surface_slots[rect], 0.0)
        base = super().surface_tint(page, rect, palette)
        tint = palette["selected"]
        weight = tint[3] * alpha * 0.35
        opacity = base[3] + (1 - base[3]) * weight
        rgb = (
            tuple(
                (base[i] * base[3] * (1 - weight) + tint[i] * weight) / opacity
                for i in range(3)
            )
            if opacity
            else tint[:3]
        )
        return (*rgb, opacity)

    def guide(self):
        if not self.radial() or self.pointer == self.origin:
            return None
        return (
            self.origin,
            self.pointer,
            0.15 + 0.65 * max(self.proximity.values(), default=0),
        )

    @property
    def presentation_active(self):
        return self.radial() and (
            self.opening() < 1 or any(self.pull(i) != (0, 0) for i in self.pulls)
        )

    @contextmanager
    def presentation(self, mapped):
        import gpu

        factor = self.opening() if self.radial() else 1.0
        if factor >= 1:
            yield
            return
        x, y, _, _ = mapped((*self.origin, 0, 0))
        with gpu.matrix.push_pop():
            gpu.matrix.translate((x, y, 0))
            gpu.matrix.scale((max(0.001, factor), max(0.001, factor), 1))
            gpu.matrix.translate((-x, -y, 0))
            yield

    @contextmanager
    def slot_transform(self, slot, mapped, scale):
        import gpu
        from mathutils import Matrix

        dx, dy = self.pull(slot)
        if not (dx or dy):
            yield
            return
        rect = mapped(self.rectangles[slot])
        x, y, w, h = rect
        stretch = 1 + min(0.18, hypot(dx, dy) * 0.01)
        angle = atan2(-dy, dx)
        with gpu.matrix.push_pop():
            gpu.matrix.translate((x + w / 2 + dx * scale, y + h / 2 - dy * scale, 0))
            gpu.matrix.multiply_matrix(Matrix.Rotation(angle, 4, "Z"))
            gpu.matrix.scale((stretch, 1 / stretch, 1))
            gpu.matrix.multiply_matrix(Matrix.Rotation(-angle, 4, "Z"))
            gpu.matrix.translate((-x - w / 2, -y - h / 2, 0))
            yield

    def surface_transform(self, rect, mapped, scale):
        if self.layout_mode == "PIE" and (self.radial() or self.root in self.parents):
            try:
                return self.slot_transform(self.surface_slots[rect], mapped, scale)
            except KeyError:
                pass
        return nullcontext()

    def row_motion_enabled(self, page, index):
        # Approach motion belongs to the entire petal, never a second row spring.
        return not self.radial(page)

    def row_transform(self, page, index, mapped, scale):
        return (
            self.slot_transform(self.leaf_slots[index], mapped, scale)
            if self.radial(page)
            else nullcontext()
        )

    def advance(self, context=None):
        if self.closed:
            return False
        context = context if context is not None else self.event_context
        if self.confirm_pending and self.motion.clock() > self.confirm_pending[0]:
            _, page, index, row = self.confirm_pending
            self.confirm_pending = None
            if (
                self.valid(context)
                and self.page is page
                and index < len(page.rows)
                and page.rows[index] is row
            ):
                self.choose(index, context)
            else:
                self.close()
        return not self.closed and (
            self.opening() < 1 or self.confirm_pending is not None
        )

    def event(self, event, x, y, context=None):
        self.event_context = context
        if event.type == "MOUSEMOVE":
            self.pointer = (x, y)
        if (
            self.radial()
            and self.pending_click is not None
            and event.type == "MOUSEMOVE"
        ):
            self.update_pointer(x, y)
        if (
            not self.radial()
            or self.editor is not None
            or self.pending_click is not None
        ):
            return super().event(event, x, y, context)
        if event.type.startswith("TIMER"):
            self.advance(context)
            return False
        if not self.refresh(context):
            return False
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if press and event.type in {"ESC", "RIGHTMOUSE", "APP", "F10"}:
            self.trigger = None
            self.confirm_pending = None
        if event.type == "WINDOW_DEACTIVATE":
            self.close()
            return False
        if event.type == "MOUSEMOVE" or (
            event.type == self.trigger and event.value == "RELEASE"
        ):
            self.motion.input(event, x, y)
            hit = self.update_pointer(x, y)
            self.page.highlight = hit if hit is not None else -1
            if self.trigger:
                if (
                    event.type == "MOUSEMOVE"
                    and (x - self.origin[0]) ** 2 + (y - self.origin[1]) ** 2 > 50
                ):
                    self.dragged = True
                distance = hypot(
                    x - self.direction_origin()[0], y - self.direction_origin()[1]
                )
                if event.type == self.trigger:
                    self.trigger = None
                    self.confirm_pending = None
                    if not inside(self.clip, x, y):
                        self.close()
                    elif self.elapsed() < self.settings.tap and not self.dragged:
                        pass  # A quick un-dragged tap enters click mode.
                    elif hit is not None and self.page.available[hit]:
                        self.choose(hit, context)
                    else:
                        self.close()
                elif (
                    self.settings.confirm > 0
                    and distance >= self.dead_zone + self.settings.confirm
                    and hit is not None
                    and self.page.available[hit]
                ):
                    self.confirm_pending = (
                        self.motion.clock() + 0.02,
                        self.page,
                        hit,
                        self.page.rows[hit],
                    )
                    if self.motion.wake:
                        self.motion.wake(self.motion)
                else:
                    self.confirm_pending = None
                return True
            if event.type == "MOUSEMOVE":
                self.hover_tip(hit, x, y, context)
                return inside(self.clip, x, y)
        if (
            press
            and event.type in KEYS
            and not any(
                getattr(event, k, False) for k in ("ctrl", "alt", "shift", "oskey")
            )
        ):
            if not getattr(event, "is_repeat", False):
                leaf = self.direction_leaf(KEYS[event.type])
                if leaf is not None:
                    self.choose(leaf, context)
            return True
        return super().event(event, x, y, context)
