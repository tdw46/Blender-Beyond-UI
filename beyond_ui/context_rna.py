"""Capability-checked public RNA context actions; host owns undo and registration.

No active native button operators or BVT product imports. Native actions are
separately admitted by exact platform, source and executable fingerprints.
"""

from copy import deepcopy
from dataclasses import replace
from .context_menu import Entry, Shortcut
from .rna_owner import identity, readonly

_SHORTCUTS = {
    "RESET": ("ui.reset_default_button", {}),
    "PATH": ("ui.copy_data_path_button", {"full_path": False}),
    "FULL_PATH": ("ui.copy_data_path_button", {"full_path": True}),
    "KEY": ("anim.keyframe_insert_button", {}),
    "DELETE_KEY": ("anim.keyframe_delete_button", {}),
    "DRIVER": ("anim.driver_button_add", {}),
    "REMOVE_DRIVER": ("anim.driver_button_remove", {}),
    "COPY_DRIVER": ("anim.copy_driver_button", {}),
    "PASTE_DRIVER": ("anim.paste_driver_button", {}),
    "NATIVE_DRIVER": ("ui.copy_as_driver_button", {}),
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
                        hyper=getattr(item, "hyper", 0),
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
        source=None,
        enum_value=None,
    ):
        self.resolve, self.name, self.index, self.commit = resolve, name, index, commit
        self.update = update
        self.source = source
        self.enum_value = enum_value
        owner = resolve()
        self.identity = self._identity(owner)

    _identity = staticmethod(identity)

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
        return (data is None or getattr(data, "is_editable", True)) and not readonly(
            owner, self.name
        )

    def component(self, index):
        self.owner()
        return Property(
            self.resolve,
            self.name,
            index,
            self.commit,
            self.update,
            self.source,
            self.enum_value,
        )

    def paths(self):
        owner = self.owner()
        path = (
            owner.path_from_id(self.name)
            if callable(getattr(owner, "as_pointer", None))
            else owner.path_from_id() + "." + self.name
        )
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
        if key in {"COPY_DRIVER", "PASTE_DRIVER", "NATIVE_DRIVER"}:
            from .hosts.menu_native import driver_apply

            return driver_apply(key, self, target)
        if key == "REMOVE_FAVORITE":
            from .hosts.menu_native import property_favorite

            if not property_favorite(self, context, remove=True):
                raise ReferenceError("Favorite no longer exists")
            return
        if key == "FAVORITE":
            from .hosts.menu_native import add_property_favorite

            return add_property_favorite(self, context)
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
            path = (
                owner.path_from_id(self.name)
                if callable(getattr(owner, "as_pointer", None))
                else owner.path_from_id() + "." + self.name
            )
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
        from .hosts import menu_native
        from .context_paths import owner_path

        if meta.type in {"FLOAT", "INT", "BOOLEAN", "ENUM"}:
            for key, label in (
                ("COPY_DRIVER", "Copy Driver"),
                ("PASTE_DRIVER", "Paste Driver"),
                ("NATIVE_DRIVER", "Copy as New Driver"),
            ):
                add(
                    key,
                    label,
                    lambda t, c, k=key: menu_native.driver_enabled(k, self, t),
                    "Uses Blender's driver clipboard on admitted builds; paste requires host undo.",
                )
        is_favorite = menu_native.property_favorite(self, context)
        favorite_path = owner_path(self, context)
        add(
            "REMOVE_FAVORITE" if is_favorite else "FAVORITE",
            "Remove from Quick Favorites" if is_favorite else "Add to Quick Favorites",
            lambda t, c: c.area is not None
            and favorite_path is not None
            and owner_path(self, c) == favorite_path
            and menu_native.api() is not None,
            "Add this context-relative property to Blender's real Quick Favorites.",
            True,
            "menu",
        )
        from .context_shortcuts import property_entry

        rows.append(replace(property_entry(self, context), divider=True))
        add("MANUAL", "Online Manual", True, divider=True, icon="globe")
        if getattr(context.preferences.view, "show_developer_ui", False):
            add("API", "Online Python Reference")
            from .context_source import entry

            rows.append(entry(self.source))
        from .context_extensions import entries

        extra = entries(context, self)
        if extra:
            extra[0] = replace(extra[0], divider=True)
        if getattr(context.preferences.view, "show_tooltips_python", False):
            hint = f"Python: {owner.bl_rna.identifier}.{self.name}"
            rows = [replace(row, tip=(row.tip + "\n" + hint).strip()) for row in rows]
        return decorate(rows, context) + list(extra)
