# Explicit layout sizing

`Layout.scale_x`, `scale_y`, `ui_units_x` and `ui_units_y` now affect retained
custom geometry. They are no longer inert attributes. They reuse the existing
BVT fields, switches, sliders, compound controls, glass and motion rather than
introducing a separate painter. [Actual captures and animation](design/qa/layout-sizing-v1/index.html)
remain available for Tyler's visual QA; exact generated-reference acceptance is
not claimed.

```python
row = ui.row()
left, right = row.column(), row.column()
right.scale_x = 2.0
left.prop(settings, "amount", slider=True)
right.prop(settings, "radius", slider=True)

footer = ui.row()
footer.scale_y = 1.5
footer.prop(settings, "enabled")

fixed = ui.column()
fixed.ui_units_x = 8.0
fixed.ui_units_y = 2.5
fixed.prop(settings, "name")
fixed.prop(settings, "mode")
```

## Geometry contract

- Each setting defaults to zero. Zero means automatic size / identity scale.
  New children have their own zero settings; parent settings are applied through
  the tree, not copied onto every child. Explicit nested scales multiply once.
  This preserves the native local-property convention verified in both installed
  runtimes and audited in the 4.2 source.
- `scale_x` changes intrinsic widths and flexible-row width weights. Expansion
  still respects available host width. Scaling a whole expanding row does not
  force it outside its parent. Intrinsic left/center/right layouts and automatic
  flow packing use scaled preferred widths.
- `scale_y` changes ordinary control heights. Fonts, icons, BVT slider geometry
  and switch glyphs retain their normal logical sizing inside those rows; they
  are not stretched with the rectangle.
- A custom UI unit is one host logical row (`Canvas.theme.row_height`, normally
  32), rather than an artboard pixel. `ui_units_x` provides a fixed-width request
  before flexible siblings consume remaining space. Narrow parents constrain
  fixed requests proportionally. A local units request overrides that layout's
  own scale; ancestor scale still applies.
- `ui_units_y` fits the group's contents into its explicit height slot. Child
  positions/heights fit that slot, including nested groups. Custom text remains
  at the host font size and clips inside short fields. Empty groups consume no
  space. This custom fit policy is **not** a claim of identical native root,
  column, row and popup height-negotiation behavior.
- Compound controls retain their aspect ratio and preferred host font scale.
  Larger slots reserve space without magnifying the artboard. Smaller explicit
  constraints use the existing uniform shrink-to-fit path. Readability at tiny
  sizes remains unqualified; unconstrained compounds keep their normal size.
- Source gaps and padding retain their own spacing policy. Pixel-identical native
  distribution, minimum-width heuristics, joined corners and every native layout
  edge case remain open. Native `UI_UNIT_X/Y` pixel dimensions are not substituted
  for BVT logical geometry.

Settings accept finite values from 0 to 4096. Combined nonzero scale products
must be positive, finite and at most 4096. Invalid values fail explicitly; no
unbounded dimensions or silent native fallback are admitted. These bounds are
part of this library's partial contract, not unrestricted native range parity.

## Input and lifetime

Control bounds used for painting and input come from the same retained plan.
Resizing retains the control and binding identities. Changing a sizing policy
cancels an active edit with rollback, closes menus/popovers and clears motion
before invalidating geometry, so a drag or deferred menu cannot keep obsolete
bounds. Hosts retain their existing redraw/invalidation responsibility; no
polling timer is added.

Right-click actions continue to target the exact property. Compound overlays
still use `Canvas.open_widget` and host bounds. Wide numeric controls retain the
15% amplitude rule based on their resulting width. Global/host animation disable,
active-theme roles and the shared real-glass backdrop are unchanged.

## Cost and evidence

Sizing state is tracked in a weak registry owned by each Canvas. The registry
cannot keep a discarded group alive. With no nonzero sizing policies, arrangement
uses the small ordinary-placement path. Configured plans resolve scale products
once per layout invalidation; neither path adds sizing work to paint or idle
redraw. Resetting all policies returns to the ordinary path.

The QA records include source hashes, six 1×/1.5×/2× capture sets, narrow/wide
bounds, explicit size changes, owner menus, disabled motion and 360 native-text-
batching frame pairs. Disposable Blender 5.1.2 and 5.2.2 tests cover native property
defaults/setters, real N-panel input, RNA rollback, retained geometry and teardown.
Existing renderer, flow, list, menu, pointer and popover regressions remain in the
same run. Before/after paint and 144-control layout timing distributions are
separate; configured layout timings have no equivalent baseline implementation.
These measurements do not establish source-level speed or exact visual parity.

Official exact-version [4.2](https://docs.blender.org/api/4.2/bpy.types.UILayout.html),
[5.1](https://docs.blender.org/api/5.1/bpy.types.UILayout.html), and
[5.2](https://docs.blender.org/api/5.2/bpy.types.UILayout.html) API pages and Manuals
were searched. Some direct fetches were unavailable and are not counted as
evidence. Immutable official `interface_layout.cc` / `rna_ui.cc` source hashes
for 4.2.0 and both installed builds are retained in the
[source audit](design/qa/layout-sizing-v1/source-audit.json). Blender 4.2 and Windows
execution, the full theme matrix and exact-reference acceptance remain open.

All four members remain **partial** in the [API ledger](CUSTOM_PARITY.json).
