# Core right-click audit — 2026-10-30

Full applicable right-click parity is **not complete**. This inventory replaces
the vague remaining-context-review item. Editor/template scope exclusions do not
remove these actions when their owning property or ID is exposed by an extension.

Evidence: exact-build Blender `interface_context_menu.cc` for 5.1.2
(`ec6e62d40fa9`) and 5.2.2 (`d13f752e3b9c`), retained under
`build/menu-adapters-audit/`. File hashes match the published
[`menu-native-audit.json`](../beyond_ui/hosts/menu-native-audit.json).
The exact-version API/Manual pages were requested but unavailable through the web
tool; no freshly fetched documentation or untested 4.2 behavior is claimed.

## Closed in this pass

- Contributed Reset, Copy to Selected and Copy Data Path now route through the
  captured property owner, without an active native button. Native RNA supplies
  supported argument defaults; component/all-array and full-path flags are
  honored. Unknown arguments and unavailable capabilities fail closed.
- Custom registered Python operators ending in `_button` are no longer rejected
  solely by name. Operator identity, polling, scope, arguments and unregister
  invalidation still apply.
- Background fixtures on both installed versions cover component/all-array
  operations, isolated clipboard paths, disabled inheritance, locked controls,
  rejected-commit rollback, deleted owners and unregistered operators.

The shared glass, theme and spring renderer is unchanged. Current production GPU
captures and human review are in [Core visual QA](design/qa/core-review-v1/index.html).

## Coverage and exact remaining gaps

| Native action family | Current custom support | Remaining work |
| --- | --- | --- |
| Reset / Copy to Selected | Exact scalar/component or whole-array owner, no-op suppression, transaction rollback; contributed `all` flags | Single/all alternatives exposed. Object, pose/data bone, node and object-data selections tested; unsupported nested selection domains remain explicit |
| Data paths | Exact component/full paths; readable on locked controls; contributed command support | No gap identified for supported RNA-backed fields |
| Keyframes | Insert/delete exact component or whole array at current subframe; dynamic removal availability | Replace wording at the current subframe and driven-property applicability implemented; clear-channel and single/all alternatives implemented |
| Keying sets | Add/remove exact component/all-array paths; active-set identity guard; create custom set if absent; rejected commit rollback | Built-in nonabsolute sets remain disabled |
| Drivers | Add/remove, exact-build clipboard, Copy as New Driver | Single/all driver copy to supported selected owners implemented with rollback. Existing visible-channel Graph/Drivers Editor routing implemented; new-window/native Edit Driver routing remains. Applicability and remove-all implemented |
| File/directory properties | Open File/Location with owning-library relative paths, stale-value and existence checks | OS opener dispatch is implemented; OS app launch intentionally not exercised by automated tests |
| ID selectors / search targets | Exact-ID Mark/Clear Asset with metadata rollback; Jump for visible objects and active-rig bones; root and candidate menus | Library override menu, hidden/excluded/cross-mode Jump and native asset preview execution qualification remain |
| Overridable properties | Define/remove simple REPLACE rules on exact scalar/component/all-array properties; restore linked values; transactional rollback; contributed native command mapping | Hierarchy-wide ID operations and complex flagged/collection rules remain unsupported |
| Custom property defaults | Scalar integer/float ID bindings support Assign Value as Default, Reset, paths, keys/drivers/keying sets, selected value/driver copies and decorators | Scalar ID-property clipboard/Favorites now qualified on admitted builds; numeric value shortcuts use host-owned registry with undo. Scalar custom Python button-menu contributions are now qualified on admitted builds; nonnumeric/array ID properties remain outside this implementation |
| Favorites and shortcuts | Exact-build Favorites, keyboard/mouse/chord capture, conflict/stale checks, custom dispatcher | Unsupported builds remain explicit limitations; pointer-scoped shortcut/favorite actions require host integration |
| Developer/help and host commands | Manual/API/source, operator command, public Python menu contributions | Other native-button-dependent contributed commands stay disabled until explicitly mapped |

The file/ID/override rows are conditional user-panel actions, not requests to
recreate Blender's file browser, asset editor or built-in Properties panels.
Graph/driver editor navigation should remain an explicit consumer action; drawing
a replacement editor is out of scope. Blender-specific special cases such as
Swap Render Dimensions are not generic panel-toolkit additions.

## Review queue

1. Animation/context semantics: keying sets, clear channels, component alternatives
   and relevant driver operations.
2. Conditional property/data actions: paths, search/ID targets and overrides,
   with exact owner and capability validation.
3. Visual follow-up: synthetic light-theme menu contrast over a dark backdrop,
   then Tyler's recorded core review feedback. Retain real glass and shared motion.

These are newly itemized defects, not newly requested scope. The old 1–7 turn
range understated this work. The overview records both completed work and the
specific estimate adjustment rather than silently declaring the audit complete.

## Animation/keying-set completion in the menu-design pass

