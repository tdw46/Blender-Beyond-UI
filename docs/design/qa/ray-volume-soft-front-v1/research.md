# Soft-front radial prototype — 2026-11-04

**Research, not installed.** Tyler now explicitly permits an approximate extreme
lens projection, smooth compression and small hacks to retain the exterior mesh
without crossing the camera plane. This supersedes the previous exact-projection
constraint for this experiment. The requested control remains 2.5 mm; it is not
silently relabeled as an exact optical 2.5 mm result.

## Recommended candidate

Keep ordinary source depths, derive the lateral enlargement/reduction from a
positive continuation of the lens denominator, then restore total volume with
one uniform scale about the fixed camera. Uniform radial scale preserves screen
positions. There is no clipping, cap, topology rebuild, lens-dependent root choice
or Python per-vertex loop in the Geometry Nodes implementation.

The real camera, lens, sensor, near plane and focus-plane screen scale remain
unchanged in all front comparison renders. The target's extreme perspective is
intentionally approximated. Whole silhouettes may expand outside the frame; this
is permitted by the user's correction. Suzanne fits entirely in the shown 2.5 mm
frame, and all vertices remain in front. The second fixture is an explicitly
synthetic, connected closed character silhouette, not the actual Uraraka asset.

Three approaches are retained for comparison:

1. `lateral`: change only sideways coordinates when the source is safely in front;
   preserve original depth. Suzanne's 2.5 mm volume becomes 1.664 times baseline.
2. `volume`: compress the target depth with a smooth positive function and restore
   volume. It avoids a flat clamp, but produces an undesirable long/thin side view.
3. `radial` (preferred): use the lateral result, then a global camera-centered
   volume scale. Suzanne's scale is 0.843879, volume ratio is 1.0, and its depth
   interval is 2.9803–3.7708 versus the original 3.5316–4.4684. The exterior remains
   visible, without the strong shape thinning of the compressed candidate.

## Formula and explicit compromises

Use positive camera-forward coordinates. Let `z` be source depth, `d>0` focus
depth, `r>0` requested/real lens ratio, and `w=z-d*(1-r)` the old target depth.
Set `a=0.5*max(d-min(source_z), d*1e-6)`, using the complete pre-effect domain,
including offscreen vertices. Define the positive shoulder:

```
g(w,a) = w                    if w >= a
         a*a / (2*a-w)         otherwise
safe_w = r*d*g(w,a)/g(r*d,a)
real_depth = g(z, 0.01*d)
Q = (r*real_depth/safe_w * lateral, real_depth)
P_out = C + cbrt(V_source/V_Q) * Q
```

`g` is positive, strictly increasing and C1; it has a second-derivative change at
the join. Its derivative in the soft region is `a²/(2a-w)² > 0`, so it does not
collapse a region onto one plane. Safe ordinary target depths are unchanged when
the focus normalization is also outside the shoulder. Once the focus enters the
shoulder, normalization adjusts the whole projection to keep focus-plane scale.
This changes perceived lens behavior, not just hidden geometry.

At the focus, lateral/depth equals original lateral/d, so the focus-plane screen
framing remains fixed. No guarantee is made for an invariant silhouette box.
Camera-centered uniform scale leaves every vertex's screen coordinates unchanged;
for the unchanged triangular mesh it also leaves projected edges/faces unchanged
when near/far clipping is inactive. It changes depths relative to other objects.

The second `real_depth` shoulder handles source vertices already behind the actual
camera in close views. Otherwise `real_depth=z` exactly. It guarantees positive
camera-plane depth for finite admitted values, **not a universal near-clip
clearance** after volume scaling. Close-camera tests reached depths around
`1.7e-5`; those may still be behind a scene's near clip plane. A clip-aware depth
distribution and its volume/framing tradeoff remain an integration gate.

For sideways-only scaling `x'=s(z)x, y'=s(z)y, z'=z`, the Jacobian determinant is
`s(z)^2`. It is not locally volume preserving except where `s=1`. Whole-volume
normalization can restore the global integral, but does not preserve local
thickness, principal curvature, normals, material sampling or raycast results.
The original assumption that volume/depth preservation alone leaves those shaders
unaffected is therefore not valid. The prototype retains 3D geometry; it does not
promise unchanged shaders. Nonlinear triangles also need material/interpolation
qualification; prior rational projective UV correction is not automatically a
complete solution for this non-projective mapping.

