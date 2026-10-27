// Experimental macOS/libc++ ABI probe, NOT a shipped Blender integration.
// Source contracts: Blender d13f752e3b9c, ec6e62d40fa9 and d0cbe84903e8, UI_interface_c.hh,
// BLI_string_ref.hh, DNA_vec_types.h. No Blender struct offsets are accessed.
#include <cstdint>
#include <dlfcn.h>
#include <functional>
#include <optional>

struct StringRefABI { const char *data; int64_t size; };
struct ButtonTypeABI { int8_t type; uint8_t pointer_type; char bit; };
struct Rect { int xmin, xmax, ymin, ymax; };
using Callback = void (*)(uint64_t, int, int, int, int);
using Draw = std::function<void(const void *, Rect *)>;
static Callback callback = nullptr;
static void *(*get_block)(void *) = nullptr;
static void (*set_current)(void *, void *) = nullptr;
static void (*set_draw)(void *, Draw) = nullptr;
static void *create_button = nullptr;
static int family = 0;
static void *(*active_framebuffer)() = nullptr;
static void (*blit_framebuffer)(void *, int, void *, int, int) = nullptr;
static void *(*region_viewport)(void *) = nullptr;
static int (*viewport_view)(void *) = nullptr;
static void *(*viewport_color)(void *, int) = nullptr;
static int (*texture_width)(const void *) = nullptr;
static int (*texture_height)(const void *) = nullptr;
static void (*draw_viewport)(void *, int, const Rect *) = nullptr;
static float (*region_blend_alpha)(void *) = nullptr;
using WindowCallback = void (*)(const void *, void *);
static WindowCallback window_callback = nullptr;
static void *(*window_activate)(void *, WindowCallback, void *) = nullptr;
static void (*window_exit)(void *, void *) = nullptr;
static void (*metal_ensure)(void *) = nullptr;
static void (*metal_crop)(void *, unsigned, unsigned, unsigned, void *,
                          unsigned, unsigned, unsigned, unsigned, unsigned, int) = nullptr;

