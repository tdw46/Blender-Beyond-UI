# Visual specifications

Hard rule: implemented controls must match the generated references exactly.
See the project `AGENTS.md` for the full acceptance contract.

| Reference | Families | State |
| --- | --- | --- |
| [Specialized controls v1](references/specialized-controls-v1.png) | Curve Mapping, Color Ramp, Data Picker, Color Picker | Reference generated; exact implementation match remains unverified |

The image, exact prompt, generator and SHA-256 are versioned together. This
reference was generated with the built-in image generation tool. The source
style is the existing Effect Layers custom UI, including its compact charcoal
glass cards, restrained cyan-blue highlights, rounded fields and outline icons.

Custom widget execution tests are not reference-match evidence. Do not mark
these controls visually accepted until actual Blender captures at the specified
size/theme/state have been directly compared to this image. Additional states
and sizes require corresponding references. Retain every reference revision.

## Current implementation comparison

[QA board](qa/v2/index.html) · [All four side by side](qa/v2/all-controls-comparison.png).
Reference left, actual Blender 5.2.2 / Metal implementation right. Tyler performs
visual QA; no control is marked reference-matched.

Revision 2 includes [transparency evidence](qa/v2/transparency.png),
[exact comparison results](qa/v2/comparison.json),
[performance measurements](qa/v2/performance.json) and
[remaining defects/specification conflicts](qa/v2/NOTES.md).
Revision 1 remains unchanged in `qa/v1/`.
