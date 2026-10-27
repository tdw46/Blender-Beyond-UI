# Next parity batch — awaiting Tyler QA

The board places immutable generated reference v2 on the left and unmodified
Blender GPU framebuffer captures on the right. Every card has a comparison,
overlay and difference image. Contrast and alpha captures test actual
translucency. This fixture exercises the tint fallback, not a live blurred
viewport backdrop. Reference lighting, highlights, typography and details are
still visibly different; numerical exact-match checks remain false.

## New controls

- Palette: virtualized swatches, selection, focused arrow navigation, scrolling,
  add/remove and a custom color-editor callback. A 10,000-color palette paints
  only 18 visible swatches plus the selected preview. Selection/undo snapshots
  do not scan every color; topology edits preserve the affected palette state.
- Matrix: read-only 4×4 RNA matrix decomposition into translation, XYZ Euler
  rotation in degrees and scale. Decomposition is cached by matrix values.
- Progress: read-only BAR and RING with finite/clamped factors. The ring uses a
  retained analytic GPU batch; progress changes update uniforms, not geometry.

The original generated matrix grid conflicted with the documented Blender
matrix template. Reference v2 explicitly replaces it with the correct read-only
decomposition; v1 is retained with provenance. `template_matrix` is documented
from Blender 5.0. The custom implementation also works through mathutils on
older supported versions, independently of native template availability.

Palette's legacy `color` parameter remains available explicitly. When omitted,
the adapter follows the native version's default: false through 5.1, true in 5.2
where the native parameter was removed. API pages for 4.2–5.2 and installed 5.1.2/
5.2.2 runtimes were checked. Official references:
[4.2 UILayout](https://docs.blender.org/api/4.2/bpy.types.UILayout.html),
[5.1 UILayout](https://docs.blender.org/api/5.1/bpy.types.UILayout.html),
[5.2 UILayout](https://docs.blender.org/api/5.2/bpy.types.UILayout.html).

## Scope still open

Palette brush-context discovery, complete sorting/reordering/keyboard behavior,
linked/read-only data presentation and weight-editing semantics remain partial.
Compact progress sizes are implemented but not covered by this generated board.
No new visual or motion approval is inferred. Full API parity remains incomplete.
The prior four controls' presented resting state was approved separately; that
approval does not transfer to new controls, sizes, states or animations.

[Animation configuration and gaps](../../../ANIMATION.md) describes the shared
spring integration. The [motion recording](motion.gif) shows actual frames from
all eight cards. Settled/disabled captures are pixel-identical to their resting
fixture, and animated frames retain geometry. The original approved resting
captures are also checked for regression.

Performance data is in `performance.json`: 20 warmup + 100 measured frames,
Blender 5.2.2 Metal, four cards at 630 logical pixels, 10,000 palette colors,
progress changing every frame. Active-motion measurements hold four springs at
an animated phase. Readback appears only in the benchmark. These are submission
measurements, not live input latency or proof of equivalence to the source
extension. Resting overhead and tail variability remain visible in the report.
