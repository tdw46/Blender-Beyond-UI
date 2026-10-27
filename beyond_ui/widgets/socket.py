from .base import Widget
from ..gpu import style


class Socket(Widget):
    width = 20.0
    height = 20.0

    def __init__(self, color):
        super().__init__()
        self.color = tuple(color)

    def paint(self, rect, font, palette, *, backdrop=None):
        x, y, w, h = rect
        r = min(w, h) * 0.3
        style.draw(
            x + w / 2 - r, y + h / 2 - r, r * 2, r * 2, self.color, mode=3, border=1.0
        )
