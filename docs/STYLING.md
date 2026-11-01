# Stylesheets and reusable templates

Keep Blender's theme by default. Opt into a named preset when an add-on needs its own identity. Presets change presentation; your RNA bindings, operators, undo, owner menus and shared BVT glass remain the same.

```python
from ._vendor.beyond_ui import integrate, StyleSheet

STUDIO = StyleSheet(
    name="Studio",
    colors={"accent": "#F17C67", "toggle_on": "#39BFA5C2"},
    geometry={"gap": 6, "button_height": 22, "field_height": 24},
    motion={"enabled": True, "strength": 0.7, "speed": 1.0},
    opacity=0.85,
    cards=True,
)
integrate(globals(), stylesheet=STUDIO)
```

Put `integrate` after your existing registration functions. For module loaders that reload their settings module during registration, resolve the current preset through a factory:

```python
from . import ui_theme
integrate(globals(), stylesheet=lambda: ui_theme.STUDIO)
```

Use the same `stylesheet=` with `AddonUI`. For a standalone canvas, call `STUDIO.apply(canvas)` before authoring controls that measure themselves, such as lists.

## Tokens

| Section | Supported values |
| --- | --- |
| `colors` | `accent`, `bg`, `card`, `bar`, `field`, `input`, `text`, `title`, `muted`, `selected_text`, `selected`, `hover`, `overlay`, `tab`, `slider_track`, `slider_fill`, `toggle_off`, `toggle_on`, `menu_glass`, `api`, `edge`, `curve`, `point`, `point_selected` |
| `geometry` | `row_height`, `gap`, `padding`, `radius`, `font_size`, `icon_size`, `field_height`, `button_height`, `icon_button_size`, `list_tool_size`, `label_band`, `list_row_height` |
| `motion` | `enabled`, `strength`, `speed` |
| `opacity` | 0–1 multiplier for chrome alpha; text and user-authored color values stay unchanged |
| `cards` | Draw top-level `layout.box()` groups as glass cards |
| `surfaces` | Optional lower/upper RGBA pairs for named specialized-widget skin roles; see `gpu.skin.ROLES` |
| `variants` | Named semantic color overrides for particular controls |
| `operators` | Operator identifier → variant name |
| `wide_numeric_motion_scale` | Wide number-field amplitude multiplier; default 0.15 |

Colors accept `#RRGGBB`, `#RRGGBBAA`, or display-space RGB/RGBA tuples. Unspecified roles inherit the active Blender theme. Setting an accent derives selection/slider/toggle roles unless explicitly overridden. User data such as picked colors and ramp stops is never recolored.

Geometry is in host logical units. It does not enlarge controls to reference-artboard pixels. Menus retain their shared compact rhythm; specialized controls keep their own normalized geometry. `icon_size` affects ordinary canvas text/icon groups; specialized widget glyphs retain their component metrics. Presets are validated data, not arbitrary CSS.

Animation speed is a 0.25–4 time multiplier. Strength is finite and nonnegative. Zero strength or `enabled=False` removes deformation and stops animation ticks. Global disables still win. No motion setting disables glass. Existing per-control `animation` policies remain available; see [animation configuration](ANIMATION.md).

## Update, inherit and save presets

```python
compact = STUDIO.extend(name="Compact", geometry={"gap": 3, "padding": 6})
STUDIO.update(colors={"accent": "#8CA8FF"}, motion={"strength": 0.4})
STUDIO.update(motion={"enabled": False})

# update merges sections; replace replaces entire sections atomically.
STUDIO.replace(colors={}, surfaces={}, variants={}, operators={})  # Follow Blender
```

Existing registered hosts refresh once on an explicit update. Invalid settings leave the prior preset intact. A popup editing its own appearance stays open. Ordinary menus inherit updated roles; dialog `check()` rebuilds its own fields after geometry changes. Importing a preset performs no registration, timers, GPU allocation or file I/O.

```python
import json
from pathlib import Path

Path("studio.json").write_text(json.dumps(STUDIO.to_dict(), indent=2))
loaded = StyleSheet.from_dict(json.loads(Path("studio.json").read_text()))
```

The consumer owns where and when settings are persisted. The library never writes Blender preferences or a scene behind the user's back. CamKeys' Appearance dialog currently previews session-local changes, commits with OK and restores the whole preset with Cancel; edit its `ui_theme.py` or load a JSON preset for persistent defaults.

## Semantic variants and responsive copy

```python
STUDIO.update(
    variants={"primary": {"field": "#D46252B8", "text": "#FFF8F2"}},
    operators={"my_addon.apply": "primary"},
)
row = layout.row()
row.style_class = "primary"
row.operator("my_addon.apply", text="Apply")

layout.paragraph(text="Help copy wraps at the actual panel width.", icon="INFO")
```

`style_class` inherits through rows/columns and is local to that preset. Operator rules are a convenient alternative when the same action appears in many panels. Registered UILists can declare `beyond_ui_row_height = 48` for two-line rows; ordinary lists inherit the preset's `list_row_height`. Rows remain virtualized and retain exact item ownership after sorting.

Use `row`, `column`, `split`, `grid_flow`, aligned groups and shared tokens like a web grid. Keep labels outside editable values. Avoid fixed spaces in labels, draw-time RNA mutation, per-control blur passes or custom timers for appearance.

## Validation boundary

CamKeys' preset and routed Appearance dialog are exercised on macOS Blender 5.1.2 and 5.2.2. Older library compatibility paths remain intact, but this consumer redesign has not been runtime-qualified on Blender 4.2. Generated artwork and real renders are separate in the [Studio review](design/qa/camkeys-studio-v1/index.html); visual differences are not counted as exact matches.
