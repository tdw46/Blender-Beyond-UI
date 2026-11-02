# Add Beyond UI to an add-on

## Copy once, add one line

From a checkout or source archive of this repository:

```sh
python tools/vendor.py /path/to/my_addon/_vendor
```

At the bottom of the add-on's `__init__.py`, **after** its existing registration
functions and **before** any `if __name__ == "__main__": register()` guard:

```python
from ._vendor.beyond_ui import integrate; integrate(globals())
```

That's the integration line. Keep your normal `bpy.types.Panel`, `Menu`, `UIList`,
`Operator`, properties, `poll()`, `bl_parent_id` and `self.layout` code. Keep
registering them with your existing functions. No panel-base replacement and no
`auto_load.py` dependency. See the complete [example](../examples/single_line.py).

The hook works after manual registration, imported/aliased `register_class`,
`bpy.utils.register_classes_factory`, or a loader called by your registration
function. It discovers registered panels whose Python modules belong to your
package, then adapts their draw content in place. Class identities and panel IDs
stay unchanged. Other add-ons' classes and global `bpy.utils` are not patched.

An add-on distributed as one `.py` file must first become a package directory to
carry its vendored dependency. A loader that recursively imports dependencies
must exclude `_vendor`; the integration does not rewrite an unknown loader.
Classes registered later, outside the wrapped `register()`, are not auto-discovered.

## Explicit migration compatibility

For a consumer with unsupported panel bodies or direct operator dialogs:

```python
from ._vendor.beyond_ui import integrate; integrate(globals(), native_fallback=True)
```

This opt-in keeps those surfaces native when the adapter raises `UnsupportedControl`.
It labels native panel bodies and reports the reason in
`__beyond_ui_integration__.status` (`host.native_fallbacks` / `popups.native_fallbacks`).
Embedded panel bodies remain strict by default. Popup openers have a separate
recovery policy below; native recovery never counts as custom control parity.

The one-line integration initializes local, package-owned PropertyGroup lists
with persistent `_beyond_ui_row_id` metadata. Initialization is deferred outside
native panel drawing; dialog/popover preparation runs after authoring and before
opening. IDs survive reorder and save/load. Duplicate tokens are regenerated for
all ambiguous rows, revoking old actions. No repeating timer or per-draw full-list
scan is added. The IDs remain when the integration is disabled.

For foreign/read-only data or an existing identity schema, pass
`layout_options={"list_identity": resolver}`. The callback receives
`(collection_owner, property_name, item)` and returns a unique stable key.
Supplying `None` explicitly opts out of automatic IDs and leaves PropertyGroup
lists unsupported. Low-level `Layout` users still supply their own resolver.
Do not use indices or RNA storage pointers as identities.

## Optional consumer data hooks

For popovers whose original draw code creates data or starts timers, move those
operations into a static `Panel.beyond_ui_prepare(context)` method. It runs on
open, outside draw. An optional static
`Panel.beyond_ui_changed(context, before, after)` runs before the host's undo
commit; return `True` only when the body needs rebuilding (for example, an enum
reveals another curve). Point edits can return `False` to retain motion and layout.
Context pointers are preserved for both hooks. Ordinary `draw()` stays read-only;
use `layout.is_custom` to distinguish the custom path from a native fallback.
These product-specific data hooks do not add another library setup line.

`template_curve_mapping(..., brush=True)` uses the shared custom curve engine,
point handles, Clip toggle and Extend enum. The consumer's preset operators keep
their brush context. Blender 4.3+ excludes Brush IDs from global undo snapshots:
consumers requiring brush undo must store/replay their curve state through their
own undo policy. The library does not install a scene journal or product handler.
See [brush behavior and limits](BRUSH_CURVES.md) and the
[CamKeys qualification](CAMKEYS_MIGRATION.md).

## Dynamic panels and lifecycle

For the one-line integration, existing `draw()` callbacks run at Blender's normal
layout-draw cadence. A bounded command recorder rebuilds the custom canvas only
when the authored layout changes. Conditional rows, labels, enabled states and
operator arguments therefore update without adding `refresh()` calls. Bound
property values remain live. GPU painting does not run authoring callbacks.
Unchanged command streams retain controls, geometry and animation state.

The integration owns automatic input startup, per-panel/window/region canvases,
shortcuts, undo/load invalidation, finite animations and teardown. There is no
idle discovery/polling loop. Newly opened windows show **Enable Panel Input** until
input is enabled there. Ordinary property edits get an undo boundary; operators
retain their own `UNDO` policy.

On unregister, custom hosts stop and original draw methods are restored before
your original unregister function runs. Repeated helper registration/teardown is
idempotent. Disable the add-on before reloading its modules. Importing/installing
the hook itself creates no Blender classes, timers, native loads or scene edits.

