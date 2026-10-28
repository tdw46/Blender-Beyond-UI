# Pointer properties and animation decorators

`Layout.prop` now supports custom ID pointer fields. Clicking opens the existing
searchable Data Picker as a popover with the shared BVT strong liquid glass,
active-theme colors, title font and finite squash/stretch animation. Search,
virtual scrolling, Home/End, arrow/Page navigation and Enter select an exact ID.
Escape dismisses; right-click retains the shared cancellation/context contract.

```python
from beyond_ui import Canvas, Layout, PointerItems

canvas = Canvas(menu_commit=commit_property_action)
ui = Layout(canvas, context=context, commit=commit_value_change)
ui.prop(context.scene, "camera", text="Camera")
ui.prop(context.object, "parent", text="Parent")
ui.use_property_split = True
ui.prop(context.object, "location", index=0, text="Position X")
# Or place a decorator explicitly:
ui.prop_decorator(context.object, "location", index=1)
```

Automatic pointer policies cover `Scene.camera`, cycle-safe `Object.parent` and
registered Python ID `PointerProperty` annotations whose type/poll metadata is
still available. Blender does not expose every built-in pointer's C poll through
public RNA. Those properties fail explicitly with `UnsupportedControl` until the
consumer supplies an authoritative policy:

```python
ui = Layout(canvas, context=context, commit=commit_value_change,
    pointer_sources=lambda owner, name: (
        PointerItems(lambda: bpy.data.meshes,
                     poll=lambda owner, candidate: owner.type == 'MESH',
                     allow_none=False)
        if isinstance(owner, bpy.types.Object) and name == 'data' else None
    ))
ui.prop(context.object, "data")
```

`items()` returns the current candidate collection; `poll(owner, candidate)` is
read-only and belongs to the consuming extension. The picker snapshots eligible
IDs on opening, then revalidates the owner, original value, candidate membership,
identity, target type and poll before assignment. A renamed candidate keeps its
identity; refresh the popover to update snapshot labels. Deleted/stale candidates
and concurrent property changes cannot redirect a selection. Nullable pointers
get None/Clear; absent create/duplicate actions remain visibly disabled. No data
creation or deletion is invented. Setter rejection and ordinary host commit
failures restore the old pointer when its binding is still valid.

Right-clicking the field acts on its exact RNA property. Right-clicking a
candidate exposes Select and Copy Name for that candidate, with host extensions
available through the shared provider. A host can add data-specific operations;
they must revalidate the row and provide their own undo policy. Pointer selection
uses `Layout.commit(before, after)` once per change. Do not delete the old ID in
a failing commit callback: deleted data cannot be restored by pointer assignment.

## Decorators

`prop_decorator(owner, name, index=-1)` renders empty, keyed, changed, animated
elsewhere and driven states. Scalar/indexed properties use their exact RNA path.
Click inserts a key or deletes the current key (including a changed keyed value,
as in Blender's decorator callback). A driven property opens the shared property
menu. Right-click and Shift-F10 use the same property/component target. A host
`Canvas.menu_commit(action)` callback is required to enable mutation; the existing
property action backend owns execution and the host owns undo. As with existing
animation menu actions, a callback failure after key/driver mutation is not an
atomic animation rollback.

When both `use_property_split` and `use_property_decorate` are true, scalar or
indexed `prop` controls receive a fixed compact decorator slot. Expanded vector
components inherit this behavior. `use_property_decorate=False` opts out.
Nonanimatable properties receive a disabled blank slot. This reserves the
alignment space; it does not implement Blender's complete split-label layout.
Wide numeric controls keep their 15% motion amplitude; decorators and picker
popovers retain the normal source amplitude. Global/host disable overrides
per-control settings, including open popovers.

Animation colors come from the active theme's `user_interface.wcol_state`
key/animated/driven/changed roles; missing roles use an observable fallback.
Channel lookup supports capability-gated Action slots/channelbags and the legacy
4.2 `Action.fcurves` path. Curves are cached on creation/invalidation and action,
slot or cached collection-count changes. Key lookup is binary rather than a full
key scan. Call `canvas.invalidate()` after external channel-path/topology edits;
rebuild bindings after undo/load. Hosts remain responsible for event-driven
redraws when frames, animation data or themes change. No polling timer is added.

## Evidence and remaining gaps

[QA v1](design/qa/pointer-decorators-v1/index.html) contains actual Blender output,
real-window input results and a README GIF. Public-RNA and window fixtures pass
on macOS arm64 Blender 5.1.2 and 5.2.2. The 4.2 legacy channel branch has a unit
fixture and exact source review, but no installed 4.2 execution. Official API and
Manual searches used exact 4.2/5.1/5.2 URLs; access failures were supplemented
with installed-runtime probes and exact official source revisions in the audit.
No minimum supported version, private production API or registration changed.

Open parity includes non-ID pointers; unexposed native polls without host adapters;
eyedropper, drag/drop, previews and ID-specific creation/duplication actions;
full keyboard focus traversal; `index=-2`/expanded standalone decorator layouts;
NLA time remapping, multi-layer blending, modifiers and all animation variants;
all prop keyword combinations, themes, DPI and platform coverage. New visuals
have not been matched to an approved generated reference. These remain **partial
implementations**, not completed custom Blender API parity.
