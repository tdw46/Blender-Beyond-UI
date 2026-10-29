"""Source BVT scalar geometry shared by painting and logical input."""

from math import isfinite


def slider_parts(rect, label=True):
    from .gpu.style import slider_parts as source_parts

    x, y, w, h = rect
    narrow = label and w < 260
    label_rect = (x, y, w if narrow else w * 0.43, 20 if narrow else h)
    offset = 0 if narrow or not label else w * 0.46
    top = y + (24 if narrow else max(0, (h - 24) / 2))
    controls = (x + offset, top, max(0, w - offset), min(24, h))
    track, field = source_parts(*controls)
    return label_rect, track, field


def switch_rect(rect):
    x, y, w, h = rect
    return (x + max(0, w - 46), y + max(0, (h - 24) / 2), min(46, w), min(24, h))


def usable_range(low, high):
    return isfinite(low) and isfinite(high) and 0 < high - low < 1e6
