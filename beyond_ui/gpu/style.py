"""Retained display-space canvas primitives. No scene producer or pixel readback."""

import math
from functools import lru_cache

icon_tint = None  # Optional host-supplied semantic color adapter.

_shader = _batch = None
_icon_shader = None
_preview_shader = _preview_batch = None
_icons = {}


def text_outline(font, enabled=True):
    """BLF's native outline, without extra Python glyph draws (4.2+)."""
    import blf

    if not all(hasattr(blf, name) for name in ("shadow", "shadow_offset", "SHADOW")):
        return
    if enabled:
        blf.shadow(font, 6, 0.0, 0.0, 0.0, 0.60)
        blf.shadow_offset(font, 0, 0)
        blf.enable(font, blf.SHADOW)
    else:
        blf.disable(font, blf.SHADOW)


def tab_label_parts(x, width, text_width, scale):
    """Icon center, text origin and clip bounds in one display-space system."""
    left = max(x + 5 * scale, x + (width - text_width - 23 * scale) / 2)
    return left + 7 * scale, left + 23 * scale, left + 20 * scale, x + width


def shade(color, amount, alpha=None):
    return tuple(max(0.0, min(1.0, v + amount)) for v in color[:3]) + (
        color[3] if alpha is None else alpha,
    )


def theme_palette(preferences=None, *, reference=False):
    """Resolve once per host paint. Reference artwork is an explicit fixture."""
    return reference_palette() if reference else native_theme_palette(preferences)


@lru_cache(maxsize=1)
def reference_palette():
    from types import MappingProxyType
    from . import skin

    result = skin.palette()
    native = _theme_palette(((0.025, 0.38, 0.77, 1.0),) * 11)
    names = ("bg", "card", "bar", "accent", "field", "text", "muted", "api", "selected")
    result["tokens"] = MappingProxyType(
        {key: result[name] for key, name in zip(native["tokens"], names)}
    )
    result.update(skin.reference_inks())
    result["surfaces"] = MappingProxyType(skin.ROLES)
    result["source"] = "reference"
    result["fallback_roles"] = ()
    return MappingProxyType(result)


def native_theme_palette(preferences):
    """Read public widget roles at paint time; cache derived colors, not RNA.

    Theme RNA is display-space, unlike scene material colors. No conversion,
    saturation guessing, preference mutation or theme polling timer is needed.
    """
    try:
        ui = preferences.themes[0].user_interface
    except (AttributeError, IndexError, TypeError, ReferenceError):
        ui = None

    missing = []

    def read(widget, field, fallback):
        try:
            value = tuple(getattr(getattr(ui, widget), field))
            if len(value) == 3:
                value += (1.0,)
            if len(value) == 4 and all(math.isfinite(v) for v in value):
                return value
        except (AttributeError, TypeError, ReferenceError, ValueError):
            pass
        missing.append(f"{widget}.{field}")
        return fallback

    accent = read("wcol_radio", "inner_sel", (0.025, 0.38, 0.77, 1.0))
    regular = read("wcol_regular", "inner", (0.070, 0.091, 0.111, 1.0))
    text = read("wcol_regular", "text", (0.91, 0.94, 0.97, 1.0))
    return _theme_palette(
        (
            accent,
            regular,
            text,
            read("wcol_tool", "inner", regular),
            read("wcol_num", "inner", regular),
            read("wcol_tab", "inner_sel", accent),
            read("wcol_numslider", "inner", regular),
            read("wcol_numslider", "item", accent),
            read("wcol_toggle", "inner", regular),
            read("wcol_toggle", "inner_sel", accent),
            read("wcol_radio", "text_sel", text),
        ),
        tuple(missing),
    )


