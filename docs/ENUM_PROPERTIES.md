# Enum properties

`Layout.prop` scalar enum fields and `Layout.prop_menu_enum` now open the same
custom menu used by context actions and menu shortcuts. Mouse clicks no longer
use the legacy unanimated overlay or reject a list taller than the viewport.
The menu retains BVT strong liquid glass, theme roles, 11-unit text, shared finite
spring motion and per-control animation settings. Its logical hit targets remain
stable during animation. The current value is checked and scrolled into view.

```python
ui = Layout(canvas, context=context, commit=commit_change)
ui.prop(settings, "mode")
ui.prop_menu_enum(settings, "channels")  # ENUM_FLAG also stays a compact menu.
ui.props_enum(settings, "mode")          # Expanded choices.
ui.prop_enum(settings, "mode", "FAST")   # One exact choice.
```

Enum menus admit up to 4096 choices, matching the existing dynamic-RNA adapter's
bound. Larger input fails explicitly instead of silently dropping choices.
Only up to 18 rows are painted, with clipping, wheel/trackpad scrolling,
Home/End, Page/arrow navigation and Enter selection. Escape, outside clicks and
right-click cancellation retain the shared menu contract. Descriptions use the
shared tooltip path. Right-click on a resting field or expanded choice still
resolves the exact property and, for expanded choices, its enum identifier.
Regular context menus keep their existing 64-entry admission bound.

## Grouping, modifiers and metadata

The v2 pass preserves enum headings and separators in the admitted dynamic-RNA
copy path. Headings are read-only, use the retained 12-unit title face, receive
menu opening motion, and are skipped by keyboard selection. Separators attach
to the following row. `props_enum` creates columns separated by named groups,
matching Blender's source structure. `prop(..., expand=True)` and flag `prop`
retain their expanded strip presentation.

Expanded flag strips select one flag on a normal click; Shift toggles the clicked
flag without disturbing others, including clearing the final flag. A normal
click on the sole selected flag leaves it selected. Individual `prop_enum`
buttons, `props_enum` entries and explicit menu entries toggle their own flag.
Those are distinct Blender code paths; a universal Shift rule would be wrong.
Menu selections still close. Context-dependent multi-choice persistence has not
been qualified and is not claimed as a newly completed feature.

`Layout.enum_item_name`, `Layout.enum_item_description`, and
`Layout.enum_item_icon` are now available as class methods. They resolve current
items using the existing item adapter, return translated name/description or the
numeric icon ID, and return empty text/zero for missing identifiers or unsuitable
properties. Their static and dynamic results match native methods in the tested
runtimes. Returning an icon ID does not yet implement every custom icon drawing.

The optional separator-copy change retains existing ABI structs, allocation
ownership and exact build/platform admission. The adapter's reviewed source
fingerprint is updated. **Public-RNA fallback omits structural rows** on tested
runtimes: choices and static metadata still work, but heading/separator parity
is not qualified there. `hosts.menu_native.reason()` exposes unavailable native
admission; no native UI is drawn as a fallback. Expanded orientation, wrapping,
specialized tabs and all keyword combinations still need broader qualification.

## Transactions and dynamic choices

The library snapshots choices at layout construction and again when opening a
menu. Current labels are retained in a lookup table; painting does not explicitly
request the full item list. Ordinary RNA value reads still occur and Blender may
invoke an enum callback internally for those reads. This is not a promise that
all Python enum callbacks are absent from a paint-facing RNA getter.

Selecting rechecks the owner, captured property value, candidate identifier and
numeric enum value. Removal, numeric remapping or concurrent property edits
reject the old choice. Renaming an unchanged identifier/value refreshes its label
on reopening. Dynamic callbacks must be read-only, as in native RNA UI. Refresh a
closed control's labels by rebuilding the layout after external label changes.
Expanded groups resolve the full list once per build, rather than once per button.

Scalar and expanded choices now share a transaction: preserve the authoritative
old value, write, verify setter acceptance, and commit once only for a real change.
A setter/commit failure restores the old property when the binding remains valid.
Flag-menu choices toggle their own identifier while preserving other flags;
commit receives real old/new sets. A menu action closes the menu; selecting an
already-selected scalar is a no-op. Callback side effects outside the property
remain host-owned and are not an atomic general scene transaction.

```python
# Explicitly refresh labels without rebuilding the control:
control.options["enum_field"].snapshot()
# Schedule a normal host redraw afterward; no polling timer is installed.
```

Dynamic enum evaluation uses the existing exact-build admitted adapter on macOS
arm64 Blender 5.1.2 and 5.2.2. It adds no new private ABI access. Other builds use
the existing public `enum_items` fallback. If that fallback cannot expose dynamic
choices, opening fails explicitly with `canvas.menu_error`; it does not guess or
use a native widget. Static fallback behavior remains available for Blender 4.2.
No 4.2 executable is installed for this validation.

## Searching long menus

Dropdowns with 12 or more options now use the shared pinned search field.
Type to match option labels and group names; arrows/Enter choose the original
option. Filtering makes no property writes. Escape/right-click clears the query
before returning or dismissing. [Search behavior and configuration](MENU_SEARCH.md)
and [QA evidence](design/qa/menu-search-v1/index.html) cover enum and general menus.

## Evidence and open parity

[Enum QA v2](design/qa/enum-properties-v2/index.html) contains actual Blender
implementation captures, motion GIF, source hashes, before/after performance
records, and runtime/window input results. Existing menu artwork/geometry is
reused; captures are not newly approved generated references. All new enum
surfaces are captured at 1×, 1.5× and 2× beside ordinary panel controls.

Still open: context-dependent multi-toggle menu persistence; full custom icon
variants and grouping on unqualified adapters; fuzzy popup ranking; specialized tab highlights and full focus traversal;
complete translation/keyword combinations; native callbacks on unqualified
platforms/builds; exact generated-reference and all theme/display/platform
acceptance. `prop_tabs_enum` retains the expanded strip route; its
specialized tab semantics are not complete. These changes close discrete enum
interaction/transaction gaps, not full UILayout or enum API parity.


Operator-backed choices now have their own [custom action/menu path](OPERATOR_CHOICES.md).
They execute an operator with a selected enum argument; property enums retain
their existing binding and transaction semantics.