extern "C" int bvt_probe_initialize(int requested_family)
{
  // Names are ABI-specific and capability-checked before any native call.
  const bool legacy = requested_family == 42;
  if (!legacy && requested_family != 51 && requested_family != 52) return 0;
  get_block = reinterpret_cast<decltype(get_block)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z16uiLayoutGetBlockP8uiLayout" : "_ZNK7blender2ui6Layout5blockEv"));
  set_current = reinterpret_cast<decltype(set_current)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z27UI_block_layout_set_currentP7uiBlockP8uiLayout" :
      "_ZN7blender2ui24block_layout_set_currentEPNS0_5BlockEPNS0_6LayoutE"));
  set_draw = reinterpret_cast<decltype(set_draw)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z25UI_but_func_drawextra_setP7uiBlockNSt3__18functionIFvPK8bContextP4rctiEEE" :
      "_ZN7blender2ui25button_func_drawextra_setEPNS0_5BlockENSt3__18functionIFvPKNS_8bContextEPNS_4rctiEEEE"));
  create_button = dlsym(RTLD_DEFAULT, legacy ?
      "_Z8uiDefButP7uiBlockiiN7blender9StringRefEiissPvffPKc" :
      "_ZN7blender2ui8uiDefButEPNS0_5BlockENS0_25ButtonTypeWithPointerTypeENS_9StringRefEiissPvffNSt3__18optionalIS4_EE");
  family = get_block && set_current && set_draw && create_button ? requested_family : 0;
  // Optional GPU-only UI backdrop copy. Opaque pointers only, no struct reads.
  active_framebuffer = reinterpret_cast<decltype(active_framebuffer)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z26GPU_framebuffer_active_getv" : "_ZN7blender26GPU_framebuffer_active_getEv"));
  blit_framebuffer = reinterpret_cast<decltype(blit_framebuffer)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z20GPU_framebuffer_blitP14GPUFrameBufferiS0_i19eGPUFrameBufferBits" :
      "_ZN7blender20GPU_framebuffer_blitEPNS_3gpu11FrameBufferEiS2_iNS_18GPUFrameBufferBitsE"));
  region_viewport = reinterpret_cast<decltype(region_viewport)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z27WM_draw_region_get_viewportP7ARegion" : "_ZN7blender27WM_draw_region_get_viewportEPNS_7ARegionE"));
  viewport_view = reinterpret_cast<decltype(viewport_view)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z28GPU_viewport_active_view_getP11GPUViewport" : "_ZN7blender28GPU_viewport_active_view_getEPNS_11GPUViewportE"));
  viewport_color = reinterpret_cast<decltype(viewport_color)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z26GPU_viewport_color_textureP11GPUViewporti" : "_ZN7blender26GPU_viewport_color_textureEPNS_11GPUViewportEi"));
  texture_width = reinterpret_cast<decltype(texture_width)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z17GPU_texture_widthPK10GPUTexture" : "_ZN7blender17GPU_texture_widthEPKNS_3gpu7TextureE"));
  texture_height = reinterpret_cast<decltype(texture_height)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z18GPU_texture_heightPK10GPUTexture" : "_ZN7blender18GPU_texture_heightEPKNS_3gpu7TextureE"));
  draw_viewport = reinterpret_cast<decltype(draw_viewport)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z27GPU_viewport_draw_to_screenP11GPUViewportiPK4rcti" : "_ZN7blender27GPU_viewport_draw_to_screenEPNS_11GPUViewportEiPKNS_4rctiE"));
  region_blend_alpha = reinterpret_cast<decltype(region_blend_alpha)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z21ED_region_blend_alphaP7ARegion" : "_ZN7blender21ED_region_blend_alphaEPNS_7ARegionE"));
  window_activate = reinterpret_cast<decltype(window_activate)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z19WM_draw_cb_activateP8wmWindowPFvPKS_PvES3_" :
      "_ZN7blender19WM_draw_cb_activateEPNS_8wmWindowEPFvPKS0_PvES4_"));
  window_exit = reinterpret_cast<decltype(window_exit)>(dlsym(RTLD_DEFAULT, legacy ?
      "_Z15WM_draw_cb_exitP8wmWindowPv" : "_ZN7blender15WM_draw_cb_exitEPNS_8wmWindowEPv"));
  metal_ensure = reinterpret_cast<decltype(metal_ensure)>(dlsym(RTLD_DEFAULT,
      "_ZN7blender3gpu14MTLFrameBuffer31ensure_attachments_and_viewportEv"));
  metal_crop = reinterpret_cast<decltype(metal_crop)>(dlsym(RTLD_DEFAULT, legacy ?
      "_ZN7blender3gpu14MTLFrameBuffer4blitEjjjPS1_jjjjj19eGPUFrameBufferBits" :
      "_ZN7blender3gpu14MTLFrameBuffer4blitEjjjPS1_jjjjjNS_18GPUFrameBufferBitsE"));
  return family;
}

// After all region textures complete, before Blender's floating native menus.
// The trampoline can be disabled even if Blender still owns a window handle.
extern "C" int bvt_probe_has_region_alpha() { return region_blend_alpha != nullptr; }
extern "C" float bvt_probe_region_alpha(void *region)
{
  // Borrow the live RNA pointer for this call only. Blender owns the timer,
  // easing input and parent-region behavior; never inspect timer struct offsets.
  return family && region && region_blend_alpha ? region_blend_alpha(region) : 1.0f;
}
extern "C" void bvt_probe_window_callback(WindowCallback fn) { window_callback = fn; }
extern "C" void *bvt_probe_window_add(void *window)
{
  if (!family || !window || !window_activate || !window_exit) return nullptr;
  return window_activate(window, [](const void *win, void *data) {
    if (window_callback) window_callback(win, data);
  }, nullptr);
}
extern "C" void bvt_probe_window_remove(void *window, void *handle)
{
  if (family && window && handle && window_exit) window_exit(window, handle);
}

