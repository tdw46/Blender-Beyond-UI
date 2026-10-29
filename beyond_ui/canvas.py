"""Retained custom controls, independent of bpy, native layout and scene data.

Hosts own event delivery, redraw, undo, translation and visibility. Paint reads
only visible controls. Layout caches geometry until structure or width changes.
"""

from dataclasses import dataclass, field, replace
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
            "event",
            "pointer",
            "search",
            "decorator",
            "text",
            "enum",
            "color",
            "separator",
            "image",
            "widget",
        }:
            raise ValueError(f"Unsupported custom control: {kind}")
        if (
            kind in {"toggle", "number", "event", "text", "enum", "color"}
            and binding is None
        ):
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

    def __init__(
        self,
        theme=None,
        *,
        animation=None,
        context_provider=None,
        menu_commit=None,
        shortcut_registry=None,
        shortcut_namespace="canvas",
    ):
        self.animation = animation or AnimationSettings()
        self._wide_numeric_motion_scale = 0.15
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
        self.backdrop_revision = 0
        self.edit = None
        self.editor = None
        self.active = None
        self.overlay = None
        self.context_menu = None
        self.context_provider = context_provider
        self.menu_commit = menu_commit
        self.shortcut_registry = shortcut_registry
        self.shortcut_namespace = shortcut_namespace
        self.context_focus = None
        self._context_point = (0.5, 0.5)
        self.menu_error = None
        self._tooltip_wake = lambda delay: None
        self.widget_capture = None
        self.keyboard_focus = None
        self.hover = None
        self.visible = True
        super().__init__(self)

    @property
    def wide_numeric_motion_scale(self):
        return self._wide_numeric_motion_scale

    @wide_numeric_motion_scale.setter
    def wide_numeric_motion_scale(self, value):
        value = AnimationSettings._validate(value)
        if value is None:
            raise ValueError("Numeric motion scale must be finite and nonnegative")
        self._wide_numeric_motion_scale = value
        self._scale_numeric_motion()

    def _scale_numeric_motion(self):
        if self._width is None:
            return
        width = max(1, self._width - 2 * self.theme.padding)
        for control in self.controls.values():
            if control.kind == "number":
                control.motion.amplitude_scale = (
                    self._wide_numeric_motion_scale
                    if control.rect[2] >= width * 0.75
                    else 1.0
                )

    def _bind_motion(self, motion, owner=None):
        parents = (*self._animation_parents, self.animation)
        motion.bind(
            (*parents, owner.motion.settings) if owner else parents,
            self._wake_motion,
        )

    def bind_animation(self, parents=(), wake=None):
        self._animation_parents = tuple(parents)
        self._animation_wake = wake
        for control in self.controls.values():
            self._bind_motion(control.motion)

    def bind_context_tooltips(self, schedule):
        """Host one-shot scheduler: delay seconds starts/replaces, None cancels."""
        if self.context_menu:
            self.context_menu.hide_tip()
        self._tooltip_wake = schedule or (lambda delay: None)
        if self.context_menu:
            self.context_menu.on_tip = self._tooltip_wake

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
            self._bind_motion(motion, self.overlay.get("owner"))
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
        self.backdrop_revision += 1
        self.close_context()
        self._dirty = True
        for control in self.controls.values():
            control.motion.clear()
            if control.kind == "decorator" and control.options["decorator"] is not None:
                try:
                    control.options["decorator"].refresh()
                except (ReferenceError, RuntimeError):
                    pass

    def arrange(self, width):
        width = max(1.0, float(width))
        if not self._dirty and width == self._width:
            return self.height
        t = self.theme

        heights = {}

        def row_widths(node, width):
            usable = max(0.0, width - max(0, len(node.children) - 1) * t.gap)
            fixed = [
                c.options.get("width") if isinstance(c, Control) else None
                for c in node.children
            ]
            total = sum(v for v in fixed if v is not None)
            factor = min(1.0, usable / total) if total else 1.0
            flex = max(0.0, usable - total) / max(1, fixed.count(None))
            return [v * factor if v is not None else flex for v in fixed]

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
            widths = (
                row_widths(node, inner)
                if node.kind == "row"
                else [inner] * len(node.children)
            )
            values = [height(c, width) for c, width in zip(node.children, widths)]
            h = (
                max(values, default=0.0)
                if node.kind == "row"
                else sum(values) + max(0, len(values) - 1) * t.gap
            )
            heights[cache_key] = h + (2 * t.padding if node.kind == "box" else 0.0)
            return heights[cache_key]

        def place(node, x, y, w):
            if isinstance(node, Control) and "width" in node.options:
                w = min(w, node.options["width"])
            h = height(node, w)
            node.rect = (x, y, max(0.0, w), h)
            if isinstance(node, Control):
                return
            if node.kind == "box":
                x += t.padding
                y += t.padding
                w = max(0.0, w - 2 * t.padding)
            if node.kind == "row":
                for child, cell in zip(node.children, row_widths(node, w)):
                    place(child, x, y, cell)
                    x += cell + t.gap
            else:
                for child in node.children:
                    place(child, x, y, w)
                    y += height(child, w) + t.gap

        place(self, t.padding, t.padding, max(0.0, width - 2 * t.padding))
        self.height = height(self, max(0.0, width - 2 * t.padding)) + 2 * t.padding
        self._width = width
        self._scale_numeric_motion()
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

    def hit(self, x, y, clip, *, include_disabled=False):
        cx, cy, cw, ch = clip
        if not (cx <= x < cx + cw and cy <= y < cy + ch):
            return None
        for control in reversed(tuple(self.visible_controls(clip))):
            a, b, w, h = control.rect
            if (
                a <= x < a + w
                and b <= y < b + h
                and (include_disabled or control.enabled)
            ):
                return control
        return None

    def park(self):
        self.visible = False
        self.cancel()
        self.hover = None

    def cancel(self):
        self.close_context()
        self.context_focus = None
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
        try:
            if self.edit:
                self.edit.finish()
        finally:
            self.edit = self.editor = self.active = None

    def _begin(self, control):
        self.finish()
        self.active = control
        self.edit = Edit(control.binding)
        numeric = control.options.get("numeric")
        self._numeric_state = numeric.snapshot() if numeric else None
        self._initial_text = (
            numeric.format(self.edit.before, self._numeric_state)
            if numeric
            else str(self.edit.before)
        )

    def blur_focus(self):
        if self.keyboard_focus is not None:
            self.keyboard_focus.options["widget"].blur()
            self.keyboard_focus = None
            if self.visible and self._animation_wake:
                self._animation_wake()

    def close_context(self):
        menu = getattr(self, "context_menu", None)
        if menu is not None:
            menu.close()
            self._moving.discard(menu.motion)
            self.context_menu = None
            if self._motion_focus is menu.motion:
                self._motion_focus = None
            if self.visible and self._animation_wake:
                self._animation_wake()

    def open_enum_menu(self, control, clip, context):
        """Open an owned enum through the same bounded glass menu as context actions."""
        from .context_menu import Entry, Menu, Target

        if not control.enabled or not control.binding.valid():
            return False
        rows = []
        for value, label in control.options["items"][:63]:

            def apply(target, ctx, selected=value):
                before = control.binding.read()
                try:
                    control.binding.write(selected)
                    control.binding.commit(before, control.binding.read())
                except Exception:
                    if control.binding.valid():
                        control.binding.write(before)
                    raise

            rows.append(
                Entry(
                    str(value),
                    label,
                    apply,
                    checked=lambda t, c, v=value: control.binding.read() == v,
                )
            )
        if not rows:
            return False
        self.cancel()
        target = Target(
            control.key,
            binding=control.binding,
            valid=lambda: self.visible
            and self.controls.get(control.key) is control
            and control.enabled
            and control.binding.valid(),
        )
        self.context_menu = Menu(
            target,
            rows,
            control.rect[:2],
            clip,
            context=context,
            on_tip=self._tooltip_wake,
            on_error=lambda error: setattr(self, "menu_error", str(error)),
        )
        self.context_menu.motion.bind(
            (*self._animation_parents, self.animation, control.motion.settings),
            self._wake_motion,
        )
        self.context_menu.motion.pulse("reveal", 0.12)
        return True

    def _bind_shortcut(self, control, target, context, clip):
        registry = self.shortcut_registry
        if registry is None or control.kind not in {"enum", "button"}:
            return None
        shortcut_key = control.options.get("shortcut_key")
        if shortcut_key is None and control.kind == "enum":
            from .context_paths import property_path

            source = getattr(control.binding, "context", None)
            path = property_path(source, context) if source is not None else None
            shortcut_key = "enum:" + path if path else None
        command = self.shortcut_namespace + ":" + (shortcut_key or control.key)
        scene = context.scene.as_pointer() if context.scene else None

        def run(ctx, event):
            if control.kind == "enum":
                result = self.open_enum_menu(control, clip, ctx)
            else:
                result = control.action()
            if getattr(ctx, "area", None):
                for region in ctx.area.regions:
                    region.tag_redraw()
            return result

        registry.bind(
            command,
            context,
            run,
            valid=lambda ctx: target.valid()
            and control.enabled
            and (ctx.scene.as_pointer() if ctx.scene else None) == scene,
        )
        return command

    def bind_shortcuts(self, context, clip):
        """Call after rebuilding/arranging a host canvas, outside painting."""
        from .context_menu import Target

        if self.shortcut_registry is None:
            return
        for control in self.visible_controls(clip):

            def valid(c=control):
                return (
                    self.visible
                    and self.controls.get(c.key) is c
                    and c.enabled
                    and (c.binding is None or c.binding.valid())
                )

            self._bind_shortcut(
                control, Target(control.key, valid=valid), context, clip
            )

    def open_context(
        self, control, x, y, clip, *, context=None, measure=None, overlay=None
    ):
        from .context_menu import Menu, Target, default_entries
        from .context_rna import Property

        def scope(ctx):
            if ctx is None:
                return None
            scene = getattr(ctx, "scene", None)
            prefs = getattr(getattr(ctx, "preferences", None), "view", None)
            return (
                scene.as_pointer() if scene else None,
                getattr(prefs, "show_developer_ui", False),
            )

        try:
            if control.kind == "widget" or overlay is not None:
                from .widgets.context import target as widget_target

                widget = (
                    overlay["widget"]
                    if overlay is not None
                    else control.options["widget"]
                )
                a, b, w, h = overlay["rect"] if overlay is not None else control.rect
                target = widget_target(
                    widget,
                    control.key,
                    (x - a) * widget.width / max(w, 1),
                    (y - b) * widget.height / max(h, 1),
                )
            else:
                binding = control.binding
                source = getattr(binding, "context", None)
                target = Target(
                    control.key,
                    (control.kind,),
                    binding,
                    source.valid
                    if isinstance(source, Property)
                    else binding.valid
                    if binding
                    else lambda: True,
                    payload=control,
                )
            valid = target.valid
            target = replace(
                target,
                valid=lambda: self.controls.get(control.key) is control
                and self.visible
                and (overlay is None or self.overlay is overlay)
                and any(c is control for c in self.visible_controls(clip))
                and bool(valid()),
                commit=self.menu_commit,
                editable=lambda: control.enabled,
            )
            provider = (
                control.options.get("context_menu")
                or self.context_provider
                or default_entries
            )
            from itertools import islice

            rows = list(islice(provider(target, context), Menu.limit))
            if self.shortcut_registry is not None:
                command = self._bind_shortcut(control, target, context, clip)
                routed = (
                    self.shortcut_registry.entry(command, context) if command else None
                )
                if routed is not None:
                    if control.kind == "enum":
                        rows.insert(
                            0,
                            replace(
                                routed, label="Shortcut to Open Menu", divider=True
                            ),
                        )
                    elif not any(
                        r.key == "SHORTCUT" and r.enabled is not False for r in rows
                    ):
                        rows = [r for r in rows if r.key != "SHORTCUT"] + [routed]
            # Empty providers deliberately preserve Blender's outside/unsupported path.
            from itertools import islice

            rows = tuple(islice(rows, Menu.limit))
            if not rows or not target.valid():
                return False
            self.close_context()
            menu = Menu(
                target,
                rows,
                (x, y),
                clip,
                context=context,
                measure=measure,
                scope=scope,
                on_error=lambda error: setattr(self, "menu_error", str(error)),
                on_tip=self._tooltip_wake,
            )
            menu.motion.bind(
                (*self._animation_parents, self.animation, control.motion.settings),
                self._wake_motion,
            )
            self.context_menu = menu
            self.context_focus = control
            a, b, w, h = control.rect
            self._context_point = ((x - a) / max(w, 1), (y - b) / max(h, 1))
            self.menu_error = None
            menu.motion.pulse("reveal", 0.12)
            return True
        except Exception as error:
            self.menu_error = str(error)
            return False

    def event(
        self, event, x, y, clip, *, clipboard=None, context=None, menu_measure=None
    ):
        if not self.visible:
            return False
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if self.context_menu is not None:
            menu = self.context_menu
            if tuple(clip) != tuple(menu.clip):
                self.close_context()
                return False
            used = menu.event(event, x, y, context)
            if menu.closed:
                self.close_context()
                from .context_menu import inside

                if event.type == "LEFTMOUSE" and press and not inside(clip, x, y):
                    self.context_focus = None
                    self.blur_focus()
            return used
        invocation = press and (
            event.type == "RIGHTMOUSE"
            or event.type == "APP"
            or event.type == "F10"
            and getattr(event, "shift", False)
        )
        if (
            invocation
            and self.overlay
            and "widget" in self.overlay
            and not self.overlay["widget"].capturing
        ):
            owner = self.overlay.get("owner")
            if owner is not None:
                from .context_menu import inside

                if event.type != "RIGHTMOUSE":
                    a, b, w, h = self.overlay["rect"]
                    px, py = self.overlay.get("context_point", (0.5, 0.5))
                    x, y = a + w * px, b + h * py
                if inside(self.overlay["rect"], x, y):
                    return self.open_context(
                        owner,
                        x,
                        y,
                        clip,
                        context=context,
                        measure=menu_measure,
                        overlay=self.overlay,
                    )
        if invocation and not (self.edit or self.overlay or self.widget_capture):
            control = self.hit(x, y, clip, include_disabled=True)
            if event.type != "RIGHTMOUSE" and self.context_focus is not None:
                control = self.context_focus
                a, b, w, h = control.rect
                x, y = a + w * self._context_point[0], b + h * self._context_point[1]
            if control is not None and any(
                c is control for c in self.visible_controls(clip)
            ):
                return self.open_context(
                    control, x, y, clip, context=context, measure=menu_measure
                )
            return False
        if event.type == "LEFTMOUSE" and press:
            if self.overlay and "widget" in self.overlay:
                from .context_menu import inside

                a, b, w, h = self.overlay["rect"]
                if inside(self.overlay["rect"], x, y):
                    self.overlay["context_point"] = (
                        (x - a) / max(w, 1),
                        (y - b) / max(h, 1),
                    )
            self.context_focus = self.hit(x, y, clip, include_disabled=True)
            if self.context_focus:
                a, b, w, h = self.context_focus.rect
                self._context_point = ((x - a) / max(w, 1), (y - b) / max(h, 1))

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
        control = self.hit(x, y, clip) if event.type == "LEFTMOUSE" and press else None
        if (
            control is not None
            and control.kind == "event"
            and event.type == "LEFTMOUSE"
            and press
            and not (self.edit or self.overlay or self.widget_capture)
        ):
            from .context_menu import Menu, Target

            target = Target(
                control.key,
                binding=control.binding,
                valid=lambda: self.visible
                and self.controls.get(control.key) is control
                and control.enabled
                and any(c is control for c in self.visible_controls(clip)),
            )
            field = control.options["event_field"]
            try:
                row = field.entry(context)
                self.menu_error = None
                menu = Menu(
                    target,
                    (row,),
                    (x, y),
                    clip,
                    context=context,
                    measure=menu_measure,
                    on_tip=self._tooltip_wake,
                    on_error=lambda error: setattr(self, "menu_error", str(error)),
                )
                menu.motion.bind(
                    (*self._animation_parents, self.animation, control.motion.settings),
                    self._wake_motion,
                )
                menu.choose(0, context)
                self.context_menu = menu
                self.context_focus = control
            except (ReferenceError, RuntimeError, ValueError) as error:
                self.menu_error = str(error)
            return True
        previous = self.overlay
        used = self._event(event, x, y, clip, clipboard=clipboard, context=context)
        if self.keyboard_focus and not self.keyboard_focus.options["widget"].focused:
            self.keyboard_focus = None
        if self.overlay is not previous and self.overlay and "widget" in self.overlay:
            motion = self.overlay["widget"].motion
            owner = self.overlay.get("owner")
            self._bind_motion(motion, owner)
            motion.pulse("reveal", 0.12)
        return used

    def _event(self, event, x, y, clip, *, clipboard=None, context=None):
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
                        self._parse_number(self.editor.text)
                        if self.active.kind == "number"
                        else self.editor.text
                    )
                    if (
                        self.active.kind != "number"
                        or value != self.active.binding.read()
                    ):
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
                    and (
                        not widget.capturing
                        or self.overlay.get("owner") is not None
                        and self.overlay["owner"].kind in {"pointer", "search"}
                    )
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
                numeric = self.active.options.get("numeric")
                if numeric is not None:
                    if numeric.snapshot() != self._numeric_state:
                        self.cancel()
                        return True
                    if not self._dragged and abs(x - self._drag_x) <= 3:
                        return True
                    self._dragged = True
                    step = (
                        ((maximum - minimum) / max(1.0, self.active.rect[2]))
                        if self.active.options.get("slider")
                        and 0 < maximum - minimum < 1e6
                        else numeric.drag(self._numeric_state)
                    )
                    if getattr(event, "shift", False):
                        step *= 0.25
                    self._drag_start += (x - self._drag_last) * step
                    self._drag_last = x
                    self._drag_start = max(minimum, min(maximum, self._drag_start))
                    value = self._drag_start
                    if getattr(event, "ctrl", False):
                        snap = max(
                            1e-12,
                            numeric.step
                            / (1 if numeric.integer else 100)
                            / numeric.display_scale(self._numeric_state),
                        )
                        value = round(value / snap) * snap
                    value = max(minimum, min(maximum, value))
                    self._write(value)
                else:
                    self._write(self._drag_start + delta)
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                if self.active.options.get("numeric") and not self._dragged:
                    self.editor = Text(self._initial_text)
                else:
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
        elif control.kind in {"pointer", "search"}:
            try:
                picker = (
                    control.options["search_field"].open()
                    if control.kind == "search"
                    else control.options["pointer_field"].picker(self, control)
                )
                picker.glass_blur = 0.7
                scale = min(1.0, clip[2] / picker.width, clip[3] / picker.height)
                w, h = picker.width * scale, picker.height * scale
                self.overlay = {
                    "widget": picker,
                    "owner": control,
                    "rect": (
                        clip[0] + (clip[2] - w) / 2,
                        clip[1] + (clip[3] - h) / 2,
                        w,
                        h,
                    ),
                }
                self.menu_error = None
            except (ReferenceError, RuntimeError, ValueError) as error:
                self.menu_error = str(error)
        elif control.kind == "decorator":
            model = control.options["decorator"]
            if model is not None:
                try:
                    if model.state() == "DRIVEN":
                        self.open_context(control, x, y, clip, context=context)
                    else:
                        model.click(self, control, context)
                except (ReferenceError, RuntimeError, ValueError) as error:
                    self.menu_error = str(error)
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
                        "owner": control,
                        "rect": (
                            clip[0] + (clip[2] - w) / 2,
                            clip[1] + (clip[3] - h) / 2,
                            w,
                            h,
                        ),
                    }
                return True
            if control.kind == "text" or event.value == "DOUBLE_CLICK":
                self.editor = Text(self._initial_text)
            else:
                self._drag_x = x
                self._drag_start = control.binding.read()
                self._drag_last = x
                self._dragged = False
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

    def _parse_number(self, text):
        numeric = self.active.options.get("numeric")
        if numeric:
            if numeric.snapshot() != self._numeric_state:
                raise ValueError("Unit settings changed; cancel and reopen the field")
            return numeric.parse(text, self.edit.before, self._numeric_state)
        return number(text)

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
