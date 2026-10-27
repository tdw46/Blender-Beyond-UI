# Integration

Copy the entire `beyond_ui` package into an extension-local `vendor` directory.
Use relative imports. Do not put the library on global sys.path or install a
second top-level copy. Exclude the vendor directory from class auto-discovery.
Preserve `LICENSE` and `NOTICE`; pin the repository commit alongside the copy.

The library does not register an extension of its own. Your extension owns its
panels, operators, preferences, handlers and translations. A supported extension
can use the pure helpers without importing the GPU/native integration.

## Custom authoring

```python
from .vendor.beyond_ui import Layout

ui = Layout(context=context, commit=on_committed_edit)
ui.label(text="Settings")
ui.prop(settings, "enabled")
ui.prop(settings, "strength", slider=True)
ui.template_color_picker(settings, "color")
canvas = ui.canvas
```

Build a schema once, retaining a Canvas for each window/area/region. Rebuild on
structural changes; values stay in the host's authoritative model. For long-lived
RNA bindings provide `resolve(data)` returning a stable-ID reacquisition callable.
Do not search mutable names or collection indices to reinterpret stale controls.
Invalidate canvases before undo/load and rebuild them afterwards. The `commit`
callback owns one undo boundary and relevant redraw; the library never invents
undo state, silently saves a file, or changes unrelated scene data.

Custom API support is intentionally explicit. `ui.supports(name)` reports an
implemented authoring method, not that every mode or visual state is accepted.
Unimplemented calls raise `UnsupportedControl`. Consult the parity ledger before
integrating specialized controls. The present editors have known incomplete
features, listed in the ledger.

## Embedded N-panel host

```python
from .vendor.beyond_ui.hosts.panel import PanelHost

host = PanelHost(__package__)
host.start()  # during an explicit host lifecycle, not module import
# In your owned Panel.draw(context):
host.draw(self.layout, context, canvas)
# In your window modal:
consumed = host.event(context, event)
# Before undo/load and when unregistering:
host.invalidate()
host.close()
```

Start the input modal explicitly or from a guarded lifecycle callback. Do not
start timers/operators from draw. The example exposes an Enable Custom UI Input
button and preserves its row height after activation.

`draw()` returns False when the embedded host is unavailable. The host may
explicitly offer a separately labeled native compatibility UI, or display the
unavailability reason. It must never call native widgets a custom implementation.
Only one canvas is supported in an exclusively owned panel block; Blender's
private extra-draw callback is block-owned, not independent for arbitrary widgets.

The bundled macOS adapter admits only recorded exact hashes. Windows adapter
source is preserved, but there is no validated Windows or Linux binary in this
repository. `tools/build_bridge.py` is an explicit developer build step, never a
startup action. Binaries are checked against their package source and manifest.

Glass is optional: pass `backdrop_revision=lambda context: meaningful_revision`
to PanelHost. This borrows the completed host UI framebuffer. The default stays
on the readable tint fallback; do not claim the fallback is blurred glass.
`gpu.glass.draw(..., viewport_present=callback)` lets an extension supply its
completed viewport presentation without coupling the library to its renderer.

## Explicit native compatibility

```python
from .vendor.beyond_ui import NativeLayout
ui = NativeLayout(self.layout)
ui.template_curve_mapping(node, "mapping")
```

This preserves native behavior and full installed API access. It is not part of
the custom parity acceptance count. Retain a `NativeLayout` only during the
current Blender draw callback.

## Shared typography and reference skin

`PanelHost` owns bundled Inter Regular/SemiBold handles. Use `canvas.title(key,
text)` or `Layout.title(text=...)` for headings. Labels returned inside
`Layout.panel()` and `panel_prop()` headers, plus row/column `heading` labels,
receive the title role automatically. A custom host should create
`beyond_ui.gpu.typography.Fonts()` once, pass it as `font`, and call `close()` at
teardown. Plain integer font handles remain supported but cannot supply a
separate semibold face.

The default shared palette is the explicit reference skin, including transparent
fields and consistent blue highlights. `style.native_theme_palette(preferences)`
is an explicit opt-in utility; native Blender theme colors do not override the
reference skin. Compound widgets include their card/header; do not wrap them in
a second painted header. Canvas derives their height from the authored aspect
ratio unless an explicit height is supplied. Hosts provide a backdrop revision
to `PanelHost` to reuse the source glass pipeline; otherwise translucent tinting
is used. `ColorRamp(linear=True)` converts scene-linear stop colors to display
space consistently for the gradient, handles and swatch. Set `linear=False` only
for display-space bindings.

## Animation configuration

Use `AnimationSettings` on the host, canvas or individual control for live
`enabled` and `strength` settings. [The animation guide](ANIMATION.md) documents
inheritance, read-only change notifications, finite redraw ownership and current
coverage gaps. The library does not register settings in the consuming extension;
bind these Python properties to your own backend/preferences.
