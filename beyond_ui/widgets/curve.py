"""Custom point editing and sampled curve display; evaluation stays host-owned."""

from .base import Widget, Painter, contains
from ..bindings import Edit
from .metrics import CURVE, SIZE
from ..editing import Text, number


class CurveMapping(Widget):
    design_font_size = 22.0
    width, height = SIZE
    graph = CURVE["graph"]

    def __init__(self, binding, *, evaluate=None, channel=None, brush=False):
        super().__init__()
        self.binding = binding
        self.brush = brush
        self.evaluate = evaluate
        self.channel = channel
        self.selected = 0
        self.transaction = None
        self._signature = None
        self._samples = ()

    def _edit(self):
        factory = getattr(self.binding, "begin_edit", None)
        return factory() if factory else Edit(self.binding)

    def cancel(self):
        if self.transaction:
            self.transaction.finish(cancel=True)
        self.transaction = None
        super().cancel()

    def _finish(self):
        if self.transaction:
            self.transaction.finish()
        self.transaction = None
        self.capturing = False

    def event(self, event, x, y, *, clipboard=None):
        if (
            not self.capturing
            and hasattr(self.binding, "refresh")
            and not self.binding.valid()
        ):
            self.binding.refresh()
        if not self.binding.valid():
            self.cancel()
            return False
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind in {"ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE"} and self.capturing:
            self.cancel()
            return True
        points = tuple(self.binding.read())
        self.selected = max(0, min(self.selected, len(points) - 1))
        if self.text_edit:
            result = self.edit_text(event, clipboard=clipboard)
            if result is False:
                self.cancel()
            elif isinstance(result, str):
                try:
                    values = list(points)
                    point = list(values[self.selected])
                    point[self.field] = max(0.0, min(1.0, number(result)))
                    values[self.selected] = tuple(point)
                    self.transaction.update(tuple(values))
                    self._finish()
                except ValueError:
                    self.text_edit = Text(result)
                    self.capturing = True
            return True
        a, b, w, h = self.graph
        if self.capturing:
            if kind == "MOUSEMOVE":
                values = list(points)
                values[self.selected] = (
                    max(0.0, min(1.0, (x - a) / w)),
                    max(0.0, min(1.0, 1 - (y - b) / h)),
                )
                moved = values[self.selected]
                self.transaction.update(tuple(values))
                self.selected = min(
                    range(len(values)),
                    key=lambda i: sum(
                        (a - b) ** 2 for a, b in zip(self.binding.read()[i], moved)
                    ),
                )
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self._finish()
            return True
        if press and (kind in {"DEL", "BACK_SPACE"} or
                      (kind == "LEFTMOUSE" and contains(CURVE["remove"], x, y))):
            if len(points) <= 2:
                return True
            values = tuple(p for i, p in enumerate(points) if i != self.selected)
            if hasattr(self.binding, "remove"):
                self.binding.remove(self.selected)
            else:
                edit = Edit(self.binding)
                edit.update(values)
                edit.finish()
            self.selected = min(self.selected, len(values) - 1)
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        if self.brush:
            for i, r in enumerate(CURVE["tabs"][:3]):
                if contains(r, x, y) and points:
                    edit = Edit(self.binding.handle(self.selected))
                    edit.update(("AUTO", "VECTOR", "AUTO_CLAMPED")[i])
                    edit.finish()
                    return True
        for i, r in enumerate(CURVE["tabs"] if not self.brush else ()):
            if contains(r, x, y) and self.channel:
                old = self.channel.read()
                self.channel.write(i)
                self.channel.commit(old, i)
                return True
        for i, r in enumerate(CURVE["fields"][:2]):
            if contains(r, x, y) and points:
                self.transaction = self._edit()
                self.field = i
                self.text_edit = Text(points[self.selected][i])
                self.capturing = True
                return True
        if contains(self.graph, x, y):
            if not points:
                return False
            self.selected = min(
                range(len(points)),
                key=lambda i: (a + points[i][0] * w - x) ** 2
                + (b + (1 - points[i][1]) * h - y) ** 2,
            )
            px, py = points[self.selected]
            hit = (a + px * w - x) ** 2 + (b + (1 - py) * h - y) ** 2 <= CURVE["point_hit_radius"] ** 2
            self.transaction = self._edit()
            if not hit:
                added = ((x - a) / w, 1 - (y - b) / h)
                self.transaction.update((*points, added))
                current = self.binding.read()
                self.selected = min(range(len(current)), key=lambda i:
                    sum((v - t) ** 2 for v, t in zip(current[i], added)))
            # One transaction covers insertion and drag. A double-click over
            # the just-inserted point selects it, without creating a duplicate.
            self.capturing = True
            return True
        return False

    def _sample(self, x, points):
        if self.evaluate:
            return float(self.evaluate(x))
        ordered = sorted(points)
        if x <= ordered[0][0]:
            return ordered[0][1]
        for (a, ay), (b, by) in zip(ordered, ordered[1:]):
            if x <= b:
                return ay + (by - ay) * (x - a) / max(1e-9, b - a)
        return ordered[-1][1]

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        p.card("Curve Mapping")
        if not self.binding.valid():
            p.text(self.graph, "Curve changed — move here to refresh", size=19)
            return
        points = tuple(self.binding.read())
        if not points:
            return
        channel = self.channel.read() if self.channel else 0
        modes = ("AUTO", "VECTOR", "AUTO_CLAMPED")
        labels = ("Auto", "Vector", "Clamped") if self.brush else "CRGB"
        handle = (
            self.binding.handle_value(min(self.selected, len(points) - 1))
            if self.brush
            else None
        )
        for i, (label, r) in enumerate(zip(labels, CURVE["tabs"])):
            active = handle == modes[i] if self.brush else i == channel
            p.surface(r, "tab" if active else "button")
            p.text(
                r,
                label,
                role="selected_text" if active else "text",
                size=19,
                align="center",
            )
        p.surface(CURVE["remove"], "button")
        p.text(CURVE["remove"], "−", align="center", size=24,
               role="text" if len(points) > 2 else "muted")
        p.surface(self.graph, "graph", 7, 1.4)
        a, b, w, h = self.graph
        for major in (False, True):
            lines = []
            for i in range(1, 6):
                if (i == 3) != major:
                    continue
                t = i / 6
                lines.extend(
                    (
                        ((a + t * w, b + 2), (a + t * w, b + h - 2)),
                        ((a + 2, b + t * h), (a + w - 2, b + t * h)),
                    )
                )
            p.lines(lines, palette["grid_major" if major else "grid_minor"], p.scale)
        signature = (
            points,
            channel,
            self.binding.revision() if hasattr(self.binding, "revision") else None,
        )
        if signature != self._signature:
            min_x = min(pt[0] for pt in points)
            span = max(pt[0] for pt in points) - min_x
            self._samples = tuple(
                (
                    a + (min_x + i / 256 * span) * w,
                    b
                    + (1 - max(0, min(1, self._sample(min_x + i / 256 * span, points))))
                    * h,
                )
                for i in range(257)
            )
            self._signature = signature
        p.line(self._samples, palette["curve"], 2.2 * p.scale)
        for i, (px, py) in enumerate(points):
            pos = (a + px * w, b + (1 - py) * h)
            p.circle(
                pos,
                9 if i == self.selected else 7,
                palette["point_border"],
                motion_key=("point", i),
            )
            p.circle(
                pos,
                8 if i == self.selected else 6.4,
                palette["point_selected"] if i == self.selected else palette["point"],
                0.6,
                motion_key=("point", i),
            )
        index = min(self.selected, len(points) - 1)
        for i, label in enumerate(("X", "Y")):
            value = (
                self.text_edit.text
                if self.text_edit and self.field == i
                else f"{points[index][i]:.2f}"
            )
            p.field(CURVE["fields"][i], label, value, split=54)
        if not self.brush:
            p.surface(CURVE["fields"][2])
        label = handle.replace("AUTO_CLAMPED", "Clamped").title() if handle else "Auto"
        p.text(CURVE["fields"][2], label, inset=18)
        if not self.brush:
            p.chevron(583, 432, 14)
