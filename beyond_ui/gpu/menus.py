"""Reusable Blender GPU menu painting with host-provided theme and primitives.

No BVT/VRM data, global state, handlers, timers or scene evaluation. The host
owns GPU state and lifetime, clipping, transforms, input and retained backdrop.
"""

from ..menu_metrics import Metrics as menu_metrics


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
    if item.get("heading"):
        from . import typography

        font = typography.face(font, "title")
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
        from . import skin

        highlight = menu_metrics.highlight(rect, scale)
        if not glass.lens(backdrop, highlight, 4 * scale, color, blur=0.4):
            style.draw(*highlight, color, radius=4 * scale)
        skin.selection_outline(highlight, palette, scale, 4,
                               color[3] / max(0.001, palette["selected"][3]))
    ink = (
        (palette["selected_text"] if color[3] > 0 and not item.get("heading") else TEXT)
        if item["enabled"] or item.get("heading")
        else MUTED
    )
    blf.size(font, 11 * scale)
    left = x + menu_metrics.TEXT_INSET * scale
    right = x + w - 8 * scale
    if item.get("menu_icon") not in {None, "", "NONE", 0} and not item.get("heading"):
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
    if item.get("toggle"):
        style.switch(
            right - 46 * scale,
            y + (h - 24 * scale) / 2,
            46 * scale,
            24 * scale,
            float(bool(item["data"])),
            shape=item.get("shape", (1.0, 1.0)),
            scale=scale,
            palette=palette
            if item["enabled"]
            else dict(palette, text=MUTED, toggle_on=palette["toggle_off"]),
            backdrop=backdrop,
        )
        right -= 50 * scale
    elif item["data"]:
        style.icon("●", right - 4 * scale, y + h / 2, 6 * scale, ink)
        right -= 16 * scale
    if item.get("field"):
        right = min(right, x + w * 0.44)
    if item.get("label_split") and item.get("field"):
        left = max(left, right - measure(item["text"], 11 * scale)[0] - 2 * scale)
    text(
        item["text"],
        left,
        right,
        (menu_metrics.TITLE_SIZE if item.get("heading") or item.get("title") else 11)
        * scale,
        ink,
    )


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
    """Keep every label/shortcut in the same transform as its menu geometry."""
    from . import typography

    # Include both retained type faces so headings follow the same menu transform.
    with typography.motion_text(
        font, menu.motion, force=getattr(menu, "presentation_active", False)
    ):
        with menu.presentation(mapped):
            _context_menu(menu, mapped, scale, font, palette, backdrop, clip)


