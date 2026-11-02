"""Opt-in class presentation hints, resolved only during retained authoring."""

from collections.abc import Mapping
from math import isfinite


def property_options(data, name, overrides=None):
    result = {}
    identifier = getattr(getattr(data, "bl_rna", None), "identifier", type(data).__name__)
    for mapping in (getattr(type(data), "beyond_ui_props", {}), overrides or {}):
        if not isinstance(mapping, Mapping):
            raise ValueError("beyond_ui_props must map property names to presentation hints")
        for key in (name, identifier + "." + name):
            entry = mapping.get(key, {})
            if not isinstance(entry, Mapping):
                raise ValueError("Property presentation hints must be a mapping")
            result.update(entry)
    allowed = {"precision", "suffix", "value_width", "width", "slider", "trailing_icon", "disabled_accent"}
    if set(result) - allowed:
        raise ValueError("Unknown Beyond UI property presentation hint")
    for key, value in result.items():
        if key == "precision" and (type(value) is not int or not 0 <= value <= 6):
            raise ValueError("precision must be an integer from 0 through 6")
        if key in {"width", "value_width"} and (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or not 24 <= value <= 240
        ):
            raise ValueError("field widths must be finite logical units from 24 through 240")
        if key in {"slider", "disabled_accent"} and type(value) is not bool:
            raise ValueError(key + " must be Boolean")
        if key in {"suffix", "trailing_icon"} and (
            not isinstance(value, str) or len(value) > 64 or any(ord(c) < 32 for c in value)
        ):
            raise ValueError(key + " must be short display text")
    return result
