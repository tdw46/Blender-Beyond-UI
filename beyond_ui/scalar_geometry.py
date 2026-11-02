"""Source BVT scalar geometry shared by painting and logical input."""

from math import isfinite


def slider_parts(
    rect, label=True, *, stacked=None, label_band=24, value_width=53, label_width=None
):
    from .gpu.style import slider_parts as source_parts

    x, y, w, h = rect
    narrow = label and (w < 260 if stacked is None else stacked)
    label_size = w * 0.43 if label_width is None else label_width
    label_rect = (x, y, w if narrow else label_size, 20 if narrow else h)
    offset = (
        0
        if narrow or not label
        else (w * 0.46 if label_width is None else label_size + 8)
    )
    top = y + (label_band if narrow else max(0, (h - 24) / 2))
    controls = (x + offset, top, max(0, w - offset), min(24, h))
    track, field = source_parts(*controls, value_width=value_width)
    return label_rect, track, field


def switch_rect(rect):
    x, y, w, h = rect
    return (x + max(0, w - 46), y + max(0, (h - 24) / 2), min(46, w), min(24, h))


def usable_range(low, high):
    return isfinite(low) and isfinite(high) and 0 < high - low < 1e6


def entry_parts(rect, label=True, *, label_width=None, stacked=False, label_band=20):
    """Shared left label column and right entry surface, in host logical units.

    The full row remains the owned focus/context target; only the value is
    editable. Tiny widths clip the label while retaining a useful value area.
    """
    x, y, w, h = rect
    if stacked and label:
        return (x, y, w, min(20, label_band)), (
            x,
            y + label_band,
            w,
            max(0, h - label_band),
        )
    label_width = (
        min(w * 0.36 if label_width is None else label_width, max(0.0, w - 48))
        if label
        else 0.0
    )
    gap = min(8.0, max(0.0, w - label_width)) if label_width else 0.0
    return (x, y, label_width, h), (
        x + label_width + gap,
        y,
        max(0.0, w - label_width - gap),
        h,
    )
