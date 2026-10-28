"""Retained custom controls, independent of bpy, native layout and scene data.

Hosts own event delivery, redraw, undo, translation and visibility. Paint reads
only visible controls. Layout caches geometry until structure or width changes.
"""

from dataclasses import dataclass, field
from .animation import AnimationSettings, Motion
from .bindings import Edit
from .editing import Text, number


@dataclass(frozen=True)
class Theme:
    row_height: float = 32.0
    gap: float = 4.0
    padding: float = 8.0
    radius: float = 8.0
    font_size: float = 11.0
    palette: str = "BLENDER"

    def __post_init__(self):
        if self.palette not in {"BLENDER", "REFERENCE"}:
            raise ValueError("palette must be BLENDER or REFERENCE")


@dataclass
class Control:
    key: str
    kind: str
    label: str = ""
    binding: object = None
    action: object = None
    options: dict = field(default_factory=dict)
    rect: tuple = (0.0, 0.0, 0.0, 0.0)

    motion: object = field(default_factory=Motion, repr=False)

    @property
    def enabled(self):
        value = self.options.get("enabled", True)
        return bool(value() if callable(value) else value) and (
            self.binding is None or self.binding.valid()
        )


class Group:
    def __init__(self, canvas, kind="column", parent=None):
        self.canvas, self.kind, self.parent = canvas, kind, parent
        self.children = []
        self.rect = (0.0, 0.0, 0.0, 0.0)

    def _group(self, kind):
        child = Group(self.canvas, kind, self)
        self.children.append(child)
        self.canvas.invalidate()
        return child

    def row(self):
        return self._group("row")

    def column(self):
        return self._group("column")

    def box(self):
        return self._group("box")

    def add(self, kind, key, label="", *, binding=None, action=None, **options):
        if key in self.canvas.controls:
            raise ValueError(f"Duplicate control key: {key}")
        if kind not in {
            "label",
            "button",
            "toggle",
            "number",
            "text",
            "enum",
            "color",
            "separator",
            "image",
            "widget",
        }:
            raise ValueError(f"Unsupported custom control: {kind}")
        if kind in {"toggle", "number", "text", "enum", "color"} and binding is None:
            raise ValueError(f"{kind} requires a Binding")
        control = Control(key, kind, label, binding, action, options)
        if kind == "widget":
            control.motion = options["widget"].motion
        if "animation" in options:
            control.motion.settings = options["animation"]
        control.motion.toggle = kind == "toggle"
        self.canvas._bind_motion(control.motion)
        self.canvas._motion_owners[control.motion] = control
        self.canvas.controls[key] = control
        self.children.append(control)
        self.canvas.invalidate()
        return control

    def label(self, key, text, **kw):
        return self.add("label", key, text, **kw)

    def title(self, key, text, **kw):
        return self.label(key, text, text_role="title", **kw)

    def button(self, key, text, action, **kw):
        return self.add("button", key, text, action=action, **kw)

    def toggle(self, key, text, binding, **kw):
        return self.add("toggle", key, text, binding=binding, **kw)

    def number(self, key, text, binding, **kw):
        return self.add("number", key, text, binding=binding, **kw)

    def text(self, key, text, binding, **kw):
        return self.add("text", key, text, binding=binding, **kw)

    def enum(self, key, text, binding, *, items, **kw):
        return self.add("enum", key, text, binding=binding, items=tuple(items), **kw)

    def color(self, key, text, binding, **kw):
        return self.add("color", key, text, binding=binding, **kw)

    def separator(self, key, **kw):
        return self.add("separator", key, **kw)

    def widget(self, key, widget, **kw):
        return self.add("widget", key, widget=widget, **kw)

    def image(self, key, texture, **kw):
        return self.add("image", key, texture=texture, **kw)


