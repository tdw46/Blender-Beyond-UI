"""Copy into your addon; call integrate(globals(), stylesheet=STUDIO)."""

from ._vendor.beyond_ui import StyleSheet

# Unspecified roles follow Blender. No scene or preference mutation on import.
STUDIO = StyleSheet(
    name="Studio",
    colors={"accent": "#F17C67", "toggle_on": "#39BFA5C2"},
    geometry={"padding": 8, "gap": 6, "button_height": 22, "field_height": 24},
    motion={"enabled": True, "strength": 0.7, "speed": 1.0},
    cards=True,
)
COMPACT = STUDIO.extend(name="Compact", geometry={"gap": 3, "padding": 6})
QUIET = STUDIO.extend(name="Quiet", motion={"enabled": False})
