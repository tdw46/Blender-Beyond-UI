# Custom collection lists

`Layout.template_list("UI_UL_list", ...)` now renders custom default, compact and
grid lists. This is a partial implementation of Blender's list template, not full
UIList parity. [Production captures and motion](design/qa/collection-lists-v1/index.html)
remain available for Tyler's visual QA. No new generated reference or exact match
is claimed for this composition of the existing source controls.

## Using the template

```python
ui = Layout(context=context, commit=host_commit, state=host_ui_state)
ui.template_list(
    "UI_UL_list", "objects", context.scene, "objects",
    host_settings, "active_object_index", rows=5, maxrows=12,
)
```

The active property must be a scalar RNA integer; the source must be an RNA
collection. The default list requires a nonempty `list_id`. State is scoped by
list type and ID in the host-owned `Layout.state` dictionary. Use different IDs
for independent list views. Add/remove/reorder operators remain the host's job.

PropertyGroup collections require a stable identity function:

```python
ui = Layout(
    context=context, commit=host_commit, state=host_ui_state,
    list_identity=lambda owner, property_name, item: item.stable_uuid,
)
control = ui.template_list(
    "UI_UL_list", "layers", settings, "layers", settings, "active_layer",
)
```

The host must create unique, immutable keys when creating its items, never reuse
them for replacement items, and preserve them through rename/move. Keys must be
hashable. Duplicate keys reject authoring/refresh. This library never adds hidden
properties or UUIDs. The hook propagates through nested layouts and panel popovers.

Blender's PropertyGroup collection `move()` can exchange item contents while
retaining their slot addresses. RNA pointer equality alone is insufficient.
Missing host identities fail explicitly for these collections. Other collections
use public RNA identity by default; supply the same hook for any host collection
whose storage can replace a row at an existing address. Snapshot index **and**
identity are rechecked before selection, rename and deferred menu actions.
Deletion of the owning ID invalidates the guarded resolver before item access.

## Interactions

- First click selects the original collection index. Ctrl-click or double-click
  on the active row starts name editing. Enter commits through the host; Escape
  or right-click cancels without changing the name. A rejected host commit rolls
  the property back. Selection and rename are distinct transactions.
- Arrow, Home/End and Page Up/Down keys navigate visible ordering while writing
  original indices. Compact lists provide previous/next buttons and wheel input.
  Grid columns shrink with available width without enlarging body text.
- The filter disclosure opens a wildcard search plus source toggle switches for
  inversion, alphabetical sorting and reverse ordering. Ctrl/Cmd-F opens search
  for a focused noncompact list. Search cancellation restores the original query.
  `sort_lock` hides/disables ordering controls. `sort_reverse` initializes state.
- The scrollbar supports wheel, trackpad, paging and drag; right-click cancels
  an active drag. The footer handle resizes between `rows` and `maxrows`, within
  the explicit 128-row admission bound. Zero rows means the five-row default.
- Right-click/keyboard menus retain the exact row name property, including Copy
  Full Data Path and host contributions. Empty/scroll/filter regions expose list
  search, refresh, scrolling and boolean filter actions. Disabled rows permit
  read-only property actions; selection/rename obey the control's enabled state.

After external collection/name changes, rebuild the layout or call
`control.options["widget"].refresh()` on host invalidation. No polling timer or
collection-wide comparison runs during drawing. Another view's rename becomes
visible on its next refresh; views share the active index but retain independent
filter/scroll state.

## Rendering and cost

The list consumes the host's existing backdrop/blur, theme roles, font policy,
motion ancestry and finite animation scheduler. Filter switches use the shared
BVT switch painter. Geometry changes keep the backdrop and active springs.
Global disable/zero strength overrides per-control animation settings.

Name/identity snapshots are built on authoring/explicit refresh, with a hard
100,000-item admission bound. Filtering and sorting operate on those snapshots
on input. Drawing is proportional to the visible cells, not collection length;
it reads only the shared active-index property. It does not invoke RNA collection
iteration, list draw/filter callbacks, capture, blur, file I/O or timers. Hit
testing also visits only visible rows. Long names use clipped text; active editors
show selection/caret and keep the keyboard caret in view.

## Open parity and acceptance gates

Registered Python `draw_item`, `draw_filter` and `filter_items` callbacks now
have a [bounded custom implementation](REGISTERED_LISTS.md). Native-only callbacks
and the limitations listed there remain open, as do `item_dyntip_propname`, native data-type icons,
drag/drop reordering, native compact count/index presentation, automatic height
heuristics, mouse caret placement/selection, full focus traversal/accessibility,
and Blender's context-specific UIList operators. Unsupported parameters fail
before adding a control. Read-only/nameless collection presentation and the full
theme/platform matrix need further qualification. The API accepts bounded rows
and columns rather than silently accepting extreme allocations.

The 4.2 compatibility path remains intact, but this pass executes only installed
macOS arm64 Blender 5.1.2 and 5.2.2. No Windows or Blender 4.2 execution is claimed.
The 137-member ledger still contains unimplemented controls, partial behaviors
and open reference acceptance. Native forwarding does not close those gaps.

## Official evidence

The [4.2 UILayout reference](https://docs.blender.org/api/4.2/bpy.types.UILayout.html)
defines the template signature and mandatory default-list ID. The
[5.1 UIList reference](https://docs.blender.org/api/5.1/bpy.types.UIList.html) and
[5.2 UIList reference](https://docs.blender.org/api/5.2/bpy.types.UIList.html) define
original-to-display order mapping. The
[5.1 List View Manual](https://docs.blender.org/manual/sr/5.1/interface/controls/templates/list_view.html)
documents selection, rename, resize and filter interactions (that versioned page
served English content). Exact English 4.2/5.1/5.2 Manual and 5.1/5.2 UILayout
opens were attempted but unavailable through the documentation fetcher; those
failed fetches are not treated as evidence. Immutable official source at v4.2.0,
`ec6e62d40fa9`, and `d13f752e3b9c` was inspected instead, including the default
row/filter implementation. URLs/hashes are retained in the
[source audit](design/qa/collection-lists-v1/source-audit.json).
