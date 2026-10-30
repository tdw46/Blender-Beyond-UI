"""Registered Python menu definitions rendered by the custom menu engine.

Draw once on open/navigation, never paint. Unsupported calls abort collection;
no callback is silently omitted and no native menu is opened.
"""

from dataclasses import replace
from itertools import islice
from types import SimpleNamespace
from .context_arguments import Arguments
from .context_menu import Entry, Target, default_entries
from .context_edit import Field
from .context_extensions import operator, operator_entries
from .hosts.menu_context import override
from .operator_enum import context_key

LIMIT = 4096
DEPTH = 3


def menu_class(name):
    import bpy

    cls = bpy.types.Menu.bl_rna_get_subclass_py(name)
    if cls is None:
        raise ValueError(f"Registered menu {name!r} is unavailable")
    return cls


def draw_key(cls):
    draw = cls.draw
    return (draw, tuple(getattr(draw, "_draw_funcs", ())))


def owner_guard(data):
    """Validate the owning ID before accessing possibly stale embedded RNA."""
    owner = getattr(data, "id_data", None)
    key = owner.as_pointer() if owner is not None else None
    pointer = data.as_pointer()

    def resolve():
        if owner is not None and owner.as_pointer() != key:
            raise ReferenceError("Menu property owner disappeared")
        if data.as_pointer() != pointer:
            raise ReferenceError("Menu property changed")
        return data

    return resolve


class Proxy:
    """Expose Python draw helpers without constructing a native RNA menu."""

    def __init__(self, cls, layout):
        self._cls, self.layout = cls, layout

    def __getattr__(self, name):
        import inspect

        value = inspect.getattr_static(self._cls, name)
        if hasattr(value, "__get__"):
            return value.__get__(self, self._cls)
        return value


class ContextArguments(Arguments):
    def __init__(self):
        super().__init__()
        self.guards = []

    def capture(self, values):
        super().capture(values)
        self.guards = [owner_guard(v) for v, _ in self.pointers]

    def valid(self):
        try:
            for guard in self.guards:
                guard()
            return super().valid()
        except (ReferenceError, RuntimeError, AttributeError):
            return False


def retarget(rows, target):
    """Nested row actions keep their exact property/operator target."""
    result = []
    for row in rows:

        def wrap(callback):
            def call(t, c, *args):
                if not target.valid():
                    raise ReferenceError("Menu row owner changed")
                return callback(target, c, *args)

            return call

        def enabled(t, c, row=row):
            return target.valid() and (
                row.enabled(target, c) if callable(row.enabled) else row.enabled
            )

        def children(t, c, row=row):
            if not target.valid():
                raise ReferenceError("Menu row owner changed")
            return retarget(row.children(target, c), target)

        def nested(callback):
            def call(t, c):
                if not target.valid():
                    raise ReferenceError("Menu row owner changed")
                return retarget(callback(target, c), target)

            return call

        field = row.field
        if field is not None:

            def apply(text, original, t, c, field=field):
                if not target.valid():
                    raise ReferenceError("Menu row owner changed")
                return field.apply(text, original, target, c)

            field = Field(wrap(field.read), apply, field.format, wrap(field.state))
        result.append(
            replace(
                row,
                enabled=enabled,
                action=wrap(row.action) if row.action else None,
                children=children if row.children else None,
                checked=wrap(row.checked) if callable(row.checked) else row.checked,
                capture=wrap(row.capture) if row.capture else None,
                capture_options=nested(row.capture_options)
                if row.capture_options
                else None,
                context=nested(row.context) if row.context else None,
                field=field,
            )
        )
    return tuple(result)


