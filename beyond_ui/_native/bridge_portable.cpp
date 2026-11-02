// SPDX-License-Identifier: GPL-3.0-or-later
// Built against the exact stock Blender headers. No guessed structure offsets.
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include "UI_interface_c.hh"
#if __has_include("UI_interface_layout.hh")
# include "UI_interface_layout.hh"
#endif
#include "ED_keyframing.hh"
#include "WM_api.hh"
#include "WM_types.hh"
#include "BKE_context.hh"
#include "DNA_userdef_types.h"
#include "DEG_depsgraph_build.hh"
#include "GPU_framebuffer.hh"
#include "GPU_viewport.hh"
#include "GPU_texture.hh"
#include "GPU_matrix.hh"
#include "GPU_state.hh"
#include "BLF_api.hh"
#include "RNA_access.hh"
#include "RNA_types.hh"
#include "bui_screen_declarations.hh"

#ifdef _WIN32
# define EXPORT extern "C" __declspec(dllexport)
#else
# define EXPORT extern "C" __attribute__((visibility("default")))
#endif
#if BUI_FAMILY >= 51
using namespace blender;
using Layout = ui::Layout;
using Block = ui::Block;
using Button = ui::Button;
#else
using Layout = uiLayout;
using Block = uiBlock;
using Button = uiBut;
#endif
struct _object;
#if BUI_FAMILY >= 51
namespace blender { const PointerRNA *pyrna_struct_as_ptr(_object *, const StructRNA *); }
#elif BUI_PYRNA_C
extern "C" const PointerRNA *pyrna_struct_as_ptr(_object *, const StructRNA *);
#else
const PointerRNA *pyrna_struct_as_ptr(_object *, const StructRNA *);
#endif

static bool enabled = false;
using Callback = void (*)(uint64_t, int, int, int, int);
static Callback callback = nullptr;
static void *free_slot = nullptr;
EXPORT int bui_bridge_abi() { return 1; }
EXPORT int bvt_probe_initialize(int family) {
  enabled = family == BUI_FAMILY; return enabled ? BUI_FAMILY : 0;
}
EXPORT void bui_free_slot(void *slot) { free_slot = slot; }
EXPORT void bui_free(void *pointer, int kind) {
  if (!pointer || !free_slot) return;
#if BUI_FREE_TYPED
  (*static_cast<void (**)(void *, int)>(free_slot))(pointer, kind);
#else
  (*static_cast<void (**)(void *)>(free_slot))(pointer);
#endif
}
EXPORT void bvt_probe_callback(Callback value) { callback = value; }
static void present(uint64_t token, rcti *rect) {
  if (!callback || !rect) return;
  int clip[4], viewport[4]; GPU_scissor_get(clip); GPU_viewport_size_get_i(viewport);
  GPU_scissor(viewport[0], viewport[1], viewport[2], viewport[3]);
  BLF_batch_draw_end(); GPU_scissor(clip[0], clip[1], clip[2], clip[3]);
  BLF_batch_draw_begin(); callback(token, rect->xmin, rect->ymin, rect->xmax, rect->ymax);
}
EXPORT int bvt_probe_reserve(Layout *layout, int width, int height, uint64_t token) {
  if (!enabled || !layout || width < 1 || height < 1 || width > 16000 || height > 16000) return 0;
#if BUI_FAMILY >= 51
  auto *block = layout->block(); ui::block_layout_set_current(block, layout);
  ui::uiDefBut(block, ui::ButtonType::Extra, "", 0, 0, short(width), short(height), nullptr, 0, 0, std::nullopt);
  ui::button_func_drawextra_set(block, [token](const bContext *, rcti *rect) { present(token, rect); });
#else
# if BUI_FAMILY >= 50
  auto *block = layout->block(); blender::ui::block_layout_set_current(block, layout);
# else
  auto *block = uiLayoutGetBlock(layout); UI_block_layout_set_current(block, layout);
# endif
# if BUI_OPTIONAL_LABELS
  uiDefBut(block, UI_BTYPE_EXTRA, 0, "", 0, 0, short(width), short(height), nullptr, 0, 0, std::nullopt);
# else
  uiDefBut(block, UI_BTYPE_EXTRA, 0, "", 0, 0, short(width), short(height), nullptr, 0, 0, nullptr);
# endif
# if BUI_FUNCTION_DRAW
  UI_but_func_drawextra_set(block, [token](const bContext *, rcti *rect) { present(token, rect); });
# else
  UI_but_func_drawextra_set(block, [](const bContext *, void *, void *id, void *, rcti *rect) {
    present(uint64_t(id), rect); }, reinterpret_cast<void *>(token), nullptr);
# endif
#endif
  return 1;
}
EXPORT void *bvt_probe_framebuffer() { return enabled ? GPU_framebuffer_active_get() : nullptr; }
EXPORT int bvt_probe_copy_framebuffer(void *opaque) {
  auto *destination = GPU_framebuffer_active_get();
  auto *source = static_cast<decltype(destination)>(opaque);
  if (!enabled || !source || !destination || source == destination) return 0;
  GPU_framebuffer_blit(source, 0, destination, 0, GPU_COLOR_BIT); return 1;
}
EXPORT int bvt_probe_draw_viewport(ARegion *region, int x, int y) {
  if (!enabled || !region) return 0;
  auto *viewport = WM_draw_region_get_viewport(region); if (!viewport) return 0;
  const int view = GPU_viewport_active_view_get(viewport); if (view < 0 || view > 1) return 0;
  auto *texture = GPU_viewport_color_texture(viewport, view); if (!texture) return 0;
  const rcti rect = {x, x + GPU_texture_width(texture) - 1, y, y + GPU_texture_height(texture) - 1};
  GPU_matrix_push(); GPU_matrix_translate_2f(GLA_PIXEL_OFS, GLA_PIXEL_OFS);
  GPU_viewport_draw_to_screen(viewport, view, &rect); GPU_matrix_pop(); return 1;
}
EXPORT float bvt_probe_region_alpha(ARegion *region) { return enabled && region ? ED_region_blend_alpha(region) : 1.0f; }
using WindowCallback = void (*)(const wmWindow *, void *);
static WindowCallback window_callback = nullptr;
EXPORT void bvt_probe_window_callback(WindowCallback value) { window_callback = value; }
EXPORT void *bvt_probe_window_add(wmWindow *window) {
  if (!enabled || !window || !BLI_thread_is_main()) return nullptr;
  return WM_draw_cb_activate(window, [](const wmWindow *w, void *data) {
    if (window_callback) window_callback(w, data); }, nullptr);
}
EXPORT void bvt_probe_window_remove(wmWindow *window, void *handle) {
  if (enabled && window && handle && BLI_thread_is_main()) WM_draw_cb_exit(window, handle);
}

