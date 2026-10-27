// SPDX-License-Identifier: GPL-2.0-or-later
// Exact-build Windows/MSVC ABI adapter. The Darwin implementation is separate.
#include "UI_interface_c.hh"
#include "UI_interface_layout.hh"
#include "ED_screen.hh"
#include "WM_api.hh"
#include "GPU_framebuffer.hh"
#include "GPU_viewport.hh"
#include "GPU_texture.hh"
#include "GPU_matrix.hh"
#include "GPU_platform.hh"
#include "BLI_threads.h"
#include "ED_keyframing.hh"
#include "DEG_depsgraph_build.hh"
#include "BKE_global.hh"
static blender::Global *ui_global = nullptr;
static void *ui_host_free = nullptr;
#define G (*ui_global)
#include "vk_context.hh"
#include "vk_framebuffer.hh"
#include "vk_texture.hh"

using namespace blender;
#define EXPORT extern "C" __declspec(dllexport)
EXPORT size_t npr_windows_data_size(unsigned index)
{
  return index == 0 ? sizeof(Global) : index == 1 ? sizeof(void *) : 0;
}
EXPORT int npr_windows_data_initialize(void *global, void *host_free)
{
  if (!global || !host_free || (ui_global && (ui_global != global || ui_host_free != host_free))) return 0;
  ui_global = static_cast<Global *>(global);
  ui_host_free = host_free;
  return 1;
}
using Callback = void (*)(uint64_t, int, int, int, int);
static Callback callback = nullptr;
static bool enabled = false;
EXPORT int npr_deformation_bridge_abi() { return 2; }
EXPORT int bvt_probe_initialize(int family) { enabled = family == 52; return enabled ? 52 : 0; }
EXPORT void bvt_probe_callback(Callback fn) { callback = fn; }
EXPORT int bvt_probe_has_region_alpha() { return 1; }
EXPORT float bvt_probe_region_alpha(ARegion *region)
{
  return enabled && region ? ED_region_blend_alpha(region) : 1.0f;
}
EXPORT int bvt_probe_reserve(ui::Layout *layout, int width, int height, uint64_t token)
{
  if (!enabled || !layout || width < 1 || height < 1 || width > 16000 || height > 16000) return 0;
  ui::Block *block = layout->block();
  if (!block) return 0;
  ui::block_layout_set_current(block, layout);
  ui::uiDefBut(block, ui::ButtonType::Extra, "", 0, 0, short(width), short(height), nullptr, 0, 0, std::nullopt);
  ui::button_func_drawextra_set(block, [token](const bContext *, rcti *rect) {
    if (callback && rect) callback(token, rect->xmin, rect->ymin, rect->xmax, rect->ymax);
  });
  return 1;
}
EXPORT gpu::FrameBuffer *bvt_probe_framebuffer()
{
  return enabled ? GPU_framebuffer_active_get() : nullptr;
}
// Borrow a host attachment only for this synchronous draw. No Python wrapper,
// retained host texture or framebuffer readback is created.
EXPORT int bvt_probe_bind_framebuffer_color(gpu::FrameBuffer *frame, int slot)
{
  if (!enabled || !frame || GPU_backend_get_type() != GPU_BACKEND_VULKAN ||
      frame == GPU_framebuffer_active_get() || slot < -1 || slot > 15) return 0;
  gpu::Texture *texture = frame->color_tex(0);
  if (!texture) return 0;
  if (slot == -1) GPU_texture_unbind(texture);
  else GPU_texture_bind(texture, slot);
  return 1;
}
EXPORT int bvt_probe_copy_framebuffer(gpu::FrameBuffer *source)
{
  if (!enabled || !source) return 0;
  gpu::FrameBuffer *destination = GPU_framebuffer_active_get();
  if (!destination || destination == source) return 0;
  GPU_framebuffer_blit(source, 0, destination, 0, GPU_COLOR_BIT);
  return 1;
}
EXPORT int bvt_probe_draw_viewport(ARegion *region, int x, int y)
{
  if (!enabled || !region) return 0;
  GPUViewport *viewport = WM_draw_region_get_viewport(region);
  if (!viewport) return 0;
  const int view = GPU_viewport_active_view_get(viewport);
  if (view < 0 || view > 1) return 0;
  gpu::Texture *texture = GPU_viewport_color_texture(viewport, view);
  if (!texture) return 0;
  const rcti rect = {x, x + GPU_texture_width(texture) - 1, y, y + GPU_texture_height(texture) - 1};
  // Blender's screen presenter adds GLA_PIXEL_OFS to texture coordinates
  // because wmOrtho has that origin. Our private target uses an unshifted
  // projection: restore the matching model translation before resampling it.
  GPU_matrix_push();
  GPU_matrix_translate_2f(GLA_PIXEL_OFS, GLA_PIXEL_OFS);
  GPU_viewport_draw_to_screen(viewport, view, &rect);
  GPU_matrix_pop();
  return 1;
}

