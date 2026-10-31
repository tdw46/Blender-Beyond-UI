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
