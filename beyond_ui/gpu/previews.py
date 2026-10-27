"""Bounded UI thumbnail cache, independent of material/scene/product RNA.

Hosts pass shading snapshots, existing ImagePreview pixels or fallback colors.
A shared small target samples textures on cache misses; no scene IDs, geometry
evaluation or Blender preview render jobs are created.
"""

from collections import OrderedDict


def sphere_pixels(color, size=48):
    import numpy as np

    axis = (np.arange(size, dtype=np.float32) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    rr = x * x + y * y
    z = np.sqrt(np.maximum(0.0, 1 - rr))
    light = np.maximum(0.0, -0.42 * x + 0.48 * y + 0.77 * z)
    spec = np.maximum(0.0, -0.25 * x + 0.30 * y + 0.92 * z) ** 28
    pixels = np.empty((size, size, 4), dtype=np.float32)
    pixels[:, :, :3] = (
        np.asarray(color[:3], dtype=np.float32)[None, None, :]
        * (0.18 + 0.78 * light[:, :, None])
        + spec[:, :, None] * 0.30
    )
    pixels[:, :, 3] = np.clip((1.0 - np.sqrt(rr)) * size * 0.5, 0.0, 1.0)
    return pixels


class PreviewCache:
    def __init__(self, limit=64):
        self.limit = limit
        self.entries = OrderedDict()
        self.retired = []
        self.uploads = 0
        self.images = OrderedDict()
        self.image_reads = 0
        self.material_builds = 0
        self.target = None
        self.shader = None
        self.batch = None

    def clear(self):
        self.entries.clear()
        self.retired.clear()
        self.uploads = 0
        self.images.clear()
        self.image_reads = 0
        self.material_builds = 0
        if self.target is not None:
            self.target.free()
        self.target = None
        self.shader = None
        self.batch = None

    def image(self, image, revision):
        """Cold-only bounded GPU downsample; never reads a full image to Python."""
        import gpu
        import numpy as np
        from mathutils import Matrix
        from gpu_extras.batch import batch_for_shader

        key = (image.as_pointer(), revision)
        if key in self.images:
            self.images.move_to_end(key)
            return self.images[key]
        if not image.has_data or not all(image.size):
            return None
        state = (
            gpu.state.viewport_get(),
            gpu.state.scissor_get(),
            gpu.state.blend_get(),
            gpu.state.depth_test_get(),
            gpu.state.depth_mask_get(),
        )
        try:
            if self.target is None:
                self.target = gpu.types.GPUOffScreen(96, 96, format="RGBA16F")
            if self.shader is None:
                self.shader = gpu.shader.from_builtin("IMAGE")
                self.batch = batch_for_shader(
                    self.shader,
                    "TRI_FAN",
                    {
                        "pos": ((-1, -1), (1, -1), (1, 1), (-1, 1)),
                        "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
                    },
                )
            with (
                self.target.bind(),
                gpu.matrix.push_pop(),
                gpu.matrix.push_pop_projection(),
            ):
                gpu.state.viewport_set(0, 0, 96, 96)
                gpu.state.scissor_set(0, 0, 96, 96)
                gpu.state.blend_set("NONE")
                gpu.state.depth_test_set("NONE")
                gpu.state.depth_mask_set(False)
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))
                texture = gpu.texture.from_image(image)
                self.shader.bind()
                self.shader.uniform_sampler("image", texture)
                self.batch.draw(self.shader)
                raw = gpu.state.active_framebuffer_get().read_color(
                    0, 0, 96, 96, 4, 0, "FLOAT"
                )
                pixels = np.array(raw.to_list(), dtype=np.float32)
                self.image_reads += 1
            if image.alpha_mode == "PREMUL":
                pixels[:, :, :3] /= np.maximum(pixels[:, :, 3:4], 1e-6)
            self.images[key] = pixels
            while len(self.images) > self.limit:
                self.images.popitem(last=False)
            return pixels
        except (AttributeError, RuntimeError, ValueError, ReferenceError):
            self.images[key] = None
            while len(self.images) > self.limit:
                self.images.popitem(last=False)
            return None
        finally:
            gpu.state.viewport_set(*state[0])
            gpu.state.scissor_set(*state[1])
            gpu.state.blend_set(state[2])
            gpu.state.depth_test_set(state[3])
            gpu.state.depth_mask_set(state[4])

    def material(self, key, parameters, revision, preview=None):
        """One shading snapshot per visible material and menu generation."""
        import gpu
        from ..materials import shade

        if parameters.get("kind") == "UNKNOWN":
            return self.texture(key, preview, parameters["base_color"], revision)
        signature = ("shaded", key, revision)
        if signature in self.entries:
            self.entries.move_to_end(signature)
            return self.entries[signature]
        textures = {}
        for channel, image in parameters.get("images", {}).items():
            if image is None or channel in {
                "mask",
                "outline",
                "receive_shadow",
                "shading_grade",
            }:
                continue
            pixels = self.image(image, revision)
            if pixels is not None:
                textures[channel] = pixels
        pixels = shade(parameters, textures)
        texture = gpu.types.GPUTexture(
            (pixels.shape[1], pixels.shape[0]),
            format="RGBA16F",
            data=gpu.types.Buffer("FLOAT", pixels.size, pixels.ravel()),
        )
        self.entries[signature] = texture
        self.uploads += 1
        self.material_builds += 1
        while len(self.entries) > self.limit:
            self.retired.append(self.entries.popitem(last=False)[1])
        self.retired[:] = self.retired[-self.limit :]
        return texture

    def texture(self, key, preview=None, color=(0.3, 0.3, 0.3), revision=None):
        import gpu
        import numpy as np

        try:
            size = tuple(preview.image_size) if preview else (0, 0)
        except (AttributeError, ReferenceError):
            size = (0, 0)
        native = (
            all(size) and max(size) <= 256 and hasattr(preview, "image_pixels_float")
        )
        signature = (key, revision, size if native else (), tuple(color[:3]))
        if signature in self.entries:
            self.entries.move_to_end(signature)
            return self.entries[signature]
        if native:
            try:
                pixels = (
                    np.asarray(preview.image_pixels_float[:], dtype=np.float32)
                    .reshape(*size[::-1], 4)
                    .copy()
                )
                rgb = pixels[:, :, :3]
                pixels[:, :, :3] = np.where(
                    rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4
                )
            except (AttributeError, ReferenceError, ValueError, RuntimeError):
                native = False
        if not native:
            size = (48, 48)
            pixels = sphere_pixels(color)
        texture = gpu.types.GPUTexture(
            size,
            format="RGBA16F",
            data=gpu.types.Buffer("FLOAT", pixels.size, pixels.ravel()),
        )
        self.entries[signature] = texture
        self.uploads += 1
        while len(self.entries) > self.limit:
            self.retired.append(self.entries.popitem(last=False)[1])
        # Keep previous draws alive across asynchronous submission.
        self.retired[:] = self.retired[-self.limit :]
        return texture