Both 5.1.2 and 5.2.2 pass the new keying fixture: exact component paths, add-all,
repeat-add no-op, active-set invalidation, rejected removal restoration and
rejected new-set cleanup. Clear Keyframes removes the selected channel; all-array
alternatives preserve component semantics. Insert/reset-all and undo-required
regressions pass. Evidence is copied into `design/qa/menu-spacing-v1/report.json`.
Driver copying/editor routing and conditional data actions remain open.

## Animation applicability and selected owners — completed

Add Driver now rejects existing action channels (including other-frame/empty
channels) and existing drivers. Insert/Delete Keyframe reject driven channels;
Paste Driver rejects action channels. These checks run again before mutation,
including all-component actions. Menu construction uses Replace Keyframe wording
when the exact component has a key at the current subframe. Other components do
not incorrectly block single-channel actions.

Copy to Selected now resolves exact Object, PoseBone, Bone (from pose selection),
Node and selected object-data ID owners. It requires matching RNA owner type and
property shape, filters read-only targets, deduplicates shared datablocks and
re-reads selection before execution. Component rollback preserves sibling edits.
Arbitrary nested properties are not guessed by name; those selection domains
remain unsupported. Driver-copy and editor navigation are still open.

Ten background processes pass on 5.1.2/5.2.2, covering the new behavior, existing
context contributions, keying sets and transaction regressions. No renderer or
menu-metric changes; no new visual acceptance is claimed. Evidence:
[context selection runtime](design/qa/context-selection-v1/runtime.json).

## Driver copy to selected — completed

Shared menus now offer Copy Driver to Selected and Copy All Drivers to Selected,
using the supported owner domains above. The public RNA copy preserves the entire
FCurve, modifiers, driver expression, variables and their original target IDs.
Destination paths change to the exact selected owner; source variable targets
are not heuristically remapped. Existing destination drivers are replaced; keyed
destination channels and channels absent from the source are preserved.

The operation resolves current selection/capabilities at execution, requires host
undo, and rolls back every changed destination if the host rejects the commit.
Rollback preserves unrelated edits and removes newly created empty animation data.
Temporary copies are unlinked, input-only resources and are always released.
No OS/driver clipboard or private ABI is needed. Public new/remove tags dependency
relations around from_existing, whose implementation only copies the FCurve.
Evaluation and subsequent variable updates are verified. Contributed native
ui.copy_driver_to_selected_button commands use this same owner-aware path.

Six background runs pass across 5.1.2/5.2.2, including driver fidelity/evaluation,
transaction rejection, sparse all-channel copying, same-ID node paths, stale
channels and contribution argument/undo checks. Missing public-copy capability
disables this action on unqualified runtimes; no 4.2 execution claim is made.
Evidence: [driver copy runtime](design/qa/driver-copy-v1/runtime.json).
Editor/edit routing and the conditional file/ID/override/default actions remain.

## Conditional data actions and existing-editor routing — completed bounded routes

File/Directory properties now provide conditional Open File/Location actions.
Paths resolve with the owning ID's linked library, not process cwd. Nonexistent
paths and unsaved-file relative paths are unavailable. Owner/property/path changes
are checked again before dispatch through Blender's public path opener. Tests
intercept only the external launch, preserving real resolution and menu logic.

Pointer fields, pointer candidates and collection-search fields/rows expose
Mark as Asset and Clear Asset for the exact ID. Native capability polling uses
an explicit single-ID context. Host undo is required. Clear backs up the complete
AssetMetaData through the public copy setter; rejection restores tags, catalog
UUID, custom metadata and fake-user state, without overwriting unrelated edits.
Temporary unlinked IDs are removed. Preview generation is requested after accepted
marks in windowed Blender; that job was not exercised in this background pass.

Jump to Target supports visible objects in this view layer from Object Mode and
bones on the active pose rig, using capability-gated bone selection. Failed host
commits restore the prior selection/active owner. Hidden/excluded targets and
cross-mode switches are explicitly disabled; they are not silently approximated.

Single/all View in Graph Editor and View Driver in Drivers Editor use an existing
editor in the same window, correct mode and exact visible channels. They select
and frame the requested curves without a native button, filter mutation, focus
change or new window. Absent/filtered/stale channels disable routing. This is not
the native Edit Driver popup or new-window Drivers Editor route; those remain open.

Eight background processes pass on 5.1.2/5.2.2, including pointer/search/non-ID
regressions. All shared glass, bounce, theming and menu layout code is retained.
Evidence: [conditional action runtime](design/qa/context-data-v1/runtime.json);
[explicit limits](design/qa/context-data-v1/provenance.json).

## Library property overrides and scalar custom defaults — verified

Define/Remove Library Override now acts on exact editable user overrides, for
scalar, clicked component and all-array cases. Removing a component from a
whole-array rule creates sibling rules and restores only that component from
the linked reference. Rejected host commits restore rules and affected values;
unrelated sibling edits survive. Removed/changed rules, unavailable undo,
system overrides and non-reproducible flagged/collection rules fail closed.
Contributed ui.override_add_button/ui.override_remove_button honor their all flag
without invoking a different active native button.

