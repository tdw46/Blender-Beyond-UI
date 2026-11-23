"""Resolve author-owned ImagePreviews and upload visible gallery tiles on demand."""
from collections import OrderedDict

from .base import Widget


class PreviewIcons:
    def __init__(self, provider):
        self.provider = provider
        self.index = {}
        self.textures = OrderedDict()
        self.errors = {}
        self.collections_key = None
        self._warm_request = None
        self._warm_callback = None

    def _preview(self, key):
        collections = tuple(self.provider())
        stamp = tuple((id(c), len(c)) for c in collections)
        if stamp != self.collections_key or key not in self.index:
            self.index = {p.icon_id: p for collection in collections for p in collection.values()}
            self.collections_key = stamp
        return self.index.get(key)

    @staticmethod
    def _upload(preview, *, square=False, letterbox=None):
        import gpu
        import numpy as np
        width, height = preview.image_size
        if not width or not height:
            return None
        aspect = width/height
        pixels = preview.image_pixels
        if width*height > 4096**2:
            width,height = preview.icon_size
            pixels = preview.icon_pixels
        if not width or not height:
            return None
        packed = np.empty(width*height, dtype=np.int32)
        pixels.foreach_get(packed)
        rgba = packed.view(np.uint8).reshape(height,width,4)
        if square and letterbox is None:
            side = min(width, height)
            x, y = (width-side)//2, (height-side)//2
            rgba = rgba[y:y+side, x:x+side]
            aspect = 1.0
        step = max(1,(max(rgba.shape[:2])+383)//384)
        rgba = np.ascontiguousarray(rgba[::step,::step],dtype=np.float32)
        rgba *= 1./255.
        if letterbox is not None and width != height:
            # Pad only the retained, display-sized upload. Leave the source alpha intact.
            h, w = rgba.shape[:2]
            side = max(w, h)
            x = np.linspace(0, 1, side)
            gradient = np.asarray(letterbox, dtype=np.float32)
            stops = np.linspace(0, 1, len(gradient))
            strip = np.stack([np.interp(x, stops, channel) for channel in gradient.T], axis=-1)
            padded = np.empty((side, side, 4), dtype=np.float32)
            padded[:] = strip
            left, bottom = (side-w)//2, (side-h)//2
            padded[bottom:bottom+h, left:left+w] = rgba
            rgba = padded
            aspect = 1.0
        h,w = rgba.shape[:2]
        data = gpu.types.Buffer('FLOAT',rgba.size,rgba.ravel())
        return gpu.types.GPUTexture((w,h),format='RGBA8',data=data), aspect

    def _texture(self, icon_value, tile, letterbox):
        if not icon_value:
            return None
        key = (int(icon_value), "square") if tile else int(icon_value)
        if letterbox is not None:
            key = (int(icon_value), letterbox)
        if key not in self.textures:
            try:
                preview = self._preview(int(icon_value))
                entry = self._upload(preview, square=tile, letterbox=letterbox) if preview else None
            except (AttributeError, ReferenceError, RuntimeError, ValueError, BufferError) as exc:
                # A stale/deferred preview must not interrupt later cells or their actions.
                if len(self.errors) >= 96:
                    self.errors.clear()
                self.errors[key] = str(exc)
                return None
            if entry is None:
                return None
            self.errors.pop(key, None)
            self.textures[key] = entry
            while len(self.textures) > 96:
                self.textures.popitem(last=False)
        self.textures.move_to_end(key)
        return self.textures[key]

    def prepare_tiles(self, canvas, icons, *, letterbox=None):
        """Warm this page in bounded idle slices. A first paint always resolves immediately."""
        from weakref import ref
        import bpy
        import gpu

        # Timers have a usable GPU context on the qualified windowed Metal host.
        # Other backends continue to create textures in the owning draw callback.
        if bpy.app.background or gpu.platform.backend_type_get() != "METAL":
            return
        variant = "square" if letterbox is None else letterbox
        pending = tuple(dict.fromkeys(icon for icon in icons if icon and (icon, variant) not in self.textures))[:96]
        self._warm_request = (ref(canvas), iter(pending), letterbox) if pending else None
        if pending and self._warm_callback is None:
            self._warm_callback = self._warm_one
            bpy.app.timers.register(self._warm_callback, first_interval=0.01)

    def _warm_one(self):
        request = self._warm_request
        if request is not None:
            owner, icons, letterbox = request
            canvas = owner()
            if canvas is not None and canvas.visible:
                for icon in icons:
                    key = (icon, "square" if letterbox is None else letterbox)
                    if key not in self.textures:
                        self._texture(icon, True, letterbox)
                        return 0.01
        self._warm_request = self._warm_callback = None
        return None

    def cancel_preparation(self):
        import bpy

        callback = self._warm_callback
        self._warm_request = self._warm_callback = None
        if callback is not None and bpy.app.timers.is_registered(callback):
            bpy.app.timers.unregister(callback)

    def draw_icon(self, icon, icon_value, rect, color, *, tile=False, radius=0, letterbox=None):
        entry = self._texture(icon_value, tile, letterbox)
        if not entry:
            return False
        texture, aspect = entry
        x,y,w,h = rect
        dw = min(w, h*aspect)
        dh = dw/aspect
        if tile:
            from ..gpu import style
            style.preview(texture, x+(w-dw)/2, y+(h-dh)/2, dw, dh,
                          radius, display_space=True)
        else:
            import gpu
            from gpu_extras.presets import draw_texture_2d

            # Blender's ImagePreview bytes are already premultiplied. Text
            # drawn just before this widget can leave blending disabled.
            previous_blend = gpu.state.blend_get()
            try:
                gpu.state.blend_set("ALPHA_PREMULT")
                draw_texture_2d(texture, (x+(w-dw)/2, y+(h-dh)/2), dw, dh)
            finally:
                gpu.state.blend_set(previous_blend)
        return True


class PreviewIcon(Widget):
    def __init__(self, canvas, icon_value, scale, tile_radius=None, *, letterbox=None):
        super().__init__()
        self.bank = canvas.preview_icons
        self.icon_value = icon_value
        self.size = max(1., 16.*scale)
        self.tile_radius = tile_radius
        self.letterbox = letterbox

    def dimensions(self, font_size, available_width, available_height=None):
        self.width = max(1., available_width)
        if self.tile_radius is None:
            self.width = min(self.size, self.width)
        self.height = self.width if available_height is None else min(self.width, available_height)
        return self.width, self.height

    def paint(self, rect, font, palette, *, backdrop=None):
        if self.tile_radius is None:
            self.bank.draw_icon(None, self.icon_value, rect, None)
        else:
            scale = rect[2] / self.width
            self.bank.draw_icon(None, self.icon_value, rect, None, tile=True,
                                radius=self.tile_radius*scale, letterbox=self.letterbox)
