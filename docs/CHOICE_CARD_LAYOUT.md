# Choice-card text containment — 2026-11-03

## Native panel width follow-up

The first component-only checks missed a second source of truncation: Blender
can allocate an Extra button narrower than its requested width while retaining
the requested height. In the actual NVIDIA N-panel, a 420px region reserved a
390px-wide canvas but supplied only 344px. The card's text was laid out for the
larger width and then clipped in the smaller painted rectangle.

PanelHost now includes native View2D zoom in its layout metrics and learns the
actual panel gutters from the admitted native draw callback. A bounded deferred
redraw reflows the canvas at the measured width. Half-pixel rounding and gutter
hysteresis prevent integer native geometry from producing an idle layout loop.
Subsequent sidebar resizes predict the available width from the same gutters.
The card font sizes, media, shaders and native binaries are unchanged.

`tests/blender_choice_card_panel.py` exercises all three user-reported cards in a
real native panel, with actual bundled preview frames. The previous code clipped
43 lines across four zoom states. The fixed version has zero clipped lines on
NVIDIA Vulkan and OpenGL, including actual region widths 341, 420 and 540px,
native View2D zoom changes, card-center hit tests and an unchanged idle layout
counter. Both native adapters were admitted. Each backend used a fresh disposable
process with mandatory `--no-window-focus`; 50ms focus audits observed no owned
test process activation. The existing native panel scroll regression also passes
all five checks. The unit suite now has 460 passing tests; Ruff passes.

Results, focus audits and actual panel PNGs are in
[`design/qa/choice-card-overflow-v2`](design/qa/choice-card-overflow-v2/).
[Wide panel](design/qa/choice-card-overflow-v2/after-wide.png) and
[narrow panel](design/qa/choice-card-overflow-v2/after-narrow.png).
Metal execution remains unverified for this follow-up. The installed Windows
vendor contains 248 verified files, with all 46 native files unchanged. Only the
Python panel host, new geometry helper and vendor record changed in this install.
The fixed UI was subsequently reloaded through MCP with its owner lifecycle; the live scene was left unsaved. See WIZARD_CLICK_THROUGH.md.

## Initial component wrapping correction (superseded acceptance scope)

At intermediate N-panel widths, a card could calculate its height using fewer
lines than it subsequently painted. Layout rescaled glyph advances measured at
the theme size, while painting wrapped again at the card's explicit font size.
Font hinting and the separate title-size multiplier made those wraps disagree.

ChoiceCard now retains the title/body lines during layout and paints those exact
lines. Panel and floating hosts supply optional `text_measure.at_size` metrics
at the actual font size and host pixel scale. The existing two-argument callback
contract remains supported. DPI changes invalidate the panel measurement key.
No font-size reduction or additional steady-state wrapping is used. Card height,
following controls, and the whole-card click rectangle grow together. The shared
change has no platform branches or native-adapter changes.

### Component validation

- 457 unit tests and Ruff pass, including retained painting without rewrapping,
  sized metrics, widths 150–450, three theme sizes, and resize order/neighbor bounds.
- Official Blender 5.2.2 `d13f752e3b9c`, NVIDIA RTX 4090 Laptop: 8,127 real BLF
  width/theme-size/pixel-scale/language cases per backend. Baseline: 642 overflow
  cases. Fixed Vulkan and OpenGL: zero. Backends ran in separate processes.
- Actual offscreen card PNGs include the consumer's bundled preview. These are
  component captures, not live N-panel screenshots or native-adapter acceptance.
- The installed Windows vendor passed the Vulkan sweep again; all 247 vendor
  hashes match source and all 46 native files match the backup.
- The open user Blender process has no MCP listener. Its scene and preferences
  were untouched. The installed Python fix loads on the next restart.
- New Metal execution and live N-panel resizing remain unverified. Shared BLF
  measurement and existing font/theme/motion behavior are preserved.

[Before](design/qa/choice-card-overflow-v1/before.png) ·
[After](design/qa/choice-card-overflow-v1/after.png) ·
[Ordinary width](design/qa/choice-card-overflow-v1/ordinary-width.png).
Raw results and installation hashes are alongside those captures.

## Reproduction

Open CamKeys setup, advance to workflow selection, and slowly narrow the N-panel.
The Forced Perspective description previously crossed the lower card border near
some wrapping thresholds. Check that the card now grows and the next card remains
below it. Repeat at 1×, 1.5×, and 2× UI scale.

The standalone automated fixture is `tests/blender_choice_card_layout.py`, run
through `tools/run_blender_tests.py --fixture ... --gpu-backend vulkan` or
`--gpu-backend opengl` with the official executable. It uses the runner's isolated
background profile and calls `gpu.init()`. Optional `CHOICE_CARD_MEDIA` names the
consumer's `assets/demos/perspective` directory. `CHOICE_CARD_SOURCE` and
`CHOICE_CARD_BASELINE=1` reproduce the archived pre-fix vendor.
