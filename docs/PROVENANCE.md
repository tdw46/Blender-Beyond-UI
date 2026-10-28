# Extraction provenance

Extracted from first-party Effect Layers UI helpers in Beyond VTuber Tools at
commit `70f28650352f61652273f32cd042fbb3df491c53`. The source working tree had
unrelated changes; it was read without modification. `extraction.json` records
the exact source-file hashes and destination paths, including any uncommitted
source bytes present at extraction time.

Retained: geometry/search/grouping, clipping, text/number/color math, rounded
GPU style and vector icons, springs, material preview shading, bounded preview
caches, shared glass/refraction, and native bridge sources.

Removed: product-specific softness scaling, BVT/VRM imports, the direct
ShoostFrame renderer dependency. The glass adapter accepts an optional host
presentation callback. The generic layout, binding, lifecycle, widget and panel
host APIs were added in this repository.

Original native exported symbol names retain their `bvt_probe_` ABI names to
avoid changing the extracted binary contract. They do not imply a runtime import
of BVT. Source and compiled-binary fingerprints are validated before loading.

The generated reference sheet uses the existing Effect Layers design language.
The prompt and generation metadata are stored beside the image. It is a visual
specification, not a screenshot proving implementation. No client scene assets,
scene renders, product shaders, credentials or shared guidance were copied.

GPL-3.0-or-later. The copied first-party code is distributed under the GPL license
already declared by its source extension. No third-party MIT-only VRMXT code was
copied; this library is independent of the exporter and renderer dependencies.

## Typography

Unmodified Inter Regular and SemiBold WOFF2 assets are vendored from the official
[Inter repository](https://github.com/rsms/inter), under the SIL Open Font License
1.1. `beyond_ui/assets/fonts/OFL.txt` and `provenance.json` travel with the library.

## BVT theme and context-menu behavior

The [source UI contract audit](SOURCE_UI_CONTRACT.md) records the original
examples, exact source commit/file hashes, reusable behavior and remaining
extraction gaps. BVT-specific data resolution and operators remain host-owned.

## Menu parity v3

New action adapters follow Blender's exact tested-build sources, while appearance
and motion continue through the extracted BVT painter, lens and spring. The
[native audit manifest](../beyond_ui/hosts/menu-native-audit.json) records SHA256s
for both build revisions, including `screen_user_menu.cc`, `MEM_guardedalloc.h`,
`mallocn_intern_function_pointers.hh`, and `scripts/startup/bl_operators/wm.py`.
Favorite removal uses `ED_screen_user_menus_find` / `ED_screen_user_menu_item_remove`
and releases the returned array using the active `mem_freeN_ex` dispatcher with
`DestructorType::NonTrivial`, matching the exact upstream `MEM_delete` path.
Public enum shortcuts use Blender's `wm.context_set_enum` / `wm.context_set_value`.
Only validated RNA paths and quoted known flag identifiers enter flag expressions.

[QA v3](design/qa/context-menu-v3/index.html) preserves source and fixture hashes,
raw captures, runtime results and logs. Its GIF contains actual production-rendered
frames. Existing generated references and earlier QA versions remain immutable.


### Menu completion adapters (v5)

`context_enums.py` uses admitted `pyrna_struct_as_ptr` and
`RNA_property_enum_items`, keeping the GIL for Python callbacks. Copied enum
strings outlive the returned native array; owned arrays use the audited trivial
`mem_freeN_ex` release. Exact 5.1.2/5.2.2 `bpy_rna`, `RNA_access`, `RNA_types`
and `rna_access.cc` source hashes are in `hosts/menu-native-audit.json`.

`_native/menu_context_macos.cpp` uses opaque exported `ui::Layout` context-store
interfaces, compiled libc++ strings and the audited StringRef ABI. It creates a
regionless, buttonless, undrawn block to own a scoped string store; it never uses
a native UI widget as the custom implementation. Nested stores copy their parent,
restore on exit and release both layout and block. `UI_interface_c.hh`,
`UI_interface_layout.hh`, `interface.cc`, `interface_layout.cc`, `BKE_context.hh`
and `context.cc` are audited at both exact revisions already listed above.
The packaged dylib and source have separate SHA-256 admission in
`_native/macos-arm64/menu-context.json`, in addition to exact Blender executable
admission. `tools/build_menu_context.py` is an explicit developer build only;
imports/painting never compile it. No Blender struct offset is read by this shim.

The existing source BVT glass, spring and theme extraction remain shared by inline
menu fields. v5 adds actual implementation frames, without changing prior
reference images or claiming new reference acceptance.


### Numeric properties

The original BVT `begin_edit` / numeric gesture path and `_shoost_canvas_edit.py`
were re-read at commit `ec947ccefc44bd02ad2b175323fa4fc78d60ee4d`; those files had
no local changes. [Audited source hashes](design/qa/numeric-props-v1/bvt-source-audit.json)
record the three-pixel threshold, fractional drag accumulation, Shift precision
and unchanged-text preservation used by this pass. Product-specific transform
ranges and bindings remain outside the library. The renderer, fonts, spring,
theme roles and backdrop implementation are reused.

The new conversion uses Blender's public unit helpers, with [official source
URLs and hashes](design/qa/numeric-props-v1/api-source-audit.json) for the 4.2.0 tag
and exact installed 5.1.2/5.2.2 revisions. No native adapter is introduced. A
bounded unit-token/arithmetic gate precedes public parsing; arbitrary Python
expressions are not forwarded.

### Numeric motion correction and event fields

The numeric v2 revision applies Tyler's explicit 15% amplitude correction to
panel-spanning numeric fields. It retains the existing audited BVT spring formula,
shared glass and theme mapping. The v1 generated/reference and actual QA history
is unchanged; v2 compares verified historical implementation frames with current
frames and does not claim a new generated-reference approval.

Event fields reuse the existing custom field painter and the original BVT-derived
menu/capture path. Capture mode construction is shared with operator shortcuts;
no separate native dialog, menu theme, spring or glass implementation was added.
`docs/design/qa/event-props-v1/api-source-audit.json` identifies exact official
Blender UILayout event/full_event flag sources. Runtime scripts record the tested
public KeyMapItem setter behavior and rollback; arbitrary native variants are not
inferred from the existence of an API flag. New GIFs are actual production renders,
with source/fixture hashes in each capture record.

### Menu text motion v6

The immutable v6 baseline stores the pre-fix `gpu/menus.py` and its SHA. The
fixture enables native BLF batching to reproduce text escaping its GPU transform;
current batched/unbatched animation frames are compared directly. Official
`blf.cc`, `blf_font.cc` and `blf_py_api.cc` snapshots at 4.2.0, ec6e62d40fa9 and
d13f752e3b9c document the public zero-angle ROTATION submission path and are
recorded in `docs/design/qa/context-menu-v6/blf-source-audit.json`. No private
font symbol is used by production; the admitted batch symbols are test-only.
The original BVT context-menu and Canvas deferred-text handling were re-inspected
for ownership, clipping and retained glass behavior. User-requested animation
coverage now includes every menu label/shortcut, including disabled and final rows.
