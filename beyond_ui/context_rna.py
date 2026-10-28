"""Capability-checked public RNA context actions; host owns undo and registration.

No active native button operators, private driver ABI, or BVT product imports.
"""

from copy import deepcopy
from dataclasses import replace
from .context_menu import Entry, Shortcut

_SHORTCUTS = {
    "RESET": ("ui.reset_default_button", {}),
    "PATH": ("ui.copy_data_path_button", {"full_path": False}),
    "FULL_PATH": ("ui.copy_data_path_button", {"full_path": True}),
    "KEY": ("anim.keyframe_insert_button", {}),
    "DELETE_KEY": ("anim.keyframe_delete_button", {}),
    "DRIVER": ("anim.driver_button_add", {}),
    "REMOVE_DRIVER": ("anim.driver_button_remove", {}),
    "MANUAL": ("wm.doc_view_manual_ui_context", {}),
}


def decorate(rows, context):
    """Snapshot user shortcuts only while opening a page."""
    config = getattr(
        getattr(getattr(context, "window_manager", None), "keyconfigs", None),
        "user",
        None,
    )
    maps = (
        [config.keymaps.get(n) for n in ("User Interface", "Screen")] if config else ()
    )
    result = []
    for row in rows:
        operator, props = _SHORTCUTS.get(row.key, ("", {}))
        bindings = []
        label = ""
        for keymap in maps:
            for item in keymap.keymap_items if keymap else ():
                if (
                    not item.active
                    or item.idname != operator
                    or item.value not in {"PRESS", "ANY"}
                ):
                    continue
                if any(
                    getattr(item.properties, k, None) != v for k, v in props.items()
                ):
                    continue
                formatter = getattr(item, "to_string", None)
                if not label and callable(formatter):
                    try:
                        label = formatter(compact=True)
                    except TypeError:
                        label = formatter()
                bindings.append(
                    Shortcut(
                        item.type,
                        item.shift,
                        item.ctrl,
                        item.alt,
                        item.oskey,
                        item.any,
                        item.key_modifier,
                    )
                )
        result.append(
            replace(
                row,
                shortcut=label or row.shortcut,
                bindings=tuple(bindings) or row.bindings,
            )
        )
    return result


