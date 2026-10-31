# Third-party panel scope — 2026-10-30

Tyler approved this scope: only controls likely to be used in custom third-party
extension panels, not replacements for Blender's entire native UI. Full Blender
API coverage is no longer the release goal. Existing useful implementations stay;
visual and behavioral requirements are not weakened. The canonical member-by-member
coverage remains CUSTOM_PARITY.json; no implementation status is promoted here.
Editor/application templates are deferred unless a concrete consumer needs them.
The categories below guide prioritization, not automatic promises to ship every
core candidate or permanently exclude every feature-dependent template.

## Required reusable UI surface

Full reusable-control parity covers extension-authored N-panels and Properties
panels, popovers, invoke dialogs/menus, dropdowns/enums and nested menus. Properties
panel support means the extension's own UI, not replacing Blender's built-in
modifier stacks, Grease Pencil feature UI or other editor/application panels.

**Full applicable right-click parity is required.** Every supported control and
individual field, row, handle or swatch must expose its relevant property,
operator and data actions with exact-owner resolution and live capability checks.
This includes shortcuts, keyboard invocation, nested/back navigation, cancellation,
clipping, stale-owner rejection and the same BVT glass, theme and spring motion.
An unavailable native-button-dependent action remains a documented gap; omitting
it or disabling it does not establish full context-menu parity. Built-in feature
panel exclusions do not excuse missing context actions on supported controls.

## What the current counts mean

137 inventoried UILayout members: 65 partial implementations and 72 unimplemented.
There are no reference-matched members under the current strict release gate.
That does not mean there are no working controls: partial includes substantial
execution-tested functionality as well as missing semantics and visual acceptance.
The count mixes UI controls, layout flags, compound templates and metadata helpers;
it is not a percentage of usable product functionality.

Existing custom families include layout/spacing/sizing, common RNA properties,
sliders/switches, operators, searchable enums, pointer/collection search, menus,
pies, popovers, decorators, registered lists, data-block selectors, colors,
ramps, curves, palettes, matrices and progress indicators. Each retains explicit
limits in the canonical ledger; existing does not mean complete.

## Recommended first release priorities

1. Finish common property correctness and keyboard navigation: remaining units,
   supported keywords/subtypes, cancellation and dynamic-owner behavior.
2. Finish practical list behavior, icons and previews, then multiline text.
3. Finish curve handles, exact-coordinate editing and bounds when used by consumers.
4. Qualify the core on supported Blender versions and delivery platforms, including
   explicit failure/fallback behavior for currently build-specific native adapters.
5. Close visual/motion/theme acceptance for the supported core at representative
   sizes. This remains separate from passing runtime tests.

A vendored toolkit does not need to recreate Blender's entire application UI to
be useful. Full drop-in compatibility for arbitrary existing Panel.draw callbacks
is a different promise: that requires either the broader surface or explicit
unsupported-method errors. Native forwarding must never count as custom parity.
A core release must document its supported subset and never advertise full parity.

Every supported control still requires real shared BVT glass, source springs,
active-theme roles, stable hit geometry, exact-owner right-click actions and
bounded retained resource use. Deferring an editor template does not relax these
requirements for any shipped control.

## Missing members by recommended priority

These groups are recommendations based on the repository inventory and intended
vendored-extension use, not proof that a particular consumer needs each feature.

### Core candidates (10)

- `template_ID_preview`
- `template_any_ID`
- `template_file_select_path`
- `template_icon`
- `template_icon_view`
- `template_menu_search`
- `template_operator_search`
- `template_search_preview`
- `textbox`
- `textbox_with_state`

### Feature-dependent (20)

- `template_ID_session_uid`
- `template_action`
- `template_bone_collection_tree`
- `template_colormanaged_view_settings`
- `template_curveprofile`
- `template_image`
- `template_image_layers`
- `template_image_settings`
- `template_image_stereo_3d`
- `template_image_views`
- `template_keymap_item_properties`
- `template_light_linking_collection`
- `template_node_inputs`
- `template_node_link`
- `template_node_tree_interface`
- `template_node_view`
- `template_path_builder`
- `template_preview`
- `template_shape_key_tree`
- `template_texture_user`

### Blender editor/application templates (38)

- `template_asset_shelf_popover`
- `template_asset_view`
- `template_cache_file`
- `template_cache_file_layers`
- `template_cache_file_procedural`
- `template_cache_file_time_settings`
- `template_cache_file_velocity`
- `template_collection_exporters`
- `template_collection_importer`
- `template_constraint_header`
- `template_constraints`
- `template_edit_mode_selection`
- `template_grease_pencil_layer_tree`
- `template_grease_pencil_modifiers`
- `template_greasepencil_color`
- `template_header`
- `template_header_3D_mode`
- `template_histogram`
- `template_input_status`
- `template_layers`
- `template_marker`
- `template_modifier_asset_menu_items`
- `template_modifiers`
- `template_movieclip`
- `template_movieclip_information`
- `template_node_asset_menu_items`
- `template_node_operator_asset_menu_items`
- `template_node_operator_asset_root_items`
- `template_node_operator_registration_errors`
- `template_recent_files`
- `template_reports_banner`
- `template_running_jobs`
- `template_shaderfx`
- `template_status_info`
- `template_strip_modifiers`
- `template_track`
- `template_vectorscope`
- `template_waveform`

### Metadata helpers (4)

- `bl_rna_get_subclass`
- `bl_rna_get_subclass_py`
- `icon`
- `introspect`

## Evidence boundaries

This audit reads the current local parity ledger and implementation notes.
Exact-version official API pages were requested but unavailable through the web
tool; no newly fetched documentation is claimed. No runtime behavior changed in
this scope audit. The existing per-member execution and reference evidence stays
in CUSTOM_PARITY.json. Editor-specific items can be implemented when a consumer
requires them; they are not silently removed from the inventory.
