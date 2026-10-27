"""Lossless access to the installed Blender UILayout API.

Never drops arguments, copies RNA values or emulates unsupported native methods.
Use supports() for version-dependent members and retain your older-version path.
A Layout belongs to ONE draw callback; do not retain it between redraws.
"""

from functools import wraps


class Layout:
    __slots__ = ("_raw",)

    def __init__(self, layout):
        if layout is None:
            raise ValueError("A live Blender UILayout is required")
        object.__setattr__(self, "_raw", layout)

    @property
    def raw(self):
        """The unchanged UILayout, for C APIs or code requiring exact RNA types."""
        return self._raw

    def supports(self, name):
        return hasattr(self._raw, name)

    def __dir__(self):
        return sorted(set(dir(type(self))) | set(dir(self._raw)))

    @staticmethod
    def _is_layout(value):
        rna = getattr(value, "bl_rna", None)
        return getattr(rna, "identifier", None) == "UILayout"

    @classmethod
    def _wrap(cls, value):
        if cls._is_layout(value):
            return cls(value)
        if isinstance(value, tuple):
            return tuple(cls._wrap(item) for item in value)
        return value

    def __getattr__(self, name):
        value = getattr(self._raw, name)
        if not callable(value):
            return value

        @wraps(value)
        def call(*args, **kwargs):
            args = tuple(a.raw if isinstance(a, Layout) else a for a in args)
            kwargs = {
                k: (v.raw if isinstance(v, Layout) else v) for k, v in kwargs.items()
            }
            return self._wrap(value(*args, **kwargs))

        return call

    def __setattr__(self, name, value):
        setattr(self._raw, name, value)
