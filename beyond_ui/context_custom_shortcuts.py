"""Host-owned, undoable custom numeric property shortcut execution."""

import ast
import json
import math
from .context_paths import ROOTS


def resolve_owner(context, path):
    """Only the attribute/string-index paths produced by owner_path; never eval."""
    if len(path) > 1024:
        raise ValueError("Owner path exceeds shortcut limit")
    node = ast.parse(path, mode="eval").body

    def resolve(item):
        if isinstance(item, ast.Name) and item.id in ROOTS:
            return getattr(context, item.id)
        if isinstance(item, ast.Attribute) and not item.attr.startswith("_"):
            return getattr(resolve(item.value), item.attr)
        if (
            isinstance(item, ast.Subscript)
            and isinstance(item.slice, ast.Constant)
            and type(item.slice.value) is str
        ):
            return resolve(item.value)[item.slice.value]
        raise ValueError("Unsupported custom property owner path")

    return resolve(node)


def assign(context, owner_path, key, kind, value):
    from .context_custom import CustomProperty

    owner = resolve_owner(context, owner_path)
    source = CustomProperty(
        lambda: owner, "[" + json.dumps(key, ensure_ascii=False) + "]"
    )
    number = ast.literal_eval(value)
    expected = {"INT": int, "FLOAT": float}.get(kind)
    if expected is None or type(number) is not expected or source.kind is not expected:
        raise TypeError("Shortcut custom property type changed")
    if type(number) is float and not math.isfinite(number):
        raise ValueError("Shortcut value must be finite")
    if not source.editable():
        raise PermissionError("Shortcut property is read-only")
    before = source.read()
    if before == number:
        return False
    try:
        source.assign(owner, number)
    except Exception:
        if source.valid():
            source.assign(owner, before)
        raise
    return True


def operator_class(idname):
    import bpy

    def execute(self, context):
        try:
            changed = assign(context, self.owner_path, self.key, self.kind, self.value)
            if changed:
                for area in context.screen.areas if context.screen else ():
                    area.tag_redraw()
            return {"FINISHED"} if changed else {"CANCELLED"}
        except (
            AttributeError,
            KeyError,
            ReferenceError,
            RuntimeError,
            TypeError,
            ValueError,
            SyntaxError,
        ) as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}

    namespace, name = idname.split(".")
    return type(
        namespace.upper() + "_OT_" + name,
        (bpy.types.Operator,),
        {
            "bl_idname": idname,
            "bl_label": "Set Custom Property",
            "bl_options": {"UNDO", "INTERNAL"},
            "__annotations__": {
                "owner_path": bpy.props.StringProperty(maxlen=1024),
                "key": bpy.props.StringProperty(),
                "kind": bpy.props.EnumProperty(
                    items=(("INT", "Integer", ""), ("FLOAT", "Float", ""))
                ),
                "value": bpy.props.StringProperty(maxlen=1024),
            },
            "execute": execute,
        },
    )
