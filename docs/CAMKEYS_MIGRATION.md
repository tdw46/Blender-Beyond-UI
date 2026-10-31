# CamKeys custom consumer qualification — 2026-10-30

**Stable list IDs and the three tested brush-falloff popovers are implemented.**
The isolated checkout remains `/Users/tylerwalker/dev/CamKeys-beyond-ui`, branch
`codex/camkeys-beyond-ui`. The tested changes are now installed at the canonical CamKeys location on
`codex/camkeys-beyond-ui-test` for Tyler’s next Blender 5.2 launch. The existing
module remains enabled in saved preferences. The running unsaved scene was not
reloaded or saved. Original source files and preferences are backed up under
`build/camkeys-visual-v2/install/backup`; unrelated dirty work was preserved. Existing billboard/translation changes in the experiment
were copied from the source before the earlier consumer pass.

## Single-line library setup

```python
from ._vendor.beyond_ui import integrate; integrate(globals())
```

No native-fallback opt-in is now used for the tested consumer states. The six
panel definitions pass the populated-state authoring audit, and final runtime
status reports no draw errors or native fallbacks. This is not exhaustive visual
approval of every hidden panel or feature combination.

The integration initializes package-owned list rows with persistent IDs outside
drawing. They survive reordering and save/load; stale/deleted targets are rejected
and duplicate IDs revoke all ambiguous tokens. Read-only or foreign collections
still require an explicit host identity resolver. Bounded cached panel signatures
inspect count and active-row identity, not every row on every draw.

## Consumer-owned brush lifecycle

`ui_lists.py` uses optional prepare/change hooks for mesh, distance and flatten
falloff popovers. Brush creation happens on opening; custom drawing only looks
up prepared brushes and does not start the old synchronization timer. Changes
synchronize CamKeys through its existing correction function. Native drawing
keeps its existing path.

`custom_curve_lifecycle.py`, registered through CamKeys' existing utils lifecycle,
owns undo snapshots for Blender 4.3+ Brush data, which Blender excludes from global
undo. Curve preset/add/remove operators record the same snapshot before their undo
boundary. The reusable library does not contain CamKeys data bindings or handlers.
These are consumer data-lifecycle fixes, not additional UI setup lines.

## Verified

On macOS arm64 Blender **5.1.2 and 5.2.2**:

- Empty, tracked-mesh, CamProp, enabled and lattice panel authoring states.
- Persistent list IDs: read-only discovery, deferred initialization, reorder,
  duplicate repair, deletion rejection and a saved blend/loaded-scene round trip.
- Three real brush popovers: draw without brush creation/timer startup, point
  drag cancellation, handle context menus, preset changes, safe point allocation
  and removal, and native undo/redo through the consumer journal.
- Actual Add to CamProps exact camera-lens action/undo, Billboard Groups dialog,
  export-dialog cancellation, registered menu and disable/re-enable cleanup.
- Generic popup/keymap, registered-list and property-context regressions.
- No owned test-window activation or focus-restoration requests. Other app
  activation events are retained in the raw audit rather than suppressed.

[Checks and focus logs](design/qa/camkeys-custom-v1/runtime.json) ·
[Implementation provenance](design/qa/camkeys-custom-v1/provenance.json).

## Remaining boundaries

[CamKeys visual review](design/qa/camkeys-visual-v2/index.html) now includes two
GPU-captured GIFs, all three brush popover stills, owner menus and theme fixtures.
Crowded labels, missing preset icon presentation and untitled popover spacing
are corrected in v2, with immutable before/after captures. Exact reference
acceptance is pending.
The final Blender 5.2.2 capture run recorded no activation or focus changes.

Foreground
hotkeys, other platforms, Blender 4.2 execution, every CamKeys feature combination
and all native curve-editor tools are not qualified. Existing native import/export
file workflows are not a full I/O certification. The general parity ledger still
tracks unrelated core right-click/platform gaps. This is a local test deployment; no release or publication occurred.

## Embedded UI repair — 2026-10-30

