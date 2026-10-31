"""Unregistered pie authoring using the shared collector and Canvas lifecycle."""

from .context_menu import Target
from .operator_enum import context_key
from .registered_menu import ContextArguments, MenuLayout


class Definition:
    def __init__(self, layout):
        self.layout, self.context = layout, layout.context
        self.name, self.label = "standalone_pie", "Pie"
        self.invocation = layout.operator_context
        self.pointers = ContextArguments()
        self.pointers.capture({**layout._context_pointers, **layout._context_strings})
        self.pointers.values()

    def check(self, context, scope=None, *, poll=True):
        if context is None:
            raise ValueError("Standalone pies require an explicit context")
        if scope is not None and context_key(context) != scope:
            raise ReferenceError("Pie context changed; rebuild the definition")
        if not self.pointers.valid() or not self.layout.group._effective_enabled:
            raise ReferenceError("Pie owner changed or layout is disabled")

    def available(self, context, scope=None, *, poll=True):
        try:
            self.check(context, scope, poll=poll)
            return True
        except (ReferenceError, RuntimeError, ValueError, AttributeError):
            return False


class StandalonePie(MenuLayout):
    def __init__(self, layout):
        model = Definition(layout)
        scope = context_key(layout.context)
        model.check(layout.context, scope)
        super().__init__(model, layout.context, scope, 0)
        self.menu_pie()
        for flag in (
            "alert",
            "emboss",
            "active_default",
            "activate_init",
            "use_property_split",
            "use_property_decorate",
        ):
            setattr(self, flag, getattr(layout, flag))

    def open(self, *, anchor, clip, context=None, trigger=None, settings=None):
        """Open on the owning Canvas; return its menu or raise the reported error.

        Coordinates use host logical units. ``trigger`` is the already-held
        invoking key/button. Rebuilding the definition is required after a
        scene/area/active-owner change, just like a registered menu invocation.
        """
        context = self.context if context is None else context
        self.model.check(context, self.scope)
        if not self.eligible():
            raise ReferenceError("Pie definition is disabled")
        self.finish()
        canvas = self.model.layout.canvas
        target = Target(
            self.model.name,
            valid=lambda: self.eligible() and self.model.available(context, self.scope),
            commit=canvas.menu_commit,
        )
        if not canvas.open_pie(
            target,
            tuple(self.rows),
            anchor,
            clip,
            context=context,
            trigger=trigger,
            settings=settings,
            scope=context_key,
        ):
            raise ValueError(canvas.menu_error)
        return canvas.context_menu
