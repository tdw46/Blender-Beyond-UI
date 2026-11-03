"""Native panel geometry and text-fit regression in an isolated no-focus window."""
import json
import os
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace
import zlib

import bpy
import gpu

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from beyond_ui import Layout
from beyond_ui.hosts.panel import PanelHost
from beyond_ui.gpu import typography
from beyond_ui.gpu.paint import measure
from beyond_ui.widgets import choice_card
from capture_controls import png

OUT = Path(os.environ['BEYOND_UI_TEST_RESULT'])
state = dict(step=0, samples=[], errors=[], current=[], capture=False)
host = PanelHost('test.choice_card_native')
assert host.start(), host.reason
layout = Layout()
cards = [
    ('Shapekeys × Camera Angle', 'Blend shapes as the view changes.', 88),
    ('Forced Perspective', 'Control proportions of parts of your character/scene independent of true camera FOV.', 116),
    ('Dolly Zoom + Camera Tricks', 'Hold framing while the camera moves', 88),
]
for index, (title, copy, height) in enumerate(cards):
    control = layout.group.button(index, title, lambda: None)
    control.options['choice_card'] = choice_card.ChoiceCard(
        layout.canvas, title, copy, None, None, height=height, media_width=96,
        padding=6, radius=10, font_size=14.5, description_size=11.5, line_height=16)
layout.label(text='Next')

OriginalPainter = choice_card.Painter
class ProbePainter(OriginalPainter):
    def text(self, rect, text, **kwargs):
        mapped = self.map(rect)
        font = typography.face(self.font, kwargs.get('weight', 'body'))
        size = kwargs['size'] * self.scale
        pixels = measure(font, size, text)[0]
        state['current'].append(dict(text=text, width=pixels, available=mapped[2], size=size,
                                     fits=pixels <= mapped[2] + .01))
        return super().text(rect, text, **kwargs)
choice_card.Painter = ProbePainter
original_paint = host._paint
def paint(*args):
    if not state.get('media_loaded') and os.environ.get('BEYOND_UI_CAMKEYS_ROOT'):
        import numpy as np
        from beyond_ui.widgets.media import MediaWidget
        frames = {}
        for index, name in enumerate(('angles', 'perspective', 'dolly')):
            asset = Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])/'assets/demos'/name
            meta = json.loads((asset/'metadata.json').read_text())
            start, count = json.loads((asset/'offsets.json').read_text())[0]
            raw = zlib.decompress((asset/'frames.rgba.z').read_bytes()[start:start+count])
            pixels = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255
            texture = gpu.types.GPUTexture((meta['width'], meta['height']), format='RGBA8', data=gpu.types.Buffer('FLOAT', len(pixels), pixels))
            frames[name] = (texture, 0, meta['width'], meta['height'])
            card = layout.canvas.controls[index].options['choice_card']
            card.media = MediaWidget(SimpleNamespace(frames=frames, touch=lambda widget: None), name, layout.canvas, card.height-12, 8)
        state['media_loaded'] = True
    state['current'] = []
    original_paint(*args)
    if state['current']:
        record = next(iter(host.records.values()))
        state['last'] = dict(region=bpy.context.region.width, ui_scale=bpy.context.preferences.system.ui_scale,
                             view0=list(bpy.context.region.view2d.region_to_view(0, 0)),
                             view100=list(bpy.context.region.view2d.region_to_view(100, 100)),
                             requested=[layout.canvas._width, layout.canvas.height], actual=record['rect'],
                             text=list(state['current']))
        if state['capture']:
            typography.flush_text(host.font)
            region = bpy.context.region
            viewport = gpu.state.viewport_get()
            fb = gpu.state.active_framebuffer_get()
            path = OUT.parent/f"panel-{state['step']}.png"
            png(path, region.width, region.height, fb.read_color(viewport[0], viewport[1], region.width, region.height,4,0,'UBYTE'))
            state['capture'] = False
host._paint = paint

class BUI_PT_choice_fit(bpy.types.Panel):
    bl_label = 'Choice text fit'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Choice Fit'
    def draw(self, context):
        try:
            assert host.draw(self.layout, context, layout.canvas)
        except Exception:
            state['errors'].append(traceback.format_exc())

bpy.utils.register_class(BUI_PT_choice_fit)
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == 'UI')

def finish(error=None):
    baseline = os.environ.get('CHOICE_PANEL_BASELINE') == '1'
    errors = state['errors'] + ([error] if error else [])
    overflow = sum(not t['fits'] for sample in state['samples'] for t in sample['text'])
    result = dict(passed=not errors and (overflow > 0 if baseline else overflow == 0),
                  native_adapter=bool(host.bridge), baseline=baseline, overflow_lines=overflow,
                  samples=state['samples'], errors=errors, backend=gpu.platform.backend_type_get(),
                  version=bpy.app.version_string, build=bpy.app.build_hash.decode(),
                  idle_layout_count=state.get('idle_layout_count'), hit_areas_verified=state.get('hit_areas_verified', False))
    OUT.write_text(json.dumps(result, indent=2), encoding='utf-8')
    host.close()
    bpy.utils.unregister_class(BUI_PT_choice_fit)
    bpy.ops.wm.quit_blender()

def tick():
    try:
        step = state['step']
        if step == 0:
            region.active_panel_category = 'Choice Fit'
        elif step in (2,4,6,8,13,18,23):
            assert state.get('last'), 'Native panel did not paint'
            state['samples'].append(state['last'])
            assert not host.bridge.errors, host.bridge.errors
            if step < 8:
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view2d.zoom_in() if step < 6 else bpy.ops.view2d.zoom_out()
            elif step in (8,13,18):
                state['old_width'] = region.width
                state['resize_x'] = region.x - 1
                state['resize_y'] = region.y + region.height // 2
                bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=state['resize_x'], y=state['resize_y'])
            else:
                assert region.width != state['old_width'], 'Sidebar resize did not execute'
                for control in layout.canvas.controls.values():
                    if control.options.get('choice_card'):
                        x,y,w,h=control.rect
                        assert layout.canvas.hit(x+w/2,y+h/2,(0,0,layout.canvas._width,layout.canvas.height)) is control
                state['hit_areas_verified'] = True
                state['idle_layout_count'] = layout.canvas.layout_count
                state['step'] += 1
                return 1
        elif step in (9,14,19):
            bpy.context.window.event_simulate(type='LEFTMOUSE', value='PRESS', x=state['resize_x'], y=state['resize_y'])
        elif step in (10,15,20):
            delta = -120 if step == 10 else 80 if step == 15 else -200
            bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=state['resize_x']+delta, y=state['resize_y'])
        elif step in (11,16,21):
            bpy.context.window.event_simulate(type='LEFTMOUSE', value='RELEASE', x=state['resize_x'], y=state['resize_y'])
        elif step == 24:
            assert layout.canvas.layout_count == state['idle_layout_count'], 'Idle layout is still rebuilding'
            assert not bpy.app.timers.is_registered(host._resume_callback), 'Geometry feedback did not settle'
            finish()
            return None
        state['capture'] = True
        area.tag_redraw()
        state['step'] += 1
        return .4
    except Exception:
        finish(traceback.format_exc())
        return None

bpy.app.timers.register(tick, first_interval=1)
