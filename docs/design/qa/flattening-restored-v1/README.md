# Restored 215–250 mm flattening

The high-lens ramp was incorrectly restricted to Artistic in `projection_policy.py`. It now applies in Exact and Artistic: zero through 215 mm, smoothstep to 1 at 250 mm. The existing local compression math is unchanged. Ordinary camera/viewport clipping remains after deformation; no hidden-endpoint remapping or reconstructed pre-deformation cut was added.

Live Uraraka at 250 mm / Exact now reads Near Plane Protection = 1 in all seven affected modifiers. The hand previously clipped away is visible again. The view, lens and saved file were not changed. Source and installed policy match. There is no release version bump or new graph schema.

14 runtime/geometry checks pass across Blender 4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2 and 5.2.2. Tests exercise both modes, camera and viewport callbacks, threshold values, positive ordered depths, and unchanged geometry outside the compression band.

## Remaining outer teeth

A disposable process loaded the freshly saved 142.07 mm Uraraka view and retained ordinary camera clipping. Linear mesh subdivision before deformation greatly reduced the outer teeth: 68,185 vertices at level 0, 285,886 at level 1, 1,141,346 at level 2. The camera clip stage did not change. This demonstrates insufficient deformation sampling across crossing faces; expected outline slivers remain excluded.

Whole-mesh refinement is NOT installed. Capturing evaluated geometry took about 29 / 308 / 910 ms in this cold diagnostic, including topology generation and extraction; these are not warm frame-rate measurements. It would be inappropriate to claim a realtime fix from this prototype. The remaining choice is bounded refinement or an authorized change to near-camera deformation below 215 mm. No front-side deformation patch has been added while that choice is pending.

Shared renderer/GPU code and Windows qualification are untouched. Physical Windows replay is still unverified for these local changes. The live scene remains unsaved.

## User-requested behind-plane-only discard experiment

Kept all triangles touching or in front of the final camera plane, plus a 0.02-unit rear margin and three conservative shared-vertex face rings. Removed only 23,624 triangles strictly farther behind it from the visible draw indices. The source geometry and shadow-source data were not changed. Blender 5.2.2 Metal rendered pixel-identical results (zero differing channels) with and without this pruning; the outer teeth remain. Thus off-camera-only discard cannot repair the visible defect. Native clipping already rejects these portions.

The isolated NumPy classification took roughly 8.6 ms across 68,185 vertices in this diagnostic; this is not a production performance estimate or a renderer speedup. No Python scan, new native/shader path, face deletion or topology change was installed. The 215–250 mm shared ramp remains restored. The remaining task is the visible deformation defect; behind-plane-only cleanup has now been ruled out as its repair.
