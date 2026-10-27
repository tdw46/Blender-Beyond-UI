"""Custom SV/hue, RGB/HSV fields, alpha and hexadecimal color editing."""

from .base import Widget, Painter, contains
from ..bindings import Edit
from ..editing import (
    Text,
    number,
    color_hsv,
    color_rgb,
    color_hex,
    parse_color_hex,
    to_display,
    to_linear,
)
from ..gpu import style


class ColorPicker(Widget):
    width = 320.0
    height = 240.0
    sv = (8, 40, 176, 176)
    hue = (8, 222, 176, 14)

    def __init__(self, binding, *, linear=True, eyedropper=None):
        super().__init__()
        self.binding = binding
        self.linear = linear
        self.eyedropper = eyedropper
        self.mode = "RGB"
        self.hue_value = 0.0
        self.transaction = None
        self.drag = None

    def cancel(self):
        if self.transaction:
            self.transaction.finish(cancel=True)
        self.transaction = None
        self.drag = None
        super().cancel()

    def _begin(self):
        if self.transaction is None:
            self.transaction = Edit(self.binding)
        self.capturing = True

    def _finish(self):
        if self.transaction:
            self.transaction.finish()
        self.transaction = None
        self.drag = None
        self.capturing = False

    def _rgb(self, hsv):
        self.hue_value = hsv[0]
        current = self.binding.read()
        rgb = color_rgb(hsv, self.linear)
        self.transaction.update(rgb + ((current[3],) if len(current) > 3 else ()))

    def _move(self, x, y):
        value = self.binding.read()
        h, s, v = color_hsv(value, self.linear, self.hue_value)
        if self.drag == "sv":
            a, b, w, d = self.sv
            self._rgb(
                (
                    h,
                    max(0.0, min(1.0, (x - a) / w)),
                    max(0.0, min(1.0, 1 - (y - b) / d)),
                )
            )
        elif self.drag == "hue":
            a, b, w, d = self.hue
            self._rgb((max(0.0, min(1.0, (x - a) / w)), s, v))
        elif self.drag == "alpha" and len(value) > 3:
            self.transaction.update((*value[:3], max(0.0, min(1.0, (x - 196) / 116))))

    def event(self, event, x, y, *, clipboard=None):
        if not self.binding.valid():
            self.cancel()
            return False
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        kind = event.type
        if self.text_edit is not None:
            field = self.field
            result = self.edit_text(event, clipboard=clipboard)
            if result is False:
                self.cancel()
            elif isinstance(result, str):
                try:
                    current = self.binding.read()
                    if field == "hex":
                        value = parse_color_hex(result, current, self.linear)
                    elif field == 3:
                        value = (*current[:3], max(0.0, min(1.0, number(result))))
                    else:
                        channels = list(
                            color_hsv(current, self.linear, self.hue_value)
                            if self.mode == "HSV"
                            else tuple(to_display(c) for c in current[:3])
                            if self.linear
                            else current[:3]
                        )
                        channels[field] = number(result)
                        rgb = (
                            color_rgb(channels, self.linear)
                            if self.mode == "HSV"
                            else tuple(to_linear(c) for c in channels)
                            if self.linear
                            else tuple(channels)
                        )
                        value = rgb + ((current[3],) if len(current) > 3 else ())
                    self.transaction.update(value)
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
                self._move(x, y)
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self._finish()
            return True
        if kind != "LEFTMOUSE" or not press:
            return False
        if y < 32:
            self.mode = "RGB" if x < 160 else "HSV"
            return True
        for name, rect in (
            ("sv", self.sv),
            ("hue", self.hue),
            ("alpha", (196, 178, 116, 16)),
        ):
            if contains(rect, x, y):
                self._begin()
                self.drag = name
                self._move(x, y)
                return True
        current = self.binding.read()
        for i in range(4 if len(current) > 3 else 3):
            if contains((196, 40 + i * 34, 116, 28), x, y):
                channels = (
                    color_hsv(current, self.linear, self.hue_value)
                    if self.mode == "HSV"
                    else tuple(to_display(c) for c in current[:3])
                    if self.linear
                    else current[:3]
                )
                self._begin()
                self.field = i
                self.text_edit = Text(current[3] if i == 3 else channels[i])
                return True
        if contains((196, 208, 88, 28), x, y):
            self._begin()
            self.field = "hex"
            self.text_edit = Text(color_hex(current, self.linear))
            return True
        if contains((288, 208, 24, 28), x, y) and self.eyedropper:
            self.eyedropper(self.binding)
            return True
        return False

    def paint(self, rect, font, palette):
        p = Painter(rect, self.width, self.height, font, palette)
        value = self.binding.read()
        h, s, v = color_hsv(value, self.linear, self.hue_value)
        for i, label in enumerate(("RGB", "HSV")):
            r = (8 + i * 156, 6, 148, 26)
            p.surface(r, "tab" if self.mode == label else "field")
            p.text(r, label)
        style.draw(*p.map(self.sv), (1, 1, 1, 1), radius=4 * p.scale, mode=1, hue=h)
        style.draw(*p.map(self.hue), (1, 1, 1, 1), radius=3 * p.scale, mode=2)
        a, b, w, d = p.map(self.sv)
        style.picker_marker(
            a + s * w, b + v * d, 5 * p.scale, (1, 1, 1, 1), scale=p.scale
        )
        a, b, w, d = p.map(self.hue)
        style.draw(
            a + h * w - 2 * p.scale,
            b - 1 * p.scale,
            4 * p.scale,
            d + 2 * p.scale,
            palette["text"],
            radius=1 * p.scale,
        )
        channels = (
            color_hsv(value, self.linear, self.hue_value)
            if self.mode == "HSV"
            else tuple(to_display(c) for c in value[:3])
            if self.linear
            else value[:3]
        )
        labels = ("H", "S", "V") if self.mode == "HSV" else ("R", "G", "B")
        for i, (label, v) in enumerate(zip(labels, channels)):
            r = (196, 40 + i * 34, 116, 28)
            p.surface(r)
            txt = (
                self.text_edit.text
                if self.text_edit and self.field == i
                else f"{v:.2f}"
            )
            p.text(r, f"{label}   {txt}")
        if len(value) > 3:
            r = (196, 142, 116, 28)
            p.surface(r)
            p.text(
                r,
                "Alpha  "
                + (
                    self.text_edit.text
                    if self.text_edit and self.field == 3
                    else f"{value[3]:.2f}"
                ),
            )
            p.surface((196, 178, 116, 8), "slider_track", 4)
            p.surface((196, 178, 116 * max(0, min(1, value[3])), 8), "slider_fill", 4)
        r = (196, 208, 88, 28)
        p.surface(r)
        p.text(
            r,
            self.text_edit.text
            if self.text_edit and self.field == "hex"
            else color_hex(value, self.linear),
        )
        a, b, w, d = p.map((288, 208, 24, 28))
        p.surface((288, 208, 24, 28))
        style.icon(
            "eyedropper",
            a + w / 2,
            b + d / 2,
            16 * p.scale,
            palette["text"] if self.eyedropper else palette["muted"],
        )
