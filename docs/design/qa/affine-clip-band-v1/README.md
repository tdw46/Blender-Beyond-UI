# Affine clipping band — schema 25

Tyler authorized either bounded deformation conditioning or subdivision, choosing the cheaper approach. This revision uses constant-size geometry-node arithmetic and retains the existing mesh. It does not delete, subdivide, cap or manually clip triangles. The actual renderer clips the resulting geometry.

The long-lens radial warp varies its homogeneous scale across coarse triangles. Inside a small near-plane band, a common affine depth mapping regularizes that interpolation. A smoothstep joins the established warp outside the band. For full influence below 215 mm, positive visible vertex projections remain the same within floating-point accuracy; local thickness changes. This is the explicitly authorized exception to the former no-flattening preference. General volume preservation inside this correction band is not claimed.

The existing 215–250 mm protection remains shared by Exact and Artistic. The band solves the guarded depth map's near-plane preimage, so partial protection does not relocate the clipping threshold. Full 250 mm protection bypasses the added correction and is numerically identical to the previous geometry in the saved Uraraka fixture. Partial protection has a small bounded projection approximation in the band (synthetic maximum 0.00013913, about 0.14 pixel at a 1000-pixel focal scale). Outside the band the prior warp is retained.

The band is disabled below a 1e-5 clip distance, where float32 world/local precision can swamp compressed depth. That fallback retains the established deformation and normal camera clipping, rather than claiming this correction is qualified at arbitrarily small distances.

## Validation

- 56 geometry/runtime/migration checks passed across Blender 4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2, 5.2.2. Includes 558 contour sweeps per version, 168 transformed depth cases, short/neutral invariance, custom-curve migration and high-lens transitions.
- Saved Uraraka view: 68,185 vertices / 135,206 triangles retained; captured shadow positions unchanged. Diagnostic flat Metal renders remove the large outer teeth without subdivision. Existing outline slivers remain intentional.
- Actual live Uraraka at 93.3956 mm: matched before/after screenshots show a clean outer boundary. Reload preserved view, lens, curves, vertex/face counts, shadow sources, and saved file mtime. No scene save.
- 239.42 mm diagnostic comparison and 210/215/230/239.42/245/250 geometry checks. Full 250 mm output is identical to the baseline.
- Windowed test focus audits report no activation/restoration. Existing user session was not raised.

## Cost and limits

Matched retained 32,001-point update medians: baseline 1.672 / 1.697 ms; new 1.954 / 1.745 ms. Increment roughly 0.05–0.28 ms in this fixture, not a whole-scene frame-time claim. An earlier whole-mesh subdivision diagnostic multiplied geometry from 68,185 to 285,886 or 1,141,346 vertices; it remains uninstalled. No new Python vertex scans, timers, shader APIs, GPU readbacks or reductions are added to production.

No universal collision-free guarantee, broad motion acceptance or physical Windows replay. The graph uses existing portable math/vector/switch nodes; renderer and Windows native paths are unchanged. No release version bump.
