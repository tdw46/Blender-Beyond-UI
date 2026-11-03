"""Beyond UI: copy this package inside your extension and import it relatively.

No bpy import, registration, native loading, threads or timers at import time.
"""

from .wizard import wizard, help_button, help_row, badge, choice, segmented
from .media import MediaLibrary, media
from .artwork import Artwork, ArtworkLibrary, header, heading
from .integration import integrate
from .addon import AddonUI
from .stylesheet import StyleSheet
from .style_api import style, prop
from .pointer import PointerItems
from .id_template import IDAction
from .animation import AnimationSettings, animation_defaults
from .native import Layout as NativeLayout
from .layout import Layout, UnsupportedControl
from .canvas import Canvas, Theme
from .lifecycle import Scope
from .context_menu import Entry as MenuEntry, Target as MenuTarget, Shortcut
from .context_dispatch import ShortcutRegistry

__version__ = "0.1.0"
__all__ = [
    "wizard", "help_button", "help_row", "badge", "choice", "segmented",
    "MediaLibrary", "media",
    "Artwork", "ArtworkLibrary", "header", "heading",
    "AddonUI",
    "StyleSheet",
    "style",
    "prop",
    "integrate",
    "AnimationSettings",
    "animation_defaults",
    "Canvas",
    "IDAction",
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
