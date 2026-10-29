# Shared animation policy

Custom controls use the Effect Layers spring equations already extracted into
`gpu/style.py`. Animation affects presentation, never logical layout, hit bounds,
RNA values or undo. The default amplitude is the source amplitude, except wide numeric fields as
described below. Importing the
library installs no timers or callbacks.

```python
from .vendor.beyond_ui import AnimationSettings, animation_defaults, Canvas
from .vendor.beyond_ui.hosts.panel import PanelHost

# Shared defaults within this vendored library instance.
animation_defaults.enabled = True
animation_defaults.strength = 1.0

host = PanelHost(__package__, animation=AnimationSettings(strength=0.75))
canvas = Canvas()  # inherits host policy when attached
button = canvas.button(
    "refresh", "Refresh", refresh,
    animation=AnimationSettings(strength=1.25),
)

# Live backend changes apply without reloading the extension.
button.motion.settings.strength = 0.5
host.animation.enabled = False
```

A control inherits strength from its canvas, host and library defaults, in that
order, unless it overrides it. Any ancestor `enabled=False` or `strength=0`
disables descendants. `None` strength means inherit. Negative/nonfinite strengths
are rejected; extreme strengths are bounded so deformation cannot become
singular. Changing a setting clears existing springs and requests a final resting
frame; it never leaves a partially deformed control frozen.

For widgets created directly, use `widget.motion.settings.enabled` and
`widget.motion.settings.strength`. The `Canvas.widget(..., animation=...)` option
also accepts an `AnimationSettings` instance. All input is routed automatically
when the widget belongs to a Canvas. A standalone painter host must deliver
`widget.motion.input(event, logical_x, logical_y)` before `widget.event(...)`,
call `advance()` while active, and clear it on hide/teardown.

## Host revision notifications

Read-only controls never consume clicks to manufacture motion. After a value
change or explicit reveal, notify the retained Canvas from the host's operator,
update callback or lifecycle event:

```python
progress.factor = new_factor
canvas.notify_changed("progress")
# Also request the host's ordinary redraw for the changed value.
```

Do not call this on every draw. Changes to read-only values are not discovered by
polling RNA or scanning data in a draw callback. Initial reveal is likewise an
explicit host notification, not a timer started from Panel.draw.

`PanelHost` owns one finite timer while visible controls animate. Hover entry
excites a spring once; remaining hovered does not restart it. Rapid input
retargets from the current deformation, with a bounded number of tracks. The
last tick redraws exact rest, then unregisters. Hidden/clipped controls, owner
invalidation and teardown clear motion. Settings changes can require one final
redraw; disabled and settled UI has no animation polling loop.

## Current integration and remaining parity

- Basic controls use shared entry/press/drag/release springs. Toggle knobs use
  the source's reciprocal-axis shape, 0.36-second eased travel and longer switch
  settling time. Travel retargets from the current position; backend disable
  clears both travel and shape. See [scalar QA](design/qa/scalar-layout-v1/index.html).
- Compound fields/tabs, palette swatches, curve points, ramp stops, color handles,
  picker rows and compact enum menus use retained chrome deformation.
- Color popovers use reveal motion; read-only matrices, progress and sockets can
  use explicit reveal/change notifications.
- Basic control text stays stable under chrome hover motion, as in the source
  hover-lens path. Menu labels and shortcuts follow their menu/row transforms.
  Primitive geometry and glass backdrop ownership remain retained.

This is **not complete source animation parity**. The source's full highlight
wipe, elastic tab travel, every toolbar sub-action, focus/
keyboard state and all popup/reveal combinations still require dedicated
integration and visual references. New surfaces must meet AGENTS.md's motion
rule; none of these gaps may be silently marked complete.

## Evidence

[Actual animation recording](design/qa/next-v1/motion.gif) uses the production
Canvas/painters, deterministic 30 fps fixture time, and a neutral backdrop. It
covers eight cards, entry/press/drag/release and read-only change pulses. It does
not substitute for live input latency or exact motion-reference acceptance.
Blender 5.1.2 and 5.2.2 Metal captures verify identical pixels at rest, after
settling and after disabling; retained line batches do not change. Windowed
modal tests verify timer termination while hovered and cleanup on invalidation.
See [validation](VALIDATION.md) for scope and outstanding platform checks.

## Wide numeric fields

Numeric controls occupying at least 75% of the usable panel width multiply the
otherwise-resolved strength by **0.15**, per Tyler's motion correction. Compact
numeric controls and menus retain their existing strength. Spring timing,
area-preserving deformation, resting pixels and logical hit targets are unchanged.

```python
canvas.wide_numeric_motion_scale = 0.15  # Set before layout or change live.
```

The multiplier accepts finite nonnegative values. Global/host disable still wins;
zero stops motion. Updates clear active tracks and request the final resting
frame without reloading, relayout, or another glass capture. Classification is
updated when layout width changes, outside steady-state painting. See the
[original/current motion comparison](design/qa/numeric-props-v2/index.html).

## Menu text follows every opening transform

Every menu option participates in the shared opening/reveal transform, including
labels, shortcut hints, disabled rows, checkmarks, submenu arrows and inline
values. Hover motion remains separate from the whole-menu reveal. Logical targets
and keyboard selection never move with the rendered transform.

During finite menu motion, the privately owned BLF font uses public zero-angle
`ROTATION` mode to submit glyphs while the corresponding GPU matrix is still
active. A non-rendering space first drains earlier text at the incoming matrix.
This avoids deferred native text batches painting the final rows after the menu
matrix has been popped. The flag is reset in `finally`; settled menus retain
the original batching path. There is no GPU wait, framebuffer readback, extra
texture, glyph-size churn, offscreen, glass pass or persistent timer.

The regression fixture deliberately enables Blender's enclosing native text
batch and compares every animation frame against an unbatched capture. These
test-only native calls require exact build/source/executable admission; production
uses public `blf.rotation`/`enable`/`disable` APIs only. See
[menu motion QA v6](design/qa/context-menu-v6/index.html).
