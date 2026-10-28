# Numeric property support

`Layout.prop()` now preserves RNA numeric semantics through a shared `Numeric`
codec while retaining the custom Canvas painter, BVT glass, motion, semantic theme
roles and exact original binding for context-menu actions. The same codec is used
for numeric fields contributed to context menus.

```python
ui = Layout(context=context, commit=host_undo_callback)
ui.prop(obj, "rotation_euler", index=1)  # displayed angle, stored radians
ui.prop(obj, "location", index=0)        # scene units and scale
ui.prop(scene.render, "resolution_percentage", slider=True)
```

Always supply the owning context. A missing context uses deterministic defaults
(no scene units, degrees, ordinary factors); it does not infer a global scene.
The consumer still owns registration, undo, redraw and rebuild/invalidation.

## Implemented behavior

- Angles/Euler components display degrees or radians according to scene settings.
  Typed bare values use that setting; explicit `90°` and `1rad` are accepted.
- Lengths use metric/imperial settings, preferred length units and `scale_length`.
  Mixed unit expressions such as `1m 3cm` and `1ft + 2in` use Blender's public unit
  parser. Bare values use the displayed reference unit. Area and volume apply
  squared/cubed scene scale, with Blender's adaptive unit formatter.
- Factor fields follow Blender's factor/percentage preference. Explicit `50%`
  always means a factor of 0.5; percentage-valued RNA remains in its native
  0–100 domain. Integer displays remain integers.
- Click/release without dragging enters text mode. A drag crosses the source
  three-pixel threshold and uses retained fractional accumulation, BVT step
  behavior, Shift precision and Ctrl snapping. Preferred length units and angles
  determine the displayed drag scale. Sliders use a finite soft-range track.
  Mouse dragging respects soft limits; typed values respect hard limits.
- `slider=False` suppresses the numeric track; `slider=True` retains the shared
  slider fill/theme role. Direct low-level `Canvas.number()` keeps its prior
  default unless a `numeric` codec or explicit slider option is supplied.
- Confirming unchanged rounded text preserves the exact original stored value.
  Unit settings are captured at edit start; changed settings reject stale text
  interpretation and cancel an active drag. Escape/right-click restores the
  original value before another menu can open.
- A failed host commit restores the original value and releases the Canvas edit.
  Right-click commands continue to receive raw RNA values and the exact component,
  rather than a display-converted replacement binding.

Unit input is bounded to 256 characters, twelve nesting levels, basic arithmetic
and known length/angle unit tokens before reaching Blender's public parser.
Arbitrary Python, calls, attributes, powers and collection literals are rejected.

## Rendering and lifetime

Scene/view settings are resolved once per context in a visible Canvas paint and
shared by its numeric controls. Unit conversion/formatting caches have bounded
primitive keys (1024 text results, 32 fixed-unit factors); they retain no owners,
contexts, GPU resources, timers or handlers. Clipped controls are still culled
before binding reads. No unit parser runs during steady-state painting after the
fixed preferred-unit factors are warm. Settings changes use the host's existing
redraw/invalidation lifecycle; there is no polling timer or geometry rebuild.

[QA v1](design/qa/numeric-props-v1/index.html) includes actual unit/raw presentation,
inline editing, right-click, live theme/imperial/radians and finite motion frames.
Its baseline disables only formatting in the same renderer; it is not a historical
binary or a generated reference. Settled and motion-disabled pixels equal resting
pixels. Exact generated-reference/motion acceptance remains open.

## Compatibility and remaining parity

The public `bpy.utils.units.to_value(..., str_ref_unit=...)` and `to_string`
surfaces are verified against official Blender source at 4.2.0 and both exact
installed 5.1.2/5.2.2 revisions; hashes and URLs are in the
[API source audit](design/qa/numeric-props-v1/api-source-audit.json).
Optional unit/view settings use capability fallbacks. Both installed runtimes
pass disposable-profile execution tests; Blender 4.2 and other platforms have
not been executed in this pass. No minimum-version change or native ABI adapter
is introduced.

The exact 4.2/5.1/5.2 API and Manual URLs were queried, but the documentation fetch
service returned access/cache errors for most pages. Current behavior is supported
by installed-runtime results and exact official source, not stale search pages.
Relevant documentation: [4.2 units](https://docs.blender.org/api/4.2/bpy.utils.units.html),
[5.1 units](https://docs.blender.org/api/5.1/bpy.utils.units.html),
[5.2 units](https://docs.blender.org/api/5.2/bpy.utils.units.html), and
[5.2 numeric fields](https://docs.blender.org/manual/en/5.2/interface/controls/buttons/fields.html).

This is still partial `prop` parity. Remaining work includes pointer fields, remaining event variants,
decorators, step arrows, Tab/multiple-field editing, full mathematical expressions
and expression-to-driver input, additional unit categories (time, mass, power,
temperature, velocity and others), complete subtype/keyword semantics, and exact
visual/motion acceptance. These are tracked in `CUSTOM_PARITY.json`; they are not
silently counted as implemented.

## Wide-field motion correction

Wide numeric controls now use 15% of their otherwise-resolved bounce amplitude.
Compact fields and menu motion are unchanged. Configure
`canvas.wide_numeric_motion_scale` before layout or live; shared disabled/zero
strength settings continue to win. [QA v2](design/qa/numeric-props-v2/index.html)
preserves v1 and compares the actual original/reduced motion side by side.
[Event property support](EVENT_PROPERTIES.md) is the next implemented prop slice.
