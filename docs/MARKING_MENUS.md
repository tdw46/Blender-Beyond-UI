# Marking menus and release-owned clicks

The custom menu engine now commits ordinary mouse selections on matching release.
Press captures the exact page, row object and index; release must hit that same
row. Moving off it, Escape, right-click, window deactivation, removed owners or
changed capabilities cannot dispatch the action. Keyboard activation remains
immediate. An active text editor or explicit shortcut-capture mode retains its
own input semantics. No timeout guesses or platform key-state polling are used.

Actions may replace the current menu with another popup. Canvas dismisses only
the originating menu, and never forwards the consumed release to its replacement.

## Standalone Layout.menu_pie

A custom `Layout` can now author and open a pie without registering a `bpy.types.Menu`:

```python
ui = Layout(context=context, commit=host.commit_property)
ui.canvas.menu_commit = host.commit_menu_action
pie = ui.menu_pie()
pie.operator_context = "EXEC_DEFAULT"
col = pie.box().column(heading="Transform")
col.prop(context.active_object, "location", index=0, text="Location X")
col.use_property_split = True
col.use_property_decorate = True
col.prop(context.active_object, "location", index=1, text="Location Y")
pie.operator("object.shade_smooth", text="Smooth")
menu = pie.open(anchor=opening_pointer, clip=host_clip, trigger=invoking_key)
```

`open()` is the custom host invocation adapter, not an additional Blender UILayout
member. Coordinates are logical host units. Pass `trigger=None` for click mode.
Route input/paint and finite animation wakes through the owning Canvas as usual.
No keymaps, RNA types, handlers or timers are installed by authoring. The host
owns undo and teardown. Registered nested menus are optional and share the same
owner checks, selection snapshots, right-click targets and Back stack.

Definitions require an explicit context and must be rebuilt if their scene, area
or active owner changes. Opening finalizes operator arguments; disabled layouts,
stale context pointers and invalid arguments fail before presentation. Reopening
cancels the prior Canvas menu and constructs fresh geometry. This is genuine custom
execution, but not a claim of full native UI or exact-reference parity.

### Compound presentation flags

These apply to both registered and standalone pie collectors. Child groups inherit
presentation flags at creation; enabled/active ancestor guards remain live.

| Flag | Current custom behavior |
| --- | --- |
| `alert` | Active theme error tint on the row/field; disabled controls remain muted |
| `emboss` | `NONE` removes inner field chrome; `NONE_OR_STATUS` retains alert/animation-status chrome; method `emboss=False` selects the latter |
| `use_property_split` | Right-aligns numeric/string labels within the shared label lane; does not enlarge fonts |
| `use_property_decorate` | With split enabled, scalar/indexed properties reserve an exact-owner decorator; False omits it |
| `activate_init` | First eligible marked field enters selected-text editing on open; never activates the OS window or executes an operator |
| `active_default` | First eligible marked action gets initial keyboard selection; Return dispatches through normal owner checks |

`prop_decorator()` is also available explicitly in a compound. It uses the existing
public-RNA decorator model for exact component key insertion/deletion and property
right-click actions. Hosts must supply `canvas.menu_commit` to enable mutation.
Non-animatable/empty decorators retain a spacing slot. Decorator states and numeric
animation colors are prepared on open/input; paint never scans animation data.
`NONE_OR_STATUS` uses those prepared colors. All translucent status fills still use
the shared glass. Boolean properties remain source toggle switches under every
emboss mode, per Tyler's scalar-layout requirement.

`NORMAL`, `PULLDOWN_MENU` and `PIE_MENU` use the existing custom menu chrome;
separate native emboss geometry is not claimed. Full native split alignment across
mixed arrays, specialized compound widgets, dialog acceptance/focus traversal and
joined-corner geometry remain open. The narrow searchable fallback exposes the same
leaves, but does not retain every inline compound relationship (including decorator
placement). Alert/emboss integration on ordinary non-menu Canvas controls is still
open and is not covered by this menu implementation.

## Registered pie definitions

The registered-menu authoring surface implements `self.layout.menu_pie()`:

