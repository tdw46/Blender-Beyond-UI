# Value-change feedback

Visible bound values briefly use the theme's `accent` ink when they change, then
return to their ordinary color. CamKeys maps this role to its configurable coral
accent (color 2). Read-only values participate; property ownership and editing
behavior do not change. User-authored swatch/ramp colors remain their actual data.

Defaults: enabled, 0.22-second hold, 0.18-second fade, numeric epsilon `1e-6`.
The first displayed value establishes a quiet baseline. Text labels containing
computed values opt in explicitly:

```python
row.prop(item, "weight")
bui.style(row, value_feedback={"hold": 0.22, "fade": 0.18, "role": "accent"})

row.label(text=f"{value:.3f}")
bui.style(row, value_feedback=True)
```

Disable or configure a complete host with `StyleSheet(value_feedback=False)` or
`StyleSheet(value_feedback={"enabled": True, "hold": .3, "fade": .2})`.
Apply the sheet through the normal host stylesheet update path. Global disable
wins over control overrides and inherited list settings. Per-control `False`
disables that control. Durations must be finite between zero and five seconds;
`role` must be an existing semantic color role, and epsilon is in `[0, 1]`.

Feedback observes the value already read by visible painting. It adds no RNA
polling, dependency scanning, geometry rebuild, GPU resource or backdrop pass.
It reuses the host's finite animation wake/settle mechanism, clears on parking,
and prunes deleted controls. Hidden controls are culled before reads. Supported
snapshots are scalars and bounded scalar arrays/enum sets; arbitrary RNA objects
are not traversed. It does not request constant idle redraws.

## Responsive groups and reusable target icon

```python
actions = layout.row()
bui.style(actions, scope="group", flex_wrap=True, gap=8)
actions.operator("my.snap", text="Snap to View", icon="VIEWZOOM")
bui.style(actions, icon="BUI_TARGET", icon_size=16, min_width=135)
```

`BUI_TARGET` is a retained vector bullseye/crosshair. The original native icon
remains available when rendering through Blender's native layout. `flex_wrap`
wraps authored child groups using their minimum widths; it changes neither
bindings nor action owners. `text_inset` overrides a label's horizontal ink
inset in logical units (0–64), useful for aligning metadata with a field border.

The CamKeys consumer displays captured direction as `(pitch, yaw, 0)°`, relative
to its upright/front convention. These are elevation/azimuth angles, not a full
XYZ Euler rotation. Direction captures do not contain roll; invalid captures
say “Uncaptured.” This calculation belongs to CamKeys, not the generic renderer.

See the [reference and Blender captures](design/qa/camkeys-response-v1/index.html).