// One window callback after region textures, before native floating menus.
using WindowCallback = void (*)(const wmWindow *, void *);
static WindowCallback window_callback = nullptr;
EXPORT void bvt_probe_window_callback(WindowCallback fn) { window_callback = fn; }
EXPORT void *bvt_probe_window_add(wmWindow *window)
{
  if (!enabled || !window || !BLI_thread_is_main()) return nullptr;
  return WM_draw_cb_activate(window, [](const wmWindow *win, void *data) {
    if (window_callback) window_callback(win, data);
  }, nullptr);
}
EXPORT void bvt_probe_window_remove(wmWindow *window, void *handle)
{
  if (enabled && window && handle && BLI_thread_is_main()) WM_draw_cb_exit(window, handle);
}

// The exact-build Vulkan counterpart of the Metal crop. Borrow both textures
// for this call and enqueue their resource dependencies in Blender's graph.
// No host readback, explicit submit/wait, or retained raw attachment pointer.
EXPORT int bvt_probe_crop_framebuffer(gpu::FrameBuffer *source, int x, int y, int w, int h)
{
  if (!enabled || !source || !BLI_thread_is_main() ||
      GPU_backend_get_type() != GPU_BACKEND_VULKAN || x < 0 || y < 0 || w < 1 || h < 1)
    return 0;
  auto *context = gpu::VKContext::get();
  auto *destination = GPU_framebuffer_active_get();
  if (!context || !destination || source == destination) return 0;
  auto *src = static_cast<gpu::VKTexture *>(source->color_tex(0));
  auto *dst = static_cast<gpu::VKTexture *>(destination->color_tex(0));
  if (!src || !dst || src == dst || x > src->width_get() - w ||
      y > src->height_get() - h || w > dst->width_get() || h > dst->height_get()) return 0;
  gpu::render_graph::VKBlitImageNode::CreateInfo copy = {};
  copy.src_image = src->vk_image_handle();
  copy.dst_image = dst->vk_image_handle();
  copy.filter = VK_FILTER_NEAREST;
  copy.region.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
  copy.region.dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
  copy.region.srcOffsets[0] = {x, y, 0};
  copy.region.srcOffsets[1] = {x + w, y + h, 1};
  copy.region.dstOffsets[0] = {0, 0, 0};
  copy.region.dstOffsets[1] = {w, h, 1};
  context->render_graph().add_node(copy);
  return 1;
}

// Native driver clipboard uses Blender's own copy buffer. It is a cold user
// action; no button state, struct offsets or private clipboard serialization.
EXPORT void bvt_driver_new(ID *id, const char *path, const char *name)
{
  if (enabled && BLI_thread_is_main() && id && path && name) ANIM_copy_as_driver(id, path, name);
}
EXPORT bool bvt_driver_available()
{
  return enabled && BLI_thread_is_main() && ANIM_driver_can_paste();
}
EXPORT bool bvt_driver_copy(ReportList *reports, ID *id, const char *path, int index, short flags)
{
  return enabled && BLI_thread_is_main() && id && path &&
         ANIM_copy_driver(reports, id, path, index, flags);
}
EXPORT bool bvt_driver_paste(ReportList *reports, ID *id, const char *path, int index, short flags)
{
  return enabled && BLI_thread_is_main() && id && path &&
         ANIM_paste_driver(reports, id, path, index, flags);
}
EXPORT void bvt_driver_relations(Main *main)
{
  if (enabled && BLI_thread_is_main() && main) DEG_relations_tag_update(main);
}
