# Pointer properties and animation decorators

`Layout.prop` supports custom ID pointer fields and named non-ID pointer fields
with explicit host policies. Clicking opens the existing
searchable Data Picker as a popover with the shared BVT strong liquid glass,
active-theme colors, title font and finite squash/stretch animation. Search,
virtual scrolling, Home/End, arrow/Page navigation and Enter select an exact candidate. Type immediately after opening to filter;
a rejected commit keeps the text editor open for correction.
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
candidates on opening, then revalidates the owner, original value, candidate membership,
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

## Non-ID pointers and collection-owned properties

Named RNA targets such as `Bone` and `Node` now share the same field and popover.
Collection wrappers such as `armature.bones` and `node_tree.nodes` can own the
bound `active` property. Their binding identity uses the containing ID, RNA path
and collection type; normal struct bindings retain their pointer identity.
Copy Data Path / Copy Full Data Path use the exact collection property path.
The shared host `context_provider` receives that exact binding owner. Blender's
public `temp_override(button_pointer=collection)` converts the wrapper to a list:
native `UI_MT_button_context_menu` callbacks requiring a struct owner are not
qualified for collection-owned fields. Supply those contributions through the
host provider; native callback parity remains open and is recorded in the tests.

Non-ID targets require an explicit `PointerItems` policy, a `revision` callback
returning an immutable generation token, and a `transaction` context-manager factory. Increment it after structural
edits, removal/replacement, mode changes that recreate RNA wrappers, undo/load,
or other host changes that invalidate candidate identity. Rebuild bindings after
undo/load as usual. The callback must be read-only and cheap; it is checked for
visible-row validity. It must not scan collections, allocate GPU resources or
perform I/O.

```python
generation = 0  # Owned by the consuming extension's lifecycle.
ui = Layout(canvas, context=context, commit=commit_change,
    pointer_sources=lambda owner, name: PointerItems(
        lambda: node_tree.nodes,
        poll=lambda owner, candidate: candidate.id_data == node_tree,
        revision=lambda: generation,
        transaction=host_pointer_transaction))
ui.prop(node_tree.nodes, "active", text="Active Node")
ui.prop_search(node_tree.nodes, "active", node_tree, "nodes", text="Find Node")
# After a structural edit, advance generation and cancel/reopen affected popovers.
# After undo/load, rebuild the layout/bindings too.
```

`transaction(owner, before, after)` returns a context manager that snapshots the
setter's related state before yielding and restores that state on an exception,
then re-raises. The library restores the bound pointer first, while still inside
the context. This hook is also available for ID policies. It must not suppress
errors or delete data needed for rollback. The host owns the full setter/undo
contract: active-bone setters can change selection flags, and active output-node
setters can change other nodes' output flags. A pointer-only snapshot is not a
complete transaction for those cases. The supplied tests exercise public Bone
fields and Value-node selection state; hidden legacy bone flags and every
specialized node setter remain unqualified. Those cases require a host adapter
with suitable restoration or an explicit unsupported policy.

Opening records the candidate sequence, owning IDs, types, names and host
revision. Selection and candidate Copy Name recheck that snapshot and membership;
renames, reordering or deletion require reopening. Clear also checks the captured
revision. Revision checks reject identical-label/address replacements that a
public-RNA snapshot alone cannot detect. The host remains responsible for updating
the revision and supplying the real property poll. Ordinary pointer selection
also now revalidates membership before Copy Name, and propagates rejected commits
to the editor. Paint-facing reads never enumerate candidates.

The same support applies to compact and full-card `prop_search` and
`template_search`. Search uses the collection type's public RNA name property
when no explicit name override is given, with a capability fallback to `name`.
Special Action-slot naming and all native name/icon variants remain open.
[Non-ID pointer QA](design/qa/non-id-pointers-v1/index.html) includes Bone/Node
execution, actual window input, 500-node captures, retained-resource measurements
and ID-control regression evidence.

## Decorators

`prop_decorator(owner, name, index=-1)` renders empty, keyed, changed, animated
elsewhere and driven states. Standalone vector/array calls now expand into a
vertical tuple of compact component decorators. Color/color-gamma/direction
properties retain one aggregate decorator, following native expansion rules. Scalar/indexed properties use their exact RNA path.
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

Open parity includes unnamed/nonassignable non-ID targets and broader non-ID
collection/version coverage; unexposed native polls without host adapters;
eyedropper, drag/drop, previews and ID-specific creation/duplication actions;
full keyboard focus traversal; `index=-2` and remaining specialized decorator layouts;
NLA time remapping, multi-layer blending, modifiers and all animation variants;
all prop keyword combinations, themes, DPI and platform coverage. New visuals
have not been matched to an approved generated reference. These remain **partial
implementations**, not completed custom Blender API parity.
