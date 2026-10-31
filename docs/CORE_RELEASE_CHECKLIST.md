# Practical panel-toolkit release audit — 2026-10-30

This replaces API-inventory completion as the near-term work plan. Existing
implementations are retained; deferred additions are not release blockers solely
because they occur in Blender's API. No visual acceptance is implied by this audit.

| Core area | Existing evidence | Remaining release check |
| --- | --- | --- |
| Layout, labels, buttons, sizing | layout-flow-v1, layout-sizing-v1 | Representative narrow/wide N-panel and Properties integration; common flags and icon expectations |
| Sliders, switches, text/numeric fields | scalar-layout-v1, numeric-props-v2 | Practical units, edit/cancel, keyboard focus and owner-change regression matrix |
| Enums, dropdowns, data/search selectors | enum-properties-v2, menu-search-v1, pointer-decorators-v1, id-templates-v1 | Standard consumer polls, stale candidates, search/selection and applicable data actions |
| Basic editable lists | registered-lists-v1 | Visible-row owner identity, sorting/filtering, selection and row context actions; advanced drag/drop only if a consumer requires it |
| Menus, pies, popovers, confirmation | marking-menu-v5, action-parity-v1 | Representative invoke workflow, keyboard navigation, dismissal and nested ownership |
| Full applicable right-click support | context-menu-v6, operator-host-context-v1 | Per-core-control action checklist, keyboard invocation, host contributions, shortcuts, disabled/stale owners and native-button-dependent gaps |
| BVT visual/performance contract | Recorded per-feature GPU comparisons | User QA of core glass, motion, theme and scale; exact-reference conflicts remain defects, not waived |
| Supported runtime contract | 5.1.2/5.2.2 macOS execution | Clearly document build-specific adapters and untested platforms/4.2; do not claim universal compatibility without qualification |

## Scope held for later demand

New multiline editors, preview galleries, advanced curve tooling, specialized
image/node/animation templates and built-in Blender feature panels are not
near-term additions. Existing specialized controls remain available with their
recorded limitations. Missing mandatory right-click actions on core controls
cannot be deferred by reclassifying them as optional templates.

## Current estimate

**The final budgeted pass is complete: 0 more implementation/QA turns before the
next core review checkpoint.** This is not release completion or full right-click
parity. Hierarchy-wide/complex overrides, Edit Driver/new-window routes,
hidden/cross-mode Jump, other custom property types, native platform qualification
and human visual acceptance remain explicit gaps. No reliable total-hours forecast
is available. The [overview estimate](design/qa/overview/estimate.json) is the
current record; ranges below describe historical planning checkpoints.

## Gap closed during this audit

Cancel-only popup footers omitted consuming-extension context contributions.
They now preserve the built-in Cancel action followed by host actions, with the
shared menu's exact-target invalidation. A regression test verifies inclusion,
execution against the clicked control and rejection after owner removal. Shared
rendering, BVT glass, motion and theming were not replaced or altered.

## Shortcut context follow-up

Read-only shortcut displays now include host context contributions after Copy
Shortcut. Background tests cover keyboard APP invocation, isolated clipboard
copy, exact clicked host action and rejection after keymap deletion on Blender
5.1.2/5.2.2. All 246 pure tests and Ruff pass. Shared menu rendering is unchanged;
no new visual acceptance is claimed. Evidence:
`design/qa/shortcut-context-v1/runtime.json`.

Remaining context audit must still cover the supported core's action-by-action
capabilities, not just provider composition. Native-button-dependent gaps remain
explicit blockers for claims of full applicable right-click parity.

## Property action transaction follow-up

Reset and Copy to Selected now avoid writes/host commits when the selected
component already has the desired value. Failed component transactions restore
only the touched component, preserving unrelated sibling changes made by the
host. Changed copies still commit once. Disposable Blender 5.1.2/5.2.2 checks
cover both no-op and rejected-commit paths. Shared appearance and animation are
unchanged. Evidence: `design/qa/context-transactions-v1/runtime.json`.

## Mixed core workflow integration — completed

A single consumer Canvas combines scalar properties, editable fields, a real
collection list, held actions and a registered confirmation popup. Both Blender
5.1.2/5.2.2 background runs pass: 260/400/560 logical-width bounds, boolean changes,
numeric expressions, text right-cancel before context, popup click-through
prevention, list selection and exact-row menus, disabled-motion interaction and
quiescent teardown. No production renderer changes were needed.

Evidence: `design/qa/core-workflow-v1/runtime.json`; exact fixture/library hashes
are in the adjacent provenance record. This is a shared Canvas integration test,
not actual N-panel/Properties host embedding or new visual acceptance.

Remaining concrete review work:
- Real N-panel and Properties host integration: completed below.
- Finish the core action-by-action right-click coverage audit, including disabled
  actions and any native-button-dependent gaps; fix confirmed core defects.
- Review the existing core glass/motion/theme evidence with current host captures
  and address identified differences. No template expansion is planned.

