"""Custom point editing and sampled curve display; evaluation stays host-owned."""

from .base import Widget, Painter, contains
from ..bindings import Edit
from ..gpu import style


class CurveMapping(Widget):
    width = 320.0
    height = 240.0
    graph = (74, 38, 176, 176)

    def __init__(self, binding, *, evaluate=None, channel=None):
        super().__init__()
        self.binding = binding
        self.evaluate = evaluate
        self.channel = channel
        self.selected = 0
        self.transaction = None
        self._signature = None
        self._samples = ()

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
        if not self.binding.valid():
            self.cancel()
            return False
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind in {"ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE"} and self.capturing:
            self.cancel()
            return True
        points = tuple(self.binding.read())
        a, b, w, h = self.graph
        if self.capturing:
            if kind == "MOUSEMOVE":
                values = list(points)
                values[self.selected] = (
                    max(0.0, min(1.0, (x - a) / w)),
                    max(0.0, min(1.0, 1 - (y - b) / h)),
                )
                self.transaction.update(tuple(values))
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self._finish()
            return True
        if kind == "DEL" and press and len(points) > 2:
            values = tuple(p for i, p in enumerate(points) if i != self.selected)
            self.binding.write(values)
            self.binding.commit(points, values)
            self.selected = min(self.selected, len(values) - 1)
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        if y < 32 and self.channel:
            old = self.channel.read()
            new = min(3, max(0, int(x / 80)))
            self.channel.write(new)
            self.channel.commit(old, new)
            return True
        if contains(self.graph, x, y):
            if event.value == "DOUBLE_CLICK":
                values = (*points, ((x - a) / w, 1 - (y - b) / h))
                self.binding.write(values)
                self.binding.commit(points, values)
                self.selected = len(points)
                return True
            if not points:
                return False
            self.selected = min(
                range(len(points)),
                key=lambda i: (a + points[i][0] * w - x) ** 2
                + (b + (1 - points[i][1]) * h - y) ** 2,
            )
            self.transaction = Edit(self.binding)
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

    def paint(self, rect, font, palette):
        p = Painter(rect, self.width, self.height, font, palette)
        points = tuple(self.binding.read())
        if not points:
            return
        channel = self.channel.read() if self.channel else 0
        for i, label in enumerate("CRGB"):
            r = (8 + i * 78, 6, 74, 24)
            p.surface(r, "tab" if i == channel else "field")
            p.text(r, label)
        p.surface(self.graph)
        a, b, w, h = self.graph
        for i in range(7):
            t = i / 6
            p.line(
                ((a + t * w, b), (a + t * w, b + h)),
                (*palette["muted"][:3], 0.3),
                0.5 * p.scale,
            )
            p.line(
                ((a, b + t * h), (a + w, b + t * h)),
                (*palette["muted"][:3], 0.3),
                0.5 * p.scale,
            )
        signature = (points, channel)
        if signature != self._signature:
            self._samples = tuple(
                (
                    a + i / 128 * w,
                    b + (1 - max(0, min(1, self._sample(i / 128, points)))) * h,
                )
                for i in range(129)
            )
            self._signature = signature
        p.line(self._samples, palette["slider_fill"], 1.5 * p.scale)
        for i, (px, py) in enumerate(points):
            x, y, rw, rh = p.map((a + px * w - 3, b + (1 - py) * h - 3, 6, 6))
            style.draw(
                x,
                y,
                rw,
                rh,
                palette["slider_fill"] if i == self.selected else palette["text"],
                mode=3,
            )
        self.selected = min(self.selected, len(points) - 1)
        px, py = points[self.selected]
        for r, text in (
            ((8, 218, 104, 22), f"X  {px:.2f}"),
            ((118, 218, 104, 22), f"Y  {py:.2f}"),
            ((228, 218, 84, 22), "Auto"),
        ):
            p.surface(r)
            p.text(r, text)
