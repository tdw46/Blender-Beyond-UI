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
        source=None,
        pointer_sources=None,
        id_actions=None,
    ):
        self.canvas = canvas if canvas is not None else Canvas()
        self.context = context
        self.group = group if group is not None else self.canvas
        self.resolve = resolve
        self.source = source
        self.pointer_sources = pointer_sources
        self.id_actions = id_actions
        self.commit = commit or (lambda before, after: None)
        self.state = state if state is not None else {}
        self._sequence = 0
        self._text_role = "body"
        self.alert = False
        self.operator_context = "INVOKE_DEFAULT"
        self.search_popovers = True
        self.use_property_split = False
        self.use_property_decorate = True
        self.scale_x = self.scale_y = 1.0
        self.ui_units_x = self.ui_units_y = 0.0
        self.emboss = "NORMAL"
        self.activate_init = self.active_default = False
        self._context_pointers = {}
        self._context_strings = {}
        self._menu_stack = ()
        self._is_popover = False
        self._panel_stack = ()

    def _key(self, kind):
        self._sequence += 1
        return f"{id(self.group)}:{kind}:{self._sequence}"

    @property
    def enabled(self):
        return self.group.options.get("enabled", True)

    @enabled.setter
    def enabled(self, value):
        self._policy("enabled", value)

    @property
    def active(self):
        return self.group.options.get("active", True)

    @active.setter
    def active(self, value):
        self._policy("active", value)

    def _policy(self, name, value):
        value = bool(value)
        if self.group.options.get(name, True) == value:
            return
        self.group.options[name] = value
        self.group._refresh_enabled()
        if any(
            c is not None and not c.enabled
            for c in (
                self.canvas.active,
                self.canvas.widget_capture,
                self.canvas.keyboard_focus,
                (self.canvas.overlay or {}).get("owner"),
            )
        ):
            self.canvas.cancel()
        self.canvas.invalidate()

    @property
    def alignment(self):
        return self.group.options.get("alignment", "EXPAND")

    @alignment.setter
    def alignment(self, value):
        if value not in {"EXPAND", "LEFT", "CENTER", "RIGHT"}:
            raise ValueError("alignment must be EXPAND, LEFT, CENTER or RIGHT")
        if value != self.alignment:
            self.group.options["alignment"] = value
            self.canvas.invalidate()

    @property
    def direction(self):
        if self.group is self.canvas or self.group.kind == "row":
            return "HORIZONTAL"
        if self.group.kind == "grid":
            try:
                import bpy

                if bpy.app.version >= (4, 5, 0):
                    return "HORIZONTAL"
            except ImportError:
                pass  # Pure-Python hosts retain the oldest supported convention.
        return "VERTICAL"

    def _options(self):
        return {}

    def _child(self, group):
        child = Layout(
            self.canvas,
            self.context,
            group=group,
            resolve=self.resolve,
            commit=self.commit,
            state=self.state,
            source=self.source,
            pointer_sources=self.pointer_sources,
            id_actions=self.id_actions,
        )
        for name in (
            "_text_role",
            "alert",
            "operator_context",
            "search_popovers",
            "use_property_split",
            "use_property_decorate",
            "alignment",
            "scale_x",
            "scale_y",
            "ui_units_x",
            "ui_units_y",
            "emboss",
            "_menu_stack",
            "_is_popover",
            "_panel_stack",
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
        row = self._child(self.group.row(align=align))
        if heading:
            row.title(text=heading, text_ctxt=heading_ctxt, translate=translate)
        return row

    def column(self, *, align=False, heading="", heading_ctxt="", translate=True):
        column = self._child(self.group.column(align=align))
        if heading:
            column.title(text=heading, text_ctxt=heading_ctxt, translate=translate)
        return column

    def split(self, *, factor=0.0, align=False):
        from math import isfinite

        factor = float(factor)
        if not isfinite(factor) or not 0 <= factor <= 1:
            raise ValueError("split factor must be finite and between zero and one")
        return self._child(self.group._group("split", factor=factor, align=bool(align)))

    def column_flow(self, *, columns=0, align=False):
        from operator import index

        columns = index(columns)
        if columns < 0:
            raise ValueError("column_flow columns must be nonnegative")
        return self._child(
            self.group._group("flow", columns=columns, align=bool(align))
        )

    def grid_flow(
        self,
        *,
        row_major=False,
        columns=0,
        even_columns=False,
        even_rows=False,
        align=False,
    ):
        from operator import index

        return self._child(
            self.group._group(
                "grid",
                columns=index(columns),
                row_major=bool(row_major),
                even_columns=bool(even_columns),
                even_rows=bool(even_rows),
                align=bool(align),
            )
        )

    def separator_spacer(self):
        if self.group.kind != "row":
            raise ValueError("separator_spacer requires a horizontal row")
        self.group._group("spacer", spacer=True)

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
        return rna_binding(
            resolver, property, index=index, commit=self.commit, source=self.source
        )

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
        arguments = dict(locals())
        arguments.pop("self")
        meta = data.bl_rna.properties[property]
        if (
            self.use_property_split
            and self.use_property_decorate
            and (index >= 0 or not getattr(meta, "is_array", False))
        ):
            row = self.row()
            row.use_property_decorate = False
            result = row.prop(**arguments)
            row.prop_decorator(data, property, index=index)
            return result
        subtype = (
            "NONE"
            if getattr(meta, "unit", "NONE") in {"AREA", "VOLUME"}
            else meta.subtype
        )
        label = self._text(text or meta.name, text_ctxt, translate)
        if event or full_event:
            from .event_field import EventField

            binding = self._binding(data, property)
            try:
                field = EventField(binding, full=full_event)
            except ValueError as error:
                raise UnsupportedControl(str(error)) from error
            return self.group.add(
                "event",
                self._key(property),
                label,
                binding=binding,
                event_field=field,
                **self._options(),
            )
        if (
            getattr(meta, "is_array", False)
            and index < 0
            and subtype not in {"COLOR", "COLOR_GAMMA"}
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
            if subtype in {"COLOR", "COLOR_GAMMA"} and index < 0:
                return self.group.color(
                    key, label, binding, linear=subtype == "COLOR", **options
                )
            from .numeric import Numeric

            return self.group.number(
                key,
                label,
                binding,
                min=meta.soft_min,
                max=meta.soft_max,
                hard_min=meta.hard_min,
                hard_max=meta.hard_max,
                integer=meta.type == "INT",
                numeric=Numeric(meta, self.context),
                slider=slider,
                **options,
            )
        if meta.type == "STRING":
            return self.group.text(
                key, label, binding, placeholder=placeholder, **options
            )
        if meta.type == "ENUM":
            if getattr(meta, "is_enum_flag", False):
                return self._expanded_enum(data, property)
            if expand:
                return self._expanded_enum(data, property)
            return self._enum_control(data, property, label, binding, key, options)
        if meta.type == "POINTER":
            from .pointer import PointerField
            from .context_menu import default_entries

            policy = (
                self.pointer_sources(data, property) if self.pointer_sources else None
            )
            try:
                field = PointerField(binding, policy)
            except ValueError as error:
                raise UnsupportedControl(str(error)) from error

            def context_rows(target, context):
                provider = self.canvas.context_provider
                if callable(target.payload):
                    return (
                        *target.payload(target, context),
                        *(provider(target, context) if provider else ()),
                    )
                entries = list((provider or default_entries)(target, context))
                if field.allow_none and binding.valid():
                    entries.insert(0, field.clear_entry())
                return entries

            return self.group.add(
                "pointer",
                key,
                label,
                binding=binding,
                pointer_field=field,
                context_menu=context_rows,
                **options,
            )
        raise UnsupportedControl(f"prop {meta.type}")

    def template_ID(
        self,
        data,
        property,
        *,
        new="",
        open="",
        unlink="",
        filter="ALL",
        live_icon=False,
        text="",
        text_ctxt="",
        translate=True,
    ):
        if live_icon:
            raise UnsupportedControl("template_ID live preview icons")
        from .id_template import IDTemplate

        try:
            model = IDTemplate(
                self,
                data,
                property,
                filter=filter,
                operators={
                    k: v
                    for k, v in (("new", new), ("open", open), ("unlink", unlink))
                    if v
                },
            )
        except ValueError as error:
            raise UnsupportedControl(str(error)) from error
        column = self.column()
        head = column.row()
        picker = head.group.add(
            "pointer",
            self._key("id-picker"),
            self._text(text, text_ctxt, translate),
            binding=model.binding,
            pointer_field=model,
            context_menu=model.property_entries,
            width=160,
        )
        picker.options["id_template"] = model
        head.group.text(
            self._key("id-name"),
            "",
            model.field_binding("name"),
            placeholder="Data-block name",
        )
        actions = column.grid_flow(row_major=True)
        model.button(
            actions.group,
            self._key("id-users"),
            "Make Single User",
            model.duplicate,
            lambda: model.can_copy() and model.users() > 1,
            label_get=lambda: f"Users: {model.users()}",
            width=80,
        )
        actions.group.toggle(
            self._key("id-fake"),
            self._text("Fake User"),
            model.field_binding("use_fake_user"),
            enabled=model.fake_user_allowed,
            width=132,
        )
        for operation, label in (("new", "New"), ("open", "Open")):
            if operation in model.operators:
                model.button(
                    actions.group,
                    self._key("id-" + operation),
                    self._text(label),
                    lambda token, op=operation: model.invoke(op, token),
                    lambda op=operation: model.operator_available(op),
                    width=64,
                )
        if unlink:
            model.button(
                actions.group,
                self._key("id-unlink"),
                self._text("Unlink"),
                lambda token: model.invoke("unlink", token),
                lambda: model.operator_available("unlink")
                and model.current() is not None,
                width=64,
            )
        else:
            model.button(
                actions.group,
                self._key("id-unlink"),
                self._text("Unlink"),
                model.clear,
                lambda: model.editable()
                and model.field.allow_none
                and model.current() is not None,
                width=64,
            )
        return None

    def template_ID_tabs(self, data, property, *, new="", menu="", filter="ALL"):
        if menu:
            raise UnsupportedControl("template_ID_tabs registered context menu")
        from .id_template import IDTemplate

        try:
            model = IDTemplate(
                self,
                data,
                property,
                filter=filter,
                operators={"new": new} if new else {},
            )
            row = self.grid_flow(row_major=True, even_columns=True)
            model.add_tabs(row.group)
        except ValueError as error:
            raise UnsupportedControl(str(error)) from error
        if new:
            model.button(
                row.group,
                self._key("id-new"),
                self._text("New"),
                lambda token: model.invoke("new", token),
                lambda: model.operator_available("new"),
                width=64,
            )
        return None

    def prop_decorator(self, data, property, *, index=-1):
        from .decorator import Decorator

        binding = None
        model = None
        if data is not None and property:
            meta = data.bl_rna.properties[property]
            if index < -1 or (
                index >= 0 and (not meta.is_array or index >= meta.array_length)
            ):
                raise ValueError("Decorator component index is outside the property")
            if (
                index == -1
                and getattr(meta, "is_array", False)
                and meta.subtype not in {"COLOR", "COLOR_GAMMA", "DIRECTION"}
                and meta.is_animatable
            ):
                column = self.column()
                return tuple(
                    column.prop_decorator(data, property, index=i)
                    for i in range(meta.array_length)
                )
            if meta.is_animatable and getattr(data, "id_data", None) is not None:
                binding = self._binding(data, property, None if index < 0 else index)
                model = Decorator(binding, self.context)
        return self.group.add(
            "decorator",
            self._key("decorator"),
            "",
            binding=binding,
            decorator=model,
            width=self.canvas.theme.row_height,
            enabled=lambda: self.enabled
            and model is not None
            and model.editable(self.canvas),
        )

    @staticmethod
    def _enum_metadata(data, property, identifier, attribute):
        import bpy
        from .context_enums import items

        default = 0 if attribute == "icon" else ""
        meta = data.bl_rna.properties.get(property)
        if meta is None or meta.type != "ENUM" or not identifier:
            return default
        item = next(
            (
                i
                for i in items(data, property, bpy.context)
                if i.identifier == identifier
            ),
            None,
        )
        if item is None:
            return default
        value = getattr(item, attribute, default)
        if attribute == "icon":
            if isinstance(value, int):
                return value
            # Public-RNA EnumPropertyItem.icon uses an identifier on older paths.
            icons = (
                bpy.types.UILayout.bl_rna.functions["prop"]
                .parameters["icon"]
                .enum_items
            )
            icon = icons.get(value)
            return icon.value if icon is not None else 0
        translator = (
            bpy.app.translations.pgettext_tip
            if attribute == "description"
            else bpy.app.translations.pgettext_iface
        )
        return translator(value, getattr(meta, "translation_context", "*") or "*")

    @classmethod
    def enum_item_name(cls, data, property, identifier):
        return cls._enum_metadata(data, property, identifier, "name")

    @classmethod
    def enum_item_description(cls, data, property, identifier):
        return cls._enum_metadata(data, property, identifier, "description")

    @classmethod
    def enum_item_icon(cls, data, property, identifier):
        return cls._enum_metadata(data, property, identifier, "icon")

    def _enum_items(self, data, property, *, include_separators=False):
        from .context_enums import items

        return items(
            data, property, self.context, include_separators=include_separators
        )

    def _enum_field(self, binding):
        from .enum_field import EnumField

        source = binding.context
        return EnumField(
            binding,
            lambda: self._enum_items(
                source.owner(), source.name, include_separators=True
            ),
            flag=getattr(
                source.owner().bl_rna.properties[source.name], "is_enum_flag", False
            ),
            translate=self._text,
        )

    def _enum_control(self, data, property, label, binding, key, options):
        field = self._enum_field(binding)
        rows = field.snapshot()
        return self.group.enum(
            key,
            label,
            binding,
            items=tuple((i.identifier, i.name) for i in rows if i.identifier != ""),
            enum_field=field,
            **options,
        )

    def _enum_button(
        self,
        data,
        property,
        item,
        *,
        text="",
        text_ctxt="",
        translate=True,
        modifier_select=False,
    ):
        source = self._binding(data, property)
        source.context.enum_value = item.identifier
        field = self._enum_field(source)

        def selected():
            try:
                # Binding.read already validates; do not repeat RNA ownership work.
                return field.selected(item.identifier)
            except (ReferenceError, RuntimeError):
                return False

        def action(event=None):
            try:
                field.choose(
                    item,
                    exclusive=modifier_select and not getattr(event, "shift", False),
                )
                self.canvas.menu_error = None
            except Exception as error:
                self.canvas.menu_error = str(error)

        return self.group.button(
            self._key("enum"),
            self._text(text or item.name, text_ctxt, translate),
            action,
            selected=selected,
            action_event=action,
            binding=source,
            **self._options(),
        )

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
        field = self._enum_field(self._binding(data, property))
        item = next((i for i in field.snapshot() if i.identifier == value), None)
        if item is None:
            raise ValueError(f"Unknown enum choice: {value}")
        return self._enum_button(
            data, property, item, text=text, text_ctxt=text_ctxt, translate=translate
        )

    def _expanded_enum(self, data, property):
        field = self._enum_field(self._binding(data, property))
        row = self.row()
        for item in field.snapshot():
            if item.identifier != "":
                row._enum_button(
                    data, property, item, translate=False, modifier_select=True
                )
            elif item.name:
                row.title(text=item.name, translate=False)
            else:
                row.separator()

    def props_enum(self, data, property):
        # Native props_enum groups choices into columns under optional headings.
        field = self._enum_field(self._binding(data, property))
        split = self.row()
        column = split.column()
        populated = False
        for item in field.snapshot():
            if item.identifier != "":
                column._enum_button(data, property, item, translate=False)
            elif item.name:
                if populated:
                    column = split.column()
                column.title(text=item.name, translate=False)
            else:
                column.separator()
            populated = True

    def prop_menu_enum(
        self,
        data,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
    ):
        meta = data.bl_rna.properties[property]
        if meta.type != "ENUM":
            raise ValueError("prop_menu_enum requires an enum property")
        return self._enum_control(
            data,
            property,
            self._text(text or meta.name, text_ctxt, translate),
            self._binding(data, property),
            self._key(property),
            self._options(),
        )

    def prop_tabs_enum(self, data, property, **kwargs):
        return self._expanded_enum(data, property)

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
        pointers = {**self._context_pointers, **self._context_strings}
        from .hosts.menu_context import override

        def execute():
            if context is None:
                raise RuntimeError(
                    "An explicit Blender context is required for operators"
                )
            # Operator properties are passed intact. No active-button operators
            # are synthesized against a native widget the user did not click.
            with override(context, pointers):
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
                operator,
                vars(properties),
                ctx or context,
                invocation=invocation,
                pointers=pointers,
            ),
            **self._options(),
        )
        return properties

    def _operator_enum(self, operator, property):
        from .operator_enum import OperatorEnum

        return OperatorEnum(
            operator,
            property,
            self.context,
            self.operator_context,
            {**self._context_pointers, **self._context_strings},
            self._text,
        )

    def operator_enum(self, operator, property, *, icon_only=False):
        if icon_only:
            raise UnsupportedControl("operator_enum icon_only")
        model = self._operator_enum(operator, property)
        from .operator_enum import context_key

        enabled = model.available(
            self.context, model.arguments(), context_key(self.context)
        )
        for item in model.snapshot():
            if not item.identifier:
                if item.name:
                    self.title(text=item.name, translate=False)
                else:
                    self.separator()
                continue

            def action(item=item):
                try:
                    result = model.execute(item, self.context)
                    self.canvas.menu_error = None
                    return result
                except Exception as error:
                    self.canvas.menu_error = str(error)
                    return {"CANCELLED"}

            self.group.button(
                self._key(operator),
                item.name,
                action,
                context_menu=lambda target, ctx, item=item: model.context_rows(
                    item, ctx or self.context
                ),
                enabled=enabled,
            )

    def operator_menu_enum(
        self,
        operator,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
    ):
        if icon != "NONE":
            raise UnsupportedControl("operator_menu_enum custom icon")
        from .context_menu import Entry

        model = self._operator_enum(operator, property)
        label = self._text(text or model.label, text_ctxt, translate)
        self.group.button(
            self._key(operator),
            label,
            None,
            operator_enum=model,
            context_menu=lambda target, ctx: (
                Entry(
                    "CHOICES",
                    "Choose " + label,
                    children=lambda t, c: model.rows(c or self.context)[0],
                ),
                Entry(
                    "SHORTCUT",
                    "Shortcut to Open Menu",
                    enabled=False,
                    tip="The consuming host must provide a ShortcutRegistry for this custom popup.",
                ),
            ),
            **self._options(),
        )
        return model.properties

    @property
    def is_popover(self):
        return self._is_popover

    def popover(
        self,
        panel,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        icon_value=0,
        direction="VERTICAL",
    ):
        if icon_value or direction not in {"VERTICAL", "HORIZONTAL"}:
            raise UnsupportedControl("popover preview icon or attachment direction")
        from .popover import author

        author(
            self,
            panel,
            text=text,
            text_ctxt=text_ctxt,
            translate=translate,
            icon=icon,
            direction=direction,
        )

    def popover_group(self, space_type, region_type, context, category):
        from .popover import panel_group

        for panel in panel_group(self, space_type, region_type, context, category):
            self.popover(panel)

    def prop_with_popover(
        self,
        data,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        icon_only=False,
        panel,
    ):
        from .popover import RegisteredPanel

        meta = data.bl_rna.properties[property]
        if icon_only or (
            meta.type != "ENUM" and meta.subtype not in {"COLOR", "COLOR_GAMMA"}
        ):
            raise UnsupportedControl(
                "prop_with_popover requires a text enum or color field"
            )
        binding = self._binding(data, property)
        model = RegisteredPanel(self, panel, source=binding.context)
        label = self._text(text or meta.name, text_ctxt, translate)
        key = self._key("popover-property")
        if meta.type == "ENUM":
            control = self._enum_control(
                data, property, label, binding, key, dict(icon=icon)
            )
        else:
            control = self.group.color(
                key, label, binding, linear=meta.subtype == "COLOR"
            )
        model.attach(control)

    def menu(
        self, menu, *, text="", text_ctxt="", translate=True, icon="NONE", icon_value=0
    ):
        if icon_value:
            raise UnsupportedControl("menu preview icon")
        from .registered_menu import RegisteredMenu

        model = RegisteredMenu(self, menu)
        self.group.button(
            self._key("menu"),
            self._text(text or model.label, text_ctxt, translate),
            None,
            menu_model=model,
            context_menu=model.context_rows,
            icon=icon,
        )

    def prop_with_menu(
        self,
        data,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        icon_only=False,
        menu,
    ):
        if icon_only or data.bl_rna.properties[property].type != "ENUM":
            raise UnsupportedControl("prop_with_menu requires a text enum field")
        from .registered_menu import RegisteredMenu

        binding = self._binding(data, property)
        model = RegisteredMenu(self, menu, source=binding.context)
        control = self._enum_control(
            data,
            property,
            self._text(
                text or data.bl_rna.properties[property].name, text_ctxt, translate
            ),
            binding,
            self._key("menu-property"),
            dict(icon=icon),
        )
        control.options.update(menu_model=model, context_menu=model.context_rows)

    def menu_contents(self, menu):
        from .registered_menu import inline

        inline(self, menu)

    def context_pointer_set(self, name, data):
        self._context_pointers[name] = data

    def context_string_set(self, name, value):
        if not isinstance(value, str):
            raise TypeError("Context strings must be strings")
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
        # Accepted legacy attributes without custom behavior are not capabilities.
        if name in {
            "activate_init",
            "active_default",
            "alert",
            "emboss",
            "scale_x",
            "scale_y",
            "ui_units_x",
            "ui_units_y",
        }:
            return False
        return (
            isinstance(getattr(type(self), name, None), property)
            or callable(getattr(type(self), name, None))
            or name in self.__dict__
        )

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
        from .search import CollectionSearch

        if item_search_property:
            import bpy

            if (
                "item_search_property"
                not in bpy.types.UILayout.bl_rna.functions["prop_search"].parameters
            ):
                raise UnsupportedControl(
                    "item_search_property is unavailable in this Blender version"
                )
        resolver = self.resolve(search_data) if self.resolve else lambda: search_data
        policy = self.pointer_sources(data, property) if self.pointer_sources else None
        try:
            model = CollectionSearch(
                self._binding(data, property),
                resolver,
                search_property,
                policy=policy,
                label=self._text(
                    text or data.bl_rna.properties[property].name, text_ctxt, translate
                ),
                item_name=item_search_property,
                suggestions=results_are_suggestions,
                eager=not self.search_popovers,
            )
        except ValueError as error:
            raise UnsupportedControl(str(error)) from error
        control = self.group.add(
            "search" if self.search_popovers else "widget",
            self._key("search"),
            model.widget.title,
            widget=model.widget,
            binding=model.binding,
            search_field=model,
            context_menu=model.entries,
            **self._options(),
        )
        model.canvas, model.control = self.canvas, control
        return control

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
            self.canvas.open_widget(widget, control)

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
