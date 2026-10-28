"""On-demand adapter for public Python button-menu contributions (source BVT).

A deliberately bounded collector, not a general replacement UILayout. Unsupported
callbacks are isolated and reported; native-button-dependent actions stay absent.
"""

from types import SimpleNamespace
from dataclasses import replace
from .context_menu import Entry
from .context_arguments import Arguments
from .context_enums import items as enum_items, operator_items
from .hosts.menu_context import override


def overrides(source):
    owner = source.owner() if source is not None else None
    return dict(
        button_pointer=owner,
        button_prop=owner.bl_rna.properties[source.name] if owner is not None else None,
        button_operator=None,
    )


def operator(idname):
    import bpy

    namespace, name = idname.split(".")
    return getattr(getattr(bpy.ops, namespace), name)


class Collector:
    def __init__(self, rows, context, source, depth=0):
        self.rows, self.context, self.source, self.depth = rows, context, source, depth
        self.enabled = self.active = True
        self.operator_context = "INVOKE_DEFAULT"
        self.extra = {}
        self.divider = False
        self.snapshots = []

    def row(self, **kwargs):
        child = Collector(self.rows, self.context, self.source, self.depth)
        child.enabled = self.enabled and self.active
        child.operator_context = self.operator_context
        child.extra = dict(self.extra)
        child.snapshots = self.snapshots
        return child

    column = split = column_flow = box = row

    def context_pointer_set(self, name, value):
        self.extra[name] = value

    def context_string_set(self, name, value):
        if not isinstance(value, str):
            raise TypeError("Context strings must be strings")
        self.extra[name] = value

    def separator(self, **kwargs):
        self.divider = True

    def _add(self, row):
        if len(self.rows) < 64:
            self.rows.append(replace(row, divider=self.divider))
            self.divider = False

    def label(self, *, text="", icon="", **kwargs):
        if text:
            self._add(Entry("LABEL", text, enabled=False, icon=icon))

    def _scope(self):
        extra = dict(self.extra)
        identities = {
            k: v.as_pointer() for k, v in extra.items() if hasattr(v, "as_pointer")
        }

        def values():
            if any(extra[k].as_pointer() != ptr for k, ptr in identities.items()):
                raise ReferenceError("Extension context changed")
            return {**extra, **overrides(self.source)}

        return values

    def operator(self, idname, *, text="", icon="", **kwargs):
        if len(self.rows) >= 64:
            return SimpleNamespace()
        props = SimpleNamespace()
        snapshot = Arguments()
        self.snapshots.append((props, snapshot))
        if idname.startswith("ui.") or idname.endswith("_button"):
            self._add(
                Entry(
                    idname,
                    text or idname,
                    enabled=False,
                    icon=icon,
                    tip="Requires a native Blender button.",
                )
            )
            return props
        op = operator(idname)
        info = op.get_rna_type()
        identity = info.as_pointer()
        invocation = self.operator_context
        values = self._scope()
        permitted = self.enabled and self.active

        def scope(context):
            return override(context, values())

        def poll(target, context):
            with scope(context):
                current = operator(idname)
                return (
                    permitted
                    and snapshot.valid()
                    and current.get_rna_type().as_pointer() == identity
                    and current.poll()
                )

        def execute(target, context):
            with scope(context):
                if poll(target, context):
                    return operator(idname)(invocation, **snapshot.values())
                raise ReferenceError("Contributed operator changed or is unavailable")

        self._add(
            Entry(
                idname,
                text or info.name,
                execute,
                poll,
                icon=icon,
                tip=info.description,
            )
        )
        return props

    def prop(self, data, property, *, text="", index=-1, expand=False, **kwargs):
        from .context_fields import property_row

        if expand and data.bl_rna.properties[property].type == "ENUM":
            return self.props_enum(data, property)
        self._add(
            property_row(
                data,
                property,
                text=text,
                index=index,
                permitted=self.enabled and self.active,
            )
        )

    def prop_enum(self, data, property, value, *, text="", **kwargs):
        from .context_fields import property_row

        item = (
            None
            if text
            else next(
                (
                    i
                    for i in enum_items(data, property, self.context)
                    if i.identifier == value
                ),
                None,
            )
        )
        self._add(
            property_row(
                data,
                property,
                text=text or (item.name if item else value),
                value=value,
                permitted=self.enabled and self.active,
            )
        )

    def props_enum(self, data, property):
        from itertools import islice

        for item in islice(
            (i for i in enum_items(data, property, self.context) if i.identifier), 64
        ):
            self.prop_enum(
                data, property, item.identifier, text=item.name or item.identifier
            )

    def operator_enum(self, operator, property, **kwargs):
        from itertools import islice

        op = globals()["operator"](operator)
        meta = op.get_rna_type().properties[property]
        with override(self.context, self._scope()()):
            choices = operator_items(operator, property, self.context)
        for item in islice((i for i in choices if i.identifier), 64):
            props = self.operator(operator, text=item.name)
            setattr(
                props,
                property,
                {item.identifier} if meta.is_enum_flag else item.identifier,
            )

    def operator_menu_enum(self, idname, property, *, text="", icon="", **kwargs):
        if len(self.rows) >= 64:
            return SimpleNamespace()
        from itertools import islice

        props, snapshot = SimpleNamespace(), Arguments()
        self.snapshots.append((props, snapshot))
        values, invocation = self._scope(), self.operator_context
        permitted, depth = self.enabled and self.active, self.depth + 1
        info = operator(idname).get_rna_type()
        identity = info.as_pointer()

        def enabled(target, context):
            current = operator(idname)
            with override(context, values()):
                return (
                    permitted
                    and snapshot.valid()
                    and current.get_rna_type().as_pointer() == identity
                    and current.poll()
                )

        def children(target, context):
            meta = operator(idname).get_rna_type().properties[property]
            with override(context, values()):
                choices = operator_items(idname, property, context, snapshot.values())

            def draw(holder, current):
                holder.layout.operator_context = invocation
                for item in islice((i for i in choices if i.identifier), 63):
                    settings = holder.layout.operator(idname, text=item.name)
                    for key, value in snapshot.values().items():
                        setattr(settings, key, value)
                    setattr(
                        settings,
                        property,
                        {item.identifier} if meta.is_enum_flag else item.identifier,
                    )

            return collect(context, self.source, (draw,), depth, values())

        self._add(
            Entry(
                idname + ":" + property,
                text or info.name,
                enabled=enabled,
                children=children,
                icon=icon,
                tip=info.description,
            )
        )
        return props

    def menu(self, idname, *, text="", icon="", **kwargs):
        import bpy

        cls = getattr(bpy.types, idname, None)
        if cls is None or self.depth >= 3:
            return
        permitted = self.enabled and self.active
        depth = self.depth + 1
        values = self._scope()

        def poll(target, context):
            menu = getattr(bpy.types, idname, None)
            with override(context, values()):
                return (
                    permitted
                    and menu is cls
                    and (not hasattr(menu, "poll") or menu.poll(context))
                )

        def children(target, context):
            menu = getattr(bpy.types, idname, None)
            return (
                collect(context, self.source, (menu.draw,), depth, values())
                if menu
                else ()
            )

        self._add(
            Entry(
                idname, text or cls.bl_label, enabled=poll, children=children, icon=icon
            )
        )

    def menu_contents(self, idname, **kwargs):
        import bpy

        cls = getattr(bpy.types, idname, None)
        if cls is not None and self.depth < 3:
            with override(self.context, self._scope()()):
                if not hasattr(cls, "poll") or cls.poll(self.context):
                    # Inline children inherit the same state as an ordinary row.
                    child = self.row()
                    child.depth += 1
                    try:
                        cls.draw(SimpleNamespace(layout=child), self.context)
                    except Exception as error:
                        print("[Beyond UI context extension]", idname, error)


