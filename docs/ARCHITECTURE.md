# Architecture

`Layout` is the custom authoring surface. `NativeLayout` is opt-in and exposes
Blender's complete native API without truncating its methods or arguments.
Native forwarding does not satisfy custom parity.

Modules:

| Module | Responsibility |
| --- | --- |
| `layout` | Custom UILayout-style authoring and explicit unsupported errors |
| `canvas` | Retained logical geometry, clipped input, edit/overlay ownership |
| `bindings` | Stable-owner validation and one-transaction commit/cancel |
| `editing` | Bounded arithmetic parsing, text selection, RGB/HSV/hex conversion |
| `components`, `virtual` | Grouping/search/navigation/occlusion and indexed visible rows |
| `widgets` | Custom color, ramp, curve and searchable data editors |
| `gpu.style` | Extracted rounded primitives, icons, springs and theme roles |
| `gpu.glass` | Shared retained background blur/refraction, optional host presenter |
| `gpu.previews`, `materials` | Bounded thumbnail cache and approximate material swatches |
| `hosts.panel` | One custom canvas per exclusively owned native panel block |
| `hosts.bridge` | Exact-build callback broker; no compiler/download at runtime |
| `native` | Explicit lossless compatibility route |
| `lifecycle` | Reverse-order idempotent cleanup |

No BVT/VRM imports or scene renderer are required. Product effects, image import,
material decoding, naming, commands, translations and scene ownership remain
in the consuming extension. No top-level `bpy` import is needed for pure tests.

## Cost model

Geometry is retained until width/structure changes. Small property reads occur
only for intersecting controls; completely parked canvases read none. A virtual
list uses prefix sums and binary search; iteration is O(log n + visible rows).
The underlying original `components.virtual_rows` remains for compatibility,
but scans heights from the start; use `VirtualList` for large data sets.

Shader and shape batches are retained. Texture/material previews are bounded
and revision-keyed. The host must provide meaningful backdrop revisions; a
redraw count is not a valid invalidation key. Controls share completed glass
resources. No per-control blur producers, scene-render jobs or idle timers.

## Ownership

One interactive Canvas per window/area/region. The host passes context and owns
modal lifetime, redraw, undo, cursor leases, load/undo invalidation and class
registration. `PanelHost.start()` explicitly installs region draw hooks;
`PanelHost.close()` revokes only its tokens and hooks. Native library mappings
remain alive while old UI blocks may retain native lambdas. A stable process
broker prevents vendored copies from replacing each other's callbacks.

GPU primitives require the caller's valid draw context, enabled scissor test,
clipped bounds, and a privately owned BLF font. They restore the public GPU state
they change. Blender has no complete public BLF state snapshot API; the panel
host loads its own font instead of mutating another extension's font settings.

## Limits

Custom controls are in development. Advanced modes and unimplemented APIs fail
explicitly. See `CUSTOM_PARITY.json`; native forwarding is never an automatic
replacement. Exact visual-reference acceptance is a separate mandatory gate.