@lru_cache(maxsize=8)
def _theme_palette(signature, missing=()):
    (
        accent,
        regular,
        text,
        button,
        field,
        tab,
        track,
        fill,
        toggle_off,
        toggle_on,
        selected_text,
    ) = signature
    # Theme supplies RGB; our existing glass treatment owns surface opacity.
    alpha = lambda color, a: color[:3] + (a,)
    p = dict(
        accent=alpha(accent, 1.0),
        bg=alpha(regular, 0.48),
        card=alpha(button, 0.55),
        bar=alpha(button, 0.70),
        field=alpha(field, 0.96),
        text=alpha(text, 1.0),
        selected_text=alpha(selected_text, 1.0),
        tab=alpha(tab, 0.68),
        slider_track=alpha(track, 1.0),
        slider_fill=alpha(fill, 1.0),
        toggle_off=alpha(toggle_off, 0.55),
        toggle_on=alpha(toggle_on, 0.76),
    )
    p["muted"] = tuple(a * 0.55 + b * 0.45 for a, b in zip(text[:3], regular[:3])) + (
        1.0,
    )
    p["selected"] = tuple(
        a * 0.48 + b * 0.52 for a, b in zip(accent[:3], button[:3])
    ) + (0.55,)
    p["hover"] = shade(button, 0.07, 0.72)
    p["overlay"] = alpha(regular, 0.62)
    p["api"] = shade(accent, 0.25, 1.0)
    # Retained layout items carry stable semantic tokens. Resolve at paint:
    # theme edits must not invalidate layout, thumbnails, geometry or blur.
    p["tokens"] = {
        (0.070, 0.091, 0.111, 0.48): p["bg"],
        (0.105, 0.135, 0.157, 0.55): p["card"],
        (0.14, 0.175, 0.20, 0.70): p["bar"],
        (0.025, 0.38, 0.77, 1): p["accent"],
        (0.060, 0.081, 0.10, 0.96): p["field"],
        (0.91, 0.94, 0.97, 1): p["text"],
        (0.45, 0.51, 0.57, 1): p["muted"],
        (0.50, 0.74, 0.96, 1): p["api"],
        (0.025, 0.29, 0.55, 0.55): p["selected"],
        (0.035, 0.05, 0.065, 1): alpha(regular, 1.0),
        (0.025, 0.035, 0.047, 1): alpha(regular, 1.0),
    }
    from types import MappingProxyType
    from .skin import themed_roles

    surfaces, inks = themed_roles(p)
    p.update(inks)
    p["surfaces"] = MappingProxyType(surfaces)
    p["tokens"] = MappingProxyType(p["tokens"])
    p["source"] = (
        "fallback" if len(missing) == 11 else "mixed" if missing else "blender"
    )
    p["fallback_roles"] = missing
    return MappingProxyType(p)


def animation_palette(preferences, *, reference=False):
    """Central animation-state colors; missing theme data remains observable."""
    palette = theme_palette(preferences, reference=reference)
    try:
        state = preferences.themes[0].user_interface.wcol_state
    except (AttributeError, IndexError, TypeError, ReferenceError):
        state = None
    colors, missing = [palette["muted"]], []
    for field in ("inner_key", "inner_anim", "inner_driven", "inner_changed"):
        try:
            value = (
                tuple(getattr(state, field)) if not reference else palette["accent"][:3]
            )
            if len(value) < 3 or not all(math.isfinite(c) for c in value):
                raise ValueError("Invalid theme state color")
        except (AttributeError, TypeError, ReferenceError, ValueError):
            missing.append("wcol_state." + field)
            value = palette["accent"][:3]
        colors.append(tuple(value[:3]) + (1.0,))
    return _animation_palette(tuple(colors), tuple(missing), reference)


@lru_cache(maxsize=8)
def _animation_palette(colors, missing=(), reference=False):
    from types import MappingProxyType

    return MappingProxyType(
        {
            **dict(zip(("EMPTY", "KEYED", "ANIMATED", "DRIVEN", "CHANGED"), colors)),
            "fallback_roles": missing,
            "source": "reference" if reference else "mixed" if missing else "blender",
        }
    )


