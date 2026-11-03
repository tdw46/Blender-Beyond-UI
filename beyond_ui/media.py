"""Visible-only, owner-scoped looping media. No registration on import.

Providers prepare files outside paint and return display-space RGBA bytes.
The scheduler owns uploads; painting only uses retained textures. No transport UI.
"""
from collections import OrderedDict
from time import monotonic
from weakref import WeakKeyDictionary, ref


class MediaLibrary:
    def __init__(self, provider, *, fps=12, budget_bytes=64 * 1024 * 1024):
        if not 1 <= fps <= 60 or budget_bytes < 1024:
            raise ValueError('Invalid media cadence or memory budget')
        self.provider, self.fps, self.budget = provider, float(fps), int(budget_bytes)
        self.leases = WeakKeyDictionary()
        self.textures = OrderedDict()
        self.bytes = 0
        self.frames = {}
        self.errors = {}
        self.started = monotonic()
        self._timer = self._tick
        self.closed = False

    def touch(self, widget):
        if self.closed or widget.key in self.errors:
            return
        import bpy
        if bpy.app.background:
            return
        self.leases[widget] = monotonic()
        if not bpy.app.timers.is_registered(self._timer):
            bpy.app.timers.register(self._timer, first_interval=0.001)

    def release(self, widget):
        self.leases.pop(widget, None)

    def _tick(self):
        now = monotonic()
        active = []
        for widget, last in tuple(self.leases.items()):
            canvas = widget.owner()
            if self.closed or canvas is None or not canvas.visible or now - last > 0.5:
                self.leases.pop(widget, None)
            else:
                active.append(widget)
        if not active:
            return None
        import gpu
        for key in dict.fromkeys(w.key for w in active):
            try:
                token, width, height, pixels = self.provider.frame(key, int((now-self.started)*1000))
                cache_key = (key, token)
                entry = self.textures.get(cache_key)
                if entry is None:
                    size = width * height * 4
                    if size > self.budget:
                        raise ValueError('Media frame exceeds texture budget')
                    # GPUTexture requires FLOAT transfer buffers, including RGBA8 on Metal.
                    # Blender ships NumPy; vectorized transfer avoids Python per-pixel work.
                    import numpy as np
                    rgba = np.frombuffer(pixels(), dtype=np.uint8).astype(np.float32)
                    rgba *= 1.0 / 255.0
                    data = gpu.types.Buffer('FLOAT', size, rgba)
                    texture = gpu.types.GPUTexture((width, height), format='RGBA8', data=data)
                    entry = (texture, size, width, height)
                    self.textures[cache_key] = entry
                    self.bytes += size
                    while self.bytes > self.budget:
                        old, removed = self.textures.popitem(last=False)
                        self.bytes -= removed[1]
                self.textures.move_to_end(cache_key)
                self.frames[key] = entry
                self.errors.pop(key, None)
            except Exception as exc:
                self.errors[key] = str(exc)
        if all(w.key in self.errors for w in active):
            return None
        for widget in active:
            canvas = widget.owner()
            if canvas is not None and canvas._animation_wake:
                canvas._animation_wake()
        return 1 / self.fps

    def close(self):
        self.closed = True
        import bpy
        if bpy.app.timers.is_registered(self._timer):
            bpy.app.timers.unregister(self._timer)
        self.leases.clear()
        self.frames.clear()
        self.textures.clear()
        self.bytes = 0
        self.provider.close()


def media(layout, library, key, *, height=160, radius=12, caption="", caption_size=10, caption_padding=8):
    """Autoplay a silent, looping demo. Native fallback is explicitly a poster."""
    from .artwork import _custom
    if _custom(layout):
        layout.beyond_media(library, key, height=height, radius=radius, caption=caption, caption_size=caption_size, caption_padding=caption_padding)
    else:
        poster = getattr(library.provider, 'poster', lambda key: 0)(key)
        if poster:
            layout.template_icon(icon_value=poster, scale=max(1, height / 32))
        else:
            layout.label(text='Example preview requires Beyond UI', icon='IMAGE_DATA')
