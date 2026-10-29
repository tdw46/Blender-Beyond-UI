# Searchable dropdowns

Shared menus automatically show search when a page contains at least **12 options**.
This covers scalar/flag enum dropdowns, host-provided action menus and nested menu
pages. Existing pointer and collection pickers keep their shared search UI.
Short menus retain their current appearance and interactions.

Type while a searchable menu is open, or click its search field. Matching is
case-insensitive: every space-separated query word must appear in the option
label or its group heading. Order stays stable, and matching headings/separators
stay with their original options. Search does not invoke nested providers to
scan unopened pages. Each child page searches its own choices and retains the
parent query when navigating back.

- Up/Down and Page Up/Down navigate results; Enter accepts the highlighted choice.
- Ctrl/Cmd+F focuses search and selects its query. Ctrl/Cmd+A selects all;
  paste, Backspace/Delete, caret movement and mouse selection use the shared text
  editor. Copy/Cut apply to focused search; unfocused menu action shortcuts remain
  available. Home/End move the caret while editing and navigate results otherwise.
- The × button clears the query. Escape or right-click clears a nonempty query
  first; a second press returns to the parent or dismisses the menu. Right-click
  outside the host still passes through. Property right-click menus keep their
  exact owner and actions.
- Empty results show “No matches”. Disabled actions remain disabled. Filtering
  never writes a binding, and selection revalidates the original owner/action.

The search field stays pinned while results scroll. Menu height shrinks with the
result count and restores when cleared. Typography uses the shared 11-unit field
style. The field and its text use the same retained glass backdrop, theme colors
and bounded squash/stretch motion as the menu. Motion disable/strength controls
remain inherited from the host; there is no new idle redraw or capture loop.

## Host configuration

```python
canvas = Canvas(menu_search_threshold=12)  # default; positive integer
canvas.menu_search_threshold = 8          # applies the next time a menu opens

# Hosts constructing the shared menu directly:
menu = Menu(target, entries, anchor, clip, search_threshold=12)
```

Option labels are case-folded once per opened page. Filtering runs only when the
query changes; painting consumes prepared rows and draws only visible results.
Existing row admission limits remain: default general menus 64, enum menus up to
4096. Search text is capped at 4096 characters. Filtering changes neither binding
snapshots nor action identity, and does not rebuild shaders, fonts or backdrops.

[QA gallery](design/qa/menu-search-v1/index.html) contains actual implementation
captures at three scales on Blender 5.1.2/5.2.2, a motion GIF, runtime/window
results and equivalent-workload performance records. Existing field and menu
styling is reused; this is not a new generated-reference approval. Complete IME
composition, fuzzy ranking, exact visual acceptance and broader theme/platform
coverage remain open. The unchanged 4.2 event path has no new API dependency;
Blender 4.2 runtime execution remains unqualified.
