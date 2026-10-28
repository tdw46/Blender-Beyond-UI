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
from ..gpu import style, skin
from .metrics import COLOR, SIZE


class ColorPicker(Widget):
    width, height = SIZE
    sv = COLOR["sv"]
    hue = COLOR["hue"]

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
            self.transaction.update(
                (
                    *value[:3],
                    max(
                        0.0,
                        min(
                            1.0, (x - COLOR["alpha_track"][0]) / COLOR["alpha_track"][2]
                        ),
                    ),
                )
            )

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
        for mode, r in zip(("RGB", "HSV"), COLOR["tabs"]):
            if contains(r, x, y):
                self.mode = mode
                return True
        for name, rect in (
            ("sv", self.sv),
            ("hue", self.hue),
            ("alpha", COLOR["alpha_track"]),
        ):
            if contains(rect, x, y):
                self._begin()
                self.drag = name
                self._move(x, y)
                return True
        current = self.binding.read()
        for i in range(4 if len(current) > 3 else 3):
            if contains((COLOR["fields"][i] if i < 3 else (374, 294, 230, 48)), x, y):
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
        if contains(COLOR["hex"], x, y):
            self._begin()
            self.field = "hex"
            self.text_edit = Text(color_hex(current, self.linear))
            return True
        if contains(COLOR["eyedropper"], x, y) and self.eyedropper:
            self.eyedropper(self.binding)
            return True
        return False

    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(
            rect, self.width, self.height, font, palette, backdrop, motion=self.motion
        )
        p.card("Color Picker")
        value = self.binding.read()
        h, s, v = color_hsv(value, self.linear, self.hue_value)
        for label, r in zip(("RGB", "HSV"), COLOR["tabs"]):
            p.surface(r, "tab" if self.mode == label else "button")
            p.text(
                r,
                label,
                role="selected_text" if self.mode == label else "text",
                size=19,
                align="center",
            )
        skin.draw(p.map(self.sv), (1, 1, 1, 1), radius=6 * p.scale, mode=1, hue=h)
        skin.draw(p.map(self.hue), (1, 1, 1, 1), radius=6 * p.scale, mode=2)
        a, b, w, d = p.map(self.sv)
        with p.deform(
            "sv",
            (
                self.sv[0] + s * self.sv[2] - 14,
                self.sv[1] + (1 - v) * self.sv[3] - 14,
                28,
                28,
            ),
            circular=True,
        ):
            style.picker_marker(
                a + s * w,
                b + v * d,
                14 * p.scale,
                color_rgb((h, s, v), False) + (1.0,),
                scale=p.scale,
                palette=palette,
            )
        self.motion.region("sv", self.sv, circular=True)
        a, b, w, d = self.hue
        p.surface(
            (a + h * w - 4, b - 3, 8, d + 6), palette["text"], 1, 0.6, motion_key="hue"
        )
        self.motion.region("hue", self.hue)
        channels = (
            color_hsv(value, self.linear, self.hue_value)
            if self.mode == "HSV"
            else tuple(to_display(c) for c in value[:3])
            if self.linear
            else value[:3]
        )
        for i, (label, v) in enumerate(
            zip("HSV" if self.mode == "HSV" else "RGB", channels)
        ):
            txt = (
                self.text_edit.text
                if self.text_edit and self.field == i
                else f"{v:.2f}"
            )
            p.field(COLOR["fields"][i], label, txt, size=21)
        if len(value) > 3:
            p.surface(COLOR["alpha"])
            p.field(
                (374, 294, 230, 48),
                "Alpha",
                self.text_edit.text
                if self.text_edit and self.field == 3
                else f"{value[3]:.2f}",
                split=126,
                size=21,
            )
            r = COLOR["alpha_track"]
            a, b, w, d = r
            p.surface(r, "track", 8, 0)
            ratio = max(0, min(1, value[3]))
            p.surface((a, b, w * ratio, d), "fill", 8, 0)
            p.circle(
                (a + w * ratio, b + d / 2), 11, palette["text"], 0.7, motion_key="alpha"
            )
            self.motion.region("alpha", COLOR["alpha_track"], circular=True)
        p.surface(COLOR["hex"], "input")
        p.text(
            COLOR["hex"],
            self.text_edit.text
            if self.text_edit and self.field == "hex"
            else color_hex(value, self.linear),
            size=21,
        )
        p.surface(COLOR["eyedropper"])
        p.icon("eyedropper", COLOR["eyedropper"], 29)
