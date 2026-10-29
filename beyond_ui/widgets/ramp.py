"""Custom gradient/stop editing with host-owned ColorRamp transactions."""

from .base import Widget, Painter, contains
from ..bindings import Edit, Binding
from ..editing import Text, number, to_display, to_linear
from ..gpu import style
from .metrics import RAMP, SIZE


class ColorRamp(Widget):
    design_font_size = 22.0
    width, height = SIZE

    def __init__(
        self,
        binding,
        *,
        evaluate=None,
        interpolation=None,
        edit_color=None,
        linear=True,
    ):
        super().__init__()
        self.binding = binding
        self.linear = linear
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
                self._position((x - RAMP["gradient"][0]) / RAMP["gradient"][2])
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self._finish()
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        points = tuple(self.binding.read())
        if contains(RAMP["handles"], x, y) and points:
            self.selected = min(
                range(len(points)), key=lambda i: abs(x - (30 + points[i][0] * 572))
            )
            self.transaction = Edit(self.binding)
            self.drag = True
            self.capturing = True
            return True
        if contains(RAMP["add"], x, y) and len(points) < 32:
            before = points
            position = 0.5
            color = self.sample(position, points)
            points = (*points, (position, color))
            self.binding.write(points)
            self.binding.commit(before, points)
            self.selected = len(points) - 1
            return True
        if contains(RAMP["remove"], x, y) and len(points) > 2:
            before = points
            points = tuple(p for i, p in enumerate(points) if i != self.selected)
            self.binding.write(points)
            self.binding.commit(before, points)
            self.selected = min(self.selected, len(points) - 1)
            return True
        if contains(RAMP["position"], x, y) and points:
            self.transaction = Edit(self.binding)
            self.field = "position"
            self.text_edit = Text(points[self.selected][0])
            self.capturing = True
            return True
        if contains(RAMP["color"], x, y) and points and self.edit_color:
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

    def display_color(self, color):
        return (
            tuple(to_display(c) for c in color[:3]) + (color[3],)
            if self.linear
            else color
        )

    def paint(self, rect, font, palette, *, backdrop=None):
        import gpu
        from array import array

        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        p.card("Color Ramp")
        points = tuple(self.binding.read())
        if not points:
            return
        selected = min(self.selected, len(points) - 1)
        interpolation = self.interpolation.read() if self.interpolation else "LINEAR"
        signature = (points, interpolation, self.linear)
        if signature != self._signature:
            pixels = array(
                "f",
                (
                    (to_linear(channel) if not self.linear and j < 3 else channel)
                    for i in range(256)
                    for j, channel in enumerate(self.sample(i / 255, points))
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
        p.surface(RAMP["mode"], "input")
        p.text(RAMP["mode"], interpolation.title(), size=24, inset=20)
        p.chevron(404, 107, 15)
        for key, label in (("add", "+"), ("remove", "−")):
            p.surface(RAMP[key], "button")
            p.icon(label, RAMP[key], 24)
        style.preview(self._textures[-1], *p.map(RAMP["gradient"]), radius=7 * p.scale)
        for i, (position, color) in enumerate(points):
            color = self.display_color(color)
            x = 30 + position * 572
            with p.deform(("stop", i), (x - 12, 287, 24, 42)):
                p.triangle(((x, 289), (x - 12, 304), (x + 12, 304)), palette["text"])
                p.triangle(((x, 292), (x - 9, 303), (x + 9, 303)), color)
                p.surface((x - 12, 303, 24, 26), color, 2, 1)
        position, color = points[selected]
        p.field(
            RAMP["position"],
            "Position",
            self.text_edit.text if self.text_edit else f"{position:.2f}",
            split=168,
        )
        p.surface(RAMP["color"])
        p.surface(RAMP["swatch"], self.display_color(color), 6, 0.7)
        p.chevron(580, 400, 14)
