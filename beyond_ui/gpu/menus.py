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


def uncovered(rect, covers):
    """BVT _custom_ui_components: exclude panels above a deferred text run."""
    regions = (rect,)
    for a, b, c, d in covers:
        result = []
        for x0, y0, x1, y1 in regions:
            left, right = max(x0, a), min(x1, c)
            bottom, top = max(y0, b), min(y1, d)
            if left >= right or bottom >= top:
                result.append((x0, y0, x1, y1))
                continue
            result.extend(
                r
                for r in (
                    (x0, y0, x1, bottom),
                    (x0, top, x1, y1),
                    (x0, bottom, left, top),
                    (right, bottom, x1, top),
                )
                if r[0] < r[2] and r[1] < r[3]
            )
        regions = tuple(result)
    return regions


def context_menu(menu, mapped, scale, font, palette, backdrop, clip):
    """Source row painter, shared host backdrop, retained bounded menu motion."""
    from . import style, glass, skin, typography
    from .paint import measure

    font = typography.face(font, "body")
    menu.motion.begin_paint()
    menu.glass_ready = backdrop is not None
    pages = (*menu.parents, menu.page)
    for page_index, page in enumerate(pages):
        active = page is menu.page
        panel = mapped(page.rect)
        covers = []
        if menu.tooltip:
            a, b, w, h = mapped(menu.tooltip[0])
            covers.append((a, b, a + w, b + h))
        for later in pages[page_index + 1 :]:
            a, b, w, h = mapped(later.rect)
            covers.append((a, b, a + w, b + h))
        from contextlib import nullcontext

        with menu.motion.deform("reveal", panel) if active else nullcontext():
            if backdrop is None or not glass.lens(
                backdrop, panel, 10 * scale, (0.0, 0.0, 0.0, 0.0), blur=0.7
            ):
                menu.glass_ready = False
                skin.draw(panel, palette["overlay"], radius=10 * scale, border=scale)
            for index, rect, row in menu.visible_rows(page):
                target = mapped(rect)
                key = ("row", index)
                if active:
                    menu.motion.region(key, rect)
                color = palette["selected"] if index == page.highlight else (0, 0, 0, 0)
                item = dict(
                    text=row.label,
                    enabled=page.available[index],
                    data=page.checked[index] if page.checked else False,
                    menu_icon=row.icon,
                    shortcut=row.shortcut,
                    divider=row.divider,
                    submenu=row.children is not None,
                )

                def text_clip(bounds):
                    a, b, c, d = bounds
                    x, y, w, h = clip
                    return uncovered(
                        (max(a, x), max(b, y), min(c, x + w), min(d, y + h)), covers
                    )

                with menu.motion.deform(key, target) if active else nullcontext():
                    enum_option(
                        item,
                        target,
                        scale,
                        font,
                        palette,
                        style,
                        lambda value, size: measure(font, size, value),
                        glass,
                        backdrop,
                        color,
                        text_clip=text_clip,
                    )

    if menu.tooltip:
        rect, lines = menu.tooltip
        panel = mapped(rect)
        with menu.motion.deform("tooltip", panel):
            if backdrop is None or not glass.lens(
                backdrop, panel, 10 * scale, (0.0, 0.0, 0.0, 0.0), blur=0.7
            ):
                menu.glass_ready = False
                skin.draw(panel, palette["overlay"], radius=10 * scale, border=scale)
            for i, line in enumerate(lines):
                x, y, w, h = mapped(
                    (rect[0] + 3, rect[1] + 6 + i * 16, rect[2] - 6, 16)
                )
                bounds = (
                    max(x, clip[0]),
                    max(y, clip[1]),
                    min(x + w, clip[0] + clip[2]),
                    min(y + h, clip[1] + clip[3]),
                )
                text_run(
                    font,
                    line,
                    11 * scale,
                    palette["text"],
                    (x + 7 * scale, y + (h - measure(font, 11 * scale, "H")[1]) / 2),
                    (bounds,),
                )
