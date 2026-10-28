"""Explicit regular/semibold faces shared by all custom panel titles.

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
        title = blf.load(str(ASSETS / "Inter-SemiBold.woff2"))
        if min(regular, title) < 0:
            for name in ("Inter-Regular.woff2", "Inter-SemiBold.woff2"):
                blf.unload(str(ASSETS / name))
            raise RuntimeError("Beyond UI bundled font could not be loaded")
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

        for name in ("Inter-Regular.woff2", "Inter-SemiBold.woff2"):
            blf.unload(str(ASSETS / name))
        self.closed = True
        _owners -= 1
        if _owners == 0:
            from . import skin, style, progress
            from .paint import measure
            from ..widgets import base

            progress.clear()
            skin.clear()
            style.clear()
            base.clear()
            measure.cache_clear()


def face(font, role="body"):
    return getattr(font, "title", int(font)) if role == "title" else int(font)


@contextmanager
def motion_text(font, motion):
    """Submit owned fonts inside finite transforms; retain batching at rest."""
    import blf

    moving = bool(motion.tracks) and bool(motion.strength)
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

    for handle in {face(font), face(font, "title")}:
        blf.rotation(handle, 0.0)
        blf.enable(handle, blf.ROTATION)
        try:
            blf.position(handle, 0, 0, 0)
            blf.draw(handle, " ")
        finally:
            blf.disable(handle, blf.ROTATION)
