"""On-demand adapter for public Python button-menu contributions (source BVT).

A deliberately bounded collector, not a general replacement UILayout. Unsupported
callbacks are isolated and reported; native-button-dependent actions stay absent.
"""

from types import SimpleNamespace
from dataclasses import replace
from .context_menu import Entry


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
        raise NotImplementedError(
            "String context requires a host adapter; Blender temp_override accepts RNA pointers"
        )

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
        props = SimpleNamespace()
        snapshot = {}
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
        invocation = self.operator_context
        values = self._scope()
        permitted = self.enabled and self.active

        def scope(context):
            return context.temp_override(**values())

        def poll(target, context):
            with scope(context):
                return permitted and operator(idname).poll()

        def execute(target, context):
            with scope(context):
                if operator(idname).poll():
                    return operator(idname)(invocation, **snapshot)

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
            with context.temp_override(**values()):
                return (
                    permitted
                    and menu is not None
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
            with self.context.temp_override(**self._scope()()):
                if not hasattr(cls, "poll") or cls.poll(self.context):
                    self.rows.extend(
                        collect(
                            self.context,
                            self.source,
                            (cls.draw,),
                            self.depth + 1,
                            self.extra,
                        )[: max(0, 64 - len(self.rows))]
                    )


def collect(context, source, callbacks, depth=0, extra=None):
    from .context_rna import decorate

    rows = []
    with context.temp_override(**{**(extra or {}), **overrides(source)}):
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
                snapshot.update(vars(props))
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


def operator_entries(idname, properties, context):
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
    reason = "Requires a native Blender button; unavailable on the custom canvas."
    rows.extend(
        (
            Entry(
                "FAVORITE",
                "Add to Quick Favorites",
                enabled=False,
                tip=reason,
                icon="menu",
            ),
            Entry(
                "SHORTCUT",
                "Assign Shortcut",
                enabled=False,
                tip=reason,
                icon="shortcut",
            ),
            Entry(
                "MANUAL",
                "Online Manual",
                lambda t, c: operator("wm.doc_view_manual")(doc_id=idname),
                icon="globe",
            ),
        )
    )
    rows.extend(entries(context, None))
    return rows