One planned QA turn is credited: 4–10 becomes 3–9. No new scope was added.

## Actual host integration — completed

Both N-panel and Properties hosts pass on Blender 5.1.2/5.2.2 using disposable
no-focus windows and Blender event simulation. The checks verify real GPU anchor
execution and an available shared glass backdrop, modal toggle input, exact
property right-click targeting, registered confirmation popup opening/dismissal,
clip bounds, warm layout retention, runtime motion disable, edit rollback during
invalidation and owned modal teardown. No production changes were required.

The fixture waits for the Properties editor's first UI tick before setting its
SCENE context: immediate assignment exposed an empty enum on 5.1.2. The fixture
also uses the host's valid marker, since its painted marker is cleared after draw.
These were test setup corrections, not product failures.

Final matrix: four passing processes and zero observed test-process activations
in the 26.7-second audit. Earlier attempts did activate test windows despite the
flag; those records are retained. This is not general focus-safety qualification.
No foreground activation or restoration workaround was used. No new pixel/reference
acceptance is claimed. Evidence: `design/qa/core-hosts-v1/runtime.json`, focus
records and source/fixture hashes in that directory.

Credited one planned host QA turn: 3–9 becomes 2–8. Remaining work is the applicable
context-action coverage review and current core visual/motion/theme acceptance,
plus fixes if those reviews identify defects.

## Exact-channel context action audit — completed fix

Delete Keyframe and Remove Driver incorrectly appeared enabled for empty or
sibling-only animation channels. They now resolve the clicked component and
recheck before mutation; removed channels skip host commits. Keyframe actions
also use the current subframe consistently with decorators. Both installed
versions pass empty/sibling/whole-array, frame/subframe, stale-open-menu,
missing-undo and locked-control checks. Reset/copy transaction regressions also
pass both versions; all 246 pure tests and Ruff pass. No renderer changes or
new visual acceptance. Evidence: `design/qa/context-availability-v1/runtime.json`.

Credited one planned correctness turn: 2–8 becomes 1–7; no added scope. The
remaining core context review must distinguish the following evidence levels:

| Action family | Coverage and remaining boundary |
| --- | --- |
| Reset / Copy to Selected | Fresh component no-op and rollback regression on both installed versions |
| Keyframe / Driver add and remove | Fresh exact-channel availability, subframe, stale execution and undo-required tests on both versions |
| Copy paths / operator command / documentation | Existing context-menu and adapter fixtures; documentation opening is not newly executed by this pass |
| Driver clipboard / Quick Favorites | Existing exact-build adapter evidence; unknown builds fail closed, not full portable parity |
| Shortcuts / host contributions / nested actions | Existing action/shortcut fixtures and recent actual-host input evidence; native-button-dependent contributed operators stay explicit gaps |
| Compound/list/picker owner actions | Existing per-feature identity tests; consuming extensions supply product-specific actions |

This is not a declaration that every native context action has been implemented.
Full applicable context support and core visual acceptance remain release gates.
The exact-version API/Manual pages were requested again but unavailable from
the web tool; this pass establishes installed-runtime behavior, not a new 4.2 or
cross-platform qualification.

## Contributed commands and current visual package — completed

Reset/Copy to Selected/Data Path contributions now use exact RNA owners and native
argument defaults; registered Python operators ending in `_button` no longer fail
by name. Both installed versions pass disabled, stale, rollback and argument checks.
Five final GPU runs pass, including 390 pixel-equal native text batching pairs;
shared resources remain retained. The final 1× capture adds host contributions,
component context/search motion and synthetic light/purple theme states. Both
focus audits observed only the previously active application. Exact reference
acceptance and the explicitly listed context-action gaps remain open.

## Menu geometry, search and keying follow-up

The approved macOS menu reference now drives shared menu spacing. Fixed the
popover host overwriting compact menu geometry with parent row metrics; repeated
resize and theme changes retain the measured rhythm. Enum/context/registered
menus and pointer/search pickers share compact rows and unboxed inactive options.
Search magnifiers, text and caret insets are shared with collection-list filters.
Titles use the retained Bold face. Scalar switches are 25% larger visually while
logical hit regions stay stable. Dark fields and light-menu contrast are updated.

Keying-set and clear-channel actions pass both installed Blender runtimes.
Remaining release work: driver applicability/selected-owner routing, conditional
file/ID/override actions, and human visual acceptance. The new QA page preserves
reference/implementation differences explicitly; exact pixel matching is not
claimed. Updated provisional budget: 2–7 turns (1–4 implementation, 1–3 QA).

## External labels and icons — visual feedback pass

All shared editable field labels now paint outside their value surface; sliders
retain the BVT scalar layout. Compound color/ramp/curve fields receive the same
treatment. Labels can opt into retained, theme-colored icons; custom icon values
use a consumer-owned renderer. Confirmation text is centered, search type is
smaller, inset surfaces have fine outlines, and highlights bleed vertically
without changing rows or hit targets. Component forms keep ordinary host sizing.