Layout.prop(data, '["gain"]') and rna_binding accept scalar numeric ID properties.
Assign Value as Default updates their UI metadata, while Reset reads that default.
Metadata rejection restores only the default, preserving unrelated metadata/value
changes. Registered RNA storage is rejected by the custom path, never given a
fabricated editable default. Exact escaped/nested paths, selected value/driver
copies, animation decorators, keys/drivers/keying sets and stale key/type guards
share the existing controls and owner-aware menu machinery.

The native clipboard/Favorites adapter's admitted source hash had been invalidated
by a previous paste applicability guard. That guard now lives in the public
property dispatcher. The exact audited adapter bytes are restored and a checksum
regression protects admission. Actual clipboard/Favorites/shortcut tests pass on
both admitted builds, including rejection of Paste Driver over keyed channels.

Ten final runtime processes pass across 5.1.2/5.2.2 (eight headless, two windowed),
plus 249 pure tests and Ruff. Both final windowed launches had zero observed
activations and no focus restoration. Renderer, glass, spring, font/spacing and
theme code are unchanged. No new visual acceptance or 4.2 runtime claim.
Evidence: [runtime](design/qa/context-overrides-v1/runtime.json),
[focus](design/qa/context-overrides-v1/focus.json),
[provenance and limits](design/qa/context-overrides-v1/provenance.json).

## Custom-property clipboard, Favorites and shortcuts — verified

Scalar integer/float custom ID properties now share the standard Copy/Paste Driver
and Copy as New Driver rows, using exact escaped paths and the existing ID/path
clipboard API. Paste preserves original driver data on host-commit rejection,
rejects keyed/stale/locked targets, and retains unrelated animation data. Favorites
store Blender's escaped custom-property identifier, with exact-owner context,
deduplication, read-only queries and removal. UTF-8 paths that exceed native fixed
buffers fail closed instead of creating truncated entries. No new ABI symbol,
raw dynamic PropertyRNA pointer or expanded platform admission was needed.

Numeric shortcuts show explicit Set to Value choices. Assign/change/remove/cancel
use the existing glass key-capture menu and real user keymaps. Previously assigned
values remain discoverable when the current field changes. The consuming extension
registers its existing ShortcutRegistry; it now owns a separate undoable numeric
setter as well as its popup dispatcher. Canvas routes custom numeric controls to
it automatically. No registration happens on library import.

The setter resolves attribute/string-index owner paths without eval, rejects
missing/retyped/read-only values, updates the owning ID's dependency tags and
supports actual Blender undo/redo. Keymaps retain context-relative owner, key,
expected numeric type and a numeric literal; no arbitrary expression is executed.
It follows the future context owner, like native property shortcuts, instead of
retaining a stale datablock pointer. A tested generic wm.context_set_value attempt
was rejected: it wrote the value but bypassed undo and left driven values stale.

Eight final processes pass on Blender 5.1.2/5.2.2, including legacy native adapters,
registry/popup regressions and overrides/defaults. The regression matrix also fixed
an enum-only is_array assumption in driver labels and override handling. 252 pure
tests and Ruff pass. All six final windowed launches observed no activation or
restoration. Rendering/glass/springs/theme and reference acceptance are unchanged.
Evidence: [runtime](design/qa/custom-adapters-v1/runtime.json),
[focus](design/qa/custom-adapters-v1/focus.json),
[qualification](design/qa/custom-adapters-v1/provenance.json).

Remaining after that pass (custom contributions closed below):
hierarchy-wide/complex override actions; the previously named editor and Jump
routing boundaries; visual acceptance. Other custom ID-property types are not
silently counted as covered by the scalar numeric implementation.

## Scalar custom-property menu contributions — verified

Public `UI_MT_button_context_menu.append` callbacks now receive the exact clicked
owner and genuine Blender `FloatProperty`/`IntProperty` metadata, including the
custom identifier and description. Nested menus/operators reacquire metadata at
each callback/poll/action; cross-property scopes restore the outer context.
Contributed custom numeric fields support editing, rejected-commit rollback and
right-click actions for their own property. `ui.assign_default_button` maps to
the existing host-undo transaction; unknown arguments/native-button commands
remain unavailable. Removed keys/types/owners and unregistered operators revoke
pending actions.

A bounded, unattached native metadata scope is admitted only for the exact
macOS arm64 5.1.2/5.2.2 executables. It never draws, activates or executes a native
button. Its Python/C++/binary fingerprints are checked; all native scopes are
released synchronously. Unsupported builds retain base menus and expose a disabled
contribution-unavailable row. No registration or native compilation occurs on import.

Eight runtime processes pass (six background, two no-focus windowed), plus 253
unit tests and Ruff. Window launches recorded no activation/restoration. Rendering
was unchanged; visual/reference and source-speed acceptance are not newly claimed.
Evidence: [runtime](design/qa/custom-contributions-v1/runtime.json),
[qualification](design/qa/custom-contributions-v1/provenance.json),
[focus](design/qa/custom-contributions-v1/focus.json).

Still open: hierarchy-wide/complex override actions, Edit Driver/new-window routes,
hidden/cross-mode Jump, nonnumeric/array custom properties, wider native platform
qualification, and human visual/reference review.
