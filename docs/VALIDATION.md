# Validation record — 2026-10-28

## 2026-10-29 — enum property interaction pass

Scalar enum clicks now share the existing strong-glass menu route with shortcuts.
Explicit flag menus stay compact, long lists scroll instead of failing/truncating,
and expanded choices use verified transactions with rollback. Dynamic selection
checks both identifier and numeric enum value; concurrent property edits reject
an old menu. Bounded admission is 4096 choices; ordinary context menus remain 64.

- 98 unit tests pass. New cases cover no-op/flag transactions, failed commits,
  setter rejection, dynamic removal/remapping, concurrent writes, retained label
  lookup, 200-choice navigation, cancellation, integer Canvas keys including zero,
  duplicate identifiers and explicit oversized-input rejection.
- Disposable Blender 5.1.2 / 5.2.2 runtime and actual-window fixtures pass. Real
  input selects choice 199 with End/Enter, reveals the current choice on reopen,
  retains exact-property right-click routing and cancels without writes. Existing
  menu shortcut, native context, enum context and general runtime regressions pass.
- [Enum QA v1](design/qa/enum-properties-v1/index.html) retains 100 motion frames
  at each of 1×/1.5×/2× on each runtime: 600 native-batched/standalone pairs match
  byte-for-byte. Stable one-backdrop/one-blur/five-offscreen counts and retained
  font/shader/batch/layout identities pass. The README includes the motion GIF.
- Equivalent short-enum benchmark against exported revision `44f055a` asserts
  the actual loaded package root. Closed-field median/p95 on 5.2 is
  0.181/0.211 → 0.175/0.199 ms; on 5.1, 0.181/0.210 → 0.187/0.220 ms.
  Open-menu median/p95: 5.2 0.220/0.243 → 0.208/0.230 ms; 5.1
  0.221/0.237 → 0.220/0.238 ms. An initial duplicate expanded-button ownership
  check was removed; Binding.read already performs it. These separate-process
  CPU submission samples show comparable warm costs, not a speedup or GPU timing
  claim. Each workload uses 20 warmups/100 samples and excludes framebuffer reads.
- Resting benchmark pixels are unchanged. The open-menu comparison intentionally
  differs because menus now anchor below the field instead of at its top edge.
  No other visual-match acceptance is inferred from that comparison.

Full enum and UILayout parity remains partial. Shift/multi-toggle persistence,
headings/separators/icons, specialized tabs, full focus traversal and wider
platform/theme/reference qualification remain tracked in
[ENUM_PROPERTIES.md](ENUM_PROPERTIES.md). Blender 4.2 fallback remains intact but
was not executed. No unrelated live scene, preferences or BVT source was changed.

## 2026-10-29 — consistent host scale audit

The user-reported oversized Active Node, collection search and Target popovers
shared width-driven artboard scaling. Canvas now normalizes authored body text to
its host font (normally 11 logical units); section titles are 12. The same sizing
covers embedded curve/ramp/color/picker/palette/matrix/progress cards, compact
progress and sockets. Pointer/search/color/palette popovers use one owner-aware,
visible-clip-bounded route with source strong glass. Open popovers reflow before
input on clip resize; layout and hit transforms preserve uniform aspect ratio.

- 90 Python tests pass, including width/height bounds, popup resizing, logical
  hit mapping, socket layout and no magnification at 360/560/960 logical widths.
- Blender 5.1.2 `ec6e62d40fa9` and 5.2.2 `d13f752e3b9c`, macOS arm64/Metal:
  scale/color/palette RNA checks, existing non-ID/pointer/search/general runtime
  checks and real window pointer/picker/menu input regressions pass in disposable
  profiles. No user scene or preferences were saved.
- [Current QA gallery](design/qa/ui-scale-v1/index.html): 13 families × three
  physical rendering scales = 39 images per version. All match byte-for-byte
  with native text batching enabled/disabled. Warm resource counts and layout
  identities remain stable. Recorded CPU submission medians span 0.043–0.217 ms
  on 5.2 and 0.044–0.212 ms on 5.1; p95 spans 0.052–0.310 / 0.053–0.240 ms.
  Each workload uses 10 warmups and 50 samples; framebuffer readback is excluded.
- The unchanged 500-node fixture supplies 100 opening/filter/context-motion
  frames per version, all matching both text paths. One backdrop production,
  one blur, five offscreens and retained font/shader/batch identities remain
  stable. A refreshed Target/ID-search fixture also passes all 100 frames on 5.2.
- Same-fixture before/after warm open-picker CPU median/p95: 5.2
  0.231/0.273 → 0.223/0.258 ms; 5.1 0.214/0.239 → 0.217/0.249 ms.
  These separate process runs show comparable timings, not a speedup claim or
  controlled BVT benchmark. Geometry is intentionally smaller; source-equivalent
  performance and GPU completion latency are not established by these numbers.

Historical generated references/galleries are preserved. The user's scale
correction supersedes their oversized presentation; exact reference acceptance
remains open. Physical-scale captures do not qualify every OS display setting.
Blender 4.2 and other platforms were not executed. Extremely constrained bounds
shrink uniformly; arbitrary tiny-viewport readability is not claimed. Full API
parity remains incomplete (137 members, 40 partial, zero reference-matched).

## Current status

The modular extraction and initial custom implementation are execution-tested.
Full custom Blender UI parity is **not complete**. Tyler approved the prior four controls' presented resting state; full exact
matching across controls/states is not established. Tyler owns visual QA; do not infer approval from screenshots,
unit tests, native forwarding or ordinary CI.

## Evidence

- 50 pure Python tests pass: transactions/rollback, stale-owner rejection,
  retained geometry, clipped input, million-row virtualization, text/arithmetic,
  independent vendor namespaces, and custom color/curve/ramp/picker interactions.
- Ruff parser/name-error checks pass. No claim of full static type validation.
- Exact official documentation inventories: Blender 4.2, 4.3, 4.4, 4.5, 5.0,
  5.1 and 5.2; UILayout, Panel, Menu, UIList and Header. The union includes
  137 UILayout members. Versioned Manual button pages were also checked.
- Blender 5.1.2 `ec6e62d40fa9` and 5.2.2 `d13f752e3b9c`, macOS arm64:
  documented RNA availability, edit rollback, two vendor namespaces,
  registration cycles, custom RNA authoring, ramp/curve rollback and explicit
  unsupported-template behavior pass in disposable background profiles.
- Real windowed tests on both installed versions pass: native reference API
  access, custom anchor/GPU drawing, actual modal toggle input, retained warm
  geometry, outside-region pass-through, invalidation rollback, and disable /
  re-enable callback ownership.
- All four specialized widget painters execute in Blender 5.2.2 / Metal and
  produce actual GPU framebuffer captures. [QA board](design/qa/v2/index.html),
  [full image](design/qa/v2/all-controls-comparison.png),
  [capture provenance](design/qa/v2/capture.json).

No live Blender MCP listener was available. Tests used isolated processes and
profiles; the source BVT extension and unrelated user scenes were not changed.
No new visual approval or native Windows/Linux qualification is implied.

## Gates still open

- Full custom control semantics and all documented API methods.
- Exact generated-reference matching, including additional states/sizes/themes.
- Full keyboard/context-menu/tooltip/accessibility parity.
- All older runtime series. 4.2's inherited native ABI allowlist is not a fresh
  qualification of this library; unknown builds are rejected.
- Windows and Linux custom embedded hosts; source is not binary qualification.
- Complete GPU/CPU performance, multi-window, DPI and stress/idle matrices.

The strict `tools/check_custom_parity.py --require-complete` gate intentionally
fails. Ordinary CI validates the current implementation and honest ledger; it
must never be described as evidence of full custom parity.

## Reference styling revision 2

All four revised compound painters execute in Blender 5.1.2 and 5.2.2. The
[revision notes](design/qa/v2/NOTES.md) distinguish the improved visual comparison,
actual alpha/transparency proof, measured rendering costs and remaining defects.
No exact match or source-performance equivalence is claimed.

## Next controls and shared motion

Palette, read-only matrix decomposition, BAR/RING progress and the shared
animation policy are implemented with partial parity. [QA board](design/qa/next-v1/index.html)
and [motion guide](ANIMATION.md) enumerate remaining gaps. The ledger has 39
partial members out of 137; no member is marked fully reference-matched.