class RegisteredMenu:
    def __init__(self, layout, name, *, source=None, depth=0):
        self.layout, self.context, self.name = layout, layout.context, name
        self.cls, self.depth, self.source = menu_class(name), depth, source
        self.draw_identity = draw_key(self.cls)
        self.parent_check = None
        self.label = self.cls.bl_label
        self.pointers = ContextArguments()
        from .context_extensions import overrides

        self.pointers.capture(
            {**layout._context_pointers, **layout._context_strings, **overrides(source)}
        )
        self.pointers.values()
        self.invocation = layout.operator_context

    def check(self, context, scope=None, *, poll=True):
        if self.parent_check is not None:
            self.parent_check(context, poll)
        if not self.pointers.valid():
            raise ReferenceError("Menu context owners changed")
        if (
            menu_class(self.name) is not self.cls
            or draw_key(self.cls) != self.draw_identity
        ):
            raise ReferenceError(
                "Menu registration or draw callbacks changed; reopen it"
            )
        if scope is not None and context_key(context) != scope:
            raise ReferenceError("Menu context changed; reopen it")
        if not self.layout.group._effective_enabled:
            raise ReferenceError("Menu layout is disabled")
        if self.source is not None and not self.source.valid():
            raise ReferenceError("Attached menu property owner changed")
        if context is None:
            raise ValueError("Registered menus require an explicit context")
        if poll:
            with override(context, self.pointers.values()):
                if hasattr(self.cls, "poll") and not self.cls.poll(context):
                    raise ReferenceError("Menu is unavailable in this context")

    def available(self, context, scope=None, *, poll=True):
        try:
            self.check(context, scope, poll=poll)
            return True
        except (ReferenceError, RuntimeError, ValueError, AttributeError):
            return False

    def rows(self, context):
        scope = context_key(context)
        self.check(context, scope)
        collector = MenuLayout(self, context, scope, self.depth)
        with override(context, self.pointers.values()):
            self.cls.draw(Proxy(self.cls, collector), context)
        collector.finish()
        self.check(context, scope)
        if not collector.rows:
            raise ValueError("Menu has no supported rows in this context")
        valid = lambda: self.available(context, scope)
        rows = tuple(collector.rows)
        if self.depth:
            # The outer Menu owns the root scope. Keep each child definition's
            # poll/registration/ancestor guards on every descendant row as well.
            rows = retarget(
                rows,
                Target(self.name, valid=valid, commit=self.layout.canvas.menu_commit),
            )
        return rows, valid

    def context_rows(self, target, context):
        rows = [
            Entry(
                "OPEN_MENU",
                "Open " + self.label,
                children=lambda t, c: self.rows(c)[0],
                enabled=lambda t, c: self.available(c),
            )
        ]
        if self.source is not None:
            rows.extend(default_entries(target, context))
        provider = self.layout.canvas.context_provider
        if provider:
            rows.extend(provider(target, context))
        return tuple(rows)


