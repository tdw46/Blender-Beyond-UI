# CamKeys guided setup — approved B direction

Status: B approved and implemented. See `../../qa/camkeys-onboarding-v2/` for runtime evidence. No version bump. Four design directions each depict the same six
screens: target, workflow, three alternative branch setup screens, completion.
The three branch screens are alternatives, not a six-step required sequence.

## Recommended flow

1. Choose a subject/focus object using a searchable object picker or eyedropper.
   Reuse CamKeys' existing armature association logic. If an armature exists,
   show an editable bone picker and recommend a verified VRM 0/1 humanoid Head
   mapping. Do not assume a bone literally named Head; do not require VRM.
   Multiple rigs require explicit resolution. No rig: omit bone controls.
   Armature selection for shape-key workflows must resolve a mesh explicitly
   when several meshes are possible; do not silently choose an arbitrary mesh.
2. Choose Shapekeys × Camera Angle, Forced Perspective, or Dolly Zoom + Camera
   Tricks. Use semantic icons, one-line explanations and contextual demos.
3. Show the appropriate minimal branch controls. Camera-angle workflow: source
   (Viewport/Camera), shape-key search, capture current view, sensitivity.
   Forced perspective: camera, inherited focus, apparent focal length.
   Dolly zoom: camera, inherited focus, starting lens and an explicit non-authoring animated-example
   preview. Missing camera/shape keys show an actionable explanation rather than
   a silent auto-created object. Do not imply preview has authored keyframes.
4. Create setup through an explicit undoable consumer action, summarize what
   changed, then open full controls. Offer another workflow and further help.

Use Back at every noninitial step, retain draft inputs across navigation, and
provide an always-available Open full controls escape. Match reference copy except Tyler's explicit step-2 Forced Perspective/Dolly overrides. Media captions, timestamps and controls are omitted by request. Correct skipped Back buttons and inconsistent progress numbers. Mockup demo pictures and durations are generated
placeholders, not captures of the supplied clips. Use the existing approved
CamKeys logo asset rather than replacing it with a generated camera/aperture mark.

## Ownership boundary

**BUI:** reusable wizard/step containers, responsive field and help lanes,
progress and validation presentation, accessible focus transfer, clipped slide
transition using existing motion settings (including disabled motion), media
surface/poster/playback controls, and reusable help popovers. All ordinary
properties retain exact-owner right click and native tooltip/developer metadata.
No CamKeys names, VRM knowledge, or scene-completeness heuristics in BUI.

**CamKeys:** workflow graph, draft values, target/rig/head discovery, per-workflow
requirements, idempotent transactional setup commands, existing-property mapping,
help copy, media IDs and onboarding visibility. Read-only poll/draw checks use
cached revisions rather than scanning the scene each draw. Next validates the
draft; only explicit setup/capture actions write meaningful scene state.

**Media dependency:** pin a redistributable package with license/provenance and
expose it through a generic BUI media provider. Current BVT checkout implements
its inspected animated warning UI via `animated_warning_popovers.py` calling
`VRM_Posing.animated_preview_icon_id`; a separate vendored package named
"Blender animated UI" was not identified in this audit. Resolve that dependency
before implementation; do not vendor BVT's monolithic posing module into CamKeys.
Reuse its bounded, duration-aware, visible-only playback behavior, with package
frame caches prepared outside draw. No runtime system FFmpeg dependency for end
users. Preprocess distributable frames/posters, cache GPU/preview resources,
pause hidden/closed help, and guarantee owner-scoped popup cleanup. Respect
source aspect ratios and clip durations; any sampled preview is labeled as such.

## When to show it

Use one setup panel for an unconfigured target/new scene. Existing configured
projects retain their panels. An incomplete optional feature must not replace
otherwise working full UI or repeatedly force onboarding. Store explicit
completed/dismissed state with a schema; treat deleted targets as repairable
rather than silently rebuilding. Provide Run Setup from full UI. Use native
panel poll/consumer routing to choose setup versus normal panels; keep that
policy out of the reusable library.

## Supplied media placement (attachment numbers)

| Attachment | Setup and full UI help placement |
| --- | --- |
| 1 | Forced Perspective preview and section ? |
| 2 | Camera-angle/shape-key preview and linking ? |
| 3 | Dolly Zoom preview and camera-trick ? |
| 4 | Billboard Emulation row ? |
| 5 | CamProps section ? |
| 6 | CamProps additional example, as requested despite its AutoFOV filename |
| 7 | Apparent FOV/focal-length row ? |
| 8 | CamKeys additional example tab, also relevant to CamProps |

`media-manifest.json` records all eight verified local sources, codecs, sizes and
durations. Help buttons belong in the same accessory lane as settings cogs, with
separate hit targets. No automatic simultaneous playback of every hidden demo.

## Implementation gates after approval

- Confirm chosen A/B/C/D direction or per-stage mix; freeze approved references.
- Audit exact versioned API/runtime support from Blender 4.2 onward. No support
  claim from mockups. Retain older fallbacks and default theme/custom accents.
- Build generic BUI primitives plus CamKeys workflow logic and media adapter.
- Exercise no-armature, VRM0/1, ambiguous rigs, missing keys/cameras, deletion,
  cancel/back/reopen, existing scenes, undo/redo, native fallback, and teardown.
- Exercise Metal, Vulkan and OpenGL where supplied by each Blender version;
  hardware Windows validation is separate from Mac tests.
- Verify slide/disabled-motion, glass, right-click, scroll chaining, scaling,
  video lifecycle and no hidden polling/decoding. Preserve unrelated scenes.

The boards remain immutable design references, not runtime proof. New execution and Metal rendering evidence lives in the v2 review; Windows and older-version wizard hardware QA remains open.

Implementation update: the dependency was resolved to the pinned pure cache/timing subset of `tdw46/blender-animated-ui`, commit `33b7bbf3b2049a9bacfb7241eb484f7fed31be5e`. The source-audit discussion above is historical. Subject media uses attachment 7 (verified Sonic content), per Tyler's correction; its attachment number was initially recalled as 8.