// Caller MUST capability-check gpu.platform.backend_type_get() == "METAL".
// Exact audited method ABI; no MTL object layouts or attachment fields read.
extern "C" int bvt_probe_crop_framebuffer(void *source, int x, int y, int w, int h)
{
  if (!family || !source || !active_framebuffer || !metal_ensure || !metal_crop ||
      x < 0 || y < 0 || w < 1 || h < 1) return 0;
  void *destination = active_framebuffer();
  if (!destination || destination == source) return 0;
  metal_ensure(source); metal_ensure(destination);
  metal_crop(source, 0, unsigned(x), unsigned(y), destination, 0, 0, 0,
             unsigned(w), unsigned(h), 1);
  return 1;
}

// Re-present Blender's completed color/overlay textures with its own display
// transform. This never evaluates or renders a scene, and borrows no pointers
// beyond this call. The caller's small target/projection clips the desired crop.
extern "C" int bvt_probe_draw_viewport(void *region, int x, int y)
{
  if (!family || !region || !region_viewport || !viewport_view || !viewport_color ||
      !texture_width || !texture_height || !draw_viewport) return 0;
  void *viewport = region_viewport(region);
  if (!viewport) return 0;
  const int view = viewport_view(viewport);
  if (view < 0 || view > 1) return 0;
  void *texture = viewport_color(viewport, view);
  if (!texture) return 0;
  const Rect rect = {x, x + texture_width(texture) - 1, y, y + texture_height(texture) - 1};
  draw_viewport(viewport, view, &rect);
  return 1;
}

// Source is borrowed only across the caller's synchronous destination bind.
// Never retain it between UI callbacks or read any pixels on the CPU.
extern "C" void *bvt_probe_framebuffer()
{
  return family && active_framebuffer && blit_framebuffer ? active_framebuffer() : nullptr;
}
extern "C" int bvt_probe_copy_framebuffer(void *source)
{
  if (!family || !source || !active_framebuffer || !blit_framebuffer) return 0;
  void *destination = active_framebuffer();
  if (!destination || destination == source) return 0;
  blit_framebuffer(source, 0, destination, 0, 1); // GPU_COLOR_BIT in every audited build.
  return 1;
}

extern "C" void bvt_probe_callback(Callback fn) { callback = fn; }

extern "C" int bvt_probe_reserve(void *layout, int width, int height, uint64_t token)
{
  if (!family || !layout || width < 1 || height < 1 || width > 16000 || height > 16000)
    return 0;
  void *block = get_block(layout);
  if (!block) return 0;
  set_current(block, layout);
  if (family == 42) {
    using Create = void *(*)(void *, int, int, StringRefABI, int, int, short,
                             short, void *, float, float, const char *);
    reinterpret_cast<Create>(create_button)(block, 42 << 9, 0, {"", 0}, 0, 0,
                                             short(width), short(height), nullptr, 0, 0, "");
  }
  else {
    using Create = void *(*)(void *, ButtonTypeABI, StringRefABI, int, int, short,
                             short, void *, float, float, std::optional<StringRefABI>);
    reinterpret_cast<Create>(create_button)(block, {int8_t(family == 51 ? 34 : 35), 0, 0}, {"", 0}, 0, 0,
                                             short(width), short(height), nullptr, 0, 0, std::nullopt);
  }
  // Captures only a value, never a Python callable or a retained Layout pointer.
  // Disable the global callback BEFORE removing the Python callback reference.
  set_draw(block, [token](const void *, Rect *rect) {
    if (callback && rect) callback(token, rect->xmin, rect->ymin, rect->xmax, rect->ymax);
  });
  return 1;
}
