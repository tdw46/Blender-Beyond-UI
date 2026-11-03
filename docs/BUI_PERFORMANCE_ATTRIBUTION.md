# BUI cost attribution — 2026-11-02

BUI still has measurable overhead, concentrated in the visible angle list and
unchanged panel authoring during viewport-driven redraws. This investigation did
not implement another production optimization. Earlier installed fixes remain.

## Controlled BUI/native comparison

| Workload | Full BUI median intervals | Native Blender panels | Interpretation |
| --- | --- | --- | --- |
| Active Uraraka, character translation, main panel visible | 25.44 / 26.78 / 26.60 ms | 26.11 / 25.90 ms | No clear BUI movement penalty in this layout |
| Active Uraraka, orbit, main panel visible | 28.84 / 23.92 / 11.57 ms | 27.86 / 26.76 ms | Large run-to-run drift; no reliable causal delta |
| Copied Uraraka, orbit, four angle rows visible | 43.17 / 37.35 ms | 32.04 / 29.03 ms | Both BUI runs slower; approximately 10 ms difference between average run medians, not a universal per-frame cost |
| Active session, 5 seconds without input | 1.61 / 1.80 / 1.95 CPU-seconds | 1.00 / 0.97 CPU-seconds | BUI adds idle CPU work in this running session |

These are timer/event-loop intervals, not GPU FPS. Native uses different panel
geometry and painter. It is a whole-UI alternative, not a pixel-matched rendering
test or accepted BUI fallback. Do not compare absolute timings between the live
and copied profiles. The live angle panel was offscreen and parked.

CamKeys evaluation stayed enabled throughout. BVT and Normal Keys stayed enabled
in the live session; BVT's spring simulation remained running. The copied profile
isolates CamKeys, but the working Blender instance remains open. Repeated full/
native runs reduce order bias, not all system variability. Shape-key outputs
changed during every copied-scene run (49–54 distinct output tuples).

## BUI CPU slices

Separate lightweight probes measured CPU submission work. Nested rows overlap
their parent timings: do not add all rows or subtract medians to derive totals.
The heavy cProfile run is used only to identify code paths, never as cadence data.

| Slice | Main panel, live idle | Visible angle panel, orbit | Scope |
| --- | --- | --- | --- |
| Panel authoring + refresh | 1.07 ms/call | 2.81 ms/call | Includes row refresh and recorded author callbacks |
| Panel paint | 0.70 ms/call | 4.61 ms/call | Includes row paint, bindings and glass submission |
| Whole list refresh | Not separately probed | 1.31 ms/call | Included in panel authoring |
| One angle row paint | Offscreen | 0.79 ms/call | Four row paints per panel paint; included above |
| One changed row author callback | Offscreen | 0.48 ms/call | 75 callbacks across 90 panel refreshes, not 360 |
| Glass CPU submission | 0.058 ms/call | 0.093 ms/call | Included in paint; not completed GPU blur/copy time |
| Layout arrange entry | 0.0014 ms/call | 0.0022 ms/call | Zero actual relayouts in either measured workload |

The main panel was authored/painted 151 times in 5.03 seconds (about 30 Hz), with
zero authored-signature changes and zero changes in sampled visible parent
bindings/labels. The repeat idle sample also had 151 paints and no authored
changes. This sampling does not prove all scene data was stationary: it covers
the visible parent controls, not recursive/offscreen list contents.

Temporarily disabling glass stopped the main panel's idle authoring/painting and
backdrop production. Process CPU fell to 1.05 CPU-seconds over 5.05 seconds versus
1.69/1.72 in the instrumented full-glass samples. This switch disables the
viewport-to-sidebar refresh request as well as glass, so this is NOT a pure GPU
blur benchmark. The uninstrumented no-glass sample was noisier (1.52 CPU-seconds).
Full glass was restored automatically.

Source trace: `gpu/glass.py:viewport_changed` increments the viewport revision and
tags a valid sidebar for redraw. `hosts/addon.py:draw` records the adopted panel
again before comparing its signature, even when its retained layout is unchanged.
`hosts/panel.py:_paint` then presents the controls and current backdrop. Thus a
changing viewport can trigger unchanged UI authoring. The origin of every viewport
redraw was not isolated in this pass; the active BVT simulation means no-input
idle is not a quiescent scene.

The separate angle-list profile attributes 0.829 seconds of the 1.158-second
panel-paint total to four-row painting over 90 callbacks. Authoring was 0.772
seconds, including 0.399 in the consumer panel callback and 0.338 in list refresh.
Within these nested paths, style normalization/recording/freezing and repeated
exact-owner/binding validation remain substantial. The prior row cache is working:
only changed rows were reauthored. All 360 visible rows still painted and resolved
their dynamic bindings. Profiling overhead is substantial; use the lightweight
slice table for absolute timings.