Fresh background/runtime tests pass on 5.1.2 and 5.2.2. Fresh windowed tests cover
input, timer registration during motion, automatic termination while hovered,
live host disable, invalidation rollback and repeated registration. Deterministic
actual Canvas captures on both versions prove identical resting/settled/disabled
pixels and unchanged retained geometry. These do not qualify older runtimes,
Windows/Linux, every motion state or every UI scale.

The performance record retains the earlier baseline and the resting/active-motion
measurements; exact source-extension performance equivalence is not claimed.

## README previews and Data Picker interaction pass

[The main README](../README.md) now contains eight per-panel GIFs, generated by
`tools/build_readme_gallery.py` from actual captured frames. Data Picker gains
keyboard focus/navigation, Enter selection, draggable/pageable scrollbar and
clipped partial rows with retained icon geometry. The [picker QA record](design/qa/picker-v1/NOTES.md)
contains runtime, performance and visual-comparison limits. The original resting
captures remain unchanged. No new exact-match acceptance is inferred.

Original BVT right-click menus and theme extraction are now explicit hard rules
with an [audited source contract](SOURCE_UI_CONTRACT.md). Complete menu wiring remains open. The default live-theme role plumbing was
implemented in the following checkpoint; exact theme-reference fidelity is open.

## Active Blender theme colors

The source BVT reader now supplies production colors to basic controls, selection
menus and all eight compound cards. [Theme configuration](THEMING.md) records
semantic mappings, fallback reporting and explicit reference-only policy.
[Theme QA](design/qa/theme-v1/NOTES.md) includes 5.1.2/5.2.2 execution records,
native dark and synthetic light/purple captures, data-color preservation,
retained resource checks, before/after timings and a generated-reference conflict.

All 12 earlier individual resting captures and all 75 frames of the eight-panel
reference animation remain byte-identical. Real windowed input, animation idle,
teardown and re-registration checks pass on both installed versions. This
checkpoint does not grant visual acceptance or full context-menu/API parity.

## Right-click menus and liquid glass — 2026-10-28

[Menu QA and raw evidence](design/qa/context-menu-v1/index.html) records the shared
contract: exact subtargets, scalar/array reset, selected-owner rollback,
paths, keyframe/driver undo handoff, nested public callbacks and stale-owner
rejection. Disposable windowed tests on both 5.1.2 and 5.2.2 pass real mouse and
keyboard invocation, nested/back/shortcut execution, cancel-before-menu, outside
pass-through, one-shot tooltip shutdown, default liquid-glass admission, finite
motion and teardown. Existing background/windowed suites also pass on both.

The initial preview incorrectly exercised tint-only fallback. The corrected host
default and menu painter use BVT's original lens, 0.7 strong blur and untinted
refractive body. `_ensure_lens`, `_strong_blur` and `lens` match the audited source
AST exactly. `prepare_texture` supports host-owned GPU textures without native
capture or CPU readback. Source/follow-up file hashes are in
[source-ui-audit.json](source-ui-audit.json).

The 640×560 Metal fixture measures 20 warm-up and 100 timed submissions per mode,
plus 100 navigation events. [capture.json](design/qa/context-menu-v1/capture.json)
contains distributions, source hashes and resource counts. Timings are CPU draw
submission time, not a GPU fence or end-to-end input-latency measurement. One base
production, one strong-blur production and five texture/framebuffer targets serve
the tested frames; shader, batch and icon identities remain unchanged. Settled
and animation-disabled frames exactly equal the resting frame. Glass remains
enabled when motion is disabled. The source-level speed gate still requires the
broader dense-controls, DPI, platform and live-host workload matrix.

Exact visual-reference acceptance is not claimed: generated menu v1 altered
contrast/glyphs/dimensions and represented the rejected tint material. It remains
immutable and explicitly rejected. Corrected liquid-glass root/nested/tooltip and
all eight compound targets are actual renders for Tyler's QA. Additional state,
theme and motion references remain open. No private native-button action is
silently invoked against another control.

