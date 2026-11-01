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
| `gap` | Row/column spacing, 0–64. Use `scope="group"` for a row. |
| `width`, `height` | Explicit layout allocation, 1–4096 logical units. |
| `min_width`, `max_width`, `min_height`, `max_height` | Container constraints; available host bounds still win over minimum width. Content fits an explicit height without changing its binding. |
| `align` | Container content alignment: `left`, `center`, `right`, `expand`. |
| `flex_grow` | Relative flexible width in a row, 0.01–100. Fixed/intrinsic widths retain precedence. |
| `display` | `flex` or `none`. Hidden descendants get zero geometry and cannot be hit; hiding an active owned edit cancels it. Native fallback remains visible. |
| `text_align` | `left`, `center`, `right`, `expand` for ordinary control text. Active text editing retains caret/selection behavior. |
| `font_weight`, `font_size` | `normal`/`bold`, 8–32 logical units. Ordinary labels/fields/buttons; specialized widget internals retain their own host-scale typography. |
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
