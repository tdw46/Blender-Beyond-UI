# Context menus

Right-click menus share BVT's row painter, navigation, owner validation, theme
roles, liquid-glass lens and finite squash-and-stretch motion. `PanelHost` enables
shared glass by default. Menus use the stronger 0.7 blur level and untinted
refractive body; labels beneath a child page are clipped out, not allowed to
shine through the child. Unsupported graphics hosts expose a tint fallback.
That fallback does **not** satisfy liquid-glass acceptance.

## Use the RNA defaults

```python
from .vendor.beyond_ui import Canvas, Layout

canvas = Canvas(menu_commit=lambda action: host_undo_boundary(action))
ui = Layout(canvas, context=context, commit=host_property_commit)
ui.prop(context.object, "location", index=1)
```

The ordinary binding commit callback owns reset/copy-to-selected transactions.
The separate `menu_commit(action)` owns keyframe/driver undo policy. Those actions
stay disabled without that callback. Callback-only bindings expose Copy Value
when readable; they never acquire guessed reset, keyframe or data operations.
The host remains responsible for Blender registration and undo integration.

RNA defaults cover reset, component-aware copy to selected, data/full paths,
applicable insert/delete keyframes and add/remove drivers, Manual and developer
API links. Reset/copy roll back assignments if the host commit raises. Animation
callbacks run after a successful RNA operation; the host must own any larger
transaction/rollback policy. Read-only owners retain readable actions.

## Supply product actions

```python
from .vendor.beyond_ui import MenuEntry
from .vendor.beyond_ui.context_menu import default_entries

def actions(target, context):
    rows = list(default_entries(target, context))
    if target.part[:1] == ("row",):
        row_id = target.part[1]
        rows.append(MenuEntry(
            "inspect", "Inspect Item",
            action=lambda t, c: inspect_current_item(row_id, c),
            enabled=lambda t, c: item_still_exists(row_id),
            tip="Inspect this exact item.",
        ))
    return rows

canvas.context_provider = actions
# A control-specific provider overrides the canvas provider:
canvas.button("tools", "Tools", open_tools, context_menu=actions)
```

`MenuEntry` accepts `key`, `label`, `action(target, context)`, boolean/callable
`enabled`, on-demand `children(target, context)`, `icon`, `tip`, `divider`,
`shortcut`, a tuple of `Shortcut` event bindings, and boolean/callable `checked`.
Checked state is resolved on input/opening; painting never reads bound RNA. Providers are called on open,
not paint. Rows are capped at 64, nesting at three child pages, visible rows at
18. Logical hit targets never follow visual spring deformation.

`MenuTarget` identifies the exact control key and subpart, and carries `binding`,
`value`, `payload`, `valid`, `editable` and host `commit`. Compound parts distinguish
color channels (including derived HSV), curve channels/points/point fields,
ramp stops/position/color/interpolation, picker row IDs, palette swatch IDs,
matrix components and progress indicators. Pointer-picker row menus deliberately
use the hovered row, not the currently selected pointer property. Hosts supply
row-specific data actions. Generic palette sources should supply `identity(index)`;
RNA palette adapters already do. A count/color fallback cannot distinguish
reordered identical colors and is not sufficient for destructive host actions.

A widget or binding can supply `context_target(target)` to attach its own stable
owner resolver. Never resolve actions later from only the current selection or a
mutable list index. Existing RNA ramp/curve/palette adapters retain exact element
identity and fail closed after deletion/replacement/reordering where appropriate.

## Input, descriptions and lifecycle

Right-click cancels an active edit/drag first. A subsequent right-click opens the
menu. APP and Shift-F10 use the last focused control/subpart. Arrows, Home/End,
Page Up/Down, wheel and trackpad navigation are bounded to visible entries;
Enter/Right chooses and Left/Escape navigates back. Root Escape/right-click closes.
Outside wheel passes through. Outside clicks dismiss and clear focus. Removed or
hidden owners, changed scene/developer context, invalidated layouts and teardown
revoke the menu. Each host window keeps one active menu.

User keymaps are snapshotted on opening; execution rechecks target identity and
capability. Key-modifier chords track held/released keys and honor wildcard modifiers;
focus loss clears the held-key state. Disabled actions cannot execute. Public Python
`UI_MT_button_context_menu` contributions are collected on demand with explicit
`button_pointer` / `button_prop`; nested pointer contexts and operator properties
are snapshotted and revalidated. Native-button-dependent operators are disabled.
Unsupported callback surfaces are logged and isolated. String contexts cannot be
passed through Blender's public `temp_override` and require a host adapter.

Descriptions use BVT's 0.55-second dwell, honor `show_tooltips`, and stop their
one-shot callback after reveal. They use the same glass and motion resources.
Direct Canvas hosts may use `canvas.bind_context_tooltips(schedule)` and call
`menu.reveal_tip(context)` after that delay; `None` cancels the pending callback.
PanelHost supplies this scheduler and removes it on invalidation/teardown.