```python
class MY_MT_actions(bpy.types.Menu):
    bl_label = "Actions"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator_context = "EXEC_DEFAULT"
        pie.operator("object.shade_smooth", text="Smooth")  # West
        pie.operator("object.shade_flat", text="Flat")      # East
        pie.separator()                                    # Empty south slot
        pie.menu("MY_MT_more")                             # North

# In the consuming extension's custom Layout:
layout.menu("MY_MT_actions")
```

Slots follow W, E, S, N, NW, NE, SW, SE. Up to eight slots are accepted; separators
reserve empty directions. Nested ordinary menus keep their 4096-row bound,
search, owner-specific context actions, numeric editing and Boolean switches.
Root pie definitions cannot be mixed with preceding ordinary rows. A row,
column or box at the pie root occupies one direction; nested rows/columns/boxes
retain their geometry inside that slot. Each leaf keeps its own enabled state,
property owner, operator arguments and right-click target. Ancestor disabling
remains live. Trees are bounded to depth 16 and 4096 nodes; cyclic/oversized trees
fail before painting. Empty slots reserve directions without inventing actions.

```python
pie = self.layout.menu_pie()
column = pie.box().column(heading="Transform")  # One west slot
buttons = column.row(align=True)
buttons.operator("transform.translate", text="Move")
buttons.operator("transform.rotate", text="Rotate")
column.prop(context.scene.render, "film_transparent", text="Transparent")
pie.operator("object.duplicate_move", text="Duplicate")  # East
```

A direction into a compound does not guess which child should execute: child
selection uses its exact hit area. Nested registered radial definitions are supported
through `menu()` children from either a list or a pie. Each child replaces the visible
ring and grows from its selection point. A center Back control (or the list header
in narrow fallback), Left Arrow and Escape restore the retained parent. Ordinary
list children and exact property contexts keep their existing page stack. The combined
navigation budget includes both page stacks and saved rings; it remains three levels.
Inline `menu_contents()` cannot insert another radial root into an existing slot.
A standalone retained-panel
`Layout.menu_pie()` authoring route is not implemented; this is specifically a
registered menu callback capability, recorded as partial in the ledger.

Hosts can also open an entry-based marking menu from their own keymap:

```python
canvas.open_pie(
    target, entries, anchor, clip,
    context=context, trigger=event.type,
)
```

The host invokes this once on the initiating press and routes subsequent events
to `Canvas.event`. `anchor` must be the original mouse location in canvas logical
units. Button and registered-shortcut routes capture their current event point.
Leaving `trigger` unset opens click mode. The optional `settings=PieSettings(...)`
and `dead_zone=` arguments override the invocation defaults without editing GPU
code. Per-menu/host/global `AnimationSettings.enabled` and `.strength` apply live.

## Compound layouts and nested ownership

Compound slots now support `split(factor, align)`, `column_flow(columns, align)`
and `grid_flow(row_major, columns, even_columns, even_rows, align)`, in addition
to rows, columns and boxes. They use `flow.Plan`, the same retained layout engine
as ordinary panels. Geometry is measured/placed when the menu opens, not during
painting. Positive grid counts are fixed; zero/negative counts use the shared
available-width and major-axis packing rules. Column flow supports nonnegative
counts. Counts are bounded to 4096; trees remain bounded to 4096 nodes/depth 16.

Compound groups accept `alignment` (`EXPAND`, `LEFT`, `CENTER`, `RIGHT`),
`scale_x`, `scale_y`, `ui_units_x` and `ui_units_y`. Zero sizing values preserve
the automatic policy; finite nonnegative values are capped at 4096 and combined
scale is checked by the shared planner. A logical size unit is one 23-unit menu
row. These settings allocate geometry without magnifying fonts/icons. Explicit
very small sizes can constrain content; they do not establish reference fidelity.
Automatic flow depends on the slot's available width; set a logical width when
more columns are desired. Group sizing is sampled on open, while ancestor enabled
state and host animation policy remain live.

`separator(factor, type)` retains explicit spacing in compound groups; `LINE`
paints a theme-derived rule, `SPACE`/`AUTO` reserve space. At the pie root it still
reserves one direction. `separator_spacer()` distributes surplus width inside a
compound horizontal row. Spacing has no invented action or context target and
moves with its owning surface. Joined-corner and all native sizing details remain
reference/parity work.