def icon(glyph, x, y, size, color):
    """Centered vector icons, independent of a font's bearings and baseline."""
    global _icon_shader
    supported = {
        "⚙",
        "+",
        "×",
        "↑",
        "↓",
        "‹",
        "›",
        "◆",
        "◇",
        "●",
        "○",
        "✎",
        "◐",
        "◌",
        "☼",
        "◉",
        "✦",
        "▾",
        "▸",
        "👁",
        "◡",
        "★",
        "☆",
        "trash",
        "search",
        "object",
        "collection",
        "image",
        "grid",
        "list",
        "folder",
        "grip",
        "−",
        "eyedropper",
        "camera",
        "visibility_sync",
        "layers",
        "reset",
        "menu",
        "shortcut",
        "globe",
        "palette",
        "wand",
        "unlink",
        "material",
        "vertices",
        "outline",
    }
    glyph = {
        "LOOP_BACK": "reset",
        "MENU_PANEL": "menu",
        "KEYINGSET": "shortcut",
        "URL": "globe",
        "COPYDOWN": "↓",
        "PASTEDOWN": "↓",
        "PRESET_NEW": "+",
        "KEY_HLT": "◇",
        "KEY_DEHLT": "◇",
        "DUPLICATE": "collection",
        "DRIVER": "◌",
        "KEYFRAME": "◇",
        "NONE": "",
    }.get(glyph, glyph)
    if glyph not in supported:
        return False
    if icon_tint is not None:
        color = icon_tint(glyph, color)
    import gpu
    from gpu_extras.batch import batch_for_shader

    if _icon_shader is None:
        _icon_shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    if glyph not in _icons:
        verts = []

        def tri(a, b, c):
            verts.extend((a, b, c))

        def disc(cx, cy, r, segments=12):
            for i in range(segments):
                a = i * math.tau / segments
                b = (i + 1) * math.tau / segments
                tri(
                    (cx, cy),
                    (cx + r * math.cos(a), cy + r * math.sin(a)),
                    (cx + r * math.cos(b), cy + r * math.sin(b)),
                )

        def line(a, b, r=0.075):
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            n = math.hypot(dx, dy)
            nx = -dy / n * r
            ny = dx / n * r
            p = (a[0] + nx, a[1] + ny)
            q = (a[0] - nx, a[1] - ny)
            s = (b[0] + nx, b[1] + ny)
            t = (b[0] - nx, b[1] - ny)
            tri(p, q, s)
            tri(q, t, s)
            disc(*a, r)
            disc(*b, r)

        def ring(outer, inner, segments=48, gear=False):
            for i in range(segments):
                a = i * math.tau / segments
                b = (i + 1) * math.tau / segments
                ra = outer if not gear or i % 6 in (1, 2, 3) else outer * 0.78
                rb = outer if not gear or (i + 1) % 6 in (1, 2, 3) else outer * 0.78
                p = (ra * math.cos(a), ra * math.sin(a))
                q = (rb * math.cos(b), rb * math.sin(b))
                s = (inner * math.cos(a), inner * math.sin(a))
                t = (inner * math.cos(b), inner * math.sin(b))
                tri(p, q, s)
                tri(q, t, s)

        if glyph == "palette":
            points = [
                (0.82 * math.cos(i * math.tau / 36), 0.72 * math.sin(i * math.tau / 36))
                for i in range(32)
            ]
            points.extend(((0.30, -0.12), (0.50, -0.05), (0.82, 0)))
            for a, b in zip(points, points[1:]):
                line(a, b, 0.06)
            for a, b in ((-0.42, 0.28), (0, 0.43), (0.42, 0.25), (-0.46, -0.18)):
                disc(a, b, 0.13)
        elif glyph == "wand":
            line((-0.7, -0.7), (0.35, 0.35), 0.10)
            for a, b in (
                ((0.55, 0.40), (0.55, 0.88)),
                ((0.31, 0.64), (0.79, 0.64)),
                ((-0.35, 0.45), (-0.35, 0.83)),
                ((-0.54, 0.64), (-0.16, 0.64)),
            ):
                line(a, b, 0.045)
        elif glyph == "unlink":
            for sign in (-1, 1):
                points = [
                    (sign * 0.42 + 0.36 * math.cos(a), sign * 0.42 + 0.24 * math.sin(a))
                    for a in [i * math.pi / 18 for i in range(37)]
                ]
                for a, b in zip(points, points[1:]):
                    line(a, b, 0.055)
            line((-0.75, 0.45), (-0.45, 0.75), 0.06)
            line((0.45, -0.75), (0.75, -0.45), 0.06)
        elif glyph == "reset":
            points = [
                (0.7 * math.cos(a), 0.7 * math.sin(a))
                for a in [i * math.pi / 24 for i in range(-36, 13)]
            ]
            for a, b in zip(points, points[1:]):
                line(a, b, 0.06)
            line((0, 0.7), (0.35, 0.95), 0.06)
            line((0, 0.7), (0.38, 0.40), 0.06)
        elif glyph == "globe":
            ring(0.85, 0.75, 40)
            line((-0.8, 0), (0.8, 0), 0.045)
            for sign in (-1, 1):
                points = [
                    (
                        sign * 0.37 * math.sin(i * math.pi / 24),
                        0.80 * math.cos(i * math.pi / 24),
                    )
                    for i in range(25)
                ]
                for a, b in zip(points, points[1:]):
                    line(a, b, 0.045)
        elif glyph == "material":
            ring(0.78, 0.67)
            disc(-0.24, 0.27, 0.22)
        elif glyph == "vertices":
            pts = ((-0.7, -0.55), (0.7, -0.55), (0, 0.65))
            for a, b in zip(pts, pts[1:] + pts[:1]):
                line(a, b, 0.04)
            for a in pts:
                disc(*a, 0.19)
        elif glyph == "outline":
            ring(0.82, 0.68)
            ring(0.49, 0.39)
        elif glyph == "menu":
            points = ((-0.8, -0.7), (0.8, -0.7), (0.8, 0.7), (-0.8, 0.7))
            for i in range(4):
                line(points[i], points[(i + 1) % 4], 0.06)
            line((-0.35, -0.7), (-0.35, 0.7), 0.045)
            for yy in (-0.25, 0.25):
                line((-0.12, yy), (0.56, yy), 0.045)
        elif glyph == "shortcut":
            for cx, cy in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
                points = [
                    (
                        cx + 0.27 * math.cos(i * math.tau / 20),
                        cy + 0.27 * math.sin(i * math.tau / 20),
                    )
                    for i in range(21)
                ]
                for a, b in zip(points, points[1:]):
                    line(a, b, 0.045)
            for x in (-0.24, 0.24):
                line((x, -0.5), (x, 0.5), 0.045)
            for y in (-0.24, 0.24):
                line((-0.5, y), (0.5, y), 0.045)
        elif glyph == "layers":
            points = ((0, 0.8), (0.85, 0.35), (0, -0.1), (-0.85, 0.35))
            for i in range(4):
                line(points[i], points[(i + 1) % 4], 0.055)
            for cy in (-0.05, -0.43):
                line((-0.85, cy), (0, cy - 0.45), 0.055)
                line((0, cy - 0.45), (0.85, cy), 0.055)
        elif glyph == "visibility_sync":
            # Monitor + interlocking links, matching Blender's visibility-sync
            # visual language. Retained vector geometry, not a font glyph.
            for a, b in (
                ((0.38, 0.60), (-0.85, 0.60)),
                ((-0.85, 0.60), (-0.85, -0.36)),
                ((-0.85, -0.36), (0.23, -0.36)),
                ((-0.30, -0.36), (-0.30, -0.72)),
                ((-0.59, -0.72), (0.0, -0.72)),
            ):
                line(a, b, 0.05)
            # Open diagonal capsule links stay legible at small UI sizes.
            for cx, cy, start in ((0.40, -0.04, -0.25), (0.73, 0.29, 0.75)):
                points = []
                for i in range(25):
                    angle = (start + i / 24 * 1.5) * math.pi
                    u = 0.17 * math.cos(angle)
                    v = 0.27 * math.sin(angle)
                    points.append((cx + (u + v) * 0.707, cy + (v - u) * 0.707))
                for a, b in zip(points, points[1:]):
                    line(a, b, 0.05)
            line((0.42, -0.02), (0.71, 0.27), 0.05)
        elif glyph == "camera":
            points = (
                (-0.8, -0.55),
                (0.8, -0.55),
                (0.8, 0.45),
                (0.35, 0.45),
                (0.2, 0.7),
                (-0.2, 0.7),
                (-0.35, 0.45),
                (-0.8, 0.45),
            )
            for i in range(len(points)):
                line(points[i], points[(i + 1) % len(points)], 0.055)
            ring(0.32, 0.23, 24)
        elif glyph == "eyedropper":
            # Blender-style pipette: hollow diagonal tube, pointed sampling
            # tip, cross-guard and a solid rounded rubber bulb. One cached batch.
            for a, b in (
                ((-0.68, -0.48), (0.08, 0.28)),
                ((-0.48, -0.68), (0.28, 0.08)),
                ((-0.68, -0.48), (-0.68, -0.62)),
                ((-0.68, -0.62), (-0.85, -0.80)),
                ((-0.48, -0.68), (-0.62, -0.68)),
                ((-0.62, -0.68), (-0.80, -0.85)),
            ):
                line(a, b, 0.045)
            tri((0.08, 0.28), (0.28, 0.08), (0.75, 0.55))
            tri((0.08, 0.28), (0.75, 0.55), (0.55, 0.75))
            disc(0.55, 0.55, 0.28, 24)
            line((-0.12, 0.48), (0.48, -0.12), 0.065)
        elif glyph == "grip":
            for cx in (-0.25, 0.25):
                for cy in (-0.5, 0, 0.5):
                    disc(cx, cy, 0.145)
        elif glyph == "−":
            line((-0.7, 0), (0.7, 0))
        elif glyph == "grid":
            for cx in (-0.45, 0.45):
                for cy in (-0.45, 0.45):
                    a = (cx - 0.28, cy - 0.28)
                    b = (cx + 0.28, cy - 0.28)
                    c = (cx + 0.28, cy + 0.28)
                    d = (cx - 0.28, cy + 0.28)
                    tri(a, b, c)
                    tri(a, c, d)
        elif glyph == "list":
            for cy in (-0.5, 0, 0.5):
                disc(-0.65, cy, 0.09)
                line((-0.3, cy), (0.7, cy), 0.065)
        elif glyph == "folder":
            points = (
                (-0.8, -0.55),
                (0.8, -0.55),
                (0.8, 0.4),
                (-0.1, 0.4),
                (-0.3, 0.65),
                (-0.8, 0.65),
            )
            for i in range(len(points)):
                line(points[i], points[(i + 1) % len(points)], 0.055)
            line((-0.75, 0.2), (0.75, 0.2), 0.045)
        elif glyph == "trash":
            line((-0.55, 0.4), (0.55, 0.4), 0.06)
            line((-0.24, 0.7), (0.24, 0.7), 0.06)
            for a, b in (
                ((-0.43, 0.35), (-0.35, -0.65)),
                ((-0.35, -0.65), (0.35, -0.65)),
                ((0.35, -0.65), (0.43, 0.35)),
                ((-0.14, 0.14), (-0.14, -0.43)),
                ((0.14, 0.14), (0.14, -0.43)),
            ):
                line(a, b, 0.055)
        elif glyph == "search":
            ring(0.56, 0.44, 32)
            line((0.4, -0.4), (0.85, -0.85), 0.075)
        elif glyph == "object":
            points = (
                (0, 0.8),
                (0.68, 0.4),
                (0.68, -0.4),
                (0, -0.8),
                (-0.68, -0.4),
                (-0.68, 0.4),
            )
            for i in range(6):
                line(points[i], points[(i + 1) % 6], 0.055)
            for point in (points[1], points[3], points[5]):
                line((0, 0), point, 0.055)
        elif glyph == "collection":
            for cy in (0.35, 0, -0.35):
                points = ((-0.75, cy), (0, cy + 0.35), (0.75, cy), (0, cy - 0.35))
                for i in range(4):
                    line(points[i], points[(i + 1) % 4], 0.045)
        elif glyph == "image":
            points = ((-0.72, -0.6), (0.72, -0.6), (0.72, 0.6), (-0.72, 0.6))
            for i in range(4):
                line(points[i], points[(i + 1) % 4], 0.055)
            line((-0.65, -0.4), (-0.15, 0.2), 0.055)
            line((-0.15, 0.2), (0.48, -0.5), 0.055)
            disc(0.38, 0.30, 0.12)
        elif glyph == "⚙":
            ring(0.94, 0.43, gear=True)
        elif glyph in {"👁", "◡"}:
            # Almond outline and centered pupil; a slash marks a hidden layer.
            for sign in (-1, 1):
                points = [
                    (-0.86 + 1.72 * i / 16, sign * 0.48 * math.sin(math.pi * i / 16))
                    for i in range(17)
                ]
                for a, b in zip(points, points[1:]):
                    line(a, b, 0.055)
            if glyph == "👁":
                disc(0, 0, 0.22, 24)
            else:
                line((-0.68, 0.72), (0.68, -0.72), 0.09)
        elif glyph in {"★", "☆"}:
            points = [
                (
                    (0.9 if i % 2 == 0 else 0.40)
                    * math.cos(math.pi / 2 + i * math.pi / 5),
                    (0.9 if i % 2 == 0 else 0.40)
                    * math.sin(math.pi / 2 + i * math.pi / 5),
                )
                for i in range(10)
            ]
            for i in range(10):
                if glyph == "★":
                    tri((0, 0), points[i], points[(i + 1) % 10])
                else:
                    line(points[i], points[(i + 1) % 10], 0.05)
        elif glyph == "+":
            line((-0.7, 0), (0.7, 0))
            line((0, -0.7), (0, 0.7))
        elif glyph == "×":
            line((-0.55, -0.55), (0.55, 0.55))
            line((-0.55, 0.55), (0.55, -0.55))
        elif glyph in {"↑", "↓"}:
            sign = 1 if glyph == "↑" else -1
            line((0, -0.7 * sign), (0, 0.7 * sign))
            line((-0.5, 0.2 * sign), (0, 0.7 * sign))
            line((0.5, 0.2 * sign), (0, 0.7 * sign))
        elif glyph in {"‹", "›", "▾", "▸"}:
            points = (
                ((0.3, -0.5), (-0.3, 0), (0.3, 0.5))
                if glyph == "‹"
                else (
                    ((-0.5, 0.25), (0, -0.3), (0.5, 0.25))
                    if glyph == "▾"
                    else ((-0.3, -0.5), (0.3, 0), (-0.3, 0.5))
                )
            )
            line(points[0], points[1])
            line(points[1], points[2])
        elif glyph in {"◇", "◆"}:
            points = ((0, 0.8), (0.8, 0), (0, -0.8), (-0.8, 0))
            for i in range(4):
                if glyph == "◆":
                    tri((0, 0), points[i], points[(i + 1) % 4])
                else:
                    line(points[i], points[(i + 1) % 4], 0.06)
        elif glyph == "●":
            disc(0, 0, 0.66, 32)
        elif glyph == "○":
            ring(0.72, 0.57)
        elif glyph == "◉":
            ring(0.83, 0.71)
            disc(0, 0, 0.53, 32)
        elif glyph == "◐":
            ring(0.8, 0.68)
            for i in range(16):
                a = math.pi / 2 + i * math.pi / 16
                b = a + math.pi / 16
                tri(
                    (0, 0),
                    (0.72 * math.cos(a), 0.72 * math.sin(a)),
                    (0.72 * math.cos(b), 0.72 * math.sin(b)),
                )
        elif glyph == "◌":
            for i in range(12):
                disc(
                    0.72 * math.cos(i * math.tau / 12),
                    0.72 * math.sin(i * math.tau / 12),
                    0.065,
                )
        elif glyph == "☼":
            ring(0.38, 0.25, 32)
            for i in range(8):
                a = i * math.tau / 8
                line(
                    (0.60 * math.cos(a), 0.60 * math.sin(a)),
                    (0.88 * math.cos(a), 0.88 * math.sin(a)),
                    0.06,
                )
        elif glyph == "✦":
            pts = (
                (0, 0.92),
                (0.26, 0.26),
                (0.92, 0),
                (0.26, -0.26),
                (0, -0.92),
                (-0.26, -0.26),
                (-0.92, 0),
                (-0.26, 0.26),
            )
            for i in range(8):
                tri((0, 0), pts[i], pts[(i + 1) % 8])
        else:
            line((-0.55, -0.50), (0.55, 0.60), 0.18)
            tri((-0.70, -0.70), (-0.66, -0.32), (-0.32, -0.66))
        if glyph == "search":
            # Center the complete silhouette, including its offset handle.
            cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2
            cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2
            verts = [(vx - cx, vy - cy) for vx, vy in verts]
        _icons[glyph] = batch_for_shader(_icon_shader, "TRIS", {"pos": verts})
    gpu.state.blend_set("ALPHA")
    with gpu.matrix.push_pop():
        gpu.matrix.translate((x, y, 0))
        gpu.matrix.scale((size / 2, size / 2, 1))
        _icon_shader.bind()
        _icon_shader.uniform_float("color", color)
        _icons[glyph].draw(_icon_shader)
    return True


