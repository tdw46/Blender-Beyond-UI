"""Bounded snapshots of contributed operator arguments; no Blender import."""


class Arguments:
    def __init__(self):
        self.tree = ("dict", ())
        self.pointers = []
        self.error = None

    def capture(self, properties):
        self.error = None
        # Blender's mathutils classes can report __module__ == "builtins".
        # Resolve actual loaded classes; importing this library stays bpy-free.
        import sys

        mathutils = sys.modules.get("mathutils")
        math_types = tuple(
            cls
            for name in ("Vector", "Color", "Euler", "Quaternion", "Matrix")
            if isinstance(cls := getattr(mathutils, name, None), type)
        )
        remaining = [512]
        self.pointers.clear()

        def freeze(value, depth=0):
            remaining[0] -= 1
            if depth > 8 or remaining[0] < 0:
                raise ValueError("Operator arguments exceed snapshot bounds")
            if value is None or isinstance(value, (bool, int, float, str)):
                return ("value", value)
            if hasattr(value, "as_pointer"):
                identity = value.as_pointer()
                if not identity:
                    raise ReferenceError("Operator argument owner disappeared")
                self.pointers.append((value, identity))
                return ("value", value)
            if isinstance(value, dict):
                if len(value) > remaining[0]:
                    raise ValueError("Operator arguments exceed snapshot bounds")
                if not all(isinstance(key, str) for key in value):
                    raise TypeError("Operator argument keys must be strings")
                return (
                    "dict",
                    tuple((k, freeze(v, depth + 1)) for k, v in value.items()),
                )
            if type(value).__name__ == "bpy_prop_array" or isinstance(
                value, math_types
            ):
                return (tuple, tuple(freeze(v, depth + 1) for v in value))
            if isinstance(value, (list, tuple, set, frozenset)):
                return (type(value), tuple(freeze(v, depth + 1) for v in value))
            raise TypeError("Unsupported operator argument snapshot type")

        try:
            self.tree = freeze(properties)
        except Exception as error:
            self.tree = ("dict", ())
            self.error = str(error)

    def valid(self):
        if self.error:
            return False
        try:
            return all(value.as_pointer() == ptr for value, ptr in self.pointers)
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def values(self):
        if not self.valid():
            raise ReferenceError(self.error or "Operator argument owner changed")

        def thaw(node):
            kind, value = node
            if kind == "value":
                return value
            if kind == "dict":
                return {k: thaw(v) for k, v in value}
            return kind(thaw(v) for v in value)

        return thaw(self.tree)