class Canvas(Group):
    navigation_keys = {
        "UP_ARROW",
        "DOWN_ARROW",
        "HOME",
        "END",
        "PAGE_UP",
        "PAGE_DOWN",
        "RET",
        "NUMPAD_ENTER",
        "ESC",
    }

    def __init__(self, theme=None, *, animation=None):
        self.animation = animation or AnimationSettings()
        self._animation_parents = ()
        self._animation_wake = None
        self._moving = set()
        self._motion_owners = {}
        self._motion_focus = None
        self.theme = theme or Theme()
        self.controls = {}
        self._dirty = True
        self._width = None
        self.height = 0.0
        self.layout_count = 0
        self.schema_revision = 0
        self.edit = None
        self.editor = None
        self.active = None
        self.overlay = None
        self.widget_capture = None
        self.keyboard_focus = None
        self.hover = None
        self.visible = True
        super().__init__(self)

    def _bind_motion(self, motion):
        motion.bind((*self._animation_parents, self.animation), self._wake_motion)

    def bind_animation(self, parents=(), wake=None):
        self._animation_parents = tuple(parents)
        self._animation_wake = wake
        for control in self.controls.values():
            self._bind_motion(control.motion)

    def _wake_motion(self, motion):
        self._moving.add(motion)
        if self._animation_wake and self.visible:
            self._animation_wake()

    def advance_animations(self, clip=None):
        for motion in tuple(self._moving):
            control = self._motion_owners.get(motion)
            if clip is not None and control is not None:
                a, b, w, h = control.rect
                x, y, cw, ch = clip
                if not (a < x + cw and a + w > x and b < y + ch and b + h > y):
                    motion.clear()
            if not motion.advance():
                self._moving.discard(motion)
        return bool(self._moving)

    def notify_changed(self, key):
        """Host revision hook, including read-only indicators; never polls RNA."""
        control = self.controls[key]
        if self.visible and control.enabled:
            control.motion.pulse("reveal", 0.12)

    def _motion_input(self, event, x, y, clip):
        if self.overlay and "widget" in self.overlay:
            widget = self.overlay["widget"]
            motion = widget.motion
            self._bind_motion(motion)
            a, b, w, h = self.overlay["rect"]
            mx, my = (
                (x - a) * widget.width / max(1, w),
                (y - b) * widget.height / max(1, h),
            )
        elif self.overlay:
            motion = self.active.motion if self.active else None
            mx, my = x, y
        else:
            control = self.widget_capture or self.active or self.hit(x, y, clip)
            motion = control.motion if control and control.enabled else None
            mx, my = x, y
            if motion and control.kind == "widget":
                widget = control.options["widget"]
                a, b, w, h = control.rect
                mx, my = (
                    (x - a) * widget.width / max(1, w),
                    (y - b) * widget.height / max(1, h),
                )
        if self._motion_focus and self._motion_focus is not motion:
            self._motion_focus.hover = None
            self._motion_focus.pointer = None
        self._motion_focus = motion
        if motion:
            motion.input(event, mx, my)

    def invalidate(self):
        self._dirty = True
        for control in self.controls.values():
            control.motion.clear()

    def arrange(self, width):
        width = max(1.0, float(width))
        if not self._dirty and width == self._width:
            return self.height
        t = self.theme

        heights = {}

        def height(node, available):
            cache_key = (id(node), available)
            if cache_key in heights:
                return heights[cache_key]
            if isinstance(node, Control):
                default_height = (
                    (
                        node.options["widget"].height
                        * available
                        / node.options["widget"].width
                    )
                    if node.kind == "widget"
                    else 8.0
                    if node.kind == "separator"
                    else t.row_height
                )
                return max(
                    0.0,
                    node.options.get("height", default_height),
                )
            inner = max(0.0, available - (2 * t.padding if node.kind == "box" else 0.0))
            child_width = (
                max(
                    0.0,
                    (inner - max(0, len(node.children) - 1) * t.gap)
                    / max(1, len(node.children)),
                )
                if node.kind == "row"
                else inner
            )
            values = [height(c, child_width) for c in node.children]
            h = (
                max(values, default=0.0)
                if node.kind == "row"
                else sum(values) + max(0, len(values) - 1) * t.gap
            )
            heights[cache_key] = h + (2 * t.padding if node.kind == "box" else 0.0)
            return heights[cache_key]

        def place(node, x, y, w):
            h = height(node, w)
            node.rect = (x, y, max(0.0, w), h)
            if isinstance(node, Control):
                return
            if node.kind == "box":
                x += t.padding
                y += t.padding
                w = max(0.0, w - 2 * t.padding)
            if node.kind == "row":
                cell = max(
                    0.0,
                    (w - max(0, len(node.children) - 1) * t.gap)
                    / max(1, len(node.children)),
                )
                for i, child in enumerate(node.children):
                    place(child, x + i * (cell + t.gap), y, cell)
            else:
                for child in node.children:
                    place(child, x, y, w)
                    y += height(child, w) + t.gap

        place(self, t.padding, t.padding, max(0.0, width - 2 * t.padding))
        self.height = height(self, max(0.0, width - 2 * t.padding)) + 2 * t.padding
        self._width = width
        self._dirty = False
        self.layout_count += 1
        return self.height

    def visible_controls(self, clip):
        if not self.visible:
            return
        x, y, w, h = clip
        for control in self.controls.values():
            a, b, c, d = control.rect
            if a < x + w and a + c > x and b < y + h and b + d > y:
                yield control

    def hit(self, x, y, clip):
        for control in reversed(tuple(self.visible_controls(clip))):
            a, b, w, h = control.rect
            if a <= x < a + w and b <= y < b + h and control.enabled:
                return control
        return None

    def park(self):
        self.visible = False
        self.cancel()
        self.hover = None

    def cancel(self):
        self.blur_focus()
        for motion in tuple(self._moving):
            motion.clear()
        self._moving.clear()
        self._motion_focus = None
        for control in self.controls.values():
            if control.kind == "widget":
                control.options["widget"].cancel()
        if self.overlay and "widget" in self.overlay:
            self.overlay["widget"].cancel()
        self.widget_capture = None
        if self.edit is not None:
            self.edit.finish(cancel=True)
        self.edit = self.editor = self.active = self.overlay = None

    def finish(self):
        if self.edit:
            self.edit.finish()
        self.edit = self.editor = self.active = None

    def _begin(self, control):
        self.finish()
        self.active = control
        self.edit = Edit(control.binding)

    def blur_focus(self):
        if self.keyboard_focus is not None:
            self.keyboard_focus.options["widget"].blur()
            self.keyboard_focus = None
            if self.visible and self._animation_wake:
                self._animation_wake()

    def event(self, event, x, y, clip, *, clipboard=None):
        if not self.visible:
            return False
        if (
            event.type == "LEFTMOUSE"
            and event.value in {"PRESS", "DOUBLE_CLICK"}
            and not (self.overlay or self.widget_capture)
        ):
            hit = self.hit(x, y, clip)
            focus = (
                hit
                if hit
                and hit.kind == "widget"
                and getattr(hit.options["widget"], "focusable", False)
                else None
            )
            if focus is not self.keyboard_focus:
                self.blur_focus()
                self.keyboard_focus = focus
                if focus:
                    focus.options["widget"].focus()
        if (
            self.keyboard_focus
            and event.type in self.navigation_keys
            and not (self.overlay or self.widget_capture or self.edit)
        ):
            control = self.keyboard_focus
            if not control.enabled or not any(
                c is control for c in self.visible_controls(clip)
            ):
                self.blur_focus()
                return False
            widget = control.options["widget"]
            used = widget.event(event, 0, 0, clipboard=clipboard)
            if not widget.focused:
                self.keyboard_focus = None
            return used
        self._motion_input(event, x, y, clip)
        previous = self.overlay
        used = self._event(event, x, y, clip, clipboard=clipboard)
        if self.keyboard_focus and not self.keyboard_focus.options["widget"].focused:
            self.keyboard_focus = None
        if self.overlay is not previous and self.overlay and "widget" in self.overlay:
            motion = self.overlay["widget"].motion
            self._bind_motion(motion)
            motion.pulse("reveal", 0.12)
        return used

    def _event(self, event, x, y, clip, *, clipboard=None):
        """Return True only for consumed events; coordinates are top-down logical px.

        event has type/value/unicode/shift/ctrl/oskey fields (Blender Event works).
        clipboard is an optional object with a writable clipboard attribute.
        """
        if not self.visible:
            return False
        kind = event.type
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if kind in {"WINDOW_DEACTIVATE"}:
            consumed = bool(self.edit or self.overlay)
            self.cancel()
            return consumed
        if kind in {"ESC", "RIGHTMOUSE"} and press and (self.edit or self.overlay):
            self.cancel()
            return True
        if self.widget_capture is not None:
            control = self.widget_capture
            widget = control.options["widget"]
            a, b, w, h = control.rect
            used = widget.event(
                event,
                (x - a) * widget.width / max(1.0, w),
                (y - b) * widget.height / max(1.0, h),
                clipboard=clipboard,
            )
            if not widget.capturing:
                self.widget_capture = None
            return used
        if self.editor is not None:
            if kind in {"RET", "NUMPAD_ENTER"} and press:
                try:
                    value = (
                        number(self.editor.text)
                        if self.active.kind == "number"
                        else self.editor.text
                    )
                    self._write(value)
                    self.finish()
                except ValueError:
                    pass  # Keep invalid text selected for correction.
                return True
            if kind == "LEFTMOUSE" and press:
                self.cancel()
                return True
            if press:
                command = getattr(event, "ctrl", False) or getattr(
                    event, "oskey", False
                )
                if command and kind == "A":
                    self.editor.anchor = 0
                    self.editor.cursor = len(self.editor.text)
                elif command and kind in {"C", "X"} and clipboard is not None:
                    a, b = sorted((self.editor.anchor, self.editor.cursor))
                    clipboard.clipboard = self.editor.text[a:b]
                    if kind == "X":
                        self.editor.erase()
                elif command and kind == "V" and clipboard is not None:
                    self.editor.insert(clipboard.clipboard)
                elif kind in {"BACK_SPACE", "DEL"}:
                    self.editor.erase(kind == "BACK_SPACE")
                elif kind in {"LEFT_ARROW", "RIGHT_ARROW", "HOME", "END"}:
                    target = {
                        "LEFT_ARROW": self.editor.cursor - 1,
                        "RIGHT_ARROW": self.editor.cursor + 1,
                        "HOME": 0,
                        "END": len(self.editor.text),
                    }[kind]
                    self.editor.move(target, getattr(event, "shift", False))
                elif getattr(event, "unicode", "") and not command:
                    self.editor.insert(event.unicode)
            return True
        if self.overlay is not None:
            if "widget" in self.overlay:
                widget = self.overlay["widget"]
                a, b, w, h = self.overlay["rect"]
                if (
                    kind == "LEFTMOUSE"
                    and press
                    and not (a <= x < a + w and b <= y < b + h)
                    and not widget.capturing
                ):
                    self.cancel()
                    return True
                widget.event(
                    event,
                    (x - a) * widget.width / max(1.0, w),
                    (y - b) * widget.height / max(1.0, h),
                    clipboard=clipboard,
                )
                return True
            if kind == "LEFTMOUSE" and press:
                selected = None
                for rect, value, label in self.overlay["items"]:
                    a, b, w, h = rect
                    if a <= x < a + w and b <= y < b + h:
                        selected = value
                        break
                if selected is not None:
                    self._write(selected)
                    self.finish()
                    self.overlay = None
                else:
                    self.cancel()
            return True
        if self.edit is not None:
            if kind == "MOUSEMOVE" and self.active.kind == "number":
                minimum = self.active.options.get("min", 0.0)
                maximum = self.active.options.get("max", 1.0)
                delta = (
                    (x - self._drag_x)
                    * (maximum - minimum)
                    / max(1.0, self.active.rect[2])
                )
                if getattr(event, "shift", False):
                    delta *= 0.25
                self._write(self._drag_start + delta)
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                self.finish()
            return True
        control = self.hit(x, y, clip)
        if kind == "MOUSEMOVE":
            self.hover = control.key if control else None
            return False
        if control is not None and control.kind == "widget":
            widget = control.options["widget"]
            a, b, w, h = control.rect
            used = widget.event(
                event,
                (x - a) * widget.width / max(1.0, w),
                (y - b) * widget.height / max(1.0, h),
                clipboard=clipboard,
            )
            if widget.capturing:
                self.widget_capture = control
            return used
        if control is None or kind != "LEFTMOUSE" or not press:
            return False
        if control.kind == "button":
            if control.action:
                control.action()
        elif control.kind == "toggle":
            self._begin(control)
            self._write(not control.binding.read())
            self.finish()
        elif control.kind in {"number", "text", "color"}:
            self._begin(control)
            if control.kind == "color":
                self.cancel()
                if control.action:
                    control.action()
                else:
                    from .widgets.color import ColorPicker

                    picker = ColorPicker(
                        control.binding, linear=control.options.get("linear", True)
                    )
                    scale = min(1.0, clip[2] / picker.width, clip[3] / picker.height)
                    w = picker.width * scale
                    h = picker.height * scale
                    self.overlay = {
                        "widget": picker,
                        "rect": (
                            clip[0] + (clip[2] - w) / 2,
                            clip[1] + (clip[3] - h) / 2,
                            w,
                            h,
                        ),
                    }
                return True
            if control.kind == "text" or event.value == "DOUBLE_CLICK":
                self.editor = Text(control.binding.read())
            else:
                self._drag_x = x
                self._drag_start = control.binding.read()
        elif control.kind == "enum":
            self._begin(control)
            a, b, w, h = control.rect
            items = control.options["items"]
            rh = self.theme.row_height
            # Keep this compact picker inside the host clip. Long lists belong
            # in VirtualList, rather than constructing an unbounded overlay.
            count = len(items)
            if count * rh > clip[3]:
                self.cancel()
                return False
            top = max(clip[1], min(b + h, clip[1] + clip[3] - count * rh))
            self.overlay = {
                "rect": (a, top, w, count * rh),
                "items": [
                    ((a, top + i * rh, w, rh), value, label)
                    for i, (value, label) in enumerate(items)
                ],
            }
        else:
            return False
        return True

    def _write(self, value):
        if self.active.kind == "number":
            lo = self.active.options.get("hard_min", float("-inf"))
            hi = self.active.options.get("hard_max", float("inf"))
            value = max(lo, min(hi, value))
            if self.active.options.get("integer"):
                value = round(value)
        self.edit.update(value)

    def paint(self, rect, clip, *, preferences=None, font=0, backdrop=None):
        from .gpu.paint import paint

        return paint(
            self, rect, clip, preferences=preferences, font=font, backdrop=backdrop
        )
