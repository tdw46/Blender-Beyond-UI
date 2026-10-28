# Custom event properties

`Layout.prop(owner, name, event=True)` renders a custom field for scalar integer
Blender event codes or event-valued enums. `full_event=True` supports an existing
`KeyMapItem.type`: keyboard modifiers, explicit mouse/device capture and a held-key
modifier chord. Both reuse the existing BVT field and context-menu painters,
active-theme roles, shared liquid glass and finite squash/stretch motion.

```python
ui = Layout(context=context, commit=commit_change)
ui.prop(keymap_item, "type", event=True, text="Key")
ui.prop(keymap_item, "type", full_event=True, text="Shortcut")
```

Click the field, select a capture mode, then provide the input. Escape or
right-click cancels. Right-click on the resting field routes to the exact RNA
property using the shared host-extensible context-menu contract. Keyboard menu
navigation and Shift-F10 context invocation retain their existing behavior.

Event-only capture changes the key, preserving a KeyMapItem's modifiers and
activation settings. Full-event capture sets modifiers from the captured input
while preserving activation value, repeat and direction. Device changes set
`map_type` before `type`; dependent RNA fields are restored in setter order.
Optional fields such as `hyper` are capability checked. No new operator, keymap,
timer or preference save is installed by this feature.

The host's `commit(before, after)` callback receives scalar values for event-only
capture, and dictionaries of the entire editable event state for full-event
capture. It runs once after a successful change. Failed commits roll back the
snapshot. The host remains responsible for undo and persistence; it should rebuild
bindings after undo/load. Invalidated/deleted owners, changed chords or operator
identity, read-only bindings and out-of-range integer codes fail closed.

Full-event capture checks collisions in the selected keymap and the existing
shared global/editor scopes at commit time. It never silently replaces another
binding. Keymap discovery and collision scans run only on capture submission,
not during painting or mouse movement. Immutable event metadata is bounded and
cached; no per-control backdrop capture, GPU resource creation or theme timer
is added.

## Evidence and limits

[QA v1](design/qa/event-props-v1/index.html) contains actual production frames,
disposable-profile RNA cases and real window-event tests on macOS arm64 Blender
5.1.2 and 5.2.2. The exact official `UILayout.prop` event/full_event implementation
sources at Blender 4.2.0 and both installed revisions are recorded in the
[API source audit](design/qa/event-props-v1/api-source-audit.json). Exact versioned
API/Manual URLs were searched/opened; most fetches returned access/cache errors,
so installed runtime and exact official source provide the execution evidence.
Blender 4.2, Windows/Linux and physical NDOF devices have not been executed here.
No minimum supported version or native ABI adapter changed.

Remaining parity includes arbitrary full-event owner types, modifier-only/Escape/
right-mouse assignment (reserved for cancellation here), complete modal/event
variants, all editor-specific conflict scopes, keyboard focus traversal/activation,
all keyword combinations, and generated-reference/motion/theme/DPI acceptance.
Event-only fields do not perform full-chord conflict checking. This is partial
`prop` support, not complete event UI parity. Pointer properties, decorators and
additional numeric semantics remain separate ledger items.
