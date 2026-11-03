# Uraraka viewport performance repair — 2026-11-02

Installed and loaded into the existing Windows Uraraka session. No scene or
preferences were saved. The guarded reload restored the previously running BVT
and CamKeys operators, frame 173, selection, transforms and existing NPR sidebar
grouping. The original file remains dirty. All six CamKeys native adapters are
admitted; no native fallback or UI errors. The visible host records are present;
the angle list is currently clipped/parked, with all four source entries intact.

## Changes

- Beyond UI reuses recorded command signatures instead of freezing unchanged
  commands repeatedly. Fixed-width live labels update without rebuilding layout,
  cancelling edits/menus, resetting motion or invalidating the backdrop.
- UIList callback signature inspection occurs once per widget. An optional,
  consumer-supplied authored-row revision retains unchanged row tapes. CamKeys
  angle rows declare all authored text/search-owner inputs; bound fields retain
  live RNA reads and exact-owner editing guards.
- Row paint resolves its window/area/scene scope once within that synchronous
  read-only call. Owner/membership checks remain live. No cache spans input or
  another paint. RNA array/scalar reads resolve their owner once per getter.
- BVT caches the VRM search module identity, invalidating on removal/replacement.
  Armature/context/function results are never cached. Warm lookup no longer
  scans unrelated imported modules or invokes their dynamic attribute hooks.
- Normal Keys fast-forward pull confirmed latest remote commit 3a5e1ff; its
  geometry evaluation and feature settings were not changed.

## Measured performance

Official Blender 5.2.2 LTS d13f752e3b9c; NVIDIA RTX 4090 Laptop, driver 591.74;
Windows 11 build 26220. Display scaling 150%, Blender UI scale 1.0 (effective 1.5).
Separate factory profiles and a disk copy of Uraraka-diagnostic.blend; 1280×900
nonactivating test windows. Warm samples discard the first ten updates per phase.
No-focus auditing observed no owned test window take foreground focus.

| Vulkan workload | Before median | After median | Before p95 | After p95 |
|---|---:|---:|---:|---:|
| Orbit | 14.56 ms | 11.90 ms | 50.95 ms | 39.38 ms |
| Armature-object movement | 34.28 ms | 24.82 ms | 49.72 ms | 32.24 ms |
| Panel authoring | 4.36 ms | 2.08 ms | 8.63 ms | 4.30 ms |
| Panel painting | 6.12 ms | 4.30 ms | 11.78 ms | 7.27 ms |

Orbit/movement values are timer/event-loop update intervals, **not GPU FPS**.
Authoring/paint are CPU submission timings. The isolated profile does not load
all working-session add-ons and cannot be compared directly with the earlier
40–43 ms all-add-on measurement. A subsequent authorized full-session comparison is documented below. Ordinary
mouse-driven posing remains user QA.

The live loaded module-registry lookup benchmark improved from 0.7925 ms median
to 0.0002 ms. This measures the resolver alone, not total converter-panel cost.
30-second idle tests on both GPU backends recorded zero BUI draws and paints,
stable retained owner counts and no errors. Total Blender idle CPU remains
nonzero and is not claimed fixed by these UI changes; raw CPU/memory values are
in the result JSONs. These short runs are not long-duration resource-soak proof.

## Validation

| Check | Vulkan/NVIDIA | OpenGL/NVIDIA | Metal/macOS |
|---|---|---|---|
| Native admission, live Uraraka shape/list values, idle owner stability | Pass | Pass | Unverified on hardware |
| Registered list editing, stale owners, deferred menus | Pass | Not repeated | Unverified on hardware |
| Scrolling/offscreen refresh and native panel height | Pass | Not repeated | Unverified on hardware |
| Matched orbit/object-movement cadence | Improved | Not measured | Not measured |
| Safe complete BVT/CamKeys reload and restored engines | Pass | Not repeated | Not repeated |

421 Beyond UI unit tests and three BVT discovery tests passed. A new Blender
fixture covers skipped unchanged authoring, live bound values, changed literal
text, layout-only passes and deleted-owner rejection. Existing registered-list
fixture passes nine interaction checks; scrolling fixture passes five checks.
The first isolated reload attempt correctly refused teardown while a spring
modal remained. The corrected harness suppresses automatic engine restart,
waits for actual modal exit, uses complete ownership teardown/re-enable, then
explicitly restores previously running engines. No registered callbacks were
hot-patched in the working session. A background launch of the timer-based list
fixture produced no result; its proper windowed rerun passed.

Metal binaries, native bridges, shader sources, backend gates and qualification
files are unchanged. Shared Python behavior is unit-tested; this is not fresh
Mac hardware acceptance. No native optimization was disabled to improve timing.

BVT's existing shader/worker optimization was already unadmitted before this
repair: its installed certificate disagrees with VRM_Compositor.py and renderer
shadow_scene.py. The baseline and candidate preflight failures are identical.
This separate pre-existing renderer qualification issue was not papered over
with new hashes. It is distinct from CamKeys' successfully admitted UI adapters.

## Reproduction and evidence

1. Use the official executable at `C:/Program Files/Blender Foundation/Blender 5.2/blender.exe`.
2. Run `run_fixture.py cadence.py --windowed --backend vulkan --source <baseline-or-candidate-CamKeys> --suffix=<label>` from this evidence root with Blender's bundled Python. Each run creates a fresh profile, uses the scene copy and exits its own process.
3. The fixture exposes the angle list, performs 60 view steps and 60 armature
   translation steps, restores both, then measures 30 seconds of idle.
