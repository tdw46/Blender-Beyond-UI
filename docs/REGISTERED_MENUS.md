# Registered custom menus

`Layout.menu`, `menu_contents` and enum `prop_with_menu` now author custom
controls from registered Python `bpy.types.Menu` definitions. They reuse the
shared BVT menu painter, liquid-glass backdrop, theme roles, host scale,
squash-and-stretch motion, search and context actions. Their parity entries
remain **partial**.

```python
ui = Layout(context=context, commit=commit_property_change)
ui.menu("MYEXT_MT_settings", text="Settings")
ui.menu_contents("MYEXT_MT_inline")
ui.prop_with_menu(context.object, "display_type", menu="MYEXT_MT_display")
```

The consuming extension registers the menus and operators, supplies the host
context and owns undo policy. Importing this library does not register RNA,
create timers, mutate scenes or compile code.

## Authoring and ownership

Dropdowns collect a registered Python menu's draw callback on opening or nested
navigation. The collector supports labels, separators, scalar property fields,
boolean switches, enum choices, operators, operator enum choices and nested
registered menus. `row` and `column` form vertical menu groups, with inherited
`enabled` and `active` state, including assignments made after authoring a row.
Python draw helper methods and appended draw callbacks are retained. Unsupported
calls abort the whole collection; they never leave a partially working menu.

`menu_contents` authors into the normal custom Layout, so its draw callback can
use the controls and layout geometry that Layout currently implements. Failed
inline authoring removes only its new controls and groups. It does not erase
existing controls. Recursive inline definitions and oversized menus fail
explicitly. Admission is 4096 root rows, 4095 nested rows plus Back, and three
nested levels; nested context actions share that depth budget.

Each pending menu retains its definition, draw callbacks, context pointers,
operator arguments and owning data. Execution rechecks registration, context,
owner identity, parent eligibility and applicable polls. Selection-sensitive
operator execution checks the original selection again. Original owning ID
wrappers are validated before embedded RNA is dereferenced, including ordinary
RNA bindings. Undo/load or owner changes require rebuilding stale controls.

`prop_with_menu` retains an enum property's display and exact property context.
Its registered menu receives `button_pointer` and `button_prop`; an ordinary
menu clears stale native button context. Operator context pointers, strings and
invocation mode are captured during authoring. String overrides retain the
existing exact-build ABI admission requirements.

## Input, menus and performance

Menu property rows support the shared field editor, switches, enum selection
and host commits with rollback. Right-click, the Menu key and Shift-F10 expose
exact-row property/operator actions; disabled rows can expose read-only actions
such as Copy Python Command. Back restores the parent and refreshes its values.
Right-click first cancels an active edit, and clicks outside owned bounds pass
through to Blender.

Long dropdowns use the existing search and scrolling behavior. Draw callbacks
run on opening/navigation, never painting. Operator polls refresh the visible
rows and the row being activated; offscreen shortcuts revalidate before running.
Opening/filtering snapshots all admitted rows once. Initial collection is bounded
but is not a lazy iterator over arbitrary host data. Inline context identity is
checked during rendering without invoking host draw/poll callbacks or entering
context overrides; input performs the full check.

All surfaces share the retained host backdrop and strong menu blur. This adds
no GPU producer, idle polling loop, per-control blur or timer. Motion settings
and the wide-numeric 15% amplitude rule remain those of the shared controls.

## Remaining gaps

This is not a complete `UILayout` interpreter. Dropdown rows are vertical;
`split`, grids, boxes, compound templates, custom preview icons and slider-style
property rows are not implemented by the dropdown collector. Use supported
inline controls where appropriate. Unsupported presentation calls raise an
error; accepted compatibility arguments such as emboss, alignment and separator
factor do not establish full native layout/presentation semantics.

C-only menu definitions and helpers requiring a real native RNA menu instance
are not admitted as custom widgets. Active-native-button operators require a
host-owned action and are rejected by the collector. Full icon coverage,
interactive tab menus, menu pies, hold menus, remaining [panel popover](POPOVERS.md)
behaviors, all templates and full
keyboard/accessibility equivalence remain open. Registered menus do not close
those separate API entries.

## Evidence and acceptance

[QA gallery](design/qa/registered-menus-v1/index.html) and its README GIF contain
actual production Blender frames at 1×, 1.5× and 2× on Blender 5.1.2 and 5.2.2.
The capture checks compare native text batching with standalone text for 360
motion frames and verify stable retained resources and zero menu draw/poll
callbacks during painting. Equivalent older workloads retain identical pixels.
These are execution and comparison checks; Tyler owns visual acceptance.

Existing BVT controls are reused. There is no newly approved generated reference
for this composition, and exact-reference acceptance remains open. Source-level
speed across all workloads, platforms and GPU completion timings is not established
by the recorded CPU submission samples.

The [4.2 UILayout API](https://docs.blender.org/api/4.2/bpy.types.UILayout.html)
provides the public API baseline. Exact 5.1/5.2 API and English Manual fetches were
unavailable during this work; the [source audit](design/qa/registered-menus-v1/source-audit.json)
records immutable official 4.2.0 and installed 5.1.2/5.2.2 source revisions instead.
Both installed runtimes execute the fixtures using disposable profiles. Blender
4.2 paths remain intact, but no installed 4.2 runtime was available for execution.