## Controls and styling

Use ordinary layout calls, for example:

```python
layout.label(text="Settings", icon="SETTINGS")
layout.prop(settings, "enabled")
layout.prop(settings, "strength", slider=True)
layout.prop(settings, "name")
layout.prop(settings, "mode")
layout.prop(settings, "target")
row = layout.row(align=True)
row.operator("my_addon.apply", text="Apply")
row.operator("my_addon.reset", text="Reset")
layout.menu("MYADDON_MT_actions")
layout.popover(panel="MYADDON_PT_options")
```

Supported content uses the existing BVT liquid glass, shared squash/stretch,
Blender theme roles, macOS field/menu styling and owner-aware right-click paths.
The integration does not introduce a different skin or animation implementation.
Registered menus, UILists and popover panels reached through supported custom
Layout calls use their existing drawing adapters.

## Direct dialogs and menus

The same integration line now routes these calls made by your owned operators'
`invoke()` / `execute()` callbacks:

```python
return context.window_manager.invoke_props_dialog(self, width=340)
context.window_manager.popup_menu(draw_callback, title="Actions", icon="INFO")
bpy.ops.wm.call_menu(name="MYADDON_MT_actions")
bpy.ops.wm.call_menu_pie(name="MYADDON_MT_pie")
```

The hook also adapts `invoke_popup(self, width=...)` (properties only, never
executes), `invoke_confirm(self, event, ...)` (message/action, no properties),
`invoke_search_popup(self)` (searches the enum named by `bl_property`) and
`popup_menu_pie(event, draw_callback, title=..., icon=...)`. Search retains its
native `None` return value; your `invoke()` still returns `{'RUNNING_MODAL'}`.
Selecting a result executes the original instance once, including when choosing
the current enum value. Search rows expose the exact property's context menu.
Callback pie titles occupy the center, not a directional option slot.

On qualified 3D View and Properties hosts, these open custom floating surfaces.
The dialog keeps the **actual operator instance** from `invoke()` through
`execute()`: edited RNA properties and transient Python attributes survive.
Confirmation executes once; Escape/outside dismissal cancels; native operator
undo remains in charge. Committed property changes call `Operator.check()` and
rebuild conditional controls when it returns true. Right-click targets the exact
operator property; unavailable persistent-path/animation actions stay disabled.

Direct menus reuse the registered menu/pie engine. Callback menus retain their
title/icon and custom rows. Popups use the existing glass producer, retained
backdrop, typography, theming, bounded motion and context routing. They preserve
the invoking region's context even when drawn over the editor's main region.

This is package-scoped: existing modal classes are patched in place, preserving
their registered RNA, running instances and consumer timers. Classes needing a
new modal callback are re-registered; macro dependencies and nonmodal ancestors
of registered modal classes remain protected. Original methods are restored on
teardown. See [operator lifecycle safety](OPERATOR_LIFECYCLE.md). The hook
passes a context facade and temporarily rebinds `bpy`/`ops`/`context` aliases in
the current owned callback's globals, restoring them in `finally`. It does **not**
modify the shared Blender modules or WindowManager type. Foreign menus continue
to use their native route. Code that strictly checks facade/RNA object types,
imports `bpy` inside the callback, or opens menus indirectly through another
module may need an explicit adapter.

Host capability or custom popup-construction failures preserve the native route
and are recorded in `status["popups"]["native_fallbacks"]` with `custom=False`.
Registered panel/menu buttons likewise recover through native `call_panel` or
`call_menu` after revalidating their exact owners, context and poll. Their records
are in `status["host"]["popup_fallbacks"]` (and `canvas.popup_fallbacks` for low-level
hosts). Set `canvas.popup_native_fallback = False` for strict opener diagnostics.
Unsupported custom headers retain a recoverable opener. Failed custom surfaces
are discarded before recovery; no operator action is retried. This degraded
behavior is explicitly recorded and does not count as custom parity. Failures
inside the original native UI itself cannot be repaired by switching renderers.

## Existing menu shortcuts

Keep your existing keymap setup, including direct `wm.call_menu` and
`wm.call_menu_pie` items. During registration, the hook routes items in the add-on
and user keyconfigs only when the named registered menu belongs to your package.
It keeps the same keymap item, event chord, order and enabled state. Removal
restores the native menu route and preserves shortcut edits made while integrated.
Saved owner-local routes are recognized on registration. Menu-only packages work
without declaring a Panel or Operator.

For shortcuts installed after registration, call
`__beyond_ui_integration__.refresh()` once after creating them. There is no keymap
polling loop. `status['popups']['keymap_routes']` reports tracked route records.

Blender 5.1.2/5.2.2 tests verify RNA event matching and invoke the matched route
through a test modal operator. Ordinary top-level shortcuts did not dispatch in
the inactive no-focus fixture (an unmodified native Select All probe also failed
to dispatch). Foreground hotkey dispatch still needs consumer/manual QA; no
activation workaround was used.

