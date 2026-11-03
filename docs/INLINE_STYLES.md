# One extra line after native Blender UI

Import the vendored package, keep the native call, then style the item it just
emitted on that **same layout**:

```python
from ._vendor import beyond_ui as bui

row.prop(camera, "lens", text="Focal Length")
bui.style(row, units="mm", precision=1, value_width=78)
```

`bui.style()` records presentation when Beyond UI owns the layout. On Blender's
native `UILayout`, it does nothing. It never monkey-patches Blender, changes RNA
metadata, converts stored data, or forwards extra keywords to native `prop()`.
Keep importing the vendored package even when its custom rendering is disabled.

The optional one-call form separates native and styling arguments:

```python
bui.prop(row, camera, "lens", text="Focal Length",
         style={"units": "mm", "precision": 1, "value_width": 78})
```

Do **not** add `units=`, `padding=` or other custom arguments directly to native
`layout.prop()`. Blender rejects unknown RNA keywords. `bui.prop()` forwards only
its ordinary keyword arguments to Blender.

## Reuse styles like web design tokens

```python
FIELD = dict(padding=(3, 8), margin=(2, 0), radius=6)
FOCAL = dict(units="mm", precision=1, value_width=78)
HELP = dict(text_align="center", trailing_icon="INFO")

row.prop(camera, "lens")
bui.style(row, FIELD, FOCAL)  # Later dictionaries/keywords win.

col = layout.column()
bui.style(col, scope="group", gap=8, padding=6, color="#E8EEF2")
col.prop(settings, "enabled")
col.prop(settings, "name")
```

Presets are ordinary dictionaries: JSON-compatible, copied during authoring, and
composable. `colors` and `motion` merge by key. There are no executable CSS files,
selectors, global monkey-patches, runtime style polling, or product-name rules.

The default scope is the preceding item, including its array/compound group.
It never reaches backward through unrelated layouts. Calling it on an empty
custom layout is an error. `scope="group"` targets the passed row/column/root and
provides visual defaults to both existing and future descendants. Numeric
formatting belongs to an individual property, not a group-wide default.

## Supported properties

This is a validated CSS-inspired vocabulary, not a browser CSS engine. Unsupported
keys fail explicitly instead of being silently ignored.

