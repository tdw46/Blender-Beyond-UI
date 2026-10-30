# Custom panel popovers

`Layout.popover`, `prop_with_popover` and `popover_group` now use registered Python
Panel definitions to build retained custom canvases. The Panel proxy exposes
Blender's `is_popover` flag. Beyond UI also provides a convenience
`Layout.is_popover` flag that propagates to layout children; that helper is not a
Blender UILayout API member or an extra ledger completion. The three API entries
remain partial; complete UI and visual parity is not established.

```python
ui.popover("MYEXT_PT_settings", text="Settings")
ui.prop_with_popover(context.object, "display_type", panel="MYEXT_PT_display")
ui.prop_with_popover(context.object, "color", panel="MYEXT_PT_color")
ui.popover_group("VIEW_3D", "UI", "", "My Extension")
```

The consuming extension owns Panel/operator registration, context, undo and
property commits. Importing the library does not install timers, register RNA,
mutate scenes or compile code.

## Drawing and ownership

A panel's Python draw callback authors the current custom Layout once on opening.
It can use the implemented sliders, switches, fields, enum controls, menus,
pickers, specialized editors, rows, columns and grids. Unsupported draw calls
reject the popup instead of leaving partial controls. Python helper methods are
supported through a proxy with `is_popover=True`.

Header callbacks author controls beside the opener, as in Blender's panel-button
API. Header failure rolls back only the new controls/groups. Header and body
controls retain their original panel definition, draw callbacks, owning context
and parent eligibility. Input rechecks poll and ownership before edits and
operator execution; stale deferred actions also reject execution. Unregistering
or replacing a definition requires rebuilding its controls.

Enum and color property popovers expose the original `button_pointer` and
`button_prop`. Their custom closed fields continue to display current property
values. Ordinary panel buttons clear stale native-button context. Context
pointers, strings, host commit callbacks, pointer-source policies and ID-action
dispatchers propagate into panel contents.

`popover_group` snapshots registered Python Panel subclasses on authoring,
filters exact space/region/context and optional category, excludes subpanels,
checks poll and orders by `bl_order` with discovery order for ties. Discovery is
bounded at 4096 classes and 256 matching openers. It never scans the registry in
painting. Full native region-list registration order is not claimed.

## Shared appearance and input

Panels open through `Canvas.open_widget`, with widths derived from
`bl_ui_units_x` in host logical units and clamped to the host clip. Vertical and horizontal attachment use the same
central opening path, including on older runtimes without the native direction
keyword. Controls keep
the host's font and row scale; narrow layouts reflow and short layouts scroll.
The scrollbar supports dragging, wheel input and right-click top/bottom actions.
Painting culls clipped controls before binding reads.

Every panel uses the host's retained liquid-glass backdrop and stronger menu blur.
The resolved active-theme palette is passed into nested canvases, preserving
user-authored colors and avoiding another theme scan for each child. There is no
per-panel capture, blur producer, font load or shader compilation during painting.

Opening motion transforms the entire child canvas, including text and nested
controls. Individual controls retain their existing source motion. Parent/host
animation disable and strength apply to existing children; wide numeric controls
retain the 15% amplitude rule. One host scheduler advances child animations and
stops when they settle. Invalidation and teardown cancel child edits, menus,
animations and tooltips.

Property, operator, picker and menu context actions retain their exact clicked
owners inside popovers. The host finds nested menus for tooltip scheduling and
input priority. Escape dismisses the current edit/menu/nested panel before its
parent. Outside right-click dismissal passes the event through. Popover opening
is also available through the shared context-menu and shortcut routes. Child
canvas shortcut bindings are scoped to the current opening and released on
dismissal without removing a newer binding that replaced them. Native operator
shortcuts retain their existing semantics. Persistent custom-canvas shortcuts
across reopened panels require explicit stable host command identities; they
are not inferred from row positions or labels.

## Remaining gaps

This does not implement unsupported Layout methods inside a Panel. C-only draw
callbacks, helpers requiring native Panel instances/custom data, automatic
subpanel expansion, pinned/instanced panel behavior, preview icons, icon-only
property presentation, and complete focus/accessibility traversal remain open.
Group discovery does not enumerate native-only panels. Poll-derived opener
availability updates on authoring and pointer/input events, not an idle poll loop;
changes without input require the consuming host's normal UI invalidation.

Generated-reference acceptance, light/custom-theme visual QA, Blender 4.2 runtime,
other platforms and full source-speed qualification remain open. Existing BVT
controls are reused; there is no newly approved generated reference for this
composition. Tyler owns visual validation.

## Evidence

[QA gallery](design/qa/panel-popovers-v1/index.html) contains actual Blender
5.1.2/5.2.2 frames at 1×, 1.5× and 2×, nested glass, context menus, narrow/scrolled
panels and disabled motion, plus the README GIF. Capture checks compare native
text batching with standalone text and count draw/poll callbacks and retained
resources. These checks do not establish exact-reference acceptance.

The [4.2 UILayout API](https://docs.blender.org/api/4.2/bpy.types.UILayout.html),
[5.1 Panel API](https://docs.blender.org/api/5.1/bpy.types.Panel.html) and
[5.2 Panel API](https://docs.blender.org/api/5.2/bpy.types.Panel.html) supply the
public API baseline. Exact versioned English Manual and 5.1/5.2 UILayout fetches
were unavailable; immutable official 4.2.0 and installed-build source revisions
are recorded in the [source audit](design/qa/panel-popovers-v1/source-audit.json).
Installed runtimes are tested in disposable profiles. No unrelated live Blender
scene or preferences are saved.
