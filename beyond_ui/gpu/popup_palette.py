"""Resolve the popup background once per canvas, theme revision and tint amount."""
from types import MappingProxyType


def for_canvas(canvas, base):
    base = base.get("_popup_content_palette", base)
    amount = canvas.theme.popup_tint
    if not amount:
        return base
    cached = getattr(canvas, "_popup_palette_cache", None)
    if cached and cached[0] is base and cached[1] == amount:
        return cached[2]

    accent = base["accent"]
    alpha = amount * accent[3] * base.get("_surface_opacity", 1.0)

    def tint(color):
        # Source-over in display space also works on a fully clear glass lens.
        remaining = color[3] * (1.0 - alpha)
        opacity = alpha + remaining
        if not opacity:
            return color
        return (*((accent[i] * alpha + color[i] * remaining) / opacity for i in range(3)), opacity)

    surfaces = dict(base["surfaces"])
    surfaces["card"] = tuple(tint(c) for c in surfaces["card"])
    result = MappingProxyType(dict(base, menu_glass=tint(base["menu_glass"]),
                                   overlay=tint(base["overlay"]), surfaces=MappingProxyType(surfaces),
                                   _popup_content_palette=base))
    canvas._popup_palette_cache = (base, amount, result)
    return result