The user’s live screenshot exposed defects not caught by offscreen captures.
Owned text now flushes inside each control transform and before widget clips;
native queued headers flush before backdrop work. The global BLF queue is flushed
without ending Blender’s batch scope. Each control retains glyph batching.
53 original Blender 5.2.2 SVG glyphs are bundled in one retained atlas, tinted by
active semantic colors. Offline regeneration has no runtime dependency or I/O.
Icon-only rails use intrinsic widths; narrow UIList rows keep authored trailing
status on a second line. Explicit empty menu labels remain empty.

[Actual embedded evidence and reference conflicts](design/qa/camkeys-visual-v3/index.html).
283 unit tests and 5.1.2/5.2.2 consumer checks pass. Idle/settled text crops are
pixel-identical. The installed test branch vendor is updated; consumer Python
files are unchanged. Previous vendor backup: `build/camkeys-lists-v3/install-backup`.
The running unsaved scene was not reloaded or saved; restart Blender to load it.

Reference matching remains open: the generated concept omits authored status and
uses different search state/icon semantics. Broad source-icon coverage beyond
this consumer is not claimed. CPU paint median is 2.79 ms versus prior 2.47 ms
(p95 3.22 versus 2.77 ms), excluding capture/GPU completion. The added per-control
flush is required by the reproduced text corruption; one global-queue flush
replaces duplicate body/title flushes. Glass production stays at one per revision.
This measures a correctness cost, not proof of source-performance equivalence.


## Compact lists and authored help actions — 2026-10-31

Unembossed Boolean actions now preserve author alignment and use action-button
presentation. This removes the incorrect HOW TO switch while retaining the same
RNA binding, right click, undo and source motion. Ordinary booleans remain switches.
Icon-only menus draw exactly one centered glyph. Registered list name/status pairs
share a compact column; status aligns under the name, accounting for an optional
icon. List titles use the retained bold face and paragraph rows use body spacing.

The native adapter drains the enclosing BLF queue before custom framebuffer work,
then resumes batching before the custom callback. It admits only the existing
exact supported builds with the required symbols. Per-control text still submits
inside its clip and motion transform. The earlier sampler-slot and deferred-text
experiments were discarded. No glass, animation or theme feature was disabled.

284 unit tests and the 5.1.2/5.2.2 consumer checks pass. Actual idle, expanded and
collapsed captures all contain ten required labels in an independent macOS Vision
OCR check, supplementing pixel and interaction checks. 195 fresh frames record
list and brush interactions. One shared glass production; warm CPU paint median
2.48 ms, p95 2.70 ms (previous v3 2.79/3.22 ms, same fixture; excludes GPU completion
and readback, not proof of whole-source speed). Final no-focus audits recorded no
activation. See [v4 review](design/qa/camkeys-visual-v4/index.html).

The installed test vendor is refreshed with a backup at
`build/camkeys-panel-v4/install-backup`; consumer Python is unchanged. The running
unsaved Blender session was not reloaded. Restart to load the new vendor.
Generated icon shapes/card composition and real glass are not pixel-identical:
those differences remain explicit reference defects, not approved parity.


## Forced Perspective responsive panel correction — 2026-10-31

The adopted panel host now uses the generic [panel presentation policy](PANEL_LAYOUT.md).
Section headings are bold and wrap, units/switches/icon actions reserve intrinsic
widths, percentage splits reflow under minimum pressure, and field labels/entries
share columns or stack. Input accessories align to values; list toolbars remain
at the top. No CamKeys UI source was changed. Ordinary icon-only `toggle=True`
properties retain full BVT switches; unembossed HOW TO remains an action.

[Current generated and actual review](design/qa/forced-perspective-v1/index.html)
includes the previous installed library at the same widths, nine scale/width
captures on each 5.1.2/5.2.2 runtime, and a real 5.2.2 N-panel/owner menu capture.
288 unit tests and existing consumer/list/brush tests pass. The short warm CPU
paint sample is about 0.97 ms median / 1.00 ms p95 versus 0.93/0.96 ms for the
previous installed library in the same fixture. This small sample excludes GPU
completion/readback and is not proof of a speed gain or whole-source parity.
No activation was recorded by the no-focus audits. The installed vendor backup
is `build/forced-perspective-v1/install-backup`; reload by restarting Blender,
without saving or modifying the unrelated live scene.

Exact reference matching is not claimed: generated numeric arrows conflict with
plain-entry semantics, and generated icon/glass artwork differs from the real host.
