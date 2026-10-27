"""Explicit regular/semibold faces shared by all custom panel titles.

Load at host setup, never in paint. Font handles are privately owned and released
with the host. A plain integer remains supported for host-supplied legacy fonts.
"""

from pathlib import Path

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
            from . import skin, style
            from .paint import measure
            from ..widgets import base

            skin.clear()
            style.clear()
            base.clear()
            measure.cache_clear()


def face(font, role="body"):
    return getattr(font, "title", int(font)) if role == "title" else int(font)
