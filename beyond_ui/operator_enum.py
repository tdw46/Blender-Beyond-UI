"""Operator enum choices with bounded snapshots and input-time validation."""

from dataclasses import replace
from itertools import islice
from types import SimpleNamespace
from .context_arguments import Arguments
from .context_enums import operator_items
from .context_extensions import operator, operator_entries
from .context_menu import Entry
from .enum_field import Item, LIMIT
from .hosts.menu_context import override


def context_key(context):
    """Reject a pending action after its scene, selection owner or host changes."""
    if context is None:
        return None
    return tuple(
        value.as_pointer() if value is not None else 0
        for value in (
            getattr(context, name, None)
            for name in (
                "window",
                "area",
                "region",
                "scene",
                "view_layer",
                "active_object",
            )
        )
    ) + (getattr(context, "mode", None),)


class OperatorEnum:
    def __init__(self, idname, name, context, invocation, pointers, translate):
        self.idname, self.name, self.context = idname, name, context
        self.invocation, self.translate = invocation, translate
        info = operator(idname).get_rna_type()
        meta = info.properties.get(name)
        if meta is None or meta.type != "ENUM":
            raise ValueError("Operator choice requires an enum property")
        self.identity = info.as_pointer()
        self.flag = meta.is_enum_flag
        self.label, self.description = info.name, info.description
        self.properties = SimpleNamespace()
        self.pointers = Arguments()
        self.pointers.capture(pointers)
        self.pointers.values()  # Fail explicitly for unsupported context snapshots.

    def current(self):
        info = operator(self.idname).get_rna_type()
        if info.as_pointer() != self.identity:
            raise ReferenceError("Operator changed; rebuild the controls")
        return info

    def snapshot(self, context=None, arguments=None):
        context = context or self.context
        if context is None:
            raise RuntimeError(
                "An explicit Blender context is required for operator choices"
            )
        self.current()
        arguments = arguments or self.arguments()
        with override(context, self.pointers.values()):
            rows = tuple(
                islice(
                    operator_items(
                        self.idname,
                        self.name,
                        context,
                        arguments.values(),
                        include_separators=True,
                    ),
                    LIMIT + 1,
                )
            )
        if len(rows) > LIMIT:
            raise ValueError("Operator enum exceeds the bounded 4096-item limit")
        result = tuple(
            Item(
                i.identifier,
                self.translate(i.name),
                self.translate(i.description),
                i.value,
            )
            for i in rows
        )
        identifiers = [i.identifier for i in result if i.identifier]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Operator enum identifiers must be unique")
        if not identifiers:
            raise ValueError("No operator choices are available in this context")
        return result

    def arguments(self):
        snapshot = Arguments()
        snapshot.capture(vars(self.properties))
        snapshot.values()
        return snapshot

    def selection(self, context):
        # Only sampled on opening/activation, never painting or pointer movement.
        with override(context, self.pointers.values()):
            values = tuple(islice(getattr(context, "selected_objects", ()), LIMIT + 1))
        if len(values) > LIMIT:
            raise ValueError("Operator selection exceeds the bounded 4096-owner limit")
        return frozenset(value.as_pointer() for value in values)

    def prepare(self, context):
        arguments = self.arguments()
        arguments.selection = self.selection(context)
        return arguments

    def check(self, context, arguments, scope, item=None):
        self.current()
        if context_key(context) != scope or self.arguments().tree != arguments.tree:
            raise ReferenceError(
                "Operator context or arguments changed; reopen the menu"
            )
        arguments.values()
        with override(context, self.pointers.values()):
            if not operator(self.idname).poll():
                raise ReferenceError("Operator is unavailable in this context")
        if item is not None:
            if self.selection(context) != arguments.selection:
                raise ReferenceError("Operator selection changed; reopen the menu")
            current = next(
                (
                    i
                    for i in self.snapshot(context, arguments)
                    if i.identifier == item.identifier
                ),
                None,
            )
            if current is None or current.value != item.value:
                raise ReferenceError("Operator choice changed; reopen the menu")
            # Dynamic enum callbacks are host code; they must not change the scope.
            self.check(context, arguments, scope)
            if self.selection(context) != arguments.selection:
                raise ReferenceError(
                    "Operator selection changed while resolving choices"
                )

    def available(self, context, arguments, scope):
        try:
            self.check(context, arguments, scope)
            return True
        except (ReferenceError, RuntimeError, AttributeError, ValueError):
            return False

    def values(self, item, arguments):
        return {
            **arguments.values(),
            self.name: {item.identifier} if self.flag else item.identifier,
        }

    def execute(self, item, context, arguments=None, scope=None):
        arguments = arguments or self.prepare(context)
        scope = context_key(context) if scope is None else scope
        self.check(context, arguments, scope, item)
        with override(context, self.pointers.values()):
            return operator(self.idname)(
                self.invocation, **self.values(item, arguments)
            )

    def rows(self, context):
        arguments, scope = self.prepare(context), context_key(context)
        choices = self.snapshot(context, arguments)
        self.check(context, arguments, scope)
        rows, divider = [], False
        for index, item in enumerate(choices):
            if not item.identifier:
                if item.name:
                    rows.append(
                        Entry(
                            f"heading:{index}",
                            item.name,
                            enabled=False,
                            heading=True,
                            divider=divider,
                        )
                    )
                    divider = False
                else:
                    divider = True
                continue
            rows.append(
                Entry(
                    f"operator:{item.identifier}",
                    item.name,
                    lambda t, c, item=item: self.execute(item, c, arguments, scope),
                    enabled=True,
                    tip=item.description,
                    divider=divider,
                )
            )
            divider = False
        return tuple(rows), lambda: self.available(context, arguments, scope)

    def context_rows(self, item, context):
        """Exact choice arguments for copy/shortcuts/favorites, guarded again on use."""
        arguments, scope = self.prepare(context), context_key(context)
        self.check(context, arguments, scope, item)

        def guarded(rows):
            result = []
            for row in rows:

                def action(t, c, row=row):
                    self.check(c, arguments, scope, item)
                    return row.action(t, c)

                def children(t, c, row=row):
                    self.check(c, arguments, scope, item)
                    return guarded(row.children(t, c))

                def capture(t, c, event, row=row):
                    self.check(c, arguments, scope, item)
                    return row.capture(t, c, event)

                def capture_options(t, c, row=row):
                    self.check(c, arguments, scope, item)
                    return guarded(row.capture_options(t, c))

                result.append(
                    replace(
                        row,
                        enabled=lambda t, c, row=row: self.available(
                            c, arguments, scope
                        )
                        and (
                            row.enabled(t, c) if callable(row.enabled) else row.enabled
                        ),
                        action=action if row.action else None,
                        children=children if row.children else None,
                        capture=capture if row.capture else None,
                        capture_options=capture_options
                        if row.capture_options
                        else None,
                    )
                )
            return tuple(result)

        return guarded(
            operator_entries(
                self.idname,
                self.values(item, arguments),
                context,
                invocation=self.invocation,
                pointers=self.pointers.values(),
            )
        )
