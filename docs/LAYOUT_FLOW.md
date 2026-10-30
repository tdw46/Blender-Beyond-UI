# Retained split and flow layouts

`Layout.split()`, `column_flow()`, `grid_flow()` and `separator_spacer()` now arrange
existing custom controls. These methods do not forward to native UI or introduce
another renderer. `direction` follows Blender's local-direction API, which is
not always the visible packing axis: roots/rows report horizontal and splits
report vertical. Grids report vertical on 4.2–4.4 and horizontal from 4.5 onward;
the explicit version check retains the older behavior. Pure-Python hosts use
the 4.2 convention. The installed-runtime fixture compares all seven container
kinds directly with native RNA.

```python
from .vendor.beyond_ui import Layout

ui = Layout(context=context)
split = ui.split(factor=0.35)
split.column().prop(settings, "amount", slider=True)
split.column().prop(settings, "radius", slider=True)

grid = ui.grid_flow(row_major=True, columns=-2, even_columns=True)
for name in ("visible", "enabled", "preview", "render"):
    grid.prop(settings, name)

flow = ui.column_flow(columns=2)
for item in settings.items:
    flow.prop(item, "weight", slider=True)

footer = ui.row()
footer.label(text="Status")
footer.separator_spacer()
footer.label(text="Ready")
```

## Geometry and state

- A split allocates `factor` to its first child and divides the remainder among
  subsequent children. Zero selects equal shares. Invalid/nonfinite factors fail.
- Grids support row/column order, automatic and explicit column counts, negative
  multiples along the major axis, weighted column widths and equal row cells.
  Automatic packing uses intrinsic widths; changing host width reflows geometry
  without replacing controls, bindings, menus or motion owners.
- Column flow balances cumulative item heights into columns. Automatic columns
  use the available custom host width and widest child. Explicit counts are
  nonnegative. Automatic columns use local host space rather than Blender's
  native root-block `emw`, which this custom host does not expose.
- `align=True` removes inter-control spacing. It preserves BVT rounded surfaces;
  native joined-button corner treatment is not claimed.
- `alignment` supports `EXPAND`, `LEFT`, `CENTER` and `RIGHT` for ordinary rows
  and columns. Intrinsic controls do not enlarge their fonts to fill a layout.
  Full alignment semantics for grid/flow groups remain partial.
- Horizontal spacers divide spare width after intrinsic control widths. They
  have no paint, binding, hit target, context menu or animation. A vertical spacer
  request, including non-row containers, fails explicitly instead of inventing a visible control.
- `enabled` and `active` are live group policies. Every descendant must satisfy
  all ancestor policies, regardless of a child's local value. Disabling the
  owner of an edit, captured widget, focused widget or popover cancels it safely;
  re-enabling the group restores its descendants' own eligibility. Context menus
  retain their existing disabled/read-only property action rules.

The host supplies retained BLF measurement using the same body/title fonts and
logical sizes as painting. Other hosts can call
`canvas.set_text_measure(callback, revision_key)`, where `callback(text, role)`
returns logical width. Change the key after a font or size revision. Without a
callback the pure-Python fallback estimates text width; that estimate is not
qualified for exact visual acceptance. Embedded-host teardown releases its
measurement callback before releasing fonts.

Geometry plans exist only while arranging an invalidated layout. Unchanged
`arrange(width)` calls return the retained height without measurement or binding
reads. Child geometry, paint clipping, exact context targets, BVT scalar layouts,
wide-numeric amplitude, theme roles and shared backdrop/motion paths are retained.
No shader, texture, font, timer or blur producer is created by the flow engine.

## Evidence and limitations

[QA gallery](design/qa/layout-flow-v1/index.html) contains actual Blender frames at
1×, 1.5× and 2×, narrow bounds, parent state changes, right alignment and a grid
cell's owner menu. Existing BVT controls are reused; no new generated visual
specification or visual approval is claimed. Tyler owns visual QA.

Direct API/Manual fetches were unavailable; indexed official [4.3](https://docs.blender.org/api/4.3/bpy.types.UILayout.html) and [5.0](https://docs.blender.org/api/5.0/bpy.types.UILayout.html) API pages confirm the public layout signatures. The source audit records official 4.2.0 and installed 5.1.2/5.2.2 source URLs
and hashes used for split/flow/grid signatures and packing behavior. Additional
4.3, 4.4, 4.5 and 5.0 source snapshots establish the grid-direction transition. Both installed
runtimes exercise real RNA and N-panel mouse/context input in disposable profiles.
No installed 4.2 runtime is available, and no older API path was removed.

`scale_x/y`, `ui_units_x/y`, complete property-split alignment, automatic root-block
width equivalence, joined corners, every compound-child sizing combination,
platform/theme qualification and exact generated-reference acceptance remain
open. These methods are partial in the member ledger. They do not close the
remaining specialized templates or the overall parity release gate.