Global, host, canvas and per-control animation policies apply to the menu.
Disabling motion or setting zero strength leaves the resting material intact.
Glass does not depend on animation being enabled. See [animation](ANIMATION.md)
and [GPU backdrop integration](INTEGRATION.md).

## Evidence and remaining parity

[QA gallery](design/qa/context-menu-v5/index.html) includes real Blender root,
nested, tooltip, all eight compound targets, glass-versus-tint comparison and
motion. Disposable Blender 5.1.2/5.2.2 tests cover RNA transactions, selected-owner
rollback, keyframes/drivers, public nested menu contributions, stale elements,
actual window input, delayed tooltip shutdown, glass admission and teardown.
Pure tests cover clipping, bounds, disabled actions, provider exceptions and
compound target resolution. Older supported runtimes/platforms are not freshly
qualified by these tests.

## Driver clipboard, favorites, shortcuts and developer actions

The menu adapters now implement Blender's real driver clipboard, property and
operator Quick Favorites, custom keyboard capture, Edit Source and Python tooltip
text. The clipboard and Favorites adapters are experimental on **macOS arm64,
exact Blender 5.1.2 and 5.2.2 executables only**. Their admission requires the
allowlisted build, platform, adapter source hash and executable SHA256 in
[`menu-native-audit.json`](../beyond_ui/hosts/menu-native-audit.json). Unknown builds,
4.2, Windows and Linux retain explicit disabled entries. This does not raise the
library's minimum Blender version or qualify those runtimes by inference.
`PanelHost.start()` warms admission once; direct Canvas hosts can call
`beyond_ui.hosts.menu_native.api()` during their explicit initialization.
`reason()` and `PanelHost.menu_adapter_reason` expose degraded capability.

- **Copy/Paste Driver:** uses the actual Blender clipboard, including Copy as New
  Driver for an exact scalar/component. Whole-array clipboard targets are disabled.
  Read-only/non-animatable numeric inputs can be copied as driver sources. Paste
  stages on an unlinked temporary object, copies the complete FCurve through RNA,
  replaces only the requested component, and restores the previous driver if the
  host's undo callback rejects the transaction. Temporary IDs are always removed.
- **Quick Favorites:** stores exact properties/components or operators plus their
  arguments in Blender's real context menu. Add is idempotent. Opening/polling the
  menu never creates a favorite or changes preferences. Context-relative property
  paths must resolve the exact clicked owner; unrelated/unlinked owners are
  disabled. Operator pointer overrides cannot be persisted and remain disabled.
  Add/Remove resolves the exact current item again when clicked, including
  inherited Topbar/Properties favorites. Native item pointers are never retained
  in menu state. Operator buttons expose a Quick Favorites submenu; opening that
  submenu queries through a temporary typed property container, always released.
  Queries leave preferences clean; changes mark them dirty without saving.
- **Shortcuts:** Assign opens a liquid-glass mode chooser. Arrows and Enter
  select Keyboard, Mouse/NDOF or Key modifier chord before capture is armed. Escape/right-click cancels; modifier-only input waits. Conflicting
  chords in the chosen keymap, global UI/Screen/Window maps and applicable
  View3D/mode maps are rejected without removing somebody else's binding. Existing exact operator/argument matches offer Change and Remove;
  concurrent item/context changes revoke the action. Edits use public user keymaps
  and mark preferences dirty without saving them. The admitted helper chooses
  Blender's native keymap; `context_shortcuts.Action(..., keymap="Window")` also
  supports an explicit host-selected public keymap without native guessing.
  Explicit alternate capture rows support mouse/NDOF buttons and a held ordinary
  key plus a second key. Escape/right-click always cancel; these two inputs cannot
  be assigned through this capture UI. Left-click can be assigned in the mouse
  capture instruction/body area. Cancel returns to the mode chooser; another
  Escape returns to the originating menu. Navigation keys remain assignable once
  capture is armed. Mode selection adds no extra nesting beyond the capture page.
  Hosts can supply `conflict_keymaps(context, selected_keymap)` to `Action` or
  `ShortcutRegistry` to include their editor/modal maps. This is bounded to 64
  additional maps and cannot bypass the built-in checks. Blender does not expose
  every active C modal handler through public RNA; host-owned modal routing must
  provide its applicable maps explicitly.
- **Shortcut applicability:** direct boolean property toggles and independent
  `INVOKE_DEFAULT` operator buttons are supported. Numeric fields have no direct
  native-style shortcut action. Expanded enum options assign their exact value;
  collapsed enums offer a Shortcut to Value submenu. Enum flags toggle only the
  specified flag and preserve the other flags. Shortcuts that reopen a custom
  enum popup, custom invocations and context pointer overrides use the explicit
  host-owned `ShortcutRegistry` below. The callback retains the original action
  and its scope; enum dispatch opens the same custom glass menu.
- **Edit Source:** provide `source=your_authoring_function` to `Layout(...)` or
  `rna_binding(...)`; child layouts and component bindings inherit it. Python
  operators resolve their registered class automatically. Native C operators have
  no Python source and remain disabled. Source location checks use code metadata;
  files are read only after the user clicks Edit Source. The action opens the
  precise file/line in the owning area's Text Editor, like BVT, without saving it.