```python
pie = self.layout.menu_pie()
column = pie.box().column(heading="Transform")
column.ui_units_x = 14
split = column.split(factor=0.4)
split.operator("transform.translate", text="Move")
split.operator("transform.rotate", text="Rotate")
grid = column.grid_flow(columns=2, row_major=True, even_columns=True)
grid.prop(context.scene.render, "film_transparent")
grid.menu("MY_MT_nested_pie")
row = column.row(align=True)
row.operator("object.select_all", text="Select")
row.separator_spacer()
row.operator("object.select_all", text="Deselect").action = "DESELECT"
```

`Canvas` owns navigation automatically, including right-click contributed menus.
Low-level hosts constructing `Menu` directly must install
`menu.on_navigate(previous, current)` to adopt the new active menu and continue
routing paint/input to it. The callback is inherited by children. Hosts must honor
the normal `closed` state. Each child inherits motion policies, theme/backdrop
through the host, and current owner/scope guards. A selected action closes the
presentation chain before dispatch while preserving valid owner rechecks. Back
revalidates the saved parent; removed owners, changed polls and disabled ancestors
cannot execute. Closing, hiding or cancelling releases the saved menu chain.

## Preference-based timing

`PieSettings.from_context(context)` snapshots the active `preferences.view` once
per invocation, with capability-gated defaults for unavailable fields. Values
are never written back. The first three native preferences use hundredths of a
second and are converted to seconds:

| Preference | Behavior |
| --- | --- |
| `pie_animation_timeout` | Finite pointer-origin grow envelope; source springs remain shared |
| `pie_tap_timeout` | A quick un-dragged tap enters click mode; a longer hold applies the hovered action or cancels if none |
| `pie_initial_timeout` | Direction uses the original pointer until this deadline, then the clamped menu center |
| `pie_menu_radius` | Minimum center spacing, increased when needed to preserve readable custom compound geometry |
| `pie_menu_threshold` | Central selection dead zone |
| `pie_menu_confirm` | When nonzero, crossing threshold + confirm arms a 20ms stationary confirmation |
| `use_reduce_motion`, when available | Starts the menu with motion disabled; glass/highlights remain |

Drag intent uses the source's squared-distance threshold of 50. Directional
confirmation revalidates the exact row/page and owner; movement retargets the
finite deadline. Back, context navigation, close, changed owners and teardown
cancel it. Number-row and keypad 4/6/2/8/7/9/1/3 select matching simple directions;
repeats and modifier chords do not execute. Release outside the host clip cancels.

The host's existing finite animation wake handles opening and pending confirmation;
no additional polling timer is installed. Deadlines are evaluated on that host
wake cadence (currently up to 60 Hz), so exact native 10ms-timer dispatch latency
is not claimed. `PanelHost` evaluates timer actions in
the original window/area/region override. Custom hosts must call
`canvas.advance_animations(context=current_context)` while it returns true. Once
motion and any confirmation settle, the host stops scheduling. Timing preferences
are sampled again on the next invocation; animation enabled/strength are live.

## Rendering, bounds and motion

Pies use the production context-menu painter, 11-unit body text, 23-unit content
rows, active Blender theme, retained GPU primitives, strong BVT glass and shared
Motion settings. Petals share the same captured backdrop and blur revision.
Their opening transform includes all labels, icons, values and checks. Global,
host and menu motion disabling leaves glass enabled. Logical hit targets do not
move with the presentation transform.

The pie grows from the original pointer point. The approached slot pulls toward
the pointer with the shared source spring, capped translation and area-preserving
stretch. Labels, icons, values and the slot's glass surface receive the same
presentation transform. Logical hit rectangles remain unchanged. Highlight
strength increases with proximity using the active theme's selection role. A
thin themed guide connects the original opening point to the current pointer.
The surface-tension treatment is Tyler's chosen interaction; no separate Gaussian
shader or extra backdrop/blur pass was introduced.

