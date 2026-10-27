"""Custom gradient/stop editing with host-owned ColorRamp transactions."""

from .base import Widget, Painter, contains
from ..bindings import Edit, Binding
from ..editing import Text, number
from ..gpu import style


class ColorRamp(Widget):
    width = 320.0
    height = 166.0

    def __init__(self, binding, *, evaluate=None, interpolation=None, edit_color=None):
        super().__init__()
        self.binding = binding
        self.evaluate = evaluate
        self.interpolation = interpolation
        self.edit_color = edit_color
        self.selected = 0
        self.transaction = None
        self.drag = False
        self._signature = None
        self._textures = []

    def cancel(self):
        if self.transaction:
            self.transaction.finish(cancel=True)
        self.transaction = None
        self.drag = False
        super().cancel()

    def _finish(self):
        if self.transaction:
            self.transaction.finish()
        self.transaction = None
        self.drag = False
        self.capturing = False

    def _position(self, position):
        points = list(self.binding.read())
        i = min(self.selected, len(points) - 1)
        points[i] = (max(0.0, min(1.0, position)), points[i][1])
        self.transaction.update(tuple(points))

    def event(self, event, x, y, *, clipboard=None):
        if not self.binding.valid():
            self.cancel()
            return False
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if self.text_edit:
            result = self.edit_text(event, clipboard=clipboard)
            if result is False:
                self.cancel()
            elif isinstance(result, str):
                try:
                    self._position(number(result))
                    self._finish()
                except ValueError:
                    self.text_edit = Text(result)
                    self.capturing = True
            return True
        if kind in {"ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE"} and self.capturing:
            self.cancel()
            return True
        if self.drag:
            if kind == "MOUSEMOVE":
                self._position((x - 8) / 304)
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self._finish()
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        points = tuple(self.binding.read())
        if contains((8, 86, 304, 30), x, y) and points:
            self.selected = min(
                range(len(points)), key=lambda i: abs(x - (8 + points[i][0] * 304))
            )
            self.transaction = Edit(self.binding)
            self.drag = True
            self.capturing = True
            return True
        if contains((238, 8, 32, 28), x, y) and len(points) < 32:
            before = points
            position = 0.5
            color = self.sample(position, points)
            points = (*points, (position, color))
            self.binding.write(points)
            self.binding.commit(before, points)
            self.selected = len(points) - 1
            return True
        if contains((280, 8, 32, 28), x, y) and len(points) > 2:
            before = points
            points = tuple(p for i, p in enumerate(points) if i != self.selected)
            self.binding.write(points)
            self.binding.commit(before, points)
            self.selected = min(self.selected, len(points) - 1)
            return True
        if contains((8, 126, 164, 30), x, y) and points:
            self.transaction = Edit(self.binding)
            self.field = "position"
            self.text_edit = Text(points[self.selected][0])
            self.capturing = True
            return True
        if contains((184, 126, 128, 30), x, y) and points and self.edit_color:
            index = self.selected

            def get():
                return self.binding.read()[index][1]

            def set_value(color):
                points = list(self.binding.read())
                points[index] = (points[index][0], tuple(color))
                self.binding.write(tuple(points))

            self.edit_color(
                Binding(get, set_value, self.binding.valid, self.binding.commit)
            )
            return True
        return False

    def sample(self, x, points):
        if self.evaluate:
            return tuple(self.evaluate(x))
        ordered = sorted(points, key=lambda p: p[0])
        if x <= ordered[0][0]:
            return ordered[0][1]
        for (a, ac), (b, bc) in zip(ordered, ordered[1:]):
            if x <= b:
                t = (x - a) / max(1e-9, b - a)
                return tuple(v + (z - v) * t for v, z in zip(ac, bc))
        return ordered[-1][1]

    def paint(self, rect, font, palette):
        import gpu
        from array import array

        p = Painter(rect, self.width, self.height, font, palette)
        points = tuple(self.binding.read())
        if not points:
            return
        self.selected = min(self.selected, len(points) - 1)
        interpolation = self.interpolation.read() if self.interpolation else "LINEAR"
        signature = (points, interpolation)
        if signature != self._signature:
            pixels = array(
                "f",
                (
                    channel
                    for i in range(256)
                    for channel in self.sample(i / 255, points)
                ),
            )
            texture = gpu.types.GPUTexture(
                (256, 1),
                format="RGBA16F",
                data=gpu.types.Buffer("FLOAT", len(pixels), pixels),
            )
            self._textures.append(texture)
            self._textures = self._textures[-3:]
            self._signature = signature
        p.surface((8, 8, 218, 28))
        p.text((8, 8, 218, 28), interpolation.title())
        for r, label in (((238, 8, 32, 28), "+"), ((280, 8, 32, 28), "−")):
            p.surface(r)
            p.text(r, label, size=16)
        style.preview(self._textures[-1], *p.map((8, 48, 304, 64)), radius=4 * p.scale)
        for i, (position, color) in enumerate(points):
            a, b, w, h = p.map((8 + position * 304 - 5, 113, 10, 14))
            style.draw(a, b, w, h, color, radius=1 * p.scale, border=p.scale)
            p.line(
                (
                    (8 + position * 304 - 5, 113),
                    (8 + position * 304, 107),
                    (8 + position * 304 + 5, 113),
                ),
                palette["text"],
                p.scale,
            )
        position, color = points[self.selected]
        p.surface((8, 134, 164, 28))
        p.text(
            (8, 134, 164, 28),
            "Position  "
            + (self.text_edit.text if self.text_edit else f"{position:.2f}"),
        )
        p.surface((184, 134, 128, 28))
        style.draw(*p.map((188, 138, 104, 20)), color, radius=3 * p.scale)
