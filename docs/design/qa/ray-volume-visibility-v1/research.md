# Source-relative visibility prototype — 2026-11-04

**Research only; not installed.** Supersedes the earlier all-positive and
horizontal-overscan experiments. Tyler's latest contract is:

- Vertices inside the original, uncorrected camera/viewport frame must not newly
  escape it. Originally offscreen vertices may remain offscreen.
- Originally front-of-camera vertices must not cross behind. Originally behind
  vertices may remain behind, with a smooth transition near the camera plane.
- Extreme lens appearance may be approximated to retain the exterior mesh.
- Keep the real camera fixed, preserve volume where well-defined, and remain fast.

The renders use the same camera, real focal length, sensor and source geometry at
every setting. They do not preserve an identical silhouette bounding box; they
preserve the original frame-membership eligibility and focus-plane scale. There
is no automatic camera movement, reframe, clipping/cap, or topology rebuilding.

## Algorithm

Let `C` be camera position, `f` unit forward, `up/right` camera axes, `F` the focus,
`d=dot(F-C,f)>0`, `z=dot(P-C,f)`, and `r` requested/real lens ratio. All camera basis
and frustum inputs must come from the actual view. Default symmetric half-angle
tangents `.36/.36` match the square 50 mm / 36 mm render fixture, not every camera.

The nominal lateral factor is the perspective-derived reciprocal
`1/[1+(1/r-1)*(z-d)/z]`. It is exact until 2x enlargement, then uses a positive,
monotonic C1 shoulder approaching configurable `max_lateral_gain=4`. This is an
explicit artistic approximation at the extreme, not exact optical 2.5 mm output.

Near the actual camera plane, evaluate that factor with a finite denominator and
multiply its deviation from 1 by `smoothstep(z/(0.05*d))`, clamped to 0..1. Behind
the plane the deformation is zero; at the plane both the deviation and its first
derivative vanish. No original depth is flattened, replaced, or forced positive.

For each lateral camera coordinate `x`, compute desired displacement `w`, the
original depth's frustum edge `e=max(z,0)*tan_half_angle`, and

```
m = max(e - sign(w)*x, 0)
delta = w*m / (m + abs(w))       # zero when the denominator is zero
x_new = x + delta
```

This smoothly reduces outward movement as available room vanishes. When an input
is inside its frame interval, `abs(delta)<m` for finite nonzero inputs, so it cannot
newly cross that edge. An already-outside vertex can stay outside or move inward;
it is not pulled back merely to satisfy a guard. Apply to both camera axes. The
position is continuous across frame boundaries; do not claim globally C1 velocity
across all boundary cases. There is no screen-visibility-derived mesh bound.

The resulting relative point `Q` retains **exactly the original z**. Restore the
chosen total volume measure with `k=cbrt(V_source/V_Q)>0`, then `P_out=C+k*Q`.
Positive uniform radial scale preserves screen projection and depth sign. Thus a
front input remains front and a behind input remains behind. Originally behind
geometry receives no lateral deformation, and its projection is unchanged by k.

`closed_signed` uses oriented enclosed volume of a closed, consistently oriented
mesh. `open_absolute_fan` uses summed absolute tetrahedral fans around the mapped
focus for open selections; this is explicitly **not physical enclosed volume**.
The metric is selected by the owner, never switched per frame from a sign test.
Zero/reversed volume is rejected rather than hidden by an identity fallback.

## What the prototype qualifies

- 2,700,000 deterministic point evaluations: no newly escaped in-frame vertices,
  no newly behind-camera front vertices, and all originally behind vertices remain
  behind. Small frame-edge/camera-plane crossing perturbations remain continuous.
- 1800 numerical recorded pre-effect Uraraka Head views, including 220 source-
  behind cases, pass the visibility and open absolute-fan checks.
- 900 actual Blender 5.2.2 Geometry Nodes recorded-mesh cases pass. Float32
  visibility checks use a documented `2e-5` camera-coordinate tolerance; the
  double-precision guard checks use `1e-10`. These are not infinite-precision GPU
  raster or live scene guarantees.
- Closed-mesh GN tests: 27 ordinary lens/orientation cases and eight cases where
  the camera starts inside the source sphere, on 5.2.2 and 4.2.23.
