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

## Evidence and publication

Maintain a member-by-member API inventory and custom parity ledger. Distinguish
implemented, execution-tested, reference-matched and unimplemented controls.
Native forwarding, concept artwork, method stubs, RNA introspection and generic
property forms do not establish custom control parity.

Use disposable Blender profiles for runtime fixtures. Do not save unrelated live
.blend files or preferences. Native ABI adapters require exact build/platform
and source/binary admission; unverified platforms fail closed. Importing the
library must not register RNA, install timers, mutate scenes or compile code.