def slider_parts(x, y, width, height, scale=1.0):
    """One geometry contract for the visible track, numeric field and input."""
    number_width = min(width * 0.48, 53.0 * scale)
    track_width = max(1.0, width - number_width - 16.0 * scale)
    return (x + 7.0 * scale, y + height / 2.0, track_width), (
        x + width - number_width,
        y,
        number_width,
        height,
    )


def slider(
    track, value, *, shape=(1.0, 1.0), scale=1.0, palette=None, enabled=True, hue=False
):
    """BVT track and bubble; reuse the retained style shader/batch."""
    palette = palette or theme_palette()
    tx, ty, tw = track
    ratio = max(0.0, min(1.0, value))
    if hue:
        from . import skin

        skin.draw(
            (tx, ty - 2.5 * scale, tw, 5 * scale),
            (1, 1, 1, 1),
            radius=3 * scale,
            mode=2,
        )
    else:
        draw(
            tx,
            ty - 2.5 * scale,
            tw,
            5 * scale,
            palette["slider_track"],
            radius=3 * scale,
            border=0.5 * scale,
        )
    fill = tw * ratio
    color = palette["slider_fill"] if enabled else palette["muted"]
    if fill > 0 and not hue:
        draw(
            tx,
            ty - 2.5 * scale,
            fill,
            5 * scale,
            color,
            radius=3 * scale,
            top=shade(color, 0.06),
        )
    ax, ay = shape
    r = 6.5 * scale
    draw(
        tx + fill - r * ax - scale,
        ty - r * ay - 2 * scale,
        2 * r * ax + 2 * scale,
        2 * r * ay + 2 * scale,
        shade(palette["switch_shadow"], 0, 0.65),
        mode=3,
    )
    color = palette["text"] if enabled else palette["muted"]
    draw(
        tx + fill - r * ax,
        ty - r * ay,
        2 * r * ax,
        2 * r * ay,
        shade(color, -0.18),
        top=shade(color, 0.15),
        mode=3,
        border=0.5 * scale,
    )