## Open selections versus closed meshes

`closed_signed` normalizes oriented enclosed volume for closed consistently
oriented meshes. `open_absolute_fan` normalizes the sum of absolute tetrahedral fan
volumes around the mapped focus. The latter is an explicit stable proxy for an
open selection, **not physical enclosed volume**. The caller chooses the contract
for the source topology; it must not switch each frame based on a sign threshold.

The first open-patch attempt used signed normalization and rejected 632/1800
samples (including failures in the separate compressed candidate). Its numerical
report is preserved as `signed-rejected.json`. It is not a usable fallback.
The explicit absolute-fan version passes all 1800 sampled views and avoids that
cancellation. General selected-region closure and weighted falloff remain open.
None of these tests proves absence of self-intersections in arbitrary nonconvex
triangulated inputs or preserves material/UV behavior by itself.

## Execution evidence

- Double precision: 1800 recorded pre-effect Uraraka Head samples, including a
  0.2-distance close-view sweep; 220 contain source vertices behind the camera.
  Every output is finite and positive-depth. Maximum absolute-fan relative error
  is `2.0e-15`; maximum movement for the tested tiny orientation perturbation is
  `1.79e-5` Blender units. This does not test the live full modifier stack.
- Actual Blender 5.2.2 GN: 900 recorded ordinary-distance cases pass against the
  double-precision model. Maximum positional error `3.62e-6`; maximum relative
  absolute-fan error `1.09e-6`.
- Actual closed-mesh GN: 27 lens/orientation cases plus eight cases with the real
  camera inside the source sphere pass on 5.2.2 and 4.2.23.
- Apple M5 Pro, 5.2.2, 40,962 vertices / 81,920 triangles, 92 nodes:
  median 2.41–2.65 ms across the final serial runs, 60 measured updates after 20
  warmups per lens. This is a standalone kernel cost, not full viewport FPS or
  feature-equivalent production performance. Earlier parallel diagnostic timing
  was excluded; authoritative timings are `dense-gn.json`.
- All rendering was headless Cycles CPU with fixed source-face emission colors.
  It establishes exterior geometry and framing evidence, not shading fidelity.
  No live Blender file, preferences, installed addon or release version changed.

Exact 4.2/5.2 official API and Manual retrieval was attempted and unavailable.
Version evidence is installed-runtime execution. The 5.2 modifier input adapter
uses an explicit version/capability gate; older runtimes keep the ID-property path.
Other release families and Windows GPU/backend behavior are not newly qualified.

## Next implementation gates

1. Add near-clip-aware depth protection without silently changing the user's
   framing or claiming both volume and framing where they are not preserved.
2. Retain the source-derived domain and one shared normalization across companions;
   qualify selected-region closure, weighted falloff and native material/UV paths.
3. Keep the existing changed-view scheduling. Cache topology; invalidate pre-effect
   geometry inputs on real geometry changes. Do not derive bounds from screen
   visibility and do not create a new idle timer.
4. Compare the actual Uraraka full stack during orbit, close zoom, billboard motion
   and external-object occlusion. Then qualify Windows and all supported families.

Use `tools/run_blender_tests.py` from Beyond UI for `gn_probe.py`,
`recorded_gn_probe.py` and `render_probe.py`, with disposable background profiles.
Set `RAY_DENSITY=7` for dense timing. The recorded probe/sweep require the ignored
`RAY_STABILITY_SNAPSHOT` private mesh path; do not publish that source geometry.
The supplied `.blend` contains only the synthetic Suzanne prototype.

Research basis: [PBRT projective camera model](https://www.pbr-book.org/4ed/Cameras_and_Film/Projective_Camera_Models)
explains the depth denominator and clipping domain. The positive continuation,
Jacobian calculation and radial normalization above are this project's derivation,
not an algorithm attributed to the referenced social post or to PBRT.
