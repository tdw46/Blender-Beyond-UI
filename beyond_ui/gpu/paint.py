"""Canvas painter. Own touched GPU state; share retained style batches."""

from contextlib import contextmanager, nullcontext
from functools import lru_cache
from . import style, glass, typography, skin
from ..editing import display_number


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


def paint(canvas, rect, clip, *, preferences=None, font=0, backdrop=None):
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
    palette = style.theme_palette(
        preferences, reference=canvas.theme.palette == "REFERENCE"
    )
    t = canvas.theme

    def mapped(r):
        a, b, c, d = r
        return x + a * sx, y + h - (b + d) * sy, c * sx, d * sy

    def text(value, r, ink, role="body", *, center=False, editor=None):
        active_font = typography.face(font, role)
        a, b, c, d = r
        size = t.font_size * scale * (12 / 11 if role == "title" else 1)
        blf.size(active_font, size)
        left = max(a + 6 * scale, cx)
        bottom = max(b, cy)
        right = min(a + c - 4 * scale, cx + cw)
        top = min(b + d, cy + ch)
        if right <= left or top <= bottom:
            return
        origin = (
            max(left, a + (c - measure(active_font, size, str(value))[0]) / 2)
            if center
            else left
        )
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
            blf.draw(active_font, str(value))
        finally:
            blf.disable(active_font, blf.CLIPPING)

    def surface(r, ink, radius=t.radius):
        if backdrop is None or not glass.lens(backdrop, r, radius * scale, ink):
            skin.draw(
                r,
                ink,
                style.shade(ink, 0.025),
                radius=radius * scale,
                border=0.6 * scale,
            )

    count = 0
    animation_colors = None
    numeric_states = {}  # Resolve shared scene/view settings once per visible host paint.
    with gpu_state():
        # Geometry is clipped via scissor rectangle as well as logical culling.
        # The caller establishes scissor enable; no unsupported getter is used.
        import gpu

        gpu.state.scissor_set(int(cx), int(cy), max(0, int(cw)), max(0, int(ch)))
        style.draw(*rect, palette["bg"], radius=t.radius * scale)
        for control in canvas.visible_controls(logical):
            r = mapped(control.rect)
            a, b, c, d = r
            kind = control.kind
            slider = kind == "number" and control.options.get("slider", True)
            # No binding reads for fully clipped controls or hidden canvases.
            try:
                value = control.binding.read() if control.binding else None
            except (ReferenceError, RuntimeError):
                value = None
            enabled = control.enabled
            ink = palette["text"] if enabled else palette["muted"]
            selected = control.options.get("selected", False)
            selected = selected() if callable(selected) else selected
            if selected and enabled:
                ink = palette["selected_text"]
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
                            control.rect, bool(control.label)
                        )
                        control.motion.region(
                            "handle", (tx - 7, ty - 12, tw + 14, 24), circular=True
                        )
                        control.motion.region("field", field)
            with (
                typography.motion_text(font, control.motion),
                control.motion.deform("reveal", r),
                nullcontext()
                if kind == "toggle" or slider
                else control.motion.deform("body", r),
            ):
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
                ):
                    surface(
                        r,
                        palette["selected"]
                        if selected
                        else palette["hover"]
                        if canvas.hover == control.key
                        else palette["field"],
                    )
                if kind == "widget":
                    control.options["widget"].paint(r, font, palette, backdrop=backdrop)
                elif kind == "separator":
                    style.draw(a, b + d / 2, c, scale, palette["muted"], radius=0)
                elif kind == "toggle":
                    from ..scalar_geometry import switch_rect

                    switch = mapped(switch_rect(control.rect))
                    text(control.label, (a, b, max(0.0, c - 52 * scale), d), ink)
                    style.switch(
                        *switch,
                        control.motion.position("body", bool(value)),
                        shape=control.motion.sample("body")[0],
                        scale=scale,
                        palette=palette
                        if enabled
                        else dict(
                            palette,
                            text=palette["muted"],
                            toggle_on=palette["toggle_off"],
                        ),
                        backdrop=backdrop,
                    )
                elif kind in {"pointer", "search"}:
                    label = control.options[
                        "search_field" if kind == "search" else "pointer_field"
                    ].label()
                    text(
                        f"{control.label}  {label}",
                        (a, b, max(0, c - 22 * scale), d),
                        ink,
                    )
                    style.icon(
                        "search" if kind == "search" else "▾",
                        a + c - 12 * scale,
                        b + d / 2,
                        (18 if kind == "search" else 10) * scale,
                        ink,
                    )
                elif kind == "decorator":
                    model = control.options["decorator"]
                    if model is not None:
                        state = model.state()
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
                    text(f"{control.label}  {label}", r, ink)
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
                            control.rect, bool(control.label)
                        )
                        if control.label:
                            text(control.label, mapped(label_rect), ink)
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
                            enabled=enabled,
                        )
                        field = mapped(field)
                        with control.motion.deform("field", field):
                            surface(field, palette["field"], radius=6)
                            text(
                                label,
                                field,
                                ink,
                                center=True,
                                editor=canvas.editor
                                if canvas.active is control
                                else None,
                            )
                    else:
                        text(f"{control.label}  {label}", r, ink)
                elif kind == "text":
                    value = (
                        canvas.editor.text
                        if canvas.active is control and canvas.editor
                        else value
                    )
                    text(
                        f"{control.label}  {value if value is not None else ''}", r, ink
                    )
                elif kind == "button" and (
                    control.options.get("operator_enum")
                    or control.options.get("menu_model")
                ):
                    text(control.label, (a, b, max(0, c - 20 * scale), d), ink)
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
                        f"{control.label}  {label}",
                        (a, b, max(0, c - 20 * scale), d),
                        ink,
                    )
                    style.icon("▾", a + c - 12 * scale, b + d / 2, 10 * scale, ink)
                elif kind == "color":
                    text(control.label, (a, b, max(0, c - 40 * scale), d), ink)
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
                else:
                    label_get = control.options.get("label_get")
                    text(
                        label_get() if label_get else control.label,
                        r,
                        ink,
                        control.options.get("text_role", "body"),
                    )
            count += 1
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
    return count
