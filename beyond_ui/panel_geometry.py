"""Native panel width calibration, independent of GPU and RNA ownership."""
from math import ceil, isfinite


def pixel_scale(region, ui_scale):
    """Include the user's native sidebar zoom, without depending on its pan."""
    try:
        view = region.view2d
        span = view.region_to_view(0, 100)[1] - view.region_to_view(0, 0)[1]
        scale = ui_scale * 100 / span
        if isfinite(scale) and scale > 0:
            return round(scale, 4)
    except (AttributeError, ReferenceError, ZeroDivisionError):
        pass
    return ui_scale


def available_width(region_width, scale, gutter=20):
    return max(1.0, region_width / scale - gutter)


def measured_gutter(region_width, anchor_width, scale):
    # Reserve a half logical pixel outward at native integer rounding edges.
    return ceil(max(0, region_width - anchor_width) / scale * 2) / 2
