"""Registered Python UIList callbacks on retained custom row canvases.

Callbacks run on authoring, input or explicit refresh. Painting never invokes
draw_item, draw_filter, filter_items, or registry discovery.
"""

from dataclasses import replace
from inspect import signature, Parameter
from itertools import islice, count
from .registered_menu import Proxy, ContextArguments
from .operator_enum import context_key
from .hosts.menu_context import override
from .widgets.collection_list import CollectionList
from .bindings import Binding, Edit
from .context_menu import Entry, default_entries, inside

SHOW = 1 << 30
NEVER = 1 << 16
_serial = count()
SETTINGS = {
    "filter_name": ("query", ""),
    "use_filter_invert": ("invert", False),
    "use_filter_sort_alpha": ("alpha", False),
    "use_filter_sort_reverse": ("reverse", False),
    "use_filter_show": ("show_filter", False),
}


def list_class(name):
    import bpy
    from .layout import UnsupportedControl

    cls = bpy.types.UIList.bl_rna_get_subclass_py(name)
    if cls is None:
        raise UnsupportedControl(f"unavailable UIList {name}")
    return cls


def callbacks(cls):
    return tuple(
        (
            getattr(cls, name, None),
            tuple(getattr(getattr(cls, name, None), "_draw_funcs", ())),
        )
        for name in ("draw_item", "draw_filter", "filter_items")
    )


def python_callback(cls, name):
    value = getattr(cls, name, None)
    return value if callable(value) and hasattr(value, "__code__") else None


def filter_order(items, flags, order, reverse=False, invert=False):
    """RNA callback indices map original indices to destination positions."""
    size = len(items)
    flags, order = tuple(islice(flags, size + 1)), tuple(islice(order, size + 1))
    if flags and (
        len(flags) != size
        or any(type(x) is not int or not 0 <= x < 2**32 for x in flags)
    ):
        raise ValueError(
            "UIList filter_flags must be empty or one uint32 per source item"
        )
    if order and (
        len(order) != size
        or any(type(x) is not int for x in order)
        or set(order) != set(range(size))
    ):
        raise ValueError(
            "UIList filter_neworder must be empty or a full original-to-new permutation"
        )
    visible = [
        item
        for item in items
        if not flags
        or (bool(flags[item.index] & SHOW) != invert)
        and not flags[item.index] & NEVER
    ]
    if order:
        visible.sort(key=lambda item: order[item.index])
    if reverse:
        visible.reverse()
    return tuple(visible), flags


