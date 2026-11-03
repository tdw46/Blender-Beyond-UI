# Wizard double-click correction — 2026-11-03

An ordinary BUI button treated both PRESS and DOUBLE_CLICK as new actions. In
CamKeys, Next moves from workflow selection to configuration. The shorter new
page places Open full controls over part of the former Next rectangle, so the
second click could immediately dismiss the wizard.

Ordinary button actions now consume DOUBLE_CLICK without executing again.
Controls with explicit action_event callbacks retain their event semantics;
numeric editing and list-row rename double-clicks remain supported. This changes
no shaders, native adapters, layout, motion, or continuous polling.

Reproduce with an Uraraka copy in workflow selection, Forced Perspective selected:
click the right half of Next, then deliver the double-click event at the same
window position after the new page is drawn. Previously state became step=2,
force=False, dismissed=True (full controls). It now stays step=2, force=True,
dismissed=False (human step 3). A deliberate fresh Open press still exits.

Validation on official Blender 5.2.2 d13f752e3b9c, NVIDIA RTX 4090 Laptop:

| Check | Result |
| --- | --- |
| Native BUI Uraraka copy, Vulkan | Pass |
| Native BUI Uraraka copy, OpenGL, separate process | Pass |
| Actual CamKeys controls, all three routes | Pass |
| Unit suite including numeric and explicit double-click behavior | 462 pass |
| Live MCP UI owner teardown/reload, source bytecode verification | Pass |
| Metal execution | Unverified on this Windows host |

Native reproduction uses Blender-internal PRESS/RELEASE for Next, followed by
a DOUBLE_CLICK dispatched through BUI's runtime: Blender event_simulate does
not accept that value. The all-route fixture dispatches BUI canvases directly
and establishes functional behavior, not independent native renderer acceptance.
Both native runs admit the adapter, report no UI fallback/errors, and preserve
foreground focus (50ms audit). No original scene or preferences were saved.
The live reload preserved wizard state, frame, item/object counts and enabled
state; all unrelated extension modals remained running.

[Evidence](design/qa/wizard-click-through-v1/) includes the before/after states,
all-route checks, focus audits and a [native step-3 capture](design/qa/wizard-click-through-v1/step3.png).
`tests/blender_onboarding_click_through.py` is the portable consumer regression;
`tests/test_button_click_through.py` checks replacement-page and explicit-event
semantics without Blender. The captured Uraraka file stays outside the repository.