// Context actions: all object layouts below come from this build's own headers.
EXPORT void bui_driver_new(ID *id, const char *path, const char *name) { ANIM_copy_as_driver(id, path, name); }
EXPORT bool bui_driver_available() { return ANIM_driver_can_paste(); }
EXPORT bool bui_driver_copy(ReportList *r, ID *id, const char *path, int index, short flags) { return ANIM_copy_driver(r,id,path,index,flags); }
EXPORT bool bui_driver_paste(ReportList *r, ID *id, const char *path, int index, short flags) { return ANIM_paste_driver(r,id,path,index,flags); }
EXPORT void bui_relations(Main *main) { DEG_relations_tag_update(main); }
EXPORT bUserMenu *bui_favorites(bContext *context) { return ED_screen_user_menu_ensure(context); }
EXPORT void *bui_favorite_items(bUserMenu *menu) { return menu ? &menu->items : nullptr; }
using Items = decltype(bUserMenu::items);
EXPORT void *bui_find_property(Items *items, const char *path, const char *name, int index) { return ED_screen_user_menu_item_find_prop(items,path,name,index); }
EXPORT void bui_add_property(Items *items, const char *label, const char *path, const char *name, int index) { ED_screen_user_menu_item_add_prop(items,label,path,name,index); }
EXPORT void *bui_find_favorites(const bContext *context, unsigned *count) { return ED_screen_user_menus_find(context,count); }
EXPORT void bui_remove_favorite(Items *items, bUserMenuItem *item) { ED_screen_user_menu_item_remove(items,item); }
EXPORT wmKeyMap *bui_guess_keymap(const bContext *context, const char *name) { return WM_keymap_guess_opname(context,name); }
EXPORT wmOperatorType *bui_operator_type(const char *name, bool quiet) { return WM_operatortype_find(name,quiet); }
#if BUI_FAMILY >= 50
using Invocation = blender::wm::OpCallContext;
#else
using Invocation = wmOperatorCallContext;
#endif
EXPORT void *bui_find_operator(Items *items, const wmOperatorType *op, IDProperty *props, const char *name, int invocation) { return ED_screen_user_menu_item_find_operator(items,op,props,name,Invocation(invocation)); }
EXPORT void bui_add_operator(Items *items, const char *label, const wmOperatorType *op, const IDProperty *props, const char *name, int invocation) { ED_screen_user_menu_item_add_operator(items,label,op,props,name,Invocation(invocation)); }
EXPORT const PointerRNA *bui_rna_pointer(_object *object, const StructRNA *type) { return pyrna_struct_as_ptr(object,type); }
EXPORT PropertyRNA *bui_rna_find(PointerRNA *owner, const char *name) { return RNA_struct_find_property(owner,name); }
EXPORT void bui_enum_items(bContext *context, PointerRNA *owner, PropertyRNA *prop, const EnumPropertyItem **items, int *count, bool *owned) { RNA_property_enum_items(context,owner,prop,items,count,owned); }
EXPORT void *bui_py_dict(const bContext *context) { return CTX_py_dict_get(context); }
EXPORT void bui_py_push(bContext *context, bContext_PyState *state, void *value) { CTX_py_state_push(context,state,value); }
EXPORT void bui_py_pop(bContext *context, bContext_PyState *state) { CTX_py_state_pop(context,state); }
EXPORT size_t bui_py_state_size() { return sizeof(bContext_PyState); }

