"""One pixel-aligned foreground tile for a stable, backdrop-independent widget."""

from math import ceil, floor


class StaticInk:
    def __init__(self):
        self.clear()

    def clear(self):
        self.key = self.palette = self.texture = None
        self.unavailable = False

    def draw(self, rect, font, palette, revision, draw):
        import gpu
        from mathutils import Matrix
        from . import typography, style

        x, y, w, h = rect
        left, bottom = floor(x), floor(y)
        width, height = ceil(x + w) - left, ceil(y + h) - bottom
        local = (x-left, y-bottom, w, h)
        key = (local, font, revision, width, height)
        if self.unavailable or width < 1 or height < 1 or width * height > 512 * 512:
            draw(rect, font, palette)
            return
        if self.key != key or self.palette is not palette:
            # Skip allocation for one-off geometry during opening/resize.
            self.key, self.palette, self.texture = key, palette, None
            draw(rect, font, palette)
            return
        if self.texture is None:
            viewport = gpu.state.viewport_get()
            scissor = gpu.state.scissor_get()
            blend = gpu.state.blend_get()
            try:
                texture = gpu.types.GPUTexture((width, height), format="RGBA8")
                target = gpu.types.GPUFrameBuffer(color_slots=texture)
            except (RuntimeError, MemoryError):
                self.unavailable = True
                draw(rect, font, palette)
                return
            try:
                with target.bind(), gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                    gpu.state.viewport_set(0, 0, width, height)
                    gpu.state.scissor_set(0, 0, width, height)
                    target.clear(color=(0, 0, 0, 0))
                    gpu.matrix.load_matrix(Matrix.Identity(4))
                    gpu.matrix.load_projection_matrix(Matrix((
                        (2 / width, 0, 0, -1),
                        (0, 2 / height, 0, -1),
                        (0, 0, 1, 0),
                        (0, 0, 0, 1),
                    )))
                    gpu.state.blend_set("ALPHA")
                    draw(local, font, palette)
                    typography.flush_text(font)
                self.texture = texture
            finally:
                gpu.state.viewport_set(*viewport)
                gpu.state.scissor_set(*scissor)
                gpu.state.blend_set(blend)
        style.preview(self.texture, left, bottom, width, height, 0,
                      display_space=True, premultiplied=True)