V5 applies Tyler's landing correction: entering a petal's **logical** rectangle,
including compound padding, immediately restores its resting position and shape.
It discards approach spring tracks rather than animating them back under the
pointer. Radial rows have no second hover/press squash layered on top. Leaving
restarts the approach spring from rest. Highlight/proximity, the guide, opening
reveal, property interactions and ordinary list/context-menu animation remain.
The hover capture and a later held capture must be byte-identical after opening
has settled; logical hit geometry never moves.


Visible child hit regions take priority over angular sectors. The full menu is
clamped inside the clip. If its natural compound geometry cannot fit,
`layout_mode == "LIST_FALLBACK"` exposes the same leaves through a searchable
custom list at the same text size. No native menu is substituted and no desktop
pointer warping is used. Radius placement is deliberately constrained by readable
custom geometry. Slot centers now share a circular radius, expanded only enough
to prevent natural-size rectangle overlaps and clear the dead zone. Full native
edge anchoring and size-dependent offsets remain a parity gap.

## Evidence and remaining work

[Compound/timing execution report](design/qa/marking-menu-v2/index.html) records
headless 5.1.2/5.2.2 RNA checks, source fingerprints and a focus audit. Unit tests
exercise tap/hold boundaries, confirmation cancellation, compound ownership,
ancestor disabling, pointer-origin growth, proximity, strength/disable behavior,
stable hit geometry and painter command traversal with mocked GPU calls.
Painter command checks are not visual verification. Event-loop timings measure
CPU input processing only; they do not establish GPU or overall UI performance.

[The v3 gallery](design/qa/marking-menu-v3/index.html) contains actual GPU captures
of growth, stretch, proximity highlights, guide, compound contexts, disabled
motion and narrow fallback. Blender 5.2.2 passed at 1×/1.5×/2×; 5.1.2 passed at 1×.
Across four fixtures, 192 animated frames matched byte-for-byte with native text
batching enabled/disabled. Backdrop/strong-blur revisions, fonts, shaders and
batches remained stable. Two native N-panel input fixtures and six background
regression processes also passed. The v1/v2 pages remain historical evidence.

All windowed launches used `--no-window-focus`, under Tyler's standing
permission, but several still activated Blender. Successful GPU checks are not
focus-safety qualification. See [background testing](BACKGROUND_TESTING.md).

The 1× warm CPU paint median/p95 was 0.211/0.248 ms for the simple pie and
0.197/0.229 ms for the compound. Paired ordinary-list median changed from 0.140
to 0.144 ms. The 1.5× current-list p95 was 0.474 ms, versus 0.164 ms baseline;
other tested scales did not reproduce that tail increase. Raw maxima and timing
distributions are retained in the capture reports. These are CPU submission
measurements without readback, not GPU completion or end-to-end latency; full
performance acceptance is still open.

[The v4 gallery](design/qa/marking-menu-v4/index.html) adds nested rings, center Back,
split/grid/flow/sizing/spacers, exact child contexts, and a PNG animation scrubber.
Four GPU fixtures passed (5.2.2 at 1×/1.5×/2×, 5.1.2 at 1×), with 144 identical
native-batching frames and stable shared GPU resources. Six background fixtures
and native N-panel nested-navigation/context/release/teardown tests passed on both
runtimes. The narrow context-menu paint regression found by native input testing
was fixed and regression-tested. No-focus launches still activated Blender in the
audit; no focus-safety qualification is claimed.

Open parity items: full native flag semantics and specialized controls inside compound menus,
exact native edge anchoring/apply/sizing/joined-corner semantics, additional themes
and platforms, and generated-reference/visual/motion acceptance. Blender 4.2 runtime
testing remains unavailable. The API ledger remains partial.

The [v5 gallery](design/qa/marking-menu-v5/index.html) adds standalone authoring,
compound flags and Tyler's stable-hover correction. All four approach/hover captures
passed; the immediate hover image and a held image one second later are byte-identical.
There are 235 passing unit tests, eight background runtime processes, four GPU
captures (5.2.2 at 1×/1.5×/2× and 5.1.2 at 1×) and two native N-panel regression
runs. 144 animation frames match with native text batching enabled/disabled.
The native panel runs cover the shared nested narrow-fallback path; standalone
flags/decorators are covered by real-RNA execution plus GPU captures. These are
implementation evidence for Tyler's QA, not exact-reference acceptance.

