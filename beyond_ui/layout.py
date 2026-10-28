"""Custom UILayout-style authoring API; never silently draws native widgets.

Only implemented methods are exposed. Unsupported templates raise an explicit
exception rather than displaying a generic form or claiming parity.
"""

from types import SimpleNamespace
from .canvas import Canvas, Group
from .bindings import Binding, rna_binding


class UnsupportedControl(NotImplementedError):
    def __init__(self, name):
        super().__init__(
            f"Custom control {name!r} is not implemented. See docs/CUSTOM_PARITY.json; no native fallback was used."
        )
        self.control = name


class Layout:
    """Build a custom Canvas with Blender-like layout/prop/operator calls.

    Pass context explicitly. resolve(data) can provide a stable-ID re-resolution
    callback for persistent data. commit(before,after) owns host undo/redraw.
    """

    def __init__(
        self,
        canvas=None,
        context=None,
        *,
        group=None,
        resolve=None,
        commit=None,
        state=None,
    ):
        self.canvas = canvas if canvas is not None else Canvas()
        self.context = context
        self.group = group if group is not None else self.canvas
        self.resolve = resolve
        self.commit = commit or (lambda before, after: None)
        self.state = state if state is not None else {}
        self._sequence = 0
        self._text_role = "body"
        self.enabled = True
        self.active = True
        self.alert = False
        self.operator_context = "INVOKE_DEFAULT"
        self.use_property_split = False
        self.use_property_decorate = True
        self.alignment = "EXPAND"
        self.scale_x = self.scale_y = 1.0
        self.ui_units_x = self.ui_units_y = 0.0
        self.emboss = "NORMAL"
        self.activate_init = self.active_default = False
        self._context_pointers = {}
        self._context_strings = {}

    def _key(self, kind):
        self._sequence += 1
        return f"{id(self.group)}:{kind}:{self._sequence}"

    def _options(self):
        return {"enabled": self.enabled}

    def _child(self, group):
        child = Layout(
            self.canvas,
            self.context,
            group=group,
            resolve=self.resolve,
            commit=self.commit,
            state=self.state,
        )
        for name in (
            "_text_role",
            "enabled",
            "active",
            "alert",
            "operator_context",
            "use_property_split",
            "use_property_decorate",
            "alignment",
            "scale_x",
            "scale_y",
            "ui_units_x",
            "ui_units_y",
            "emboss",
        ):
            setattr(child, name, getattr(self, name))
        child._context_pointers = dict(self._context_pointers)
        child._context_strings = dict(self._context_strings)
        return child

    def _text(self, text, text_ctxt="", translate=True):
        if not translate:
            return text
        try:
            import bpy

            return bpy.app.translations.pgettext_iface(text, text_ctxt or "*")
        except ImportError:
            return text

    def row(self, *, align=False, heading="", heading_ctxt="", translate=True):
        row = self._child(self.group.row())
        if heading:
            row.title(text=heading, text_ctxt=heading_ctxt, translate=translate)
        return row

    def column(self, *, align=False, heading="", heading_ctxt="", translate=True):
        column = self._child(self.group.column())
        if heading:
            column.title(text=heading, text_ctxt=heading_ctxt, translate=translate)
        return column

    def box(self):
        return self._child(self.group.box())

    def label(
        self, *, text="", text_ctxt="", translate=True, icon="NONE", icon_value=0
    ):
        return self.group.label(
            self._key("label"),
            self._text(text, text_ctxt, translate),
            icon=icon,
            icon_value=icon_value,
            text_role=self._text_role,
            **self._options(),
        )

    def title(self, *, text="", text_ctxt="", translate=True):
        return self.group.title(
            self._key("title"),
            self._text(text, text_ctxt, translate),
            **self._options(),
        )

    def separator(self, *, factor=1.0, type="AUTO"):
        return self.group.separator(self._key("separator"), height=8 * factor)

    def _binding(self, data, property, index=None):
        resolver = self.resolve(data) if self.resolve else lambda: data
        return rna_binding(resolver, property, index=index, commit=self.commit)

    def prop(
        self,
        data,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        placeholder="",
        expand=False,
        slider=False,
        toggle=-1,
        icon_only=False,
        event=False,
        full_event=False,
        emboss=True,
        index=-1,
        icon_value=0,
        invert_checkbox=False,
        text_align="LEFT",
    ):
        meta = data.bl_rna.properties[property]
        label = self._text(text or meta.name, text_ctxt, translate)
        if event or full_event:
            raise UnsupportedControl("prop event binding")
        if (
            getattr(meta, "is_array", False)
            and index < 0
            and meta.subtype not in {"COLOR", "COLOR_GAMMA"}
        ):
            row = self.row()
            for i in range(meta.array_length):
                row.prop(
                    data, property, text=f"{label} {i + 1}", index=i, slider=slider
                )
            return None
        binding = self._binding(data, property, index if index >= 0 else None)
        key = self._key(property)
        options = self._options()
        if meta.type == "BOOLEAN":
            if invert_checkbox:
                original = binding
                binding = Binding(
                    lambda: not original.read(),
                    lambda v: original.write(not v),
                    original.valid,
                    lambda a, b: original.commit(not a, not b),
                    original.context,
                )
            return self.group.toggle(key, label, binding, **options)
        if meta.type in {"INT", "FLOAT"}:
            if meta.subtype in {"COLOR", "COLOR_GAMMA"} and index < 0:
                return self.group.color(
                    key, label, binding, linear=meta.subtype == "COLOR", **options
                )
            return self.group.number(
                key,
                label,
                binding,
                min=meta.soft_min,
                max=meta.soft_max,
                hard_min=meta.hard_min,
                hard_max=meta.hard_max,
                integer=meta.type == "INT",
                **options,
            )
        if meta.type == "STRING":
            return self.group.text(
                key, label, binding, placeholder=placeholder, **options
            )
        if meta.type == "ENUM":
            if getattr(meta, "is_enum_flag", False):
                return self.props_enum(data, property)
            items = tuple(
                (item.identifier, self._text(item.name))
                for item in meta.enum_items
                if item.identifier
            )
            if expand:
                return self.props_enum(data, property)
            return self.group.enum(key, label, binding, items=items, **options)
        if meta.type == "POINTER":
            raise UnsupportedControl("prop pointer picker")
        raise UnsupportedControl(f"prop {meta.type}")

    def prop_enum(
        self,
        data,
        property,
        value,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
    ):
        meta = data.bl_rna.properties[property]
        source = self._binding(data, property)
        flag = getattr(meta, "is_enum_flag", False)
        item = meta.enum_items.get(value)
        label = self._text(text or (item.name if item else value), text_ctxt, translate)

        def get():
            return value in source.read() if flag else source.read() == value

        def set_value(selected):
            if flag:
                values = set(source.read())
                if selected:
                    values.add(value)
                else:
                    values.discard(value)
                source.write(values)
            elif selected:
                source.write(value)

        # Snapshot authoritative enum values so undo sees the real old/new state.
        def action():
            before = source.read()
            set_value(not get())
            after = source.read()
            if before != after:
                source.commit(before, after)

        return self.group.button(
            self._key("enum"),
            label,
            action,
            selected=get,
            binding=source,
            **self._options(),
        )

    def props_enum(self, data, property):
        row = self.row()
        for item in data.bl_rna.properties[property].enum_items:
            if item.identifier:
                row.prop_enum(data, property, item.identifier)

    def prop_menu_enum(self, data, property, **kwargs):
        return self.prop(data, property, **kwargs)

    def prop_tabs_enum(self, data, property, **kwargs):
        return self.props_enum(data, property)

    def operator(
        self,
        operator,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        emboss=True,
        depress=False,
        icon_value=0,
        search_weight=0.0,
    ):
        import bpy

        category, name = operator.split(".", 1)
        function = getattr(getattr(bpy.ops, category), name)
        properties = SimpleNamespace()
        label = self._text(text or function.get_rna_type().name, text_ctxt, translate)
        context = self.context
        invocation = self.operator_context
        pointers = dict(self._context_pointers)

        def execute():
            if context is None:
                raise RuntimeError(
                    "An explicit Blender context is required for operators"
                )
            # Operator properties are passed intact. No active-button operators
            # are synthesized against a native widget the user did not click.
            with context.temp_override(**pointers):
                if function.poll():
                    return function(invocation, **vars(properties))
            return {"CANCELLED"}

        from .context_extensions import operator_entries

        self.group.button(
            self._key(operator),
            label,
            execute,
            selected=depress,
            icon=icon,
            context_menu=lambda target, ctx: operator_entries(
                operator, vars(properties), ctx or context
            ),
            **self._options(),
        )
        return properties

    def context_pointer_set(self, name, data):
        self._context_pointers[name] = data

    def context_string_set(self, name, value):
        self._context_strings[name] = value

    def link(
        self,
        *,
        url="",
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        icon_value=0,
    ):
        props = self.operator(
            "wm.url_open",
            text=text or url,
            text_ctxt=text_ctxt,
            translate=translate,
            icon=icon,
        )
        props.url = url

    def panel(self, idname, *, default_closed=False):
        expanded = self.state.get(idname, not default_closed)
        header = self.row()
        header._text_role = "title"

        def toggle():
            self.state[idname] = not expanded
            # Host rebuilds schema on explicit state changes; no draw-time writes.
            self.canvas.schema_revision += 1

        header.group.button(self._key("disclosure"), "▾" if expanded else "▸", toggle)
        return header, self.column() if expanded else None

    def panel_prop(self, data, property):
        header = self.row()
        header._text_role = "title"
        header.prop(data, property)
        return header, self.column() if getattr(data, property) else None

    def supports(self, name):
        return callable(getattr(type(self), name, None)) or name in self.__dict__

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        raise UnsupportedControl(name)

    def template_color_picker(
        self,
        data,
        property,
        *,
        value_slider=False,
        lock=False,
        lock_luminosity=False,
        cubic=False,
    ):
        from .widgets import ColorPicker

        if lock or lock_luminosity or cubic:
            raise UnsupportedControl("template_color_picker lock/cubic modes")
        meta = data.bl_rna.properties[property]
        widget = ColorPicker(
            self._binding(data, property), linear=meta.subtype == "COLOR"
        )
        return self.group.widget(self._key("color_picker"), widget, **self._options())

    def template_color_ramp(self, data, property, *, expand=False):
        from .widgets import ColorRamp
        from .widgets.rna import color_ramp

        binding, ramp = color_ramp(data, property, self.commit)
        interpolation = rna_binding(lambda: ramp, "interpolation", commit=self.commit)
        return self.group.widget(
            self._key("color_ramp"),
            ColorRamp(binding, evaluate=ramp.evaluate, interpolation=interpolation),
            **self._options(),
        )

    def template_curve_mapping(
        self,
        data,
        property,
        *,
        type="NONE",
        levels=False,
        brush=False,
        use_negative_slope=False,
        show_tone=False,
        show_presets=False,
    ):
        from .widgets import CurveMapping
        from .widgets.rna import curve_mapping

        if any((levels, brush, use_negative_slope, show_tone, show_presets)):
            raise UnsupportedControl("template_curve_mapping advanced modes")
        channel = [0]
        binding, mapping, curve = curve_mapping(data, property, self.commit, channel)
        channel_binding = Binding(
            lambda: channel[0],
            lambda value: channel.__setitem__(0, min(value, len(mapping.curves) - 1)),
        )
        return self.group.widget(
            self._key("curve_mapping"),
            CurveMapping(
                binding,
                evaluate=lambda x: mapping.evaluate(curve(), x),
                channel=channel_binding,
            ),
            **self._options(),
        )

    def prop_search(
        self,
        data,
        property,
        search_data,
        search_property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        results_are_suggestions=False,
        item_search_property="",
    ):
        from .widgets import DataPicker

        source = self._binding(data, property)
        collection = getattr(search_data, search_property)
        values = tuple(collection)
        snapshots = {value.as_pointer(): value for value in values}

        def valid(key):
            try:
                return (
                    key in snapshots
                    and snapshots[key].as_pointer() == key
                    and any(v.as_pointer() == key for v in collection)
                )
            except ReferenceError:
                return False

        pointer = data.bl_rna.properties[property].type == "POINTER"

        def select(key):
            if not valid(key):
                return
            before = source.read()
            value = snapshots[key]
            source.write(value if pointer else value.name)
            source.commit(before, source.read())

        def selected():
            value = source.read()
            return (
                value.as_pointer()
                if pointer and value
                else next(
                    (key for key, v in snapshots.items() if v.name == value), None
                )
            )

        widget = DataPicker(
            ((key, value.name, "object") for key, value in snapshots.items()),
            select,
            selected=selected,
            valid=valid,
        )
        widget.binding = source
        return self.group.widget(self._key("search"), widget, **self._options())

    def template_search(
        self,
        data,
        property,
        search_data,
        search_property,
        *,
        new="",
        unlink="",
        text="",
        text_ctxt="",
        translate=True,
    ):
        result = self.prop_search(
            data,
            property,
            search_data,
            search_property,
            text=text,
            text_ctxt=text_ctxt,
            translate=translate,
        )
        row = self.row()
        if new:
            row.operator(new, text="New")
        if unlink:
            row.operator(unlink, text="Unlink")
        return result

    def template_matrix(self, data, property):
        from .widgets import MatrixView
        from .widgets.rna import matrix_components

        resolver = self.resolve(data) if self.resolve else None
        return self.group.widget(
            self._key("matrix"),
            MatrixView(
                matrix_components(data, property, resolver),
                labels=tuple(
                    self._text(t) for t in ("Translation", "Rotation", "Scale")
                ),
                title=self._text("Matrix"),
                unavailable_text=self._text("Matrix unavailable"),
            ),
            **self._options(),
        )

    def progress(
        self, *, text="", text_ctxt="", translate=True, factor=0.0, type="BAR"
    ):
        from .widgets import Progress

        return self.group.widget(
            self._key("progress"),
            Progress(
                factor,
                type=type,
                text=self._text(text, text_ctxt, translate),
                framed=False,
            ),
            **self._options(),
        )

    def template_palette(self, data, property, *, color=None):
        from .widgets import Palette, ColorPicker
        from .widgets.rna import palette_source
        import bpy

        # 5.2 removed the native color/value flag. Preserve explicit legacy
        # calls, with version-appropriate defaults when it is omitted.
        if color is None:
            function = bpy.types.UILayout.bl_rna.functions.get("template_palette")
            color = not (function and function.parameters.get("color"))
        brush = None
        owner = getattr(data, "brush", None)
        brush_property = "color" if color else "weight"
        if owner is not None and brush_property in owner.bl_rna.properties:
            brush = rna_binding(lambda: owner, brush_property)
        control = None

        def edit(binding):
            widget = ColorPicker(binding, linear=True)
            x, y, w, h = control.rect
            scale = min(
                1.0,
                max(1.0, self.canvas._width or w) / widget.width,
                max(1.0, self.canvas.height) / widget.height,
            )
            width, height = widget.width * scale, widget.height * scale
            self.canvas.overlay = {
                "widget": widget,
                "rect": (
                    max(0.0, min(x, (self.canvas._width or w) - width)),
                    max(0.0, min(y, self.canvas.height - height)),
                    width,
                    height,
                ),
            }

        resolver = self.resolve(data) if self.resolve else None
        source = palette_source(
            data,
            property,
            self.commit,
            brush=brush,
            edit=edit if color else None,
            resolve=resolver,
            value_mode=not color,
        )
        control = self.group.widget(
            self._key("palette"),
            Palette(
                source,
                show_colors=bool(color),
                title=self._text("Palette"),
                selected_text=self._text("Selected"),
                unavailable_text=self._text("Palette unavailable"),
            ),
            **self._options(),
        )
        return control

    def template_node_socket(self, *, color=(0.0, 0.0, 0.0, 1.0)):
        from .widgets.socket import Socket

        return self.group.widget(self._key("socket"), Socket(color), **self._options())
