"""Registered Python panels in retained custom canvases; no native popup widgets."""

from .registered_menu import RegisteredMenu, Proxy, LIMIT
from .operator_enum import context_key
from .hosts.menu_context import override
from .widgets.base import Widget
from .context_menu import Entry, inside
from itertools import count

_open_serial = count()


def panel_class(name):
    import bpy

    cls = bpy.types.Panel.bl_rna_get_subclass_py(name)
    if cls is None:
        raise ValueError(f"Registered panel {name!r} is unavailable")
    return cls


class PanelProxy(Proxy):
    is_popover = True


class RegisteredPanel(RegisteredMenu):
    lookup = staticmethod(panel_class)

    def __init__(self, layout, name, *, source=None):
        super().__init__(layout, name, source=source)
        self.direction = "VERTICAL"
        self.header = getattr(self.cls, "draw_header", None)
        self.header_identity = (
            self.header,
            tuple(getattr(self.header, "_draw_funcs", ())),
        )
        self.poll_ok = self.available(layout.context)

    def check(self, context, scope=None, *, poll=True):
        super().check(context, scope, poll=poll)
        header = getattr(self.cls, "draw_header", None)
        if (header, tuple(getattr(header, "_draw_funcs", ()))) != self.header_identity:
            raise ReferenceError("Panel header changed; rebuild the controls")

    def refresh_poll(self, context):
        self.poll_ok = self.available(context or self.context)

    def context_rows(self, target, context):
        from .context_menu import default_entries

        rows = list(default_entries(target, context)) if self.source else []
        provider = self.layout.canvas.context_provider
        if provider:
            rows.extend(provider(target, context))
        return tuple(rows)

    def attach(self, control):
        def rows(target, context):
            return (
                Entry(
                    "OPEN_POPOVER",
                    "Open " + self.label,
                    lambda t, c: self.layout.canvas.open_panel(
                        control, self.layout.canvas._event_clip, c
                    ),
                    enabled=lambda t, c: self.available(c),
                ),
                *self.context_rows(target, context),
            )

        control.options.update(
            panel_model=self,
            context_menu=rows,
            enabled=lambda: self.poll_ok and self.available(self.context, poll=False),
        )
        self.layout.canvas._panel_buttons = True

    def build(self, parent, owner, context):
        from .canvas import Canvas
        from .layout import Layout

        scope = context_key(context)
        self.check(context, scope)
        depth = getattr(parent, "_popover_depth", 0)
        if depth >= 3:
            raise ValueError("Popover nesting exceeds three levels")
        child = Canvas(
            parent.theme,
            context_provider=parent.context_provider,
            menu_commit=parent.menu_commit,
            shortcut_registry=parent.shortcut_registry,
            shortcut_namespace=f"{parent.shortcut_namespace}:{self.name}:{next(_open_serial)}",
            menu_search_threshold=parent.menu_search_threshold,
        )
        child._popover_depth = depth + 1
        child._scoped_shortcuts = {}
        child.wide_numeric_motion_scale = parent.wide_numeric_motion_scale
        child.bind_animation(
            (*parent._animation_parents, parent.animation, owner.motion.settings),
            lambda: parent._animation_wake() if parent._animation_wake else None,
        )
        child.bind_context_tooltips(parent._tooltip_wake)
        child.set_text_measure(parent.text_measure, parent._text_measure_key)
        ui = Layout(
            child,
            context,
            resolve=self.layout.resolve,
            commit=self.layout.commit,
            state=self.layout.state,
            source=self.layout.source,
            pointer_sources=self.layout.pointer_sources,
            id_actions=self.layout.id_actions,
        )
        ui._is_popover = True
        ui.operator_context = self.invocation
        ui._context_pointers = dict(self.pointers.values())
        try:
            with override(context, self.pointers.values()):
                if "HIDE_HEADER" not in getattr(self.cls, "bl_options", set()):
                    ui.title(
                        text=self.label,
                        text_ctxt=getattr(self.cls, "bl_translation_context", "*"),
                    )
                self.cls.draw(PanelProxy(self.cls, ui), context)
            self.check(context, scope)
            if len(child.controls) > LIMIT:
                raise ValueError("Popover exceeds 4096 controls")
            guard_controls(
                self,
                child,
                tuple(child.controls.values()),
                context,
                scope,
                owner_valid=lambda: child.visible
                and parent.controls.get(owner.key) is owner
                and owner.enabled
                and getattr((parent.overlay or {}).get("widget"), "canvas", None)
                is child,
            )
            return PanelPopover(self, parent, owner, child, scope)
        except Exception:
            child.cancel()
            raise


