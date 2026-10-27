"""Read-only translation/rotation/scale display, matching template_matrix semantics."""

from .base import Widget, Painter
from ..gpu import skin


class MatrixView(Widget):
    width = 630.0
    height = 436.0

    def __init__(
        self,
        binding,
        *,
        labels=("Translation", "Rotation", "Scale"),
        title="Matrix",
        unavailable_text="Matrix unavailable",
    ):
        super().__init__()
        self.binding = binding
        self.labels = labels
        self.title = title
        self.unavailable_text = unavailable_text

    def paint(self, rect, font, palette, *, backdrop=None):
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
        p.card(self.title, title_inset=76)
        if not self.binding.valid():
            p.text((24, 78, 584, 52), self.unavailable_text, role="muted")
            return
        values = self.binding.read()
        for row, (label, vector) in enumerate(zip(self.labels, values)):
            p.text((24, 78 + row * 117, 584, 32), label, inset=0, size=23)
            for col, (axis, value) in enumerate(zip("XYZ", vector)):
                r = (24 + col * 199, 119 + row * 117, 189, 52)
                x, y, w, h = r
                p.surface(r, "input", 8, 1)
                p.line(
                    ((x + 50, y + 1), (x + 50, y + h - 1)),
                    skin.rgba("7c858e", 0.24),
                    p.scale,
                )
                p.text((x, y, 50, h), axis, size=21, align="center", inset=0)
                p.text(
                    (x + 50, y, w - 50, h),
                    f"{value:.2f}" + ("°" if row == 1 else ""),
                    size=21,
                    align="center",
                    inset=0,
                )