Official documentation checked for the GPU texture/framebuffer surface:
[5.2 GPU types](https://docs.blender.org/api/5.2/gpu.types.html),
[5.1 GPU types](https://docs.blender.org/api/5.1/gpu.types.html), and
[4.2 texture utilities](https://docs.blender.org/api/4.2/gpu.texture.html).
Exact 4.2 GPU-types and 4.2/5.1/5.2 English Manual menu-page fetches returned 402
in this session; older/development pages were not substituted as current proof.
The public API path and existing 4.2 capability fallbacks remain intact, but the
new menu implementation is not runtime-qualified on 4.2 by these tests.


## Menu adapters and mandatory glass — 2026-10-28

The local AGENTS.md now has a dedicated **real BVT liquid glass** hard rule.
Every translucent panel/menu/nested menu/tooltip/popover/control must use the
source shared backdrop, Gaussian levels, refraction and rim. Source material and
performance are simultaneous completion criteria; tint-only fallback is degraded.

[Versioned QA v2](design/qa/context-menu-v2/index.html) adds exact-build native
driver clipboard and Quick Favorites tests, public keymap assign/change/remove,
Edit Source, and Python tooltip targets. Both macOS arm64 5.1.2 (`ec6e62d40fa9`)
and 5.2.2 (`d13f752e3b9c`) pass in disposable profiles. A separate real window
fixture assigns a shortcut through the custom menu, invokes it outside the canvas,
and removes it. Clipboard tests cover replacement and host-commit rollback;
Favorites tests cover typed arguments, exact components, repeated adds, unrelated
owners, and temporary configuration cleanup. No live user scene/preferences were
saved. Imports remain free of Blender registration and timers.

Warm 640×560 CPU submission timings remain around 0.23 ms for the root menu.
The same fixture uses 20 warmups, 100 samples and 100 navigation events; current
and prior distributions are retained in [comparison.json](design/qa/context-menu-v2/comparison.json).
The added capability checks increase navigation CPU time by about 0.02 ms in the
initial comparison (roughly 0.06 to 0.08 ms); they revalidate the clicked owner and
clipboard/favorite availability on input and do not run in paint or idle timers.
Painting retains one backdrop preparation, one strong blur and five offscreens,
with no resource rebuild through menu motion/navigation. Shared glass shaders,
batches and borrowed view caches now release when the final host releases its
backdrop; other active hosts retain their resources. These are CPU submission
measurements, not GPU-completion or end-to-end input latency claims. Exact-binary
hashing is cached at host startup, outside menu interaction/painting.

The native menu manifest records audited exact Blender source hashes and tested
executable hashes. Official version-specific API/Manual lookup was attempted for
4.2/5.1/5.2; several exact pages returned 402/cache misses or stale search indexes.
No newer/older search result was substituted as version proof. Exact upstream
[5.1 driver source](https://github.com/blender/blender/blob/ec6e62d40fa9/source/blender/editors/animation/drivers.cc),
[5.2 driver source](https://github.com/blender/blender/blob/d13f752e3b9c/source/blender/editors/animation/drivers.cc),
[5.1 menu source](https://github.com/blender/blender/blob/ec6e62d40fa9/source/blender/editors/interface/interface_context_menu.cc),
and [5.2 keymap source](https://github.com/blender/blender/blob/d13f752e3b9c/source/blender/windowmanager/intern/wm_keymap_utils.cc)
plus installed-runtime RNA supplied the compatibility evidence. Unsupported native
builds/platforms, including 4.2, fail closed; public paths remain available.

Full menu/API parity is not claimed. See [explicit remaining adapter cases](CONTEXT_MENUS.md).
The rejected generated reference is retained, and no new capture is labeled an
exact reference match or visual approval on Tyler's behalf.

The screenshot process retains a shutdown warning also present in historical v1
capture logs: one 65,624-byte allocation. A guarded-allocator diagnostic names it
`MTLSafeFreeList`; see [raw diagnostic](design/qa/context-menu-v2/metal-shutdown-diagnostic.log).
Explicit library owner/view/shader/batch cleanup assertions pass, and separate
menu modal/action fixture logs do not report this warning. Its Metal backend
cause remains unresolved; zero-allocation shutdown is not claimed for the
screenshot fixture.

## Right-click gap closure — QA v3, 2026-10-28

[QA v3](design/qa/context-menu-v3/index.html) adds property/operator Favorites
removal, direct enum-value and enum-flag shortcuts, explicit mouse/NDOF-button
and held-key capture modes, common global/View3D keymap conflict checks, prepared
checked states, and contributed boolean/enum/operator-choice rows. These reuse
the existing BVT menu painter, theme roles, liquid glass and finite spring.
No new shader, blur pass or redraw timer was added.

Both exact macOS arm64 Blender 5.1.2 and 5.2.2 builds pass adapter, new parity,
actual-window input and background regression fixtures in disposable profiles.
The new fixture tests middle-mouse assignment, held-key release/reset and
assignment, cross-map conflict rejection, exact enum values, preservation of
other enum flags, disabled contributions, host-commit rollback and scoped
operator arguments. Physical NDOF hardware is not qualified by these tests.
53 pure tests, Ruff and the package build pass. The parity ledger remains
137 documented members, 39 partial, zero reference-matched.

Favorites queries search the active editor plus Blender's inherited menu scopes.
Removal repeats exact matching at execution rather than retaining item pointers.
Temporary native arrays are freed through Blender's active allocator dispatcher,
with the exact source-defined destructor type. Query loops leave preferences
clean; writes mark preferences dirty without saving. Operator query containers
are always released. Native admission remains limited to the audited executables;
this work does not extend native support to 4.2, Windows or Linux.

The equivalent 640×560 warm fixture records root CPU submission median/p95
0.237/0.280 ms (v2: 0.248/0.344 ms), nested 0.241/0.267 ms, and navigation
0.079/0.082 ms. One backdrop, one strong blur and five retained offscreens serve
all tested states and motion. Resource identities stay stable, and resting and
animation-disabled root pixels match. These samples do not establish GPU latency,
full source-level speed or a significant speedup. The broader workload gate stays
open. Current capture shutdown has no allocation warning; the historical Metal
`MTLSafeFreeList` observation remains unresolved and is not declared fixed.

Official evidence consulted: [5.2 KeyMapItem](https://docs.blender.org/api/5.2/bpy.types.KeyMapItem.html),
[5.2 keymap customization](https://docs.blender.org/manual/en/5.2/advanced/keymap_editing.html),
and exact tested-build source listed in the native audit manifest. Exact 4.2/5.1
KeyMapItem and several Manual pages were unavailable during lookup; runtime and
exact-source verification are identified separately rather than substituting
older/latest pages as proof. Existing capability fallbacks remain.

Reference v1 and QA v2 are unchanged. No corrected generated liquid-glass
reference is yet approved, and these captures are not labeled reference-matched.
[Remaining cases](CONTEXT_MENUS.md) explicitly include custom-popup shortcut
dispatch, arbitrary editor/modal hierarchy conflicts, keyboard-only alternate
capture selection, inline scalar fields, dynamic enum callbacks, string contexts,
and the broader theme/DPI/platform/window and motion acceptance matrix.

## Keyboard capture and contribution ownership — QA v4, 2026-10-28

[QA v4](design/qa/context-menu-v4/index.html) closes keyboard-only selection of
capture modes. Assign/Change first opens a standard menu page; arrows and Enter
select the mode before capture is armed. Escape/right-click returns to the mode
chooser, then the parent menu. Tab/arrows/Enter remain assignable once capturing.
The chooser and capture share one nesting slot, preserving the three-level limit.
Both stages reuse the existing glass painter, theme mapping and finite spring.

Inline extension menu contents now inherit disabled/active state, invocation and
pointer scope. Contributed commands snapshot nested mutable arguments, mathutils
values and RNA arrays by value. Pointer arguments and operator/menu registration
identity are revalidated. Snapshots are bounded; unsupported argument trees and
nested callback failures are isolated from subsequent contributions. Native
admission and Blender 4.2 fallback behavior are unchanged.

57 pure tests, Ruff, packaging, and disposable Blender 5.1.2/5.2.2 adapter,
contribution, actual-window input and background regression fixtures pass. New
cases include keyboard mode navigation, cancellation, deepest-level capture,
argument mutation after collection, mathutils/RNA array support, inline disabled
state and EXEC_DEFAULT inheritance, nested callback recovery, unsupported argument
isolation and operator-unregister revocation. Runtime inspection caught that
mathutils classes report a `builtins` module on these executables; the snapshot
adapter now checks the actual loaded classes instead of trusting module names.

The unchanged warm root workload records CPU median/p95 0.242/0.293 ms versus
v3's 0.237/0.280 ms; navigation median is 0.079 ms in both. Resources remain one
backdrop production, one strong blur and five offscreens, with stable identities
through both mode-chooser and capture animations. These small sample differences
do not establish a speed change or full source-level performance qualification.
No shader, geometry rebuild, blur pass or idle timer was introduced. Source/fixture
hashes, raw captures, GIF frame hashes and logs are versioned with this evidence.

Exact 4.2, 5.1 and 5.2 UILayout API and Manual menu pages were searched/opened.
Most exact pages remained inaccessible to the fetch tool; the indexed
[4.2 UILayout API](https://docs.blender.org/api/4.2/bpy.types.UILayout.html) and
[5.2 Operator API](https://docs.blender.org/api/5.2/bpy.types.Operator.html)
provide the public layout/operator contract. Installed runtime checks supply
separate execution evidence for 5.1.2/5.2.2; stale 5.0/5.3 search hits were not used
as proof for those versions. This is not new runtime qualification for 4.2.

Prior references and galleries remain unchanged. Exact generated-reference and
motion acceptance, custom-popup shortcut dispatch, inline scalar contribution
editors, dynamic enum/string contexts and the broader platform/theme/DPI matrix
remain open. The ledger remains 137 documented members, 39 partial and zero
reference-matched.


## Functional menu completion — QA v5, 2026-10-28

[QA v5](design/qa/context-menu-v5/index.html) supersedes the functional menu gaps
listed in v4. Inline numeric/string/array-component editors now provide deferred
transactions, safe arithmetic, clipboard editing, mouse caret/drag selection,
keyboard selection and shared-glass validation feedback. Cancellation never
writes; stale values and rejected host commits cannot overwrite data.

An explicit host-owned `ShortcutRegistry` reopens custom enum menus and routes
custom invocation/context callbacks. Actual simulated window key events assign
and invoke the shortcut outside the canvas, then commit a selection, on both
macOS arm64 Blender 5.1.2 and 5.2.2. Hidden/replaced controls reject dispatch;
unregister clears callbacks. Hosts can supply additional editor/modal keymaps;
a runtime conflict fixture confirms those bindings cannot be overwritten.

Dynamic RNA enum callbacks, including changed choices and operator-property
snapshots, use exact-build admitted native evaluation. Property callbacks receive
the current context; Blender can intentionally supply `None` to operator callbacks.
Native string scopes now reach operator poll/execute and nested/direct menu
contributions. Tests cover Unicode, inherited keys, nested and exception restore,
zero remaining native stores and temporary keyconfig cleanup without dirtying
preferences. Typed operator scratch containers and owned enum arrays are released.

62 pure tests, Ruff, the parity checker and source/wheel builds pass. The runtime
completion, native-context, adapter, menu contribution, modal-input and general
regression fixtures pass on both installed qualified builds. Disposable profiles
are used throughout; no live scene or preferences were saved. The wheel contains
matching native source, admitted binary, manifests and all new Python modules.

The v5 root pixels exactly equal v4. Inline-field motion and live native/synthetic
light/purple themes retain the same shaders, batches and shared backdrop resources.
150% render captures check scaling/clipping; they are not a complete system-DPI
or multi-window/hardware qualification. No generated reference or motion approval
is inferred. Previous gallery/reference versions are unchanged.

The remaining release gates are broader platform/native-build qualification and
Tyler's exact visual/motion QA. General UILayout templates, pointer/event property
options, unit/subtype semantics and other controls remain in the main UI parity
ledger: 137 documented members, 39 partial, zero reference-matched. This work does
not convert that ledger to full parity or admit untested Blender 4.2 native APIs.

On the equivalent 640×560 fixture (20 warmups, 100 samples), root CPU submission
median/p95 is 0.235/0.267 ms versus v4's 0.242/0.293 ms.
The new inline-edit workload is 0.117/0.141 ms. Navigation median is
0.084 ms versus 0.079 ms previously. One backdrop production, one strong-blur
production and five retained offscreens serve the entire capture. These are CPU
submission measurements, not GPU completion or end-to-end latency. Current capture
shutdown has no allocation warning; the historical intermittent Metal warning is
not declared fixed.


## Numeric property units and gestures — 2026-10-28

[Numeric property QA](design/qa/numeric-props-v1/index.html) extends the existing
custom painter with scene-unit presentation and input. Both installed macOS arm64
Blender 5.1.2/5.2.2 runtimes pass metric/imperial conversion, preferred length
units, scaled area/volume, degree/radian and percentage-factor handling, unchanged
roundtrip, click-to-type, soft/hard limits, Ctrl snapping, unit-setting changes
during edits, cancellation before context menus and exact raw RNA subtargets.
Authoring, contributed-menu and actual window-menu regression fixtures also pass.
68 pure tests, Ruff, ledger validation and source/wheel builds pass. No scene or
preferences were saved outside disposable profiles.

The 640×560 capture uses 16 numeric properties with clipping, 20 warmups and 100
CPU submission samples. Unit-aware median/p95 is 0.230/0.309 ms; the
raw-format baseline in the same renderer is 0.213/0.238 ms. This is not
a historical binary comparison or GPU completion measurement. An initial probe
identified repeated per-field scene/view setting reads; the final painter resolves
those once per context per paint. Unit caches retain primitive keys only.

The real BVT backdrop has one production, one strong-blur production and five
retained offscreens. Layout, shader and batch identities remain unchanged through
hover/press/release, live theme/unit changes and captures. Settled and disabled
motion pixels equal the resting capture. Existing visual references are unchanged;
no new exact-match/motion acceptance is claimed. The current capture log has no
allocation warning. Unrelated historical Metal shutdown observations remain open.

Exact official public unit-helper source was inspected for 4.2.0 and the installed
5.1.2/5.2.2 revisions. Most exact API/Manual URLs returned fetch/access errors;
they were not replaced with stale-version compatibility evidence. Blender 4.2
runtime and broader platform/DPI qualification remain untested in this pass.
[Numeric integration](NUMERIC_PROPERTIES.md) lists the remaining property semantics;
full API parity remains false (137 members, 39 partial, zero reference-matched).

## Wide numeric motion and event properties — 2026-10-28

Wide numeric fields (at least 75% of usable panel width) now multiply the resolved
motion strength by 0.15. Pure tests cover inheritance, compact controls, unchanged
buttons, pre-layout configuration, runtime changes, unchanged geometry, disabling
and invalid values. The 69-test suite, Ruff, parity checker and package build pass.

[Numeric QA v2](design/qa/numeric-props-v2/index.html) retains the earlier v1 gallery
and verifies its historical raw frame hashes before building the paired recording.
Resting pixels remain byte-identical to v1; settled and disabled pixels equal rest.
The shared shader/batch/layout resources remain stable, with one backdrop capture,
one strong blur and five offscreens for the entire motion sequence. At 640×560,
16 fields with clipped-row culling, 20 warmups and 100 CPU paint submissions,
formatted-field median/p95 was 0.213/0.292 ms (v1: 0.230/0.309 ms). The same-renderer
raw formatter baseline was 0.197/0.225 ms. These are submission timings on the
recorded macOS/Metal runtime, not GPU completion, physical input latency or a
cross-platform/source-binary performance qualification.

[Event QA v1](design/qa/event-props-v1/index.html) adds `event=True` scalar INT/ENUM
and `full_event=True` existing KeyMapItem.type support. Disposable-profile tests on
Blender 5.1.2 and 5.2.2 cover modifiers, event-only preservation, keyboard↔mouse
map-type changes, held-key chords, exact right-click owners, cancellation, stale
chords/deleted owners, collision rejection and host-commit rollback. Real window
input exercises click→mode choice→capture, active liquid glass, cancellation,
right-click actions and idle/teardown timer cleanup. Numeric, general runtime,
menu transaction and existing menu-window input regressions are rerun on both.

Event captures share the existing field/menu painters, theme roles, fonts and
spring policy. Two event fields at 640×560 measured 0.070/0.088 ms median/p95 CPU
paint submission after 20 warmups, over 100 samples excluding readback. The full
capture sequence retains one backdrop, one strong blur and five offscreens.
This small event workload does not establish dense-event or all-theme performance.

The feature uses public RNA; optional KeyMapItem fields are capability checked.
Official UILayout source snapshots for 4.2.0 and both tested build revisions are
recorded with hashes. Blender 4.2, other platforms and physical NDOF devices remain
unexecuted. No native ABI admission, minimum supported version, registration or
preference-persistence policy changed. Exact generated-reference/motion acceptance,
all editor scopes and the remaining prop keywords/subtypes stay open in the ledger.

## Every menu option follows the reveal transform — 2026-10-28

[Menu motion QA v6](design/qa/context-menu-v6/index.html) reproduces native BLF
batching in an exact-build disposable fixture. With the original painter, final
text runs could be submitted after the menu's matrix was popped. Public
zero-angle BLF rotation mode now keeps text submission inside the finite menu
transform, including labels, shortcut hints, disabled rows and inline values.
Earlier text is drained at the incoming matrix, and the font flag is always
restored. Settled menus retain their original batching behavior.

For each of Blender 5.1.2 and 5.2.2, **153 animated frames are byte-identical**
between native-batched and unbatched rendering: 45 root/nested/back, 36 capture
mode, 36 shortcut capture and 36 inline-field frames. The original painter fails
the native-batched comparison. Resting pixels match the old painter; settling and
disabling restore rest. The full resource snapshot stays stable: no new font
loads, geometry, backdrop captures, blur productions or offscreen allocations.
All menu and event real-window regressions pass again after the painter change.

At 640×560, 20 warmups and 100 CPU submissions with a fixed active reveal sample,
5.2 animated-menu median/p95 changes from 0.190/0.223 ms to 0.220/0.282 ms. The
roughly 0.030 ms median cost is bounded per-label submission during animation;
settled-menu median remains 0.188 ms (baseline 0.187 ms). On 5.1 the active result
is 0.239/0.266 ms. This intentionally preserves all text motion and does not add
GPU synchronization or an offscreen workaround. Timings exclude framebuffer
readback and do not establish cross-platform input latency or full source speed.

Test-only calls to BLF batch begin/end are source/executable admitted for the two
exact installed builds. Production adds no private ABI calls. The audit includes
official 4.2.0 and exact 5.1.2/5.2.2 font/Python API sources; 4.2 execution and
other platforms remain open. Historical v1-v5 captures are untouched.

## Pointer pickers and animation decorators — 2026-10-28

[QA v1](design/qa/pointer-decorators-v1/index.html) records custom pointer fields,
filtered virtual popovers and empty/keyed/changed/animated/driven decorators.
Public-RNA checks and real window-input fixtures pass on macOS arm64 Blender
5.1.2 and 5.2.2. Cases include camera/custom polls, parent-cycle exclusion,
exact candidate/property context ownership, stale/deleted/renamed candidates,
commit-time poll/membership changes, failed pointer-commit rollback, read-only
pointers, key insertion/deletion, driver state, action replacement, automatic
split slots, opt-out and host animation disable/teardown. Numeric, event,
general runtime and existing menu/event-window regressions pass on both.

74 pure tests, Ruff, compilation, distribution build and the member-by-member
ledger check pass. The ledger now has 40 partial members out of 137; none are
marked reference-matched. Blender 4.2 execution, other platforms and all listed
pointer/animation variants remain open. See
[scope and integration](POINTERS_AND_DECORATORS.md).

Each runtime capture compares 100 actual animation frames with native BLF
batching enabled and disabled: all are byte-identical after font/menu warmup.
The checks exposed underlying field text flushing after a settled popover and
body/title text escaping finite transforms. Owned text now drains before
layered overlays, and finite-motion text is submitted within its transform.
Settled fields retain batching; popup shell and contents animate together.
Per-control popup strength/disable survives subsequent input (unit regression).

The 640×560 workload has two pointers, five scalar properties, five decorators
and optionally a 28-row virtualized picker. Each measurement uses 20 warmups and
100 CPU paint submissions, excluding framebuffer readback. At UI scale 1:

| Runtime | Workload | Median ms | p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | fields and decorators | 0.388 | 0.467 |
| 5.2.2 LTS | open picker | 0.494 | 0.556 |
| 5.1.2 | fields and decorators | 0.366 | 0.421 |
| 5.1.2 | open picker | 0.475 | 0.525 |

The entire animation capture retains one backdrop production, one strong blur,
five offscreens, unchanged font handles/shader/batch identities and one layout.
No per-frame capture/blur or permanent animation timer is introduced. These
small-workload measurements are a baseline for the new controls, not proof of
source-equivalent dense-scene speed, GPU completion time or input latency.

The first decorator visuals reuse existing retained BVT-family geometry. No new
generated-reference approval is claimed. Exact theme/DPI/motion fidelity remains
Tyler's QA gate; immutable earlier reference and comparison galleries are intact.

## Transactional collection search and array decorators — 2026-10-28

[Search QA v1](design/qa/collection-search-v1/index.html) includes 503-candidate
rendering, actual window input, and an immutable before/after row-motion comparison.
Both Blender 5.1.2 and 5.2.2 pass RNA checks for string/custom-label selection,
free suggestions, stale/removed collection members, concurrent edits, rejected
commits, host pointer candidate/poll restrictions, exact context targets and
standalone vector/aggregate-color decorators. The 500-item non-ID fixture
reproduces address reuse after removal and rejects stale actions. Refresh cancels
owned text/focus/capture/context state. Removed collection RNA fails closed.

Real window input covers End/Enter, typed suggestions, right-click cancellation,
candidate menus, exact component keying, motion disable and timer cleanup.
Existing pointer/decorator and general runtime regressions pass on both versions;
existing pointer real-window navigation/context/glass/teardown checks also pass.
77 unit tests, Ruff, compilation, distribution build and parity-ledger checks pass.
The ledger remains 40 partial members out of 137, with no reference acceptance.

At scale 1 and 640×560, the renderer compares the old and new picker painters on
the same retained 503-row workload and three decorators. Each case has 20 warmups
and 100 CPU paint submission samples, with readback excluded:

| Runtime | Workload | Median ms | p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | baseline rest | 0.270 | 0.310 |
| 5.2.2 LTS | current rest | 0.274 | 0.305 |
| 5.2.2 LTS | baseline row motion | 0.276 | 0.303 |
| 5.2.2 LTS | current row motion | 0.282 | 0.315 |
| 5.1.2 | baseline rest | 0.266 | 0.316 |
| 5.1.2 | current rest | 0.278 | 0.305 |
| 5.1.2 | baseline row motion | 0.282 | 0.319 |
| 5.1.2 | current row motion | 0.283 | 0.314 |

The measured change is small for this workload. No source-equivalent speed or
cross-platform input-latency claim follows from these CPU timings. The old/new
resting images are byte-identical. Every one of 100 current animated frames per
runtime matches between native BLF batching and standalone submission. Row
backgrounds, labels and icons now share their motion transform; clipping and
logical hit targets remain fixed. Resource records retain one backdrop, one
strong blur, five offscreens, one layout and unchanged recorded shader/batch/font
identities. Paint-facing model reads are separately checked for zero collection
iteration; membership/signature scans occur only on refresh or actions.

This evidence uses actual Blender pixels, not generated images. Exact reference,
theme/DPI and remaining search/decorator semantics are still open in the ledger.
Blender 4.2's default-name path is preserved and the newer item-string keyword is
capability gated; 4.2 and non-macOS runtimes remain unexecuted here.

## Compact search popovers — 2026-10-28

[Compact search QA v1](design/qa/search-popover-v1/index.html) records the default
compact `prop_search` / `template_search` presentation. The retained full-card
mode remains available through `Layout.search_popovers = False`. Closed fields
read the current property without enumerating candidates; opening builds a fresh
snapshot and gives keyboard focus without starting an edit until text arrives.

Both Blender 5.1.2 and 5.2.2 pass RNA and real-window checks for opening, immediate
typing, navigation, selection, field/candidate context menus, Escape/right-click/
outside-click cancellation, rejected host commits, stale values, per-control
motion disable, refresh cancellation and teardown. Successful selection closes
only the owning popover; rejection rolls back and leaves it open for correction.
Existing full-card, pointer/decorator and general runtime regressions pass, as do
full-card and pointer real-window tests. 79 unit tests, Ruff, compilation,
distribution build and parity-ledger checks pass. The ledger remains 40 partial
members of 137 and zero reference-matched members.

The 640×560, scale-1 Metal fixture uses two compact fields and optionally a
503-candidate virtualized picker. Paint measurements are 100 CPU submissions
after 20 warmups, excluding readback. Opening measurements are 25 event-preparation
samples, excluding drawing and readback:

| Runtime | Workload | Median ms | p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | closed fields | 0.119 | 0.154 |
| 5.2.2 LTS | prepare 503-row popover | 0.568 | 0.629 |
| 5.2.2 LTS | open picker paint | 0.235 | 0.267 |
| 5.1.2 | closed fields | 0.107 | 0.141 |
| 5.1.2 | prepare 503-row popover | 0.535 | 0.684 |
| 5.1.2 | open picker paint | 0.224 | 0.260 |

All 100 sampled frames per runtime match with native text batching enabled and
disabled. Resources retain one backdrop production, one strong blur, five
offscreens, one layout and unchanged recorded shader/batch/font identities.
The capture reproduces PanelHost's existing root glass pass before the canvas
tint; production root glass behavior is unchanged. New popup motion uses the
existing shared spring and owner settings. No per-frame capture or blur is added.
These timings establish a compact-search baseline, not equivalent-workload BVT
performance, GPU completion time or input latency. Exact generated-reference,
theme/DPI and motion acceptance remain open, as do 4.2 and non-macOS runtime checks.

## Named non-ID pointers and collection owners — 2026-10-29

[Non-ID pointer QA](design/qa/non-id-pointers-v1/index.html) adds Bone and Node
selection through explicit candidate/poll, revision and rollback policies. Pointer
fields and prop_search/template_search share the same strong-glass picker. The
public binding adapter now handles collection-owned properties such as
bones.active and nodes.active without native control delegation.

Both Blender 5.1.2 and 5.2.2 pass selection, clear, copy paths, rejected commits,
host snapshot restoration, stale revisions, renamed/removed candidates and deleted
containing-ID checks. Candidate Copy Name revalidates membership. Existing ID
pointer, search, compact-popover and general RNA regressions pass. Actual window
runs pass non-ID pointer/search typing, selection, field/candidate menus, Escape/
right-click cancellation and idle teardown; existing pointer/decorator and public
context-menu window fixtures pass too. 84 unit tests, Ruff, compilation, package
build and ledger validation pass. The ledger remains 40 partial / 137 documented
members, with zero reference-matched members.

The 640×560 scale-1 Metal fixture has one non-ID pointer and one compact search,
500 nodes plus the None row. Paint uses 20 warmups and 100 CPU submission samples;
opening uses 25 event-preparation samples. Readback is outside both measurements.

| Runtime | Non-ID workload | Median ms | p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | closed fields | 0.119 | 0.164 |
| 5.2.2 LTS | prepare 501-row picker | 1.111 | 1.261 |
| 5.2.2 LTS | open picker paint | 0.231 | 0.273 |
| 5.1.2 | closed fields | 0.114 | 0.141 |
| 5.1.2 | prepare 501-row picker | 1.128 | 1.248 |
| 5.1.2 | open picker paint | 0.214 | 0.239 |

The unchanged 503-ID search fixture was rerun against its prior published record.
The same five 5.2.2 static states have identical RGB pixels (rest, open, filtered,
field context and disabled). Equivalent-workload median timings are:

| Runtime | Workload | Previous ms | Current ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | closed fields | 0.119 | 0.114 |
| 5.2.2 LTS | prepare 503-row picker | 0.568 | 0.545 |
| 5.2.2 LTS | open picker paint | 0.235 | 0.235 |
| 5.1.2 | closed fields | 0.107 | 0.115 |
| 5.1.2 | prepare 503-row picker | 0.535 | 0.543 |
| 5.1.2 | open picker paint | 0.224 | 0.224 |

These separate-process samples show no material regression for this small fixture;
they are not controlled BVT source comparisons, GPU completion timing or input
latency guarantees. Each current capture retains one backdrop production, one
strong blur, five offscreens and recorded shader/batch/font/layout identities.
All 100 frames per version match with native BLF batching enabled and disabled.
No new production paint path, per-frame capture or candidate enumeration was added.

Non-ID revision/transaction callbacks are mandatory because public RNA addresses
and bound-pointer rollback alone cannot establish lifetime or setter-side-effect
safety. The host must qualify specialized setters. Hidden legacy bone flags and
all output-node transactions remain open. Native extension button-pointer overrides
for collection owners become lists and remain unsupported for struct-dependent
callbacks; shared host providers and normal property/candidate actions retain the
exact owner. Type-specific icons, broader non-ID models, exact generated-reference/
theme/DPI/motion acceptance, Blender 4.2 and non-macOS execution remain open.


## Enum grouping, modifiers and metadata — 2026-10-29

[Enum QA v2](design/qa/enum-properties-v2/index.html) adds nonselectable headings,
separators, grouped `props_enum` columns and native expanded-flag selection:
plain clicks select exclusively; Shift toggles individual flags. Individual
`prop_enum` buttons retain toggle behavior. Metadata helpers for item names,
descriptions and icon IDs match native results for tested static, dynamic and
missing choices. This is metadata coverage, not complete custom icon artwork.

Blender 5.1.2 and 5.2.2 pass RNA, real window input, menu/context regressions and
general runtime fixtures in disposable profiles. 102 unit tests, Ruff, compilation,
package build and ledger validation pass. The ledger has 43 partial members out
of 137, with zero reference-matched members. Three previously unimplemented
metadata helpers now have execution evidence.

At 1×, 1.5× and 2×, all 600 capture frames match with native BLF batching enabled
and disabled, including both heading and body fonts during opening motion.
Retained resources remain stable: one shared backdrop production, one strong blur,
five offscreens and recorded font/shader/batch/layout identities. These capture
checks do not establish exact generated-reference acceptance; Tyler owns visual QA.

The equivalent ungrouped workload uses the prior published revision `1e95dc8`
and the current checkout in separate processes. It contains one three-choice
scalar field and three individual enum buttons, 640×560 at scale 1 on Metal,
with 20 warmups and 100 CPU paint-submission samples. Readback is outside timing.

| Runtime | Workload | Before median / p95 ms | After median / p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 LTS | closed fields | 0.184 / 0.224 | 0.179 / 0.212 |
| 5.2.2 LTS | open scalar menu | 0.219 / 0.247 | 0.215 / 0.233 |
| 5.2.2 LTS | retained menu | 0.223 / 0.255 | 0.220 / 0.249 |
| 5.1.2 | closed fields | 0.187 / 0.244 | 0.180 / 0.204 |
| 5.1.2 | open scalar menu | 0.221 / 0.237 | 0.219 / 0.239 |
| 5.1.2 | retained menu | 0.231 / 0.274 | 0.222 / 0.260 |

The 5.2.2 resting and open benchmark images have identical RGB pixels before and
after. This small workload shows no material regression; it does not measure GPU
completion, input latency or equivalent BVT source performance.

Official versioned source was audited for 4.2, 5.1.2 and 5.2.2. The native adapter
change only opts into copying structural enum rows; ABI, bounds and ownership
remain unchanged, and both exact-build admissions pass. Public RNA fallback
preserves static choices and metadata but omits headings/separators on tested
runtimes. Grouping on other adapters, context-dependent menu persistence, custom
icons, popup search, specialized tab/focus behavior, complete localization and
broader theme/platform acceptance remain open. Blender 4.2 paths are retained;
no 4.2 executable was available for runtime qualification.


## Searchable long dropdowns — 2026-10-29

[Search QA](design/qa/menu-search-v1/index.html) covers shared menu search at the
default 12-option threshold. Labels and group names are matched on input; the
original Entry/action remains authoritative. Search covers enum and generic/nested
menus, no matches, disabled choices, clipboard/caret editing, query-first
cancellation, current owner validation and flag transactions. Existing pointer
and collection pickers retain their search path.

114 unit tests, Ruff, compilation and package build pass. Blender 5.1.2 and 5.2.2
pass RNA search tests, real window typing/selection/cancellation, enum regressions,
menu/context regressions and the general runtime fixture in disposable profiles.
The window test types 199 into a 200-choice dropdown, verifies no intermediate RNA
writes, accepts I199 once, then checks no-match clearing and exact property
right-click support. Concurrent RNA changes reject stale filtered selections.

At 1×, 1.5× and 2× on both runtimes, 600 actual production frames are identical
with native BLF batching enabled and disabled. Search/clear text participates in
the menu transform. One backdrop production, one strong blur and five offscreens
remain stable, along with recorded font/shader/batch/layout identities. Filtering
retires obsolete row motion while preserving the current reveal/search springs.
Disabling motion still leaves glass active, with no idle animation/tooltip timers.
Generated-reference, theme and motion visual acceptance remain with Tyler.

### Performance

The 200-choice capture filters a query over its cached labels in approximately
0.051 ms median / 0.055 ms p95 on 5.2.2 and 0.051 / 0.053 ms on 5.1.2 (100
input-only samples). Filtering and RNA preparation are outside the paint loop.

The separate equivalent-workload benchmark compares published `8085cb7` against
the current implementation: one 200-choice scalar field, three individual enum
buttons, 640×560, scale 1, Metal, 20 warmups and 100 CPU submission samples.
Framebuffer readback is excluded. Adding search intentionally adds one retained
field lens/text draw; it adds no capture, blur, font load or shader allocation.

| Runtime | Workload | Before median / p95 ms | After median / p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 | closed fields | 0.198 / 0.241 | 0.188 / 0.229 |
| 5.2.2 | open 200-choice menu | 0.356 / 0.384 | 0.339 / 0.362 |
| 5.2.2 | retained open menu | 0.374 / 0.424 | 0.352 / 0.388 |
| 5.1.2 | closed fields | 0.198 / 0.263 | 0.182 / 0.203 |
| 5.1.2 | open 200-choice menu | 0.356 / 0.397 | 0.325 / 0.358 |
| 5.1.2 | retained open menu | 0.369 / 0.456 | 0.341 / 0.420 |

These separate-process samples vary by a few hundredths of a millisecond; they
cannot isolate the marginal field-drawing cost or establish a speed improvement.
Short three-choice menu/resting benchmark pixels remain identical before and
after. Current short-menu medians are 0.222–0.243 ms. The new search field adds
one lens/text draw while retaining the existing backdrop and GPU resources.
These are CPU submission checks, not GPU completion/input-latency guarantees or
equivalent BVT source-speed claims. Raw timings, loaded-package paths and source
hashes are in the gallery.

Matching is stable all-word substring search, not fuzzy ranking. Search does not
scan unopened child providers. Existing admission limits remain (64 general menu
rows, up to 4096 enum rows); query length is bounded at 4096 characters. No new
Blender/native API dependency was introduced. Blender 4.2 runtime execution,
IME composition, broader themes/platforms and exact reference acceptance remain
unqualified. The ledger remains 43 partial / 137 members, zero reference-matched.


## BVT scalar layouts — 2026-10-29

[Slider/switch QA](design/qa/scalar-layout-v1/index.html) retains Tyler's original
screenshots beside production-rendered wide/compact sliders, switches, menu bools,
number entry and hue/alpha controls. Production follows the active theme; red is
an explicit comparison fixture without preference mutation. Geometry, shaders,
source spring behavior and 0.36-second switch easing come from audited BVT files.

121 unit tests pass. Blender 5.1.2 and 5.2.2 pass disposable-profile RNA tests,
real-window input, numeric regressions, context/menu regressions and the general
runtime fixture. Input covers absolute track positioning, relative drag, numeric
entry, rollback, exact owner menus, single boolean commits and idle teardown.
Hue/alpha tests preserve the other color components and route exact context parts.

150 frames per runtime/scale at 1×, 1.5× and 2× (900 total) are pixel-identical
with native text batching enabled/disabled. Motion includes handle dragging,
rapid switch retargeting, number entry, boolean menu reveal and hue/alpha input.
One backdrop production, one strong blur, five offscreens, font handles and
recorded shader/batch/layout identities remain stable. Static captures cover
motion disabled and settled appearance; no live scene or preferences were saved.

### Equivalent workload performance

Published `f048ce0` and the new implementation paint the same eight sliders and
three booleans, then the same property context menu. Both packages are loaded
from their verified paths, with fixture/source hashes in the gallery. Metal,
640×560, scale 1, 20 warmups and 100 CPU submission samples per state; framebuffer
readback is excluded. These are separate disposable processes.

| Runtime | Workload | Before median / p95 ms | After median / p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 | closed fields | 0.361 / 0.489 | 0.529 / 0.656 |
| 5.2.2 | open property menu | 0.557 / 0.694 | 0.674 / 0.827 |
| 5.2.2 | retained open menu | 0.598 / 0.827 | 0.731 / 0.939 |
| 5.1.2 | closed fields | 0.351 / 0.480 | 0.552 / 0.773 |
| 5.1.2 | open property menu | 0.542 / 0.654 | 0.740 / 0.872 |
| 5.1.2 | retained open menu | 0.556 / 0.796 | 0.757 / 0.891 |

The eight-slider layout adds about 0.17–0.20 ms median closed-field CPU submission
in these runs. Inspection attributes additional work to retained rail/fill,
handle/shadow draws and separate label/value text in place of the former minimal
underline field. Each slider retains its single number-cell glass lens; no new
backdrop/blur producer or steady-state shader/font/resource creation was added.
The new closed workload stays below 0.56 ms median here. This is a measured drawing
cost, not a speed improvement or proof of source-equivalent BVT performance.
GPU completion, input latency and broader dense/scrolling workloads remain outside
this fixture's qualification.

Source screenshots have unknown exact UI scale/theme/background, so no pixel-
exact reference acceptance is claimed. These requests supersede older scalar
artwork while preserving prior reference versions. Blender 4.2 paths remain;
4.2 execution, broader theme/platform coverage and full API parity are unverified.
The ledger remains partial; no member is promoted to reference-matched.


## Operator enum actions — 2026-10-29

[Operator choices QA](design/qa/operator-enums-v1/index.html) covers the new custom
`operator_enum` and `operator_menu_enum` paths. Expanded action buttons, grouped
choices, searchable 200-action dropdowns and exact operator context menus reuse
the existing BVT glass/button/menu painters. No new generated artwork or visual
approval is claimed; Tyler owns visual QA.

130 unit tests pass. Blender 5.1.2 and 5.2.2 pass disposable-profile operator tests,
real window input, enum/search regressions, context/menu regressions and general
runtime checks. Tests cover explicit EXEC/INVOKE behavior, pointer overrides,
extra arguments, singleton enum flags, public static fallback, dynamic numeric
remaps, changed arguments/selections, removed operators, poll failures, exact
command copy and host-registered shortcuts that reopen the custom popup. The
real-window fixture searches for action 199, verifies no execution while typing,
executes once with supplied arguments, cancels, clicks an expanded choice, opens
both right-click routes and verifies timer/bridge cleanup.

At 1×, 1.5× and 2× on both runtimes, 600 production motion frames are identical
with native BLF batching enabled/disabled. The captured workload retains one
backdrop production, one strong blur, five offscreens, fonts, style/skin shaders
and batches, lens batches and layout identity. Warm painting asserts zero dynamic
enum callback evaluations and no keyconfig creation. Scratch keyconfigs used for
input-time RNA preparation are released; neither scenes nor preferences are saved.

### Performance

Actual new controls: two dropdown buttons and expanded grouped operator actions,
then a 200-action menu and filtered result. Metal, 640×560, scale 1, 20 warmups,
100 CPU submission samples per state; framebuffer readback excluded.

| Runtime | Workload | Median / p95 ms |
| --- | --- | ---: |
| 5.2.2 | closed controls | 0.125 / 0.154 |
| 5.2.2 | open actions | 0.185 / 0.231 |
| 5.2.2 | open 200 actions | 0.295 / 0.332 |
| 5.2.2 | filtered actions | 0.170 / 0.195 |
| 5.1.2 | closed controls | 0.118 / 0.156 |
| 5.1.2 | open actions | 0.169 / 0.204 |
| 5.1.2 | open 200 actions | 0.272 / 0.330 |
| 5.1.2 | filtered actions | 0.160 / 0.190 |

The separate regression benchmark compares published `adbe5d6` with this change:
six identical action buttons and a searchable 48-action context menu using APIs
available in both revisions. It checks the shared renderer, not an older version
of the new operator-authoring methods. Resting and open-menu RGB pixels match
exactly on both runtimes. Same dimensions, warmups and CPU sample count as above.

| Runtime | Workload | Before median / p95 ms | After median / p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 | closed buttons | 0.098 / 0.140 | 0.085 / 0.140 |
| 5.2.2 | open 48-action menu | 0.277 / 0.327 | 0.233 / 0.304 |
| 5.2.2 | retained open menu | 0.288 / 0.363 | 0.246 / 0.309 |
| 5.1.2 | closed buttons | 0.095 / 0.125 | 0.089 / 0.119 |
| 5.1.2 | open 48-action menu | 0.268 / 0.323 | 0.239 / 0.271 |
| 5.1.2 | retained open menu | 0.273 / 0.335 | 0.263 / 0.358 |

No regression is evident in this sample; separate-process timing variation does
not establish an optimization. These measurements exclude operator execution,
dynamic callback work, GPU completion and end-to-end input latency. They do not
establish equivalence with a complete source BVT workload. Raw source hashes,
loaded-package paths, retained resources and timing records are in the gallery.

No new private ABI dependency or minimum Blender version was introduced. Exact
versioned API/Manual requests were blocked by the documentation service; official
4.2.0 and installed 5.1.2/5.2.2 source signatures were audited instead. Static
public RNA remains the compatibility fallback. Blender 4.2 execution, broader
theme/platform acceptance, custom icons/icon-only actions, complete native
OperatorProperties semantics and all layout/invocation contexts remain open.
The ledger now has 45 partial members out of 137, with zero reference-matched.

## Retained layout foundations — 2026-10-30

[Layout QA](design/qa/layout-flow-v1/index.html) records split layouts, balanced column flow, weighted/even grids, flexible row spacers, live inherited enable/active state and intrinsic row/column alignment. Every visible control uses the existing BVT material, theme, scalar geometry and motion paths. The user owns visual acceptance.

144 unit tests pass. Disposable Blender 5.1.2 and 5.2.2 runs pass real RNA, N-panel mouse/context input, operator regressions, native direction comparisons, vendorability and general runtime checks. The direction audit includes source snapshots across 4.2–5.2; a version gate preserves the grid-direction change in 4.5. No 4.2 runtime is installed.

360 motion frames at 1×, 1.5× and 2× match exactly with native font batching enabled/disabled. Captures preserve one shared backdrop, one strong blur, five offscreens and stable fonts/shaders/batches/layout. Closed painting evaluates each visible control eligibility predicate once. Reflow performs no binding reads; unchanged arrangement does not measure again.

### Performance

Metal, 640×560, logical scale 1. Each state uses 20 warmups and 100 CPU submission samples, excluding readback. The new layout fixture includes two numeric fields, six grid switches, four flow buttons and a disabled row.

| Runtime | New layout median / p95 ms |
| --- | ---: |
| 5.2.2 | 0.318 / 0.344 |
| 5.1.2 | 0.319 / 0.383 |

The unchanged-workload regression uses 144 buttons in 24 rows, a clipped/scrolled 520-pixel viewport and a 48-action menu. Published `d2be324` and current RGB pixels match in all ten sparse/dense comparison states across both runtimes.

| Runtime | Dense workload | Before median / p95 ms | After median / p95 ms |
| --- | --- | ---: | ---: |
| 5.2.2 | closed controls | 0.719 / 0.818 | 0.727 / 0.806 |
| 5.2.2 | open menu | 0.839 / 0.937 | 0.853 / 0.958 |
| 5.2.2 | retained menu | 1.189 / 1.261 | 1.239 / 1.390 |
| 5.2.2 | scrolled controls | 1.030 / 1.106 | 1.120 / 1.268 |
| 5.1.2 | closed controls | 0.734 / 0.810 | 0.700 / 0.740 |
| 5.1.2 | open menu | 0.878 / 0.987 | 0.870 / 0.976 |
| 5.1.2 | retained menu | 1.327 / 1.486 | 1.294 / 1.448 |
| 5.1.2 | scrolled controls | 1.134 / 1.280 | 1.123 / 1.243 |

The initial implementation walked ancestors during painting. Profiling workloads exposed that cost; inherited eligibility now updates on policy changes, spacers have no paint/hit-test entry, and painting resolves eligibility once per visible control. The final samples still vary by runtime/state: the 5.2.2 scrolled median is about 0.09 ms higher, while the 5.1.2 sample is slightly lower. These separate-process CPU timings do not establish a speedup, absence of every regression, GPU completion/input latency or full source-BVT workload equivalence. That broader performance gate remains open.

### Honest remaining scope

The ledger contains **95 unimplemented and 42 partial members**, zero reference-matched. Five missing authoring members gained implementations in this change. The audit also corrected eight inert attributes previously counted as partial: `activate_init`, `active_default`, `alert`, `emboss`, `scale_x/y` and `ui_units_x/y`. Their stored attributes remain compatible, but `supports()` now returns false. Full parity is not finished and `check_custom_parity.py --require-complete` correctly fails.

Remaining work includes specialized ID/list/preview, image/movie/scope, node/modifier/constraint, asset/menu/popover, header/status and multiline templates, the inert settings above, incomplete existing-editor semantics and exact-reference/theme/platform acceptance. No stub, generic form or native forwarding was counted as custom completion. See [layout limits](LAYOUT_FLOW.md) and the [member ledger](CUSTOM_PARITY.json).

## Data-block templates — 2026-10-30

[ID template QA](design/qa/id-templates-v1/index.html) records custom ID selectors,
name fields, user counts, Fake User switches, New/Open/Unlink routing and ID tabs.
The fixture includes ordinary fields to make host-scale comparison possible.
Generated-reference and user visual acceptance remain open; the new API entries
are partial. Remaining API coverage is 93 unimplemented and 44 partial members.

- 148 pure-Python tests passed, including dynamic binding ownership, stale editor
  dismissal, context snapshots and picker visibility filtering. Ruff, compilation,
  custom-ledger consistency and source/wheel packaging passed.
- Blender 5.2.2 LTS and 5.1.2 disposable-profile tests passed for real RNA name and
  Fake User edits, single-user copy/rollback, unlink, hidden names, rename-safe
  identity, deleted candidates, scene filtering and exact operator context.
  Native active-button operators require host dispatch; stale delayed requests,
  disabled layouts and unregistered operators reject execution. Deleting the
  owning ID disables all template controls before touching embedded RNA.
- Real N-panel input passed in both versions: Fake User mouse toggling, selected-ID
  property menus, text input renaming, keyboard picker selection, right-click edit
  cancellation and timer-free disabled-animation teardown. General and pointer/
  decorator regression fixtures passed in both versions.
- Six production GPU capture sets cover both runtimes at 1×, 1.5× and 2×,
  narrow width, picker and owner/tab menus. All 360 motion frames are pixel-equal
  with admitted native text batching enabled versus disabled. Candidate
  enumeration during painting is zero. Shader/batch/font/layout resources remain
  stable; shared glass produces one backdrop, one strong blur and five retained
  offscreens per capture host. No live user scene or preferences were saved.
- Equivalent sparse and dense/scrolled workloads were compared to published
  `8a321cb0e50211ffe3635a1593b996dcfd9f7303`. All ten settled image comparisons
  are RGB-equal. Warm CPU submission medians/p95 are recorded below; measurements
  exclude framebuffer readback and do not establish end-to-end GPU latency or
  full source-addon performance parity.

| Blender | Workload | Before median / p95 ms | After median / p95 ms |
|---|---|---:|---:|
| 5.2.2 | benchmark: closed_fields | 0.082 / 0.114 | 0.078 / 0.103 |
| 5.2.2 | benchmark: open_scalar | 0.228 / 0.253 | 0.222 / 0.252 |
| 5.2.2 | benchmark: open_scalar_retained | 0.243 / 0.292 | 0.233 / 0.281 |
| 5.2.2 | dense: closed_fields | 0.703 / 0.769 | 0.703 / 0.788 |
| 5.2.2 | dense: open_scalar | 0.824 / 0.905 | 0.828 / 0.896 |
| 5.2.2 | dense: open_scalar_retained | 1.176 / 1.249 | 1.190 / 1.332 |
| 5.2.2 | dense: scrolled_controls | 1.051 / 1.149 | 1.065 / 1.185 |
| 5.1.2 | benchmark: closed_fields | 0.081 / 0.116 | 0.080 / 0.099 |
| 5.1.2 | benchmark: open_scalar | 0.227 / 0.252 | 0.220 / 0.240 |
| 5.1.2 | benchmark: open_scalar_retained | 0.241 / 0.285 | 0.234 / 0.287 |
| 5.1.2 | dense: closed_fields | 0.703 / 0.788 | 0.734 / 0.822 |
| 5.1.2 | dense: open_scalar | 0.853 / 0.960 | 0.858 / 0.980 |
| 5.1.2 | dense: open_scalar_retained | 1.286 / 1.445 | 1.266 / 1.415 |
| 5.1.2 | dense: scrolled_controls | 1.079 / 1.215 | 1.070 / 1.161 |

No measured regression appeared in these workloads. The new ID-template layout
was measured separately with 20 warmups and 100 paint samples; per-runtime/scale
results and exact source hashes are in the gallery. Blender 4.2 runtime, additional
platforms/themes, specialized ID operations and full visual acceptance remain open.

## Registered menus — 2026-10-30

`menu`, `menu_contents` and enum `prop_with_menu` now use the custom menu engine
and current Layout controls. [Registered menu QA](design/qa/registered-menus-v1/index.html)
contains actual captures and an animated README overview. The ledger now records
**90 unimplemented and 47 partial members, zero reference-matched**. Full custom
parity and generated-reference acceptance remain unfinished.

- 154 pure-Python tests pass. Ruff, compilation, ledger consistency and source/
  wheel packaging pass; the wheel contains the new registered-menu module.
- Blender 5.2.2 LTS and 5.1.2 disposable runtime and N-panel input fixtures pass:
  scalar/toggle commits, enum property context, nested Python draw helpers,
  operator arguments/overrides, search over 100 actions, exact-row clipboard
  actions, edit cancellation, stale/unregistered definitions, input-time polls,
  inherited disabled state and disabled parent/child execution. Unsupported draw
  calls fail atomically; oversized row collections fail explicitly.
- Existing general, pointer/decorator, ID-template, operator-enum and context-menu
  regression fixtures pass in both versions. The clipboard context fixture runs
  in a disposable window because background mode cannot qualify that behavior.
- Six production capture sets cover 1×/1.5×/2× on both runtimes, narrow hosts,
  inline controls, nested row context, search and property-attached menus. All
  360 motion frames match with native text batching enabled versus disabled.
  Painting invokes zero menu draw or poll callbacks. Font/shader/batch/layout
  identities remain stable; glass retains one backdrop, one strong blur and five
  offscreens. No user scene or preferences were saved.
- Hover in a 100-action registered menu invokes at most 19 operator polls rather
  than repolling every hidden action. Offscreen shortcut execution rechecks
  eligibility. Draw-time selection snapshots are shared by equivalent context
  overrides; full selection revalidation occurs on activation.
- Before/after sparse and dense/scrolled workloads use published `cf97828` as the
  baseline. All ten settled image pairs are RGB-equal. The following warm CPU
  submission samples use 20 warmups and 100 samples per state, excluding capture.
  They do not measure GPU completion or full source-addon equivalence.

| Blender | Workload | Before median / p95 ms | After median / p95 ms |
|---|---|---:|---:|
| 5.2.2 LTS | benchmark: closed_fields | 0.080 / 0.101 | 0.080 / 0.113 |
| 5.2.2 LTS | benchmark: open_scalar | 0.229 / 0.252 | 0.222 / 0.258 |
| 5.2.2 LTS | benchmark: open_scalar_retained | 0.237 / 0.290 | 0.224 / 0.252 |
| 5.2.2 LTS | dense: closed_fields | 0.735 / 0.815 | 0.689 / 0.776 |
| 5.2.2 LTS | dense: open_scalar | 0.872 / 0.972 | 0.805 / 0.861 |
| 5.2.2 LTS | dense: open_scalar_retained | 1.286 / 1.437 | 1.124 / 1.212 |
| 5.2.2 LTS | dense: scrolled_controls | 1.106 / 1.276 | 1.011 / 1.098 |
| 5.1.2 | benchmark: closed_fields | 0.083 / 0.113 | 0.079 / 0.098 |
| 5.1.2 | benchmark: open_scalar | 0.227 / 0.274 | 0.222 / 0.250 |
| 5.1.2 | benchmark: open_scalar_retained | 0.236 / 0.283 | 0.230 / 0.279 |
| 5.1.2 | dense: closed_fields | 0.710 / 0.799 | 0.734 / 0.884 |
| 5.1.2 | dense: open_scalar | 0.829 / 0.978 | 0.885 / 0.991 |
| 5.1.2 | dense: open_scalar_retained | 1.244 / 1.396 | 1.291 / 1.453 |
| 5.1.2 | dense: scrolled_controls | 1.076 / 1.249 | 1.143 / 1.272 |

The 5.1.2 dense samples are modestly higher while the 5.2.2 samples are lower.
A [reverse-order investigation](design/qa/registered-menus-v1/performance-investigation.json)
on the preceding candidate showed the 5.1.2
scrolled median changing from 1.100 ms baseline to 1.076 ms candidate, with a
higher candidate p95 (1.416 versus 1.226 ms). This variability does not establish
a speedup or exclude a small regression. The production change adds a constant
eligibility lookup to ordinary controls; registered-menu guards and polls run
only for their owners/input. No additional GPU resource production was observed.
Broader controlled source-speed qualification remains open.

Blender 4.2 runtime, other platforms/themes, native-instance draw semantics,
specialized controls and exact visual/motion acceptance remain open. See
[REGISTERED_MENUS.md](REGISTERED_MENUS.md) for the supported draw subset and limits.
The strict completion gate still correctly fails.