class MenuLayout:
    """Strict vertical menu authoring, retaining Blender's scalar/enum semantics."""

    _attributes = {
        "model",
        "context",
        "scope",
        "depth",
        "rows",
        "finalizers",
        "enabled",
        "active",
        "operator_context",
        "extra",
        "divider",
        "selections",
        "parent",
    }

    def __setattr__(self, name, value):
        if name not in self._attributes:
            from .layout import UnsupportedControl

            raise UnsupportedControl("registered menu attribute " + name)
        object.__setattr__(self, name, value)

    def eligible(self):
        return bool(
            self.enabled
            and self.active
            and (self.parent is None or self.parent.eligible())
        )

    def __init__(self, model, context, scope, depth, rows=None, finalizers=None):
        self.model, self.context, self.scope, self.depth = model, context, scope, depth
        self.rows = rows if rows is not None else []
        self.finalizers = finalizers if finalizers is not None else []
        self.enabled = self.active = True
        self.operator_context = model.invocation
        self.extra = dict(model.pointers.values())
        self.divider = False
        self.selections = {}
        self.parent = None

    def __getattr__(self, name):
        from .layout import UnsupportedControl

        raise UnsupportedControl("registered menu " + name)

    def _text(self, text, text_ctxt="", translate=True):
        return self.model.layout._text(text, text_ctxt, translate)

    def _add(self, row):
        if len(self.rows) >= LIMIT - bool(self.depth):
            raise ValueError("Registered menu exceeds 4096 rows")
        if row.children is not None and row.context is None:
            row = replace(
                row,
                context=lambda t, c, row=row: (
                    Entry(
                        "OPEN",
                        "Open " + row.label,
                        children=row.children,
                        enabled=row.enabled,
                    ),
                ),
            )
        self.rows.append(
            replace(row, key=f"{len(self.rows)}:{row.key}", divider=self.divider)
        )
        self.divider = False

    def finish(self):
        for callback in self.finalizers:
            callback()

    def row(self, *, align=False, heading="", heading_ctxt="", translate=True):
        if heading:
            self.label(text=heading, text_ctxt=heading_ctxt, translate=translate)
        child = MenuLayout(
            self.model, self.context, self.scope, self.depth, self.rows, self.finalizers
        )
        child.parent = self
        child.operator_context = self.operator_context
        child.extra = dict(self.extra)
        child.selections = self.selections
        return child

    column = row

    def separator(self, *, factor=1.0, type="AUTO"):
        if type not in {"AUTO", "LINE", "SPACE"}:
            raise ValueError("Unknown menu separator")
        self.divider = True

    def label(
        self, *, text="", text_ctxt="", translate=True, icon="NONE", icon_value=0
    ):
        if icon_value:
            raise ValueError(
                "Registered menu preview icons require an explicit renderer"
            )
        self._add(
            Entry(
                "LABEL",
                self._text(text, text_ctxt, translate),
                enabled=False,
                heading=True,
                icon=icon,
            )
        )

    def context_pointer_set(self, name, value):
        self.extra[name] = value

    def context_string_set(self, name, value):
        if not isinstance(value, str):
            raise TypeError("Context strings must be strings")
        self.extra[name] = value

    def _scope(self):
        args = ContextArguments()
        args.capture(self.extra)
        args.values()
        return args

    def _check(self, ctx, args):
        self.model.check(ctx, self.scope)
        return args.values()

    def operator(
        self,
        idname,
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
        if icon_value:
            raise ValueError(
                "Registered menu preview icons require an explicit renderer"
            )
        if idname.startswith("ui.") or idname.endswith("_button"):
            raise ValueError(
                "Active-native-button operator requires an explicit host action"
            )
        info = operator(idname).get_rna_type()
        identity = info.as_pointer()
        props = SimpleNamespace()
        args = Arguments()
        self.finalizers.append(lambda: (args.capture(vars(props)), args.values()))
        pointers = self._scope()
        invocation = self.operator_context
        permitted = self.eligible
        # Large selection snapshots occur once at draw and again at action, not on paint/hover.
        cache_key = pointers.tree
        try:
            hash(cache_key)
        except TypeError:
            cache_key = None
        selection = self.selections.get(cache_key) if cache_key is not None else None
        if selection is None:
            with override(self.context, pointers.values()):
                selected = tuple(islice(self.context.selected_objects, LIMIT + 1))
            if len(selected) > LIMIT:
                raise ValueError("Menu selection exceeds 4096 owners")
            selection = frozenset(o.as_pointer() for o in selected)
            if cache_key is not None:
                self.selections[cache_key] = selection

        def check(ctx, *, executing=False):
            values = self._check(ctx, pointers)
            if (
                not permitted()
                or not args.valid()
                or operator(idname).get_rna_type().as_pointer() != identity
            ):
                raise ReferenceError("Menu operator owner or arguments changed")
            with override(ctx, values):
                if not operator(idname).poll():
                    raise ReferenceError("Menu operator poll failed")
                if (
                    executing
                    and frozenset(o.as_pointer() for o in ctx.selected_objects)
                    != selection
                ):
                    raise ReferenceError("Selection changed; reopen the menu")
            return values

        def available(t, c):
            try:
                check(c)
                return True
            except (ReferenceError, RuntimeError, ValueError, AttributeError):
                return False

        def execute(t, c):
            with override(c, check(c, executing=True)):
                return operator(idname)(invocation, **args.values())

        def context(t, c):
            def owned():
                try:
                    self._check(c, pointers)
                    return (
                        t.valid()
                        and args.valid()
                        and operator(idname).get_rna_type().as_pointer() == identity
                    )
                except (ReferenceError, RuntimeError, ValueError, AttributeError):
                    return False

            if not owned():
                raise ReferenceError("Menu operator owner changed")
            target = replace(t, valid=owned, payload=(idname, args.values()))
            return retarget(
                operator_entries(
                    idname,
                    args.values(),
                    c,
                    invocation=invocation,
                    pointers={
                        k: v
                        for k, v in pointers.values().items()
                        if not (
                            k in {"button_pointer", "button_prop", "button_operator"}
                            and v is None
                        )
                    },
                ),
                target,
            )

        self._add(
            Entry(
                idname,
                self._text(text or info.name, text_ctxt, translate),
                execute,
                available,
                icon=icon,
                tip=info.description,
                checked=depress,
                context=context,
            )
        )
        return props

    def prop(
        self,
        data,
        property,
        *,
        text="",
        text_ctxt="",
        translate=True,
        icon="NONE",
        expand=False,
        slider=False,
        index=-1,
        toggle=-1,
        icon_only=False,
        event=False,
        full_event=False,
        emboss=True,
    ):
        if slider or icon_only or event or full_event:
            raise ValueError(
                "This property presentation requires a custom inline control"
            )
        from .context_rna import Property
        from .context_fields import property_row

        source = Property(owner_guard(data), property, None if index < 0 else index)
        meta = source.owner().bl_rna.properties[property]
        if meta.type not in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}:
            raise ValueError("This property type requires a custom inline control")
        if expand and meta.type == "ENUM":
            return self.props_enum(data, property)
        row = property_row(
            data,
            property,
            text=self._text(text or meta.name, text_ctxt, translate),
            index=index,
            permitted=self.eligible,
            source=source,
            commit=self.model.layout.commit,
            limit=LIMIT - 1,
            context_factory=self._property_context,
        )

        self._add(replace(row, icon=icon, context=self._property_context(source)))

    def _property_context(self, source):
        def context(t, c):
            from .bindings import rna_binding

            binding = rna_binding(
                source.resolve,
                source.name,
                index=source.index,
                commit=self.model.layout.commit,
            )
            target = replace(
                t,
                binding=binding,
                valid=lambda: t.valid() and source.valid(),
                editable=lambda: t.editable() and self.eligible() and source.editable(),
            )
            provider = self.model.layout.canvas.context_provider or default_entries
            return retarget(provider(target, c), target)

        return context

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
        from .context_rna import Property
        from .context_fields import property_row
        from .context_enums import items

        source = Property(owner_guard(data), property)
        item = next(
            (i for i in items(data, property, self.context) if i.identifier == value),
            None,
        )
        if item is None:
            raise ValueError("Unknown menu enum item")
        row = property_row(
            data,
            property,
            text=self._text(text or item.name, text_ctxt, translate),
            value=value,
            permitted=self.eligible,
            source=source,
            commit=self.model.layout.commit,
            limit=LIMIT - 1,
            context_factory=self._property_context,
        )
        self._add(replace(row, icon=icon, context=self._property_context(source)))

    def props_enum(self, data, property):
        from .context_enums import items

        choices = tuple(islice(items(data, property, self.context), LIMIT + 1))
        if len(choices) > LIMIT:
            raise ValueError("Enum exceeds menu bounds")
        for item in choices:
            self.prop_enum(data, property, item.identifier, text=item.name)

    def menu(
        self, menu, *, text="", text_ctxt="", translate=True, icon="NONE", icon_value=0
    ):
        if self.depth >= DEPTH or icon_value:
            raise ValueError("Menu nesting or preview icon exceeds supported bounds")
        child = self._child_model(menu)
        permitted = self.eligible
        self._add(
            Entry(
                menu,
                self._text(text or child.label, text_ctxt, translate),
                enabled=lambda t, c: permitted() and child.available(c, self.scope),
                children=lambda t, c: child.rows(c)[0],
                icon=icon,
                context=lambda t, c: child.context_rows(t, c),
            )
        )

    def _child_model(self, name):
        if self.depth >= DEPTH:
            raise ValueError("Menu nesting exceeds supported bounds")
        child = RegisteredMenu(self.model.layout, name, depth=self.depth + 1)

        def parent_check(context, poll):
            self.model.check(context, self.scope, poll=poll)
            if not self.eligible():
                raise ReferenceError("Parent menu layout is disabled")

        child.parent_check = parent_check
        child.pointers = self._scope()
        child.invocation = self.operator_context
        return child

    def menu_contents(self, menu):
        child = self._child_model(menu)
        child.check(self.context, self.scope)
        collector = self.row()
        collector.model, collector.depth = child, child.depth
        with override(self.context, collector.extra):
            child.cls.draw(Proxy(child.cls, collector), self.context)
        child.check(self.context, self.scope)

    def operator_menu_enum(
        self, idname, property, *, text="", text_ctxt="", translate=True, icon="NONE"
    ):
        from .operator_enum import OperatorEnum

        model = OperatorEnum(
            idname,
            property,
            self.context,
            self.operator_context,
            self.extra,
            self._text,
        )
        permitted = self.eligible
        self._add(
            Entry(
                idname,
                self._text(text or model.label, text_ctxt, translate),
                enabled=lambda t, c: permitted(),
                children=lambda t, c: self._operator_choices(model, c),
                icon=icon,
            )
        )
        return model.properties

    def _operator_choices(self, model, context):
        rows, _ = model.rows(context)
        items = {item.identifier: item for item in model.snapshot(context)}
        rows = tuple(
            replace(
                row,
                context=(
                    lambda t,
                    c,
                    item=items[row.key.split(":", 1)[1]]: model.context_rows(item, c)
                ),
            )
            if row.key.startswith("operator:")
            else row
            for row in rows
        )
        return retarget(
            rows,
            Target(
                self.model.name,
                valid=lambda: self.eligible()
                and self.model.available(context, self.scope),
                commit=self.model.layout.canvas.menu_commit,
            ),
        )

    def operator_enum(self, idname, property, *, icon_only=False):
        if icon_only:
            raise ValueError("Icon-only menu operators require a custom renderer")
        from .operator_enum import OperatorEnum

        model = OperatorEnum(
            idname,
            property,
            self.context,
            self.operator_context,
            self.extra,
            self._text,
        )
        for row in self._operator_choices(model, self.context):
            self._add(
                replace(
                    row,
                    enabled=lambda t, c, row=row: self.eligible()
                    and (row.enabled(t, c) if callable(row.enabled) else row.enabled),
                )
            )