## Check conversion status

From the add-on module:

```python
print(__beyond_ui_integration__.status)
```

Status lists adopted panels, panels outside the embedded-host scope, detected
menu/dialog routes, supported `routed_routes`, host availability, native fallbacks
and per-panel draw errors. The historical `native_routes` field is the static
call-site inventory; it does not mean every listed route remains native. Native
route discovery is a bounded hint from registered class callbacks; indirect
helper calls and arbitrary dynamic Python cannot be exhaustively analyzed.
Unsupported drawing revokes the previous interactive content and displays a
specific error. Correcting that layout branch lets the panel recover on redraw.

**Current limits:**

- Registered macro child operators retain their original RNA and callbacks to
  avoid dangling native pointers. Their popup calls keep native routing; these
  dependencies and limits are explicit in integration status. See
  [macro lifecycle safety](MACRO_LIFECYCLE.md). Other owned operators still route
  through custom dialogs and menus.
- Embedded bodies support `VIEW_3D/UI` and `PROPERTIES/WINDOW`. Native panel
  headers (`draw_header`) and Blender's outer panel shell remain native.
- Auto-executing `invoke_props_popup` keeps its native redo-stack behavior and
  records an explicit fallback; rerunning execute without undo replacement would
  be incorrect. `invoke_popup(auto_keymap=True)` likewise reports a native fallback
  for automatic keymap hints. These are not custom parity.
- Search popups currently qualify single-choice enums. Flag-enum search uses a
  recorded native fallback until its selection semantics are qualified.
- Calls outside owned invoke/execute callbacks, arbitrary modal callback chains
  and helper-module imports are not automatically intercepted. Keymap routing
  covers existing items plus explicit refresh, not unregistered menu names or
  modal keymaps.
- Floating hosts currently support 3D View and Properties editors. Other editor
  hosts preserve native behavior with a recorded availability reason.
- Only implemented `Layout` methods and modes convert. Advanced curve modes
  including `brush=True`, and other ledger gaps, still need dedicated work.
- Draw callbacks receive a layout proxy, not an RNA Panel instance. Ordinary
  Python helper methods and metadata work; `super()`/strict instance checks or
  helpers requiring an actual RNA panel need an explicit adapter.
- Draw code must obey Blender's read-only drawing contract. No timer-driven
  heartbeat is added to preserve an add-on's draw-time business logic.
- Embedded custom rendering requires admitted exact-build native adapters.
  Integration execution is verified on macOS arm64 Blender **5.1.2/5.2.2**.
  This is not qualification for every 4.2+ build, Windows or Linux. On unavailable
  hosts, adoption shows the availability reason and preserves the original native
  draw as an explicit degraded fallback; it is not custom parity.

See [validation](VALIDATION.md), [context-action limits](CORE_CONTEXT_AUDIT.md),
and the [custom parity ledger](CUSTOM_PARITY.json). A successful one-line install
is not a claim that every control, native popup or generated reference is complete.

## Optional configuration

The hook accepts the same options as `AddonUI` in that single call:

```python
from ._vendor.beyond_ui import integrate; ui = integrate(globals(), commit=my_commit)
```

`commit(before, after)` supplies your transaction policy. `context_menu=provider`
uses `Canvas.context_provider`; include `default_entries(target, context)` when
adding custom actions. `animation=AnimationSettings(...)` controls source motion.
`layout_options` accepts `resolve`, `source`, `pointer_sources`, `id_actions` and
`list_identity`. Configuration belongs to this add-on's integration only.

After registration, `ui.ui.animation.enabled` and `.strength` update motion live;
`ui.refresh()` explicitly invalidates unusual external layout dependencies.
Disabling motion does not disable glass. Colors come from Blender's active theme.

## Explicit lifecycle alternative

For a new add-on or an existing custom host, the lower-level APIs remain available:

```python
from ._vendor.beyond_ui import AddonUI
ui = AddonUI(__package__)

def register():
    ui.register(FirstPanel, SecondPanel)

def unregister():
    ui.unregister()
```

With **this alternative**, register panels only through `ui`, after your data and
operators; exclude them from other registration. Its draw schemas are retained:
call `ui.refresh()` after conditional structure changes, or supply a cheap static
`cache_key(context)` on each definition. This differs from automatic recording in
`integrate(globals())`. See [the explicit example](../examples/panels.py).
`Layout`, `Canvas`, `PanelHost` and `ShortcutRegistry` also remain independently
usable. Do not combine both registration approaches for the same panels.

## Updating the vendored copy

