# Custom panel popovers

`Layout.popover`, `prop_with_popover` and `popover_group` now use registered Python
Panel definitions to build retained custom canvases. The Panel proxy exposes
Blender's `is_popover` flag. Beyond UI also provides a convenience
`Layout.is_popover` flag that propagates to layout children; that helper is not a
Blender UILayout API member or an extra ledger completion. The three API entries
remain partial; complete UI and visual parity is not established.

```python
ui.popover("MYEXT_PT_settings", text="Settings")
ui.prop_with_popover(context.object, "display_type", panel="MYEXT_PT_display")
ui.prop_with_popover(context.object, "color", panel="MYEXT_PT_color")
ui.popover_group("VIEW_3D", "UI", "", "My Extension")
```

The consuming extension owns Panel/operator registration, context, undo and
property commits. Importing the library does not install timers, register RNA,
mutate scenes or compile code.

## Drawing and ownership

A panel's Python draw callback authors the current custom Layout once on opening.
It can use the implemented sliders, switches, fields, enum controls, menus,
pickers, specialized editors, rows, columns and grids. Unsupported draw calls
reject the popup instead of leaving partial controls. Python helper methods are
supported through a proxy with `is_popover=True`.

Header callbacks author controls beside the opener, as in Blender's panel-button
API. Header failure rolls back only the new controls/groups. Header and body
controls retain their original panel definition, draw callbacks, owning context
and parent eligibility. Input rechecks poll and ownership before edits and
operator execution; stale deferred actions also reject execution. Unregistering
or replacing a definition requires rebuilding its controls.

Enum and color property popovers expose the original `button_pointer` and
`button_prop`. Their custom closed fields continue to display current property
values. Ordinary panel buttons clear stale native-button context. Context
pointers, strings, host commit callbacks, pointer-source policies and ID-action
dispatchers propagate into panel contents.

`popover_group` snapshots registered Python Panel subclasses on authoring,
filters exact space/region/context and optional category, excludes subpanels,
checks poll and orders by `bl_order` with discovery order for ties. Discovery is
bounded at 4096 classes and 256 matching openers. It never scans the registry in
painting. Full native region-list registration order is not claimed.

## Shared appearance and input

Panels open through `Canvas.open_widget`, with widths derived from
`bl_ui_units_x` in host logical units and clamped to the host clip. Vertical and horizontal attachment use the same
central opening path, including on older runtimes without the native direction
keyword. Controls keep
the host's font and row scale; narrow layouts reflow and short layouts scroll.
The scrollbar supports dragging, wheel input and right-click top/bottom actions.
Painting culls clipped controls before binding reads.

Every panel uses the host's retained liquid-glass backdrop and stronger menu blur.
The resolved active-theme palette is passed into nested canvases, preserving
user-authored colors and avoiding another theme scan for each child. There is no
per-panel capture, blur producer, font load or shader compilation during painting.

Opening motion transforms the entire child canvas, including text and nested
controls. Individual controls retain their existing source motion. Parent/host
animation disable and strength apply to existing children; wide numeric controls
retain the 15% amplitude rule. One host scheduler advances child animations and
stops when they settle. Invalidation and teardown cancel child edits, menus,
animations and tooltips.

Property, operator, picker and menu context actions retain their exact clicked
owners inside popovers. The host finds nested menus for tooltip scheduling and
input priority. Escape dismisses the current edit/menu/nested panel before its
parent. Outside right-click dismissal passes the event through. Popover opening
is also available through the shared context-menu and shortcut routes. Child
canvas shortcut bindings are scoped to the current opening and released on
dismissal without removing a newer binding that replaced them. Native operator
shortcuts retain their existing semantics. Persistent custom-canvas shortcuts
across reopened panels require explicit stable host command identities; they
are not inferred from row positions or labels.

## Remaining gaps

This does not implement unsupported Layout methods inside a Panel. C-only draw
callbacks, helpers requiring native Panel instances/custom data, automatic
subpanel expansion, pinned/instanced panel behavior, preview icons, icon-only
property presentation, and complete focus/accessibility traversal remain open.
Group discovery does not enumerate native-only panels. Poll-derived opener
availability updates on authoring and pointer/input events, not an idle poll loop;
changes without input require the consuming host's normal UI invalidation.

Generated-reference acceptance, light/custom-theme visual QA, Blender 4.2 runtime,
other platforms and full source-speed qualification remain open. Existing BVT
controls are reused; there is no newly approved generated reference for this
composition. Tyler owns visual validation.

## Evidence

[QA gallery](design/qa/panel-popovers-v1/index.html) contains actual Blender
5.1.2/5.2.2 frames at 1×, 1.5× and 2×, nested glass, context menus, narrow/scrolled
panels and disabled motion, plus the README GIF. Capture checks compare native
text batching with standalone text and count draw/poll callbacks and retained
resources. These checks do not establish exact-reference acceptance.