- 110-node standalone dense kernel: about 2.6–2.8 ms median for 40,962 vertices /
  81,920 triangles on Apple M5 Pro. No production falloff, companions or viewport
  draw work is included. Timing uses 20 warmups then 60 updates per ratio.
- In the actual 2.5 mm-setting renders, all 507 Suzanne vertices and all 2258
  closed character-proxy vertices stay in frame. The closed proxy's volume ratio
  is 1.0. Suzanne has a known nonmanifold source edge, so its total metric is only
  diagnostic; the closed sphere and proxy qualify physical closed volume.

Source-face emission colors make silhouettes easy to compare but do not prove
lighting or material equivalence. The character proxy is synthetic, not Uraraka.
No live scene/preferences/addon installation/version changed. The `.blend` contains
only the owned synthetic Suzanne prototype. Script hashes and raw reports are kept
beside this file; no private source vertex data is published.

## Local thickness, curvature and raycasts: measured limitation

Total volume does **not** imply local shape preservation. The independent Blender
BVH test at the 2.5 mm setting preserves closed-sphere volume exactly while showing:

- sampled fixed-ray occupied thickness changes up to 46.6%;
- ray entry positions move by up to 0.933 Blender units;
- median surface-normal change is 14.6 degrees;
- median edge-dihedral change is 1.29 degrees, maximum 29.5 degrees;
- individual surface edge-length ratios range from about 0.24 to 3.43.

The fixed-ray thickness measurement is an occupied interval along a world-space
ray, not matched material-point thickness along the original surface normal.
Dihedral changes are a discrete surface-bend diagnostic, not a full shader's
curvature output. Nevertheless these actual changes rule out claiming unchanged
curvature/raycast behavior from volume conservation alone.

Sideways-only motion also fails that assumption: for `x'=s(z)x, y'=s(z)y, z'=z`,
the Jacobian determinant is `s(z)^2`. A volume-restoring global scale corrects the
total integral but not each local differential. A locally volume-preserving flow
would constrain the determinant, still not curvature or arbitrary ray queries.

If a specific shader must retain original curvature/raycast values, the next
direction is a separate **pre-effect reference geometry** path: retain original
positions/normals/attributes and route those specific queries to an undeformed
surface in the correct coordinate space. Rebuild references only on true geometry
changes, not every view update. This requires shader-specific integration and
proper query-space conversion; it cannot preserve every external occluder, world-
space hit or lighting result automatically. No such adapter is implemented here.

## Remaining gates

1. Actual near/far clip planes, shifted/asymmetric camera frusta, orthographic views
   and render borders. The current proof covers symmetric perspective side planes
   and depth **sign**, not unchanged near/far-clip eligibility after radial scaling.
2. Weighted falloff, selected-region closure, shared companion normalization and
   source ownership. Freeze source data before correction; never feed corrected
   bounds or visibility subsets into the next update.
3. Native materials, textures, normals and relevant BVT queries. This nonlinear
   vertex warp is not the previous projective transform; its rational UV patch is
   not automatically applicable. Check coarse triangulation and self-intersections.
4. Live Uraraka orbit/zoom/billboard/scene occlusion, then feature-equivalent frame
   timings and Windows/other-release-family hardware validation.

Exact-version official 4.2/5.2 API/Manual retrieval was attempted but unavailable;
compatibility evidence is installed-runtime execution. The GN modifier setter
uses a version/capability gate for 5.2 and retains the older ID-property route.
Tests use disposable background profiles via Beyond UI's `run_blender_tests.py`;
there is no custom GPU backend or live installation claim.

Reproduction: `gn_probe.py` (`RAY_DENSITY=7` for dense workload),
`recorded_gn_probe.py`, `distortion_probe.py`, and `render_probe.py` are Blender
runner fixtures. `guard_probe.py` and `sweep.py` use Python/NumPy with output paths
from their environment variables. Recorded probes require ignored private
`RAY_STABILITY_SNAPSHOT`; do not publish the source mesh.

Research basis: [PBRT projective cameras](https://www.pbr-book.org/4ed/Cameras_and_Film/Projective_Camera_Models)
for the projection/clipping domain. The continuation, visibility constraints,
normalization and tests here are this project's derivation, not an algorithm
attributed to PBRT or the referenced social-media post.