The vendor tool copies fonts, shaders, adapters and licenses and writes exact file
hashes in `vendor-record.json`. Git provenance is included when available; source
archives leave it unset. Re-run the command with `--replace` to update an unchanged
recorded copy. Locally modified copies are refused. Keep the complete package,
license and notice; stripping assets/ABI manifests disables capabilities.

## Reproduce the integration tests

```sh
uv run python tools/prepare_integration_fixture.py build/single-line/consumers
BEYOND_UI_CONSUMER_ROOT="$PWD/build/single-line/consumers" \
  uv run python tools/run_blender_tests.py --windowed --macos-noactivate \
  --blender '/Applications/Blender 5.1.2.app/Contents/MacOS/Blender' \
  --blender '/Applications/Blender 5.2.2.app/Contents/MacOS/Blender' \
  --fixture tests/blender_single_line.py --output build/single-line/check
```

The fixture uses three independently vendored consumers, actual simulated Blender
events, conditional rebuilds, unchanged-canvas retention, owner menus, explicit
unsupported-mode recovery, original-method restoration and isolated teardown.


Direct-dialog/menu reproduction (same runner flags/builds as above):

```sh
uv run python tools/prepare_popup_fixture.py build/direct-popups/consumers
BEYOND_UI_CONSUMER_ROOT="$PWD/build/direct-popups/consumers" \
  uv run python tools/run_blender_tests.py --windowed --macos-noactivate \
  --blender '/Applications/Blender 5.2.2.app/Contents/MacOS/Blender' \
  --fixture tests/blender_direct_popups.py --output build/direct-popups/check
```

[Direct popup runtime evidence](design/qa/direct-popups-v1/runtime.json).

Use `tests/blender_popup_variants.py` with the same prepared consumer/runner to
check property-only, confirmation, search, callback pie and keymap routes.
[Popup-variant evidence and qualification limits](design/qa/popup-variants-v1/runtime.json).
These are execution/GPU-resource checks, not new visual-reference acceptance.


### Live labels and visible list rows

Property and operator hover descriptions come from their native RNA metadata,
including enum-choice help and Python operator description callbacks. Disabled
controls retain help; Blender's `show_tooltips` preference is honored. Low-level
controls can provide `tooltip="Help"` or a context-taking callable. Descriptions
are resolved on hover, never in GPU paint or an idle polling loop. Shared menu
glass, theme roles and finite reveal motion render the tooltip in panel, popup
and active list-row hosts. Removed owners, edits, scrolling, dismissal and parking
cancel pending help. Python description callbacks that require native-only
`OperatorProperties` operations fall back to the operator's RNA description.

Adopted native panel redraws re-evaluate visible UIList callbacks. Literal
`layout.label(text=...)` values are patched into retained controls when only text
changes; unchanged rows skip layout. Changed row structure rebuilds that row, and
list membership/active-owner changes still invalidate the owning authoring tape.
This requires no CamKeys-specific bindings or consumer edits. Ordinary bound RNA
properties already read their current values. No polling timer or GPU-paint
callback executes consumer authoring; the consumer retains responsibility for
requesting its normal native region redraw when external state changes.

Fully offscreen embedded panels reserve their cached height without running the
panel body, custom cache-key callback, list callbacks, value refresh or layout.
Native clipping detects their return; one deferred redraw refreshes ownership,
list membership/filtering and displayed values before controls become interactive.
There is no polling timer. Scene/object changes and explicit invalidation still
revoke old owners. Structural changes while hidden take effect on return, so their
reserved height stays stable while scrolling. This is automatic for one-line
integration and `AddonUI`; low-level `PanelHost` consumers can call `defer_draw()`
before authoring and return early when it returns `True`.
See the [offscreen regression and timing evidence](design/qa/panel-offscreen-v1/report.json).

Owned `bpy.ops.wm.call_panel(name=...)` calls inside routed invoke/execute callbacks
now open custom panel popovers. Unsupported `keep_open=True` remains an observable
native fallback. Floating hosts avoid overlapping sidebars, toolbars and headers,
and use the invoking region for property/context guards while painting in the
viewport. See [current consumer evidence](design/qa/camkeys-live-panels-v1/index.html).
# Developer help and context actions

Hover help retains the native RNA/operator description. Enabling Blender's
Developer Extras or Python Tooltips adds Python identifiers and exact property
paths; disabling Show Tooltips hides the entire tooltip. These details are resolved
on hover, not in the paint loop. Menu fields use the same lazy help path.

Bound properties retain their standard context actions even when a consumer adds
its own context-menu rows. Copy Data Path and Copy Full Data Path are available
independently of Developer Extras, including individual array components.
Developer Extras adds applicable Python reference/source actions and Copy Python
Command for operators and registered menu/popover openers. Availability still
depends on the exact owner, current context and admitted native capabilities;
unavailable actions are not fabricated against an unrelated native button.
