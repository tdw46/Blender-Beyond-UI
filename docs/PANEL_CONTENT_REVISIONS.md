# Retained authored panel content

An adopted panel may explicitly implement
`beyond_ui_draw_cache_key(context)` as a static method. Its immutable return value
must cover every dependency of authored branches, literal text, icons, enabled
layout groups, captured owners, list membership and selection. Ordinary bound
property values need not be included unless they also affect authored commands.
The contract belongs to the consumer; the library does not infer dependencies of
arbitrary third-party Python callbacks. Non-opted-in panels retain their existing
authoring behavior.

The library additionally tracks scene/view-layer/object identity, space identity,
mode, region width, UI scale, translation settings and retained disclosure/list
state. Undo, redo, load and explicit `AddonUI.refresh()` revoke retained canvases
and their revisions. Construction initializes list/disclosure state before the
revision is acknowledged, avoiding a redundant second authoring pass.

An unchanged content revision skips recording the adopted draw callback. Live
widgets and bindings still refresh, and the host still paints the current
viewport-backed glass. This separates content authoring from backdrop/presentation
redraw without freezing the backdrop, reducing blur quality or suppressing motion.
Changed content follows the original tape comparison, label patch and structural
rebuild paths. Keys should return tuples/primitives/RNA identities, never mutable
objects expected to be recursively inspected by the library.

Lists validate visible membership during live refresh, so an external same-size
reorder refreshes the collection snapshot instead of displaying stale controls.
Only visible rows are checked on the unchanged path. Hidden panels remain parked
and revalidate on return. Within synchronous, read-only row painting, context and
container scope are checked at entry; exact row membership and RNA owner identity
are still checked at every property access. Input performs its own full checks.

RNA binding reads now validate and read the same resolved owner in one access.
No owner is cached across accesses. Replaced/removed owners, missing properties and
readonly properties still fail closed. Custom `get` or `valid` overrides disable
the combined path and use the original binding contract.

The angle-row consumer also supplies `draw_item_texts` for its captured-angle and
live-value labels. The shared tape patches only changed text commands, instead
of recording the row's style and controls again. This retains fixed-width
geometry and active edits; intrinsic/wrapped labels still invalidate layout.
The full callback contract is documented in `REGISTERED_LISTS.md`.

The first consumer opts in only its main and Linking panels. `CamKeys/ui_revisions.py`
lists their authored dependencies, and the tracked-object list supplies its own
row revision. Other panels retain ordinary authoring until their dependencies are
explicitly described. Any new conditional or captured owner in an opted-in panel
must extend its key and correctness tests.

Evidence is recorded in the follow-up performance report. The focused runtime
fixture checks moving-viewport live labels without panel authoring, falloff/help/
distance branches, selection, same-size reorder, deletion and camera-mode changes.
No backend-specific shader, bridge, native binary or visual setting changes are
part of this optimization.