| Properties | Meaning |
| --- | --- |
| `padding`, `margin` | Container spacing in logical units. Number or 1–4 values, CSS top/right/bottom/left order, 0–128. Padding is inside the item's **layout container**, around its existing native-size control; margin is outside that content. Neither enlarges fonts or changes owner hit targets. |
| `gap` | Row/column spacing, 0–64. Use `scope="group"` on the row, or style its parent immediately after authoring that row. Both target the row's internal gaps. |
| `width`, `height` | Explicit layout allocation, 1–4096 logical units. |
| `min_width`, `max_width`, `min_height`, `max_height` | Container constraints; available host bounds still win over minimum width. Content fits an explicit height without changing its binding. |
| `align` | Container content alignment: `left`, `center`, `right`, `expand`. |
| `align_items` | Row cross-axis alignment: `start`, `center`, `end`; moves complete child blocks without changing their shapes or owners. |
| `flex_grow` | Relative flexible width in a row, 0.01–100. Explicit fixed widths retain precedence; explicit flex prevents automatic intrinsic label shrinking. |
| `display` | `flex` or `none`. Hidden descendants get zero geometry and cannot be hit; hiding an active owned edit cancels it. Native fallback remains visible. |
| `text_align` | `left`, `center`, `right`, `expand` for ordinary control text. Active text editing retains caret/selection behavior. |
| `font_weight`, `font_size` | `normal`/`bold`, 8–32 logical units. Ordinary labels/fields/buttons; specialized widget internals retain their own host-scale typography. |
| `line_height` | Wrapped label line spacing, 8–96 logical units. Allocates one row per line; fixed container heights still constrain content. |
| `color_role` | Semantic theme ink role, e.g. `title`, `muted`, `text`, `edge`; explicit `color` takes precedence. |
| `icon_size` | Visible icon longest axis, 8–128 logical units. Preserve source proportions. |
| `divider_width` | Separator stroke thickness, 0.25–8 logical units. |
| `wrap` | Wrap an ordinary label. |
| `radius` | Field/button surface corner radius, 0–64. Source switch/slider silhouettes and specialized widget internals remain shared. |
| `color`, `background`, `accent` | Text/title color, field/input color, or semantic accent. Hex RGB/RGBA or 3/4-component colors. Unspecified roles still follow the host theme. |
| `colors` | Explicit shared `StyleSheet` color roles. User-authored color values and image pixels are unaffected. |
| `opacity` | Chrome alpha multiplier, 0–1; text/data colors remain legible. Real glass and its cached backdrop stay active. |
| `variant` | Named color variant in the host `StyleSheet`. |
| `template` | Named geometry variant in the host `StyleSheet`; root layout with `scope="group"` only. |
| `icon`, `trailing_icon` | Leading label icon; trailing icon on a Boolean action such as a help disclosure. Existing source icon geometry and motion are retained. |
| `motion` | Dictionary of `enabled`, `strength`, `speed`. Host/global disable still wins; zero strength settles exactly. |
| `units`, `precision` | Numeric display unit/annotation and fixed decimals (0–6). See below. |
| `value_width`, `slider`, `disabled_accent` | Slider number-box width (24–240), slider presentation, or accent fill while read-only. None enables a disabled property. |
| `list_row_height` | Registered list row height, 28–88. Apply after `template_list()`; no custom UIList class attribute needed. |
| `list_rows` | Default visible row count, 1–128. Changes the list viewport without scaling its text or controls. User resizing still works; an existing resized state takes precedence. |
| `label_position`, `label_width` | `auto`, `left`, or `top`; optional 0–320 logical-unit label column. A left slider label stacks when there is insufficient room for its text, track and number box. Paired entry captions stack together. |
| `surface`, `surface_region` | Optional decorative parent surface: `none` (default), `card`, `field`, or `input`. `surface_region="group"` covers the container; `"value"` excludes the external label on a single entry/slider. Other compound groups use their full bounds. No new hit target or owner is created. |
| `surface_radius`, `surface_color` | Parent surface radius (0–64) and optional explicit tint. Unspecified tint comes from the host theme role. Uses the existing shared glass backdrop. |
| `button_padding` | Minimum text-button padding in CSS edge order, such as `(6, 14)`. Centered content uses the larger of each opposing pair. Icon-only controls and menu-option rows retain their compact geometry. Explicit fixed size allocations may still constrain content. Host defaults are `button_padding_x=14`, `button_padding_y=6` in `StyleSheet.geometry`. |
| `list_dividers` | Boolean; registered lists show subtle separators between populated rows by default. Does not add lines through empty space, or across grid/compact presentations. |
| `list_row_padding` | Content insets inside the selection rim; default `(2, 8)` logical units (vertical, horizontal). Number or CSS-order 1–4 values, each 0–24. Applies to ordinary and registered lists. |
| `list_row_align` | Vertical alignment of the whole row content: `center` (default), `top`, or `bottom`. The same padded rectangle drives painting, editing, menus and hit-testing. |
| `list_item_layout` | `auto` (default) aligns an authored unembossed name above a collection search field, preserving its toggle, status and action controls. `authored` keeps the original callback layout. Explicitly styled groups retain their geometry. |

The common container/color/motion vocabulary works with rendered Boolean,
integer, float, string, enum, pointer, vector, color and compound controls, plus
lists authored with `template_list()`. This does not turn a raw collection RNA
property or an unsupported Blender template into a new widget. Use the existing
supported list/compound authoring APIs, then apply the same helper.

## Units, without hard-coded property names

For unitless RNA such as `Camera.lens`, `units="mm"` is a display annotation:
`155.0 (mm)`. It does not infer or change the property's physical meaning.

For native `LENGTH` fields, `mm`, `cm`, `m`, `km`, `in`, and `ft` convert the display
and typed values using scene scale. For native `ROTATION`, use `deg`, `°`, or
`rad`. Drag steps follow the selected display units. Explicit unit-bearing input
continues through Blender's codec; bare expressions use the displayed unit.
Factor/percentage fields retain their own percentage semantics and reject
conflicting custom units. Other native unit categories remain on Blender's codec.