4. For behavior, run `tests/blender_registered_lists.py` and
   `tests/blender_panel_scroll.py` with `--windowed --backend vulkan`.
5. Restart into OpenGL via a separate `run_fixture.py tests/blender_camkeys_hardware.py --windowed --backend opengl` invocation.

Evidence root: `C:\Users\tyler\Documents\CamKeys-Perf-20261102\evidence`. Per-run folders contain result JSON, command summary,
Blender log and focus audit. `live-reload.json` and
`live-installed-verification.json` record loaded installed code and runtime
admission. No new visual styling was introduced; no new screenshots/clips were
captured for this performance-only pass.

Backup: `C:\Users\tyler\Documents\CamKeys-Backups\viewport-performance-20261102-190927`. Its manifest identifies all six changed installed files,
original commits and before/after SHA-256 values. Restore these files only while
their owning add-ons are disabled or Blender is closed, then reload/restart.
The installed changes remain uncommitted for review; no branches were merged or
pushed in this performance pass.

## Full working-session follow-up — untouched interval authorized

After the user's confirmation, the active Vulkan/Solid session was measured
with all existing add-ons enabled, at its existing 1720×798 viewport size.
Each condition uses 45 timer-driven orbit or armature-object movement steps,
discards the first five intervals, and repeats the sidebar-enabled condition.
The same script/state was used before and after the additional Extreme PBR
repair. There was no downgrade of CamKeys/BVT, disable of Normal Keys, change of
GPU backend, foreground activation or scene save.

| Full session, median ms | CamKeys/BVT fixes loaded | Redraw loop removed only | Final: cloud readiness cached |
|---|---:|---:|---:|
| Orbit | 34.66 | 35.78 | 24.55 |
| Orbit repeat | 32.10 | 37.26 | 24.85 |
| Character movement | 32.46 | 35.09 | 23.39 |
| Character movement repeat | 35.30 | 37.79 | 24.35 |

The historical 40–43 ms measurements predate these repairs and used a different
script; they are context, not a tightly matched combined speedup percentage.
These new measurements are event-loop intervals, not GPU FPS or physical mouse
drag latency. The angle list remained clipped in the current working layout;
its cache is exercised by the separate copied-scene tests above.

The residual profile identified Extreme PBR panel polling as a separate cause:
`Polling.poll()` requested another area redraw unconditionally and repeatedly
checked library files on the user's G: Google Drive path, even with its tab
closed. File/directory existence checks consumed about 5 ms per sidebar redraw
in the profiled run. Removing the redraw loop alone reduced idle work but did
not improve navigation cadence in its measured run; the bounded readiness cache
produced the interaction improvement in the table.

The local Extreme PBR patch removes the self-triggering redraw and keeps one
library-readiness snapshot for at most 500 ms. Path or installer-state changes
invalidate it immediately; explicit Refresh also invalidates it. Material,
selection and operator state outside those filesystem checks remain live. No
polling timer was added, no library paths changed and no add-on was disabled.
Thirty-two readiness/operator-state combinations match the original results;
tests also cover 100 warm polls, expiry, changed paths and explicit invalidation.
The patch is installed in `extreme_pbr/UI/main_ui_panel/main_ui_v2.py`. Its plain
Python helper and refresh function were refreshed in memory; registered RNA
classes/callbacks were not replaced or reloaded. The original file is backed up
at `extreme-pbr-backup/ui/main_ui_panel/main_ui_v2.py` beneath this evidence root.
The installed third-party update may overwrite this local patch in the future.

Final full-session restoration checks pass for file, frame, dirty flag, sidebar,
category, active object, selection, view and rig transform. All six native UI
adapters remain admitted and UI error collections are empty. Fifteen-second
idle CPU usage fell from 9.42 to 5.63 CPU-seconds; backdrop productions fell from
1,365 to 450. BVT simulation remains running, so this working session is not
quiescent. Retained canvas/host/glass owner counts stayed stable. This is not a
long-duration soak or new Mac/OpenGL hardware qualification of the Extreme PBR
change.

Raw evidence: `evidence/live-cadence-after.json`, `live-cadence-final.json`,
`live-cadence-cloud-cache.json`, `live-remaining.prof`, and
`extreme-pbr-repair.json`. Reproduce the final full-session test through the
existing Blender MCP transport with `live_measure_cache.py`, only during an
untouched interval; it restores state automatically and never saves.

## Final installation state: Extreme PBR removed at user request

Extreme PBR was fully disabled through its own unregister lifecycle. No owned
registered classes or application handlers remained. Blender preferences were
saved so it stays disabled. Its complete extension folder was moved outside
Blender to `C:\Users\tyler\Documents\CamKeys-Backups\extreme-pbr-removed-20261102-205810/extreme_pbr`. The previous preferences file is
backed up alongside it. The cloud material libraries were not moved or deleted.
All 55 scene objects and eight materials remain; the dirty Uraraka scene was
not saved. The Extreme PBR local patch discussed above is now in this backup,
not in Blender’s active extension directory. CamKeys/BVT fixes remain loaded.

Post-removal full-session validation passed all restoration/native-admission/error checks.
Orbit medians were 27.97 and 30.30 ms; movement medians 34.12 and 24.97 ms.
The hidden-sidebar orbit sample was also unusually slow (29.93 ms), so this
variable run does not establish an additional speedup or regression from
removing Extreme PBR versus its preceding cache patch. All raw samples remain
in `evidence/live-cadence-pbr-removed.json`. Idle retained owners stayed stable;
15 seconds used 5.28 CPU-seconds with BVT simulation still active.