HANDLE_DURATION = 1.0
OVERLAY_DURATION = 0.7
HOVER_WIPE_DURATION = 0.25
SWITCH_DURATION = 1.4


def release_shape(amount, elapsed, initial=None, toggle=False):
    """Bounded damped spring. No integration drift and a finite idle deadline."""
    duration = SWITCH_DURATION if toggle else HANDLE_DURATION
    if elapsed >= duration:
        return 1.0, 1.0
    elapsed = max(0.0, elapsed)
    damping, frequency = (3.5, 11.0) if toggle else (4.5, 16.0)
    stretch = amount * math.exp(-damping * elapsed) * math.cos(frequency * elapsed)
    # Ease the last, tiny tail to exact rest rather than clipping the spring.
    tail = max(0.0, min(1.0, (duration - elapsed) / 0.20))
    stretch *= tail * tail * (3 - 2 * tail)
    if initial is not None:
        attack = min(1.0, elapsed / 0.035)
        attack = attack * attack * (3 - 2 * attack)
        stretch = initial * (1 - attack) + stretch * attack
    return 1.0 + stretch, 1.0 / (1.0 + stretch)


def overlay_rect(rect, bounds, elapsed):
    """Decorative group spring; logical layout and hit targets stay retained."""
    if elapsed >= OVERLAY_DURATION:
        return rect
    ax, ay = release_shape(0.12, elapsed / OVERLAY_DURATION, initial=-0.06)
    x, y, w, h = rect
    bx, by, bw, bh = bounds
    cx, cy = bx + bw / 2, by + bh / 2
    return cx + (x - cx) * ax, cy + (y - cy) * ay, w * ax, h * ay


