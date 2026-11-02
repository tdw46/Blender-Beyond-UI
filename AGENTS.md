# Beyond UI project instructions

## Scope

Build a product-independent, vendorable Blender custom UI library from the
Effect Layers controls for custom third-party extension panels. Tyler narrowed
scope on 2026-10-30: do not recreate Blender's entire native UI or pursue every
UILayout template merely to complete an API inventory. Prioritize common panel
layouts, properties, buttons, menus, popovers, lists, data selectors and useful
specialized controls. Full reusable-control parity is required for extension-authored
N-panels, Properties panels, popovers, invoke dialogs/menus, dropdowns/enums and
nested menus. This is not a request to recreate built-in modifier stacks, Grease
Pencil feature panels or other Blender application/editor interfaces. Add such
feature-specific templates only on an explicit consumer requirement. See
docs/PARITY_SCOPE.md.

Full applicable right-click/context-menu parity remains in scope, including every
supported control and its individual subcontrols. Scope exclusions for built-in
feature panels must never be used to omit relevant property/operator/data context
actions. Preserve exact-owner resolution, dynamic availability, shortcuts, nested
navigation, keyboard invocation, cancellation, clipping, stale-owner protection,
glass, theming and animation. Missing applicable actions are release defects;
unsupported native-button-dependent actions must remain explicit gaps, not be
silently omitted or counted as complete.

Every supported control must have custom appearance AND custom interactions.
The BVT glass, motion, theming, right-click, scale, performance and exact-reference
requirements remain mandatory. Native delegation is an explicit optional
compatibility route and must never count toward custom parity. Keep the full API
inventory for transparency, but distinguish out-of-scope members from supported
core defects; full Blender API coverage is no longer the product release goal.

Read the canonical shared Blender guidance AGENTS.md, guidance/core.md and
relevant routed topics before implementation. Do not edit the shared guidance.
Keep product bindings, registration, undo policy and renderer dependencies in
the consuming extension.

Compatibility target confirmed by Tyler on 2026-11-02: support every release
family from Blender 4.2 onward. Metal, Vulkan and OpenGL paths must retain the
same controls and context actions wherever Blender provides that backend. Do not
raise the minimum or count a native fallback as custom compatibility. Qualify
exact stock builds for native ABI adapters; list unqualified builds and GPU
validation separately from implemented version branches. Preserve Blender 4.2 compatibility paths and use exact
versioned official API/Manual evidence for compatibility claims.

## Hard rule: exact generated-reference fidelity

### Current acceptance correction — 2026-11-01

Tyler subsequently clarified: "Doesn't have to be perfect, just close." For the
current CamKeys styling/refinement work, prioritize a close, consistent match
and practical readability over pixel-exact reproduction. Use the references and
side-by-side evidence, report remaining differences honestly, and preserve all
glass, motion, theme, ownership and performance requirements. Do not spend further
turns chasing generated-artwork minutiae or treat them as release blockers.
This explicit correction supersedes the exact-match acceptance wording below
for this work; retain immutable references and evidence.

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

## Hard rule: consistent host UI scale

Tyler requires approximately consistent UI scale across all controls and popovers.
Use host logical units for body text, titles, icons and interaction rows. Authored
reference/artboard pixels must not be treated as host pixels or magnified to fill
available panel width. Normalize compound controls through the shared dimensions
policy and all compound popovers through `Canvas.open_widget`; preserve aspect
ratio, logical hit mapping, owner menus, glass and animation. Audit every new
control beside ordinary fields at 1×, 1.5× and 2×, including narrow/wide bounds.
See docs/UI_SCALING.md for the 2026-10-29 user correction and reference precedence.

## Hard rule: BVT scalar layouts