The measured Python slices do not account for all process CPU or GPU time. Native
Blender UI overhead, driver work and scheduling remain outside this attribution.
Stable retained counts (one glass owner, 15 allocation-counter units throughout
live warm samples) argue against resource recreation in these short tests. This
is not a long-duration memory-growth qualification.

## Proposed fixes, before production edits

1. Separate backdrop/presentation invalidation from panel-content invalidation.
   Preserve current viewport glass while reusing unchanged authored content.
   Establish explicit dependency/revision invalidation for structure, labels,
   selection, collections, theme, scale, undo/redo and owner replacement; do not
   blindly cache arbitrary third-party panel callbacks.
2. Reduce repeated style/tape recording and exact-owner resolution within one
   synchronous row refresh/paint. Keep stale-owner checks, dynamic enabled states,
   live values and independent input-time ownership checks. Reuse only data whose
   dependencies are unchanged. Do not turn off Normal Keys or CamKeys evaluation.
3. Validate the change with this full/native workload plus live values, scrolling,
   offscreen return, context actions and undo. Preserve blur, transparency,
   animations and backend behavior. Geometry caching already works; rebuilding
   the layout system is not the first target.

These are newly identified optimization tasks, not completed fixes. The evidence
does not support claiming all remaining movement latency belongs to BUI, nor that
disabling glass is an acceptable repair.

## Runtime, preservation and coverage

- Official Blender 5.2.2 LTS, build d13f752e3b9c; Vulkan, RTX 4090 Laptop GPU,
  NVIDIA 591.74. Windows 11 build 26220; 150% display scale, UI scale 1.0
  (effective 1.5). Environment details retained from this session's earlier audit.
- Live viewport 1720×798; sidebar 563×718, NPR category at top. Copied fixtures
  use a separate 1280×900 window/profile and expose only the Linking panel.
- Installed source is `C:\Users\tyler\Documents\Blender\extensions\user_default\CamKeys`.
  Exact HEAD and matching installed/fixture file hashes are in
  `evidence/bui-attribution-provenance.json`; dirty earlier performance edits
  are explicit, not represented as an unmodified commit.
- All six custom native adapters admitted; no UI draw/input errors. BUI/native
  switching used complete BUI ownership stop/adopt with CamKeys RNA and engine
  intact. Temporary probes targeted plain Python helpers, not registered RNA.
- Live file, dirty state, frame, selection, active object, rig/view, sidebar,
  category and scroll restored. All temporary live probes removed. Full BUI,
  glass, CamKeys and BVT modals restored. No scene or preferences saved this turn.
- Isolated windows never became foreground in 50 ms focus audits. Each fixture
  unregistered its owned extension and released all glass owners before exit.
  Blender's disposable quit recovery file is inside its test profile only.
- This attribution pass is **Vulkan verified**. OpenGL and Metal attribution are
  **unverified**; prior backend acceptance does not substitute for new timings.
  No new screenshot/clip: this pass changes no visuals and captures numerical
  CPU/callback evidence. No claim of a measured Windows-versus-Mac difference.

## Reproduction and raw evidence

Work from `C:\Users\tyler\Documents\CamKeys-Perf-20261102` using the bundled Python
at `C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe`.

1. Keep the intended Uraraka MCP session untouched, with full BUI, NPR sidebar
   at the top and the prior working addons enabled. Verify it is the diagnostic
   scene, not another open Blender instance. Run `mcp_client.py bui_ab_live.py`.
   Wait for `evidence/bui-ab-live.json` to show `running:false, passed:true`.
2. Run `mcp_client.py bui_slice_probe.py`; wait for `evidence/bui-slices.json` to
   finish and pass restoration. Never run measurement scripts concurrently.
3. For copied-scene angle-list comparison, run `prepare_bui_list_ab.py`, then
   `run_fixture.py <absolute-path-to-bui_list_ab_fixture.py> --windowed --backend vulkan`.
   Uses the existing copied `Uraraka-perf.blend` and isolated `camkeys` checkout.
4. Run `prepare_bui_list_slices.py`, then
   `run_fixture.py <absolute-path-to-bui_list_slices_fixture.py> --windowed --backend vulkan --suffix=-bounded`.
   Inspect result JSON, Blender logs and focus audit beneath the matching evidence
   directory. `bui-list-profile.txt` is the readable heavy-profile breakdown.
5. Check all restoration/admission assertions before any further UI work. The
   live scripts restore state automatically; never use their temporary no-glass
   mode as the installed configuration.

No source fix is installed by these scripts. The test files retain all workloads,
sample counts, discarded warm intervals and timing boundaries for review.
