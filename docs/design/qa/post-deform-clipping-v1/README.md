# Post-deformation camera clipping — schema 24

The actual camera/viewport clips the deformed triangles. No pre-deformation cut boundary is reconstructed. The schema-23 hidden-endpoint remap has been removed; no edge splitting, Boolean cut, extra cap, vertex deletion or crossing-face deletion is installed. Invisible fragments are rejected by the ordinary GPU clip stage. The existing Artistic-only protection remains optional; Exact has no near-plane correction.

## Result and remaining defect

The requested simpler clipping contract is installed in live Uraraka, but the outer teeth remain visible. This is not a completed visual repair. The native clipper is cutting the geometry it receives; the deformation around crossing faces still needs diagnosis. Expected convex-hull outline slivers are not defects and were not changed. Do not use the previous zero-contour-crossings measurement to claim visual acceptance.

The freshly saved Uraraka view was loaded into an isolated process for diagnostics. The live update retained the current view, focal lengths, custom curves, vertex/face counts and captured shadow-source arrays. The original saved file was not modified. The isolated saved geometry and live evaluated geometry differ by up to 0.0459 local units after runtime refresh, so the diagnostic flat renders are not claimed as an exact live before/after comparison.

## Execution evidence

56 geometry/runtime/migration checks pass on 4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2 and 5.2.2. Each version includes 558 clipping sweeps and checks that changing the near distance does not modify Exact geometry. Migration accepts the prior schema 23 and preserves user settings.

A separate Metal raster fixture compares original crossing triangles with an independently clipped test polygon. Blender 4.2.23 and 5.2.2 produce zero differing pixels for four cases, including one/two vertices outside and wholly clipped geometry. This test oracle is not production clipping code. No-focus launch records show no activation or restoration.

Matched 32,001-point geometry medians in 5.2.2: schema 23 / 24 = 2.067 / 1.846 ms; repeat = 2.258 / 1.943 ms. This is a bounded geometry test, not full-scene viewport FPS. No new production timers, topology operations, Python vertex scans, readbacks or shader changes.

All four version-authored assets and the manifest are updated together. No release version bump. Windows backend and native qualification code are unchanged; physical Windows Vulkan/OpenGL replay remains unverified for this graph revision.