def overlay_envelope(rect):
    x, y, w, h = rect
    return x - w * 0.08, y - h * 0.08, w * 1.16, h * 1.16


def switch_position(start, end, elapsed, duration=0.22):
    """Fast eased travel, independent from the area-preserving spring."""
    t = max(0.0, min(1.0, elapsed / duration))
    return start + (end - start) * (1 - (1 - t) ** 3)


def tab_transition(start, end, elapsed, initial_stretch=1.0):
    """Retargetable, area-preserving tab travel with a finite elastic tail."""
    t = max(0.0, min(1.0, elapsed / 0.42))
    if t >= 1.0:
        return end, 1.0, 1.0
    position = switch_position(start, end, elapsed)
    stretch = (
        1.0
        + (initial_stretch - 1.0) * (1 - t) ** 3
        + min(1.0, abs(end - start)) * 0.24 * math.sin(3 * math.pi * t) * (1 - t) ** 2
    )
    return position, stretch, 1.0 / stretch


def velocity_impulse(dx, dy, elapsed, scale=1.0):
    speed = math.hypot(dx, dy) / max(0.5, scale) / max(1 / 240, elapsed)
    return min(0.70, speed / 800), math.atan2(dy, dx)


def hover_impulse(
    width, height, circular, dx, dy, elapsed, scale=1.0, *, section=False
):
    """Round actions are directional; fields/grips bounce more than headers."""
    amount, angle = velocity_impulse(dx, dy, elapsed, scale)
    if circular:
        return max(0.24, amount), angle
    strength = 0.008 + 0.012 * amount / 0.70 if section else 0.10 + 0.04 * amount / 0.70
    return strength, 0.0 if width >= height else math.pi / 2


