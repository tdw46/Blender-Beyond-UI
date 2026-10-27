"""Canvas painter. Own touched GPU state; share retained style batches."""

from contextlib import contextmanager
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
    palette = style.theme_palette(preferences)
    t = canvas.theme

    def mapped(r):
        a, b, c, d = r
        return x + a * sx, y + h - (b + d) * sy, c * sx, d * sy

    def text(value, r, ink, role="body"):
        active_font = typography.face(font, role)
        a, b, c, d = r
        size = t.font_size * scale
        blf.size(active_font, size)
        left = max(a + 6 * scale, cx)
        bottom = max(b, cy)
        right = min(a + c - 4 * scale, cx + cw)
        top = min(b + d, cy + ch)
        if right <= left or top <= bottom:
            return
        blf.enable(active_font, blf.CLIPPING)
        try:
            blf.clipping(active_font, left, bottom, right, top)
            blf.color(active_font, *ink)
            blf.position(
                active_font,
                a + 6 * scale,
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
            ink = palette["text"] if control.enabled else palette["muted"]
            # No binding reads for fully clipped controls or hidden canvases.
            try:
                value = control.binding.read() if control.binding else None
            except (ReferenceError, RuntimeError):
                value = None
            selected = control.options.get("selected", False)
            selected = selected() if callable(selected) else selected
            if kind in {"button", "number", "text", "enum", "color"}:
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
                text(control.label, (a, b, max(0.0, c - 48 * scale), d), ink)
                style.switch(
                    a + c - 48 * scale,
                    b,
                    48 * scale,
                    d,
                    float(bool(value)),
                    scale=scale,
                    palette=palette,
                    backdrop=backdrop,
                )
            elif kind == "number":
                lo = control.options.get("min", 0.0)
                hi = control.options.get("max", 1.0)
                if value is not None:
                    ratio = max(0.0, min(1.0, (value - lo) / max(1e-12, hi - lo)))
                    style.draw(
                        a, b, c * ratio, 3 * scale, palette["slider_fill"], radius=scale
                    )
                label = (
                    canvas.editor.text
                    if canvas.active is control and canvas.editor
                    else (display_number(value) if value is not None else "Unavailable")
                )
                text(f"{control.label}  {label}", r, ink)
            elif kind == "text":
                value = (
                    canvas.editor.text
                    if canvas.active is control and canvas.editor
                    else value
                )
                text(f"{control.label}  {value if value is not None else ''}", r, ink)
            elif kind == "enum":
                label = next(
                    (label for key, label in control.options["items"] if key == value),
                    str(value),
                )
                text(
                    f"{control.label}  {label}", (a, b, max(0, c - 20 * scale), d), ink
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
                text(control.label, r, ink, control.options.get("text_role", "body"))
            count += 1
        if canvas.overlay and "widget" in canvas.overlay:
            r = mapped(canvas.overlay["rect"])
            surface(r, palette["overlay"])
            canvas.overlay["widget"].paint(r, font, palette, backdrop=backdrop)
        elif canvas.overlay:
            for r, value, label in canvas.overlay["items"]:
                target = mapped(r)
                surface(target, palette["overlay"])
                text(label, target, palette["text"])
    return count
