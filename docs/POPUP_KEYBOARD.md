# Popup initial editing and default actions

Registered custom panel popovers now consume `activate_init` and `active_default`.
These settings previously had no effect. The library reuses its ordinary BVT
fields, selected-button theme role, liquid glass, source springs and exact-owner
context menus. No native widgets or operating-system activation are involved.

```python
def draw(self, context):
    ui = self.layout
    ui.activate_init = True
    ui.prop(context.scene.render, "filepath", text="Output")
    ui.activate_init = False

    ui.operator_context = "EXEC_DEFAULT"
    ui.active_default = True
    ui.operator("my_extension.apply_output", text="Apply Output")
```

## Implemented behavior

- On opening a custom registered-panel popover, the first eligible text or
  numeric field marked `activate_init` starts an edit with its value selected.
  Its existing value is not written and no operator runs. A clipped initial field
  scrolls into view; resizing or repainting does not restart its edit.
- Layout flags are local authoring settings, captured by subsequently authored
  controls. Native child layouts start with both flags false; this is verified
  with real N-panel probes on 5.1.2 and 5.2.2. The internal rows created by
  array properties and property-split decorators preserve a property's request.
- Return first commits an active text/numeric edit. Invalid numeric input keeps
  the editor open. A subsequent Return or keypad Enter invokes the first eligible
  ordinary `operator()` button marked `active_default`. Modified Return and held
  key repetition do not invoke defaults. This deliberately explicit two-step
  edit/execute contract does not claim every native dialog acceptance behavior.
- Default operator buttons use the existing selected theme treatment inside a
  popover. Text and plain numeric editors now paint selection/caret over the
  value; their labels remain outside the editable selection. Slider fields keep
  the source separate number-entry geometry and their existing caret behavior.
- Context menus, nested popovers and focused compound widgets retain their input
  ownership before default actions. A nested default cannot invoke its parent.
  The current property remains the context-menu target after cancelling an edit.
- Registered-panel, opener, control and RNA ownership are revalidated before
  activation. Removed/replaced controls, disabled fields and stale contexts cannot
  receive old edits or default actions. Operator execution retains the consuming
  extension's poll, context, undo and commit policies.
- `FINISHED`/`RUNNING_MODAL` dismiss the originating popover; `CANCELLED` leaves it
  open. A newly replaced overlay is not dismissed accidentally. Closing or
  invalidating a popover releases its candidate references and animation state.

Initial candidates and default buttons are indexed once per popup creation,
bounded by the existing 4096-control admission. No candidates are scanned during
paint. No timers, scene mutation, font/GPU allocation, OS focus changes or new
backdrop capture are introduced by the focus controller. New selection rendering
uses retained theme/font resources. Disabled/zero-strength motion still leaves
glass and keyboard behavior intact.

## Evidence and remaining gaps

[Production QA](design/qa/popup-focus-v1/index.html) includes 1×/1.5×/2× captures,
text selection, numeric entry, committed/default state, nested popovers, owner
menus, narrow bounds and disabled motion. The GIF uses actual Blender frames.
Six captures compare 360 motion frames with native font batching on/off. The
records include GPU resources, paint timing distributions, equivalent pre/post
renderer workloads, source hashes and an application-activation audit.

To reproduce the main matrix and focus audit, compile the observer described in
`BACKGROUND_TESTING.md`, then run it around `uv run python
tools/run_popup_focus_qa.py`, saving its report to `build/popup-focus/focus.json`.
The runner exports baseline `54dd612` and runs fixtures sequentially. For the
separate paired performance diagnostic, run `tests/benchmark_popup_focus_paired.py`
through `tools/run_blender_tests.py --windowed` once per installed version. Set
`BEYOND_UI_OPERATOR_BENCHMARK` to the absolute `build/popup-focus/paired/52` or
`51` directory and `--output` to the matching `52-run` or `51-run` directory.
Finally run `uv run python tools/build_popup_focus_qa.py`; it verifies source and
fixture hashes, result records, pixel equality and focus records before packaging.

Pure tests cover cancellation, stale fields/actions, disabled/replaced controls,
invalid numbers, repeated/modified Return and nested ownership. Disposable
5.1.2/5.2.2 runtime and actual N-panel input tests exercise registered operators,
RNA writes, native flag defaults, property-split/array requests and teardown.
Tests use the [no-focus runner](BACKGROUND_TESTING.md); visual judgment is Tyler's.

Both API members remain **partial**. Initial activation of enum/search/pointer,
event and arbitrary compound controls is not implemented by this controller.
Default activation of operator-enum/menu variants and arbitrary native dialogs
is not covered; ordinary inline canvases never acquire popup keyboard semantics.
Full native focus/Tab navigation and confirmation-dialog behavior, the broader
theme/platform matrix and exact generated-reference acceptance remain open.

Exact-version [4.2](https://docs.blender.org/api/4.2/bpy.types.UILayout.html),
[5.1](https://docs.blender.org/api/5.1/bpy.types.UILayout.html) and
[5.2](https://docs.blender.org/api/5.2/bpy.types.UILayout.html) API/Manual pages were
searched/requested. Unavailable exact-version fetches are not evidence. The
[source audit](design/qa/popup-focus-v1/source-audit.json) records immutable official
`rna_ui.cc` and `interface_layout.cc` sources for 4.2.0 and both installed builds.
Blender 4.2 and Windows execution remain unqualified; no support minimum changed.
