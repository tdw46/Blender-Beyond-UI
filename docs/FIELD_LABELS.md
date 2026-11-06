# External field labels and optional icons

Plain numeric entries, text/path fields, shortcut entries, pointer/search fields
and enum dropdowns paint their label on the glass at the left, outside the value
surface. `scalar_geometry.entry_parts` defines a 36% label column plus an 8-unit
gap, with bounded clipping at narrow widths. Empty labels reserve no column.
Sliders retain their BVT label/track/bubble/value layout. Compound curve, ramp and
color component fields use the same external-label treatment with their authored
label-column widths. The full row remains the focus/context owner; editing and
clipboard operations contain only the bound value, never the label.

Editable component forms use ordinary host row heights. Enum choices use the
compact menu rhythm. Confirmation buttons center their complete text/icon group.
Menu highlights grow 1.25 logical units above and below the row only in painting;
row positions, text baselines and logical hit targets remain unchanged.

Search text is 10 logical units (body text remains 11). A shared theme-derived
hairline surrounds inset fields and action buttons. The outline uses the retained
skin shader with a transparent center; shared glass/backdrop resources remain
unchanged. No extra backdrop capture, blur or GPU readback is introduced.

## Label icons

Icons are optional, not automatic decoration. The shared painter reserves a
12-unit silhouette and a 6-unit gap before the label. Buttons center the complete
icon/text group. Glyph geometry is retained, theme-colored and submitted under
the same finite animation transform as the label. No-icon labels keep their
original indent. Narrow labels clip without moving the value column.

```python
ui.prop(settings, "output", text="Output", icon="FILE_FOLDER")
ui.prop(settings, "visible", text="Visible", icon="HIDE_OFF")
ui.template_component_menu(obj, "location", name="Transform Components",
                           icon="EMPTY_ARROWS")
ui.label(text="Information", icon="INFO")
ui.title(text="Output", icon="folder")
```

Built-in custom vectors include `folder`, `axes`, `search`, `object`, `collection`,
`camera`, `image`, `material`, `palette`, and the existing source glyphs. Common
Blender aliases include `FILE_FOLDER`, `EMPTY_ARROWS`, `ORIENTATION_LOCAL`,
`HIDE_OFF`, `OBJECT_DATA`, `CAMERA_DATA`, `IMAGE_DATA`, `MATERIAL` and `INFO`.
This does **not** claim to implement Blender's entire native icon atlas.

For consumer-owned icons, create the Canvas with an optional `icon_renderer`:

```python
def draw_icon(name, icon_value, rect, color):
    # Paint a preloaded/retained icon under the current transform and clipping.
    # Return True if handled; False delegates supported names to custom vectors.
    return my_retained_icons.paint(name, icon_value, rect, color)

canvas = Canvas(icon_renderer=draw_icon)
ui = Layout(canvas, context)
ui.label(text="Custom", icon_value=123)
```

The consuming extension owns texture/cache lifetime. Do not load, compile, scan
or allocate GPU resources in this callback during steady-state paint. Numeric
`icon_value` on labels/properties/titles requires this explicit renderer; it is
not silently treated as a Blender-native preview. Popovers inherit the callback.
Compound `Painter.field(..., icon="folder")` supports the same optional label
placement in its design units.

References: `design/references/external-labels-v1/`, the optional-icon revision
`external-labels-icons-v1/`, and the earlier centered-button study
`macos-confirm-v1/`. The latter's inside-label layout is superseded. Actual
captures, geometry differences and approval status remain in the versioned QA
page; generated art is never loaded into production drawing.

## Empty labels and compact rows

For `prop()` and `operator()`, an omitted `text` uses the RNA display name; an
explicit `text=""` suppresses it. Icon-only buttons center the icon without a
phantom text gutter. Label-free row toggles use the shared compact switch width,
and horizontal AUTO separators reserve fixed blank spacing rather than equal
field-sized cells. Untitled registered popovers do not allocate a title row.

The retained vector renderer also supports `SMOOTHCURVE`, `SPHERECURVE`,
`ROOTCURVE`, `SHARPCURVE`, `LINCURVE` and `NOCURVE`. Geometry is built once per
glyph; theme tint, opening motion and context ownership remain shared.


## Themed segmented choices and duotone artwork

Retain native enum ownership while styling a choice as a segmented button:

```python
row.prop_enum(settings, "mode", "LENS")
bui.style(row, enum_style="segment", icon="BUI_LENS",
          font_weight="bold", icon_size=24, height=38,
          radius=10, text_align="center", button_padding=(7, 10))
```

`enum_style="menu"` restores the ordinary menu-option presentation. Selection,
actions, property context menus and bindings remain the original control's.
Use ordinary responsive style rules for compact widths.

Bundled transparent two-color icons: `BUI_LENS`, `BUI_SUBJECT_SIZE`,
`BUI_EXACT`, `BUI_ARTISTIC`, `BUI_FORCED_PERSPECTIVE`, `BUI_FALLOFF`,
`BUI_HELP`, `BUI_LOCK`, `BUI_RESET`. Use `bui.Artwork(name, native_fallback)`
for headers that also draw in native Blender. Layers use the resolved primary
and secondary accents; native secondary falls back to the toggle color when
no secondary override is configured. Consumer color overrides remain respected.

SVG sources live in `beyond_ui/assets/icons/duotone`. Build their shared retained
atlas offline with `uv run --with resvg-py --with pillow python tools/build_duotone_icons.py`.
No SVG parsing or texture allocation occurs during steady-state painting.
Both layers retain the same artboard, preserving their mutual alignment.
