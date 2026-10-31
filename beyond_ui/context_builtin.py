"""Bounded native property-command translations for contributed custom menus.

Never invoke operators against an unrelated active native button. Resolve their
public arguments and route supported commands through the captured RNA owner.
"""

from .context_menu import Entry

COMMANDS = {
    "ui.assign_default_button": ("ASSIGN_DEFAULT", None),
    "ui.override_add_button": ("OVERRIDE_ADD", "all"),
    "ui.override_remove_button": ("OVERRIDE_REMOVE", "all"),
    "ui.reset_default_button": ("RESET", "all"),
    "ui.copy_to_selected_button": ("SELECTED", "all"),
    "ui.copy_data_path_button": ("PATH", "full_path"),
    "ui.copy_driver_to_selected_button": ("COPY_DRIVERS_SELECTED", "all"),
}


def entry(idname, info, source, snapshot, scope, permitted, text, icon):
    key, option = COMMANDS[idname]
    meta = info.properties.get(option) if option else None
    default = meta.default if meta is not None and meta.type == "BOOLEAN" else None
    identity = info.as_pointer()

    def resolve(target, context):
        from .context_extensions import operator

        scope()  # Revalidate captured pointer contexts, even for built-in actions.
        if (
            not permitted
            or source is None
            or not source.valid()
            or (option is not None and default is None)
            or not snapshot.valid()
            or operator(idname).get_rna_type().as_pointer() != identity
        ):
            return None
        values = snapshot.values()
        if (
            set(values) - ({option} if option else set())
            or option is not None
            and type(values.get(option, default)) is not bool
        ):
            return None
        value = values.get(option, default)
        binding = source.component(None) if option == "all" and value else source
        action = "FULL_PATH" if key == "PATH" and value else key
        if key != "PATH":
            if not target.editable() or not binding.editable():
                return None
            if key == "RESET":
                prop = binding.metadata()
                if not hasattr(
                    prop,
                    "default_array" if getattr(prop, "is_array", False) else "default",
                ):
                    return None
            elif key == "ASSIGN_DEFAULT":
                from .context_custom import CustomProperty

                if not isinstance(binding, CustomProperty) or target.commit is None:
                    return None
            elif key in {"OVERRIDE_ADD", "OVERRIDE_REMOVE"}:
                from .context_overrides import entries

                row = next((r for r in entries(binding) if r.key == key), None)
                if row is None or not row.enabled(target, context):
                    return None
            elif key == "COPY_DRIVERS_SELECTED":
                from .context_drivers import plan

                if not plan(binding, target, context):
                    return None
            elif not binding.selected(context):
                return None
        return binding, action

    def execute(target, context):
        resolved = resolve(target, context)
        if resolved is None:
            raise ReferenceError("Contributed property action became unavailable")
        binding, action = resolved
        return binding.execute(action, target, context)

    return Entry(
        idname,
        text or info.name,
        execute,
        lambda t, c: resolve(t, c) is not None,
        icon=icon,
        tip=info.description,
    )
