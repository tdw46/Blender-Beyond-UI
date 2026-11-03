# Necessary-update BUI optimization — installed 2026-11-03

The new optimization is installed and loaded in the working CamKeys session.
It skips unchanged main/Linking panel author callbacks, patches changing angle-row
labels without recording the whole row, and removes redundant owner resolution
within one property read. Glass, styling, motion and scene evaluation remain enabled.
This removes identified redundant work; it does not remove the cost of painting
visible controls or evaluating the character.

## Measured results

Actual NVIDIA RTX 4090 Laptop GPU / driver 591.74, official Blender 5.2.2 LTS
`d13f752e3b9c`, Vulkan. Copied Uraraka, four angle rows visible, separate 1280×900
factory-profile windows. These are CPU submission timings, not GPU elapsed time.
Nested rows overlap their parent; do not sum them.

| Slice | Before | Installed candidate | Reduction |
| --- | ---: | ---: | ---: |
| Angle panel authoring/refresh dispatch | 3.554 ms | 1.559 ms | 56.1% |
| Visible list refresh (included above) | 1.647 ms | 1.203 ms | 27.0% |
| Angle panel painting | 6.214 ms | 5.838 ms | 6.0% |
| Single row painting (included above) | 1.023 ms | 0.934 ms | 8.7% |

Before: 73 full row-author callbacks
during 90 updates. After: **zero**, with the current labels still verified. Actual
layout rebuilds were zero in both warm runs. The separate uninstrumented orbit
medians were **38.55/38.82 ms before** and
**33.89/34.93 ms after** (about
11.1% lower across the two
run medians). These are event-loop update intervals, not GPU FPS. They are a
small repeated sample, not a long-duration benchmark or every-layout guarantee.

The live working session was measured separately with the main panel visible:

| Working session | Main author/refresh dispatch, idle median | Whole-process CPU-seconds, two idle samples |
| --- | ---: | ---: |
| Before | 0.962 / 0.913 ms | 1.578 over 5.03s / 1.281 over 5.04s |
| After | 0.423 / 0.411 ms | 1.062 over 5.03s / 0.969 over 5.20s |

These live samples include BVT spring simulation, Normal Keys and the rest of the
working profile. The live addon reload is also a confound for whole-process CPU;
do not attribute all of its reduction solely to BUI. The main panel still paints
the changing viewport-backed glass, about 30 Hz here. Its expensive authored
command recording is reused while dependency checks and live row/field refresh
continue. The independent fixture proves moving viewport values update without
rerunning the panel author callback.

## Fidelity and correctness

The before/after settled angle-panel PNGs are **byte-identical** (420×688):
SHA-256 `f9ae230e215a4aa921fdc631948288060075542c218b3bc9533ec155e0c05d4b`.
An apparent incomplete image in the preview was not present in the saved files;
repeated captures confirmed the same image. This verifies this settled panel,
not every theme/popover/animation frame. No renderer, shader, bridge, theme,
blur/transparency or animation setting was changed.

- 431 unit tests passed, including revision invalidation, label patching, exact
  owner replacement, readonly/missing properties and custom binding overrides.
- Vulkan and OpenGL each passed seven new dependency/runtime checks: live labels
  during orbit with no panel authoring; falloff/help/distance/selection branches;
  same-size reorder; deletion; main-panel reuse; camera-mode invalidation.
- Nine registered-list interaction checks passed, covering exact property context
  actions, copied paths, enum keys, text edit cancellation on owner move, search,
  right-click cancellation, disabled owners and callback replacement.
- Five scroll/offscreen checks passed, including no hidden author work, stable
  native scroll, current values on return and hidden deletion/replacement.
- The row revision runtime fixture additionally checked text-only updates without
  row callbacks and deleted-owner rejection even inside the paint scope.
- Warm actual viewport-backed glass/resources and live output checks passed.
  The isolated 30-second sample had zero idle panel draws/paints and stable owners.
  That earlier run tested the content-key stage; final working-session samples
  confirm stable glass allocations and no errors with the full change.

