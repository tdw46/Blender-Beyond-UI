# Extraction provenance

Extracted from first-party Effect Layers UI helpers in Beyond VTuber Tools at
commit `70f28650352f61652273f32cd042fbb3df491c53`. The source working tree had
unrelated changes; it was read without modification. `extraction.json` records
the exact source-file hashes and destination paths, including any uncommitted
source bytes present at extraction time.

Retained: geometry/search/grouping, clipping, text/number/color math, rounded
GPU style and vector icons, springs, material preview shading, bounded preview
caches, shared glass/refraction, and native bridge sources.

Removed: product-specific softness scaling, BVT/VRM imports, the direct
ShoostFrame renderer dependency. The glass adapter accepts an optional host
presentation callback. The generic layout, binding, lifecycle, widget and panel
host APIs were added in this repository.

Original native exported symbol names retain their `bvt_probe_` ABI names to
avoid changing the extracted binary contract. They do not imply a runtime import
of BVT. Source and compiled-binary fingerprints are validated before loading.

The generated reference sheet uses the existing Effect Layers design language.
The prompt and generation metadata are stored beside the image. It is a visual
specification, not a screenshot proving implementation. No client scene assets,
scene renders, product shaders, credentials or shared guidance were copied.

GPL-3.0-or-later. The copied first-party code is distributed under the GPL license
already declared by its source extension. No third-party MIT-only VRMXT code was
copied; this library is independent of the exporter and renderer dependencies.