class PanelPopover(Widget):
    """Host-unit layout, scrolling and nested input behind Canvas.open_widget."""

    def __init__(self, model, parent, owner, canvas, scope):
        super().__init__()
        self.model, self.parent, self.owner = model, parent, owner
        self.canvas, self.scope = canvas, scope
        self.scroll = 0.0
        self.scroll_drag = None
        units = getattr(model.cls, "bl_ui_units_x", 0) or 16
        self.preferred_width = min(960.0, max(160.0, float(units) * 20.0))

    def dimensions(self, font_size, available_width, available_height=None):
        self.canvas.theme = self.parent.theme
        self.canvas.wide_numeric_motion_scale = self.parent.wide_numeric_motion_scale
        self.width = max(1.0, min(self.preferred_width, available_width))
        height = self.canvas.arrange(self.width)
        self.height = max(
            1.0,
            min(height, available_height if available_height is not None else height),
        )
        self.scroll = min(self.scroll, max(0.0, height - self.height))
        return self.width, self.height

    def anchor(self, owner, clip):
        return panel_position(
            owner, clip, (self.width, self.height), self.model.direction
        )

    def valid(self, context, *, poll=True):
        return (
            self.parent.controls.get(self.owner.key) is self.owner
            and self.owner.enabled
            and self.model.available(
                context or self.model.context, self.scope, poll=poll
            )
        )

    @property
    def clip(self):
        return (0, self.scroll, self.width, self.height)

    def cancel(self):
        self.scroll_drag = None
        if self.canvas.shortcut_registry:
            for token in self.canvas._scoped_shortcuts.values():
                self.canvas.shortcut_registry.release(token)
            self.canvas._scoped_shortcuts.clear()
        self.canvas.park()
        super().cancel()

    def advance(self):
        return self.canvas.advance_animations(self.clip)

    def scrollbar(self):
        limit = max(0.0, self.canvas.height - self.height)
        track = (self.width - 8, 6, 3, max(1, self.height - 12))
        size = min(
            track[3], max(12.0, track[3] * self.height / max(1, self.canvas.height))
        )
        travel = track[3] - size
        return (
            (
                track[0],
                track[1] + travel * self.scroll / limit if limit else track[1],
                track[2],
                size,
            ),
            track,
            travel,
            limit,
        )

    def scroll_to(self, value):
        self.scroll = min(max(0.0, value), max(0.0, self.canvas.height - self.height))
        self.canvas.blur_focus()

    def dispatch(self, event, x, y, *, context=None, clipboard=None, menu_measure=None):
        """Logical input. The parent retains dismissal and outside pass-through."""
        if not self.valid(context):
            self.parent.cancel()
            self.parent.menu_error = "Popover owner, registration or context changed"
            return inside((0, 0, self.width, self.height), x, y)
        child = self.canvas
        self.motion.input(event, x, y)
        press = event.value in {"PRESS", "DOUBLE_CLICK"}
        thumb, track, travel, limit = self.scrollbar()
        if self.scroll_drag is not None:
            if (
                press
                and event.type in {"ESC", "RIGHTMOUSE"}
                or event.type == "WINDOW_DEACTIVATE"
            ):
                self.scroll_drag = None
                self.capturing = False
                return True
            if event.type == "MOUSEMOVE":
                self.scroll_to(
                    (y - self.scroll_drag - track[1]) * limit / max(1, travel)
                )
            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                self.scroll_drag = None
                self.capturing = False
            return True
        if (
            limit
            and not (child.edit or child.overlay or child.context_menu)
            and inside((self.width - 12, 0, 12, self.height), x, y)
            and press
        ):
            if event.type == "LEFTMOUSE":
                self.scroll_drag = (
                    y - thumb[1]
                    if thumb[1] <= y <= thumb[1] + thumb[3]
                    else thumb[3] / 2
                )
                self.scroll_to(
                    (y - self.scroll_drag - track[1]) * limit / max(1, travel)
                )
                self.capturing = True
                return True
            if event.type == "RIGHTMOUSE":
                from .context_menu import Menu, Target

                child.context_menu = Menu(
                    Target("popover-scroll", valid=lambda: self.valid(context)),
                    (
                        Entry("TOP", "Scroll to Top", lambda t, c: self.scroll_to(0)),
                        Entry(
                            "BOTTOM",
                            "Scroll to Bottom",
                            lambda t, c: self.scroll_to(limit),
                        ),
                    ),
                    (x, y + self.scroll),
                    self.clip,
                    context=context,
                    on_tip=child._tooltip_wake,
                )
                child.context_menu.motion.bind(
                    (*child._animation_parents, child.animation), child._wake_motion
                )
                child.context_menu.motion.pulse("reveal", 0.12)
                return True
        contained = inside((0, 0, self.width, self.height), x, y)
        captured = bool(
            child.edit or child.overlay or child.context_menu or child.widget_capture
        )
        if event.type == "WINDOW_DEACTIVATE":
            self.parent.cancel()
            return False
        if press and event.type in {"ESC", "RIGHTMOUSE"} and not captured:
            if event.type == "ESC" or not contained:
                self.parent.cancel()
                return contained
        if press and event.type == "LEFTMOUSE" and not contained and not captured:
            self.parent.cancel()
            return False
        if (
            event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}
            and contained
            and not captured
        ):
            old = self.scroll
            step = -1 if event.type == "WHEELUPMOUSE" else 1
            self.scroll = min(
                max(0.0, self.scroll + step * self.canvas.theme.row_height * 3),
                max(0, child.height - self.height),
            )
            if old != self.scroll:
                child.blur_focus()
            return True
        used = child.event(
            event,
            x,
            y + self.scroll,
            self.clip,
            clipboard=clipboard,
            context=context,
            menu_measure=menu_measure,
        )
        if child.menu_error:
            self.parent.menu_error = child.menu_error
        # Hover redraws must reach the owning host even when no spring is active.
        return used or contained and event.type == "MOUSEMOVE"

    def paint(self, rect, font, palette, *, backdrop=None):
        from .gpu import glass, skin
        from .gpu.paint import paint
        from .gpu.typography import flush_text

        if not self.valid(self.model.context, poll=False):
            return
        x, y, width, height = rect
        scale = width / self.width
        if backdrop is None or not glass.lens(
            backdrop,
            rect,
            self.canvas.theme.radius * scale,
            palette["surfaces"]["card"][0],
            blur=0.7,
        ):
            skin.draw(
                rect,
                palette["surfaces"]["card"][0],
                radius=self.canvas.theme.radius * scale,
            )
        content_height = self.canvas.height * scale
        paint(
            self.canvas,
            (
                x,
                y + height - content_height + self.scroll * scale,
                width,
                content_height,
            ),
            rect,
            font=font,
            backdrop=backdrop,
            palette=palette,
        )
        flush_text(font)
        thumb, track, _, limit = self.scrollbar()
        if limit:
            from .widgets.base import Painter

            painter = Painter(
                rect,
                self.width,
                self.height,
                font,
                palette,
                backdrop,
                motion=self.motion,
            )
            painter.surface(track, "track", 2, 0, motion_key=False)
            painter.surface(thumb, "thumb", 2, 0.6, motion_key="scroll")
            self.motion.region("scroll", (self.width - 12, 0, 12, self.height))


