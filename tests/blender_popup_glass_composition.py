"""Draw through the admitted window bridge. Pixel reads exist only in the fixture."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

import bpy
import gpu
from mathutils import Matrix

sys.path.insert(0, os.environ.get("BEYOND_UI_TEST_PACKAGE_ROOT", str(Path(__file__).resolve().parents[1])))
from beyond_ui.gpu import glass, style
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.hosts import bridge, window_overlay

owner = SimpleNamespace(bridge=bridge.load())
# Exercise the shared full-frame blit on a crop-capable test machine as well.
if os.environ.get("BEYOND_UI_TEST_POPUP_BLIT") == "1":
    class CopyOnly:
        def __getattr__(self, name):
            if name == "bvt_probe_crop_framebuffer":
                raise AttributeError(name)
            return getattr(self.native, name)
    proxy = CopyOnly()
    proxy.native = owner.bridge.library
    capture_host = SimpleNamespace(bridge=SimpleNamespace(library=proxy))
else:
    capture_host = owner
window = bpy.context.window
record = {}
result = {}


def read_pixel(x, y):
    pixels = gpu.state.active_framebuffer_get().read_color(x, y, 1, 1, 4, 0, "UBYTE")
    pixels.dimensions = 4
    return tuple(bytes(pixels)[:3])


def fingerprint(x, y, w, h):
    pixels = gpu.state.active_framebuffer_get().read_color(x, y, w, h, 4, 0, "UBYTE")
    pixels.dimensions = w * h * 4
    return hashlib.sha256(bytes(pixels)).hexdigest()


def texture_edits(output):
    """Rotate all three slots, hit the settled revision and resize the same owner."""
    key = "edited-panel"
    source = gpu.types.GPUOffScreen(128, 128, format="RGBA8")
    texture = source.texture_color
    hashes = []
    allocations = []
    try:
        for revision, width in ((1, 128), (2, 128), (3, 128), (4, 128), (4, 128), (5, 96)):
            box = (0, 0, width, 128)
            with source.bind(), gpu.matrix.push_pop_projection():
                gpu.state.viewport_set(0, 0, 128, 128)
                gpu.state.scissor_set(0, 0, 128, 128)
                gpu.matrix.load_projection_matrix(Matrix((
                    (2/128, 0, 0, -1), (0, 2/128, 0, -1),
                    (0, 0, 1, 0), (0, 0, 0, 1))))
                fb = gpu.state.active_framebuffer_get()
                fb.clear(color=(0.1, 0.4, 0.9, 1))
                style.draw(16 * revision, 0, 14, 128, (0.9, 0.2, 0.1, 1), radius=0)
            assert glass.prepare_texture(key, revision, texture, box)
            with output.bind(), gpu.matrix.push_pop_projection():
                gpu.state.viewport_set(0, 0, 256, 256)
                gpu.state.scissor_set(0, 0, 256, 256)
                gpu.matrix.load_projection_matrix(Matrix((
                    (2/256, 0, 0, -1), (0, 2/256, 0, -1),
                    (0, 0, 1, 0), (0, 0, 0, 1))))
                levels = []
                for blur in (0.3, 0.7, 0.3):
                    gpu.state.active_framebuffer_get().clear(color=(0, 0, 0, 1))
                    assert glass.lens(key, box, 6, (0, 0, 0, 0), blur=blur)
                    levels.append(fingerprint(8, 8, width - 16, 112))
                assert levels[0] == levels[2] and levels[0] != levels[1], levels
                hashes.append(levels[:2])
            allocations.append(glass._owners[key]["allocations"])
        assert hashes[3] == hashes[4] and len({pair[0] for pair in hashes}) == 5
        assert allocations[2] == allocations[3] == allocations[4]
        assert glass._owners[key]["productions"] == glass._owners[key]["strong_productions"] == 5
        return dict(hashes=hashes, allocations=allocations)
    finally:
        glass.release(key)
        source.free()


def exercise():
    if result:
        return
    try:
        with gpu_state(), window_overlay.scissor_scope(), gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
            _, _, width, height = gpu.state.viewport_get()
            if width < 260 or height < 260:
                return
            gpu.state.scissor_set(0, 0, width, height)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(Matrix((
                (2 / width, 0, 0, -1), (0, 2 / height, 0, -1),
                (0, 0, 1, 0), (0, 0, 0, 1))))
            rect = (64, 64, 160, 160)
            child_rect = (84, 84, 120, 120)
            clear = (0, 0, 0, 0)
            # Some Blender builds expose no Python-readable extent for the
            # window backbuffer. Present out to an owned texture for readback.
            output = gpu.types.GPUOffScreen(256, 256, format="RGBA8")
            fingerprints = []
            for repeat in range(2):
                # A native region and another menu can change pixels here
                # without a change to the 3D viewport texture or camera.
                style.draw(44, 44, 200, 200, (1, 0, 0, 1), radius=0)
                style.draw(144, 44, 100, 200, (0, 1, 0, 1), radius=0)
                with glass.popup_pass(capture_host, 'test', record, revision=1):
                    parent = glass.popup_backdrop(None, rect, 1)
                    assert record["popup_source"] == "COMPOSITE", record
                    with output.bind(), gpu.matrix.push_pop_projection():
                        gpu.state.viewport_set(0, 0, 256, 256)
                        gpu.state.scissor_set(0, 0, 256, 256)
                        gpu.matrix.load_projection_matrix(Matrix((
                            (2 / 256, 0, 0, -1), (0, 2 / 256, 0, -1),
                            (0, 0, 1, 0), (0, 0, 0, 1))))
                        assert glass.lens(parent, rect, 8, clear, blur=0.3)
                        base = read_pixel(139, 145)
                        assert glass.lens(parent, rect, 8, clear, blur=glass.POPUP_BLUR)
                        stronger = read_pixel(139, 145)
                        assert stronger[1] > base[1] + 5, (base, stronger)
                        assert read_pixel(102, 145)[0] > 210 and read_pixel(186, 145)[1] > 210
                        style.draw(129, 90, 30, 110, (0, 0, 1, 1), radius=0)
                        child = glass.popup_backdrop(parent, child_rect, 1, underlay='stable blue control')
                        assert glass.lens(child, child_rect, 8, clear, blur=glass.POPUP_BLUR)
                        stripe = read_pixel(144, 145)
                        assert stripe[2] > 160 and stripe[2] > stripe[0] + stripe[1], stripe
                        # The interior is entirely authored by this fixture. Exclude
                        # window contents and uninitialized offscreen borders.
                        fingerprints.append(fingerprint(84, 84, 120, 120))
                gpu.state.viewport_set(0, 0, width, height)
                gpu.state.scissor_set(0, 0, width, height)
            edited = texture_edits(output)
            output.free()
            for key in (parent, child):
                assert glass._owners[key]["productions"] == glass._owners[key]["strong_productions"] == 1
            assert fingerprints[0] == fingerprints[1], fingerprints
            result.update(passed=True, backend=gpu.platform.backend_type_get(),
                          version=bpy.app.version_string, baseline_edge=base, popup_edge=stronger,
                          interior_sha256=fingerprints[0], texture_edits=edited,
                          allocations=sum(glass._owners[k]["allocations"] for k in (parent,child)),
                          underlying_control=stripe, captures_for_two_paints=2, shared_blit_scratch="_popup_copy" in record)
    except Exception:
        result.update(passed=False, viewport=gpu.state.viewport_get(), error=traceback.format_exc())


def finish():
    if not result:
        for area in window.screen.areas:
            area.tag_redraw()
        return .2
    window_overlay.detach(owner.bridge, window, "glass-pixel-test")
    glass.clear()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    bpy.ops.wm.quit_blender()


window_overlay.attach(owner.bridge, window, "glass-pixel-test", exercise)
bpy.app.timers.register(finish, first_interval=.2)
