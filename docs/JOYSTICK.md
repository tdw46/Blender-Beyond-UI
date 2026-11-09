# Joystick, accents, and responsive styling

`bui.joystick` adds a retained 2D control. Bind a two-element float vector or two float properties. Native layouts retain numeric fields; the custom pad requires a BUI host.

```python
bui.joystick(layout, settings, "offset", label="View offset",
             minimum=(-20, -20), maximum=(20, 20), default=(0, 0),
             size=90, gap=18, mode="VELOCITY", speed=0.35,
             velocity_curve=(0, 0), compact_below=280,
             compact_size=64, compact_gap=10)
# Alternative binding:
bui.joystick(layout, settings, x="offset_x", y="offset_y")
```

`POSITION` is the default. `VELOCITY` integrates displacement only while held; release centers the handle and commits once. `speed` is maximum property units/second. The two `velocity_curve` values are cubic Bézier ordinate controls between endpoints 0 and 1; `(0, 0)` gives very slow cubic response near center. `size`, `gap`, and breakpoint widths use host logical units. `fields=False` omits X/Y fields. Reset restores `default`; right-click resolves the vector or exact component, and cancellation restores the pre-drag value. Hidden controls stop updating. There is no idle timer.

With `label` and `compact_below`, compact mode places reset beside the caption, shrinks the pad, and retains X/Y fields alongside it. These are explicit consumer options; no product-name or scene-name checks select the layout.

## Per-control color slots

```python
row.prop(settings, "size", slider=True)
bui.style(row, accent_slot=1)
row.prop(settings, "transition", slider=True)
bui.style(row, accent_slot=2)
```

Slots 1–8 are supported. A `StyleSheet(colors={"accent_1": "#F17C67", "accent_2": "#66DFB4"})` can define them. Without explicit slot colors, slot 1 follows Blender's accent, slot 2 its toggle accent, and additional slots fall back to the primary accent. A consuming add-on decides whether its color override is enabled; disabling it must remove its explicit colors. Slots theme chrome, not user-authored color data. Group defaults and per-control overrides are both supported.

## Width breakpoints

```python
card = layout.column()
bui.style(card, scope="group", padding=16, gap=14,
    responsive=[
        {"max_width": 280, "style": {"padding": 8, "gap": 10}},
    ])
card.prop(settings, "amount", slider=True)
bui.style(card, label_position="left", responsive=[
    {"max_width": 280, "style": {"label_position": "top"}},
])
```

Each rule accepts `min_width`, `max_width`, and `style`. Width is the **host canvas logical width**, not physical pixels or a nested group's width. Endpoints are inclusive; matching rules merge in declaration order, with later values winning. Up to 16 rules are accepted. Resize restores the base style before applying the new match; nested overrides restore in reverse order. Bindings, ownership, and control identity are retained. Hiding an actively owned control cancels its interaction.

Supported breakpoint properties: padding, margin, gap, width/height and min/max constraints, align, flex_grow, flex_wrap, align_items, display, font_size, font_weight, icon_size, text_align, label_width, label_position, wrap, line_height, text_inset. Breakpoints do not change data values or register Blender properties. Geometry resolves during retained layout; steady-state paint does not evaluate breakpoints.

## Shared inset material

Editable fields and joystick wells use the shared retained inset shader, with soft rim bloom. Fields shade dark at the top and lighter at the bottom; wells retain a dark center with brighter edges. Theme roles `inset_lower` and `inset_upper` allow explicit stylesheet overrides. Backdrop/glass remains shared; the effect adds no per-control framebuffer capture, blur, readback, or idle refresh.

## Fit before wrapping

Joysticks with a caption and X/Y fields now default to `fit_on_wrap=True`:

1. Keep the wide row while pad, fields, reset and gaps fit.
2. Move reset to the caption when that accessory would wrap.
3. Shrink the pad and gaps when the pad/fields pair would wrap.

This uses the actual nested row width and the layout engine's measured minimums, including parent padding. It is independent of a guessed host-width cutoff. The layout performs at most one additional retained reflow; paint and idle work are unchanged. `fit_on_wrap=False` opts out; explicit `compact_below` remains available.

Share `fit_group` between related joysticks to coordinate the compact state. Additional BUI styles can follow the same state:

```python
bui.style(card, scope="group", responsive=[
    {"when": "planes.compact", "style": {"padding": 8, "gap": 10}},
])
bui.joystick(card, settings, "offset", label="View offset",
             fit_group="planes", compact_size=64, compact_gap=10)
# On another property in this group:
bui.style(row, responsive=[
    {"when": "planes.compact", "style": {"label_position": "top"}},
])
```

Named states are `<fit_group>.header` and `<fit_group>.compact`. The most compact stage required by any member wins for that named group. Conditions may also include min/max host widths; all conditions in one rule must match. Each resize probes the original wide layout before applying the chosen state, so changed compact padding cannot cause oscillation while resizing. Reset and X/Y preserve their original property bindings and context menus.

## Faster outer-edge movement

For velocity mode, `edge_speed_multiplier=4.0, edge_start=0.7` preserves the original response through 70% deflection on each axis, then smoothly raises its speed multiplier to 4× at the edge. The blend uses smoothstep, with no slope discontinuity at either end. It multiplies the existing Bézier response; `speed=0.35` therefore reaches 1.4 property units/second at full deflection. Release, undo, cancellation and range limits are unchanged.

The library default multiplier is `1.0` for existing integrations. CamKeys uses the default edge multiplier, with uniform `speed=1.4` instead. `edge_start` must be finite in `[0,1)`; the multiplier must be finite and at least 1. Position mode and keyboard steps are unchanged.

## Shift precision mode

Velocity joysticks accept `fine_speed_scale=0.25`. Holding Shift multiplies their speed by this factor; modifier press/release updates during an existing drag without requiring mouse movement. It also works when Shift is held before pressing the pad. The original response curve, range clamps and single commit per drag are retained. The scale must be finite in `(0, 1]`.

CamKeys uses `speed=1.4, fine_speed_scale=0.25`: four times its original velocity at every deflection, with the original velocity restored while Shift is held. There is no additional edge-only boost.

## Controller-style handle

The default handle is now a 9-unit circular cap. Moving it reveals an 11-unit
base at the center and a 4-unit stem. These use existing retained theme-aware
GPU primitives, with the same handle motion and shared inset/glass material.
No SVG loading, extra blur capture, or idle timer is involved.

`bui.joystick(..., handle_radius=9, base_radius=11, stem_width=4, show_stem=True)`
configures each control. Set `handle_radius=5, show_stem=False` for the earlier
dot presentation. Handle radius must be in `(0, 10]` to fit the full travel,
base radius in `(0, 42]`, and stem width positive; dimensions must be finite.
Logical hit coordinates, X/Y ranges, speed, precision mode and context menus
are unchanged. Dimensions scale with the control's host logical units.
