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

The extraction already contains this reader as `native_theme_palette`, but the
production `theme_palette` currently chooses the fixed reference skin, and
compound painters still contain fixed colors. **Default theme selection and
complete role plumbing are open parity defects.** An explicit reference fixture
must stay available for reproducible comparisons, without silently becoming the
production theme policy. Graph/point roles also need a documented theme mapping.

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

The reusable library has compact selection menus, but **does not yet expose the
full BVT right-click context-menu contract**. Do not count cancellation alone as
support. Preserve these behaviors through generic callbacks/identity resolvers;
BVT scene types, IDs, operators, localization and undo ownership stay with the
consumer. AGENTS.md now makes this a completion gate for every applicable control.
