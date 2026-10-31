"""Operator-instance dialogs built from the same retained custom popover controls."""

from types import SimpleNamespace
from .layout import Layout
from .canvas import Canvas
from .popover import PanelPopover
from .hosts.addon import PanelProxy
from .context_menu import Entry


class OperatorProxy(PanelProxy):
    def __init__(self, operator, layout):
        super().__init__(type(operator), layout, operator)
        self._operator = operator

    def __getattr__(self, name):
        if name in {
            "bl_rna",
            "is_property_readonly",
            "id_data",
            "as_pointer",
            "path_from_id",
        }:
            return getattr(self._operator.properties, name)
        return super().__getattr__(name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name == "layout":
            object.__setattr__(self, name, value)
        else:
            setattr(self._operator, name, value)


class Dialog:
    direction = "VERTICAL"

    def __init__(
        self,
        host,
        operator,
        context,
        event,
        *,
        width=300,
        title="",
        confirm_text="",
        cancel_default=False,
        context_menu=None,
        mode="DIALOG",
        message="",
        icon="NONE",
        layout_options=None,
    ):
        self.host, self.operator, self.context = host, operator, context
        self.outcome = None
        self.closed = False
        self.cancel_called = False
        self.mode, self.message, self.icon = mode, message, icon
        self.layout_options = dict(layout_options or {})
        self.cls = SimpleNamespace(bl_ui_units_x=max(8, min(48, width / 20)))
        self.form = dict(
            title=title,
            confirm_text=confirm_text,
            cancel_default=cancel_default,
            context_menu=context_menu,
        )
        self.needs_check = False
        root = host.canvas
        self.owner = root.button("dialog-owner", "", lambda: None)
        x, y = host.anchor(event)
        self.owner.rect = (x, y, 1, 1)
        self.build(context)

    def changed(self, before, after):
        self.needs_check = True

    def build(self, context, *, initial=True):
        host, operator, root = self.host, self.operator, self.host.canvas
        title, confirm_text, cancel_default, context_menu = (
            self.form[k]
            for k in ("title", "confirm_text", "cancel_default", "context_menu")
        )
        if not initial:
            root.cancel()
        self.canvas = Canvas(
            root.theme,
            shortcut_registry=root.shortcut_registry,
            context_provider=context_menu,
        )
        self.canvas._scoped_shortcuts = {}
        self.canvas._popover_depth = 1
        self.canvas.bind_animation(
            (*root._animation_parents, root.animation, self.owner.motion.settings),
            root._animation_wake,
        )
        self.canvas.set_text_measure(root.text_measure, root._text_measure_key)
        self.canvas.bind_context_tooltips(root._tooltip_wake)

        def resolve(data):
            value = (
                data._operator.properties if isinstance(data, OperatorProxy) else data
            )
            return lambda: value if not self.closed else None

        options = dict(self.layout_options)
        options.update(resolve=resolve, commit=self.changed)
        ui = Layout(self.canvas, context, **options)
        ui._is_popover = True
        ui.title(text=title or operator.bl_label, icon=self.icon, translate=False)
        draw = getattr(type(operator), "draw", None)
        if self.mode == "CONFIRM":
            for line in self.message.splitlines():
                ui.label(text=line, translate=False)
        elif draw is not None:
            from .layout_recording import Tape

            tape = Tape()
            draw(OperatorProxy(operator, tape.root), context)
            tape.initialize_lists(ui.list_identity)
            tape.play(ui)
        else:
            for prop in operator.properties.bl_rna.properties:
                if (
                    prop.identifier != "rna_type"
                    and not prop.is_hidden
                    and not prop.is_readonly
                ):
                    ui.prop(operator.properties, prop.identifier)
        if self.mode != "PROPERTIES":
            self.footer(ui, confirm_text, cancel_default)
        self.popup = PanelPopover(self, root, self.owner, self.canvas, None)
        root.open_widget(self.popup, self.owner, host.clip)
        if initial:
            self.popup.opened(context)
        root._bind_motion(self.popup.motion, self.owner)
        self.popup.motion.pulse("reveal", 0.12)

    def footer(self, ui, confirm_text, cancel_default):
        row = ui.row()
        row.alignment = "RIGHT"
        for key, label, accepted in (
            ("cancel", "Cancel", False),
            ("confirm", confirm_text or "OK", True),
        ):
            control = row.group.button(
                key,
                label,
                lambda accepted=accepted: self.choose(accepted),
                operator_button=True,
                release_action=True,
                context_menu=lambda target, context, accepted=accepted, label=label: (
                    Entry(
                        "CONFIRM_DIALOG" if accepted else "CANCEL_DIALOG",
                        label,
                        lambda t, c: self.choose(accepted),
                        enabled=lambda t, c: t.valid(),
                    ),
                    *(
                        self.canvas.context_provider(target, context)
                        if self.canvas.context_provider
                        else ()
                    ),
                ),
                active_default=(not accepted if cancel_default else accepted),
            )
            control.options["text_align"] = "CENTER"

    def available(self, context, scope=None, *, poll=True):
        return not self.closed and self.host.alive(context)

    def choose(self, accepted):
        self.canvas.finish()
        self.outcome = bool(accepted)
        return {"FINISHED"}

    def dispatch(self, context, event):
        if not self.host.alive(context):
            self.outcome = False
        else:
            self.host.event(context, event)
            if self.needs_check:
                self.needs_check = False
                check = getattr(type(self.operator), "check", None)
                if check and check(self.operator, context) and self.outcome is None:
                    self.build(context, initial=False)
            if self.host.canvas.overlay is None and self.outcome is None:
                self.outcome = False
        return self.outcome

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.host.close()

    def cancel_once(self, callback, context):
        if not self.cancel_called:
            self.cancel_called = True
            if callback:
                callback(self.operator, context)


class SearchDialog(Dialog):
    """Search the original operator's enum, then execute that same instance."""

    def __init__(self, host, operator, context, event, *, context_menu=None):
        from dataclasses import replace
        from .operator_enum import context_key

        self.host, self.operator, self.context = host, operator, context
        self.outcome, self.closed, self.cancel_called = None, False, False
        self.scope = context_key(context)
        name = getattr(operator, "bl_property", "")
        meta = operator.properties.bl_rna.properties.get(name)
        if meta is None or meta.type != "ENUM":
            raise ValueError(
                "Search popup requires an EnumProperty named by bl_property"
            )
        if meta.is_enum_flag:
            from .hosts.bridge import BridgeUnavailable

            raise BridgeUnavailable(
                "Flag-enum search selection semantics are not yet qualified"
            )
        root = self.canvas = host.canvas
        root.context_provider = context_menu
        root.menu_search_threshold = 1
        ui = Layout(
            root, context, resolve=lambda data: lambda: None if self.closed else data
        )
        control = ui.prop(operator.properties, name)
        # Layout.prop returns the control for scalar properties.
        self.owner = control
        x, y = host.anchor(event)
        control.rect = (x, y, 1, 1)
        if not root.open_enum_menu(control, host.clip, context):
            raise RuntimeError(root.menu_error)
        menu = root.context_menu
        original_valid = menu.target.valid
        menu.target = replace(
            menu.target,
            valid=lambda: original_valid() and context_key(context) == self.scope,
        )
        rows = []
        for row in menu.page.rows:
            if row.action is not None:
                action = row.action

                def choose(target, ctx, action=action):
                    action(target, ctx)
                    self.outcome = True
                    return {"FINISHED"}

                def owner_menu(target, ctx):
                    from .context_menu import default_entries

                    return (
                        *default_entries(target, ctx),
                        *(context_menu(target, ctx) if context_menu else ()),
                    )

                row = replace(row, action=choose, context=owner_menu)
            rows.append(row)
        menu.page.rows = tuple(rows)
        if menu.page.search:
            # Search caches the immutable original row set for filtering.
            from .menu_search import Search

            search = Search(menu.page.rows)
            search.rect = menu.page.search.rect
            search.focused = True
            menu.page.search = search

    def dispatch(self, context, event):
        from .operator_enum import context_key

        if not self.host.alive(context) or context_key(context) != self.scope:
            self.outcome = False
        else:
            self.host.event(context, event)
            if self.host.canvas.context_menu is None and self.outcome is None:
                self.outcome = False
        return self.outcome
