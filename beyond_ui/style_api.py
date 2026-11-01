"""Small, native-safe presentation helpers. Styles are data, never executable CSS."""

from collections.abc import Mapping
from copy import deepcopy, copy
from math import isfinite

_LAYOUT = {
    "padding",
    "margin",
    "gap",
    "width",
    "height",
    "min_width",
    "max_width",
    "min_height",
    "max_height",
    "align",
    "flex_grow",
    "display",
    "template",
}
_NUMERIC = {"units", "precision", "value_width", "slider", "disabled_accent"}
_VISUAL = {
    "colors",
    "color",
    "background",
    "accent",
    "opacity",
    "radius",
    "font_size",
    "font_weight",
    "text_align",
    "icon",
    "trailing_icon",
    "motion",
    "variant",
    "wrap",
    "list_row_height",
    "list_rows",
    "label_position",
    "label_width",
}


def _number(name, value, low, high):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(f"{name} must be finite in [{low}, {high}]")
    return value


def _edges(name, value):
    values = (value,) if isinstance(value, (int, float)) else tuple(value)
    if not 1 <= len(values) <= 4:
        raise ValueError(name + " requires one to four CSS-order values")
    for v in values:
        _number(name, v, 0, 128)
    if len(values) == 1:
        return values * 4
    if len(values) == 2:
        return values * 2
    if len(values) == 3:
        return values + (values[1],)
    return values


def normalize(*presets, **options):
    from .stylesheet import color, _COLORS

    result = {}
    for preset in (*presets, options):
        if not isinstance(preset, Mapping):
            raise TypeError("Style presets must be mappings")
        for key, value in preset.items():
            if key in {"colors", "motion"} and key in result:
                result[key] = {**result[key], **value}
            else:
                result[key] = deepcopy(value)
    unknown = result.keys() - _LAYOUT - _NUMERIC - _VISUAL
    if unknown:
        raise ValueError("Unsupported style properties: " + ", ".join(sorted(unknown)))
    for key, value in tuple(result.items()):
        if key in {"padding", "margin"}:
            result[key] = _edges(key, value)
        elif key in {
            "width",
            "height",
            "min_width",
            "max_width",
            "min_height",
            "max_height",
        }:
            _number(key, value, 1, 4096)
        elif key == "list_row_height":
            _number(key, value, 28, 88)
        elif key == "list_rows":
            if type(value) is not int or not 1 <= value <= 128:
                raise ValueError("list_rows must be an integer in [1, 128]")
        elif key == "label_width":
            _number(key, value, 0, 320)
        elif key == "label_position" and value not in {"auto", "left", "top"}:
            raise ValueError("label_position must be auto, left or top")
        elif key == "display" and value not in {"flex", "none"}:
            raise ValueError("display must be flex or none")
        elif key == "wrap" and type(value) is not bool:
            raise ValueError("wrap must be Boolean")
        elif key in {"gap", "radius"}:
            _number(key, value, 0, 64)
        elif key == "flex_grow":
            _number(key, value, 0.01, 100)
        elif key == "font_size":
            _number(key, value, 8, 32)
        elif key == "value_width":
            _number(key, value, 24, 240)
        elif key == "opacity":
            _number(key, value, 0, 1)
        elif key == "precision":
            if type(value) is not int or not 0 <= value <= 6:
                raise ValueError("precision must be an integer in [0, 6]")
        elif key in {"slider", "disabled_accent"} and type(value) is not bool:
            raise ValueError(key + " must be Boolean")
        elif key in {"align", "text_align"}:
            value = str(value).upper()
            if value not in {"LEFT", "CENTER", "RIGHT", "EXPAND"}:
                raise ValueError(key + " must be left, center, right or expand")
            result[key] = value
        elif key == "font_weight" and value not in {"normal", "bold"}:
            raise ValueError("font_weight must be normal or bold")
        elif key in {"units", "icon", "trailing_icon", "variant", "template"}:
            if (
                not isinstance(value, str)
                or len(value) > 64
                or any(ord(c) < 32 for c in value)
            ):
                raise ValueError(key + " must be short display text")
        elif key in {"color", "background", "accent"}:
            result[key] = color(value)
        elif key == "colors":
            if not isinstance(value, Mapping) or value.keys() - _COLORS:
                raise ValueError("colors must map shared theme roles to colors")
            result[key] = {k: color(v) for k, v in value.items()}
        elif key == "motion":
            from .animation import AnimationSettings

            if not isinstance(value, Mapping) or value.keys() - {
                "enabled",
                "strength",
                "speed",
            }:
                raise ValueError("motion accepts enabled, strength and speed")
            if "enabled" in value and type(value["enabled"]) is not bool:
                raise ValueError("motion.enabled must be Boolean")
            AnimationSettings(**value)
    for axis in ("width", "height"):
        if result.get("min_" + axis, 0) > result.get("max_" + axis, 4096):
            raise ValueError("min_" + axis + " exceeds max_" + axis)
    return result


def style(layout, *presets, scope="last", **options):
    """Style the preceding item on this exact layout; native UILayout is a no-op.

    scope='group' sets container geometry and shared visual defaults for existing
    and future children. Formatting options belong to individual properties.
    """
    from .layout import Layout
    from .layout_recording import Node

    values = normalize(*presets, **options)
    if scope not in {"last", "group"}:
        raise ValueError("scope must be last or group")
    if scope == "group" and values.keys() & _NUMERIC:
        raise ValueError("Numeric formatting belongs to scope=last")
    if isinstance(layout, (Layout, Node)):
        layout.style_item(values, scope=scope)
    return layout