- **Python tooltips:** prepared RNA/operator rows include their Python API target
  only when Blender's `show_tooltips_python` is enabled. Tooltip reveal retains
  the same finite dwell, blur, spring and cleanup as ordinary descriptions.

[Menu parity and glass QA v5](design/qa/context-menu-v5/index.html) records disposable
runtime tests and current captures. These are execution results, not a claim of
exact generated-reference acceptance. Cross-platform/native-build admission,
the broader theme/DPI/window matrix and generated-reference/motion approval
remain separate qualification gates. Arbitrary UILayout templates belong to the
remaining control parity work, rather than being flattened into menu commands. The rejected v1 generation remains
immutable provenance and is not a specification for corrected liquid glass.

## Extension-contributed fields

The bounded public menu collector supports `prop` boolean, numeric and string
scalars/components, whole-array component submenus, `prop_enum`, `props_enum`, enum `prop` submenus, `operator_enum` and
`operator_menu_enum`. Choices use the existing BVT menu renderer, checked
indicator, theme roles, liquid glass and spring. Operator choices preserve their
arguments, invocation and pointer override scope. Property commands require the
host's `menu_commit("PROPERTY")` boundary and roll back if it rejects the change.
Disabled parent rows and stale owners cannot execute.

Inline fields use the shared text buffer, glass, theme roles and row motion.
Typing is deferred until Enter. Mouse caret placement, drag/Shift selection and
clipboard editing retain the draft; invalid input shows a shared-glass tooltip
when Blender tooltips are enabled. Escape/right-click cancels the draft without
writing; invalid expressions and concurrent owner/value changes reject commit.
Numeric input supports safe arithmetic and RNA hard bounds. Unit syntax and
full subtype formatting remain part of broader `prop` parity. Text is bounded
at 4096 characters; longer existing strings are rejected instead of truncated.

Dynamic property/operator enums are evaluated with the real Blender context on
admitted native builds; choices are revalidated before mutation. Blender may
supply `None` to operator enum callbacks according to its RNA flags, so callbacks
must preserve Blender's normal optional-context contract. Temporary typed
operator containers are released immediately without saving preferences. Other
builds retain public static RNA enumeration, with unavailable choices disabled.
`context_string_set` now supplies real native string contexts to poll, execute
and nested contributions on admitted builds. Nested stores restore on exit and
exceptions; window/context invalidation clears instead of restoring stale state.
Unsupported native scopes fail closed. Arbitrary UILayout templates still need
their own custom controls; this collector does not claim general UILayout parity.

Inline `menu_contents` inherits its parent's enabled/active state, operator
invocation and scoped pointers. Its callback failures are isolated so later
contributions still collect. Operator arguments are snapshotted recursively at
collection time; mutable lists, nested dictionaries, sets, mathutils values and
RNA arrays cannot silently change an already-open command. RNA pointer arguments
retain their owner identity and are rechecked before execution. Snapshots are
bounded to 512 nodes and eight levels; unsupported/oversized snapshots disable
the affected action and report a diagnostic. Operator/menu registration identity
is also rechecked. Collection and snapshot copying never run in painting.


## Custom-popup shortcut lifecycle

Registration remains explicit and belongs to the consuming extension:

```python
from beyond_ui import Canvas, ShortcutRegistry

shortcuts = ShortcutRegistry("your_extension.ui")
shortcuts.register()  # extension register(), never a drawing callback
canvas = Canvas(shortcut_registry=shortcuts, shortcut_namespace="tools")
# Add controls. Supply stable shortcut_key values for custom buttons/enums.
canvas.arrange(width)
canvas.bind_shortcuts(context, clip)  # after rebuild, outside painting
# ... extension unregister():
shortcuts.close()
```

Use one registry per unique extension owner. Commands are bounded, scoped to the
window/area and revalidated against the current scene, exact control identity,
binding, visibility and enabled state. Rebind after rebuilding controls, without
changing their stable `shortcut_key`. RNA enum controls default to their context
property path; transient generated layout IDs should not be persisted as keys.
For custom host actions use `bind(command, context, callback, valid=...)` and
`entry(command, context)`. Remove a particular owner with `unbind`; `close`
revokes all callbacks and unregisters the owned operator. User keymap entries
are not automatically deleted or saved: a subsequent registration/rebind
restores their targets. Host conflict maps can be passed to the registry.

The window-input fixture assigns F18, invokes it outside the canvas, opens the
custom enum popup and commits with keyboard navigation. Scope and transaction
fixtures also reject hidden/replaced owners, reject concurrent edits, roll back
host commit failures, and cleanly unregister. These are execution checks, not
exact visual acceptance.

### Opening motion includes every option

All row labels, shortcut hints, disabled options, checkmarks, arrows and inline
values follow the menu's shared reveal transform. Native deferred font batching
is covered by the [v6 pixel regression](design/qa/context-menu-v6/index.html);
153 animation frames match unbatched drawing on each tested Blender version.
The correction is scoped to finite motion and preserves resting batching,
logical hit targets, theme roles and the cached liquid-glass backdrop.
