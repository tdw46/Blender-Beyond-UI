"""Explicit regular/bold faces shared by all custom panel titles.

Load at host setup, never in paint. Font handles are privately owned and released
with the host. A plain integer remains supported for host-supplied legacy fonts.
"""

from pathlib import Path
from contextlib import contextmanager

_owners = 0

ASSETS = Path(__file__).resolve().parents[1] / "assets/fonts"


class Fonts(int):
    def __new__(cls):
        global _owners
        import blf

        regular = blf.load(str(ASSETS / "Inter-Regular.woff2"))
        title = blf.load(str(ASSETS / "Inter-Bold.woff2"))
        if min(regular, title) < 0:
            for name in ("Inter-Regular.woff2", "Inter-Bold.woff2"):
                blf.unload(str(ASSETS / name))
            raise RuntimeError("Beyond UI bundled font could not be loaded")
        from . import icons

        try:
            icons.prepare()
        except Exception:
            for name in ("Inter-Regular.woff2", "Inter-Bold.woff2"):
                blf.unload(str(ASSETS / name))
            raise
        obj = super().__new__(cls, regular)
        obj.title = title
        obj.closed = False
        _owners += 1
        return obj

    def close(self):
        global _owners
        if self.closed:
            return
        import blf

        for name in ("Inter-Regular.woff2", "Inter-Bold.woff2"):
            blf.unload(str(ASSETS / name))
        self.closed = True
        _owners -= 1
        if _owners == 0:
            from . import skin, style, progress
            from .paint import measure
            from ..widgets import base

            from . import icons

            icons.clear()
            progress.clear()
            skin.clear()
            style.clear()
            base.clear()
            measure.cache_clear()


def face(font, role="body"):
    return getattr(font, "title", int(font)) if role == "title" else int(font)


def text_measurer(font, font_size, pixel_scale=1.0):
    """Keep the two-argument layout contract, with exact sized glyph metrics.

    Compound controls use at_size instead of rescaling hinted glyph advances
    measured at another size. pixel_scale is the host's logical-to-pixel scale.
    """
    from .paint import measure

    def callback(text, role):
        size = font_size() if callable(font_size) else font_size
        return measure(face(font, role), size * (12 / 11 if role == "title" else 1), text)[0]

    def at_size(text, role, size):
        return measure(face(font, role), size * pixel_scale, text)[0] / pixel_scale

    callback.at_size = at_size
    return callback


@contextmanager
def motion_text(font, motion, *, force=False):
    """Submit owned fonts inside finite transforms; retain batching at rest."""
    import blf

    moving = (bool(motion.tracks) or force) and bool(motion.strength)
    fonts = {face(font), face(font, "title")} if moving else ()
    for handle in fonts:
        blf.rotation(handle, 0.0)
        blf.enable(handle, blf.ROTATION)
        blf.position(handle, 0, 0, 0)
        blf.draw(handle, " ")
    try:
        yield
    finally:
        for handle in fonts:
            blf.disable(handle, blf.ROTATION)


def flush_text(font):
    """Finish underlying owned text before painting an overlay above it."""
    import blf

    import gpu

    blend = gpu.state.blend_get()
    try:
        for handle in (
            face(font),
        ):  # BLF owns one global queue, including title/native text.
            blf.rotation(handle, 0.0)
            blf.enable(handle, blf.ROTATION)
            try:
                blf.position(handle, 0, 0, 0)
                blf.draw(handle, " ")
            finally:
                blf.disable(handle, blf.ROTATION)
    finally:
        gpu.state.blend_set(blend)


@contextmanager
def submitted_text(font):
    """Drain owned BLF queues before the enclosing GPU clip/state is restored."""
    try:
        yield
    finally:
        flush_text(font)


def draw_text(font, value, ink, effects=None, scale=1.0):
    """One foreground glyph pass; optional native shadow-only pass first.

    BLF retains glyph geometry and queues each effect with its own font state.
    Transparent foreground on the first pass avoids double-compositing text.
    This uses privately owned fonts and leaves SHADOW disabled for other draws.
    """
    import blf
    from ..text_effects import DEFAULTS

    cfg = DEFAULTS if not effects else {**DEFAULTS, **effects}
    capable = all(hasattr(blf, name) for name in ('shadow', 'shadow_offset', 'SHADOW'))
    if not capable:
        blf.color(font, *ink)
        blf.draw(font, str(value))
        return
    try:
        if cfg['shadow'] and cfg['shadow_opacity']:
            blf.shadow(font, cfg['shadow_blur'], 0, 0, 0, cfg['shadow_opacity'] * ink[3])
            blf.shadow_offset(font, *(round(v * scale) for v in cfg['shadow_offset']))
            blf.enable(font, blf.SHADOW)
            blf.color(font, ink[0], ink[1], ink[2], 0)
            blf.draw(font, str(value))
        if cfg['outline'] and cfg['outline_opacity']:
            blf.shadow(font, 6, 0, 0, 0, cfg['outline_opacity'] * ink[3])
            blf.shadow_offset(font, 0, 0)
            blf.enable(font, blf.SHADOW)
        else:
            blf.disable(font, blf.SHADOW)
        blf.color(font, *ink)
        blf.draw(font, str(value))
    finally:
        blf.disable(font, blf.SHADOW)
        blf.color(font, *ink)