def panel_group(layout, space_type, region_type, context, category):
    """Snapshot Python registrations on explicit authoring, never during paint."""
    import bpy

    fields = bpy.types.Panel.bl_rna.properties
    for key, value in (("bl_space_type", space_type), ("bl_region_type", region_type)):
        if value not in fields[key].enum_items:
            raise ValueError(f"Unknown panel {key}: {value}")
    pending = list(bpy.types.Panel.__subclasses__())
    classes, seen = [], set()
    while pending:
        cls = pending.pop(0)
        if cls in seen:
            continue
        seen.add(cls)
        if len(seen) > 4096:
            raise ValueError("Panel registry exceeds bounded discovery")
        pending.extend(cls.__subclasses__())
        if (
            getattr(cls, "bl_space_type", None) == space_type
            and getattr(cls, "bl_region_type", None) == region_type
            and getattr(cls, "bl_context", "") == context
            and (not category or getattr(cls, "bl_category", "") == category)
            and not getattr(cls, "bl_parent_id", "")
        ):
            name = getattr(cls, "bl_idname", "") or cls.__name__
            try:
                if panel_class(name) is cls and RegisteredPanel(layout, name).available(
                    layout.context
                ):
                    classes.append((getattr(cls, "bl_order", 0), name))
            except ValueError:
                continue
    if len(classes) > 256:
        raise ValueError("Panel group exceeds 256 openers")
    return tuple(name for _, name in sorted(classes, key=lambda item: item[0]))


