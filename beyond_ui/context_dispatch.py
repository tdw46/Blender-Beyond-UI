"""Explicit host-owned shortcut dispatch. No registration or bpy import on import."""

from collections import OrderedDict
from hashlib import sha256


class ShortcutRegistry:
    """A consuming extension registers/closes one registry under its unique ID.

    Commands are stable logical names; callbacks are scoped to current windows.
    Hidden/replaced controls fail closed. Rebind after rebuilding a host canvas.
    """

    def __init__(self, owner, *, limit=256, keymap="Window", conflict_keymaps=None):
        if not owner or not 1 <= limit <= 4096:
            raise ValueError("Supply a unique owner and a bounded command limit")
        self.owner, self.limit, self.keymap = owner, limit, keymap
        self.conflict_keymaps = conflict_keymaps
        namespace = "beyondui" + sha256(owner.encode()).hexdigest()[:12]
        self.idname = namespace + ".dispatch"
        self.classname = namespace.upper() + "_OT_dispatch"
        self.commands = OrderedDict()
        self.operator_class = None
        self.error = None

    def register(self):
        if self.operator_class is not None:
            return
        import bpy

        registry = self
        if bpy.types.Operator.bl_rna_get_subclass_py(self.classname) is not None:
            raise RuntimeError("Shortcut registry owner is already registered")

        def invoke(operator, context, event):
            return registry.dispatch(operator.command, context, event)

        def execute(operator, context):
            return registry.dispatch(operator.command, context)

        cls = type(
            self.classname,
            (bpy.types.Operator,),
            {
                "bl_idname": self.idname,
                "bl_label": "Custom UI Shortcut",
                "bl_options": {"INTERNAL"},
                "__annotations__": {"command": bpy.props.StringProperty()},
                "invoke": invoke,
                "execute": execute,
            },
        )
        bpy.utils.register_class(cls)
        self.operator_class = cls

    def bind(self, command, context, callback, *, valid=lambda context: True):
        if self.operator_class is None:
            raise RuntimeError("Register the host's shortcut registry first")
        if not command or len(command) > 256 or context.window is None:
            raise ValueError("A bounded command name and owning window are required")
        key = (
            context.window.as_pointer(),
            context.area.as_pointer() if context.area else 0,
            command,
        )
        entry = (callback, valid)
        self.commands[key] = entry
        self.commands.move_to_end(key)
        while len(self.commands) > self.limit:
            self.commands.popitem(last=False)
        return key, entry

    def release(self, token):
        """Release only this binding; a newer same-key owner must survive."""
        key, entry = token
        if self.commands.get(key) is entry:
            self.commands.pop(key, None)

    def available(self, command, context):
        if self.operator_class is None or context.window is None:
            return False
        entry = self.commands.get(
            (
                context.window.as_pointer(),
                context.area.as_pointer() if context.area else 0,
                command,
            )
        )
        try:
            return bool(entry and entry[1](context))
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def dispatch(self, command, context, event=None):
        if not self.available(command, context):
            return {"CANCELLED"}
        callback, valid = self.commands[
            (
                context.window.as_pointer(),
                context.area.as_pointer() if context.area else 0,
                command,
            )
        ]
        try:
            if not valid(context):
                return {"CANCELLED"}
            result = callback(context, event)
            self.error = None
            return {"CANCELLED"} if result is False else {"FINISHED"}
        except Exception as error:
            self.error = str(error)
            return {"CANCELLED"}

    def entry(self, command, context):
        from .context_shortcuts import Action

        return Action(
            self.idname,
            {"command": command},
            context,
            keymap=self.keymap,
            conflict_keymaps=self.conflict_keymaps,
            valid=lambda c: self.available(command, c),
        ).entry(context)

    def unbind(self, command, context):
        if context.window is not None:
            self.commands.pop(
                (
                    context.window.as_pointer(),
                    context.area.as_pointer() if context.area else 0,
                    command,
                ),
                None,
            )

    def close(self):
        import bpy

        self.commands.clear()
        cls, self.operator_class = self.operator_class, None
        if cls is not None and cls.is_registered:
            bpy.utils.unregister_class(cls)