def switch_bounds(x, y, width, height, scale=1.0):
    """Shrink only the visible switch; keep layout and hit bounds unchanged."""
    return x + width * 0.2, y + height * 0.2, width * 0.6, height * 0.6, scale * 0.6


def picker_marker(
    x, y, radius, fill, shape=(1.0, 1.0), angle=0.0, scale=1.0, *, palette=None
):
    import gpu
    from mathutils import Matrix

    palette = palette or theme_palette()
    ax, ay = shape
    with gpu.matrix.push_pop():
        gpu.matrix.translate((x, y, 0))
        if angle and shape != (1.0, 1.0):
            gpu.matrix.multiply_matrix(Matrix.Rotation(angle, 4, "Z"))
        for r, color in (
            (radius + 2 * scale, palette["marker_outer"]),
            (radius, palette["marker_ring"]),
            (radius - 2.5 * scale, fill),
        ):
            draw(-r * ax, -r * ay, 2 * r * ax, 2 * r * ay, color, mode=3)


def switch(
    x,
    y,
    width,
    height,
    position,
    shape=(1.0, 1.0),
    scale=1.0,
    palette=None,
    backdrop=None,
    hover=None,
):
    """Glass over the panel's shared blurred underlay; no extra blur producer."""
    x, y, width, height, scale = switch_bounds(x, y, width, height, scale)
    position = max(0.0, min(1.0, position))
    palette = palette or theme_palette(None)
    off = palette["toggle_off"]
    on = palette["toggle_on"]
    fill = tuple(a + (b - a) * position for a, b in zip(off, on))
    top = shade(fill, 0.06)
    from . import glass

    if backdrop is None or not glass.lens(
        backdrop, (x, y, width, height), height / 2, fill, **(hover or {})
    ):
        draw(
            x,
            y,
            width,
            height,
            fill,
            top=top,
            radius=height / 2,
            border=0.75 * scale,
            mode=4,
        )
    radius = (height - 5 * scale) / 2
    center = x + height / 2 + (width - height) * position
    cy = y + height / 2
    ax, ay = shape
    rw = radius * ax
    rh = radius * ay
    draw(
        center - rw - scale,
        cy - rh - 1.5 * scale,
        2 * rw + 2 * scale,
        2 * rh + 2 * scale,
        palette["switch_shadow"],
        mode=3,
    )
    draw(
        center - rw,
        cy - rh,
        2 * rw,
        2 * rh,
        shade(palette["text"], -0.18, 0.85),
        top=shade(palette["text"], 0.15, 0.98),
        mode=3,
        border=0.7 * scale,
    )


