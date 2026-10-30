"""Popup-local initial editing and Return actions; never changes OS focus."""

from .editing import Text


class PopupFocus:
    def __init__(self, popup):
        self.popup = popup
        self.initialized = False
        self.initial = tuple(
            c
            for c in popup.canvas.controls.values()
            if c.options.get("activate_init") and c.kind in {"text", "number"}
        )
        self.defaults = tuple(
            c
            for c in popup.canvas.controls.values()
            if c.options.get("active_default") and c.options.get("operator_button")
        )

    def eligible(self, control, context):
        canvas = self.popup.canvas
        if not canvas.visible or canvas.controls.get(control.key) is not control:
            return False
        guard = control.options.get("activation_guard")
        if guard is not None:
            guard(context)
        return control.enabled and control.rect[2] > 0 and control.rect[3] > 0

    def reveal(self, control):
        popup = self.popup
        _, y, _, height = control.rect
        if y < popup.scroll:
            popup.scroll = y
        elif y + height > popup.scroll + popup.height:
            popup.scroll = max(0, y + min(height, popup.height) - popup.height)
        popup.scroll = min(popup.scroll, max(0, popup.canvas.height - popup.height))

    def open(self, context):
        if self.initialized:
            return
        self.initialized = True
        canvas = self.popup.canvas
        for control in self.initial:
            if not self.eligible(control, context):
                continue
            canvas._begin(control)
            canvas.editor = Text(canvas._initial_text)
            canvas.context_focus = control
            canvas._context_point = (0.5, 0.5)
            self.reveal(control)
            control.motion.pulse("body", 0.12)
            break

    def event(self, event, context):
        canvas = self.popup.canvas
        if (
            event.type not in {"RET", "NUMPAD_ENTER"}
            or event.value != "PRESS"
            or canvas.edit
            or canvas.overlay
            or canvas.context_menu
            or canvas.widget_capture
            or canvas.keyboard_focus
            or any(
                getattr(event, key, False) for key in ("shift", "ctrl", "alt", "oskey")
            )
        ):
            return False
        if getattr(event, "is_repeat", False):
            return bool(self.defaults)
        for control in self.defaults:
            try:
                if not self.eligible(control, context):
                    continue
                self.reveal(control)
                canvas.context_focus = control
                canvas._context_point = (0.5, 0.5)
                control.motion.pulse("body", 0.12)
                result = control.action()
                if isinstance(result, set) and result.intersection(
                    {"FINISHED", "RUNNING_MODAL"}
                ):
                    parent = self.popup.parent
                    if (parent.overlay or {}).get("widget") is self.popup:
                        parent.cancel()
                return True
            except (ReferenceError, RuntimeError, ValueError, AttributeError) as error:
                canvas.menu_error = str(error)
                return True
        return False

    def close(self):
        self.initial = self.defaults = ()