def _context_menu(menu, mapped, scale, font, palette, backdrop, clip):
    """Source row painter, shared host backdrop, retained bounded menu motion."""
    from . import style, glass, skin, typography
    from .paint import measure

    fonts = font
    font = typography.face(fonts, "body")
    menu.motion.begin_paint()
    menu.glass_ready = backdrop is not None
    guide = getattr(menu, "guide", lambda: None)()
    if guide is not None:
        import gpu
        from math import atan2, hypot
        from mathutils import Matrix

        start, end, intensity = guide
        x, y, _, _ = mapped((*start, 0, 0))
        a, b, _, _ = mapped((*end, 0, 0))
        with gpu.matrix.push_pop():
            gpu.matrix.translate((x, y, 0))
            gpu.matrix.multiply_matrix(Matrix.Rotation(atan2(b - y, a - x), 4, "Z"))
            skin.draw(
                (0, -scale * 0.65, hypot(a - x, b - y), 1.3 * scale),
                (*palette["selected"][:3], intensity),
                radius=scale * 0.65,
                border=0,
            )
    pages = (*menu.parents, menu.page)
    status_colors = None
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

        def text_clip(bounds):
            a, b, c, d = bounds
            x, y, w, h = clip
            return uncovered(
                (max(a, x), max(b, y), min(c, x + w), min(d, y + h)), covers
            )

        with menu.motion.deform("reveal", panel) if active else nullcontext():
            for surface in menu.surfaces(page):
                with menu.surface_transform(surface, mapped, scale):
                    tint = menu.surface_tint(page, surface, palette)
                    surface = mapped(surface)
                    if backdrop is None or not glass.lens(
                        backdrop, surface, 10 * scale, tint, blur=0.7
                    ):
                        menu.glass_ready = False
                        skin.draw(
                            surface, palette["overlay"], radius=10 * scale, border=scale
                        )
            search_rect = menu.search_rect(page)
            if search_rect and search_rect[3] > 0:
                search = page.search
                rect = mapped(search_rect)
                if active:
                    menu.motion.region("search", search_rect)
                with menu.motion.deform("search", rect) if active else nullcontext():
                    search_field(
                        font,
                        rect,
                        scale,
                        palette,
                        backdrop,
                        search.text.text,
                        search.text if active and search.focused else None,
                        text_clip,
                        placeholder="Search options…",
                        trailing=22,
                    )
                    x, y, w, h = rect
                    text_run(
                        font,
                        "×" if search.text.text else "",
                        11 * scale,
                        palette["muted"],
                        (
                            x + w - 17 * scale,
                            y + (h - measure(font, 11 * scale, "H")[1]) / 2,
                        ),
                        text_clip((x, y, x + w, y + h)),
                    )
            for index, rect, row in menu.visible_rows(page):
                target = mapped(rect)
                key = ("row", index)
                row_motion = active and menu.row_motion_enabled(page, index)
                if row_motion and not row.heading:
                    menu.motion.region(key, rect)
                color = (
                    (
                        *palette["selected"][:3],
                        palette["selected"][3] * menu.highlight_alpha(page, index),
                    )
                    if index == page.highlight and not row.heading
                    else (0, 0, 0, 0)
                )
                item = dict(
                    text=row.label,
                    enabled=page.available[index],
                    data=page.checked[index] if page.checked else False,
                    menu_icon=row.icon,
                    shortcut=row.shortcut,
                    divider=row.divider,
                    heading=row.heading,
                    submenu=row.children is not None,
                    field=row.field is not None,
                    toggle=row.toggle,
                    shape=menu.motion.sample(key)[0] if row_motion else (1.0, 1.0),
                    label_split=row.label_split,
                )

                item["title"] = row.key == "__back__"
                row_font = typography.face(
                    fonts, "title" if row.heading or item["title"] else "body"
                )
                with (
                    menu.row_transform(page, index, mapped, scale),
                    (
                        menu.motion.deform(key, target)
                        if row_motion and not row.toggle
                        else nullcontext()
                    ),
                ):
                    if row.spacing is not None:
                        factor, kind, horizontal = row.spacing
                        if kind == "LINE" and factor > 0:
                            x, y, w, h = target
                            style.draw(
                                x + w / 2 if horizontal else x,
                                y if horizontal else y + h / 2,
                                0.65 * scale if horizontal else w,
                                h if horizontal else 0.65 * scale,
                                (*palette["text"][:3], 0.20),
                                radius=0,
                            )
                        continue
                    row_palette = palette
                    status = page.statuses[index] if page.statuses else "EMPTY"
                    colored = status not in {"EMPTY", "UNAVAILABLE"}
                    if row.alert or row.decorator is not None or colored:
                        if status_colors is None:
                            status_colors = style.menu_status_palette(
                                getattr(menu.event_context, "preferences", None)
                            )
                        if colored and page.available[index] and row.emboss != "NONE":
                            state_color = status_colors.get(status, palette["muted"])
                            row_palette = dict(palette, field=(*state_color[:3], 0.3))
                        if row.alert and page.available[index]:
                            alert = status_colors["ALERT"]
                            row_palette = dict(palette, field=(*alert[:3], 0.25))
                    if row.decorator is not None:
                        state = page.values[index]
                        glyph = {
                            "EMPTY": "●",
                            "KEYED": "◆",
                            "CHANGED": "◆",
                            "ANIMATED": "◇",
                            "DRIVEN": "◉",
                        }.get(state, "○")
                        x, y, w, h = target
                        if color[3] > 0 and not glass.lens(
                            backdrop, target, 4 * scale, color, blur=0.4
                        ):
                            skin.draw(target, color, radius=4 * scale)
                        style.icon(
                            glyph,
                            x + w / 2,
                            y + h / 2,
                            12 * scale,
                            status_colors.get(state, palette["muted"])
                            if page.available[index]
                            else palette["muted"],
                        )
                        continue
                    if (
                        row.alert
                        and page.available[index]
                        and not color[3]
                        and row.emboss != "NONE"
                    ):
                        color = (*status_colors["ALERT"][:3], 0.18)
                    if row.emboss == "NONE":
                        color = (0, 0, 0, 0)
                    enum_option(
                        item,
                        target,
                        scale,
                        row_font,
                        row_palette,
                        style,
                        lambda value, size: measure(row_font, size, value),
                        glass,
                        backdrop,
                        color,
                        text_clip=text_clip,
                    )
                    if row.field is not None:
                        editor = (
                            menu.editor
                            if active and menu.editor and menu.editor.index == index
                            else None
                        )
                        field_value(
                            font,
                            target,
                            scale,
                            row_palette,
                            backdrop,
                            page.values[index],
                            editor,
                            text_clip,
                            page.available[index],
                            emboss=row.emboss not in {"NONE", "NONE_OR_STATUS"}
                            or (
                                row.emboss == "NONE_OR_STATUS"
                                and (row.alert or colored)
                            ),
                        )

    if menu.tooltip:
        rect, lines = menu.tooltip
        panel = mapped(rect)
        with menu.motion.deform("tooltip", panel):
            if backdrop is None or not glass.lens(
                backdrop,
                panel,
                10 * scale,
                palette.get("menu_glass", (0, 0, 0, 0)),
                blur=0.7,
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


def field_value(
    font,
    rect,
    scale,
    palette,
    backdrop,
    value,
    editor,
    clips,
    enabled,
    *,
    full_width=False,
    emboss=True,
):
    """Prepared field text and shared lens; no binding access or new GPU resources."""
    from . import style, glass
    from .paint import measure

    x, y, w, h = rect
    if not full_width:
        x += w * 0.45
        w *= 0.55
    w -= 4 * scale
    y += 2 * scale
    h -= 4 * scale
    if emboss and not glass.lens(
        backdrop, (x, y, w, h), 4 * scale, palette["field"], blur=0.7
    ):
        style.draw(x, y, w, h, palette["field"], radius=4 * scale)
    size = 11 * scale
    left, right = x + 5 * scale, x + w - 5 * scale
    text = editor.text.text if editor else str(value)
    cursor = measure(font, size, text[: editor.text.cursor])[0] if editor else 0
    origin = left - max(0, cursor - max(0, right - left - 2 * scale))
    if editor:
        a, b = sorted((editor.text.anchor, editor.text.cursor))
        start = max(left, origin + measure(font, size, text[:a])[0])
        end = min(right, origin + measure(font, size, text[:b])[0])
        if end > start:
            style.draw(
                start,
                y + scale,
                end - start,
                h - 2 * scale,
                palette["selected"],
                radius=0,
            )
        caret = min(right, max(left, origin + cursor))
        style.draw(
            caret, y + 2 * scale, scale, h - 4 * scale, palette["text"], radius=0
        )
    ink = palette["text"] if enabled else palette["muted"]
    text_run(
        font,
        text,
        size,
        ink,
        (origin, y + (h - measure(font, size, "H")[1]) / 2),
        clips((left, y, right, y + h)),
    )


def search_field(
    font,
    rect,
    scale,
    palette,
    backdrop,
    value,
    editor,
    clips,
    *,
    placeholder="Search…",
    trailing=0,
):
    """One search surface/icon/text origin for menu and panel search bars."""
    from . import style, glass, skin
    from .paint import measure

    x, y, w, h = rect
    tint = palette["input"]
    if not glass.lens(backdrop, rect, 6 * scale, tint, blur=0.7):
        skin.draw(rect, tint, tint, radius=6 * scale, border=0.6 * scale)
    skin.inset_outline(rect, palette, scale)
    style.icon(
        "search",
        x + 13 * scale,
        y + h / 2,
        menu_metrics.SEARCH_ICON * scale,
        palette["muted"],
    )
    left = x + menu_metrics.SEARCH_TEXT * scale
    right = max(left, x + w - (8 + trailing) * scale)
    size = menu_metrics.SEARCH_FONT_SIZE * scale
    text = value or ("" if editor and editor.text else placeholder)
    cursor = measure(font, size, value[: editor.cursor])[0] if editor else 0
    origin = left - max(0, cursor - max(0, right - left - 2 * scale))
    if editor:
        a, b = sorted((editor.anchor, editor.cursor))
        start = max(left, origin + measure(font, size, value[:a])[0])
        end = min(right, origin + measure(font, size, value[:b])[0])
        if end > start:
            style.draw(
                start,
                y + 3 * scale,
                end - start,
                h - 6 * scale,
                palette["selected"],
                radius=0,
            )
        caret = min(right, max(left, origin + cursor))
        style.draw(
            caret,
            y + 5 * scale,
            scale,
            max(0, h - 10 * scale),
            palette["text"],
            radius=0,
        )
    text_run(
        font,
        text,
        size,
        palette["text"] if value else palette["muted"],
        (origin, y + (h - measure(font, size, "H")[1]) / 2),
        clips((left, y, right, y + h)),
    )
