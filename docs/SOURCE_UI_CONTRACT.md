# Original BVT UI contracts

Audited 2026-10-27 at BVT commit
`70f28650352f61652273f32cd042fbb3df491c53`. The three audited files had no local
changes. Exact hashes are in [source-ui-audit.json](source-ui-audit.json).
The owning source checkout is
`/Users/tylerwalker/Documents/Blender/extensions/user_default/beyond_vrm_extension_suite`.
Source files were read, not modified. These examples govern the reusable
implementation; the library must not import the BVT extension at runtime.

## Theme colors

`_shoost_canvas_style.py::theme_palette` reads eleven values from public UI widget
roles: radio accent, regular background/text, tool background, numeric field,
selected tab, numeric-slider track/fill, toggle off/on and selected radio text.
Reads accept RGB/RGBA and fall back when the role is unavailable. The source
explicitly treats theme values as display-space, with no scene-linear conversion.

`_theme_palette` caches the resolved palette by its immutable color signature
(maximum eight entries). Theme RGB supplies the colors; source glass treatment
supplies opacity. Muted text and selected colors are derived mixtures. Semantic
tokens resolve at painting time so edits to the active theme do not invalidate
layout, geometry, thumbnails or blur. There is no theme polling timer and no
preference mutation.

Production now selects this reader by default. Basic controls, existing selection
menus and all eight compound cards consume shared colors; graph/point mapping and
explicit artwork fixtures are documented in [THEMING.md](THEMING.md). Palette
mappings are immutable and cached by signature. Missing theme roles are reported
explicitly. Light/custom appearance and exact generated-reference acceptance
remain open; [theme QA](design/qa/theme-v1/NOTES.md) records the execution evidence
and the generated reference conflict.

## Context menus

Use `VRM_ShoostContextMenu.py` and the owning menu branch of
`VRM_ShoostCanvas.py` as examples:

- `entries` resolves the clicked property's owner and capability. Source actions
  include reset, copy to selected, data/full paths, applicable keyframe/driver
  actions, documentation and developer-only command/source tools. Product layer/
  effect clipboard actions remain supplied by the BVT host.
- Native-button-only actions are visibly disabled with an explanation. The
  source never runs `ui.*` button operators against an unrelated active button.
- `decorate` snapshots applicable user keybindings when opening. Menus are not
  rebuilt or rescanned on paint/timer ticks.
- `open_menu` takes the exact property/subcomponent action, snapshots stable owner
  identity and scene/developer context, replaces the window's earlier menu, sizes
  it to its labels/shortcuts and clamps it to the available panel bounds.
- `valid` re-resolves ownership; `execute` validates again before applying an
  action. Read-only, stale, changed-scene and invalid target cases fail closed.
- Public Python menu extensions are collected on demand. Operator polling and
  execution use explicit `button_pointer` / `button_prop` context overrides,
  without leaking a prior native button. Nested capture is depth-bounded.
- `choose` supports submenus with a parent stack and a Back row, restarts the
  finite overlay spring, and isolates action failures from the perpetual input
  modal. `back` restores parent navigation state.
- Canvas routing provides hover, arrows/wheel navigation, Enter/Right selection,
  Left/back, shortcuts, dismissal and cancellation. Right-click during an active
  edit/drag retains cancellation semantics before any new context-menu dispatch.
- Actions that mutate data use the host's undo boundary. Multi-owner operations
  restore previous values if applying the action fails partway through.

The library now exposes this shared contract through `MenuEntry`, `MenuTarget`,
`Canvas.context_provider`, RNA adapters and public Python button-menu collection.
[Context menu integration](CONTEXT_MENUS.md) documents ownership, undo, disabled
native-only actions, scoped limitations and execution evidence. The source
`_custom_ui_components.uncovered` behavior prevents parent text bleeding through
child menus. Delayed descriptions use a single 0.55-second dwell callback.

Menus and tooltips consume the original BVT lens at blur 0.7 and radius 10,
without a theme-colored opaque overlay. Parent pages and controls share the same
backdrop revision. PanelHost enables that path by default; tint fallback is an
explicit capability fallback, not visual acceptance. BVT scene types, product
operators, localization and undo ownership remain with the consumer. Exact
reference, motion, broader theme/platform and native-only action parity remain
open; see [menu QA](design/qa/context-menu-v1/index.html).


## Menu action adapters — 2026-10-28

The additional BVT `_shoost_driver_clipboard.py` audit is recorded in
[menu-adapter-source-audit.json](menu-adapter-source-audit.json). Its opaque-pointer
clipboard calls and temporary-ID staging inform the reusable adapter. The library
adds source/executable fingerprint admission, host-undo failure rollback, and no
BVT-specific Windows imports. Blender's exact `ec6e62d40fa9` and `d13f752e3b9c`
`drivers.cc`, `screen_user_menu.cc`, `interface_context_menu.cc`,
`DNA_userdef_types.h`, `wm_keymap_utils.cc` and `WM_types.hh` were audited; source
hashes are in [the native menu manifest](../beyond_ui/hosts/menu-native-audit.json).

Quick Favorites and shortcut assignment go beyond the original BVT disabled rows.
Their semantics come from those exact Blender sources, including context-relative
properties, typed operator arguments, user keymaps and invocation values. The
private favorite list offset is admitted only with the tested executable hashes;
all keymap edits use public RNA. BVT's source-location behavior is retained with
an explicit authoring callable instead of a product-specific global plan.
The shared BVT menu painter, lens/strong blur, theme roles and bounded spring are
also used for shortcut capture. No new material or animation system was added.