class ListProxy(Proxy):
    def __init__(self, widget):
        object.__setattr__(self, "widget", widget)
        object.__setattr__(self, "_metadata", {})
        super().__init__(widget.cls, None)

    def setting_meta(self, name):
        from .layout import UnsupportedControl

        if name in self._metadata:
            return self._metadata[name]
        meta = self.widget.cls.bl_rna.properties.get(name)
        for cls in self.widget.cls.__mro__:
            declaration = cls.__dict__.get("__annotations__", {}).get(name)
            keywords = getattr(declaration, "keywords", {})
            if any(key in keywords for key in ("get", "set", "update")) or callable(
                keywords.get("items")
            ):
                raise UnsupportedControl("UIList callback-backed setting " + name)
        if meta is not None and (
            getattr(meta, "is_array", False)
            or meta.type == "ENUM"
            and meta.is_enum_flag
        ):
            raise UnsupportedControl("UIList array/flag setting " + name)
        if len(self._metadata) >= 128:
            raise ValueError("UIList proxy exceeds 128 metadata lookups")
        self._metadata[name] = meta
        return meta

    def __getattr__(self, name):
        w = self.widget
        if name in SETTINGS:
            key, default = SETTINGS[name]
            return w.state.get(key, default)
        constants = {
            "layout_type": w.type,
            "list_id": w.list_id,
            "bitflag_filter_item": SHOW,
            "use_filter_sort_lock": w.sort_lock,
        }
        if name == "bitflag_item_never_show":
            # The public never-show flag was added after the oldest supported API.
            if name not in w.cls.bl_rna.properties:
                raise AttributeError(name)
            return NEVER
        if name in constants:
            return constants[name]
        meta = self.setting_meta(name)
        if (
            meta is not None
            and not meta.is_readonly
            and meta.type in {"BOOLEAN", "STRING", "INT", "FLOAT", "ENUM"}
            and not getattr(meta, "is_array", False)
        ):
            return w.state.setdefault("properties", {}).get(name, meta.default)
        return super().__getattr__(name)

    def __setattr__(self, name, value):
        if name in {"_cls", "layout"} or name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        w = self.widget
        if w.drawing:
            raise ValueError(
                "UIList draw/filter callbacks must not mutate their settings"
            )
        if name in SETTINGS:
            key, default = SETTINGS[name]
            if type(value) is not type(default):
                raise TypeError("UIList setting type changed")
            if w.sort_lock and key in {"alpha", "reverse"}:
                raise ValueError("UIList sorting is locked")
            w.state[key] = value
        else:
            meta = self.setting_meta(name)
            if meta is None or meta.is_readonly:
                raise AttributeError(name)
            if meta.type not in {
                "BOOLEAN",
                "STRING",
                "INT",
                "FLOAT",
                "ENUM",
            } or getattr(meta, "is_array", False):
                from .layout import UnsupportedControl

                raise UnsupportedControl("UIList non-scalar setting")
            from math import isfinite

            if (
                meta.type == "BOOLEAN"
                and type(value) is not bool
                or meta.type in {"STRING", "ENUM"}
                and not isinstance(value, str)
                or meta.type == "INT"
                and type(value) is not int
            ):
                raise TypeError("UIList setting has the wrong scalar type")
            if meta.type in {"INT", "FLOAT"} and (
                not isfinite(value) or not meta.hard_min <= value <= meta.hard_max
            ):
                raise ValueError("UIList numeric setting exceeds its bounds")
            if meta.type == "ENUM" and value not in meta.enum_items:
                raise ValueError("UIList enum setting is unavailable")
            w.state.setdefault("properties", {})[name] = value

    def property(self, layout, name, args):
        from .layout import UnsupportedControl

        w = self.widget
        meta = self.setting_meta(name)
        if meta is None or meta.is_readonly or getattr(meta, "is_array", False):
            raise UnsupportedControl("UIList readonly/array setting " + name)
        if (
            any(
                args[key]
                for key in (
                    "event",
                    "full_event",
                    "icon_only",
                    "icon_value",
                    "invert_checkbox",
                    "expand",
                )
            )
            or args["index"] != -1
        ):
            raise UnsupportedControl("UIList setting presentation options")
        binding = Binding(
            lambda: getattr(self, name),
            lambda value: setattr(self, name, value),
            lambda: layout.canvas.visible
            and w.available(w.context, poll=False)
            and (
                w.drawing
                or layout.canvas is w.filter_canvas
                and w.filter_visible
                or layout.canvas in w.live_canvases
            ),
            lambda before, after: setattr(w, "pending", True),
        )
        label = layout._text(
            args["text"] or meta.name, args["text_ctxt"], args["translate"]
        )
        key = layout._key("list-setting")
        group = layout.group
        if meta.type == "BOOLEAN":
            control = group.toggle(key, label, binding)
        elif meta.type == "STRING":
            control = group.text(key, label, binding)
        elif meta.type in {"INT", "FLOAT"}:
            from .numeric import Numeric

            control = group.number(
                key,
                label,
                binding,
                min=meta.soft_min,
                max=meta.soft_max,
                hard_min=meta.hard_min,
                hard_max=meta.hard_max,
                integer=meta.type == "INT",
                slider=args["slider"],
                numeric=Numeric(meta, layout.context),
            )
        elif meta.type == "ENUM" and not meta.is_enum_flag:
            control = group.enum(
                key,
                label,
                binding,
                items=tuple((i.identifier, i.name) for i in meta.enum_items),
            )
        else:
            raise UnsupportedControl("UIList setting " + meta.type)

        def entries(target, context):
            def reset(t, c):
                edit = Edit(binding)
                edit.update(SETTINGS[name][1] if name in SETTINGS else meta.default)
                edit.finish()

            return (
                Entry(
                    "RESET_LIST_SETTING",
                    "Reset to Default",
                    reset,
                    enabled=lambda t, c: t.editable(),
                ),
                *default_entries(target, context),
            )

        control.options.update(context_menu=entries, list_setting=name)
        if w.sort_lock and name in {"use_filter_sort_alpha", "use_filter_sort_reverse"}:
            control.options["enabled"] = False
        return control