Merely focusing a rounded value without editing it preserves full precision.
Right-click actions continue to use the original owner/property/component.
Copy Data Path, animation, drivers and undo never target a presentation wrapper.

## Migration and retained rendering

Existing `beyond_ui_props` class hints remain compatible. Inline hints override
the corresponding per-control presentation. No changes to property declaration
classes are necessary for the inline API.

CamKeys now uses adjacent `bui.style()` calls and `ui_theme.py` dictionaries for
focal units, help icons, enum-bin cells/gaps, list row heights, compact templates,
primary actions and the disabled CamKey accent. Its former presentation class
attributes and duplicate custom-only list draw branches were removed. Functional
brush ownership/read-only draw/undo lifecycle hooks are deliberately retained;
those implement behavior, not appearance.

Styles resolve during authoring/retained layout. Per-control palettes are cached
against the current host palette; no shader compilation, backdrop capture or blur
is added per styled control. Geometry, bindings, menus and animation objects are
retained. Changing a preset dictionary takes effect on the next authoring pass;
use `StyleSheet.update()` for the existing live host theme transaction.

Verified in the isolated Blender 5.1.2 and 5.2.2 runtime fixtures, including native
UILayout calls with the helper present, recorded replay and real property bindings.
The existing Blender 4.2 paths are retained but not runtime-qualified by this pass.

