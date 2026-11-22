"""A host-colored indeterminate indicator, centered in region or widget pixels."""

import math


class LoadingRing:
    """Share one sprite across anchors. The owner schedules redraws only while busy."""

    def __init__(self, colors):
        self.colors = tuple(tuple(c) for c in colors)
        if len(self.colors) < 2 or any(len(c) != 4 for c in self.colors):
            raise ValueError("LoadingRing requires at least two RGBA stops")
        self.texture = None

    def pixels(self, size, phase=0.0):
        """Straight-alpha, bottom-up pixels, also usable in a native image preview."""
        import numpy as np

        axis = (np.arange(size, dtype=np.float32) + 0.5 - size / 2) / size
        x, y = axis[None, :], axis[:, None]
        radius = np.hypot(x, y)
        angle = (np.arctan2(x, y) / math.tau - phase) % 1.0
        track = np.clip((0.067 - abs(radius - 0.38)) * size + 0.5, 0, 1)
        ink = np.clip((0.042 - abs(radius - 0.38)) * size + 0.5, 0, 1)
        t = np.minimum(angle / 0.79, 1.0)
        ends = np.clip(np.minimum(angle, 0.79 - angle) * size * 2.4 + 0.5, 0, 1)
        colors = np.asarray(self.colors, dtype=np.float32)
        stops = np.linspace(0, 1, len(colors))
        rgba = np.stack([np.interp(t, stops, c) for c in colors.T], axis=-1)
        alpha = ink * ends * rgba[:, :, 3]
        under = 0.76 * track * (1.0 - alpha)
        total = alpha + under
        rgba[:, :, :3] = (rgba[:, :, :3] * alpha[:, :, None] + 0.065 * under[:, :, None]) / np.maximum(total[:, :, None], 1e-8)
        rgba[:, :, 3] = total
        return np.ascontiguousarray(rgba, dtype=np.float32)

    def draw(self, rect, diameter, phase):
        """Draw one cached quad in a POST_PIXEL or widget paint context."""
        import gpu
        from gpu_extras.batch import batch_for_shader
        from mathutils import Matrix

        x, y, w, h = rect
        diameter = min(diameter, w, h)
        if diameter < 2:
            return
        if self.texture is None:
            pixels = self.pixels(96)
            data = gpu.types.Buffer("FLOAT", pixels.size, pixels.ravel())
            self.shader = gpu.shader.from_builtin("IMAGE")
            self.batch = batch_for_shader(self.shader, "TRI_FAN", {
                "pos": ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)),
                "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
            })
            self.texture = gpu.types.GPUTexture((96, 96), format="RGBA8", data=data)
        blend = gpu.state.blend_get()
        try:
            gpu.state.blend_set("ALPHA")
            with gpu.matrix.push_pop():
                gpu.matrix.translate((x + w / 2, y + h / 2, 0))
                gpu.matrix.multiply_matrix(Matrix.Rotation(-phase * math.tau, 4, "Z"))
                gpu.matrix.scale((diameter, diameter, 1))
                self.shader.bind()
                self.shader.uniform_sampler("image", self.texture)
                self.batch.draw(self.shader)
        finally:
            gpu.state.blend_set(blend)
