# Operator lifecycle and live adoption

Existing modal operators must retain their registered RNA through UI adoption and
teardown. Re-registering a class frees its existing instances even when Python
still retains a reference. That produced the CamKeys viewport navigation
`StructRNA ... has been removed` error after a live Beyond UI reload.

`operator_lifecycle.modal_registration_policy` chooses in-place Python callback
replacement for classes with an existing modal trampoline. `Router.close`
restores their original callbacks without unregistering them. A registered modal
descendant also protects its owned nonmodal ancestors, including foreign
registered descendants. Such ancestors keep native popup routing, recorded as
`modal-ancestor` fallback entries. Macro protection remains unchanged.

This fixes operator lifetime; it does not rewrite property values, cancel
consumer engines or swallow stale-reference exceptions. Existing modal
invoke/execute callbacks still receive the custom popup facade. Arbitrary popup
calls from original modal callback bodies remain an explicit integration limit.
The Blender 4.2 path is retained; actual runtime qualification here covers the
installed 5.1.2 and 5.2.2 releases, not every third-party add-on or Blender build.

## Validation — 2026-11-01

- A real timer-driven modal keeps its instance/RNA pointer and property value
  through adoption, teardown, re-adoption and a second teardown on both runtimes.
- Timer callbacks continue after each transition, and an existing modal's invoke
  callback still routes its dialog through Beyond UI. The test-owned engine ends
  normally before its owner unregisters it.
- Direct popup execution, cancellation, undo, property context ownership and
  shared glass pass; existing macro child lifetime tests pass.
- The installed CamKeys copy was refreshed. Its already-invalid engine's orphan
  timer was removed, only that engine restarted, and the original navigation
  operator completed successfully. Unrelated modal engines, selection, active
  object, frame and unsaved state were preserved. No scene save occurred.

Evidence: [runtime report](design/qa/modal-scroll-v1/report.json).

## Popup scrolling

`scroll.py` centralizes top-origin offset deltas. Trackpads use `mouse_y -
mouse_prev_y`, matching native Blender smooth popup scrolling. The OS preference
is already encoded in the event delta; `is_direction_inverted` must not invert it
again. Wheel events retain their existing direction. Zero-delta gestures do
nothing. This is shared by menus, data pickers, collection lists, palette grids
and panel popovers; compact lists also follow both gesture directions.

The source BVT context menu had the opposite trackpad sign. Tyler's macOS bug
report supersedes that source behavior for scrolling only; its appearance,
right-click routing and motion are preserved.

Official API/Manual fetches were unavailable during this audit. The native smooth
scroll formula was verified in versioned Blender source:
[4.2](https://github.com/blender/blender/blob/v4.2.0/source/blender/editors/interface/interface_handlers.cc),
[5.1](https://github.com/blender/blender/blob/v5.1.0/source/blender/editors/interface/interface_handlers.cc),
[5.2](https://github.com/blender/blender/blob/v5.2.0/source/blender/editors/interface/interface_handlers.cc).
Synthetic positive, negative, zero and wheel gestures pass actual control handler
tests. Physical trackpad feel remains user QA; no desktop input was injected.