def guard_controls(model, canvas, controls, context, scope, owner_valid=lambda: True):
    for control in controls:
        prior_valid = control.options.get("valid_context")
        prior_guard = control.options.get("activation_guard")

        def valid(previous=prior_valid):
            return (
                owner_valid()
                and (previous is None or previous())
                and model.available(context, scope, poll=False)
            )

        def guard(ctx, previous=prior_guard):
            if not owner_valid():
                raise ReferenceError("Popover opener disappeared")
            if previous:
                previous(ctx)
            model.check(ctx or context, scope)

        control.options.update(valid_context=valid, activation_guard=guard)
        if control.action is not None:
            action = control.action

            def guarded_action(action=action, guard=guard):
                guard(context)
                return action()

            control.action = guarded_action
    if controls:
        canvas._context_guarded = True


def author(layout, panel, **options):
    """Header and opener authoring is atomic, including unsupported callbacks."""
    if panel in layout._panel_stack or len(layout._panel_stack) >= 3:
        raise ValueError("Recursive panel header exceeds supported bounds")
    model = RegisteredPanel(layout, panel)
    model.direction = options["direction"]
    canvas = layout.canvas
    before = set(canvas.controls)
    children = list(layout.group.children)
    scope = context_key(layout.context)
    try:
        group = layout
        if model.header is not None and model.poll_ok:
            group = layout.row(align=True)
            group._is_popover = True
            group._panel_stack = (*layout._panel_stack, panel)
            with override(layout.context, model.pointers.values()):
                model.header(PanelProxy(model.cls, group), layout.context)
            added = tuple(c for k, c in canvas.controls.items() if k not in before)
            if len(added) > LIMIT:
                raise ValueError("Panel header exceeds 4096 controls")
            guard_controls(model, canvas, added, layout.context, scope)
        control = group.group.button(
            layout._key("popover"),
            layout._text(
                options["text"] or model.label,
                options["text_ctxt"],
                options["translate"],
            ),
            None,
            icon=options["icon"],
        )
        model.attach(control)
    except Exception:
        for key in set(canvas.controls) - before:
            control = canvas.controls.pop(key)
            control.motion.clear()
            canvas._moving.discard(control.motion)
            canvas._motion_owners.pop(control.motion, None)
        layout.group.children[:] = children
        canvas._context_guarded = any(
            c.options.get("valid_context") for c in canvas.controls.values()
        )
        canvas._panel_buttons = any(
            c.options.get("panel_model") for c in canvas.controls.values()
        )
        canvas.invalidate()
        raise


def panel_position(owner, clip, size, direction):
    """Attachment in logical units; clamp to the same host clip as other widgets."""
    a, b, ow, oh = owner
    x, y, cw, ch = clip
    w, h = size
    if direction == "HORIZONTAL":
        left = a + ow + 4 if a + ow + 4 + w <= x + cw else a - w - 4
        top = b + (oh - h) / 2
    else:
        left = a + (ow - w) / 2
        top = b + oh + 4 if b + oh + 4 + h <= y + ch else b - h - 4
    return max(x, min(left, x + cw - w)), max(y, min(top, y + ch - h)), w, h
