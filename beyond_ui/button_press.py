"""Release-owned buttons and finite hold menus; no timer or desktop input."""

from .context_menu import inside
from .operator_enum import context_key


class ButtonPress:
    def __init__(self, canvas, control, point, clip, context):
        self.canvas, self.control = canvas, control
        self.point, self.clip = tuple(point), tuple(clip)
        self.context, self.scope = context, context_key(context)
        self.started = control.motion.clock()
        self.cancelled = False
        self.menu = None
        self.hold = control.options.get("hold_menu")

    def valid(self, context):
        c, canvas = self.control, self.canvas
        guard = c.options.get("activation_guard")
        if guard:
            guard(context)
        return (
            canvas.visible
            and canvas.controls.get(c.key) is c
            and c.enabled
            and context_key(context) == self.scope
        )

    def advance(self, context=None):
        context = self.context if context is None else context
        if self.cancelled or self.menu is not None or self.hold is None:
            return False
        try:
            if not self.valid(context):
                self.cancelled = True
                return False
            if self.control.motion.clock() - self.started < 0.2:
                return True
            canvas = self.canvas
            # Opening a menu cancels prior Canvas state. Preserve just ownership
            # of this release so it cannot activate a newly opened menu row.
            canvas._button_press = None
            if canvas.open_operator_menu(
                self.control, self.clip, context, anchor=self.point, model=self.hold
            ):
                self.menu = canvas.context_menu
            self.cancelled = True
            canvas._button_press = self
        except (ReferenceError, RuntimeError, ValueError, AttributeError) as error:
            self.canvas.menu_error = str(error)
            self.cancelled = True
        return False

    def event(self, event, x, y, clip, context):
        """None lets the opened menu handle hover; bool owns the input."""
        context = self.context if context is None else context
        kind, press = event.type, event.value in {"PRESS", "DOUBLE_CLICK"}
        if tuple(clip) != self.clip:
            self.cancelled = True
        if kind == "WINDOW_DEACTIVATE" or press and kind in {"ESC", "RIGHTMOUSE"}:
            self.control.motion.clear()
            self.canvas.cancel()
            return kind != "RIGHTMOUSE" or inside(clip, x, y)
        if kind == "LEFTMOUSE" and event.value == "RELEASE" and self.menu is None:
            self.advance(context)
        if self.menu is not None:
            if kind == "LEFTMOUSE" and event.value == "RELEASE":
                self.canvas._button_press = None
                return True
            return None
        if kind == "MOUSEMOVE" and not inside(self.control.rect, x, y):
            self.cancelled = True
        if self.cancelled:
            self.control.motion.clear()
        else:
            self.control.motion.input(event, x, y)
        if kind == "LEFTMOUSE" and event.value == "RELEASE":
            self.canvas._button_press = None
            try:
                if (
                    not self.cancelled
                    and self.valid(context)
                    and inside(self.control.rect, x, y)
                ):
                    self.control.action()
            except (ReferenceError, RuntimeError, ValueError, AttributeError) as error:
                self.canvas.menu_error = str(error)
            return True
        self.advance(context)
        return True