Every custom scalar slider uses the source label, thin track, animated bubble
handle and separate right-hand number field. Use shared source geometry for
painting and hit testing; narrow rows stack the label without enlarging fonts.
All boolean properties use source toggle switches, including contributed menu
rows. Explicitly authored unembossed Boolean action buttons (such as HOW TO)
retain centered/aligned button presentation without a switch; ordinary Boolean
fields retain switches. Honor author alignment and keep icon-only menu carets
centered. This is Tyler’s 2026-10-31 semantic correction. Plain numeric entry fields and enum selection markers retain their distinct
semantics. Preserve exact owner menus, Blender theme colors, shared glass, source
motion and the 15% wide-numeric amplitude rule. See docs/SCALAR_CONTROLS.md and the
immutable user screenshots in docs/design/references/bvt-scalars-v1/.

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

## Hard rule: real BVT liquid glass

Real liquid glass is mandatory for every translucent custom UI surface, including
panels, menus, nested menus, tooltips, popovers and compound controls. Use the
original BVT shared backdrop, Gaussian blur levels, refractive lens and rim
behavior. Menus/tooltips use the source's stronger blur; underlying text must
be softened rather than clearly readable through a plain alpha overlay.

- This is a completion and publication gate, not an optional polish step. Never
  label tint-only alpha blending, an opaque sheet, baked artwork or a CSS-style
  imitation as liquid glass. Generated references must preserve real source
  glass behavior; reject conflicting references explicitly.
- Default supported hosts to real glass. Keep capability fallback explicit and
  observable; unavailable/disabled glass is degraded behavior and cannot count
  as visual acceptance or parity. Do not quietly default new hosts to fallback.
- Share one retained backdrop/blur revision across surfaces and animations.
  No per-control/per-frame capture, blur, readback or idle refresh loop. Disabling
  motion must not disable glass. Apply theme roles without flattening the glass.
- Verify actual Blender-rendered glass over text, controls and contrasting
  backgrounds, at rest and during motion, including nested overlays. Keep raw
  captures, before/after comparisons and resource/revision counts. Unexplained
  legibility, blur, refraction or rim mismatches remain open defects.

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
- Tyler's numeric-field correction: numeric controls spanning at least 75% of the
  usable panel width use 15% of their otherwise resolved motion amplitude.
  Preserve the source spring/timing and area preservation; keep compact controls
  and menus unchanged. Expose this as `Canvas.wide_numeric_motion_scale` and apply
  changes to existing controls. Parent disable/zero strength still wins.
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

### Pie landing exception — Tyler's 2026-10-30 correction

Pie surface tension applies only while approaching. Once the pointer is inside
an item's logical petal (including compound padding), immediately restore its
resting shape/position and discard the approach springs. Do not add row, toggle
or field hover/press deformation on top. Keep the opening reveal, proximity
highlight, origin guide, stable hit geometry, shared glass and ordinary nested
list/context-menu motion. Leaving the petal restarts approach motion from rest.

## Hard rule: consistent right-click menus

Preserve the source Effect Layers UI's right-click/context-menu support across
every applicable custom control, including compound controls and their individual
fields, handles, rows and swatches. A control is not complete when it only supports
left-click interaction.

Use the original BVT `VRM_ShoostContextMenu.py` and the context-menu routing in
`VRM_ShoostCanvas.py` as the implementation/behavior examples. Inspect those
examples before changing this contract; do not substitute guessed generic-menu
behavior. Keep BVT-specific resolution and operators in the consuming extension.

- Use one shared, host-extensible context-menu contract. Preserve the source's
  menu appearance, ordering, nested navigation, shortcuts, keyboard selection,
  dismissal, clipping, glass treatment and bounded squash-and-stretch motion.
- Every visible menu option must follow the opening squash/stretch transform,
  including labels, shortcut hints, disabled rows, checks, arrows and inline values.
  Submit text under its owning transform; deferred font batches must not leave
  final rows or specific actions stationary. Verify with native text batching
  enabled as well as standalone captures, and preserve the settled batching path.
- Resolve actions against the exact clicked control/subcontrol and current owner.
  Revalidate bindings and capabilities before execution. Expose applicable
  property/data actions through the consuming extension's context and undo policy;
  never invent enabled actions or mutate the wrong element after sorting/deletion.