class RegisteredList(CollectionList):
    row_height = 36.0

    def __init__(self, source, state, *, name, list_id, **options):
        self.cls, self.name, self.list_id = list_class(name), name, list_id
        self.callback_key = callbacks(self.cls)
        self.context = source.layout.context
        self.scope = context_key(self.context)
        self.pointers = ContextArguments()
        self.pointers.capture(
            {**source.layout._context_pointers, **source.layout._context_strings}
        )
        self.parent = source.layout.canvas
        self.owner = None
        self.cache, self.filter_canvas = {}, None
        self.row_map, self.live_canvases = {}, set()
        self.pending = self.drawing = False
        self.faulted = False
        self.data_pending = False
        self.flags = ()
        self.active_child = None
        self.builds = 0
        self.epoch = 0
        self.proxy = ListProxy(self)
        self.draw_item = python_callback(self.cls, "draw_item")
        self.draw_filter = python_callback(self.cls, "draw_filter")
        self.filter_items = python_callback(self.cls, "filter_items")
        if self.draw_item is None:
            from .layout import UnsupportedControl

            raise UnsupportedControl("UIList without a Python draw_item callback")
        super().__init__(source, state, **options)

    def check(self, context, scope=None, *, poll=True):
        if self.faulted:
            raise ReferenceError("UIList callback failed; refresh or rebuild it")
        if poll and (
            list_class(self.name) is not self.cls
            or callbacks(self.cls) != self.callback_key
        ):
            raise ReferenceError("UIList registration/callbacks changed; rebuild it")
        if (
            context_key(context) != self.scope
            or not self.pointers.valid()
            or not self.source.valid()
        ):
            raise ReferenceError("UIList context or collection owner changed")
        if (
            not self.parent.visible
            or self.owner is not None
            and (
                self.parent.controls.get(self.owner.key) is not self.owner
                or not self.owner.enabled
            )
        ):
            raise ReferenceError("UIList owner is unavailable")

    def available(self, context, scope=None, *, poll=True):
        try:
            self.check(context, scope, poll=poll)
            return True
        except (
            ReferenceError,
            RuntimeError,
            AttributeError,
            ValueError,
            NotImplementedError,
        ):
            return False

    def invoke(self, fn, *args):
        self.check(self.context)
        self.drawing = True
        try:
            with override(self.context, self.pointers.values()):
                result = fn(self.proxy, *args)
            self.check(self.context)
            return result
        finally:
            self.drawing = False

    def reorder(self):
        if self.filter_items is None:
            super().reorder()
            self.flags = ()
        else:
            import bpy

            result = self.invoke(
                self.filter_items, self.context, self.source.resolve(), self.source.prop
            )
            if not isinstance(result, (tuple, list)) or len(result) != 2:
                raise ValueError("UIList filter_items must return flags and order")
            self.filtered, self.flags = filter_order(
                self.source.items,
                *result,
                reverse=self.state.get("reverse", False),
                invert=bpy.app.version < (4, 5, 0) and self.state.get("invert", False),
            )
            if hasattr(self, "viewport"):
                self.scroll_to(self.offset)
        self.epoch += 1

    def child(self, item, width):
        from .canvas import Canvas
        from .layout import Layout, UnsupportedControl
        from .popover import guard_controls

        canvas = Canvas(
            replace(self.parent.theme, row_height=32, gap=2, padding=0, font_size=11),
            context_provider=self.parent.context_provider,
            menu_commit=self.parent.menu_commit,
            shortcut_registry=self.parent.shortcut_registry,
            shortcut_namespace=f"{self.parent.shortcut_namespace}:list:{next(_serial)}",
        )
        canvas._scoped_shortcuts = {}
        canvas.wide_numeric_motion_scale = self.parent.wide_numeric_motion_scale
        canvas.bind_animation(
            (
                *self.parent._animation_parents,
                self.parent.animation,
                self.motion.settings,
            ),
            lambda: self.parent._animation_wake()
            if self.parent._animation_wake
            else None,
        )
        canvas.bind_context_tooltips(self.parent._tooltip_wake)
        canvas.set_text_measure(self.parent.text_measure, self.parent._text_measure_key)
        base = self.source.layout

        def resolver(data):
            original = base.resolve(data) if base.resolve else lambda: data

            def current():
                if not canvas.visible:
                    raise ReferenceError("List row canvas was released")
                self.check(self.context, poll=False)
                if item is not None and not self.source.valid_item(item):
                    raise ReferenceError("List row owner changed during edit")
                return original()

            return current

        def commit(before, after):
            base.commit(before, after)
            self.pending = self.data_pending = True

        ui = Layout(
            canvas,
            self.context,
            resolve=resolver,
            commit=commit,
            state={"_inside_list_callback": True},
            source=base.source,
            pointer_sources=base.pointer_sources,
            id_actions=base.id_actions,
            list_identity=base.list_identity,
        )
        ui.operator_context = base.operator_context
        ui._context_pointers = dict(base._context_pointers)
        ui._context_strings = dict(base._context_strings)
        ui.use_property_decorate = False
        try:
            if item is None:
                self.invoke(self.draw_filter, self.context, ui)
            else:
                if not self.source.valid_item(item):
                    raise ReferenceError("List row changed before authoring")
                row = ui.row(align=True)
                args = (
                    self.context,
                    row,
                    self.source.resolve(),
                    self.source.collection()[item.index],
                    0,
                    self.source.active_resolve(),
                    self.source.active_prop,
                    item.index,
                    self.flags[item.index] if self.flags else 0,
                )
                params = tuple(signature(self.draw_item).parameters.values())
                n = len(params) - 1
                if any(p.kind == Parameter.VAR_POSITIONAL for p in params):
                    n = len(args)
                if n < 6:
                    raise UnsupportedControl("UIList draw_item signature")
                self.invoke(self.draw_item, *args[:n])
            if len(canvas.controls) > 128:
                raise ValueError("UIList callback exceeds 128 controls")
            canvas.arrange(width)
            if item is not None and canvas.height > self.row_height - 4 + 0.01:
                raise UnsupportedControl("multiline/oversized UIList row")
            if item is None and canvas.height > 480:
                raise UnsupportedControl("UIList filter taller than 480 logical units")

            def live():
                return (
                    canvas.visible
                    and (
                        self.filter_canvas is canvas
                        and self.state.get("show_filter", False)
                        if item is None
                        else canvas in self.live_canvases
                    )
                    and (item is None or self.source.valid_item(item))
                )

            guard_controls(
                self,
                canvas,
                tuple(canvas.controls.values()),
                self.context,
                self.scope,
                live,
            )
            for control in canvas.controls.values():
                control.motion.clock = self.motion.clock
                if control.action is not None:
                    action = control.action

                    def changed_action(action=action):
                        result = action()
                        self.pending = self.data_pending = True
                        return result

                    control.action = changed_action
            self.builds += 1
            return canvas
        except Exception:
            canvas.park()
            raise

    @property
    def filter_visible(self):
        return self.type != "COMPACT" and self.state.get("show_filter", False)

    def dimensions(self, font_size, available_width, available_height=None):
        result = super().dimensions(font_size, available_width, available_height)
        self.prepare()
        if self.filter_canvas is not None and self.filter_visible:
            self.height = self.viewport + 30 + self.filter_canvas.height
            return result[0], self.height * font_size / self.design_font_size
        return result

    def filters(self):
        return () if self.draw_filter else super().filters()

    def search(self):
        if not self.draw_filter:
            return super().search()
        from types import SimpleNamespace
        from .layout import UnsupportedControl

        self.state["show_filter"] = True
        self.prepare()
        self.changed()
        child = self.filter_canvas
        control = next(
            (
                c
                for c in child.controls.values()
                if c.options.get("list_setting") == "filter_name"
            ),
            None,
        )
        if control is None:
            raise UnsupportedControl("UIList custom filter without a filter_name field")
        x, y, w, h = control.rect
        child.event(
            SimpleNamespace(type="LEFTMOUSE", value="PRESS"),
            x + w / 2,
            y + h / 2,
            (0, 0, child._width, child.height),
            context=self.context,
        )
        self.active_child = child
        self.capturing = self.focused = True
        self.begin_capture()

    @staticmethod
    def release(canvas):
        if canvas.shortcut_registry:
            for token in canvas._scoped_shortcuts.values():
                canvas.shortcut_registry.release(token)
        canvas.park()

    def prepare(self):
        if not hasattr(self, "viewport"):
            return
        selected = self.selected()
        next_cache, created = {}, []
        try:
            for item, rect in self.visible():
                key = (
                    item.identity,
                    item.index,
                    selected,
                    round(rect[2], 6),
                    self.epoch,
                )
                entry = self.cache.get(key)
                canvas = entry[0] if entry else self.child(item, rect[2])
                if entry is None:
                    created.append(canvas)
                next_cache[key] = (canvas, rect, item)
            if sum(len(entry[0].controls) for entry in next_cache.values()) > 4096:
                raise ValueError("Visible UIList rows exceed 4096 controls")
            if self.draw_filter and self.filter_visible and self.filter_canvas is None:
                self.filter_canvas = self.child(None, max(1, self.width - 8))
            if self.filter_canvas:
                self.filter_canvas.arrange(max(1, self.width - 8))
        except Exception:
            for canvas in created:
                self.release(canvas)
            raise
        replacements = {entry[2].identity: entry[0] for entry in next_cache.values()}
        for key, (canvas, _, _) in self.cache.items():
            if key not in next_cache:
                replacement = replacements.get(self.cache[key][2].identity)
                if replacement:
                    transfer_motion(canvas, replacement)
                self.release(canvas)
                if self.active_child is canvas:
                    self.active_child = None
        self.cache = next_cache
        self.row_map = {entry[2].index: entry for entry in self.cache.values()}
        self.live_canvases = {entry[0] for entry in self.cache.values()}
        if self.filter_canvas and not self.filter_visible:
            self.filter_canvas.cancel()
            if self.active_child is self.filter_canvas:
                self.active_child = None

    def all_children(self):
        yield from self.cache.values()
        if self.filter_canvas and self.filter_visible:
            yield (
                self.filter_canvas,
                (4, self.viewport + 28, self.width - 8, self.filter_canvas.height),
                None,
            )

    def cancel(self):
        for canvas, _, _ in self.all_children():
            canvas.cancel()
        self.active_child = None
        super().cancel()
        if not self.parent.visible or self.owner is not None and not self.owner.enabled:
            for canvas, _, _ in tuple(self.cache.values()):
                self.release(canvas)
            if self.filter_canvas:
                self.release(self.filter_canvas)
            self.cache.clear()
            self.row_map.clear()
            self.live_canvases.clear()
            self.filter_canvas = None

    def refresh(self):
        self.cancel()
        self.faulted = False
        try:
            self.source.refresh()
            self.reorder()
            if self.filter_canvas:
                self.release(self.filter_canvas)
                self.filter_canvas = None
            self.prepare()
            self.changed()
        except Exception:
            self.faulted = True
            self.cancel()
            raise

    def advance(self, clip=None):
        active = False
        for canvas, rect, _ in self.all_children():
            local_clip = None
            if clip is not None:
                x, y, w, h = clip
                a, b, cw, ch = rect
                if not (a < x + w and a + cw > x and b < y + h and b + ch > y):
                    canvas.cancel()
                    continue
                local_clip = (x - a, y - b, w, h)
            active = canvas.advance_animations(local_clip) or active
        return active

    def active_menu(self):
        return self.active_child.active_menu() if self.active_child else None

    def target_at(self, key, x, y):
        target = super().target_at(key, x, y)
        return replace(
            target, valid=lambda: self.available(self.context) and target.valid()
        )

    def event(self, event, x, y, *, clipboard=None):
        used = super().event(event, x, y, clipboard=clipboard)
        try:
            self.prepare()
        except Exception as error:
            self.error = self.parent.menu_error = str(error)
            self.faulted = True
            self.cancel()
        return used

    def route(
        self, event, x, y, clip, *, context=None, clipboard=None, menu_measure=None
    ):
        try:
            self.check(context or self.context)
            self.prepare()
            if self.wants_key(event) and event.value == "PRESS" and not self.capturing:
                self.search()
                return True
            chosen = None
            children = tuple(self.all_children())
            # Modal input belongs to its child even when the pointer is over
            # an earlier row or a menu extends outside that child row.
            children = tuple(e for e in children if e[0] is self.active_child) + tuple(
                e for e in children if e[0] is not self.active_child
            )
            for canvas, rect, item in children:
                captured = canvas is self.active_child and bool(
                    canvas.edit
                    or canvas.overlay
                    or canvas.context_menu
                    or canvas.widget_capture
                )
                keyboard = canvas is self.active_child and event.type not in {
                    "MOUSEMOVE",
                    "LEFTMOUSE",
                    "RIGHTMOUSE",
                    "WHEELUPMOUSE",
                    "WHEELDOWNMOUSE",
                    "TRACKPADPAN",
                }
                if (
                    captured
                    or keyboard
                    or inside(rect, x, y)
                    and (item is None or item.index == self.selected())
                ):
                    if (
                        captured
                        or keyboard
                        or canvas.hit(
                            x - rect[0],
                            y - rect[1],
                            (0, 0, rect[2], rect[3]),
                            include_disabled=True,
                        )
                    ):
                        chosen = (canvas, rect)
                        break
            if chosen is None or self.drag or self.text_edit:
                return None
            canvas, rect = chosen
            if event.type in self.navigation_keys and not (
                canvas.edit
                or canvas.overlay
                or canvas.context_menu
                or canvas.widget_capture
                or canvas.keyboard_focus
            ):
                return None
            if event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"} and not (
                canvas.edit or canvas.overlay or canvas.context_menu
            ):
                return None
            self.active_child = canvas
            self.focused = True
            if self.parent.keyboard_focus is not self.owner:
                self.parent.blur_focus()
                self.parent.keyboard_focus = self.owner
            local_clip = (clip[0] - rect[0], clip[1] - rect[1], clip[2], clip[3])
            prior_menu = canvas.active_menu()
            used = canvas.event(
                event,
                x - rect[0],
                y - rect[1],
                local_clip,
                context=context,
                clipboard=clipboard,
                menu_measure=menu_measure,
            )
            menu = canvas.active_menu()
            if menu is not None and menu is not prior_menu:
                valid = menu.target.valid
                menu.target = replace(
                    menu.target,
                    valid=lambda: self.available(self.context) and valid(),
                )
            self.capturing = bool(
                canvas.edit
                or canvas.overlay
                or canvas.context_menu
                or canvas.widget_capture
            )
            if canvas.menu_error:
                self.parent.menu_error = canvas.menu_error
            if self.pending and not self.capturing:
                self.pending = False
                if self.data_pending:
                    self.data_pending = False
                    self.source.refresh()
                self.reorder()
                if canvas is self.filter_canvas and self.filter_visible:
                    replacement = self.child(None, max(1, self.width - 8))
                    transfer_motion(self.filter_canvas, replacement)
                    self.release(self.filter_canvas)
                    self.filter_canvas = replacement
                    self.active_child = None
                self.prepare()
                self.changed()
            return used or event.type == "MOUSEMOVE"
        except Exception as error:
            self.error = self.parent.menu_error = str(error)
            self.faulted = True
            self.cancel()
            return event.value in {"PRESS", "DOUBLE_CLICK"} and inside(clip, x, y)

    def paint_row(self, p, item, rect, active, editing):
        if editing:
            return super().paint_row(p, item, rect, active, editing)
        from .gpu.paint import paint
        from .gpu.typography import flush_text

        entry = self.row_map.get(item.index)
        if entry:
            canvas = entry[0]
            a, b, c, d = p._clip
            paint(
                canvas,
                p.map((rect[0], rect[1], rect[2], canvas.height)),
                (a, b, c - a, d - b),
                font=p.font,
                palette=p.palette,
                backdrop=p.backdrop,
                background=False,
                overlays=False,
            )
            flush_text(p.font)

    def paint_filters(self, p, backdrop):
        if not self.draw_filter:
            return super().paint_filters(p, backdrop)
        if self.filter_canvas:
            from .gpu.paint import paint

            canvas = self.filter_canvas
            paint(
                canvas,
                p.map((4, self.viewport + 28, self.width - 8, canvas.height)),
                p.rect,
                font=p.font,
                palette=p.palette,
                backdrop=backdrop,
                background=False,
                overlays=False,
            )

    def paint_overlays(self, rect, font, palette, *, backdrop, clip):
        from .widgets.base import Painter
        from .gpu.paint import paint

        p = Painter(rect, self.width, self.height, font, palette, backdrop)
        for canvas, r, _ in self.all_children():
            if canvas.overlay or canvas.context_menu:
                paint(
                    canvas,
                    p.map((r[0], r[1], r[2], canvas.height)),
                    clip,
                    font=font,
                    palette=palette,
                    backdrop=backdrop,
                    background=False,
                    controls=False,
                )


def transfer_motion(old, new):
    """Retain springs only for unambiguous, same-owner property fields."""
    new.animation = old.animation
    for control in new.controls.values():
        new._bind_motion(control.motion)

    def keys(canvas):
        result = {}
        for control in canvas.controls.values():
            prop = getattr(control.binding, "context", None)
            if prop is not None and hasattr(prop, "identity"):
                key = (
                    control.kind,
                    prop.identity,
                    prop.name,
                    prop.index,
                    control.label,
                )
                result.setdefault(key, []).append(control)
            elif control.options.get("list_setting"):
                key = (
                    "setting",
                    control.kind,
                    control.options["list_setting"],
                    control.label,
                )
                result.setdefault(key, []).append(control)
        return {key: values[0] for key, values in result.items() if len(values) == 1}

    previous = keys(old)
    for key, control in keys(new).items():
        if key not in previous:
            continue
        motion = previous[key].motion
        old._moving.discard(motion)
        old._motion_owners.pop(motion, None)
        new._motion_owners.pop(control.motion, None)
        control.motion = motion
        new._motion_owners[motion] = control
        new._bind_motion(motion)
        if motion.advance():
            new._wake_motion(motion)