The [4.2 UILayout API](https://docs.blender.org/api/4.2/bpy.types.UILayout.html),
[5.1 Panel API](https://docs.blender.org/api/5.1/bpy.types.Panel.html) and
[5.2 Panel API](https://docs.blender.org/api/5.2/bpy.types.Panel.html) supply the
public API baseline. Exact versioned English Manual and 5.1/5.2 UILayout fetches
were unavailable; immutable official 4.2.0 and installed-build source revisions
are recorded in the [source audit](design/qa/panel-popovers-v1/source-audit.json).
Installed runtimes are tested in disposable profiles. No unrelated live Blender
scene or preferences are saved.

## CamKeys popup lifetime correction — 2026-11-02

The shared routed-popup driver used to treat an absent `context_menu` as a closed
surface, even when a panel widget remained in `canvas.overlay`. Flatten Falloff
therefore opened successfully and immediately vanished on the next event. The
driver now finishes only after both menu and panel overlay are gone. No timer,
new API dependency, glass, motion or geometry change is involved.

[Audit results](design/qa/popover-audit-v1/report.json) record 11 actual Uraraka
cases on Blender 5.2.2: all six registered CamKeys popover families, the Flatten
operator route, Appearance and Add Billboard Group dialogs, shape-mode Dolly
Expressions and angle-owned falloff. Each custom surface painted with glass,
survived real mouse movement and dismissed with Escape. Separate embedded tests
verified property edits, nested dismissal and exact-owner right-click menus;
an injected custom-build failure opened the recorded native recovery path.
397 unit tests passed. Owned test launches recorded no focus activation.

The updated handler was patched in place in live Uraraka without unregistering
RNA or saving the dirty scene; Flatten Falloff stayed open with 27 controls and
an active glass backdrop. The consumer's chosen color mode was preserved.
These are execution checks, not new visual-reference or all-data-state approval.

## In-place window composition and viewport glass — 2026-11-02

The preceding lifetime audit did not establish correct placement or backdrop
content. User QA exposed two presentation defects: floating surfaces were drawn
in `WINDOW/POST_PIXEL` before the sidebar, then constrained to its left; their
backdrop came from that early framebuffer. A second child-canvas background coat
also obscured the glass in panel popovers.

`hosts/window_overlay.py` now multiplexes the already admitted native bridge's
window callback across vendored libraries. This stage runs after area/sidebar
composition and before native floating menus. Bounds include the sidebar;
event ownership remains in the original invoking region. Painting uses actual
framebuffer pixels (not Window RNA points on Retina), explicit projection and
scissor scope. Teardown removes only the owned callback and scene invalidation
handler. Missing native capability still raises the existing explicit fallback.

At that checkpoint, floating 3D View surfaces sampled the completed viewport's color/overlay
textures through the same retained Gaussian/lens pipeline as embedded panels.
Scene/view changes invalidate the source; popup hover animation reuses it.
Properties editors and non-overlapping layouts use the completed composed
framebuffer because no viewport exists behind those regions. PanelPopover owns
one glass sheet; its child painter no longer adds a second background coat.

[Actual captures and results](design/qa/popup-window-v1/index.html): 400 unit tests;
11 Uraraka popup cases on each of Blender 5.1.2/5.2.2; sidebar-inclusive placement,
real viewport source, cache reuse on hover, input survival, Escape and callback
cleanup. Direct-dialog/menu/pie/search, exact-owner right-click, nested dismissal,
RNA editing, undo and registration regressions passed. The live installed CamKeys
vendor was updated and reloaded without saving Uraraka. All these GPU tests ran
on macOS Metal; no new 4.2, Vulkan or OpenGL runtime qualification is claimed.

The exact-build [Blender compositor source](https://github.com/blender/blender/blob/d13f752e3b9c/source/blender/windowmanager/intern/wm_draw.cc#L1094-L1122)
places window callbacks between overlapping regions and floating native menus.
Exact 4.2/5.1/5.2 API/Manual fetches were attempted but unavailable in this audit;
installed runtime execution supplies the 5.1/5.2 evidence. Native bridge source,
binary fingerprints, admission list and minimum supported version are unchanged.

Capture note: `screen.screenshot` recomposites region buffers and omits custom
window callbacks. The new fixture reads the actual framebuffer once after the
owned popup paints; this readback exists only in the test, never production.


## Popup glass over composed UI — 2026-11-09

A floating popup reads the composed window immediately before its sheet is drawn.
An embedded popup reads its host after the controls below it are painted. For a
nested menu, the parent’s artwork and queued text are submitted first, so a
child can refract the parent. Native floating menus drawn later by Blender stay
on top. Each sheet uses a padded, reduced-resolution Gaussian blur and a
brighter directional rim. The rim needs no additional render target.

The admitted Metal and Windows Vulkan bridges can copy the relevant rectangle.
OpenGL and older bridges use the existing framebuffer blit with one reusable
full-size scratch target per host. A stable underlay reuses its blurred crop;
uncertain or animated lower content refreshes on host redraw. No CPU pixel read
is used in production. The existing viewport fallback is distinguishable from a
composited capture. The optional add-on-wide `popup_tint` remains independent of
sampling, blur and refraction.

[Matched captures and test results](design/qa/popup-composition-v1/index.html).
To replay the pixels on a Windows machine with an admitted Blender build, run
from the BUI checkout in PowerShell:

```powershell
foreach ($backend in 'vulkan', 'opengl') {
    python tools/run_blender_tests.py --windowed --blender 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --gpu-backend $backend --fixture tests/blender_popup_glass_composition.py --output "build/popup-glass-$backend"
    if ($LASTEXITCODE -ne 0) { throw "$backend popup glass failed" }
}
```


Embedded Canvas popups also use the admitted window compositor. The opener's
scroll clip still determines which controls are interactive; only transient
sheets use the wider window bounds. The popup retains its invoking Blender
context even when the pointer moves over another editor. A lower region that
redraws behind the popup invalidates its glass; closing the popup removes its
draw callbacks. A nested text flush preserves the enclosing font motion state,
so labels follow the opening sheet. [Window-level input and motion checks](design/qa/window-menu-motion-v1/index.html).