- Preserve right-click cancellation during active edits/drags before opening a
  menu. Outside the owned hit area, pass the event through to Blender. Do not
  indiscriminately swallow right-click or replace all context actions with cancel.
- Track missing menu/action coverage explicitly. Validate mouse and keyboard
  invocation, nested/back navigation, stale owners, disabled actions, cancellation
  and teardown before claiming parity. Keep menu references and actual QA captures.

## Hard rule: pull colors from Blender's active theme

Custom UI must obtain its semantic colors from Blender's active theme, as the
source does. A fixed reference palette must not silently override the user's
Blender theme in production.

Use original BVT `_shoost_canvas_style.py::theme_palette` / `_theme_palette` as
the color-extraction and glass-opacity examples. Its theme colors are already
display-space: do not apply scene-linear color conversion, saturation guessing,
preference mutation or a theme polling timer. Record audited source revisions in
this repository's provenance notes.

- Centralize theme-to-role mapping for text, titles, fields, buttons, selections,
  hover/focus highlights, disabled states, sliders, graphs, curves and points.
  All painters, icons, menus and popovers must use those shared roles.
  Theme the UI chrome, not user-authored data: palette/ramp colors, color-picker
  values and image previews must retain their bound values and color handling.
- Preserve the source's translucent glass, alpha hierarchy, blur/refraction and
  readable contrast while adapting colors. Do not turn translucent controls into
  opaque native-theme rectangles or hard-code blue highlights across themes.
- Capability-gate theme API access across the supported Blender versions. Keep
  deterministic fallback colors for unavailable theme data and explicit reference
  fixtures only; document fallback use rather than pretending it is theme-derived.
- Apply active-theme changes without reloading the extension. Cache the resolved
  palette per host/revision; do not scan all theme properties, rebuild GPU geometry,
  or capture/blur a new backdrop for every control or animation tick.
- Record the theme and color-management context used for each reference/capture.
  Compare exact fidelity under the reference theme and validate light/dark/custom
  themes separately. Track missing theme plumbing as a parity defect.

## Hard rule: automated tests must preserve user focus

Never activate Blender or steal focus from Tyler's current app during automated
tests. Run nonvisual fixtures with `--background`. Window-dependent GPU captures
and simulated N-panel input must use `--no-window-focus` before file/script
arguments through `tools/run_blender_tests.py`; it checks the installed executable
for that capability and refuses a windowed launch if unavailable. Use disposable
profiles and Blender-internal simulated events, never desktop input injection or
deliberate activation or raising of Blender. Revalidate no activation when changing
the runtime, platform or window workflow, including additional windows. If a test
needs foreground focus, leave it explicitly unverified and continue safe work
unless Tyler authorizes foreground testing. Stop only owned test processes.
See `docs/BACKGROUND_TESTING.md` for the verified capture/input path and limits.

Standing authorization (2026-10-30): Tyler permits no-focus launched windows
whenever needed, without per-run permission. This supersedes the earlier one-time
exception and blanket windowed-test suspension. The shared runner admits these
launches while retaining mandatory `--no-window-focus` capability checks.
The prior unsolicited activation remains recorded in `docs/BACKGROUND_TESTING.md`;
authorization does not establish focus safety. Audit changed workflows, report
unexpected activation and investigate without deliberately activating or raising Blender.
Deliberate foreground activation still requires explicit authorization.

## Evidence and publication

Maintain a member-by-member API inventory and custom parity ledger. Distinguish
implemented, execution-tested, reference-matched and unimplemented controls.
Native forwarding, concept artwork, method stubs, RNA introspection and generic
property forms do not establish custom control parity.

Use disposable Blender profiles for runtime fixtures. Do not save unrelated live
.blend files or preferences. Native ABI adapters require exact build/platform
and source/binary admission; unverified platforms fail closed. Importing the
library must not register RNA, install timers, mutate scenes or compile code.

## Hard rule: keep the overview estimate current

