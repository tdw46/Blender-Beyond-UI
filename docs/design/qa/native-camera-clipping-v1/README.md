# All geometry retained: native camera clipping test

User-requested direct verification, 2026-11-05. Read the current live Uraraka view at 239.4186 mm apparent lens and viewport Clip Start 0.01. Exported every evaluated vertex and triangle without pruning. The CamKeys graph and its nested groups contain no Delete Geometry node. The live session was only read; no file save or view change.

Created an isolated disposable Blender 5.2.2 scene from all 68,185 vertices / 135,206 triangles, with no modifiers, no CamKeys execution and no BVT renderer. Rendered with Blender's native Workbench engine and a native perspective camera. Camera transform and projection scales match the actual viewport (P00 = 1.3888888359, P11 = 2.3948898315). Flat diagnostic colors are used; this is not a material-fidelity comparison.

Only native Camera.clip_start changed: 0.001, 0.01, 0.05. Geometry, camera transform, lens and framing stayed fixed throughout. At the original clip distance, 227 evaluated triangles straddle the near plane; 12,209 vertices are behind the camera. The native renders visibly move the cut through the wrist. Relative to 0.01, 33,416 pixels changed at 0.001 and 61,448 at 0.05.

This establishes that the actual camera clip plane is reached with ALL geometry present. Teeth remain at the original clip distance. It does not establish a deformation repair. No production pruning, subdivision, renderer or GPU-backend code was changed. The 215–250 mm ramp remains restored. The owned no-focus process recorded no activation or restoration; Windows hardware was not tested in this diagnostic.
