"""Beyond UI: copy this package inside your extension and import it relatively.

No bpy import, registration, native loading, threads or timers at import time.
"""

from .pointer import PointerItems
from .animation import AnimationSettings, animation_defaults
from .native import Layout as NativeLayout
from .layout import Layout, UnsupportedControl
from .canvas import Canvas, Theme
from .lifecycle import Scope
from .context_menu import Entry as MenuEntry, Target as MenuTarget, Shortcut
from .context_dispatch import ShortcutRegistry

__version__ = "0.1.0"
__all__ = [
    "AnimationSettings",
    "animation_defaults",
    "Canvas",
    "PointerItems",
    "Layout",
    "NativeLayout",
    "Scope",
    "MenuEntry",
    "MenuTarget",
    "Shortcut",
    "ShortcutRegistry",
    "Theme",
    "UnsupportedControl",
]