## Source comparison and compatibility

Behavioral inspiration: Maya Workflow Kit revision
[`ddd6db0`](https://github.com/5hyuns/maya-workflow-kit-for-blender/tree/ddd6db096282bdb1d8de517a0c98d87729b8f11d),
especially [release dispatch](https://github.com/5hyuns/maya-workflow-kit-for-blender/blob/ddd6db096282bdb1d8de517a0c98d87729b8f11d/src/allset/marking/modal.py#L261-L290)
and its pure menu engine. This implementation was written independently; no
external painter, platform key-state poller or native-widget route was vendored.
BVT's `VRM_ShoostCanvas.enum_event` and `VRM_ShoostContextMenu` were consulted;
the existing source appearance/owner contract remains, with the explicitly
requested change from press dispatch to release dispatch.

Exact 4.2, 5.1 and 5.2 UILayout API and Manual menu pages were requested on
2026-10-30; web fetches failed and direct requests returned HTTP 403. They are
not counted as documentation verification. Local archived official sources at
[`v4.2.0`](https://github.com/blender/blender/blob/v4.2.0/source/blender/makesrna/intern/rna_ui_api.cc),
[`ec6e62d40fa9`](https://github.com/blender/blender/blob/ec6e62d40fa9/source/blender/makesrna/intern/rna_ui_api.cc)
and [`d13f752e3b9c`](https://github.com/blender/blender/blob/d13f752e3b9c/source/blender/makesrna/intern/rna_ui_api.cc)
declare the argument-free `menu_pie` sublayout return. Installed 5.1.2/5.2.2 RNA
confirmed that signature. No newer runtime API or minimum-version change is
introduced by the pure Python geometry and event state.

The timing audit additionally consulted the exact
[5.1 PreferencesView API](https://docs.blender.org/api/5.1/bpy.types.PreferencesView.html)
and versioned Manual search results; direct English-page fetches for several
4.2/5.1/5.2 URLs remained unavailable. Exact source branches at
[v4.2.0](https://github.com/blender/blender/blob/v4.2.0/source/blender/editors/interface/interface_handlers.cc),
[ec6e62d40fa9](https://github.com/blender/blender/blob/ec6e62d40fa9/source/blender/editors/interface/interface_handlers.cc)
and [d13f752e3b9c](https://github.com/blender/blender/blob/d13f752e3b9c/source/blender/editors/interface/interface_handlers.cc)
verify the hundredths conversion, quick-tap/drag split and stationary 20ms
confirmation branch. Their `interface_intern.hh` defines the squared drag
threshold as 50. The installed runtimes confirmed the preference names/defaults.

The v3 placement follow-up again requested exact 4.2/5.1/5.2 API and Manual pages;
web retrieval remained unavailable. Archived official `interface_layout.cc` for
those versions was consulted for unit-circle directions and native size-dependent
anchors. Our circle uses a collision-aware radius and centered slots; it is not
claimed to reproduce native edge anchoring exactly. No version-specific API was
added by the pure geometry changes. Leaf widths now reserve the shared painter's
label, shortcut, switch and 44%-label/56%-field lanes at invocation time.

V4 used exact-version RNA definitions and archived official `rna_ui_api.cc` /
`interface_layout.cc` for 4.2, 5.1 and 5.2. Direct versioned documentation retrieval
remained unavailable; installed 5.1.2/5.2.2 signatures and execution were checked.
The source hashes and URLs are in `design/qa/marking-menu-v4/source-audit.json`.

V5 requested exact 4.2/5.1/5.2 UILayout API and versioned Manual pages again;
retrieval remained unavailable. Archived official RNA/layout definitions and
installed runtime descriptions/execution provide the behavioral evidence.
The semantic error role uses `wcol_state.error` when present, with the 4.2
`ThemeInfo.info_error` background as a capability fallback. The icon text role is
not the error tint. Existing layered/legacy Action adapters are reused unchanged.
See [v5 source audit](design/qa/marking-menu-v5/source-audit.json).
