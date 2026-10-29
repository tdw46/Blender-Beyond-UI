# Collection search properties

`Layout.prop_search` now draws a compact field showing the bound value. Click it
to open the shared Data Picker with strong liquid glass, active-theme colors,
virtual scrolling, keyboard navigation and the source spring. Type immediately
to filter; Enter selects a result or submits an enabled string suggestion.
Successful selection closes the owned popover; rejected commits preserve the
edit for correction. Escape, right-click during an edit, or an outside click
cancel without changing the property. Right-click on a resting field or candidate
uses the shared owner-aware menu. It supports RNA string
properties searched against an RNA collection, and supported ID or named non-ID pointers searched
within an explicit collection. `template_search` inherits the same selection
validation; its optional New/Unlink operators remain consumer-owned.

```python
ui = Layout(canvas, context=context, commit=commit_change)
# Optional library setting, inherited by child layouts:
# ui.search_popovers = False  # Retain the full-card presentation.
control = ui.prop_search(settings, "bone_name", armature, "bones", text="Bone")

# Arbitrary string input is an explicit opt-in:
control = ui.prop_search(settings, "tag", settings, "tags",
                         results_are_suggestions=True,
                         item_search_property="display_name")
```

`item_search_property` must name an RNA string on non-ID collection items. The
keyword is capability-gated against the runtime UILayout signature; Blender 4.2
continues using RNA default names and rejects this newer optional keyword explicitly.
ID collections use their actual names, as in the audited native implementation.
Unknown pointer polls still require `Layout.pointer_sources` / `PointerItems`;
merely supplying a search collection does not bypass the pointer's candidate policy, poll or type.
Named non-ID pointers are supported with explicit candidate/poll policies and a
mandatory host revision and transaction callbacks; see [non-ID pointers](POINTERS_AND_DECORATORS.md#non-id-pointers-and-collection-owned-properties).
String searches over non-ID collections remain supported without pointer policies.

Closed compact fields read only their current bound value: they do not build or
scan the candidate collection. Candidate snapshots are built when opening the
popover. Per-control animation enabled/strength settings also apply to the open
popover; disabling motion leaves glass enabled. The explicit full-card mode
retains eager snapshots and the previous presentation. The presentation setting
applies when building controls; rebuild the layout to switch existing controls.

Selecting a row rechecks the property owner, original bound value, collection
owner, candidate membership and pointer poll before writing. Host commit runs
once after a successful value change, with the same rollback behavior as the
pointer field. Failed selection preserves a pending typed edit for correction.
A candidate's right-click menu targets that candidate with Select and Copy Name;
search/header actions retain the exact property owner. Read-only fields retain
inspection actions while mutation is disabled.

Non-ID collection elements do not provide ID-like lifetime guarantees: removing
one can shift elements into the same address. The model therefore compares the
captured ordered address/name signature with the current collection before row
selection or copying. Changes require an explicit refresh. This rejects stale
row actions instead of silently choosing a shifted element. An ID candidate can
be renamed without changing identity; non-ID renames require refresh too.

```python
# After host-owned collection edits, membership changes or label changes:
control.options["widget"].refresh()
# After undo/load, rebuild the layout/bindings using the host's normal lifecycle.
```

Refresh cancels this search's pending text/capture/focus and context menu before
replacing its snapshot. Hosts must refresh after structural edits, including
replacement with identical labels/addresses that a public-RNA snapshot cannot
distinguish. Host `Layout.resolve` can reacquire the collection owner; replacement
with a different identity is rejected. No polling loop is installed.

With `results_are_suggestions=False`, Enter requires a matching result. With it
true, Enter in the search editor can commit arbitrary text; arrow navigation
selects a specific result instead. Escape/right-click cancel typed search without
writing the bound property. Suggestions are strings only and never create data.
Filtering and candidate snapshots run on input/refresh. Full membership/signature
validation runs on actions, not painting. Current-selection lookup is cached and
visible-row painting is virtualized. Row background, icon and label now share
one squash/stretch transform, including keyboard-selected rows. Toolbar icons
use the same finite motion; resting geometry is unchanged.

## Evidence and limits

[Search QA v1](design/qa/collection-search-v1/index.html) contains actual Blender
captures, a before/after row-motion comparison, real-window input results and
source hashes. The runtime cases cover 500 custom collection items; rendering
uses 503 ID candidates plus three decorators. On Blender 5.1.2 and 5.2.2, tests
cover renamed/removed items, concurrent edits, failed commits, custom labels,
suggestions, pointer filtering, refresh cancellation and exact context targets.
Paint-facing reads are checked for zero collection iteration. The old/new resting
renders are identical and native-batched text matches standalone submissions.

[Compact search QA](design/qa/search-popover-v1/index.html) adds actual-window
opening/typing/selection/cancellation checks, 503-candidate preparation timings,
and 100 native-batched/unbatched animation frames per runtime. The prior full-card
QA gallery remains unchanged; it is now selected with `search_popovers=False`.

This remains partial API parity. Open gaps include unnamed/nonassignable pointer targets, native icons/previews, native fuzzy-ranking details,
all native RNA name-property variants (including Action-slot special naming),
drag/drop/eyedropper, complete keyboard focus traversal, all theme/DPI/platform
coverage and generated-reference acceptance. Blender 4.2 fallback has source
review; no 4.2 executable is installed here. Older galleries remain immutable.
