"""Actual BLF width sweep and offscreen card captures; no user scene required."""
import json
import os
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import patch
import zlib

import bpy
import gpu
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [os.environ.get('CHOICE_CARD_SOURCE', str(ROOT)), str(ROOT/'tests')]
from beyond_ui import Layout
from beyond_ui.gpu import typography, style
from beyond_ui.gpu.paint import measure, gpu_state
from beyond_ui.widgets.choice_card import ChoiceCard
from capture_controls import png

OUTPUT = Path(os.environ['BEYOND_UI_TEST_RESULT'])
BASELINE = os.environ.get('CHOICE_CARD_BASELINE') == '1'


class ProbePainter:
    texts = []

    def __init__(self, rect, width, height, *args, **kwargs):
        self.width, self.height = width, height
        self.scale = rect[3] / height

    def map(self, rect):
        return rect

    def surface(self, *args, **kwargs):
        pass

    def text(self, rect, text, **kwargs):
        self.texts.append((rect, text, kwargs))


def make_card(canvas, title, description, library=None):
    return ChoiceCard(canvas, title, description, library, 'perspective',
                      height=116, media_width=96, padding=6, radius=10,
                      font_size=14.5, description_size=11.5, line_height=16, radio_size=14)


def run():
    fonts = None
    report = {}
    try:
        gpu.init()
        fonts = typography.Fonts()
        palette = style.theme_palette(bpy.context.preferences)
        canvas = Layout().canvas
        samples = [
            ('Forced Perspective', 'Control proportions of parts of your character/scene independent of true camera FOV.'),
            ('Erzwungene Perspektive', 'Steuere die Proportionen von Teilen deiner Figur oder Szene unabhängig vom tatsächlichen Kamera-Sichtfeld.'),
            ('強制パースペクティブ', '実際のカメラの画角とは独立して、キャラクターやシーンの各部分の比率を調整します。'),
        ]
        overflows = []
        tested = 0
        for pixel_scale in (1, 1.5, 2):
            for theme_size in (11, 16.5, 22):
                scale = theme_size / 11
                if BASELINE:
                    callback = lambda text, role: measure(typography.face(fonts, role), theme_size * (12/11 if role == 'title' else 1), text)[0]
                else:
                    callback = typography.text_measurer(fonts, theme_size, pixel_scale)
                for title, description in samples:
                    card = make_card(canvas, title, description)
                    for width in range(150, 451):
                        w, h = card.dimensions(width * scale, theme_size, callback)
                        ProbePainter.texts = []
                        with patch('beyond_ui.widgets.choice_card.Painter', ProbePainter), patch('beyond_ui.widgets.choice_card.skin.draw'):
                            card.paint((0, 0, w * pixel_scale, h * pixel_scale), fonts, palette)
                        violations = []
                        for (x, y, tw, th), text, options in ProbePainter.texts:
                            if y + th > card.render_height - card.padding + .001:
                                violations.append('bottom')
                            font = typography.face(fonts, options.get('weight', 'body'))
                            actual_width = measure(font, options['size'] * scale * pixel_scale, text)[0] / (scale * pixel_scale)
                            if actual_width > tw + .001:
                                violations.append('line-width')
                        if violations:
                            overflows.append(dict(width=width, pixel_scale=pixel_scale, theme_size=theme_size, title=title, violations=sorted(set(violations))))
                        tested += 1
        # Use the real bundled preview when the consumer asset is supplied.
        library = None
        asset = os.environ.get('CHOICE_CARD_MEDIA')
        if asset:
            import numpy as np
            asset = Path(asset)
            meta = json.loads((asset/'metadata.json').read_text())
            start, count = json.loads((asset/'offsets.json').read_text())[0]
            raw = zlib.decompress((asset/'frames.rgba.z').read_bytes()[start:start+count])
            pixels = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255
            texture = gpu.types.GPUTexture((meta['width'], meta['height']), format='RGBA8', data=gpu.types.Buffer('FLOAT', len(pixels), pixels))
            library = SimpleNamespace(frames={'perspective': (texture, 0, meta['width'], meta['height'])}, touch=lambda widget: None)
        captures = []
        for width in (194, 220, 260, 268, 280, 320, 400):
            card = make_card(canvas, *samples[0], library)
            callback = (lambda text, role: measure(typography.face(fonts, role), 12 if role == 'title' else 11, text)[0]) if BASELINE else typography.text_measurer(fonts, 11, 1.5)
            w, h = card.dimensions(width, 11, callback)
            factor = 1.5
            iw, ih = round((w + 24) * factor), round((h + 48) * factor)
            off = gpu.types.GPUOffScreen(iw, ih, format='RGBA8')
            try:
                with off.bind(), gpu_state(), gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                    gpu.matrix.load_matrix(Matrix.Identity(4))
                    gpu.matrix.load_projection_matrix(Matrix(((2/iw,0,0,-1),(0,2/ih,0,-1),(0,0,1,0),(0,0,0,1))))
                    gpu.state.viewport_set(0,0,iw,ih)
                    gpu.state.scissor_set(0,0,iw,ih)
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(.20,.22,.24,1))
                    card.paint((12*factor,36*factor,w*factor,h*factor), fonts, palette)
                    typography.flush_text(fonts)
                    path = OUTPUT.parent/f'card-{width}.png'
                    png(path,iw,ih,fb.read_color(0,0,iw,ih,4,0,'UBYTE'))
                    captures.append(str(path))
            finally:
                off.free()
        report = dict(passed=bool(overflows) if BASELINE else not overflows,
                      baseline=BASELINE, tested=tested, overflow_cases=len(overflows), examples=overflows[:20],
                      captures=captures, backend=gpu.platform.backend_type_get(), gpu=gpu.platform.renderer_get(),
                      blender=bpy.app.version_string, build=bpy.app.build_hash.decode(),
                      limits='Offscreen component/font checks. Live N-panel resizing and Metal execution are separate.')
    except Exception:
        report = dict(passed=False, error=traceback.format_exc())
    finally:
        if fonts is not None:
            fonts.close()
        OUTPUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise RuntimeError('Choice card layout check failed')


run()
