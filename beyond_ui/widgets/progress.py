"""Read-only progress indicators; updates come from the consuming host."""

from math import isfinite
from .base import Widget, Painter


def factor_value(value):
    value = float(value)
    if not isfinite(value):
        raise ValueError("Progress factor must be finite")
    return max(0.0, min(1.0, value))


class Progress(Widget):
    width = 630.0
    height = 390.0

    def __init__(self, factor=0.0, *, type="BAR", text="", detail="", framed=True):
        super().__init__()
        if type not in {"BAR", "RING"}:
            raise ValueError("Progress type must be BAR or RING")
        if not callable(factor):
            factor_value(factor)
        self.factor = factor
        self.type = type
        self.text = text
        self.detail = detail
        self.framed = framed
        if not framed:
            self.width = 320.0
            self.height = 36.0 if type == "BAR" else 160.0

    def value(self):
        return factor_value(self.factor() if callable(self.factor) else self.factor)

    def paint(self, rect, font, palette, *, backdrop=None):
        from ..gpu.progress import ring

        p = Painter(
            rect,
            self.width,
            self.height,
            font,
            palette,
            backdrop,
            motion=self.motion,
            interactive=False,
        )
        value = self.value()
        label = f"{int(value * 100 + 0.5)}%"
        if self.framed:
            p.card(
                "Progress Bar" if self.type == "BAR" else "Progress Ring",
                title_inset=76,
            )
        if self.type == "BAR":
            r = (32, 150, 566, 27) if self.framed else (0, 24, 320, 10)
            text_r = (32, 111, 566, 32) if self.framed else (0, 0, 320, 21)
            p.text(text_r, self.text, inset=0, size=22 if self.framed else 12)
            p.text(
                text_r, label, align="right", inset=0, size=22 if self.framed else 12
            )
            p.surface(r, "track", r[3] / 2, border=0.6)
            if value > 0:
                x, y, w, h = r
                p.surface(
                    (x, y, h + (w - h) * value, h), "progress_fill", h / 2, border=0
                )
            if self.detail and self.framed:
                p.text((32, 194, 566, 32), self.detail, role="muted", inset=0)
        else:
            r = (190, 84, 230, 230) if self.framed else (102, 0, 116, 116)
            ring(
                p.map(r),
                value,
                16 * p.scale if self.framed else 8 * p.scale,
                palette["surfaces"]["track"][0],
                palette["surfaces"]["progress_fill"][1],
            )
            p.text(
                r,
                label,
                size=46 if self.framed else 24,
                align="center",
                inset=0,
                weight="title",
            )
            p.text(
                (32, 323, 566, 32) if self.framed else (0, 128, 320, 24),
                self.text,
                size=21 if self.framed else 12,
                align="center",
                inset=0,
            )
