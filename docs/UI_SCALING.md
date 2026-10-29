# Consistent control scale

All implemented Canvas control families now use logical host units. Extra panel
width no longer magnifies compound controls or their popovers. Blender's host DPI
transform scales the entire UI once, including surrounding fields and menus.

The source BVT type roles are 11-unit body text and 12-unit section titles. The
current compound cards were authored on 630-unit artboards with 22-unit body text;
those artboard coordinates are not host pixels. Canvas now converts them to the
host body size (normally 0.5×). Headers use the same 12-unit title size and retained
title font as surrounding sections. Authoring-space hit geometry is unchanged:
the same uniform transform maps painting and input.

| Surface | Default logical size / typography |
| --- | --- |
| Normal buttons, fields, toggles, decorators, enums | 32-high row; 11 body, 12 section title |
| Pointer, search, standalone and palette color popovers | 315 × 236; 11 body, 12 title; source strong glass |
| Embedded picker, color, curve and ramp cards | Up to 315 × 236; matching text scale |
| Palette and matrix cards | Up to 315 × 218; matching text scale |
| Framed progress bar/ring | Up to 315 × 195; matching captions |
| Compact progress bar/ring | Up to 293.3 × 33 / 146.7; 11-unit captions |
| Node socket | 20 × 20 slot, 12-unit colored dot |
| Context menus and tooltips | Existing source 11-unit body; menu rows 23 high |

Tab captions and small component labels retain their roughly 9.5–12-unit
hierarchy. Large progress percentages are data readouts, not panel headings.
Graphs, ramps, swatches and previews retain their useful content area; matching
UI scale does not mean every control must have the same overall dimensions.

## Integration

`Widget.design_font_size` declares the body font size used by a widget's authored
geometry. `Widget.dimensions(host_font_size, available_width, available_height)`
computes its preferred logical dimensions, preserving aspect ratio and shrinking
only to fit the available bounds. Supplied cards declare 22; compact progress
uses 12; ordinary/custom Widget geometry defaults to 11. A custom widget should
set this value to its actual authored body font size.

`Canvas.open_widget(widget, owner, clip)` is the shared compound-popover route.
It centers within the visible clip, retains the exact owner, and uses strong
glass. Palette editing uses the most recent input clip through the same route.
Open managed popovers reflow on clip changes before input hit testing. Neither
sizing nor resize handling captures a backdrop or creates a new blur pass.

Embedded widgets retain their preferred width instead of stretching to fill a
wide row. Explicit width/height options act as maximum bounds; they do not distort
widgets. Surrounding rows keep their existing flexible layout. Narrow/short
viewports can require uniform shrink-to-fit; this is a bounded fallback, not
proof of arbitrary tiny-viewport readability. The validated mixed-control range
is 360–960 logical panel width, plus constrained-bound geometry checks.

Standalone `widget.paint(rect, ...)` is a low-level API: its caller still owns the
rect and transform. Use Canvas or `dimensions()` for scale-consistent embedding.
After changing a Canvas Theme in a host, invalidate/rebuild its layout as usual.
Active Blender theme colors remain a separate, cached palette concern.

## Reference correction and evidence

Tyler's 2026-10-29 correction explicitly supersedes the previous width-driven
presentation and oversized compound headings. Existing generated references and
historical QA galleries remain immutable; they do not certify the corrected
screen scale. The new [scale audit](design/qa/ui-scale-v1/index.html) provides
actual Blender before/after output, a corrected popover GIF, and every implemented
control family at 1×, 1.5× and 2× physical rendering scales. This is rendered-scale
evidence, not qualification of every OS display configuration or full API parity.
Exact generated-reference and final visual acceptance remain open for Tyler.
