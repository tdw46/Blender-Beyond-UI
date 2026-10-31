# Action, status and component controls

These implementations use the production custom Canvas renderer and shared
BVT glass, theme roles, fonts, spring motion and exact-owner context menus.
They do not forward drawing to native UI widgets. Their ledger status remains
**partial** until remaining semantics and visual reference acceptance are closed.

```python
ui.operator_menu_hold("my_extension.apply", menu="MY_MT_actions", text="Apply")
ui.template_component_menu(context.object, "location", name="Transform Components")
ui.template_event_from_keymap_item(keymap_item, text="Shortcut")

# Inside an owned custom popover:
ui.template_popup_confirm("my_extension.apply", text="Apply", cancel_text="Cancel")
```

## Input and ownership

`operator_menu_hold` executes its primary operator on a quick matching release.
After 0.2 seconds it opens the registered menu through the shared custom menu
host. The opening release is consumed, so it cannot execute a newly exposed row.
The right-click menu also offers the held menu for keyboard/context access.
Dragging outside, cancellation, changed context, disabled/replaced owners and
layout invalidation discard the pending primary action. Hold deadlines use the
host's existing finite animation scheduler and work when animation is disabled.
Release motion reaches the source spring; no permanent timer is installed.

`template_popup_confirm` adds release-owned Cancel/Confirm actions and selects the
requested default for Return. Empty cancel text omits Cancel; an empty operator
permits a cancel-only footer. Successful/modal results dismiss only the owning
popup; `CANCELLED` keeps it open. A replacement popup is never closed by an old
footer. The host must supply a real custom popup; inline layouts reject this API.

`template_event_from_keymap_item` displays Blender's own localized shortcut text,
including macOS modifier symbols. It is read-only, as the native template is.
Its Copy Shortcut menu revalidates the exact keymap item; deleted items become
unavailable. This is separate from editable `prop(event/full_event)` controls.

`template_component_menu` expands the exact RNA property into a persistent custom
popup. Numeric arrays get individual indexed fields; enums get retained choice
rows. Properties keep ordinary transactions, cancellation, units, themes, motion
and property context menus. Choices at or above `Canvas.menu_search_threshold`
get a custom Search field using the shared token/group matcher. Filtering runs
only on input, retains original controls/bindings and excludes hidden choices
from hit testing. Ordinary scalar/pointer/color controls reuse their existing
capabilities and explicit limitations. Deleted owners or changed schemas/contexts
invalidate the entire popup. No RNA class registration is needed.

## Presentation flags

Ordinary Canvas fields now consume `alert`, `emboss=NONE` and
`emboss=NONE_OR_STATUS`, including `prop/operator(emboss=False)`. Alert/keyed/
changed/driven colors come from the same capability-gated active-theme roles as
compound pie controls. BVT scalar sliders and boolean switches retain their
required geometry. `PULLDOWN_MENU` and `PIE_MENU` still share normal custom chrome;
distinct native emboss geometry is not claimed.

Animation status is prepared during layout, meaningful input or an explicit
`Canvas.refresh_status(clip)` host invalidation. It is not queried during paint,
idle timers or ordinary hover. Hosts retaining a Canvas across external animation
or frame changes must call this hook or rebuild/invalidate their layout. New
specialized widgets still need their own internal alert/emboss integration.

## Evidence and limits

[QA gallery](design/qa/action-parity-v1/index.html) contains actual Metal captures
at 1×/1.5×/2×, held and right-click menus, confirmation, component editing/search,
status colors, narrow layout and disabled animation. The README GIF contains
actual captured frames. The evidence builder checks source hashes, fixture hashes,
all runtime markers and 240 exact batched/unbatched text-frame pairs.

Eight background executions cover actions, popup keyboard behavior, standalone
pies and general runtime regressions on Blender 5.1.2/5.2.2. Four no-focus GPU
processes cover the scale/version matrix. Each retains one backdrop and one
strong-blur production, with stable shader, batch, font and offscreen resources.
CPU submission timing distributions are recorded; they are not GPU completion
latency or proof of full BVT performance parity. Full Windows/Linux/4.2 runtime,
light/custom themes, generated-reference equality and full native dialog/keyboard
semantics remain open. Blender activated during all four no-focus GPU launches;
that focus failure is recorded separately from passing UI execution.

Reproduce with the focus observer from `BACKGROUND_TESTING.md` around
`uv run python tools/run_action_parity_qa.py`, writing the observation to
`build/action-parity-v1/focus.json`, then run
`uv run python tools/build_action_parity_qa.py`.

The exact 4.2/5.1/5.2 API and 5.2 Manual URLs were requested during this audit;
fetches were unavailable. They are not treated as verified web evidence.
[Source audit](design/qa/action-parity-v1/source-audit.json) records the official
Blender source revisions and files used to verify the hold threshold, template
signatures and persistent expanded-property behavior. Installed-runtime tests
provide the 5.1.2/5.2.2 execution evidence; 4.2 source inspection is not 4.2 testing.

A separate paired 5.2.2 performance probe alternates the baseline `54dd612`
painter/culling functions and current functions on the same 144-button, clipped
and scrolled workload with an identical 48-action searchable menu. Each state
uses 20 warmups and 200 alternating samples per revision. Median changes range
from -0.6% to +3.4% (largest absolute increase 0.026 ms); stable resources and
similar p95 values show no large regression in this workload. This is an older
reference baseline, not a reconstruction of every preceding dirty-tree change,
and does not establish all-control or GPU-completion performance parity.
The fifth windowed process also activated despite the no-focus flag.
The [paired record](design/qa/action-parity-v1/paired-performance.json) identifies
the exact measured painter/culling hashes. Run `tests/benchmark_popup_focus_paired.py`
through the no-focus runner with `BEYOND_UI_OPERATOR_BENCHMARK` pointing to
`build/action-parity-v1/paired`, output `build/action-parity-v1/paired-run`, and
focus output `build/action-parity-v1/focus-performance.json` to reproduce it.

## Host context contribution follow-up

Operator-authored buttons now append consuming-extension context actions, matching
the existing pointer/panel contract. Hold buttons inherit this provider once,
alongside their held-menu entry. Confirmation operator buttons share the same
authoring path. Contributions receive the exact clicked target and current
context; removed controls invalidate pending actions. The shared menu retains
glass, theme, motion, clipping and keyboard behavior. Background 5.1.2/5.2.2
regressions pass; no new visual qualification is claimed. Evidence:
`design/qa/operator-host-context-v1/runtime.json`.
