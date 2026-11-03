# Responsive custom panels

`PanelHost` enables the shared panel layout policy automatically, including panels
adopted by the single-line integration. No consumer labels or property names are
special-cased. Other canvases can opt in with `canvas.panel_layout = True` before
arranging; low-level hosts may retain literal geometry with
`PanelHost(owner, panel_layout=False)`.

The policy in `panel_metrics.py` / `flow.py` runs only on layout invalidation:

- A leading label in a box, or a label after a divider introducing controls,
  becomes a bold section heading. Long headings wrap. Inline unit labels and
  icon-bearing informational labels remain body text. A custom low-level label
  can set `control.options['section_heading'] = False` to opt out.
- Adjacent panel controls use a four-unit gutter. Compact switches, icon actions
  and unit suffixes retain their intrinsic widths. Percentage splits honor those
  minimums; a split that cannot fit stacks its authored groups in order.
- Fields share a label column where space permits, otherwise put the full label
  above the entry. Accessories align to the value baseline; list toolbars stay at
  the top. Explicit author widths/heights and degenerate 0/1 split semantics remain.
- An ordinary Boolean, including an icon-only `toggle=True` property, remains a
  full-size BVT switch. Unembossed Boolean actions retain the earlier centered
  button presentation. All existing bindings, callbacks and context owners survive.
- Moderate integral values such as 250 display as digits instead of `2.5e+02`.
  This changes presentation only, not precision, parsing or the stored value.

The production host keeps theme extraction, shared glass and source animation.
No per-frame measurement, texture, blur, font or binding work was added. Geometry
is reused until invalidation; menu and list-child layout policies are separate.

See [Forced Perspective review](design/qa/forced-perspective-v2/index.html) for
actual authored CamKeys controls at widths 260/286/360/480 and scales 1/1.5/2,
native panel captures, centered-icon raster checks and owner-menu checks. Reference
v2 adds the requested slider and removes invented numeric dropdown arrows.
Original source glyphs, theme/backdrop and author-supplied controls still differ
from the concept; exact visual acceptance remains a separate gate. Windows and
Blender 4.2 runtime validation remain outstanding.

## Compact metrics and responsive grid rules

Panel fields are 26 logical units tall; icon buttons 24; list tools 22 with
four-unit gutters. Text buttons start at 20 units and retain authored `scale_y`
(e.g. a 1.5 primary action is 30 units). Body font size is unchanged. Panel labels,
including switches and color fields, share the same zero-inset left edge. Icons
use 14-unit artwork; source SVG transparent margins are excluded when centering
its silhouette. Icon-only buttons center the visible glyph in both axes; buttons
with text center the icon/text group. The atlas and vector bounds are retained.

This is a retained layout engine with browser-style intrinsic sizing, minimum
widths, shared columns, gutters and responsive grid rules—not a web view. Paired
fields stack their captions together. A slider caption can span its accessory row
without making the slider input itself wider; the caption retains its property
context owner. Helpers keep their intrinsic widths and align with the input row.

For panel `Layout.prop`, omitting `slider` now permits a conservative automatic
slider for floating, unitless properties with finite positive hard bounds and a
span of 10–1000. This covers bounded magnitude controls without changing integer,
unit-bearing, signed, factor or unbounded entry fields. Explicit `slider=True` or
`slider=False` always wins. Other hosts keep their prior default. Low-level hosts
can set `canvas.automatic_sliders = False` and call `canvas.invalidate()` to opt
out. Slider labels use a 26-unit band above the original BVT track, bubble and
separate number field. Stored RNA values, edit limits, actions and owners remain
unchanged.


## Native panel scroll ownership

The AddonUI input service keeps a scroll gesture with Blender's native N-panel
or Properties region once every custom host has passed it through. Moving the
pointer over a list, or scrolling a list under a stationary pointer, cannot let
that list intercept the continuing gesture. A new gesture starting on a list
still operates the list immediately.

Ownership expires after 300 ms without scroll input. Mouse movement, redraws and
zero-delta trackpad tail events do not end the gesture. Explicit clicks/keys,
deactivation, region changes, file load, undo/redo and teardown clear it. The
state is bounded, per runtime/window/region, and stores no RNA references. It
measures input arrival times with a monotonic clock, with no timer or idle polling.
Wheel and trackpad directions still use the shared scroll-delta policy.

This is a cross-platform inactivity heuristic; Blender exposes no portable
momentum-end phase used by this policy. It does not change popup routing,
renderer/backend behavior, scene evaluation or list virtualization.

Execution evidence and physical-device limits: [scroll ownership report](design/qa/scroll-ownership-v1/report.json).

At the top or bottom of a collection list, further outward scrolling bubbles to
its parent. The event that reaches the boundary is consumed by the list; the
next outward event goes to the panel, avoiding simultaneous list/panel movement.
This applies to DEFAULT/GRID viewports and COMPACT selection boundaries, including
empty or non-overflowing lists. Inward scrolling still works immediately on a new
gesture. Zero-delta input does not start a parent scroll; active edits and popups
retain their existing capture policy. See [edge handoff checks](design/qa/scroll-chaining-v1/report.json).
