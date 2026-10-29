# BVT sliders and switches

Tyler's 2026-10-29 screenshots replace the earlier scalar layout specification.
[Source screenshots](design/references/bvt-scalars-v1/reference.json) are retained
unchanged. [Actual Blender QA](design/qa/scalar-layout-v1/index.html) includes
side-by-side references, motion, active-theme and red-palette fixtures, and all
three scales on Blender 5.1.2 and 5.2.2.

## Shared presentation

Every custom scalar slider has a label, thin track with a shaded bubble handle,
and separate number entry on the right. `Canvas.number` defaults to this layout;
`Layout.prop(..., slider=True)` selects it for numeric RNA properties. Plain
numeric fields (`slider=False`) remain number-entry controls. All boolean
properties use switches regardless of the legacy `toggle` display hint; boolean
menu contributions use the same switch painter. Enum choices/flags retain their
selection markers because they are enum values, not boolean properties.

The source BVT `slider_parts`, slider painter and property-row layout supply
these logical dimensions: 5-unit rail, 13-unit bubble, 53-unit number field,
24-unit controls, label at 43% of the row and controls beginning at 46%.
Labeled rows narrower than 260 units stack the label above the controls. Number
fields shrink proportionally when needed. Switches use the source 46×24 input
rectangle and its 0.6 visible-size factor. Theme colors, neutral shaded handles
and shared real glass are retained; red is only an explicit comparison fixture.

The color picker's hue and alpha sliders also use bubbles and right-hand number
fields. Hue retains the rainbow data track. The narrow alpha label is stacked;
its label, track and number cell resolve the same alpha component context target.
Hue resolves the HSV hue component independently of the RGB/HSV tab. The two-
dimensional saturation/value area and authored color-ramp gradients keep their
specialized geometry. Compound artboard coordinates are normalized by the
existing host scale policy, not magnified to fill the panel.

## Interaction and animation

Clicking the rail sets an absolute value; dragging uses the rail width and soft
limits. The number box supports click-to-type and relative drag. Numeric RNA
entry retains unit parsing, hard bounds and snapshots; text entry can exceed
soft slider limits within hard bounds. Shift precision, Ctrl stepping, transaction
rollback, right-click cancellation and exact property-owner menus are preserved.
No write is submitted when clamping/rounding leaves the value unchanged.

The bubble uses the shared reciprocal-axis spring. Switch travel uses BVT's
0.36-second easing and 1.4-second spring, retargeting from its current position.
Travel tracks are bounded and retired. Changing the bound value externally
settles the position immediately rather than replaying an obsolete target.
Menu switches share the opening transform and row spring; their action retains
the existing menu close/commit policy.

[Animation settings](ANIMATION.md) still control global/host/per-control strength
and enablement. Zero/disabled motion clears travel and restores rest. Wide numeric
controls still use 15% amplitude. Logical input geometry never follows the visual
deformation. Hide, invalidation and teardown clear motion; no idle polling or
additional blur/capture producer was added.

## Evidence and limits

121 unit tests pass. Both tested Blender versions pass isolated RNA, real-window
input, numeric regression, context/menu regression and general runtime fixtures.
The real-window fixture exercises mouse track drag, cancellation, number entry,
boolean commits and exact owner context menus. The source geometry, narrow layout,
retarget continuity and hue/alpha component preservation have direct tests.

900 production motion frames across 1×, 1.5× and 2× are pixel-identical with native
text batching enabled/disabled. Static frames cover entry, disabled controls,
settling, motion disabled, boolean menus and color sliders. One shared backdrop,
one blur and five offscreens stay retained. [Validation](VALIDATION.md) records
before/after CPU paint timing, including the increased drawing cost.

The original screenshots do not specify exact theme values, UI scale or backdrop.
Source geometry reuse and these captures do not establish pixel-exact matching;
visual acceptance stays open for Tyler. Full Blender API parity, broader themes
and platforms, and exact generated motion/reference matching remain unfinished.
No new Blender API dependency was introduced. Existing 4.2 fallbacks remain, but
no 4.2 runtime was available. Exact versioned API/Manual pages were requested;
the documentation service was inaccessible during this change. Runtime evidence
is limited to the installed 5.1.2 and 5.2.2 builds, not a new compatibility claim.

Source hashes and immutable reference dimensions are in the reference manifest.
Production changes reuse `_shoost_canvas_style.py` scalar geometry/shading and
`VRM_ShoostCanvas.py` layout, numeric interaction and `_switch_position` examples;
owner-menu behavior follows `VRM_ShoostContextMenu.py` through the shared contract.
