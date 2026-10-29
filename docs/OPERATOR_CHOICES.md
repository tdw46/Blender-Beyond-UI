# Operator choices

`Layout.operator_enum()` and `Layout.operator_menu_enum()` now have custom
implementations. They reuse the existing BVT buttons and searchable glass menus;
no native UI is opened as a fallback. [QA captures and animation](design/qa/operator-enums-v1/index.html)
cover grouped choices, 200-action search, expanded buttons, exact operator context
menus and motion disabled, at 1×, 1.5× and 2× on both tested Blender versions.

```python
ui = Layout(context=context)
ui.operator_context = "EXEC_DEFAULT"  # or the host's intended INVOKE_* context

# The consuming extension registers this operator and its enum property.
ui.operator_enum("my_addon.apply_preset", "preset")
props = ui.operator_menu_enum(
    "my_addon.apply_preset", "preset", text="Apply Preset"
)
props.amount = 0.5
```

`operator_enum` adds individual action buttons in the current group, with headings
and separators when the admitted RNA adapter supplies them. It returns `None`.
`operator_menu_enum` returns an assignment bag for additional operator arguments,
as the existing custom `operator()` method does. This is not a native
`OperatorProperties` instance and does not promise RNA introspection/default
getters. The selected enum value overrides that argument at execution. Enum flags
pass a singleton set; they are actions, not persistent property toggles.

## Choice and context ownership

Opening a popup snapshots its arguments, operator RNA identity, host/context
identity, active object, mode and selected objects. Dynamic choices are evaluated
with the supplied operator properties through the existing admitted scratch-RNA
adapter. Temporary keyconfigs are released in `finally`; no operator executes
while building, opening, searching, hovering or cancelling a menu.

Selection rechecks registration, `poll()`, context pointers, captured arguments,
the selected identifier and its numeric enum value. Removed/remapped items,
concurrent argument changes, changed active/selected owners and operator removal
reject a pending action. Dynamic callbacks must be read-only; scope/selection
changes during callback evaluation are also rejected. Expanded buttons evaluate
current context on activation and revalidate their originally displayed choice.
Rebuild a layout to refresh expanded labels and disabled/poll state.

Arguments use the existing bounded snapshot contract (512 nodes, depth eight),
including RNA pointer identity. Menus allow at most 4096 rows; selected-owner
snapshots also have a 4096-object limit and fail explicitly beyond it. The chosen
operator and consuming extension own their execution/undo semantics. This UI
layer cannot roll back arbitrary side effects from an operator that fails.

The popup button's right-click menu offers the same choices through nested menu
navigation. With a host `ShortcutRegistry`, **Shortcut to Open Menu** dispatches
back into this custom popup. Without that registry, the shortcut option explains
why it is disabled; it never binds a native operator popup instead.

Expanded choices use the shared operator context menu with the exact chosen enum
argument: command copy, supported favorites/shortcuts, manual/source and host
contributions. Context actions, nested actions and shortcut capture revalidate
before use. Pointer/string overrides retain the existing capability restrictions;
no new private ABI adapter is introduced. Right-click within an open choice menu
retains the source cancellation/back behavior.

## Rendering and performance

The opener is a normal shared glass button with the existing dropdown arrow.
Rows use existing menu typography, theme roles, stronger blur and opening motion.
Expanded buttons use the shared press/hover/release springs. Global/host/control
animation policy and teardown are unchanged. No new shader, font, blur producer,
permanent timer or renderer dependency was added.

Choice preparation and selection validation run outside painting. Availability
checks do not repeatedly enumerate choices on pointer movement; selected-owner
snapshots are only scanned when preparing or activating an action. Warm-paint
fixtures assert zero dynamic enum evaluations and no keyconfig creation. Long
menus retain the existing visible-row culling and input-only search filtering.

[Validation](VALIDATION.md) records actual operator-control timings and an
unchanged-workload shared-painter comparison against `adbe5d6`. This comparison
uses six ordinary buttons and a searchable 48-action menu on both revisions;
it does not imply the previous revision implemented these authoring methods.

## Compatibility and remaining gaps

Versioned 4.2/5.1/5.2 API and Manual URLs were requested, but the documentation
service was inaccessible. Signatures/return semantics were checked in exact
official Blender source: 4.2.0 and installed revisions `ec6e62d40fa9` / `d13f752e3b9c`.
The [source audit](design/qa/operator-enums-v1/source-audit.json) records URLs and
hashes. Installed 5.1.2/5.2.2 runtime fixtures verify the actual behavior.

Static enums retain the public-RNA fallback. Dynamic callbacks and structural
rows use the existing exact-build admission; when public RNA cannot expose
choices, opening fails explicitly. No Blender 4.2 runtime is installed here.
Other builds/platforms and complete theme/translation combinations remain open.

Icon-only expanded buttons and custom icon requests fail explicitly with
`UnsupportedControl` until their custom artwork/interaction path is implemented.
Full native `OperatorProperties` behavior, native grouping/orientation in every
parent layout, complete focus traversal, all operator invocation contexts and
exact generated-reference/motion matching remain partial. Existing shared
visual specifications are reused; captures are implementation evidence for
Tyler's QA, not new generated artwork or visual acceptance.
