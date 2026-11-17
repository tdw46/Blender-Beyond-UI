"""A missing thumbnail must not interrupt a later Blender ImagePreview upload."""
import json
import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

import bpy
import bpy.utils.previews
import gpu
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui.widgets.preview_icon import PreviewIcons

previews = bpy.utils.previews.new()
try:
    preview = previews.new('second tile')
    preview.image_size = 3, 2
    colors = np.array([[255, 64, 0, 255], [0, 32, 255, 127]] * 3, dtype=np.uint8)
    preview.image_pixels = colors.ravel().view(np.int32).tolist()
    # Background Blender can expose pixels before allocating a UI icon ID.
    icon = preview.icon_id or 1
    tile = SimpleNamespace(icon_id=icon, image_size=preview.image_size, image_pixels=preview.image_pixels)
    invalid = SimpleNamespace(icon_id=-1, image_size=(1, 1), image_pixels=None)
    tiles = {'second tile': tile, 'stale': invalid}
    bank = PreviewIcons(lambda: (tiles,))
    if bpy.app.background and hasattr(gpu, 'init'):
        gpu.init()
    target = gpu.types.GPUOffScreen(8, 8)
    with target.bind():
        assert not bank.draw_icon(None, -1, (0, 0, 8, 8), None)
        assert bank.draw_icon(None, icon, (0, 0, 8, 8), None)
        texture, aspect = bank.textures[icon]
        assert aspect == 1.5 and (texture.width, texture.height) == (3, 2)
        actual = np.array(texture.read()).reshape(-1, 4)
        assert np.array_equal(actual, colors), (actual, colors)
    target.free()
    result = {'passed': True, 'tiles_uploaded': len(bank.textures)}
except Exception:
    result = {'passed': False, 'error': traceback.format_exc()}
finally:
    bpy.utils.previews.remove(previews)
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result))