def prop(layout, data, property, *, style=None, **native_options):
    """Optional one-call form. Only native_options reach Blender's prop()."""
    values = normalize(style or {})  # Validate before emitting anything.
    result = layout.prop(data, property, **native_options)
    globals()["style"](layout, values)
    return result


def _leaves(node):
    if hasattr(node, "children"):
        for child in node.children:
            yield from _leaves(child)
    else:
        yield node


def prepare_control(control, values):
    """Preflight without mutating any control; compound styles commit atomically."""
    merged = normalize(control.options.get("_inline_style", {}), values)
    numeric = None
    if control.kind == "number" and values.keys() & _NUMERIC:
        numeric = copy(control.options["numeric"])
        presentation = dict(numeric.presentation)
        if "precision" in merged:
            presentation["precision"] = merged["precision"]
            numeric.precision = merged["precision"]
        if "units" in merged:
            presentation.pop("suffix", None)
            presentation["units"] = merged["units"]
        numeric.presentation = presentation
        numeric.validate_presentation()
    return merged, numeric


def apply_control(control, values, prepared=None):
    from .stylesheet import StyleSheet

    merged, numeric = prepared or prepare_control(control, values)
    control.options["_inline_style"] = merged
    if numeric is not None:
        control.options["numeric"] = numeric
    for key in ("slider", "value_width", "disabled_accent", "icon", "trailing_icon"):
        if key in values:
            control.options[key] = values[key]
    if "wrap" in values:
        control.options["wrap_text"] = values["wrap"]
    if "list_row_height" in values and control.kind == "widget":
        widget = control.options["widget"]
        if hasattr(widget, "row_height"):
            widget.style_row_height = values["list_row_height"]
    if "list_rows" in values and control.kind == "widget":
        control.options["widget"].style_visible_rows = values["list_rows"]
    if "variant" in values:
        control.options["style_class"] = values["variant"]
    if "text_align" in values:
        control.options["text_alignment"] = values["text_align"]
    for key in ("font_size", "font_weight", "radius", "label_width", "label_position"):
        if key in values:
            control.options[key] = values[key]
    colors = dict(merged.get("colors", {}))
    for key, roles in {
        "color": ("text", "title"),
        "background": ("input", "field"),
        "accent": ("accent",),
    }.items():
        if key in merged:
            colors.update({role: merged[key] for role in roles})
    if colors or "opacity" in merged:
        control.options["_inline_sheet"] = StyleSheet(
            colors=colors, opacity=merged.get("opacity", 1)
        )
    if "motion" in merged:
        for key, value in merged["motion"].items():
            setattr(control.motion.settings, key, value)


def apply(layout, values, scope):
    from .canvas import Group

    if scope == "last" and not layout.group.children:
        raise ValueError("style() needs a preceding item on this layout")
    target = layout.group if scope == "group" else layout.group.children[-1]
    # Validate the composed geometry before changing the tree or its controls.
    # Separate calls must obey the same constraints as one merged preset.
    geometry = normalize(
        {k: v for k, v in target.options.items() if k in _LAYOUT and k != "align"},
        {k: v for k, v in values.items() if k in _LAYOUT},
    )
    if values.keys() & {"list_row_height", "list_rows"}:
        from .registered_list import RegisteredList

        if not any(
            isinstance(c.options.get("widget"), RegisteredList) for c in _leaves(target)
        ):
            raise ValueError("List styling requires a registered UIList")
    if values.keys() & _NUMERIC and not any(
        c.kind == "number" for c in _leaves(target)
    ):
        raise ValueError("Numeric style options require a numeric property")
    if "template" in values:
        if scope != "group" or layout.group is not layout.canvas:
            raise ValueError("template applies to the root layout only")
        sheet = layout.canvas.theme.stylesheet
        if (
            sheet is None
            or values["template"] not in sheet.to_dict()["geometry_variants"]
        ):
            raise ValueError("template requires a named StyleSheet geometry variant")
    visual = {k: v for k, v in values.items() if k not in _LAYOUT}
    staged = [(c, prepare_control(c, visual)) for c in _leaves(target)]
    if scope == "last" and not isinstance(target, Group):
        wrapper = Group(layout.canvas, "column", layout.group, _style_wrapper=True)
        layout.group.children[-1] = wrapper
        wrapper.children.append(target)
        target = wrapper
    target.options.update(geometry)
    target.options["_inline_geometry"] = True
    target.options["_style_defaults"] = normalize(
        target.options.get("_style_defaults", {}), visual
    )
    if "align" in geometry:
        target.options["alignment"] = geometry["align"]
    layout.canvas._sized_groups.add(target)
    if values.get("display") == "none":
        hidden_controls = list(_leaves(target))
        hidden = {id(c) for c in hidden_controls}
        for c in hidden_controls:
            c.motion.clear()
        if layout.canvas.hover in {c.key for c in hidden_controls}:
            layout.canvas.hover = None
        owned = (
            layout.canvas.active,
            layout.canvas.keyboard_focus,
            layout.canvas.widget_capture,
            layout.canvas.context_focus,
            (layout.canvas.overlay or {}).get("owner"),
        )
        if any(c is not None and id(c) in hidden for c in owned):
            layout.canvas.cancel()
    for control, prepared in staged:
        apply_control(control, visual, prepared)
    if "template" in values:
        sheet.apply(layout.canvas, variant=values["template"])
    layout.canvas.invalidate()
