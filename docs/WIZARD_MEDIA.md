# Wizards and looping help media

Consumers keep workflow state, validation, target detection and undoable scene
changes. Beyond UI supplies reusable presentation; it has no CamKeys/VRM rules.
All helpers are native-safe: outside adopted BUI layouts they use ordinary
Blender layouts, with an explicit static-poster/unavailable-preview fallback.

```python
from ._vendor import beyond_ui as bui

body = bui.wizard(layout, state.step, title="Choose your subject",
                  subtitle="A character or any focus object.",
                  step=state.step + 1, steps=4, direction=state.direction,
                  brand="My add-on", icon=my_existing_artwork,
                  padding=8, gap=7, title_size=20)
body.prop(state, "subject")
bui.badge(body, "Rig detected", icon="ARMATURE_DATA",
          width=114, height=20, color_role="toggle_on")
bui.choice(body, state, "workflow", "SHAPES", title="Camera shapes",
           description="Blend shapes as the view changes.",
           library=media_library, media_key="shapes", height=88,
           media_width=96, padding=6, radius=10, font_size=11.5,
           description_size=9.5, line_height=13, radio_size=14)
bui.segmented(body, state, "source",
              icons={"VIEWPORT": "VIEW_CAMERA", "CAMERA": "CAMERA_DATA"})
bui.media(body, media_library, "shapes", height=130, radius=12)
bui.help_button(body, "my_addon.show_example", example="shapes")
bui.help_row(body, "my_addon.show_example", text="Lens tricks",
             icon="CAMERA_DATA", artwork="BUI_APERTURE", example="lens",
             height=30, radius=9, font_size=12.5, help_size=24)
```

`bui.style` remains available on groups and ordinary controls. Choice cards and
segments retain ordinary enum bindings: selection, tooltip metadata, ownership,
right-click and shared motion are not implemented as separate decorative hit areas.
Choice cards grow vertically at narrow widths instead of shrinking text. Status
badges are read-only. `QUESTION`/`BUI_HELP` use the shared retained circled-help
glyph; editable SVG source is in `beyond_ui/assets/icons/bui_help.svg`.
Help rows keep the feature label and leading icon aligned left, with an independent
24-unit help accessory on the right. Both invoke the same consumer-owned operator.
Use `artwork` for a BUI glyph while `icon` supplies the native Blender fallback.
The reusable glyphs `BUI_BACK`, `BUI_EXTERNAL`, `BUI_ADJUSTMENTS`, `BUI_LAYERS`,
`BUI_CLAPPERBOARD` and `BUI_APERTURE` use retained theme-tinted vector geometry;
editable SVG design sources are bundled alongside `bui_help.svg`.
`bui.style(..., radius=16)` now uses the same radius for a button's glass and rim;
`trailing_icon` is rendered for ordinary actions as well as Boolean actions.
`wizard(..., completed=True)` adds the centered read-only completion check.

Wizard transitions use the host's existing finite spring, strength, speed and
disable settings. Presentation moves; logical hit areas do not. Pass persistent
step state to the normal retained/adopted layout. A new token starts a transition;
ordinary value refreshes do not.

## Media provider and lifetime

Create `MediaLibrary(provider, fps=10, budget_bytes=96*1024*1024)` during consumer
registration, and call `close()` during consumer teardown. Importing BUI does not
register timers or touch Blender data. The provider must implement:

- `frame(key, elapsed_ms) -> (token, width, height, pixels_callable)`.
- `pixels_callable()` returns bottom-up, straight-alpha, display-space RGBA8 bytes.
- `close()` releases prepared source buffers.
- Optional `poster(key)` returns a native preview icon ID for native fallback.

Prepare files outside paint. The scheduler decodes/uploads on cache misses only;
painting reuses textures. The bounded LRU retains frames across loops. The active
visible owner and a short stale-lease guard stop scheduling for hidden/closed
surfaces. Teardown releases timers, leases, textures and provider buffers. Errors
are observable in `library.errors`; failed clips do not poll forever. Source
aspect ratio is preserved. Media has no transport controls or time readout;
CamKeys also deliberately supplies no overlay captions.

CamKeys vendors the pure cache-schema/timing modules from `blender-animated-ui`
at `33b7bbf3b2049a9bacfb7241eb484f7fed31be5e`, with GPL-3.0 license and hashes.
Its packed provider owns preprocessing/storage. End users need no FFmpeg, codec
wheels or network access. Eight clips preserve full duration at a sampled 10 FPS,
maximum 320px source edge. This is an intentional preview quality limit, not
original-video fidelity. The onboarding `Preview` button opens the looping Dolly
example; scene effects are authored only by `Create setup`.

## Evidence and limits

See [onboarding review](design/qa/camkeys-onboarding-v2/index.html): actual Metal
component captures from the saved Uraraka scene, native-popup playback/cleanup,
queued eyedropper input and 5.1.2/5.2.2 setup execution. Component images are not
live-sidebar screenshots. Existing glass and GPU abstraction paths are retained;
this new feature has not yet received physical Windows/Vulkan/OpenGL or Blender
4.2 runtime validation. No minimum version or native adapter was changed.

## Localization

Register full message IDs through the consumer's normal Blender translation
catalog. Choice titles/descriptions and badge text resolve through the active
interface language before measured layout. Cards wrap Latin words and CJK
characters using the same retained line-break policy in layout and paint.
`bui.badge(layout, object.name, translate=False)` preserves user-authored data;
`text_ctxt` supports consumer-specific meanings. Ordinary `layout.operator`
already accepts `text_ctxt`, for example to distinguish navigation Back from a
spatial direction. Do not translate partial wrapped lines. Native fallback
progress is language-neutral (`1 / 4`). Media loading/error messages are resolved
at widget construction, not during painting.

CamKeys' catalog/runtime/help audit and selected locale renders are in
[localized onboarding and help](design/qa/onboarding-locales-v1/index.html).
