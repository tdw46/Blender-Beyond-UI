"""Small retained painter and event contracts for compound custom controls."""

from ..editing import Text, number
from ..gpu import style
from ..gpu.paint import measure


class Painter:
    def __init__(self, rect, width, height, font, palette):
        self.rect = rect
        self.width = width
        self.height = height
        self.font = font
        self.palette = palette
        self.sx = rect[2] / width
        self.sy = rect[3] / height
        self.scale = min(self.sx, self.sy)

    def map(self, r):
        x, y, w, h = r
        rx, ry, rw, rh = self.rect
        return rx + x * self.sx, ry + rh - (y + h) * self.sy, w * self.sx, h * self.sy

    def surface(self, r, role="field", radius=5):
        color = self.palette.get(role, role)
        style.draw(
            *self.map(r),
            color,
            radius=radius * self.scale,
            border=0.65 * self.scale,
            top=style.shade(color, 0.025),
        )

    def text(self, r, value, role="text", size=11):
        import blf

        a, b, w, h = self.map(r)
        size *= self.scale
        blf.size(self.font, size)
        blf.color(self.font, *self.palette[role])
        blf.enable(self.font, blf.CLIPPING)
        try:
            blf.clipping(self.font, a, b, a + w, b + h)
            blf.position(
                self.font,
                a + 5 * self.scale,
                b + (h - measure(self.font, size, "H")[1]) / 2,
                0,
            )
            blf.draw(self.font, str(value))
        finally:
            blf.disable(self.font, blf.CLIPPING)

    def line(self, points, color, width=1):
        import gpu
        from gpu_extras.batch import batch_for_shader

        # Geometry is regenerated only for changed curves by the editor; small
        # line batches are cached by tuple, shared across widgets in this module.
        shader, batch = line_batch(
            tuple(points), tuple(color), self.rect, self.width, self.height, width
        )
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)


_LINE_CACHE = {}


def line_batch(points, color, rect, width, height, thickness):
    import gpu
    from gpu_extras.batch import batch_for_shader

    key = (points, rect, width, height, thickness)
    item = _LINE_CACHE.get(key)
    if item is not None:
        return item
    x, y, w, h = rect
    coords = [(x + px * w / width, y + h - py * h / height) for px, py in points]
    verts = []
    for (ax, ay), (bx, by) in zip(coords, coords[1:]):
        dx = bx - ax
        dy = by - ay
        length = max(1e-9, (dx * dx + dy * dy) ** 0.5)
        nx = -dy / length * thickness / 2
        ny = dx / length * thickness / 2
        verts.extend(
            (
                (ax + nx, ay + ny),
                (ax - nx, ay - ny),
                (bx + nx, by + ny),
                (ax - nx, ay - ny),
                (bx - nx, by - ny),
                (bx + nx, by + ny),
            )
        )
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    item = (shader, batch_for_shader(shader, "TRIS", {"pos": verts}))
    if len(_LINE_CACHE) >= 256:
        _LINE_CACHE.pop(next(iter(_LINE_CACHE)))
    _LINE_CACHE[key] = item
    return item


def contains(rect, x, y):
    a, b, w, h = rect
    return a <= x < a + w and b <= y < b + h


class Widget:
    width = 320.0
    height = 240.0

    def __init__(self):
        self.capturing = False
        self.text_edit = None
        self.field = None

    def cancel(self):
        self.capturing = False
        self.text_edit = None
        self.field = None

    def event(self, event, x, y, *, clipboard=None):
        return False

    def edit_text(self, event, *, clipboard=None):
        """Return submitted string, None while editing, or False on cancel."""
        if event.value not in {"PRESS", "DOUBLE_CLICK"}:
            return None
        kind = event.type
        edit = self.text_edit
        if kind == "ESC":
            self.text_edit = None
            self.capturing = False
            return False
        if kind in {"RET", "NUMPAD_ENTER"}:
            value = edit.text
            self.text_edit = None
            self.capturing = False
            return value
        command = getattr(event, "ctrl", False) or getattr(event, "oskey", False)
        if command and kind == "A":
            edit.anchor = 0
            edit.cursor = len(edit.text)
        elif command and kind in {"C", "X"} and clipboard is not None:
            a, b = sorted((edit.anchor, edit.cursor))
            clipboard.clipboard = edit.text[a:b]
            if kind == "X":
                edit.erase()
        elif command and kind == "V" and clipboard is not None:
            edit.insert(clipboard.clipboard)
        elif kind in {"BACK_SPACE", "DEL"}:
            edit.erase(kind == "BACK_SPACE")
        elif kind in {"LEFT_ARROW", "RIGHT_ARROW", "HOME", "END"}:
            edit.move(
                {
                    "LEFT_ARROW": edit.cursor - 1,
                    "RIGHT_ARROW": edit.cursor + 1,
                    "HOME": 0,
                    "END": len(edit.text),
                }[kind],
                getattr(event, "shift", False),
            )
        elif getattr(event, "unicode", "") and not command:
            edit.insert(event.unicode)
        return None
