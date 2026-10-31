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
    "COPY_DRIVERS_SELECTED": ("ui.copy_driver_to_selected_button", {"all": False}),
    "COPY_DRIVERS_SELECTED_ALL": ("ui.copy_driver_to_selected_button", {"all": True}),
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
        from .rna_owner import guarded

        resolve = guarded(resolve)
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

    def editable(self, owner=None):
        owner = self.owner() if owner is None else owner
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

    def metadata(self, owner=None):
        return (self.owner() if owner is None else owner).bl_rna.properties[self.name]

    def property_path(self, owner=None):
        owner = self.owner() if owner is None else owner
        return (
            owner.path_from_id(self.name)
            if callable(getattr(owner, "as_pointer", None))
            else owner.path_from_id() + "." + self.name
        )

    def paths(self):
        owner = self.owner()
        path = self.property_path(owner)
        if self.index is not None:
            path += f"[{self.index}]"
        return path, repr(owner.id_data) + "." + path

    def read(self, owner=None):
        owner = self.owner() if owner is None else owner
        value = getattr(owner, self.name)
        return (
            tuple(value) if getattr(self.metadata(owner), "is_array", False) else value
        )

    def assign(self, owner, value):
        if self.index is None:
            setattr(owner, self.name, value)
        else:
            getattr(owner, self.name)[self.index] = value[self.index]

    def selected(self, context):
        from .context_selected import owners

        return owners(self, context)

    def animation_applicable(self, key):
        """Revalidate mutually exclusive keyframe/driver channels before mutation."""
        from .decorator import channel_collections

        owner = self.owner()
        collections, drivers = channel_collections(owner.id_data)
        path = self.property_path(owner)

        def matches(curve):
            return curve.data_path == path and (
                self.index is None or curve.array_index == self.index
            )

        if key in {"KEY", "DELETE_KEY"}:
            return not any(matches(f) for f in drivers or ())
        if key in {"DRIVER", "PASTE_DRIVER"}:
            return not any(matches(f) for c in collections for f in c) and (
                key == "PASTE_DRIVER" or not any(matches(f) for f in drivers or ())
            )
        return True

    def removable_animation(self, key, context):
        """Resolve the clicked channel on input, never during menu painting."""
        from bisect import bisect_left
        from .decorator import channel_collections

        owner = self.owner()
        collections, drivers = channel_collections(owner.id_data)
        path = self.property_path(owner)
        curves = (
            (drivers if drivers is not None else ())
            if key == "REMOVE_DRIVER"
            else (curve for collection in collections for curve in collection)
        )
        frame = context.scene.frame_current_final
        for curve in curves:
            if curve.data_path != path or (
                self.index is not None and curve.array_index != self.index
            ):
                continue
            if key == "REMOVE_DRIVER":
                return True
            if key == "CLEAR_KEYS":
                return True
            points = curve.keyframe_points
            index = bisect_left(points, frame - 1e-4, key=lambda p: p.co[0])
            if index < len(points) and abs(points[index].co[0] - frame) < 1e-4:
                return True
        return False

    def execute(self, key, target, context):
        if key.endswith("_ALL") and key[:-4] in {
            "RESET",
            "SELECTED",
            "KEY",
            "DELETE_KEY",
            "CLEAR_KEYS",
            "REMOVE_DRIVER",
            "COPY_DRIVERS_SELECTED",
            "OVERRIDE_ADD",
            "OVERRIDE_REMOVE",
        }:
            return self.component(None).execute(key[:-4], target, context)
        if key in {"OVERRIDE_ADD", "OVERRIDE_REMOVE"}:
            from .context_overrides import entries

            row = next((r for r in entries(self) if r.key == key), None)
            if row is None or not row.enabled(target, context):
                raise ReferenceError("Library override action is unavailable")
            return row.action(target, context)
        owner = self.owner()
        meta = self.metadata(owner)

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

            if key == "PASTE_DRIVER" and not self.animation_applicable(key):
                raise RuntimeError("Cannot paste a driver over keyed channels")
            return driver_apply(key, self, target)
        if key == "COPY_DRIVERS_SELECTED":
            from .context_drivers import copy_selected

            return copy_selected(self, target, context)
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
            if (before if self.index is None else before[self.index]) == (
                value if self.index is None else value[self.index]
            ):
                return
            try:
                self.assign(owner, value)
                self.update()
                self.commit(before, self.read())
            except Exception:
                self.assign(owner, before)
                self.update()
                raise
        elif key == "SELECTED":
            value = self.read()
            before = []
            try:
                for obj in self.selected(context):
                    old = deepcopy(self.read(obj))
                    if (old if self.index is None else old[self.index]) == (
                        value if self.index is None else value[self.index]
                    ):
                        continue
                    before.append((obj, old))
                    self.assign(obj, value)
                if before:
                    self.update()
                    self.commit(
                        tuple(v for _, v in before),
                        tuple(self.read(o) for o, _ in before),
                    )
            except Exception:
                for obj, old in reversed(before):
                    self.assign(obj, old)
                self.update()
                raise
        elif key in {"KEY", "DELETE_KEY", "CLEAR_KEYS", "DRIVER", "REMOVE_DRIVER"}:
            if target.commit is None:
                raise RuntimeError("Host undo callback is required")
            if key in {
                "DELETE_KEY",
                "CLEAR_KEYS",
                "REMOVE_DRIVER",
            } and not self.removable_animation(key, context):
                return
            if not self.animation_applicable(key):
                return
            data = owner.id_data
            path = (
                self.property_path(owner)
                if callable(getattr(owner, "as_pointer", None))
                else owner.path_from_id() + "." + self.name
            )
            index = -1 if self.index is None else self.index
            if key == "CLEAR_KEYS":
                from .decorator import channel_collections

                collections, _ = channel_collections(data)
                for collection in collections:
                    for curve in tuple(collection):
                        if curve.data_path == path and (
                            self.index is None or curve.array_index == self.index
                        ):
                            collection.remove(curve)
            elif key in {"KEY", "DELETE_KEY"}:
                fn = data.keyframe_insert if key == "KEY" else data.keyframe_delete
                if not fn(
                    data_path=path, index=index, frame=context.scene.frame_current_final
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
        meta = self.metadata(owner)

        # OperatorProperties can belong to WindowManager but have no persistent
        # data path. Their editable defaults are real; animation/path actions are not.
        try:
            self.property_path(owner)
            pathable = True
        except (AttributeError, TypeError, ValueError, ReferenceError):
            pathable = False

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
            lambda t, c: pathable and editable(t, c) and bool(self.selected(c)),
        )
        add("PATH", "Copy Data Path", pathable)
        add("FULL_PATH", "Copy Full Data Path", pathable)
        animated = (
            pathable
            and hasattr(getattr(owner, "id_data", None), "animation_data")
            and getattr(meta, "is_animatable", False)
            and meta.type
            in {
                "FLOAT",
                "INT",
                "BOOLEAN",
                "ENUM",
            }
        )
        if animated:
            for key, label, method in (
                (
                    "KEY",
                    "Replace Keyframe"
                    if self.removable_animation("DELETE_KEY", context)
                    else "Insert Keyframe",
                    "keyframe_insert",
                ),
                ("DELETE_KEY", "Delete Keyframe", "keyframe_delete"),
                ("CLEAR_KEYS", "Clear Keyframes", "keyframe_delete"),
                ("DRIVER", "Add Driver", "driver_add"),
                ("REMOVE_DRIVER", "Remove Driver", "driver_remove"),
            ):
                add(
                    key,
                    label,
                    lambda t, c, m=method, k=key: editable(t, c)
                    and t.commit is not None
                    and callable(getattr(self.owner().id_data, m, None))
                    and self.animation_applicable(k)
                    and (
                        k not in {"DELETE_KEY", "CLEAR_KEYS", "REMOVE_DRIVER"}
                        or self.removable_animation(k, c)
                    ),
                    "Requires an editable property and a host undo callback.",
                    key == "KEY",
                    "◇" if "KEY" in key else "◌",
                )
            from .context_keying import entries as keying_entries

            rows.extend(keying_entries(self, target, context))
            from .context_drivers import entries as driver_entries

            rows.extend(driver_entries(self))
            from .context_editor import entries as editor_entries

            rows.extend(editor_entries(self))
        if self.index is not None:
            whole = self.component(None)
            alternatives = [
                ("RESET", "Reset All to Default Values"),
                ("SELECTED", "Copy All to Selected"),
            ]
            if animated:
                alternatives += [
                    (
                        "KEY",
                        "Replace All Keyframes"
                        if self.removable_animation("DELETE_KEY", context)
                        else "Insert All Keyframes",
                    ),
                    ("DELETE_KEY", "Delete All Keyframes"),
                    ("CLEAR_KEYS", "Clear All Keyframes"),
                    ("REMOVE_DRIVER", "Remove All Drivers"),
                ]
            for key, label in alternatives:
                original = next(row for row in rows if row.key == key)
                rows.insert(
                    rows.index(original) + 1,
                    replace(
                        original,
                        key=key + "_ALL",
                        label=label,
                        action=lambda t, c, k=key: whole.execute(k, t, c),
                        enabled=lambda t, c, k=key: editable(t, c)
                        and whole.animation_applicable(k)
                        and (bool(whole.selected(c)) if k == "SELECTED" else True)
                        and (
                            t.commit is not None
                            if k in {"KEY", "DELETE_KEY", "CLEAR_KEYS", "REMOVE_DRIVER"}
                            else True
                        )
                        and (
                            whole.removable_animation(k, c)
                            if k in {"DELETE_KEY", "CLEAR_KEYS", "REMOVE_DRIVER"}
                            else True
                        ),
                    ),
                )
        if meta.type == "STRING" and meta.subtype in {"FILE_PATH", "DIR_PATH"}:
            from .context_files import entries as file_entries

            rows.extend(file_entries(self))
        if meta.type == "POINTER":
            from .context_assets import entries as asset_entries

            rows.extend(asset_entries(lambda: self.read(), context))
            from .context_jump import entries as jump_entries

            rows.extend(jump_entries(lambda: self.read()))
        from .context_overrides import entries as override_entries

        rows.extend(override_entries(self))
        from .context_native_entries import entries as native_entries

        rows.extend(native_entries(self, context))
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