References: [5.2 UILayout API](https://docs.blender.org/api/5.2/bpy.types.UILayout.html),
[5.2 signature changes](https://docs.blender.org/api/5.2/change_log.html).

## Responsive list and field presets

```python
PROPERTY_LIST = dict(list_rows=5, list_row_height=30)
INLINE_VALUE = dict(label_position="left", label_width=150, value_width=42)
PAIR = dict(gap=10, label_width=60)

row.template_list("MY_UL_items", "", owner, "items", owner, "active_index")
bui.style(row, PROPERTY_LIST)

layout.prop(camera, "lens", slider=True)
bui.style(layout, INLINE_VALUE)

row = layout.row()
bui.style(row, PAIR, scope="group")
row.prop(camera, "clip_start")
row.prop(camera, "clip_end")
```

A style wrapper preserves list toolbar semantics and intrinsic spacing.
`flex_grow` is applied to flexible row children; explicit fixed widths retain
priority. These rules run during retained layout, not every paint.

## Choosing the right customization layer

The current CamKeys design needs are covered without product-specific library
rules. Use these same options in other add-ons:

| Design need | Public configuration |
| --- | --- |
| Shared palette, glass opacity, density and motion | Host `StyleSheet`, its color/geometry variants, and live `update()` |
| Panel sections and aligned rows | `padding`, `margin`, `gap`, `align`, `flex_grow`, size constraints |
| Matching field columns and narrow-panel reflow | `label_width`, `label_position`, `value_width`; shared responsive layout |
| Bold headings, centered actions and help icons | `font_weight`, `font_size`, `text_align`, `icon`, `trailing_icon`, `wrap` |
| Numeric formatting and slider presentation | `units`, `precision`, `slider`, `disabled_accent` |
| List viewport and row density | `list_rows`, `list_row_height`, plus ordinary row styles inside `draw_item()` |
| Individual accents, inset fields and reduced motion | `colors`, `background`, `accent`, `opacity`, `radius`, `motion` |

Color-only presets preserve a box's existing theme padding. `margin` adds to
that padding; explicit `padding=0` removes it. Styling a completed compound row
styles that actual row, so its internal gaps and later-added children behave the
same as `scope="group"`. Repeated size presets are validated together: an invalid
`min_width`/`max_width` combination fails before modifying geometry or colors.

This covers the requested design, not every CSS property. Arbitrary selectors,
media-query syntax, absolute positioning, per-widget shader/blur overrides and
independent resizing of every internal icon are not provided. Shared source
icons, glass and motion stay consistent; specialized controls expose their own
documented APIs. No style option silently changes bindings, right-click owners,
enabled state or operator behavior.

## Glass groups and value capsules

```python
row = layout.row()
bui.style(row, scope="group", surface="card", padding=6, gap=8)
row.prop(settings, "enabled")
row.operator("my_addon.apply")

layout.prop(settings, "sensitivity", slider=True)
bui.style(layout, surface="field", surface_region="value",
          surface_radius=6, padding=(3, 0), label_position="left")
```

The first form groups any controls. The second adds a capsule behind just the
slider track and number field, leaving its caption outside; it follows responsive
label stacking. Surfaces are retained layout decoration, not independent animated
buttons. Child controls retain their own source motion, editing and owner menus.

Selected menu/list rims derive from the active selection and text theme colors.
Override the shared `selection_rim` color role for an explicit branded rim.
Inactive menu rows remain unboxed. Rims and dividers use retained analytic drawing;
they add no framebuffer capture, blur target or idle refresh timer.

List captions, switches and values are centered as one authored content group
inside the selection rim. The full row remains selectable, including its padding.
Registered row height is a minimum: visible content can grow it to fit its padding,
up to the existing 88-unit safety limit. Oversized callbacks still fail explicitly.
Height is retained while scrolling and remeasured after width/data/style changes;
there is no all-items measurement scan or per-paint layout. Explicit padding in a
consumer's `draw_item()` is additional to these shared row insets.

```python
layout.template_list("MY_UL_items", "", owner, "items", owner, "active_index")
bui.style(layout, list_row_padding=(4, 10), list_row_align="center")
```

### Subtle text outline and shadow

All custom panel, widget and menu lettering now has a light black outline (28%
opacity) and a small native-font drop shadow (20%, one logical pixel downward).
The foreground glyph is drawn once; fonts and glyph geometry remain retained.
These effects do not change text measurement, layout, glass or motion.

```python
# Per item, after any ordinary Blender layout call:
bui.style(layout, text_effects={"outline_opacity": 0.2, "shadow_opacity": 0.15})
# Or disable both on an item/group:
bui.style(layout, text_effects={"outline": False, "shadow": False})
# Add-on-wide, including menus and compound widgets:
theme = bui.StyleSheet(text_effects={"shadow_offset": (0, -1), "shadow_blur": 3})
```

`text_effects` also accepts `outline` and `shadow` booleans, opacity values from
0–1, a two-value logical `shadow_offset` from −8–8, and native blur levels 0/3/5.
Partial settings inherit from the parent palette; updates use the existing
stylesheet invalidation path. Missing native font-effect capabilities explicitly
retain plain lettering. No scene settings or Blender preferences are modified.

### Name and search list items

An ordinary `UIList.draw_item()` with a name/search column now gets a shared
text grid, compact status/action lanes and a full-width inset search field.
No CamKeys-specific identifiers or rewritten callbacks are involved. The field
uses the collection item's Blender icon and retains search, clear and property
context menus. A clear operation uses the original binding and host commit policy.
Read-only values stay read-only; display refresh preserves their control objects.

To keep a list's authored geometry:

```python
layout.template_list("MY_UL_items", "", owner, "items", owner, "active_index")
bui.style(layout, list_item_layout="authored")
```

`list_row_padding`, `list_row_align`, `list_row_height`, and explicit styles inside
`draw_item()` remain available. Long names can still clip at narrow widths;
icons and utility controls reserve their own lanes.

Branded icon/title/subtitle rows and vertical rules can be authored with the
[configurable header helper](ARTWORK.md), using this same style vocabulary per element.

### Value feedback and wrapping

`value_feedback=True/False` or a settings dictionary controls finite change ink
using semantic theme roles. `flex_wrap=True` on a row group wraps children at
minimum widths. `text_inset` provides a logical horizontal label inset.
The reusable `BUI_TARGET` icon provides a bullseye for actions without replacing
the native operator. See [value feedback](VALUE_FEEDBACK.md) for defaults,
performance behavior, configuration and native-safe examples.

### Align help/cog accessories to values

Use `bui.style(row, scope="group", align_items="value", gap=7)` on a property
row with a trailing help or settings column. BUI aligns the first editable
value in each child column with the center of icon-only accessories, using
the same slider/entry geometry as painting and hit testing. Top labels and
extra field padding do not push the accessory down. Rows with no editable
field use child centers. Existing `start`, `center` and `end` remain unchanged.
This is retained layout work, not a per-frame adjustment; the same property
bindings, right-click targets and animations remain in place.
