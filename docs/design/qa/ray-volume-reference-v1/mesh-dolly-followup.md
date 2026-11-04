# Whole-mesh dolly safeguard — 2026-11-04

User proposal: when the lens correction threatens additional camera-plane crossings,
move the mesh in a compensated dolly operation instead of flattening individual vertices.
This is a mathematical/numerical follow-up, not an installed implementation or new
visual acceptance. Existing source-relative frame eligibility still applies.

## Two different compensations

Using positive camera depth, focus depth `d`, lens ratio `r`, exact target coordinates
before volume normalization are `q = (r*x, r*y, z-d+r*d)`.

1. **Translate away and compensate with uniform object scale**, retaining the
   projected scale of the focus plane: the resulting transform is simply a
   positive uniform scale about the camera. It preserves the sign of every depth,
   so vertices behind the camera remain behind. This does not fix crossings.
2. **Translate away by delta and compensate only the lateral size**: multiply x/y
   by `(r*d+delta)/(r*d)` and add delta to depth. The result is exactly
   `(s*x, s*y, z-d+s*d)` with `s=r+delta/d`. This avoids local clipping/flattening,
   but has the projection of a longer effective lens `s*f_real`.

Normalize the second affine map by `s**(-2/3)` about the camera to preserve closed
solid volume (determinant one) without changing its projection. No face-volume solve
is needed. Directional lengths, curvature and ray hits still change; this is not
shape or shader invariance.

## Recorded Suzanne calculation

Baseline: `f=24.65804100036621`, `d=3.370826005935669`. Original source geometry
was confirmed unchanged by its modifier. All 507 source vertices are in front and
inside the measured viewport-equivalent frame.

For a positive-depth vertex with original depth z, a pre-normalization safety margin
`e=0.01` requires `s >= (d-z+e)/d`. The maximum across the mesh is 0.255593881,
corresponding to **6.302444 mm**. This margin is a diagnostic camera-plane clearance;
it is not a general near/far-plane qualification across arbitrary radial scales.

For each source-in-frame vertex in front of the focus plane (`z<d`), let
`a = abs(x)*projection_x` or `abs(y)*projection_y`. Side-frustum containment requires
`s >= (d-z)/(d-a)`. The denominator is positive for these eligible points.
The maximum for this fixture is 0.312664213, corresponding to **7.709687 mm**.
At this threshold the extreme projected component is 1.0000000000000002 (roundoff).
A production implementation should reserve a numerical margin rather than sit on
that exact boundary. A smooth conservative shoulder would raise the effective
lens slightly more.

Thus a 2.5 mm request with this whole-mesh policy settles near 7.71 mm or longer.
It can eliminate clipping and box-shaped per-vertex guards, but cannot retain the
2.5 mm projection under the fixed-framing/no-new-escape contract.

## Real-time and continuity implications

The per-vertex transform is affine and cheap; one maximum reduction over the
pre-effect eligible domain gives the safety threshold. Share the same transform
across linked meshes rather than solving separate accessory offsets. Use pre-effect
positions, not already corrected evaluated bounds. Do not switch based on only the
number of behind vertices: that can swap which vertices cross. Track each original
vertex's eligibility. Originally outside/behind vertices should not unnecessarily
constrain the protected domain.

A raw maximum is continuous in the source coordinates but not differentiable when
the extremal vertex changes. Use a conservative continuous activation shoulder,
not delayed smoothing that can temporarily violate the safety bound. Originally
behind vertices and a mesh crossing the real source plane need additional policy;
this whole-object fixture does not qualify those mixed-domain transitions.

No runtime/GN cost has been measured for this safeguard. The prior NumPy and GN
measurements belong to different kernels. An additional nonlinear artistic warp
could continue exaggeration after the safe limit, but would be an explicit
approximation requiring a new visual target, not an exact short-lens simulation.

Underlying perspective relation: [PBRT projective camera models](https://www.pbr-book.org/4ed/Cameras_and_Film/Projective_Camera_Models).
Bounds and compensation equivalences above are our derivation and fixture calculation.