def collect(context, source, callbacks, depth=0, extra=None):
    from .context_rna import decorate

    rows = []
    with override(context, {**(extra or {}), **overrides(source)}):
        for callback in callbacks:
            pending = []
            try:
                layout = Collector(pending, context, source, depth)
                layout.extra = dict(extra or {})
                callback(SimpleNamespace(layout=layout), context)
            except Exception as error:
                print(
                    "[Beyond UI context extension]",
                    getattr(callback, "__qualname__", "callback"),
                    error,
                )
            for props, snapshot in layout.snapshots:
                snapshot.capture(vars(props))
                if snapshot.error:
                    print(
                        "[Beyond UI context extension] argument snapshot:",
                        snapshot.error,
                    )
            rows.extend(pending[: max(0, 64 - len(rows))])
            if len(rows) >= 64:
                break
    return decorate(rows, context)


def entries(context, source):
    import bpy

    cls = getattr(bpy.types, "UI_MT_button_context_menu", None)
    callbacks = getattr(getattr(cls, "draw", None), "_draw_funcs", ())
    return (
        collect(context, source, callbacks)
        if callbacks and hasattr(context, "temp_override")
        else ()
    )


def operator_entries(
    idname,
    properties,
    context,
    *,
    invocation="INVOKE_DEFAULT",
    pointers=None,
    keymap=None,
):
    if context is None:
        return ()
    rows = []
    if getattr(context.preferences.view, "show_developer_ui", False):
        command = f"bpy.ops.{idname}({', '.join(f'{k}={v!r}' for k, v in properties.items())})"
        rows.append(
            Entry(
                "COMMAND",
                "Copy Python Command",
                lambda t, c: setattr(c.window_manager, "clipboard", command),
            )
        )
    from .hosts import menu_native
    from .context_shortcuts import Action, portable

    properties = dict(properties)
    independent = not pointers and portable(properties)

    def favorites(target, ctx):
        found = menu_native.operator_favorite(
            idname, properties, invocation, ctx, operation="QUERY"
        )

        def remove(t, c):
            if not menu_native.operator_favorite(
                idname, properties, invocation, c, operation="REMOVE"
            ):
                raise ReferenceError("Favorite no longer exists")

        return (
            Entry(
                "REMOVE_FAVORITE" if found else "FAVORITE",
                "Remove from Quick Favorites" if found else "Add to Quick Favorites",
                remove
                if found
                else lambda t, c: menu_native.add_operator_favorite(
                    idname, properties, invocation, c
                ),
            ),
        )

    rows.append(
        Entry(
            "FAVORITES",
            "Quick Favorites",
            children=favorites,
            enabled=lambda t, c: independent
            and c.area is not None
            and invocation in menu_native.INVOCATIONS
            and menu_native.api() is not None,
            tip="Manage this operator and its exact arguments in Quick Favorites.",
            icon="menu",
        )
    )
    if independent and invocation == "INVOKE_DEFAULT":
        rows.append(Action(idname, properties, context, keymap=keymap).entry(context))
    else:
        rows.append(
            Entry(
                "SHORTCUT",
                "Assign Shortcut",
                enabled=False,
                icon="shortcut",
                tip="This operator's invocation or pointer overrides require a host shortcut dispatcher.",
            )
        )
    rows.append(
        Entry(
            "MANUAL",
            "Online Manual",
            lambda t, c: operator("wm.doc_view_manual")(doc_id=idname),
            icon="globe",
        )
    )
    if getattr(context.preferences.view, "show_developer_ui", False):
        from .context_source import entry, operator_subject

        rows.append(entry(operator_subject(idname)))
    if getattr(context.preferences.view, "show_tooltips_python", False):
        rows = [
            replace(row, tip=(row.tip + f"\nPython: bpy.ops.{idname}()").strip())
            for row in rows
        ]
    rows.extend(entries(context, None))
    return rows