def ensure():
    global _shader, _batch
    if _shader is not None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    interface = gpu.types.GPUStageInterfaceInfo("bvt_canvas_style_interface")
    interface.smooth("VEC2", "uv")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    # Exactly 128 bytes of push constants, including the explicit matrix.
    info.push_constant("MAT4", "mvp")
    info.push_constant("VEC4", "rect")
    info.push_constant("VEC4", "bottom")
    info.push_constant("VEC4", "top")
    info.push_constant("VEC4", "params")  # radius, border, mode, hue
    info.vertex_source("""
void main() {
    uv = pos;
    gl_Position = mvp * vec4(rect.xy + pos * rect.zw, 0.0, 1.0);
}
""")
    info.fragment_source("""
vec3 hue_rgb(float h) {
    return clamp(abs(fract(vec3(h) + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
}
void main() {
    vec2 size = rect.zw;
    float radius = min(params.x, min(size.x, size.y) * 0.5);
    vec2 q = abs((uv - 0.5) * size) - size * 0.5 + radius;
    float distance = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - radius;
    if (params.z == 3.0) distance = (length((uv - 0.5) * 2.0) - 1.0) * min(size.x, size.y) * 0.5;
    float aa = max(fwidth(distance), 0.7);
    float coverage = 1.0 - smoothstep(-aa, aa, distance);
    vec4 color = mix(bottom, top, uv.y);
    if (params.z == 1.0) color = vec4(mix(vec3(1.0), hue_rgb(params.w), uv.x) * uv.y, 1.0);
    if (params.z == 2.0) color = vec4(hue_rgb(uv.x), 1.0);
    if (params.z == 4.0) {
        // Static frosted wash: no texture allocation, capture or blur pass.
        float glow = exp(-dot((uv-vec2(0.1,0.95))*vec2(1.4,1.0), (uv-vec2(0.1,0.95))*vec2(1.4,1.0))*3.0);
        color.rgb += vec3(0.012,0.038,0.065) * glow;
    }
    if (params.y > 0.0) {
        // Analytic SDF bevel: the same distance already used for coverage.
        // Directional specular rim, without texture samples or another pass.
        vec2 corner = max(q, vec2(0.0));
        vec2 normal = dot(corner,corner)>0.00001 ? normalize(corner) :
                      (q.x>q.y ? vec2(1.0,0.0) : vec2(0.0,1.0));
        normal *= sign(uv-0.5);
        float light = max(0.0,dot(normal,vec2(-0.447214,0.894427)));
        float edge = smoothstep(-params.y-aa, -params.y+aa, distance);
        float rim = edge*(0.07+0.27*light*light);
        color.rgb = mix(color.rgb,vec3(1.0),rim);
        color.a = max(color.a,rim*0.7);
    }
    fragColor = vec4(color.rgb, color.a * coverage);
}
""")
    _shader = gpu.shader.create_from_info(info)
    _batch = batch_for_shader(
        _shader,
        "TRIS",
        {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
        indices=((0, 1, 2), (2, 1, 3)),
    )


def draw(x, y, w, h, color, *, radius=6.0, border=0.0, top=None, mode=0.0, hue=0.0):
    if w <= 0 or h <= 0:
        return
    import gpu

    ensure()
    # Native BLF flushes can reset blending between any two widgets. The UI
    # region and Properties region do not flush at the same points. Own it for
    # every primitive (the canvas restores its incoming state on exit).
    gpu.state.blend_set("ALPHA")
    _shader.bind()
    _shader.uniform_float(
        "mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    )
    _shader.uniform_float("rect", (x, y, w, h))
    _shader.uniform_float("bottom", color)
    _shader.uniform_float("top", color if top is None else top)
    _shader.uniform_float("params", (radius, border, float(mode), hue))
    _batch.draw(_shader)


def clear():
    global _shader, _batch, _icon_shader, _preview_shader, _preview_batch
    _shader = _batch = None
    _icon_shader = None
    _icons.clear()
    _preview_shader = _preview_batch = None


def preview(texture, x, y, w, h, radius=6.0):
    """One retained texture draw with rounded coverage; no mask render target."""
    global _preview_shader, _preview_batch
    import gpu
    from gpu_extras.batch import batch_for_shader

    if _preview_shader is None:
        interface = gpu.types.GPUStageInterfaceInfo("bvt_rounded_preview_uv")
        interface.smooth("VEC2", "uv")
        info = gpu.types.GPUShaderCreateInfo()
        info.vertex_in(0, "VEC2", "pos")
        info.vertex_out(interface)
        info.fragment_out(0, "VEC4", "fragColor")
        info.sampler(0, "FLOAT_2D", "image")
        info.push_constant("MAT4", "mvp")
        info.push_constant("VEC4", "rect")
        info.push_constant("FLOAT", "radius")
        info.vertex_source(
            "void main(){uv=pos;gl_Position=mvp*vec4(rect.xy+pos*rect.zw,0.0,1.0);}"
        )
        info.fragment_source("""
void main(){
    vec4 color=texture(image,uv);
    vec3 rgb=max(color.rgb,vec3(0.0));
    color.rgb=mix(1.055*pow(rgb,vec3(1.0/2.4))-0.055,rgb*12.92,lessThan(rgb,vec3(0.0031308)));
    float r=min(radius,min(rect.z,rect.w)*0.5);
    vec2 q=abs((uv-0.5)*rect.zw)-rect.zw*0.5+r;
    float d=length(max(q,vec2(0.0)))+min(max(q.x,q.y),0.0)-r;
    float aa=max(fwidth(d),0.7);
    fragColor=vec4(color.rgb,color.a*(1.0-smoothstep(-aa,aa,d)));
}""")
        _preview_shader = gpu.shader.create_from_info(info)
        _preview_batch = batch_for_shader(
            _preview_shader,
            "TRIS",
            {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
            indices=((0, 1, 2), (2, 1, 3)),
        )
    _preview_shader.bind()
    _preview_shader.uniform_sampler("image", texture)
    _preview_shader.uniform_float(
        "mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    )
    _preview_shader.uniform_float("rect", (x, y, w, h))
    _preview_shader.uniform_float("radius", radius)
    _preview_batch.draw(_preview_shader)
