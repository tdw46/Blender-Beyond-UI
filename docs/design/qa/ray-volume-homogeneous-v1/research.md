# Projective radial research checkpoint — 2026-11-04

Executable research, **not installed or production complete**. The installed
consumer remains schema 15 / `60d2015`, with known popping. No live scene was
saved. The restored production files in this source checkout are also schema 15;
do not reinstall the rejected schema 16 from the branch HEAD.

## Result and next direction

Use a bounded homogeneous/projective radial map as the next integration candidate.
It matches the existing fixed-framing lens target without moving the real camera,
clamping the requested lens or dividing geometry by target camera depth. Keep the
original topology on this fast path. Investigate specialized plane clipping and
capping separately when **every retained vertex must be in front**.

This does not solve every extreme-lens requirement simultaneously. At 2.5 mm the
existing fixed-framing target camera can be inside the character. The exact target
then shows an interior, as the saved comparison demonstrates. Moving geometry
along its rays cannot turn that target into an exterior full-character image
without changing the target. The current definition holds the focus-plane framing
convention fixed; it does not hold every silhouette bound constant across lenses.

## Evidence

- 900 double-precision samples on recorded pre-effect Uraraka Head geometry pass;
  maximum relative signed-fan-volume error `6.51e-11`.
- 900 actual Blender 5.2.2 Geometry Nodes samples pass. Maximum position difference
  from the reference is `1.98e-6` Blender units; maximum relative open-fan-volume
  error is `0.0002502`. This is **not enclosed physical volume** for an open patch.
- 36 near-zero signed-volume cases pass with a continuous affine limit.
- 442 convex cut-transition samples remain finite, positive-depth and volume
  conserving. `continuity.json` reports a surviving vertex's displacement and
  normalization change; this is not a rendered/Hausdorff continuity proof.
- The standalone triangular, full-influence GN fixture executes on stock
  4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2 and 5.2.2 on this Mac.
- The 40,962-vertex / 81,920-triangle kernel measures 1.91–2.03 ms median on an
  Apple M5 Pro. The existing full graph measures 3.96–4.45 ms on the same mesh,
  but includes features absent here: **not an equivalent-feature speedup claim**.
- Specialized convex clipping is 3.87 ms compute / 13.29 ms including Blender
  mesh publication, versus 71.78 ms for the BMesh prototype. Extraction, attributes,
  preparation, downstream modifiers and viewport drawing are excluded.
- Actual face-color renders at 12.5/25/100 mm agree with their reference images
  to sub-0.001 mean RGB levels on a 0–255 scale. These are diagnostic emission
  renders, not shaded-material or live Uraraka acceptance.
- Ordinary UV interpolation fails the projective texture fixture (mean RGB error
  17.94); rational correction reduces that to 0.00068. No consumer materials were
  modified.

## Mapping and volume contract

Let `C` be the fixed camera, `F` the focus, `f` unit forward, `r` requested/real
focal length, `d=dot(F-C,f)>0`, `z=dot(P-C,f)`, and `R=max(length(P-F))`.
The target depth is `w=z-d*(1-r)`.

```
D(P) = 1 + beta * dot(P-F,f)/R
P' = C + scale * [r*(P-C) + (1-r)*(z-d)*f] / D(P)
```

The lateral/depth ratio is exactly `r*lateral/w`. Geometry never divides by `w`.
The positive bounded `D` avoids a projective horizon over the admitted domain.
The real camera is unchanged. `beta` changes only depth distribution along the
target rays, not the requested projection.

For oriented triangle fan volumes `vi=det(P0-F,P1-F,P2-F)/6`, define `S=sum(vi)`,
`A=sum(abs(vi))`, `M=A+R^3`, `L=(1-r)/(1+r)/6`, `t=(S/M)^2*L`,
`g=1+4*abs(t)*d*r/R`, `beta=t/g`, and `beta_over_S=S/M^2*L/g`.
This last expression is valid at `S=0` and does not divide by signed volume.

For triangle depth coordinates `ui=dot(Pi-F,f)/R`:

```
E = u0+u1+u2 + beta*(u0*u1+u1*u2+u2*u0+beta*u0*u1*u2)
product_D = 1 + beta*E
K = r*r*(1-beta*d*r/R)
N = 1 - beta_over_S * sum(vi*E/product_D)
scale = cbrt(1/(K*N))
```

The transformed fan anchor is the **mapped F**, not the old fixed-depth closure.
Each tetrahedron scales by `scale^3*K/product_D`; summing yields original `S`.
For a closed consistently oriented surface this is total enclosed volume. For
an open selected patch it is only the declared signed fan metric. At vanishing
signed/absolute fan volume, beta tends continuously to zero and the map becomes
the determinant-one affine lift, which also existed in earlier research.

The local Jacobian determinant is `scale^3*K/D(P)^4`. Thus this nonlinear map
preserves **total volume, not local volume, local thickness, curvature, raycast
behavior, or lighting**. Claims about unaffected curvature/raycast shaders would
require separate evidence and are not established by the referenced social post.

The sign of output depth remains the sign of `w`. Of the 900 recorded samples,
177 retain behind-camera vertices. Finite geometry alone does not make those
vertices positive-depth. Companion meshes must fit the same admitted horizon;
the current prototype rejects out-of-domain points rather than silently clamping.

## Topology, attributes and continuity

