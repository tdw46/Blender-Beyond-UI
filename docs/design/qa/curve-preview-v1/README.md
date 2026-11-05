# Live custom-curve previews and preset refresh

The brush editor updated RNA during a drag, but CamKeys only synchronized the brush into its Geometry Nodes graph from the commit hook. Preset operators captured undo state without refreshing the dependent deformation. These were separate stale-update paths.

BUI now exposes an inherited `Layout(preview=...)` callback and the adopted-panel hook `beyond_ui_preview(context, data, property_name)`. Point/handle edits and cancellation notify preview independently of commit. External preset resizing reacquires the same owner's point wrappers on redraw; no RNA is mutated by painting and stale owners remain invalid.

CamKeys queues one finite main-thread task per event burst (1/60-second interval). It synchronizes the existing GN update path and requests viewport redraw, without rebuilding the panel or writing per-move undo entries. Commit/preset flush immediately and cancel pending duplicate work. Cancellation previews the restored curve. Unregister removes pending work; idle has no permanent timer. Preset, add/remove and import operators explicitly refresh after successful edits, so native and custom UI share the correction.

The 257-point integral table reuses its point allocation when size is unchanged, instead of removing and recreating 255 points per edit. Existing signature checks skip unchanged curves. No mesh scans, shader/backend changes or extra persistent polling were introduced.

## Evidence

Actual registered CamKeys popover tests pass on 4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2, 5.2.2. Twenty move events coalesce to one refresh before release; both graph and evaluated companion mesh change; cancellation restores both; no undo journal write during preview; all six presets synchronize immediately with the overlay still open; release commits once; integral point storage remains stable across changed presets; pending tasks stop on teardown. No owned test focus activation/restoration.

472 unit tests (one skipped), plus real packed-RNA point editing/cancellation on 4.2/5.2. Live Uraraka definitions reloaded without unregistering scene properties: view, lens, frame, curve values, schema 25 and saved-file mtime preserved. No save or version bump. Physical Windows replay and user motion acceptance remain separate; no new visual/GIF evidence is claimed.
