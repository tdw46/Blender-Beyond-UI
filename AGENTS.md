# Beyond UI project instructions

## Scope

Build a product-independent, vendorable Blender custom UI library from the
Effect Layers controls. Every Blender UI control must ultimately have custom
appearance AND custom interactions. Native delegation is an explicit optional
compatibility route and must never count toward custom API parity.

Read the canonical shared Blender guidance AGENTS.md, guidance/core.md and
relevant routed topics before implementation. Do not edit the shared guidance.
Keep product bindings, registration, undo policy and renderer dependencies in
the consuming extension. Preserve Blender 4.2 compatibility paths and use exact
versioned official API/Manual evidence for compatibility claims.

## Hard rule: exact generated-reference fidelity

Tyler requires implemented custom controls to match generated references
EXACTLY. A generated reference is a visual specification, not loose inspiration.

- Save each reference in docs/design/references/ with its prompt, source-style
  references, generation tool, version and depicted dimensions/state.
- Match geometry, proportions, corner radii, spacing, typography, text alignment,
  icon geometry, colors, transparency, blur, refraction, highlights, shadows and
  every depicted interactive state exactly. Do not substitute an approximation,
  redesign a control during coding, or silently fall back to a native widget.
- Compare the actual rendered control with its saved reference at the same
  dimensions, UI scale, theme, background and state. Use side-by-side and overlay
  or image-difference evidence. Any unexplained mismatch remains an open defect;
  passing code tests does not satisfy visual acceptance.
- If additional states, themes or sizes are needed, create matching references
  for them. Do not describe unpictured behavior as visually validated.
- If a reference cannot be implemented faithfully or conflicts with required
  Blender behavior, record the conflict and resolve the reference explicitly.
  Do not quietly relax this rule or claim parity.
- Keep reference versions immutable. Retain prior versions and record which
  version each implementation and validation result targets.

## Hard rule: source-level UI performance

Tyler requires this library to remain exceptionally fast and responsive, like
the source Effect Layers UI. Visual fidelity and performance are simultaneous
requirements; neither may be traded away to satisfy the other.

- Retain GPU shaders, batches, textures, fonts and layout geometry. Rebuild only
  the resources whose input or owning context changed; bound all caches and
  release owned resources on teardown. No shader compilation, font loading,
  file/network I/O or repeated GPU resource creation in steady-state painting.
- Share one cached backdrop capture/blur per host and revision. Never add a
  separate capture, blur or framebuffer readback for every control or frame.
- Cull clipped and hidden controls before binding reads or drawing; virtualize
  long lists. Keep draw read-only and avoid full-data scans for visible rows.
- Drive redraws from input, explicit invalidation and finite animation windows.
  Idle UI must not create a permanent redraw or polling loop.
- Measure representative warm rendering and interaction workloads in Blender,
  including dense controls and scrolling. Record runtime, scale, workload,
  timing distribution and resource counts; compare equivalent workloads before
  and after changes. Tests or subjective impressions alone do not establish
  source-level speed. Investigate regressions before claiming completion.
- Keep measurement and framebuffer capture out of the production paint path.
  Do not remove transparency, blur, animations, correct interactions, older
  supported API fallbacks or exact-reference requirements as a speed shortcut.

## Hard rule: shared source squash-and-stretch animation

Every custom control must use the source Effect Layers UI's bouncy, area-preserving
squash-and-stretch motion. This includes existing and future buttons, toggles,
tabs, fields, sliders, handles, swatches, lists, disclosures, menus, popovers and
specialized controls. Read-only indicators use appropriate reveal/change motion;
they must not pretend to accept clicks. Do not leave a new control on an unrelated
animation implementation or silently omit its animation integration.

- Reuse the shared source spring/hover/release behavior and timing. Preserve
  directional impulses, finite settling and stable hit targets; animation changes
  presentation only and must never move the logical layout or mutate bindings.
- Expose documented backend configuration for `enabled` and `strength`, with
  global/host defaults and per-control overrides. Settings must be easy to change
  without modifying shaders or individual painters. Disabled animation or zero
  strength must restore the exact resting appearance and stop animation redraws.
  Default to `enabled=True` and `strength=1.0` (the source amplitude); accept only
  finite, nonnegative strength values and keep deformation nonsingular at every
  supported strength. A global/host disable must override child settings. Apply
  setting changes to existing controls without requiring an add-on reload.
- Keep animation state per host/control, retarget from the current state during
  rapid input, and bound its lifetime. Share retained GPU geometry and the cached
  glass backdrop. Never add a blur/capture pass or rebuild geometry on each tick.
- Drive redraws only while a visible animation is active. Clear animation state
  and cancel scheduled work on hide, invalidation, reload and teardown. Idle,
  hidden and disabled UI must remain quiescent.
- Validate hover, press/release, drag, retarget, settle, disable and strength
  controls, including runtime visual evidence. Static reference approval does
  not establish animation parity; document any unfinished motion integration.
  Do not mark a control complete until its applicable motion states and backend
  settings are implemented and verified. Keep generated motion references and
  actual implementation evidence available side by side for Tyler's QA.

## Evidence and publication

Maintain a member-by-member API inventory and custom parity ledger. Distinguish
implemented, execution-tested, reference-matched and unimplemented controls.
Native forwarding, concept artwork, method stubs, RNA introspection and generic
property forms do not establish custom control parity.

Use disposable Blender profiles for runtime fixtures. Do not save unrelated live
.blend files or preferences. Native ABI adapters require exact build/platform
and source/binary admission; unverified platforms fail closed. Importing the
library must not register RNA, install timers, mutate scenes or compile code.