After every project turn, review docs/design/qa/overview/estimate.json and the
overview header. Update remaining work, turn/time ranges, assumptions, media gaps
and the review record as evidence changes, then regenerate with
`python3 tools/build_overview.py`. Discussion-only turns do not automatically
reduce remaining implementation turns. Estimates must remain explicitly uncertain;
never invent measured timing or promote execution evidence to visual acceptance.
Keep the overview's recorded GIF inventory aligned with implemented features,
and identify missing dedicated captures explicitly until they are produced.

Estimate accounting must record completed planned work and newly added scope.
When planned implementation work closes, reduce the remaining budget or explain
the specific new work/revised workload that offsets it. Generic pending QA or
uncertainty is not a reason to erase progress. Distinguish observed duration,
user-reported pace, simple extrapolation and an actual completion forecast.

## Approved menu rhythm and capture correction (2026-10-30)

Use `beyond_ui/menu_metrics.py` for menu/popover row spacing, title/search gaps,
insets and title sizing. The approved macOS reference supersedes the older
boxed-option designs. Inactive options have no individual surface; preserve the
selected/hovered highlight. All search bars include a left magnifier and reserve
the same inset for text, selection and caret. Keep titles in the retained bold
font. Popup reflow must preserve its menu metrics while inheriting current parent
theme roles; never overwrite compact menu geometry with ordinary panel rows.
Normalize pointer/collection pickers as well as enum, registered, nested and
right-click menus. Keep ordinary panel controls at host scale, with their BVT
slider/switch semantics. Reference geometry is a logical-unit specification, not
permission to enlarge controls to artboard pixels.

Tyler additionally authorized restoring the prior app after an owned test launch
if needed. Prefer the test-only LaunchServices launcher with `activates=false`
and Blender's `--no-window-focus`. The bounded restoration fallback may target
only the most recent non-owned app, only when the owned test process becomes
frontmost. Record any activation/restoration; restoration is not zero focus
theft. Never deliberately activate Blender, close unrelated sessions or restore
focus over a different app the user chose. This supersedes the older restoration
prohibition for these test launches; it does not establish general focus safety.

## External field labels and optional icons (2026-10-30)

Keep labels outside editable values at the left throughout the library. Use the
shared entry geometry; sliders keep their original BVT scalar layout. Every
label must support an optional icon, with a consistent silhouette/gutter and
shared theme/motion. Preserve exact field ownership and value-only editing.
Center action-button text/icon groups, including confirmation and cancellation.
Menu highlight expansion is visual only: do not displace adjacent text or hit
targets. Use macOS restraint for new generated references. See FIELD_LABELS.md
under docs for the public icon contract and reference versions.

## Centered button artwork and shared panel grid (2026-10-31)

Every icon-only button centers its visible glyph in both axes, including locks,
list toolbar dropdowns and vector fallback glyphs. Transparent source-art margins
must not offset the silhouette. Retain original glyph proportions and theme tint;
center icon/text action groups together. Compute atlas ink bounds offline and
vector bounds once when building their retained batch; never scan pixels in paint.
Keep this in shared rendering code, with actual raster checks at 1x/1.5x/2x.

All external panel labels, switches and color controls share the same left inset.
Use shared logical design tokens, intrinsic/minimum widths, gutters, row-spanning
captions and synchronized label stacking for paired fields. Do not patch consumer
labels or add product-name checks to achieve reference spacing. Preserve authored
explicit sizing, property ownership, BVT motion, glass and theme extraction.


## Responsive panel hierarchy and utility lanes (2026-10-31)

For adopted third-party panels, infer section headings from structure, never from
product-specific label strings. Keep full-size ordinary switches, compact icon
buttons and short unit suffixes at their intrinsic widths. Clamp percentage splits
to usable minimums and reflow a group when it cannot fit. Keep labels outside values;
stack a field label before truncating it when space is insufficient. Wrap long
section titles. Align input accessories with the editable value while preserving
top-aligned list toolbars. Apply shared gutters and label columns during retained
layout only. Menus, source animation, exact owners and glass remain independent.
See docs/PANEL_LAYOUT.md for the policy and explicit low-level opt-out.
