# Actual Suzanne reference calibration — 2026-11-04

Status: research only. The 7.83254 mm projection is reproduced. The 2.5 mm
visibility-preserving continuations are **rejected visually**. Installed CamKeys,
live scenes, preferences and Windows fixes are unchanged.

## Read-only reference evidence

The separate, unsaved Suzanne session (Blender 5.2.2, PID 31689) was inspected
through the configured MCP launcher after initialization, tool discovery and a
non-mutating scene read. Its 507 source and evaluated vertex coordinates were
identical. AutoFOV exists, but contributes no current deformation. Dolly is active.

The captured lock has lens 24.658041 mm, depth 3.370826 units, object-origin focus.
Current viewport lens 7.832541 mm, distance 1.07073116 units. Its projection x scale
is 0.21757056, corresponding to a 72 mm horizontal gate, not the 36 mm gate used
in the earlier camera fixture. This is measured viewport behavior, not a universal
claim about every viewport/editor configuration. Always use its projection matrix.

The user screenshots are close-up **perspective**, not a panoramic fisheye camera.
Focal length alone does not identify the target: distance, framing anchor, sensor
or viewport projection and aspect are required. The captured dolly relationship
predicts distance 0.34175728 at 2.5 mm; 321/507 original vertices then lie behind
that *virtual* viewpoint. This predicts the screenshot's extreme/incomplete view;
we did not mutate the live session to recapture its earlier 2.5 mm state.

## Cheap exact solution while the target is valid

In source camera coordinates (positive z forward), let d be focus depth and
r = apparent lens / source lens. The desired dolly-reference projection is
`r * (x,y) / (z - (1-r)*d)` times the original projection scale.

Define:

```
q = (r*x, r*y, z - (1-r)*d)
k = r**(-2/3)
output = k*q
```

The actual camera does not move. A positive uniform scale about it cannot change
projection. The affine map's determinant is `r*r*k**3 = 1`: closed solid volume
and differential volume are preserved exactly. No face-volume reduction is needed
for this exact branch. It does change directional thickness, normals, curvature,
and raycast hits. Unit determinant is not an isometry or shader invariance.

The source focus plane keeps its projected scale. Exact positive-depth target
triangles keep their entire perspective projection, not only projected vertices.
At 7.83254 mm no safety extension or visibility guard is active. Our actual CPU
renders compare the physically moved short-lens reference with this fixed-camera
mapping using the same source-facet emission colors. They are nearly pixel-identical;
small antialiasing/float differences remain. This is not equality of real materials.

## Why the 2.5 mm problem remains

At the same framing anchor, the virtual view passes through the source surface.
Exact pinhole projection then crosses infinity and clips surfaces. A positive
radial movement cannot fix this while retaining every target ray and all original
in-frame vertices: target rays outside the frame stay outside under positive scaling.
A genuine fisheye projection is a different lens model, not an exact reproduction
of this viewport reference.

Two continuations were tested: a C1 positive-depth rational continuation followed
by a common radial (x/y shared) frustum shoulder, and a circular shoulder. Both
retain source-relative side-frustum eligibility and depth sign in the tested
fixtures. Both produce unacceptable 2.5 mm appearance. The circular shoulder avoids
rectangular corners but still distorts the silhouette. Neither is a shipped fix.

The prior guard compressed x/y independently and imposed a maximum lateral gain;
it was active far too early to match the new 7.8 mm target. Removing that interference
solves the valid target, but cannot turn the inside-mesh 2.5 mm target into a complete
exterior without changing the projected image. Do not silently relabel that change
as an exact 2.5 mm lens.

## Evidence / scope

- `render.json`: two calibrated focal lengths, 507-vertex Suzanne. Source mesh is
  open/nonmanifold; its oriented-volume ratio is diagnostic, not enclosed volume.
- `check.json`: 28 closed 10,242-vertex sphere cases, including source vertices
  genuinely behind the camera, identity, short/long lenses and both guards.
  Finite geometry, no newly escaped in-frame vertices, depth-sign retention and
  closed volume checks pass. No self-intersection or local-curvature guarantee.
- `image-difference.json`: actual 640×418 CPU diagnostic render differences.
- NumPy timing is a research cost only, not Geometry Nodes or full-viewport FPS.
- No new retained GN graph, weighted falloff, companion-object, near/far clipping,
  orthographic/shifted camera, live Uraraka motion or Windows qualification.
- Previous prototype runtime measurements do not qualify this new implementation.

Next: preserve the exact branch where valid; investigate an explicitly stylized
extreme-view continuation with an exterior silhouette/occlusion target. Do not
promote either rejected shoulder. Full source curvature/raycast preservation needs
a separate material reference strategy.

Projection background: [PBRT projective cameras](https://www.pbr-book.org/4ed/Cameras_and_Film/Projective_Camera_Models).
The deformation, determinant proof, guards and measurements here are our derivation.
Official Blender 5.2 API/Manual pages returned fetch errors in this research pass;
reference behavior was read from the actual 5.2.2 runtime.