The bounded projective map is invertible within its horizon, preserves planar
faces and triangle connectivity, and introduces no self-intersections there for
an initially embedded surface. Whole-domain motion remains continuous while the
source domain and coefficients vary continuously. Recomputing a discrete active
selection or changing source bounds abruptly can still break that assumption.
Do not derive bounds from already-deformed geometry or the visible screen subset.

The positive-depth prototype clips hidden triangles, caps a single convex loop,
then restores volume by uniform scaling around the real camera. That last scale
preserves rays, but changes scene depths and therefore can change occlusion with
unaffected objects. The cap is below the unchanged near plane in the tested
fixture. This is not a general guarantee at arbitrary scales or clip distances.
The Suzanne render fixture retains an original nonmanifold edge at ordinary
lenses; closed-volume qualification uses the closed sphere fixtures instead.

Next implementation requirements:

1. Retain source vertex/edge/face identities and pre-effect connectivity. Classify
   against one plane, reuse cut-edge IDs, and change local faces only at crossings.
   Reuse connectivity between events. Avoid per-frame mesh datablock replacement.
2. Add robust orientation predicates and explicit coplanar conventions. A changing
   epsilon or classification hysteresis must not quietly alter exact visible
   geometry. Validate coincident vertices, grazing cuts and tiny components.
3. Generalize cap loops to nonconvex boundaries, holes and disconnected components.
   Open/nonmanifold character patches need an explicit closure policy; do not
   count signed cancellation as physical volume. Preserve winding and test volume
   continuously through split/merge events.
4. Preserve per-corner material, UV, normals, color and ownership attributes. For
   projective UVs, interpolate `UV_i/D_i` and `1/D_i`, then divide in the shader.
   Clipped vertices must interpolate these rational attributes, not raw UVs.
   Tangents, normal maps, generated coordinates and BVT materials remain open.
5. Qualify weighted falloff independently. Blending position maps can break the
   projective face contract and exact total-volume proof. Do not apply this proof
   to the production falloff by assumption. Test shared companions and billboards
   together, preserving one source snapshot and existing update scheduling.

## Real-time architecture recommendation

Prefer the retained GN path for unchanged topology. It has the best measured
component budget and avoids Python vertex loops. Cache connectivity and resource
ownership; only recompute view-dependent fields/reductions when the existing
scheduler invalidates them. Do not use a viewport-visible-vertex bound: offscreen
vertices must not change the math or trigger topology reconstruction.

For strict positive-depth geometry, benchmark a specialized native/retained plane
clip implementation before adopting it. Our 13.29 ms publication-inclusive Python
prototype already consumes most of a 16.67 ms frame, before other scene work.
General Boolean rebuilding is unsuitable for this hot path. GPU clipping alone
does not give downstream Blender modifiers a capped volume-preserving mesh.

A divergence-free volumetric ray flow is a separate research option if **local**
volume preservation becomes mandatory. It would require solving/integrating a
field, handling boundaries and reconciling nonlinear curved surfaces with a
finite triangle mesh. There is no measured real-time or exact-material result
for that route; it is not the recommended immediate implementation.

Next acceptance sequence: textured retained-mesh adapter → general cut-event
fixtures → weighted/companion full-stack parity → live Uraraka camera/orbit/zoom
comparisons → equivalent-workload timings on Mac and Windows. Keep the installed
schema 15 until a candidate can be installed without claiming these gaps closed.

## Reproduction and provenance

Use Beyond UI's `tools/run_blender_tests.py` with `--blender`, `--fixture` and
`--output`; all measurements here used disposable background profiles. Set
`RAY_PROJECTIVE_GN=1 RAY_DENSITY=7` for `probe.py` dense timings. Run
`recorded_gn_probe.py`, `continuity_probe.py`, `fast_clip_probe.py`,
`topology_probe.py`, `texture_probe.py` and `render_probe.py` independently.
`sweep.py` and `degenerate_probe.py` use the bundled Python with NumPy; inspect
their output/path options before reproduction. The recorded private Head mesh
is intentionally not distributed; reports contain measurements, not its vertices.
`source-sha256.json` records this checkpoint's research script hashes.

Exact-version Blender API/Manual requests for 4.2–5.2 were unavailable through the
documentation service during this pass. The version evidence is executed stock
runtimes, not verified documentation, Metal/Vulkan/OpenGL draw qualification or
Windows testing. No custom shader/backend implementation was installed.

Primary research references consulted:

- [PBRT: projective camera models](https://www.pbr-book.org/4ed/Cameras_and_Film/Projective_Camera_Models): perspective and clipping domain.
- [PBRT: applying transformations](https://www.pbr-book.org/4ed/Geometry_and_Transformations/Applying_Transformations): homogeneous point representation.
- [Stanford: perspective-correct interpolation](https://www.graphics.stanford.edu/courses/cs248-96-winter/Assignments/help2.html): rational texture coordinates.
- [CGAL: specialized plane clipping](https://www.cgal.org/2025/06/06/new_clip/): plane-specific processing avoids the cost of general Boolean operations; its published timings are not our timings.
- [CGAL clipping contract](https://doc.cgal.org/latest/PMP_Boolean_operations/group__PMP__clip__grp.html): surface/volume and closure distinctions.
- [Shewchuk: adaptive robust predicates](https://www.cs.cmu.edu/~quake/robust.html): uncertain orientation signs near degeneracy need robust predicates, not a guessed tolerance.

These sources motivate the architecture. The particular radial normalization
above is this repository's tested derivation, not an algorithm attributed to them.
