# Registered collection lists

`Layout.template_list` can now execute a registered **Python** `UIList` through
retained custom row and filter canvases. This extends the [default list
contract](COLLECTION_LISTS.md); it does not claim complete UIList parity.
[Actual Blender captures and motion](design/qa/registered-lists-v1/index.html)
are available for Tyler's QA. Existing BVT fields, switches, menus and glass are
reused; no new generated reference or exact visual acceptance is claimed.

## Host integration

Register the UIList and its RNA data in the consuming extension as usual. Pass
its registered type name to `template_list`, and provide `Layout.list_identity`
for PropertyGroup collections. Host keys must remain unique and immutable across
rename, moves and replacements. The library does not register RNA, add item keys,
install a timer, save preferences or choose the host's undo policy.

```python
class MY_UL_layers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_property, index=0, flt_flag=0):
        layout.prop(item, "name", text="")
        layout.prop(item, "enabled", text="Enabled")

ui = Layout(context=context, commit=host_commit, state=host_ui_state,
            list_identity=lambda data, prop, item: item.stable_uuid)
control = ui.template_list("MY_UL_layers", "layers", settings, "layers",
                           settings, "active_layer", rows=5, maxrows=12)
```

Callbacks receive the original owner, item, active owner/property, index and
filter flag. They draw into the library's supported `Layout` surface; native
widgets are never silently substituted. First click selects an inactive row;
active rows route input to their authored fields. DEFAULT, COMPACT and GRID share
this contract, and `self.layout_type` allows different callback compositions.
COMPACT has one active row and no filter area.

`draw_filter` can author the standard filter properties and simple registered
scalar settings on `self`. State lives in the host's `Layout.state` dictionary,
scoped by type and list ID. It is not a native UIList RNA instance or automatic
`.blend` persistence. String, boolean, bounded numeric and static scalar enum
settings are supported. Python helper methods on the class are available.
Callbacks must treat their settings and scene data as read-only while drawing.

`filter_items` runs on authoring, committed filter/data changes and explicit
refresh. Return empty arrays or one unsigned flag and a complete
original-index-to-destination permutation per source item. The show bit and
never-show bit retain their native meanings; custom bits reach `draw_item`.
Reverse ordering is applied after mapping. Before Blender 4.5, the adapter applies
native engine inversion; from 4.5 onward, the callback owns inversion. This is an
explicit version check backed by the versioned source audit. Without a Python
filter callback the default snapshot name filter/sort is used.

## Input, menus and lifetime

- Embedded text, switches and enum menus retain the existing custom input,
  exact-property actions, host commits, cancellation and shared motion. The
  active child keeps modal input even when the pointer crosses another row.
- Menus and popovers draw in the host clip after row bodies. They are not cut off
  at the row boundary. All use the same retained backdrop and theme roles.
- Ctrl/Cmd-F focuses the actual `filter_name` field in a custom `draw_filter`.
  If that callback omits the field, search fails explicitly. Right-click cancels
  an edit before opening a menu. Custom list settings expose reset/copy actions;
  they do not invent scene data paths or host undo transactions.
- Source identity, original item index, owner availability, callback identity,
  registration and context are checked on input. A moved/replaced row cannot
  redirect a pending edit **or its rollback** to a replacement item.
- A callback failure faults the list and cancels interaction. Refresh/rebuild is
  required. Invalid visible callbacks fail atomically before the parent control
  is added; deferred rows are checked as they enter the viewport.
- Disabling/hiding the owner cancels child interaction and clears owned caches.
  Teardown releases scoped shortcut tokens. Rebuilding a same-owner property
  field transfers its existing spring; global motion disable still wins.
  Changing `Canvas.wide_numeric_motion_scale` updates existing row canvases.

After external data or callback changes, invalidate/rebuild the host layout or
call `control.options["widget"].refresh()` as appropriate. Registration changes
require a rebuild; refresh does not silently adopt a different class.

## Bounded work

Only viewport rows are authored and retained. Callback invocations happen outside
painting. Warm painting performs visible binding/owner checks, never callback
execution or a full collection scan. Host identity resolvers must be constant
time. Schema invalidation updates a retained composite registry so ordinary
canvases avoid additional full-control scans for list animation/menu lookup.

Admission bounds are 128 controls per callback, 4096 controls across visible
rows, 128 metadata lookups, 100,000 source items and 128 rows/columns. Each row is
one 32-logical-unit field line inside a 36-unit slot; a custom filter may be at
most 480 units high. These are explicit resource limits, not claims of unrestricted
native layout equivalence. Body fonts stay at 11 logical units and scale with the
host; wide/narrow and 1×/1.5×/2× captures retain normal control scale.

## Remaining gaps

Native-only callbacks, callback-backed setting get/set/update functions, dynamic
enum settings, array/flag settings, native UIList persistence, writes to proxy settings during callbacks,
nested lists, multiline/oversized row content and unsupported `Layout` calls are
rejected explicitly. Callback icons currently receive `0`; native data-type
icons and `item_dyntip_propname` remain open. Drag/drop, full focus traversal,
accessibility, compact count presentation, automatic height heuristics, mouse
caret placement and Blender's context-specific UIList operators remain open.
External dependent data requires host invalidation rather than polling.

The public API ledger still reports **86 unimplemented / 51 partial /
0 reference-matched** UILayout members. This closes part of `template_list`'s
behavior, not its full completion gate. Blender 4.2 execution, Windows, the full
theme matrix, exact generated-reference acceptance and source-equivalent
performance qualification remain open.

## Evidence

The official [4.2 UIList API](https://docs.blender.org/api/4.2/bpy.types.UIList.html),
[5.1 UIList API](https://docs.blender.org/api/5.1/bpy.types.UIList.html),
[5.2 UIList API](https://docs.blender.org/api/5.2/bpy.types.UIList.html) and
[5.2 List View Manual](https://docs.blender.org/manual/nb/5.2/interface/controls/templates/list_view.html)
were searched. Some direct versioned fetches were unavailable; failed requests
are not treated as evidence. The [source audit](design/qa/registered-lists-v1/source-audit.json)
records official immutable source URLs/hashes for RNA callback arguments, flags,
order mapping and the pre-4.5 inversion transition, including both installed
builds. Execution uses disposable macOS arm64 Blender 5.1.2 and 5.2.2 profiles.
