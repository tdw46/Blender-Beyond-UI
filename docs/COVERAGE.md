# Blender API coverage

This native reference table documents **lossless access to Blender's native UI API**. It does not mean every widget is GPU-redrawn in the Effect Layers style. Native controls retain Blender's own keyboard, context menu, undo, tooltip, accessibility, and specialized-editor behavior.

`NativeLayout` delegates methods, arguments and property assignments unchanged. It wraps only returned UILayout objects (including tuples); operator property objects remain native. Future installed members are reachable without a library update. Missing methods raise the original error; use `supports()` to choose an explicit compatibility path.

Panel, Menu, Header and UIList remain ordinary host-registered Blender classes. No replacement class, custom registration framework or reduced set of hooks is imposed. Use `NativeLayout(self.layout)` in draw callbacks and `NativeLayout(layout)` in UIList.draw_item.

## Custom backend

The member-by-member [custom parity ledger](CUSTOM_PARITY.json) is authoritative:
**82 unimplemented / 55 partial / 0 reference-matched** members. Native delegation
does not count toward these totals. The table below groups current partial work.

| Family | Custom support | Remaining examples |
| --- | --- | --- |
| Surfaces, vector icons, glass and springs | Retained BVT primitives and host-owned lifetime | Exact reference/theme/platform and source-equivalent performance qualification |
| Labels, buttons, booleans, numbers, text and enums | Shared Canvas fields, source switches/sliders, searchable menus | Full property combinations, focus/accessibility and exact acceptance |
| Color editing | Custom SV/hue/RGB/HSV/alpha/hex controls | Host eyedropper, locking/cubic modes and full native semantics |
| Layout | Retained rows, columns, flows, grids, boxes, sizing policies and panel popovers | Remaining UILayout settings and complete sizing/alignment semantics |
| Large lists | Default lists and registered Python row/filter callbacks on retained visible canvases | Bounded callback settings/layouts, native-only callbacks, drag/drop and full native semantics; see [registered lists](REGISTERED_LISTS.md) |
| Color ramps and curves | Custom stop/point editing and channel controls | Remaining interpolation, handles, bounds and specialized modes |
| Data selectors | Searchable ID and supported non-ID pointers, collection searches, ID tabs and ID actions | Unsupported pointer categories and preview/template families |
| Property decorators and menus | Custom keyframe/driver states, property actions, registered menus and scoped shortcuts | Full context coverage, platform admission and native semantics |
| Scopes, specialized previews, asset/file browsers and pie menus | Unimplemented members remain explicitly tracked | Custom implementations and interaction/reference evidence |

## Version inventory

Fetched from exact versioned official API pages; see `api_inventory.json` for signatures and URLs. Runtime verification is a separate table in VALIDATION.md. A member present in docs is not an assertion that all its context-dependent combinations were exercised.

## UILayout