| Backend | This change's acceptance | Limit |
| --- | --- | --- |
| NVIDIA Vulkan | PASS | Runtime, measurements, exact settled screenshot, input/scroll regressions |
| NVIDIA OpenGL | PASS | Separate process; dependency/live-value/native-adapter checks; no new OpenGL performance claim |
| macOS Metal | UNVERIFIED on current hardware | Shared-code tests pass; all native package/source files unchanged; no Mac execution available |

All six custom native adapters are admitted in the working session; native
fallback is not counted as success. No draw/input errors were reported. Focus
audits observed no owned test window becoming foreground. Software CI was not
used as NVIDIA acceptance.

## Implementation and ownership

The reusable library adds explicit `beyond_ui_draw_cache_key(context)` panel
revisions and companion `draw_item_texts(...)` list refresh. Consumers declare
dependencies; arbitrary panels are not silently cached. Scene/context, viewport
width, scale, language and disclosure/list state also invalidate; undo/redo/load
revoke cached canvases. CamKeys opts in only its main and Linking panels through
`ui_revisions.py`, plus its angle and tracked-object row callbacks.

Visible collection membership is rechecked during refresh. Synchronous row paint
checks common context once at entry but keeps exact membership and RNA-owner
validation on every field access. The combined RNA reader resolves and validates
the same current owner once per read; it retains no owner between reads. Custom
`get`/`valid` overrides retain their original behavior. Controls, live edits,
context actions, fixed-width geometry and motion are retained on text updates.

Source contract: `docs/PANEL_CONTENT_REVISIONS.md` and `docs/REGISTERED_LISTS.md`.
Changes are in the isolated Beyond UI and CamKeys worktrees and installed vendor;
the validation snapshot preceded publication. Consult Git history for the published revisions.

## Installed state and backup

- Installed source: `C:\Users\tyler\Documents\Blender\extensions\user_default\CamKeys`.
- Installed base HEAD: `2dcc2a1320cf14872bc0c8b827815b33f9fce166` plus explicitly recorded local edits.
- Full pre-install source backup: `C:\Users\tyler\Documents\CamKeys-Backups\content-revisions-20261103-065713\CamKeys`.
- `content-cache-install.json` records eight installed files and before/after
  hashes. New `ui_revisions.py` is marked absent in the original backup.
- Final live verification checked all 226 vendored
  file hashes and confirmed all 46 native package/
  source files unchanged, including Metal artifacts.
- Working file/frame/dirty state/selection, sidebar grouping and existing modal
  services restored. Temporary probes removed. Full BUI and glass remain enabled.
  Neither the scene nor preferences were saved. Normal Keys/BVT remain enabled;
  Extreme PBR stays removed as previously requested.

## Reproduce and inspect

Evidence root: `C:\Users\tyler\Documents\CamKeys-Perf-20261102`.
Use the bundled Python at `C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe`.

1. Run `run_fixture.py tests/blender_panel_content_revision.py --windowed --backend vulkan`
   or `--backend opengl`. Each run uses its own process/profile and the existing
   copied `Uraraka-perf.blend`; the original scene is never opened for writing.
2. Run `run_fixture.py <absolute content_cadence_fixture.py> --windowed --backend vulkan`
   with `--source <absolute baseline-content-cache>` for the prior source or the
   default isolated candidate. Keep suffixes distinct. Captures happen after timings.
3. `bui_list_slices_fixture.py` is the separate lightweight CPU-probe workload;
   do not mix these intervals with the uninstrumented cadence measurements.
4. Live before/after records are `bui-slices-content-before.json` and
   `bui-slices-content-after.json`. Their bounded scripts use the existing local
   MCP transport and automatically restore probes, view and transforms. Run only
   on the identified untouched diagnostic session, never concurrently.
5. See fixture directories for raw JSON, Blender logs, profile and focus audit.
   Final loaded-source/admission/hash checks are in `content-runtime-final.json`;
   reload restoration is `live-reload-content.json`.

No new long-duration soak, complete interaction matrix, or Mac hardware result is
implied. Earlier QA remains separate. The initial new fixture caught a redundant
first redraw caused by newly initialized list state; that was repaired and its
rerun passed. A background launch of the timer-based registered-list fixture
produced no result because Blender exited; its correct windowed rerun passed all
nine checks. Failed attempts remain in the evidence directory for transparency.
