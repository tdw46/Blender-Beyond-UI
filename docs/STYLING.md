> Prefer the [native-safe inline `bui.style()` API](INLINE_STYLES.md) for per-control and container overrides. Class hints below remain compatible.

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
| `geometry` | `row_height`, `gap`, `padding`, `radius`, `font_size`, `icon_size`, `field_height`, `button_height`, `icon_button_size`, `list_tool_size`, `label_band`, `list_row_height`, `heading_height`, `box_padding`, `separator_height` |
| `geometry_variants` | Named panel-level geometry overrides, layered over the preset's base geometry |
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

## Panel templates

Give a dense N-panel or Properties panel a compact template without shrinking unrelated panels:

```python
STUDIO.update(geometry_variants={"compact": {
    "gap": 4, "box_padding": 6, "heading_height": 18,
    "button_height": 20, "field_height": 22, "separator_height": 4,
}})

class MYADDON_PT_tools(bpy.types.Panel):
    beyond_ui_style = "compact"
    # Existing bl_* metadata and draw() stay unchanged.
```

Embedded adopted panels resolve `beyond_ui_style` on their original class. Standalone canvases use `STUDIO.apply(canvas, variant="compact")`. Floating menus keep the shared menu metrics; the class attribute is not a general popup override. Omit the attribute (or use an empty string) for the base template. Base updates flow into every variant; removing a variant restores base values on existing canvases. Unknown explicitly selected names fail visibly instead of silently choosing a template.

`padding` controls the outer inset; `box_padding` independently controls card content (omitted means follow `padding`). `heading_height` is the minimum single-line heading height, while wrapping reserves the actual font and optional icon. `separator_height` controls the space allocated to a separator. These tokens affect retained layout, not per-frame GPU allocation.

## Validation boundary

CamKeys' preset and routed Appearance dialog are exercised on macOS Blender 5.1.2 and 5.2.2. Older library compatibility paths remain intact, but this consumer redesign has not been runtime-qualified on Blender 4.2. Generated artwork and real renders are separate in the [Studio review](design/qa/camkeys-studio-v7/index.html); visual differences are not counted as exact matches.

## Property presentation hints

Normal Python class attributes can supply Beyond UI hints without adding RNA
properties or changing stored data. Native Blender ignores these attributes.
For example, put this on your own PropertyGroup:

```python
class LensSettings(bpy.types.PropertyGroup):
    beyond_ui_props = {
        "apparent": {"precision": 1, "suffix": "mm", "value_width": 78},
    }
    apparent: bpy.props.FloatProperty(default=155.0, min=1, max=500)
```

The field displays `155.0 (mm)`; editing accepts `155.0 (mm)`, `155.0`, or an
arithmetic expression. Focusing a rounded value without changing it preserves
its full original precision. Suffixes are display annotations for unitless RNA;
properties with native unit conversion keep Blender's unit codec. Factor/percentage properties reject custom suffixes and retain their percentage scaling when precision is specified. No conversion
is implied by writing `mm`.

Adopted Panel classes, popover Panel classes, dialog Operator classes and UIList
classes may also declare `beyond_ui_props`. A plain property name applies locally;
`"ShapeKey.value"` additionally matches the RNA owner type. Class-local hints
layer over the PropertyGroup hints. For example:

```python
beyond_ui_props = {
    "ShapeKey.value": {"disabled_accent": True},
    "show_help": {"trailing_icon": "INFO"},
    "bin_size": {"precision": 1, "suffix": "°", "slider": False, "width": 72},
}
```

Supported hints: `precision` (0–6), `suffix`, `value_width` (slider number box),
`width` (whole numeric/text control; compact unlabeled switches use their shared width), `slider`, `trailing_icon` (Boolean action), and
`disabled_accent` (read-only slider fill). Widths are logical units, 24–240.
Unknown or invalid hints fail during authoring. Disabled accent changes only the
fill color; it never enables input. Trailing icons share their button's motion,
theme, clipping and centered text group. Ordinary menu labels are unaffected.

A UIList may declare `beyond_ui_row_gap = 6` (0–16 logical units) and author
unaligned rows to use that spacing. Numeric/text cells keep inset surfaces at
rest; inactive menu options still have no individual surface. Native fallback
layouts ignore Beyond UI hints. Registered `MenuLayout` contribution rows do not
yet consume this class-hint API; use the existing menu presentation contract.
Class-hint changes take effect on the next retained-layout rebuild or add-on
reload; live theme changes remain `StyleSheet.update()` transactions.
