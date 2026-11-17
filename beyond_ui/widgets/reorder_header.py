"""Handle-driven section reordering with one insertion marker per canvas."""
from .base import Widget


class ReorderHeader(Widget):
    handle_width = 28

    def __init__(self, canvas, key):
        super().__init__()
        self.canvas = canvas
        self.key = key
        self.drop = None
        self.dragging = False
        self.section = None

    def cancel(self):
        super().cancel()
        self.drop = None
        self.dragging = False

    def event(self, event, x, y, *, clipboard=None):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.origin = x, y
            self.handle = x >= self.width-self.handle_width
            self.capturing = True
            return True
        if not self.capturing:
            return False
        if event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'}:
            self.cancel()
            return True
        if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'LEFTMOUSE'}:
            return False
        moved = abs(y-self.origin[1]) + abs(x-self.origin[0]) > 4
        self.dragging |= self.handle and moved
        if self.dragging:
            siblings = [(c, c.options.get('widget')) for c in self.canvas.controls.values()
                        if type(c.options.get('widget')) is type(self)]
            own = next(c for c, w in siblings if w is self)
            position = own.rect[1] + y * own.rect[3]/self.height
            # Use the bounds of each whole section, including its expanded body.
            # In a gap, use the closest visible edge for both the mark and drop.
            self.drop = None
            nearest = float('inf')
            for control, widget in siblings:
                _, top, _, height = widget.section.rect
                after = position >= top + height / 2
                distance = max(top - position, position - (top + height), 0.)
                if distance < nearest:
                    self.drop = (widget, after) if widget is not self else None
                    nearest = distance
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.dragging and self.drop:
                self.move(self.drop[0].key, after=self.drop[1])
            elif not self.handle and not moved:
                self.toggle()
            self.cancel()
        return True

    def insertion_line(self):
        if self.dragging and self.drop:
            target, after = self.drop
            x,y,w,h = target.section.rect
            return x, y+h-1 if after else y, w, 2
        return None
