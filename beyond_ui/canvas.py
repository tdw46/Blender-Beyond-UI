"""Retained custom controls, independent of bpy, native layout and scene data.

Hosts own event delivery, redraw, undo, translation and visibility. Paint reads
only visible controls. Layout caches geometry until structure or width changes.
"""

from dataclasses import dataclass, field, replace
from weakref import WeakSet
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
    _layout_enabled: bool = field(default=True, repr=False, compare=False)

    @property
    def enabled(self):
        if not self._layout_enabled:
            return False
        valid = self.options.get("valid_context")
        if valid is not None and not valid():
            return False
        value = self.options.get("enabled", True)
        return bool(value() if callable(value) else value) and (
            self.binding is None or self.binding.valid()
        )


class Group:
    def __init__(self, canvas, kind="column", parent=None, **options):
        self.canvas, self.kind, self.parent = canvas, kind, parent
        self.options = options
        self._effective_enabled = bool(
            (parent is None or parent._effective_enabled)
            and options.get("enabled", True)
            and options.get("active", True)
        )
        self.children = []
        self.rect = (0.0, 0.0, 0.0, 0.0)
        self._sync_size_policy()

    def _sync_size_policy(self):
        registry = self.canvas._sized_groups
        if any(
            self.options.get(name, 0)
            for name in ("scale_x", "scale_y", "ui_units_x", "ui_units_y")
        ):
            registry.add(self)
        else:
            registry.discard(self)

    def _refresh_enabled(self):
        """Resolve inherited eligibility on policy changes, never during paint."""
        inherited = self.parent._effective_enabled if self.parent is not None else True
        self._effective_enabled = bool(
            inherited
            and self.options.get("enabled", True)
            and self.options.get("active", True)
        )
        for child in self.children:
            if isinstance(child, Group):
                child._refresh_enabled()
            else:
                child._layout_enabled = self._effective_enabled

    def _group(self, kind, **options):
        child = Group(self.canvas, kind, self, **options)
        self.children.append(child)
        self.canvas.invalidate()
        return child

    def row(self, **options):
        return self._group("row", **options)

    def column(self, **options):
        return self._group("column", **options)

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
        control = Control(
            key,
            kind,
            label,
            binding,
            action,
            options,
            _layout_enabled=self._effective_enabled,
        )
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
        menu_search_threshold=12,
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
        self._sized_groups = WeakSet()
        self._composites = {}
        self._dirty = True
        self._width = None
        self.height = 0.0
        self.layout_count = 0
        self.text_measure = None
        self._text_measure_key = None
        self.schema_revision = 0
        self.backdrop_revision = 0
        self.edit = None
        self.editor = None
        self.active = None
        self.overlay = None
        self._event_clip = None
        self.context_menu = None
        self.context_provider = context_provider
        self.menu_commit = menu_commit
        self.shortcut_registry = shortcut_registry
        self.shortcut_namespace = shortcut_namespace
        self.menu_search_threshold = menu_search_threshold
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
        for control in self._composites.values():
            widget = control.options["widget"]
            for child, _, _ in widget.all_children():
                child.wide_numeric_motion_scale = value
        widget = (self.overlay or {}).get("widget")
        if hasattr(widget, "canvas"):
            widget.canvas.wide_numeric_motion_scale = value

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
        child_active = False
        for control in self._composites.values() if self.visible else ():
            widget = control.options["widget"]
            local_clip = None
            if clip is not None:
                a, b, w, h = control.rect
                x, y, cw, ch = clip
                if not (a < x + cw and a + w > x and b < y + ch and b + h > y):
                    widget.cancel()
                    continue
                sx, sy = widget.width / max(1, w), widget.height / max(1, h)
                local_clip = ((x - a) * sx, (y - b) * sy, cw * sx, ch * sy)
            child_active = widget.advance(local_clip) or child_active
        if self.overlay and hasattr(self.overlay.get("widget"), "advance"):
            child_active = self.overlay["widget"].advance() or child_active
        return bool(self._moving) or child_active

    def open_widget(self, widget, owner, clip=None):
        """One host-relative scale and clip policy for every compound popover."""
        clip = clip or self._event_clip or (0, 0, self._width or 1, self.height)
        w, h = widget.dimensions(self.theme.font_size, clip[2], clip[3])
        widget.glass_blur = 0.7
        rect = (clip[0] + (clip[2] - w) / 2, clip[1] + (clip[3] - h) / 2, w, h)
        if owner is not None and hasattr(widget, "anchor"):
            rect = widget.anchor(owner.rect, clip)
        self.overlay = {
            "widget": widget,
            "owner": owner,
            "clip": tuple(clip),
            "rect": rect,
        }

    def active_menu(self):
        if self.context_menu is not None:
            return self.context_menu
        widget = (self.overlay or {}).get("widget")
        if hasattr(widget, "canvas"):
            return widget.canvas.active_menu()
        for control in self._composites.values():
            widget = control.options["widget"]
            if hasattr(widget, "active_menu"):
                menu = widget.active_menu()
                if menu is not None:
                    return menu
        return None

    def open_panel(self, control, clip, context=None):
        model = control.options["panel_model"]
        context = context or model.context
        clip = clip or self._event_clip or (0, 0, self._width or 1, self.height)
        widget = None
        try:
            model.refresh_poll(context)
            if not control.enabled:
                return False
            widget = model.build(self, control, context)
            self.cancel()
            self.open_widget(widget, control, clip)
            widget.canvas.bind_shortcuts(context, widget.clip)
            widget.opened(context)
            self._bind_motion(widget.motion, control)
            widget.motion.pulse("reveal", 0.12)
            self.menu_error = None
            return True
        except Exception as error:
            if widget is not None:
                if (self.overlay or {}).get("widget") is widget:
                    self.cancel()
                else:
                    widget.cancel()
            self.menu_error = str(error)
            return False

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
        if hasattr((self.overlay or {}).get("widget"), "canvas"):
            self.cancel()
        self.backdrop_revision += 1
        self.close_context()
        self._dirty = True
        self._composites.clear()
        for control in self.controls.values():
            if hasattr(control.options.get("widget"), "route"):
                self._composites[control.key] = control
                control.options["widget"].cancel()
            control.motion.clear()
            if control.kind == "decorator" and control.options["decorator"] is not None:
                try:
                    control.options["decorator"].refresh()
                except (ReferenceError, RuntimeError):
                    pass

    def set_text_measure(self, callback, key):
        """Host-owned, retained font measurement; change key on font/size revision."""
        if key != self._text_measure_key:
            self.text_measure = callback
            self._text_measure_key = key
            self.invalidate()

    def arrange(self, width):
        width = max(1.0, float(width))
        if not self._dirty and width == self._width:
            return self.height
        from .flow import Plan

        t = self.theme
        plan = Plan(t, self.text_measure, self if self._sized_groups else None)
        inner = max(0.0, width - 2 * t.padding)
        plan.place(self, t.padding, t.padding, inner)
        self.height = self.rect[3] + 2 * t.padding
        self._width = width
        self._scale_numeric_motion()
        self._dirty = False
        self.layout_count += 1
        return self.height

    def visible_controls(self, clip, *, composites=False):
        if not self.visible:
            return
        x, y, w, h = clip
        controls = self._composites if composites else self.controls
        for control in controls.values():
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
        from copy import deepcopy
        from types import SimpleNamespace
        from .enum_field import EnumField

        field = control.options.get("enum_field") or EnumField(
            control.binding,
            lambda: (
                SimpleNamespace(identifier=v, name=label)
                for v, label in control.options["items"]
            ),
        )
        try:
            before = deepcopy(control.binding.read())
            items = field.snapshot()
            if not items:
                raise ValueError("No enum choices are available in this context")
            rows = []
            divider = False
            for index, item in enumerate(items):
                if item.identifier == "":
                    if item.name:
                        rows.append(
                            Entry(
                                f"__heading_{index}",
                                item.name,
                                enabled=False,
                                heading=True,
                                divider=divider,
                                tip=item.description,
                            )
                        )
                        divider = False
                    else:
                        divider = True
                    continue
                rows.append(
                    Entry(
                        f"enum:{item.identifier}",
                        item.name,
                        lambda target, ctx, item=item: field.choose(
                            item, original=before
                        ),
                        checked=field.selected(item.identifier, before),
                        tip=item.description,
                        divider=divider,
                    )
                )
                divider = False
            if not any(row.action is not None for row in rows):
                raise ValueError("No enum choices are available in this context")
            self.cancel()
            target = Target(
                control.key,
                binding=control.binding,
                valid=lambda: self.visible
                and self.controls.get(control.key) is control
                and control.enabled
                and control.binding.valid()
                and control.binding.read() == before,
            )
            self.context_menu = Menu(
                target,
                rows,
                (control.rect[0], control.rect[1] + control.rect[3]),
                clip,
                context=context,
                row_limit=len(rows),
                search_threshold=self.menu_search_threshold,
                on_tip=self._tooltip_wake,
                on_error=lambda error: setattr(self, "menu_error", str(error)),
            )
            self.context_menu.page.highlight = next(
                (
                    i
                    for i, checked in enumerate(self.context_menu.page.checked)
                    if checked and self.context_menu.page.available[i]
                ),
                next(
                    (
                        i
                        for i, available in enumerate(self.context_menu.page.available)
                        if available
                    ),
                    0,
                ),
            )
            self.context_menu.reveal()
            self.context_focus = control
            self.menu_error = None
        except Exception as error:
            self.menu_error = str(error)
            return False
        self.context_menu.motion.bind(
            (*self._animation_parents, self.animation, control.motion.settings),
            self._wake_motion,
        )
        self.context_menu.motion.pulse("reveal", 0.12)
        return True

    def open_operator_menu(self, control, clip, context):
        from .context_menu import Menu, Target

        if not control.enabled:
            return False
        try:
            model = (
                control.options.get("menu_model") or control.options["operator_enum"]
            )
            context = context or model.context
            rows, valid = model.rows(context)
            self.cancel()
            menu = Menu(
                Target(
                    control.key,
                    valid=lambda: self.visible
                    and self.controls.get(control.key) is control
                    and control.enabled
                    and valid(),
                    commit=self.menu_commit,
                ),
                rows,
                (control.rect[0], control.rect[1] + control.rect[3]),
                clip,
                context=context,
                row_limit=4096 if control.options.get("menu_model") else len(rows),
                search_threshold=self.menu_search_threshold,
                visible_refresh=bool(control.options.get("menu_model")),
                on_tip=self._tooltip_wake,
                on_error=lambda error: setattr(self, "menu_error", str(error)),
            )
            self.context_menu = menu
            self.context_focus = control
            menu.motion.bind(
                (*self._animation_parents, self.animation, control.motion.settings),
                self._wake_motion,
            )
            menu.motion.pulse("reveal", 0.12)
            self.menu_error = None
            return True
        except Exception as error:
            self.menu_error = str(error)
            return False

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
            guard = control.options.get("activation_guard")
            if guard is not None:
                guard(ctx)
            if control.options.get("panel_model"):
                result = self.open_panel(control, clip, ctx)
            elif control.options.get("operator_enum") or control.options.get(
                "menu_model"
            ):
                result = self.open_operator_menu(control, clip, ctx)
            elif control.kind == "enum":
                result = self.open_enum_menu(control, clip, ctx)
            else:
                result = control.action()
            if getattr(ctx, "area", None):
                for region in ctx.area.regions:
                    region.tag_redraw()
            return result

        token = registry.bind(
            command,
            context,
            run,
            valid=lambda ctx: target.valid()
            and control.enabled
            and (ctx.scene.as_pointer() if ctx.scene else None) == scene,
        )
        if hasattr(self, "_scoped_shortcuts"):
            self._scoped_shortcuts[token[0]] = token
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
                binding = control.binding.frozen() if control.binding else None
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
                and (
                    not control.options.get("valid_context")
                    or control.options["valid_context"]()
                )
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
                    if (
                        control.kind == "enum"
                        or control.options.get("operator_enum")
                        or control.options.get("menu_model")
                        or control.options.get("panel_model")
                    ):
                        rows = [r for r in rows if r.key != "SHORTCUT"]
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
                row_limit=4096
                if control.options.get("operator_enum")
                or control.options.get("menu_model")
                else Menu.limit,
                search_threshold=self.menu_search_threshold,
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
        self._event_clip = clip
        # Registered inline menu draws retain a context, not just RNA addresses.
        candidate = None
        if getattr(self, "_context_guarded", False) and (
            self.edit or event.value in {"PRESS", "DOUBLE_CLICK"}
        ):
            candidate = (
                self.active
                or (self.overlay.get("owner") if self.overlay else None)
                or (self.context_focus if self.context_menu else None)
                or self.hit(x, y, clip, include_disabled=True)
            )
        guard = candidate.options.get("activation_guard") if candidate else None
        if guard is not None:
            try:
                guard(context)
            except (ReferenceError, RuntimeError, ValueError, AttributeError) as error:
                self.cancel()
                self.menu_error = str(error)
                from .context_menu import inside

                return event.value in {"PRESS", "DOUBLE_CLICK"} and (
                    event.type != "RIGHTMOUSE" or inside(clip, x, y)
                )
        if self.overlay and "widget" in self.overlay and "clip" in self.overlay:
            if tuple(clip) != self.overlay["clip"]:
                self.open_widget(
                    self.overlay["widget"], self.overlay.get("owner"), clip
                )
        panel_widget = (self.overlay or {}).get("widget")
        if hasattr(panel_widget, "dispatch"):
            a, b, w, h = self.overlay["rect"]
            return panel_widget.dispatch(
                event,
                (x - a) * panel_widget.width / max(1, w),
                (y - b) * panel_widget.height / max(1, h),
                context=context,
                clipboard=clipboard,
                menu_measure=menu_measure,
            )
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        if (
            getattr(self, "_panel_buttons", False)
            and not self.context_menu
            and (press or event.type == "MOUSEMOVE")
        ):
            candidate = self.hit(x, y, clip, include_disabled=True)
            model = candidate.options.get("panel_model") if candidate else None
            if model is not None:
                model.refresh_poll(context)
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
        if self._composites and not self.overlay:
            routed = (
                self.widget_capture
                or (
                    self.keyboard_focus
                    if event.type
                    not in {
                        "LEFTMOUSE",
                        "RIGHTMOUSE",
                        "MOUSEMOVE",
                        "WHEELUPMOUSE",
                        "WHEELDOWNMOUSE",
                        "TRACKPADPAN",
                    }
                    else None
                )
                or self.hit(x, y, clip, include_disabled=True)
            )
            widget = routed.options.get("widget") if routed else None
            if hasattr(widget, "route"):
                a, b, w, h = routed.rect
                sx, sy = widget.width / max(1, w), widget.height / max(1, h)
                used = widget.route(
                    event,
                    (x - a) * sx,
                    (y - b) * sy,
                    (
                        (clip[0] - a) * sx,
                        (clip[1] - b) * sy,
                        clip[2] * sx,
                        clip[3] * sy,
                    ),
                    context=context,
                    clipboard=clipboard,
                    menu_measure=menu_measure,
                )
                if used is not None:
                    self.widget_capture = routed if widget.capturing else None
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
            and (
                event.type in self.navigation_keys
                or getattr(
                    self.keyboard_focus.options["widget"], "wants_key", lambda e: False
                )(event)
            )
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
                    search_threshold=self.menu_search_threshold,
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
            if "reveal" not in motion.tracks:
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
        if self.edit is not None and not self.edit.binding.valid():
            self.cancel()
            self.menu_error = "The edited owner or selection changed"
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
                        or value != self.edit.binding.read()
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
                track_width = self._drag_width
                delta = (x - self._drag_x) * (maximum - minimum) / max(1.0, track_width)
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
                        ((maximum - minimum) / max(1.0, track_width))
                        if self._drag_part == "track" and 0 < maximum - minimum < 1e6
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
                    if not self._dragged and abs(x - self._drag_x) <= 3:
                        return True
                    self._dragged = True
                    value = self._drag_start + delta
                    if self._drag_part == "track":
                        value = max(minimum, min(maximum, value))
                    self._write(value)
            elif kind == "LEFTMOUSE" and event.value == "RELEASE":
                if (
                    self.active.options.get("numeric") or self._drag_part == "field"
                ) and not self._dragged:
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
        if control.options.get("panel_model"):
            self.open_panel(control, clip, context)
            return True
        if control.kind == "button":
            if control.options.get("operator_enum") or control.options.get(
                "menu_model"
            ):
                self.open_operator_menu(control, clip, context)
            elif control.options.get("action_event"):
                control.options["action_event"](event)
            elif control.action:
                control.action()
        elif control.kind in {"pointer", "search"}:
            try:
                picker = (
                    control.options["search_field"].open()
                    if control.kind == "search"
                    else control.options["pointer_field"].picker(self, control)
                )
                self.open_widget(picker, control, clip)
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
            before = control.binding.read()
            self._begin(control)
            self._write(not before)
            self.finish()
            control.motion.retarget("body", before, control.binding.read())
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
                    self.open_widget(picker, control, clip)
                return True
            if control.kind == "text" or event.value == "DOUBLE_CLICK":
                self.editor = Text(self._initial_text)
            else:
                self._drag_x = x
                self._drag_start = control.binding.read()
                self._drag_last = x
                self._dragged = False
                self._drag_part = "field"
                self._drag_width = control.rect[2]
                if control.kind == "number" and control.options.get("slider", True):
                    from .scalar_geometry import slider_parts, usable_range

                    _, (tx, ty, tw), field = slider_parts(
                        control.rect, bool(control.label)
                    )
                    lo, hi = (
                        control.options.get("min", 0.0),
                        control.options.get("max", 1.0),
                    )
                    if (
                        tx - 7 <= x < field[0]
                        and abs(y - ty) <= 12
                        and usable_range(lo, hi)
                    ):
                        self._drag_part = "track"
                        self._drag_width = tw
                        self._dragged = True
                        value = lo + min(1.0, max(0.0, (x - tx) / tw)) * (hi - lo)
                        self._write(value)
                        self._drag_start = control.binding.read()
                        control.motion.pulse("handle", 0.55)
        elif control.kind == "enum":
            if control.options.get("menu_model"):
                self.open_operator_menu(control, clip, context)
            else:
                self.open_enum_menu(control, clip, context)
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
        if self.edit.binding.read() != value:
            self.edit.update(value)

    def paint(self, rect, clip, *, preferences=None, font=0, backdrop=None):
        from .gpu.paint import paint

        return paint(
            self, rect, clip, preferences=preferences, font=font, backdrop=backdrop
        )
