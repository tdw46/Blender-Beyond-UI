"""Exact compound subcontrol targets, resolved on invocation, never on paint."""

from copy import deepcopy
from dataclasses import replace
from .base import contains
from .metrics import COLOR, CURVE, RAMP, PICKER
from ..context_menu import Target
from ..editing import color_hsv


def target(widget, key, x, y):
    from . import (
        ColorPicker,
        ColorRamp,
        CurveMapping,
        DataPicker,
        Palette,
        MatrixView,
        Progress,
    )

    binding = getattr(widget, "binding", None)
    valid = (
        binding.context.valid
        if binding and getattr(binding, "context", None)
        else binding.valid
        if binding
        else lambda: True
    )
    part = ("body",)
    value = binding.read if binding else None
    selected_binding = binding
    if y < 60 and widget.height > 100:
        part = ("title",)
    elif isinstance(widget, ColorPicker):
        for i, r in enumerate(COLOR["fields"]):
            if contains(r, x, y):
                part = ("channel", widget.mode, i)
        for name in ("sv", "hue", "alpha_track", "hex", "eyedropper"):
            if contains(COLOR[name], x, y):
                part = (name,)
        if contains((374, 294, 230, 48), x, y):
            part = ("channel", "ALPHA", 3)
        for i, r in enumerate(COLOR["tabs"]):
            if contains(r, x, y):
                part = ("mode", i)
        if part[0] == "channel":
            index = part[-1]
            value = (
                lambda: binding.read()[index]
                if part[1] != "HSV"
                else color_hsv(binding.read(), widget.linear, widget.hue_value)[index]
            )
    elif isinstance(widget, CurveMapping):
        for i, r in enumerate(CURVE["tabs"]):
            if contains(r, x, y):
                part = ("channel", i)
                selected_binding = widget.channel
        points = deepcopy(binding.read())
        channel = widget.channel.read() if widget.channel else 0
        a, b, w, h = widget.graph
        for i, (px, py) in enumerate(points):
            if (x - (a + px * w)) ** 2 + (y - (b + (1 - py) * h)) ** 2 <= 12**2:
                part = ("point", channel, i)
        for i, r in enumerate(CURVE["fields"]):
            if contains(r, x, y):
                part = ("point_field", channel, widget.selected, i)
        if part[0] in {"point", "point_field"}:
            valid = (
                lambda: binding.valid()
                and binding.read() == points
                and (widget.channel.read() if widget.channel else 0) == channel
            )
            index = part[2]
            value = (
                lambda: binding.read()[index]
                if part[0] == "point" or part[-1] == 2
                else binding.read()[index][part[-1]]
            )
        elif contains(widget.graph, x, y) and part == ("body",):
            part = ("graph", channel)
    elif isinstance(widget, ColorRamp):
        points = deepcopy(binding.read())
        if contains(RAMP["handles"], x, y):
            a, b, w, h = RAMP["gradient"]
            hits = [
                i for i, (pos, _) in enumerate(points) if abs(x - (a + pos * w)) <= 14
            ]
            if hits:
                part = ("stop", hits[-1])
        for name in ("mode", "add", "remove", "position", "color", "gradient"):
            if contains(RAMP[name], x, y):
                part = (
                    (name, widget.selected)
                    if name in {"position", "color", "remove"}
                    else (name,)
                )
        if part[0] == "mode":
            selected_binding = widget.interpolation
        if part[0] in {"stop", "position", "color", "remove"}:
            valid = lambda: binding.valid() and binding.read() == points
            index = part[1]
            value = lambda: binding.read()[index]
    elif isinstance(widget, DataPicker):
        selected_binding = getattr(widget, "binding", None)
        if contains(PICKER["list"], x, y):
            for i, top, h in widget.rows.visible(206):
                if contains((25, 147 + top, 560, 65), x, y):
                    identity, label, icon = widget.filtered[i]
                    part = ("row", identity)
                    selected_binding = (
                        None  # The hovered row is not the selected RNA pointer.
                    )
                    valid = lambda: widget.valid(identity)
                    value = lambda: label
                    break
        for name in ("search", "scroll"):
            if contains(PICKER[name], x, y):
                part = (name,)
        for i, r in enumerate(PICKER["actions"]):
            if contains(r, x, y):
                part = ("action", i)
    elif isinstance(widget, Palette):
        source = widget.source
        valid = source.valid
        first = next(iter(widget.visible()), 0)
        index = None
        for i in widget.visible():
            if contains(widget.cell(i - first), x, y):
                index = i
        if contains(widget.swatch_rect, x, y):
            index = source.active()
        if index is not None and 0 <= index < source.count():
            part = ("swatch", index)
            identity = (
                source.identity(index)
                if source.identity
                else (source.count(), tuple(source.color(index)))
            )

            def valid():
                return (
                    source.valid()
                    and index < source.count()
                    and (
                        source.identity(index)
                        if source.identity
                        else (source.count(), tuple(source.color(index)))
                    )
                    == identity
                )

            value = lambda: tuple(source.color(index))
        for name, r in (("add", widget.add_rect), ("remove", widget.remove_rect)):
            if contains(r, x, y):
                part = (name,)
    elif isinstance(widget, MatrixView):
        for row in range(3):
            for col in range(3):
                if contains((24 + col * 199, 119 + row * 117, 189, 52), x, y):
                    part = ("component", row, col)
                    value = lambda: binding.read()[part[1]][part[2]]
    elif isinstance(widget, Progress):
        part = ("progress", widget.type)
        value = widget.value
    result = Target(key, part, selected_binding, valid, value, widget)
    resolver = (
        getattr(widget, "context_target", None)
        or getattr(getattr(widget, "source", None), "context_target", None)
        or getattr(selected_binding, "context_target", None)
    )
    if resolver:
        result = resolver(result)
    elif (
        selected_binding
        and getattr(selected_binding, "context", None)
        and isinstance(widget, ColorPicker)
        and part[0] == "channel"
        and part[1] != "HSV"
    ):
        # Direct RNA components only; HSV is derived display data, never an RGB index.
        source = selected_binding.context.component(part[-1])
        result = replace(result, binding=replace(selected_binding, context=source))
    elif isinstance(widget, ColorPicker) and part[0] == "channel" and part[1] == "HSV":
        result = replace(result, binding=None)
    return result