def inline(layout, name):
    """Author supported custom Layout controls atomically and retain their scope."""
    if name in layout._menu_stack or len(layout._menu_stack) >= DEPTH:
        raise ValueError("Recursive menu contents exceed supported bounds")
    model = RegisteredMenu(layout, name)
    context = layout.context
    scope = context_key(context)
    model.check(context, scope)
    canvas = layout.canvas
    before = set(canvas.controls)
    children = list(layout.group.children)
    try:
        child = layout.column()
        child._menu_stack = (*layout._menu_stack, name)
        with override(context, model.pointers.values()):
            model.cls.draw(Proxy(model.cls, child), context)
        model.check(context, scope)
        added = [c for k, c in canvas.controls.items() if k not in before]
        if len(added) > LIMIT:
            raise ValueError("Inline menu exceeds 4096 controls")
        for control in added:
            previous_valid = control.options.get("valid_context")
            previous_guard = control.options.get("activation_guard")

            def valid(previous=previous_valid):
                return (previous is None or previous()) and model.available(
                    context, scope, poll=False
                )

            def guard(ctx, previous=previous_guard):
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
        if added:
            canvas._context_guarded = True
    except Exception:
        for key in set(canvas.controls) - before:
            control = canvas.controls.pop(key)
            control.motion.clear()
            canvas._moving.discard(control.motion)
            canvas._motion_owners.pop(control.motion, None)
        layout.group.children[:] = children
        canvas._context_guarded = any(
            "activation_guard" in c.options for c in canvas.controls.values()
        )
        canvas.invalidate()
        raise
