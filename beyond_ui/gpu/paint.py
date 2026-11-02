"""Canvas painter. Own touched GPU state; share retained style batches."""

from contextlib import contextmanager, nullcontext
from functools import lru_cache
from . import style, glass, typography, skin
from ..editing import display_number
from ..menu_metrics import Metrics as menu_metrics


@contextmanager
def gpu_state():
    import gpu

    state = (
        gpu.state.blend_get(),
        gpu.state.depth_test_get(),
        gpu.state.depth_mask_get(),
        gpu.state.viewport_get(),
        gpu.state.scissor_get(),
    )
    try:
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("NONE")
        gpu.state.depth_mask_set(False)
        yield
    finally:
        gpu.state.blend_set(state[0])
        gpu.state.depth_test_set(state[1])
        gpu.state.depth_mask_set(state[2])
        gpu.state.viewport_set(*state[3])
        gpu.state.scissor_set(*state[4])


@lru_cache(maxsize=2048)
def measure(font, size, text):
    import blf

    blf.size(font, size)
    return blf.dimensions(font, text)


def paint(
    canvas,
    rect,
    clip,
    *,
    preferences=None,
    font=0,
    backdrop=None,
    palette=None,
    background=True,
    controls=True,
    overlays=True,
):
    """rect/clip use bottom-left region pixels; logical layout is top-down.

    Use a privately loaded font: BLF has no getters for all font state, so font
    zero is suitable only when the host explicitly owns that state for this draw.
    The host must intersect any enclosing nonrectangular/scroll clip itself.
    """
    import blf

    x, y, w, h = rect
    cx, cy, cw, ch = clip
    if not canvas.visible or w <= 0 or h <= 0 or cw <= 0 or ch <= 0:
        return 0
    sx = w / max(1.0, canvas._width)
    sy = h / max(1.0, canvas.height)
    scale = min(sx, sy)
    logical = ((cx - x) / sx, (y + h - cy - ch) / sy, cw / sx, ch / sy)
    if palette is None:
        palette = style.theme_palette(
            preferences, reference=canvas.theme.palette == "REFERENCE"
        )
    t = canvas.theme
    if t.stylesheet is not None:
        palette = t.stylesheet.palette(palette)

    def mapped(r):
        a, b, c, d = r
        return x + a * sx, y + h - (b + d) * sy, c * sx, d * sy

    current_style = {}

    def text(
        value,
        r,
        ink,
        role="body",
        *,
        center=False,
        right_align=False,
        editor=None,
        inset=6,
        icon=None,
        icon_value=0,
        trailing_icon=None,
    ):
        face_role = role
        if current_style.get("font_weight") == "bold":
            face_role = "title"
        elif current_style.get("font_weight") == "normal":
            face_role = "body"
        alignment = current_style.get("text_align")
        if alignment and editor is None:
            center, right_align = alignment == "CENTER", alignment == "RIGHT"
        active_font = typography.face(font, face_role)
        a, b, c, d = r
        size = (
            current_style.get("font_size", t.font_size)
            * scale
            * (12 / 11 if role == "title" else 9 / 11 if role == "secondary" else 1)
        )
        blf.size(active_font, size)
        icon_only = not value and (
            icon not in {None, "", "NONE", 0} or bool(icon_value)
        )
        left = max(a + (0 if icon_only and center else inset) * scale, cx)
        bottom = max(b, cy)
        right = min(a + c - (0 if icon_only and center else 4) * scale, cx + cw)
        top = min(b + d, cy + ch)
        if right <= left or top <= bottom:
            return
        has_icon = icon not in {None, "", "NONE", 0} or bool(icon_value)
        icon_size = (
            t.icon_size
            if t.stylesheet
            else (14 if getattr(canvas, "panel_layout", False) else 12)
        )
        icon_size = current_style.get("icon_size", icon_size)
        has_icon = has_icon and right - left >= (icon_size + (0 if icon_only else 4)) * scale
        gutter = (icon_size + 6 if value else icon_size) * scale if has_icon else 0
        tail = trailing_icon not in {None, "", "NONE", 0}
        tail_gutter = (icon_size + 6) * scale if tail else 0
        group_left = (
            max(
                left,
                a
                + (c - measure(active_font, size, str(value))[0] - gutter - tail_gutter)
                / 2,
            )
            if center
            else (
                max(
                    left,
                    right
                    - measure(active_font, size, str(value))[0]
                    - gutter
                    - tail_gutter,
                )
                if right_align
                else left
            )
        )
        if has_icon:
            icon_rect = (
                group_left,
                b + (d - icon_size * scale) / 2,
                icon_size * scale,
                icon_size * scale,
            )
            handled = (
                canvas.icon_renderer(icon, icon_value, icon_rect, ink)
                if canvas.icon_renderer
                else False
            )
            if not handled:
                style.icon(
                    icon,
                    group_left + icon_size / 2 * scale,
                    b + d / 2,
                    icon_size * scale,
                    ink,
                )
            left = group_left + gutter
        origin = group_left + gutter
        if tail:
            tail_x = min(
                right - icon_size * scale,
                origin + measure(active_font, size, str(value))[0] + 6 * scale,
            )
            if tail_x >= origin:
                icon_rect = (
                    tail_x,
                    b + (d - icon_size * scale) / 2,
                    icon_size * scale,
                    icon_size * scale,
                )
                handled = (
                    canvas.icon_renderer(trailing_icon, 0, icon_rect, ink)
                    if canvas.icon_renderer
                    else False
                )
                if not handled:
                    style.icon(
                        trailing_icon,
                        tail_x + icon_size * scale / 2,
                        b + d / 2,
                        icon_size * scale,
                        ink,
                    )
                # Leave room for hinted glyph ink beyond its advance width.
                # Clipping exactly at the measured advance can drop the final
                # glyph at small host scales even with ample button space.
                right = min(right, tail_x - 2 * scale)
        if editor is not None:
            cursor = measure(active_font, size, value[: editor.cursor])[0]
            origin = left - max(0, cursor - max(0, right - left - 2 * scale))
            start, end = sorted((editor.anchor, editor.cursor))
            start = max(left, origin + measure(active_font, size, value[:start])[0])
            end = min(right, origin + measure(active_font, size, value[:end])[0])
            if end > start:
                style.draw(
                    start,
                    bottom + 2 * scale,
                    end - start,
                    top - bottom - 4 * scale,
                    palette["selected"],
                    radius=0,
                )
            caret = max(left, min(right - scale, origin + cursor))
            style.draw(
                caret,
                bottom + 4 * scale,
                scale,
                max(0, top - bottom - 8 * scale),
                ink,
                radius=0,
            )
        blf.enable(active_font, blf.CLIPPING)
        try:
            blf.clipping(active_font, left, bottom, right, top)
            blf.color(active_font, *ink)
            blf.position(
                active_font,
                origin,
                b + (d - measure(active_font, size, "H")[1]) / 2,
                0,
            )
            typography.draw_text(active_font, value, ink, palette.get("text_effects"), scale)
        finally:
            blf.disable(active_font, blf.CLIPPING)

    def surface(r, ink, radius=None, flat=False):
        radius = current_style.get("radius", t.radius if radius is None else radius)
        if backdrop is None or not glass.lens(backdrop, r, radius * scale, ink):
            skin.draw(
                r,
                ink,
                ink if flat else style.shade(ink, 0.025),
                radius=radius * scale,
                border=0.6 * scale,
            )
        if flat:
            skin.inset_outline(r, palette, scale, radius)

    def editing_text(control, value, r, ink):
        """Keep the label outside the editable value's selection and caret."""
        a, b, c, d = r
        label_width = (
            min(
                max(0, c - 40 * scale),
                measure(
                    typography.face(font, "body"),
                    t.font_size * scale,
                    control.label + "  ",
                )[0],
            )
            if control.label
            else 0
        )
        if label_width:
            text(control.label, (a, b, label_width + 6 * scale, d), ink)
        text(value, (a + label_width, b, c - label_width, d), ink, editor=canvas.editor)

    feedback_now = canvas.value_feedback.clock()
    count = 0
    animation_colors = None
    status_colors = None
    base_palette = palette
    numeric_states = (
        {}
    )  # Resolve shared scene/view settings once per visible host paint.
    with gpu_state(), typography.submitted_text(font):
        # Geometry is clipped via scissor rectangle as well as logical culling.
        # The caller establishes scissor enable; no unsupported getter is used.
        import gpu

        gpu.state.scissor_set(int(cx), int(cy), max(0, int(cw)), max(0, int(ch)))
        if background:
            style.draw(*rect, palette["bg"], radius=t.radius * scale)
        if controls:
            for card in getattr(canvas, "_style_cards", ()):
                if card[1] + card[3] > logical[1] and card[1] < logical[1] + logical[3]:
                    surface(mapped(card), palette["card"])
                    skin.inset_outline(mapped(card), palette, scale, t.radius)
            for bounds, options in getattr(canvas, "_style_surfaces", ()):
                if bounds[1] + bounds[3] <= logical[1] or bounds[1] >= logical[1] + logical[3]:
                    continue
                radius = options.get("surface_radius", t.radius)
                tint = options.get("surface_color", palette[options["surface"]])
                opacity = options.get("_style_defaults", {}).get("opacity", 1)
                surface(mapped(bounds), tint[:3] + (tint[3] * opacity,), radius)
                skin.inset_outline(mapped(bounds), palette, scale, radius)
        for control in canvas.visible_controls(logical) if controls else ():
            current_style = control.options.get("_inline_style", {})
            r = mapped(control.rect)
            if control.options.get("search_bar"):
                a, b, c, d = r
                inset = menu_metrics.SEARCH_INSET * scale
                r = (a + inset, b, max(0, c - 2 * inset), d)
            a, b, c, d = r
            palette = (
                t.stylesheet.control_palette(base_palette, control)
                if t.stylesheet is not None
                else base_palette
            )
            inline_sheet = control.options.get("_inline_sheet")
            if inline_sheet is not None:
                palette = inline_sheet.palette(palette)
            kind = control.kind
            slider = kind == "number" and control.options.get("slider", True)
            external_label = (
                bool(control.label)
                and not control.options.get("search_bar")
                and (
                    kind in {"text", "event", "pointer", "search", "enum"}
                    or kind == "number"
                    and not slider
                )
            )
            row_rect = r
            label_rect = None
            if external_label:
                from ..scalar_geometry import entry_parts

                label_logical, field_logical = entry_parts(
                    control.rect,
                    label_width=control.options.get("_entry_label_width"),
                    stacked=control.options.get("_entry_stacked", False),
                    label_band=control.options.get("_label_band", 20),
                )
                label_rect, r = mapped(label_logical), mapped(field_logical)
                a, b, c, d = r
            prefix = "" if external_label else control.label
            # No binding reads for fully clipped controls or hidden canvases.
            try:
                value = control.binding.read() if control.binding else None
            except (ReferenceError, RuntimeError):
                value = None
            if control.binding is not None or control.options.get("value_feedback"):
                canvas.value_feedback.observe(control, value if control.binding is not None else control.label, feedback_now)
            enabled = control.enabled
            alert = enabled and control.options.get("alert", False)
            status = control.options.get("status", "EMPTY")
            colored = enabled and status not in {"EMPTY", "UNAVAILABLE"}
            emboss = control.options.get("emboss", "NORMAL")
            chrome = emboss != "NONE" and (
                emboss != "NONE_OR_STATUS" or alert or colored
            )
            if alert or colored:
                if status_colors is None:
                    status_colors = style.menu_status_palette(
                        preferences, reference=t.palette == "REFERENCE"
                    )
                tint = (
                    status_colors["ALERT"]
                    if alert
                    else status_colors.get(status, base_palette["muted"])
                )
                palette = dict(base_palette, field=(*tint[:3], 0.3))
            role = "text" if "color" in current_style else current_style.get("color_role", "text")
            ink = palette[role] if enabled else palette["muted"]
            selected = control.options.get("selected", False)
            selected = selected() if callable(selected) else selected
            menu_option = control.options.get("menu_option", False)
            if menu_option and not selected and canvas.hover != control.key:
                chrome = False
            if (
                control.options.get("list_row")
                and kind not in {"number", "text", "event", "search"}
                and not control.options.get("list_action")
                and canvas.hover != control.key
                and canvas.active is not control
            ):
                chrome = False
            if selected and enabled:
                ink = palette["selected_text"]
            stable_ink = ink
            feedback = canvas.value_feedback.amount(control, feedback_now)
            if feedback:
                tint = palette[canvas.value_feedback.options(control)["role"]]
                ink = tuple(a + (b-a)*feedback for a,b in zip(ink,tint))
            if kind != "widget":
                control.motion.begin_paint()
                if enabled and kind in {
                    "button",
                    "number",
                    "event",
                    "pointer",
                    "search",
                    "decorator",
                    "text",
                    "enum",
                    "color",
                    "toggle",
                }:
                    control.motion.region(
                        "body", control.rect, circular=(abs(c - d) < 8)
                    )
                    if slider:
                        from ..scalar_geometry import slider_parts

                        _, (tx, ty, tw), field = slider_parts(
                            control.rect,
                            bool(control.label),
                            stacked=control.options.get("_slider_stacked"),
                            label_width=control.options.get("_slider_label_width"),
                            label_band=control.options.get("_label_band", 24),
                            value_width=control.options.get("value_width", 53),
                        )
                        control.motion.region(
                            "handle", (tx - 7, ty - 12, tw + 14, 24), circular=True
                        )
                        control.motion.region("field", field)
            with (
                typography.motion_text(font, control.motion),
                control.motion.deform("reveal", row_rect),
                (
                    nullcontext()
                    if (kind == "toggle" and not control.options.get("bool_button"))
                    or slider
                    else control.motion.deform("body", row_rect)
                ),
                typography.submitted_text(font),
            ):
                if external_label:
                    text(
                        control.label,
                        label_rect,
                        palette["text"] if enabled else palette["muted"],
                        "title" if control.options.get("_entry_stacked") else "body",
                        inset=0 if getattr(canvas, "panel_layout", False) else 6,
                        icon=control.options.get("icon"),
                        icon_value=control.options.get("icon_value", 0),
                        trailing_icon=control.options.get("trailing_icon"),
                    )
                if (
                    kind
                    in {
                        "button",
                        "number",
                        "event",
                        "pointer",
                        "search",
                        "decorator",
                        "text",
                        "enum",
                        "color",
                    }
                    and not slider
                    and chrome
                    and not control.options.get("search_bar")
                ):
                    inset = kind in {"text", "number", "event", "search"}
                    surface(
                        menu_metrics.highlight(r, scale) if menu_option else r,
                        (
                            palette["selected"]
                            if selected
                            else (
                                palette["hover"]
                                if canvas.hover == control.key
                                else (
                                    palette["input"]
                                    if inset and not (alert or colored)
                                    else palette["field"]
                                )
                            )
                        ),
                        flat=inset,
                    )
                    if kind == "button" and not menu_option:
                        skin.inset_outline(r, palette, scale, t.radius)
                    if selected or menu_option and canvas.hover == control.key:
                        skin.selection_outline(menu_metrics.highlight(r, scale) if menu_option else r,
                                               palette, scale, current_style.get("radius", t.radius))
                if kind == "widget":
                    typography.flush_text(font)
                    control.options["widget"].paint(r, font, palette, backdrop=backdrop)
                elif kind == "separator":
                    if not control.options.get("space"):
                        thickness = current_style.get("divider_width", 1) * scale
                        tint = ink if "color" in current_style or "color_role" in current_style else palette["muted"]
                        if control.options.get("vertical"):
                            style.draw(a + (c-thickness)/2, b, thickness, d, tint, radius=0)
                        else:
                            style.draw(a, b + (d-thickness)/2, c, thickness, tint, radius=0)
                elif kind == "toggle" and control.options.get("bool_button"):
                    if control.options.get("section_disclosure"):
                        surface(
                            mapped(control.options.get("_section_rect", control.rect)),
                            (
                                palette["hover"]
                                if canvas.hover == control.key
                                else palette["bar"]
                            ),
                        )
                    elif value or canvas.hover == control.key:
                        surface(r, palette["selected"] if value else palette["hover"])
                    alignment = control.options.get("text_alignment", "EXPAND")
                    text(
                        control.label,
                        r,
                        ink,
                        role=control.options.get("text_role", "body"),
                        center=alignment in {"EXPAND", "CENTER"},
                        right_align=alignment == "RIGHT",
                        icon=control.options.get("icon"),
                        icon_value=control.options.get("icon_value", 0),
                        trailing_icon=control.options.get("trailing_icon"),
                    )
                elif kind == "toggle":
                    from ..scalar_geometry import switch_rect

                    switch = mapped(switch_rect(control.rect))
                    text(
                        control.label,
                        (a, b, max(0.0, c - 52 * scale), d),
                        ink,
                        inset=0 if getattr(canvas, "panel_layout", False) else 6,
                        icon=control.options.get("icon"),
                        icon_value=control.options.get("icon_value", 0),
                    )
                    style.switch(
                        *switch,
                        control.motion.position("body", bool(value)),
                        shape=control.motion.sample("body")[0],
                        scale=scale,
                        palette=(
                            palette
                            if enabled
                            else dict(
                                palette,
                                text=palette["muted"],
                                toggle_on=palette["toggle_off"],
                            )
                        ),
                        backdrop=backdrop,
                    )
                elif kind in {"pointer", "search"}:
                    model = control.options[
                        "search_field" if kind == "search" else "pointer_field"
                    ]
                    label = model.label()
                    clear = kind == "search" and model.can_clear()
                    quiet_pointer = (
                        control.options.get("list_row")
                        and kind == "pointer"
                        and canvas.hover != control.key
                        and canvas.active is not control
                    )
                    text(
                        label if external_label or not prefix else f"{prefix}  {label}",
                        (a, b, max(0, c - (44 if clear else 0 if quiet_pointer else 22) * scale), d),
                        ink,
                        icon=(
                            control.options.get("search_icon", control.options.get("icon"))
                            if kind == "search" else control.options.get("icon") if not external_label else None
                        ),
                        icon_value=(
                            control.options.get("icon_value", 0)
                            if not external_label
                            else 0
                        ),
                    )
                    if not quiet_pointer:
                        style.icon(
                            "search" if kind == "search" else "▾",
                            a + c - (34 if clear else 12) * scale,
                            b + d / 2,
                            (13 if kind == "search" else 10) * scale,
                            ink,
                        )
                    if clear:
                        style.icon("X", a + c - 11 * scale, b + d / 2, 11 * scale, ink)
                elif kind == "decorator":
                    model = control.options["decorator"]
                    if model is not None:
                        state = control.options.get("status", "EMPTY")
                        if animation_colors is None:
                            animation_colors = style.animation_palette(
                                preferences, reference=t.palette == "REFERENCE"
                            )
                        colors = animation_colors
                        color = (
                            colors.get(state, palette["muted"])
                            if enabled
                            else palette["muted"]
                        )
                        glyph = {
                            "EMPTY": "●",
                            "KEYED": "◆",
                            "CHANGED": "◆",
                            "ANIMATED": "◇",
                            "DRIVEN": "◉",
                            "UNAVAILABLE": "○",
                        }[state]
                        style.icon(
                            glyph,
                            a + c / 2,
                            b + d / 2,
                            (4 if state == "EMPTY" else 12) * scale,
                            color,
                        )
                elif kind == "event":
                    label = (
                        control.options["event_field"].format(value)
                        if value is not None
                        else "Unavailable"
                    )
                    text(label if external_label else f"{prefix}  {label}", r, ink)
                elif kind == "number":
                    numeric = control.options.get("numeric")
                    numeric_state = None
                    if numeric is not None:
                        owner = id(numeric.context)
                        if owner not in numeric_states:
                            numeric_states[owner] = numeric.snapshot()
                        numeric_state = numeric_states[owner]
                    lo = control.options.get("min", 0.0)
                    hi = control.options.get("max", 1.0)
                    label = (
                        canvas.editor.text
                        if canvas.active is control and canvas.editor
                        else (
                            (
                                numeric.format(value, numeric_state)
                                if numeric is not None
                                else display_number(value)
                            )
                            if value is not None
                            else "Unavailable"
                        )
                    )
                    if slider:
                        from ..scalar_geometry import slider_parts, usable_range

                        label_rect, (tx, ty, tw), field = slider_parts(
                            control.rect,
                            bool(control.label),
                            stacked=control.options.get("_slider_stacked"),
                            label_width=control.options.get("_slider_label_width"),
                            label_band=control.options.get("_label_band", 24),
                            value_width=control.options.get("value_width", 53),
                        )
                        if control.label:
                            lx, ly, lw, lh = label_rect
                            label_rect = (
                                lx,
                                ly,
                                control.options.get("_label_span", lw),
                                lh,
                            )
                            text(
                                control.label,
                                mapped(label_rect),
                                stable_ink,
                                (
                                    "title"
                                    if control.options.get("_slider_stacked")
                                    else "body"
                                ),
                                inset=(
                                    0 if getattr(canvas, "panel_layout", False) else 6
                                ),
                                icon=control.options.get("icon"),
                                icon_value=control.options.get("icon_value", 0),
                            )
                        px, py, pw, _ = mapped((tx, ty, tw, 0))
                        ratio = (
                            (value - lo) / (hi - lo)
                            if value is not None and usable_range(lo, hi)
                            else 0.0
                        )
                        style.slider(
                            (px, py, pw),
                            ratio,
                            shape=control.motion.sample("handle")[0],
                            scale=scale,
                            palette=palette,
                            enabled=enabled
                            or control.options.get("disabled_accent", False),
                        )
                        field = mapped(field)
                        with control.motion.deform("field", field):
                            surface(field, palette["input"], radius=6, flat=True)
                            text(
                                label,
                                field,
                                ink,
                                center=True,
                                editor=(
                                    canvas.editor if canvas.active is control else None
                                ),
                            )
                    else:
                        if canvas.active is control and canvas.editor:
                            (
                                text(label, r, ink, editor=canvas.editor)
                                if external_label
                                else editing_text(control, label, r, ink)
                            )
                        else:
                            text(
                                label if external_label else f"{prefix}  {label}",
                                r,
                                ink,
                            )
                elif kind == "text" and control.options.get("search_bar"):
                    from .menus import search_field

                    search_field(
                        typography.face(font, "body"),
                        r,
                        scale,
                        palette,
                        backdrop,
                        (
                            canvas.editor.text
                            if canvas.active is control and canvas.editor
                            else value or ""
                        ),
                        canvas.editor if canvas.active is control else None,
                        lambda bounds: (
                            (
                                max(bounds[0], cx),
                                max(bounds[1], cy),
                                min(bounds[2], cx + cw),
                                min(bounds[3], cy + ch),
                            ),
                        ),
                        placeholder=control.options.get("placeholder", "Search…"),
                    )
                elif kind == "text":
                    value = (
                        canvas.editor.text
                        if canvas.active is control and canvas.editor
                        else value
                    )
                    if canvas.active is control and canvas.editor:
                        (
                            text(value or "", r, ink, editor=canvas.editor)
                            if external_label
                            else editing_text(control, value or "", r, ink)
                        )
                    else:
                        text(
                            (
                                str(value or "")
                                if external_label or not prefix
                                else f"{prefix}  {value if value is not None else ''}"
                            ),
                            r,
                            ink,
                        )
                elif kind == "button" and (
                    control.options.get("operator_enum")
                    or control.options.get("menu_model")
                    or control.options.get("panel_model")
                    or control.options.get("hold_menu")
                ):
                    if not control.label:
                        # Icon-only menus have one centered glyph, never an edge arrow.
                        glyph = control.options.get("icon")
                        text(
                            "",
                            r,
                            ink,
                            center=True,
                            icon="▾" if glyph in {None, "", "NONE", 0} else glyph,
                            icon_value=control.options.get("icon_value", 0),
                        )
                    else:
                        text(
                            control.label,
                            (a, b, max(0, c - 20 * scale), d),
                            ink,
                            icon=control.options.get("icon"),
                            icon_value=control.options.get("icon_value", 0),
                        )
                        style.icon("▾", a + c - 12 * scale, b + d / 2, 10 * scale, ink)
                elif kind == "enum":
                    field = control.options.get("enum_field")
                    label = (
                        field.format(value)
                        if field and value is not None
                        else next(
                            (
                                label
                                for key, label in control.options["items"]
                                if key == value
                            ),
                            str(value),
                        )
                    )
                    text(
                        label if external_label else f"{prefix}  {label}",
                        (a, b, max(0, c - 20 * scale), d),
                        ink,
                    )
                    style.icon("▾", a + c - 12 * scale, b + d / 2, 10 * scale, ink)
                elif kind == "color":
                    text(
                        control.label,
                        (a, b, max(0, c - 40 * scale), d),
                        ink,
                        inset=0 if getattr(canvas, "panel_layout", False) else 6,
                        icon=control.options.get("icon"),
                        icon_value=control.options.get("icon_value", 0),
                    )
                    if value is not None:
                        rgb = tuple(value[:3])
                        alpha = value[3] if len(value) > 3 else 1.0
                        style.draw(
                            a + c - 34 * scale,
                            b + 5 * scale,
                            28 * scale,
                            d - 10 * scale,
                            (*rgb, alpha),
                            radius=4 * scale,
                        )
                elif kind == "image":
                    texture = control.options["texture"]
                    texture = texture() if callable(texture) else texture
                    if texture is not None:
                        style.preview(texture, *r, radius=t.radius * scale)
                elif control.options.get("_wrapped_lines"):
                    lines = control.options["_wrapped_lines"]
                    line_height = (
                        current_style.get("line_height", current_style.get("font_size", t.font_size) * 1.55) * scale
                    )
                    has_icon = control.options.get("icon") not in {None, "", "NONE", 0}
                    for i, line in enumerate(lines):
                        gutter = 20 * scale if has_icon and i else 0
                        text(
                            line,
                            (
                                a + gutter,
                                b + d - (i + 1) * line_height,
                                c - gutter,
                                line_height,
                            ),
                            ink,
                            "body",
                            icon=control.options.get("icon") if i == 0 else None,
                        )
                elif control.options.get("_heading_lines"):
                    lines = control.options["_heading_lines"]
                    line_height = max(18, t.font_size * 18 / 11) * scale
                    top = b + d / 2 + len(lines) * line_height / 2
                    for i, line in enumerate(lines):
                        gutter = (
                            control.options.get("_heading_icon_gutter", 0) * scale
                            if i
                            else 0
                        )
                        text(
                            line,
                            (
                                a + gutter,
                                top - (i + 1) * line_height,
                                c - gutter,
                                line_height,
                            ),
                            ink,
                            "title",
                            inset=0,
                            icon=control.options.get("icon") if i == 0 else None,
                            icon_value=(
                                control.options.get("icon_value", 0) if i == 0 else 0
                            ),
                        )
                else:
                    label_get = control.options.get("label_get")
                    text(
                        label_get() if label_get else control.label,
                        (a, b, max(0, c - 22 * scale), d) if menu_option else r,
                        (
                            palette["muted"]
                            if control.options.get("text_role") == "secondary"
                            else ink
                        ),
                        control.options.get("text_role", "body"),
                        center=(kind == "button" and not menu_option)
                        or control.options.get("text_alignment") == "CENTER",
                        right_align=control.options.get("text_alignment") == "RIGHT",
                        icon=control.options.get("icon"),
                        icon_value=control.options.get("icon_value", 0),
                        inset=(
                            menu_metrics.TEXT_INSET
                            if menu_option
                            else control.options.get(
                                "text_inset",
                                (
                                    0
                                    if getattr(canvas, "panel_layout", False)
                                    and kind == "label"
                                    else 6
                                ),
                            )
                        ),
                    )
                    if menu_option and selected:
                        style.icon("✓", a + c - 12 * scale, b + d / 2, 12 * scale, ink)
            count += 1
        palette = base_palette
        current_style = {}
        if not overlays:
            return count
        if controls:
            for control in canvas.visible_controls(logical, composites=True):
                widget = control.options.get("widget")
                if hasattr(widget, "paint_overlays"):
                    widget.paint_overlays(
                        mapped(control.rect),
                        font,
                        palette,
                        backdrop=backdrop,
                        clip=clip,
                    )
        if canvas.overlay or canvas.context_menu is not None:
            typography.flush_text(font)
        if canvas.overlay and "widget" in canvas.overlay:
            r = mapped(canvas.overlay["rect"])
            widget = canvas.overlay["widget"]
            with (
                typography.motion_text(font, widget.motion),
                widget.motion.deform("reveal", r),
            ):
                surface(r, palette["overlay"])
                widget.paint(r, font, palette, backdrop=backdrop)
        elif canvas.overlay:
            motion = canvas.active.motion
            with motion.deform("menu-reveal", mapped(canvas.overlay["rect"])):
                for r, value, label in canvas.overlay["items"]:
                    target = mapped(r)
                    key = ("menu", value)
                    motion.region(key, r)
                    with motion.deform(key, target):
                        surface(target, palette["overlay"])
                        text(label, target, palette["text"])
        if canvas.context_menu is not None and not canvas.context_menu.closed:
            if canvas.overlay:
                typography.flush_text(font)
            from .menus import context_menu

            context_menu(
                canvas.context_menu, mapped, scale, font, palette, backdrop, clip
            )
        tip = getattr(canvas, "_control_tip", None)
        if tip is not None and tip.tooltip:
            from .menus import tooltip
            typography.flush_text(font)
            with typography.motion_text(font, tip.motion):
                tooltip(tip, mapped, scale, font, palette, backdrop, clip)
    return count
