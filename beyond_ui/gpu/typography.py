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
