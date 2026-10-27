"""Reusable Blender GPU menu painting with host-provided theme and primitives.

No BVT/VRM data, global state, handlers, timers or scene evaluation. The host
owns GPU state and lifetime, clipping, transforms, input and retained backdrop.
"""


def text_run(font, value, size, ink, position, clips, bold=0.0):
    """Draw in the host's restored viewport, after clipped geometry submission."""
    import blf

    blf.size(font, size)
    blf.color(font, *ink)
    blf.enable(font, blf.CLIPPING)
    for clip in clips:
        blf.clipping(font, *clip)
        blf.position(font, *position, 0)
        blf.draw(font, value)
        if bold:
            blf.position(font, position[0] + bold, position[1], 0)
            blf.draw(font, value)
    blf.disable(font, blf.CLIPPING)


def enum_option(
    item,
    rect,
    scale,
    font,
    palette,
    style,
    measure,
    glass,
    backdrop,
    color,
    text_clip=None,
    enqueue=None,
):
    import blf

    x, y, w, h = rect

    def text(value, left, right, size, ink):
        bounds = (left, y, max(left, right), y + h)
        args = (
            font,
            value,
            size,
            ink,
            (left, y + (h - measure("H", size)[1]) / 2),
            text_clip(bounds) if text_clip else (bounds,),
        )
        if enqueue is not None:
            enqueue(args)
        else:
            text_run(*args)

    TEXT = palette["text"]
    MUTED = palette["muted"]
    if item.get("divider"):
        style.draw(
            x + 4 * scale,
            y + h + 4 * scale,
            w - 8 * scale,
            0.65 * scale,
            (*TEXT[:3], 0.20),
            radius=0,
        )
    if color[3] > 0:
        if not glass.lens(backdrop, (x, y, w, h), 4 * scale, color, blur=0.4):
            style.draw(x, y, w, h, color, radius=4 * scale)
    ink = TEXT if item["enabled"] else MUTED
    blf.size(font, 11 * scale)
    left = x + 8 * scale
    right = x + w - 8 * scale
    if "menu_icon" in item:
        style.icon(item["menu_icon"], x + 11 * scale, y + h / 2, 14 * scale, ink)
        left = x + 27 * scale
    if item.get("submenu"):
        style.icon("›", right - 4 * scale, y + h / 2, 12 * scale, ink)
        right -= 16 * scale
    shortcut = item.get("shortcut", "")
    if shortcut:
        size = 10 * scale
        sw, sh = measure(shortcut, size)
        if right - sw - left >= 32 * scale:
            text(shortcut, right - sw, right, size, MUTED)
            right -= sw + 14 * scale
    if item["data"]:
        style.icon("●", right - 4 * scale, y + h / 2, 6 * scale, ink)
        right -= 16 * scale
    text(item["text"], left, right, 11 * scale, ink)