class Property:
    def __init__(
        self,
        resolve,
        name,
        index=None,
        commit=lambda before, after: None,
        update=lambda: None,
    ):
        self.resolve, self.name, self.index, self.commit = resolve, name, index, commit
        self.update = update
        owner = resolve()
        self.identity = self._identity(owner)

    @staticmethod
    def _identity(owner):
        if owner is None:
            raise ReferenceError("Property owner is unavailable")
        data = getattr(owner, "id_data", None)
        return (data.as_pointer() if data is not None else None, owner.as_pointer())

    def owner(self):
        owner = self.resolve()
        if (
            self._identity(owner) != self.identity
            or self.name not in owner.bl_rna.properties
        ):
            raise ReferenceError("Context-menu property owner changed")
        if self.index is not None and not 0 <= self.index < len(
            getattr(owner, self.name)
        ):
            raise ReferenceError("Context-menu component disappeared")
        return owner

    def valid(self):
        try:
            self.owner()
            return True
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    def editable(self):
        owner = self.owner()
        data = getattr(owner, "id_data", None)
        return (
            data is None or getattr(data, "is_editable", True)
        ) and not owner.is_property_readonly(self.name)

    def component(self, index):
        self.owner()
        return Property(self.resolve, self.name, index, self.commit, self.update)

    def paths(self):
        owner = self.owner()
        path = owner.path_from_id(self.name)
        if self.index is not None:
            path += f"[{self.index}]"
        return path, repr(owner.id_data) + "." + path

    def read(self, owner=None):
        owner = self.owner() if owner is None else owner
        value = getattr(owner, self.name)
        return (
            tuple(value)
            if getattr(owner.bl_rna.properties[self.name], "is_array", False)
            else value
        )

    def assign(self, owner, value):
        if self.index is None:
            setattr(owner, self.name, value)
        else:
            getattr(owner, self.name)[self.index] = value[self.index]

    def selected(self, context):
        import bpy

        owner = self.owner()
        if not isinstance(owner, bpy.types.Object):
            return ()
        return tuple(
            o
            for o in context.selected_objects
            if o != owner
            and o.is_editable
            and self.name in o.bl_rna.properties
            and not o.is_property_readonly(self.name)
            and (self.index is None or self.index < len(getattr(o, self.name)))
        )

    def execute(self, key, target, context):
        owner = self.owner()
        meta = owner.bl_rna.properties[self.name]
        if key in {"PATH", "FULL_PATH"}:
            context.window_manager.clipboard = self.paths()[key == "FULL_PATH"]
            return
        if key in {"MANUAL", "API"}:
            import bpy

            operator = (
                bpy.ops.wm.doc_view_manual if key == "MANUAL" else bpy.ops.wm.doc_view
            )
            return operator(doc_id=f"{owner.bl_rna.identifier}.{self.name}")
        if not self.editable():
            raise PermissionError("Property is read-only")
        if key == "RESET":
            before = self.read()
            value = (
                tuple(meta.default_array)
                if getattr(meta, "is_array", False)
                else meta.default
            )
            try:
                self.assign(owner, value)
                self.update()
                self.commit(before, self.read())
            except Exception:
                setattr(owner, self.name, before)
                self.update()
                raise
        elif key == "SELECTED":
            value = self.read()
            before = []
            try:
                for obj in self.selected(context):
                    before.append((obj, deepcopy(self.read(obj))))
                    self.assign(obj, value)
                if before:
                    self.update()
                    self.commit(
                        tuple(v for _, v in before),
                        tuple(self.read(o) for o, _ in before),
                    )
            except Exception:
                for obj, old in reversed(before):
                    setattr(obj, self.name, old)
                self.update()
                raise
        elif key in {"KEY", "DELETE_KEY", "DRIVER", "REMOVE_DRIVER"}:
            if target.commit is None:
                raise RuntimeError("Host undo callback is required")
            data = owner.id_data
            path = owner.path_from_id(self.name)
            index = -1 if self.index is None else self.index
            if key in {"KEY", "DELETE_KEY"}:
                fn = data.keyframe_insert if key == "KEY" else data.keyframe_delete
                if not fn(
                    data_path=path, index=index, frame=context.scene.frame_current
                ):
                    return
            elif key == "DRIVER":
                data.driver_add(path, index)
            elif not data.driver_remove(path, index):
                return
            target.commit(key)

    def entries(self, target, context):
        if context is None:
            return ()
        owner = self.owner()
        meta = owner.bl_rna.properties[self.name]

        def editable(t, c):
            return t.editable() and self.valid() and self.editable()

        def add(key, label, enabled=True, tip="", divider=False, icon=""):
            rows.append(
                Entry(
                    key,
                    label,
                    lambda t, c: self.execute(key, t, c),
                    enabled,
                    icon=icon,
                    tip=tip,
                    divider=divider,
                )
            )

        rows = []
        defaults = hasattr(
            meta, "default_array" if getattr(meta, "is_array", False) else "default"
        )
        add(
            "RESET",
            "Reset to Default Value",
            editable if defaults else False,
            icon="reset",
        )
        add(
            "SELECTED",
            "Copy to Selected",
            lambda t, c: editable(t, c) and bool(self.selected(c)),
        )
        add("PATH", "Copy Data Path")
        add("FULL_PATH", "Copy Full Data Path")
        animated = getattr(meta, "is_animatable", False) and meta.type in {
            "FLOAT",
            "INT",
            "BOOLEAN",
            "ENUM",
        }
        if animated:
            for key, label, method in (
                ("KEY", "Insert Keyframe", "keyframe_insert"),
                ("DELETE_KEY", "Delete Keyframe", "keyframe_delete"),
                ("DRIVER", "Add Driver", "driver_add"),
                ("REMOVE_DRIVER", "Remove Driver", "driver_remove"),
            ):
                add(
                    key,
                    label,
                    lambda t, c, m=method: editable(t, c)
                    and t.commit is not None
                    and callable(getattr(self.owner().id_data, m, None)),
                    "Requires an editable property and a host undo callback.",
                    key == "KEY",
                    "◇" if "KEY" in key else "◌",
                )
            for key, label in (
                ("COPY_DRIVER", "Copy Driver"),
                ("PASTE_DRIVER", "Paste Driver"),
                ("NATIVE_DRIVER", "Copy as New Driver"),
            ):
                add(
                    key,
                    label,
                    False,
                    "Requires an explicitly supplied, admitted driver clipboard adapter.",
                )
        reason = "Requires a native Blender button; unavailable on the custom canvas."
        add("FAVORITE", "Add to Quick Favorites", False, reason, True, "menu")
        add("SHORTCUT", "Assign Shortcut", False, reason, True, "shortcut")
        add("MANUAL", "Online Manual", True, divider=True, icon="globe")
        if getattr(context.preferences.view, "show_developer_ui", False):
            add("API", "Online Python Reference")
            add(
                "SOURCE", "Edit Source", False, "Host source-location adapter required."
            )
        from .context_extensions import entries

        extra = entries(context, self)
        if extra:
            extra[0] = replace(extra[0], divider=True)
        return decorate(rows, context) + list(extra)