248 pure tests, both 5.1/5.2 action/search regressions and six current GPU capture
runs pass. The old test assertion for an embedded Search label was corrected to
identify the search control semantically. Six capture processes recorded no
activation/restoration; 450 native text batching pairs match. Reference sheets
and actual comparisons are in `design/qa/menu-spacing-v2/`. Pixel acceptance
remains open. Credited one QA feedback pass: 2–7 becomes 2–6 remaining turns.

## Animation applicability and selected-owner routing — completed

Keyframe and driver actions now reject conflicting exact channels at execution.
Existing-key menus use Replace wording at the current subframe. Copy to Selected
extends to matching pose/data bones, nodes and object data, with shared-data
deduplication, current-selection checks, no-op suppression and component rollback.
Ten headless runtime processes pass across Blender 5.1.2/5.2.2; 248 pure tests and
Ruff pass. Existing BVT glass, bounce, theming and macOS menu rendering are unchanged.
Evidence: `design/qa/context-selection-v1/runtime.json`.

Credited one planned context batch: 2–6 becomes 2–5. Driver-copy/editor routing and
conditional property/data actions remain, as listed in CORE_CONTEXT_AUDIT.md.

## Selected-owner driver copying — completed

Single/all driver copies and contributed native command routing now preserve full
FCurve data and variable targets, skip keyed destinations and roll back rejected
host commits. Source channels, unrelated target channels and same-ID node paths
are protected; new driver dependency evaluation is verified. Six background runs
pass on 5.1.2/5.2.2, alongside 248 pure tests and Ruff. No renderer changes.
Evidence: `design/qa/driver-copy-v1/runtime.json`.

Credited one planned driver-copy batch: 2–5 becomes 2–4. Editor/edit routing,
conditional property/data actions and human visual acceptance remain.

## Conditional data and editor routes — verified

Open File/Location resolves exact owners and linked-library paths. Mark/Clear Asset
preserves complete metadata on rejected commits. Pointer/search root and candidate
menus share these actions. Jump supports visible objects and active-rig bones;
existing Graph/Drivers Editors support exact single/all-channel selection/framing.
Native Edit Driver/new-window routes and hidden/cross-mode Jump remain explicit
gaps alongside overrides/defaults. Eight headless runtime processes pass across
5.1.2/5.2.2; 248 pure tests and Ruff pass. No renderer changes or new visual claims.
Evidence: `design/qa/context-data-v1/runtime.json`.

Credited the combined implementation/integration batch: 2–4 becomes 1–3.

## Override rules and custom defaults — completed bounded actions

Exact simple property override define/remove, single/all restoration and rollback,
and scalar custom ID-property defaults now pass both installed runtimes. Custom
numeric Layout.prop bindings reuse the existing scalar controls and support paths,
selected copies, decorators, keying/driver actions and keying sets. Native adapter
source admission is repaired and protected by a regression check. Ten final
runtime runs and 249 pure tests pass; no renderer or visual-acceptance change.
See `design/qa/context-overrides-v1/` and the current context audit for limits.

Credited this implementation/integration batch: 1–3 becomes **1–2** turns to the
next core review candidate, with low confidence. Hierarchy-wide ID override
operations, non-simple rules, custom ID-property native-adapter integration and
the previously named navigation boundaries remain explicit. This is not an
estimate for universal native-action/platform parity or human visual approval.

## Scalar custom-property adapters — verified

Custom numeric driver clipboard, exact native Favorites and host-owned value
shortcuts are implemented. Nested/escaped paths, stale/type/disabled guards,
precision, cancellation, dependency evaluation and actual undo/redo pass both
installed Blender versions. Shared enum/popup registry behavior and legacy native
adapters pass as well. Eight final runtime runs, 252 pure tests and Ruff pass;
six final no-focus windows had zero observed activation/restoration.

Credited this requested batch: **1–2 becomes 1 focused implementation/review pass**
to the next core review candidate. This is low-confidence planning, not a promise
that hierarchy-wide overrides, custom native button contributions, editor routes
or human visual acceptance will all be completed in one turn. See the current
context audit for those explicit release boundaries. No built-in panel scope added.


## Scalar custom-property contributions — verified

Closed the final budgeted contribution pass: real owner/property callback contexts,
nested restoration, inline custom editing and exact-subfield right-click actions,
mapped defaults with rollback, callback isolation and stale-target rejection.
Eight 5.1.2/5.2.2 runtime runs and 253 unit tests pass. Two no-focus windows recorded
no activation; six tests ran in the background. No renderer changes or new visual
acceptance. Exact-build macOS arm64 admission applies; unsupported builds retain
base actions with an explicit contribution-unavailable entry.
See [evidence](design/qa/custom-contributions-v1/runtime.json) and
[remaining boundaries](CORE_CONTEXT_AUDIT.md).
