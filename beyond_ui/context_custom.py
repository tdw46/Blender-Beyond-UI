"""Scalar numeric ID-property bindings and metadata-default transactions."""

import ast
import json
from types import SimpleNamespace
from .context_rna import Property, decorate
from .context_menu import Entry


def custom_key(name):
    if not name.startswith('["'):
        return None
    try:
        value = ast.literal_eval(name)
    except (ValueError, SyntaxError):
        return None
    return (
        value[0]
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str)
        else None
    )


class CustomProperty(Property):
    def __init__(
        self,
        resolve,
        name,
        index=None,
        commit=lambda a, b: None,
        update=lambda: None,
        source=None,
        enum_value=None,
    ):
        if index is not None:
            raise ValueError("Scalar ID properties have no components")
        self.key = custom_key(name)
        if self.key is None:
            raise ValueError("Use a quoted ID-property path, e.g. '[\"gain\"]'")
        name = "[" + json.dumps(self.key, ensure_ascii=False) + "]"
        super().__init__(resolve, name, index, commit, update, source, enum_value)
        if self.key in resolve().bl_rna.properties:
            raise TypeError("Registered RNA properties must use their RNA binding")
        self.kind = type(resolve()[self.key])
        if self.kind not in (int, float):
            raise TypeError(
                "Custom bindings currently support scalar integer/float ID properties"
            )
        # Validate UI metadata capability on binding construction, never paint.
        self.metadata()

    def owner(self):
        owner = self.resolve()
        if (
            self._identity(owner) != self.identity
            or self.key not in owner
            or type(owner[self.key]) is not self.kind
        ):
            raise ReferenceError("Custom property owner, key or type changed")
        return owner

    def metadata(self, owner=None):
        owner = self.owner() if owner is None else owner
        if self.key not in owner or type(owner[self.key]) is not self.kind:
            raise ReferenceError("Custom property key or type changed")
        ui = owner.id_properties_ui(self.key).as_dict()
        return SimpleNamespace(
            name=self.key,
            description=ui.get("description", ""),
            type="INT" if self.kind is int else "FLOAT",
            subtype=ui.get("subtype", "NONE"),
            unit="NONE",
            is_array=False,
            array_length=0,
            is_animatable=True,
            default=ui.get("default", self.kind()),
            hard_min=ui["min"],
            hard_max=ui["max"],
            soft_min=ui["soft_min"],
            soft_max=ui["soft_max"],
            step=ui.get("step", 1),
            precision=ui.get("precision", 3),
        )

    def property_path(self, owner=None):
        owner = self.owner() if owner is None else owner
        return (
            ("" if owner == owner.id_data else owner.path_from_id())
            + "["
            + json.dumps(self.key, ensure_ascii=False)
            + "]"
        )

    def paths(self):
        path = self.property_path()
        return path, repr(self.owner().id_data) + (
            "" if path.startswith("[") else "."
        ) + path

    def editable(self, owner=None):
        owner = self.owner() if owner is None else owner
        data = owner.id_data
        if not getattr(data, "is_editable", True):
            return False
        return not getattr(
            data, "override_library", None
        ) or owner.is_property_overridable_library(self.name)

    def read(self, owner=None):
        return (self.owner() if owner is None else owner)[self.key]

    def assign(self, owner, value):
        owner[self.key] = self.kind(value)
        owner.id_data.update_tag()

    def component(self, index):
        if index is not None:
            raise ValueError("Scalar ID properties have no components")
        return self

    def execute(self, key, target, context):
        if key != "ASSIGN_DEFAULT":
            return super().execute(key, target, context)
        if (
            not target.valid()
            or not target.editable()
            or not self.editable()
            or target.commit is None
        ):
            raise PermissionError(
                "Assign default requires an editable property and host undo"
            )
        owner = self.owner()
        ui = owner.id_properties_ui(self.key)
        before = ui.as_dict()["default"]
        value = self.read()
        if before == value:
            return
        try:
            ui.update(default=value)
            self.update()
            target.commit(key)
        except Exception:
            if self.valid():
                # Restore only what we changed, preserving other metadata edits.
                owner.id_properties_ui(self.key).update(default=before)
                self.update()
            raise

    def entries(self, target, context):
        if context is None:
            return ()
        rows = []
        for key, label in (
            ("RESET", "Reset to Default Value"),
            ("ASSIGN_DEFAULT", "Assign Value as Default"),
            ("SELECTED", "Copy to Selected"),
            ("PATH", "Copy Data Path"),
            ("FULL_PATH", "Copy Full Data Path"),
            (
                "KEY",
                "Replace Keyframe"
                if self.removable_animation("DELETE_KEY", context)
                else "Insert Keyframe",
            ),
            ("DELETE_KEY", "Delete Keyframe"),
            ("CLEAR_KEYS", "Clear Keyframes"),
            ("DRIVER", "Add Driver"),
            ("REMOVE_DRIVER", "Remove Driver"),
        ):

            def enabled(t, c, k=key):
                if not t.valid() or not self.valid():
                    return False
                if k in {"PATH", "FULL_PATH"}:
                    return True
                if (
                    not t.editable()
                    or not self.editable()
                    or (k != "RESET" and t.commit is None)
                ):
                    return False
                if k == "SELECTED":
                    return bool(self.selected(c))
                return self.animation_applicable(k) and (
                    k not in {"DELETE_KEY", "CLEAR_KEYS", "REMOVE_DRIVER"}
                    or self.removable_animation(k, c)
                )

            rows.append(
                Entry(
                    key,
                    label,
                    lambda t, c, k=key: self.execute(k, t, c),
                    enabled,
                    divider=key == "KEY",
                )
            )
        from .context_keying import entries as keying_entries
        from .context_editor import entries as editor_entries
        from .context_overrides import entries as override_entries

        rows.extend(keying_entries(self, target, context))
        rows.extend(editor_entries(self))
        from .context_drivers import entries as driver_entries

        rows.extend(driver_entries(self))
        rows.extend(override_entries(self))
        from .context_native_entries import entries as native_entries
        from .context_shortcuts import numeric_property_entry

        rows.extend(native_entries(self, context))
        rows.append(numeric_property_entry(self, context))
        from .context_extensions import entries

        extra = entries(context, self)
        if extra:
            from dataclasses import replace

            extra[0] = replace(extra[0], divider=True)
        return decorate(rows, context) + list(extra)


def binding(resolve, name, *, index=None, commit=lambda a, b: None, source=None):
    from .bindings import Binding

    prop = CustomProperty(resolve, name, index, commit, source=source)

    def write(value):
        if not prop.editable():
            raise PermissionError("Custom property is read-only")
        prop.assign(prop.owner(), value)

    def valid():
        return prop.valid() and prop.editable()

    return Binding(prop.read, write, valid, commit, prop)


def metadata(data, name):
    if custom_key(name) is not None:
        return CustomProperty(lambda: data, name).metadata()
    return data.bl_rna.properties[name]
