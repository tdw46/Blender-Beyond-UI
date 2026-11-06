# Brush curve support

`Layout.template_curve_mapping(data, property, brush=True)` now admits the
single-channel brush mode used by CamKeys. It retains the existing graph, shared
liquid-glass card, theme roles, host sizing, point motion and exact-target menus.
Auto, Vector and Clamped handle buttons replace irrelevant color-channel tabs.
The handle status is read-only; X/Y remain editable. Clip and Extend use ordinary
custom property controls, including their RNA context actions.

Point drag/release, right-click cancellation, double-click addition, Delete,
handle changes and preset invalidation are execution-tested. The RNA adapter
reacquires **every** point wrapper after allocation/removal, and versions point
context bindings so old targets cannot dereference freed storage. Curve samples
are retained until coordinates/handle types/extension/clip state change. Painting
never initializes IDs or brushes, loads fonts, captures another backdrop or
starts timers.

CamKeys prepares brushes on popover opening and synchronizes its deformation on
committed changes. Its branch owns a bounded scene snapshot journal and undo/redo
handlers for Blender 4.3+, where Brush IDs opt out of memfile undo. The older
4.2 native-undo path remains. The journal checks brush identity before restoration
and unregister removes its handlers. The library remains product-independent.

Evidence: [consumer checks](design/qa/camkeys-custom-v1/runtime.json).
Source of the version boundary:
[Blender 4.3 Brush flags](https://raw.githubusercontent.com/blender/blender/v4.3.0/source/blender/blenkernel/intern/brush.cc)
versus [Blender 4.2](https://raw.githubusercontent.com/blender/blender/v4.2.0/source/blender/blenkernel/intern/brush.cc).
The installed 5.1.2/5.2.2 tests independently confirmed the undo behavior.

This does not claim every native curve-editor feature: zoom/pan, extra clip-bound
editors, tone/levels, negative-slope and general preset-gallery modes remain
outside this consumer batch. Existing native preset/import/export operators are
consumer-owned. No new generated-reference match, motion capture, visual approval
or warm GPU performance benchmark is claimed for the added brush state.

## Optional endpoint locks

Curve controls accept `curve_lock_start` and `curve_lock_end` through `bui.style`.
Both default to `False`. The enabled option holds the existing leftmost/rightmost
point at its current X/Y position; it does not assume a particular falloff value.

```python
graph = layout.column()
graph.template_curve_mapping(brush, "curve", brush=True)
bui.style(graph, scope="group", curve_lock_end=True)
```

Locked points can be selected and inspected, but not moved, typed over or deleted.
Their coordinate context menus retain readable copy/developer actions while
blocking edits. Interior points remain editable, with X constrained inside the
locked endpoint. Handle types remain editable. This contract applies to BUI's
custom curve interactions; a native fallback editor has its own behavior.
Consumers own endpoint initialization and constraints for external preset/import
operators. No binding writes occur during layout or painting.

CamKeys enables the end lock on both view-plane transition curves and initializes
that endpoint at `(1, 0)`. Every transition preset now shows an editable graph;
the first edit selects Custom automatically. Nonlinear presets seed a sampled
editable curve, rather than promising an identical analytic preset after editing.
Preset/import commits also restore the zero endpoint. Preview changes use the
existing coalesced update path while dragging; no idle polling was added.

Validation: Blender 4.2.23 and 5.2.2 execution checks cover both directions, all six
preset selections, mid-drag Custom activation, endpoint preservation and exact
context ownership. A 5.2.2 Metal capture and registered custom-popup route check
are included in the [view-plane review](design/qa/subject-controls-v2/index.html).
Physical Windows replay of this addition remains open.


### Transient registered-popover owners

Registered popovers retain custom context pointers accessed during preparation
and drawing. Blender's ordinary context copy omits these temporary override
members, so copying it alone can silently lose a curve's owner after opening.
`PanelContextCapture` records at most 64 accessed custom members and routes them
through the existing stale-owner checks. Front/back transition regression tests
open the actual operator popup, edit while dragging, flush the coalesced update,
and verify evaluated mesh coordinates change before release. Commit journaling
also prefers the exact transition owner over the scene's active list item.