struct Scope { bContext *context; Block *block; const bContextStore *previous, *current; };
static int active = 0;
static Block *new_block(bContext *context) {
#if BUI_FAMILY >= 51
  return ui::block_begin(context,nullptr,"Beyond UI context scope",ui::EmbossType::None);
#elif BUI_ENUM_EMBOSS
  return UI_block_begin(context,nullptr,"Beyond UI context scope",blender::ui::EmbossType::None);
#else
  return UI_block_begin(context,nullptr,"Beyond UI context scope",UI_EMBOSS_NONE);
#endif
}
static Layout *new_layout(Block *block) {
#if BUI_FAMILY >= 51
  return &ui::block_layout(block,ui::LayoutDirection::Vertical,ui::LayoutType::Panel,0,0,1,1,0,ui::style_get());
#elif BUI_FAMILY >= 50
  return &blender::ui::block_layout(block,blender::ui::LayoutDirection::Vertical,blender::ui::LayoutType::Panel,0,0,1,1,0,UI_style_get());
#else
  return UI_block_layout(block,UI_LAYOUT_VERTICAL,UI_LAYOUT_PANEL,0,0,1,1,0,UI_style_get());
#endif
}
static void free_block(Scope *scope) {
#if BUI_FAMILY >= 51
  ui::block_layout_free(scope->block); ui::block_free(scope->context,scope->block);
#elif BUI_FAMILY >= 50
  blender::ui::block_layout_free(scope->block); UI_block_free(scope->context,scope->block);
#else
  UI_block_layout_free(scope->block); UI_block_free(scope->context,scope->block);
#endif
}
static void copy_context(Layout *layout, const bContextStore *context) {
  if (!context) return;
#if BUI_FAMILY >= 50
  layout->context_copy(context);
#else
  uiLayoutContextCopy(layout,context);
#endif
}
static const bContextStore *get_store(Layout *layout) {
#if BUI_FAMILY >= 51
  return layout->context();
#elif BUI_FAMILY >= 50
  return layout->context_store();
#else
  return uiLayoutGetContextStore(layout);
#endif
}
EXPORT int beyond_context_init() { return enabled && BLI_thread_is_main(); }
EXPORT int beyond_context_active() { return active; }
EXPORT void *beyond_context_enter(bContext *context, const char **keys, const char **values, int count) {
  if (!enabled || !context || !BLI_thread_is_main() || count<1 || count>64 || active>=8) return nullptr;
  auto *scope=new Scope{context,nullptr,CTX_store_get(context),nullptr};
  try {
    scope->block=new_block(context); auto *layout=new_layout(scope->block); copy_context(layout,scope->previous);
    for (int i=0;i<count;++i) {
#if BUI_FAMILY >= 50
      layout->context_string_set(keys[i],values[i]);
#else
      uiLayoutSetContextString(layout,keys[i],values[i]);
#endif
    }
    scope->current=get_store(layout); CTX_store_set(context,scope->current); ++active; return scope;
  } catch (...) { if (scope->block) free_block(scope); delete scope; return nullptr; }
}
EXPORT void *beyond_context_property_enter(bContext *context, PointerRNA *owner, const char *name) {
  if (!enabled || !context || !owner || !name || !BLI_thread_is_main() || active>=8) return nullptr;
  auto *scope=new Scope{context,nullptr,CTX_store_get(context),nullptr};
  try {
    scope->block=new_block(context); auto *layout=new_layout(scope->block); copy_context(layout,scope->previous);
#if BUI_FAMILY >= 51
    auto *button=ui::uiDefButR(scope->block,ui::ButtonType::Num,std::nullopt,0,0,1,1,owner,name,-1,0,1,std::nullopt);
#elif BUI_OPTIONAL_LABELS
    auto *button=uiDefButR(scope->block,UI_BTYPE_NUM,0,std::nullopt,0,0,1,1,owner,name,-1,0,1,std::nullopt);
#else
    auto *button=uiDefButR(scope->block,UI_BTYPE_NUM,0,nullptr,0,0,1,1,owner,name,-1,0,1,nullptr);
#endif
    if (!button) { free_block(scope); delete scope; return nullptr; }
#if BUI_FAMILY >= 50
    layout->context_set_from_but(button);
#else
    uiLayoutSetContextFromBut(layout,button);
#endif
    scope->current=get_store(layout); CTX_store_set(context,scope->current); ++active; return scope;
  } catch (...) { if (scope->block) free_block(scope); delete scope; return nullptr; }
}
EXPORT void beyond_context_exit(void *opaque, int restore) {
  auto *scope=static_cast<Scope *>(opaque); if (!scope) return;
  if (CTX_store_get(scope->context)==scope->current) CTX_store_set(scope->context,restore?scope->previous:nullptr);
  free_block(scope); delete scope; --active;
}
