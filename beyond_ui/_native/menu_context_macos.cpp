// Exact macOS arm64/libc++ context-string adapter for ec6e62d40fa9/d13f752e3b9c.
// Uses only audited opaque UI/Context interfaces; never reads struct offsets.
#include <cstdint>
#include <cstring>
#include <string>
#include <dlfcn.h>

struct StringRef { const char *data; int64_t size; };
using Begin = void *(*)(const void *, void *, std::string, uint8_t);
using Layout = void *(*)(void *, int8_t, int8_t, int, int, int, int, int, const void *);
static Begin begin_block;
static Layout create_layout;
static void (*free_layout)(void *);
static void (*free_block)(const void *, void *);
static const void *(*style)();
static void (*copy_context)(void *, const void *);
static void (*set_string)(void *, StringRef, StringRef);
static const void *(*layout_context)(const void *);
static const void *(*get_context)(const void *);
static void (*set_context)(void *, const void *);
struct Scope { void *context, *block; const void *previous, *current; };
static int active = 0;

extern "C" int beyond_context_init() {
#define LOAD(var, name) var = reinterpret_cast<decltype(var)>(dlsym(RTLD_DEFAULT, name))
  LOAD(begin_block, "_ZN7blender2ui11block_beginEPKNS_8bContextEPNS_7ARegionENSt3__112basic_stringIcNS6_11char_traitsIcEENS6_9allocatorIcEEEENS0_10EmbossTypeE");
  LOAD(create_layout, "_ZN7blender2ui12block_layoutEPNS0_5BlockENS0_15LayoutDirectionENS0_10LayoutTypeEiiiiiPKNS_7uiStyleE");
  LOAD(free_layout, "_ZN7blender2ui17block_layout_freeEPNS0_5BlockE");
  LOAD(free_block, "_ZN7blender2ui10block_freeEPKNS_8bContextEPNS0_5BlockE");
  LOAD(style, "_ZN7blender2ui9style_getEv");
  LOAD(copy_context, "_ZN7blender2ui6Layout12context_copyEPKNS_13bContextStoreE");
  LOAD(set_string, "_ZN7blender2ui6Layout18context_string_setENS_9StringRefES2_");
  LOAD(layout_context, "_ZNK7blender2ui6Layout7contextEv");
  LOAD(get_context, "_ZN7blender13CTX_store_getEPKNS_8bContextE");
  LOAD(set_context, "_ZN7blender13CTX_store_setEPNS_8bContextEPKNS_13bContextStoreE");
#undef LOAD
  return begin_block && create_layout && free_layout && free_block && style && copy_context && set_string && layout_context && get_context && set_context;
}
extern "C" void *beyond_context_enter(void *context, const char **keys, const char **values, int count) {
  if (!begin_block || !context || count < 1 || count > 64 || active >= 8) return nullptr;
  auto *scope = new Scope{context, nullptr, get_context(context), nullptr};
  try {
    // A region-less, button-less block owns the store. Never attach/draw it.
    scope->block = begin_block(context, nullptr, "Beyond UI context scope", 1);
    auto *layout = create_layout(scope->block, 1, 0, 0, 0, 1, 1, 0, style());
    if (scope->previous) copy_context(layout, scope->previous);
    for (int i = 0; i < count; ++i) {
      set_string(layout, {keys[i], int64_t(std::strlen(keys[i]))}, {values[i], int64_t(std::strlen(values[i]))});
    }
    scope->current = layout_context(layout);
    set_context(context, scope->current);
    ++active;
    return scope;
  } catch (...) {
    if (scope->block) { free_layout(scope->block); free_block(context, scope->block); }
    delete scope;
    return nullptr;
  }
}
extern "C" void beyond_context_exit(void *opaque, int restore) {
  auto *scope = static_cast<Scope *>(opaque);
  if (!scope) return;
  // Do not overwrite context changes made by native window/file lifecycle code.
  if (get_context(scope->context) == scope->current)
    set_context(scope->context, restore ? scope->previous : nullptr);
  free_layout(scope->block);
  free_block(scope->context, scope->block);
  delete scope;
  --active;
}
extern "C" int beyond_context_active() { return active; }
