# Custom data-block templates

`Layout.template_ID()` and `template_ID_tabs()` now use the existing custom
fields, switches, buttons, searchable DataPicker and owner menus. These methods
never open native widgets. Their API ledger entries remain **partial**.

```python
from .vendor.beyond_ui import Layout

ui = Layout(context=context, commit=commit_property_change,
            id_actions=dispatch_id_action)
ui.template_ID(settings, "material", text="Material",
               new="my_extension.new_material", open="my_extension.open_material")
ui.template_ID_tabs(settings, "material")
```

Registered Python `PointerProperty` definitions retain their declared target type
and poll callback. Built-in pointers with unexposed C polls require the same
explicit `PointerItems` policy as ordinary pointer fields. No type-only guesses
are made about native pointer acceptance. `filter="AVAILABLE"` restricts Object
candidates to the current scene; `ALL` preserves the policy's candidates.

## Implemented behavior

- Searchable data-block selection with identity snapshots, input-time membership
  and poll checks, current owner validation and host-owned commits/rollback.
  Dot-prefixed names follow Blender's Show Hidden Files/Data-Blocks preference;
  a query starting with a dot reveals matching hidden items.
- A separate editable name field follows the selection at rest. Active edits and
  menus freeze their original owner. Changing selection closes a stale edit
  without writing or restoring its value into the replacement selection. The
  original owning ID is retained for validity checks before accessing embedded
  PropertyGroup RNA; deleting that ID disables every associated control.
- Real user count, Make Single User, Fake User and Unlink controls. Copying uses
  the ID's public copy API, leaves other users intact and clears the new copy's
  fake user. A failed host assignment removes the newly created ID only when it
  has no users. No force-unlink or global user remap is performed.
- New/Open/custom Unlink operator routes, with exact owner/selected-ID/property
  context and registration/poll checks at invocation.
- ID tabs reflect live selection and renamed labels. Input rechecks collection
  membership and polls; deleted tabs become disabled. Right-click offers exact
  selection/copy-name actions and host contributions. The selector, name, fake
  user and action controls also use shared owner-aware menus and shortcuts.
- Ancestor enable state, active-theme colors, shared liquid-glass backdrop,
  bounded source motion and host scale are inherited from existing controls.
  Selection changes require no control rebuild. Candidate enumeration occurs on
  construction/open/input, never in painting; tabs are bounded at 256 candidates
  with an explicit error beyond that limit. Use the searchable selector for
  larger collections.

## Safe operator dispatch

`Layout.id_actions` receives an `IDAction` with `operation`, `operator`, `context`,
`owner`, `property`, `selected`, `valid()` and `assign(value)`. A delayed dialog
must call `valid()` again before doing work. `assign` rechecks the original
selection and policy, then performs one host commit with rollback on failure.
The consuming extension owns operator side effects, file dialogs, cleanup and
undo policy. Disabling the authoring layout also invalidates delayed assignments.

Without a dispatcher, the library admits registered Python operators only and
supplies Blender's `id`, `template_id_ptr` and `template_id_prop` context keys.
The operator owns its transaction in this route. Built-in operators that depend
on an active native button remain disabled unless the host supplies an explicit
dispatcher: executing them against a different native button would be incorrect.
String context overrides use the existing exact-build native admission route;
unadmitted builds can use the host dispatcher without that ABI adapter.

For custom dynamic controls, `Binding.snapshot` can supply an owner-frozen binding.
Edits and ordinary context menus call `frozen()` once at opening. The snapshot's
validity must reject owner/selection changes; it must not retain an unsafe RNA
reference across undo/load. Plain bindings retain their previous behavior.

## Remaining gaps

Live ID preview icons, linked-library Make Local and override controls, packed
file Unpack, Shift-Unlink user clearing, native type-specific single-user side
effects, tab drag/drop and inline rename, registered tab-menu authoring, and
native button hiding/layout rules remain open. `live_icon=True` and a nonempty
`template_ID_tabs(menu=...)` raise `UnsupportedControl`. The user-count button
stays visible but disabled for zero/one real user. Object/Scene/Screen/WorkSpace,
linked, override and embedded IDs are not admitted for generic single-user copy.

This work does not implement `template_ID_preview`, `template_ID_session_uid`,
`template_any_ID`, asset browsers or the remaining specialized templates. No
complete custom-parity or exact-reference acceptance is claimed.

## Evidence

[ID template QA](design/qa/id-templates-v1/index.html) records actual production
Blender frames at 1×, 1.5× and 2×, narrow layouts, picker and owner menus, and
motion with native text batching. Tyler owns visual QA. The existing control
appearance is reused; there is no newly approved generated reference for this
composition. Exact-match acceptance remains open.

The public [4.2 UILayout API](https://docs.blender.org/api/4.2/bpy.types.UILayout.html)
and [5.2 data-block manual](https://docs.blender.org/manual/id/5.2/interface/controls/templates/data_block.html)
provide the documented API/behavior baseline. Direct English 5.1/5.2 API/Manual
fetches were unavailable in this session; exact installed-build official Blender
source was inspected instead. The [source audit](design/qa/id-templates-v1/source-audit.json)
records immutable source URLs and hashes for 4.2.0, 5.1.2 and 5.2.2. Runtime
fixtures use disposable profiles in both installed versions. No 4.2 executable is
installed, so 4.2 runtime qualification remains open; its API paths are retained.