| Member | 4.2 | 4.3 | 4.4 | 4.5 | 5.0 | 5.1 | 5.2 | Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `activate_init` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `active` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `active_default` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `alert` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `alignment` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `bl_rna_get_subclass` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `bl_rna_get_subclass_py` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `box` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `column` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `column_flow` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `context_pointer_set` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `context_string_set` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `direction` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `emboss` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `enabled` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `enum_item_description` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `enum_item_icon` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `enum_item_name` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `grid_flow` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `icon` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `introspect` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `label` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `link` | — | — | — | — | — | — | yes | NativeLayout → native |
| `menu` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `menu_contents` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `menu_pie` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `operator` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `operator_context` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `operator_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `operator_menu_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `operator_menu_hold` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `panel` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `panel_prop` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `popover` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `popover_group` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `progress` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_decorator` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_menu_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_search` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_tabs_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_with_menu` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `prop_with_popover` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `props_enum` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `row` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `scale_x` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `scale_y` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `separator` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `separator_spacer` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `split` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_ID` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_ID_preview` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_ID_session_uid` | — | — | — | — | — | yes | yes | NativeLayout → native |
| `template_ID_tabs` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_action` | — | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_any_ID` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_asset_shelf_popover` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_asset_view` | yes | yes | yes | yes | — | — | — | NativeLayout → native |
| `template_bone_collection_tree` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_cache_file` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_cache_file_layers` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_cache_file_procedural` | yes | yes | yes | yes | — | — | — | NativeLayout → native |
| `template_cache_file_time_settings` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_cache_file_velocity` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_collection_exporters` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_collection_importer` | — | — | — | — | — | — | yes | NativeLayout → native |
| `template_color_picker` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_color_ramp` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_colormanaged_view_settings` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_colorspace_settings` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_component_menu` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_constraint_header` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_constraints` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_curve_mapping` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_curveprofile` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_edit_mode_selection` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_event_from_keymap_item` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_file_select_path` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_grease_pencil_layer_tree` | — | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_grease_pencil_modifiers` | yes | — | — | — | — | — | — | NativeLayout → native |
| `template_greasepencil_color` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_header` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_header_3D_mode` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_histogram` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_icon` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_icon_view` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_image` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_image_layers` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_image_settings` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_image_stereo_3d` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_image_views` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_input_status` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_keymap_item_properties` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_layers` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_light_linking_collection` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_list` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_marker` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_matrix` | — | — | — | — | yes | yes | yes | NativeLayout → native |
| `template_menu_search` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_modifier_asset_menu_items` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_modifiers` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_movieclip` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_movieclip_information` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_asset_menu_items` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_inputs` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_link` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_operator_asset_menu_items` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_operator_asset_root_items` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_operator_registration_errors` | — | — | — | — | — | yes | yes | NativeLayout → native |
| `template_node_socket` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_tree_interface` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_node_view` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_operator_search` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_palette` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_path_builder` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_popup_confirm` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_preview` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_recent_files` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_reports_banner` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_running_jobs` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_search` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_search_preview` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_shaderfx` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_shape_key_tree` | — | — | — | — | yes | yes | yes | NativeLayout → native |
| `template_status_info` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_strip_modifiers` | — | — | — | — | yes | yes | yes | NativeLayout → native |
| `template_texture_user` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_track` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_vectorscope` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `template_waveform` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `textbox` | — | — | — | — | — | — | yes | NativeLayout → native |
| `textbox_with_state` | — | — | — | — | — | — | yes | NativeLayout → native |
| `ui_units_x` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `ui_units_y` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `use_property_decorate` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |
| `use_property_split` | yes | yes | yes | yes | yes | yes | yes | NativeLayout → native |

## Panel

| Member | 4.2 | 4.3 | 4.4 | 4.5 | 5.0 | 5.1 | 5.2 | Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `append` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_category` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_context` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_description` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_icon` | — | — | — | — | — | — | yes | Host-owned native class |
| `bl_icon_value` | — | — | — | — | — | — | yes | Host-owned native class |
| `bl_idname` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_label` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_options` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_order` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_owner_id` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_parent_id` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_region_type` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass_py` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_space_type` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_translation_context` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_ui_units_x` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `custom_data` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw_header` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw_header_preset` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `is_extended` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `is_popover` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `layout` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `poll` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `prepend` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `remove` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `text` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_pin` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |

## Menu

| Member | 4.2 | 4.3 | 4.4 | 4.5 | 5.0 | 5.1 | 5.2 | Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `append` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_description` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_idname` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_label` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_options` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_owner_id` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass_py` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_translation_context` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw_collapsible` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw_preset` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `is_extended` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `layout` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `path_menu` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `poll` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `prepend` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `remove` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |

## UIList

| Member | 4.2 | 4.3 | 4.4 | 4.5 | 5.0 | 5.1 | 5.2 | Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `append` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bitflag_filter_item` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bitflag_item_never_show` | — | — | — | yes | yes | yes | yes | Host-owned native class |
| `bl_idname` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass_py` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_system_properties_get` | — | — | — | — | yes | yes | yes | Host-owned native class |
| `draw_filter` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw_item` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `filter_items` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `filter_name` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `is_extended` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `layout_type` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `list_id` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `prepend` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `remove` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_filter_invert` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_filter_show` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_filter_sort_alpha` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_filter_sort_lock` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `use_filter_sort_reverse` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |

## Header

| Member | 4.2 | 4.3 | 4.4 | 4.5 | 5.0 | 5.1 | 5.2 | Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `append` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_idname` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_region_type` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_rna_get_subclass_py` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `bl_space_type` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `draw` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `is_extended` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `layout` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `prepend` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
| `remove` | yes | yes | yes | yes | yes | yes | yes | Host-owned native class |
