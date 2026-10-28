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
`shortcut` and a tuple of `Shortcut` event bindings. Providers are called on open,
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
capability. Key-modifier chords are intentionally not dispatched, matching the
source's safe behavior. Disabled actions cannot execute. Public Python
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

[QA gallery](design/qa/context-menu-v1/index.html) includes real Blender root,
nested, tooltip, all eight compound targets, glass-versus-tint comparison and
motion. Disposable Blender 5.1.2/5.2.2 tests cover RNA transactions, selected-owner
rollback, keyframes/drivers, public nested menu contributions, stale elements,
actual window input, delayed tooltip shutdown, glass admission and teardown.
Pure tests cover clipping, bounds, disabled actions, provider exceptions and
compound target resolution. Older supported runtimes/platforms are not freshly
qualified by these tests.

Native favorites/shortcut editing, Blender's private driver clipboard, source
editing, Python API tooltips and arbitrary UILayout callback surfaces remain
explicit host-adapter/parity gaps. Exact generated-reference/motion acceptance
and the full light/custom-theme, DPI and multi-window matrix remain open. The
initial generated menu image was rejected: it altered disabled contrast and
specified tint-only glass. It is preserved as rejected provenance, not an
accepted specification or a target for the corrected liquid-glass implementation.
