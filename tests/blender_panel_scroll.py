"""Parked list redraws must retain native panel height and View2D scroll."""
import json
import os
from pathlib import Path
import sys
import traceback
import time
import statistics

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
import registered_lists_fixture as fixture
from beyond_ui import AddonUI
from beyond_ui.hosts.addon import Runtime

panel_draws = 0


class BUI_PT_scroll_list(bpy.types.Panel):
    bl_label = 'Updating collection'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Scroll Test'

    def draw(self, context):
        global panel_draws
        panel_draws += 1
        self.layout.template_list('BUI_UL_registered', 'registered', context.scene,
                                  'bui_list_items', context.scene, 'bui_list_active', rows=5)


class BUI_PT_scroll_below(bpy.types.Panel):
    bl_label = 'Controls below the updating list'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Scroll Test'

    def draw(self, context):
        for i in range(70):
            self.layout.label(text=f'Lower panel row {i}')


ui = AddonUI('scroll_regression', commit=lambda a, b: None,
             layout_options={'list_identity': lambda owner, prop, item: item.uid})
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == 'UI')
state = {'stage': 0}
checks = []
errors = []
draw_times = []
adopt = os.environ.get('BEYOND_UI_TEST_ADOPT', '1') == '1'


def finish(error=None):
    ui.unregister()
    if BUI_PT_scroll_list.is_registered:
        bpy.utils.unregister_class(BUI_PT_scroll_list)
    if BUI_PT_scroll_below.is_registered:
        bpy.utils.unregister_class(BUI_PT_scroll_below)
    fixture.unregister()
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps({
        'passed': error is None, 'version': bpy.app.version_string,
        'checks': checks, 'scroll': state.get('scroll'), 'error': error,
        'adopted_native_panel': adopt, 'draw_errors': errors,
        'offscreen_work': state.get('offscreen_work'),
    }, indent=2))
    bpy.ops.wm.quit_blender()


def scroll(direction, count):
    with bpy.context.temp_override(window=window, area=area, region=region):
        for _ in range(count):
            getattr(bpy.ops.view2d, 'scroll_' + direction)()
    region.tag_redraw()


def tick():
    try:
        n = state['stage']
        if n == 0:
            fixture.register(8)
            if adopt:
                bpy.utils.register_class(BUI_PT_scroll_list)
                ui._runtime = Runtime(ui, [BUI_PT_scroll_list], adopt=True)
                ui._runtime.register()
            else:
                ui.register(BUI_PT_scroll_list)
            original_error = ui._runtime.draw_error
            def record_error(definition, key, native, error, *args):
                errors.append(f'{type(error).__name__}: {error}')
                return original_error(definition, key, native, error, *args)
            ui._runtime.draw_error = record_error
            original_draw = ui._runtime.draw
            def timed_draw(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return original_draw(*args, **kwargs)
                finally:
                    draw_times.append((time.perf_counter() - start) * 1000)
            ui._runtime.draw = timed_draw
            bpy.utils.register_class(BUI_PT_scroll_below)
        elif n == 1:
            region.active_panel_category = 'Scroll Test'
        elif n == 2:
            runtime = ui._runtime
            assert not runtime.errors, runtime.errors
            host = runtime.hosts[BUI_PT_scroll_list]
            record = next(iter(host.records.values()))
            canvas = record['canvas']
            state.update(canvas=canvas, height=canvas.height)
            assert canvas.height > 100
            canvas.park()  # Exactly the lifecycle used when the list scrolls out of view.
            assert not canvas.visible
            widget = next(c.options['widget'] for c in canvas.controls.values() if c.kind == 'widget')
            with bpy.context.temp_override(window=window, area=area, region=region):
                try:
                    widget.check(bpy.context)
                except ReferenceError:
                    pass
                else:
                    raise AssertionError('Parked list must still reject interaction')
            region.tag_redraw()
        elif n == 3:
            assert not errors, errors
            assert not ui._runtime.errors, ui._runtime.errors
            canvas = next(iter(ui._runtime.canvases[BUI_PT_scroll_list].values()))[1]
            assert canvas is state['canvas'], 'Rebuilt instead of retaining parked canvas'
            assert canvas.height == state['height'], (canvas.height, state['height'])
            checks.append('Parked list reauthors without owner error, replacement or height collapse')
            scroll('down', 45)
        elif n == 4:
            assert not ui._runtime.errors, ui._runtime.errors
            position = tuple(region.view2d.region_to_view(0, 0))
            state['scroll'] = list(position)
            assert position[1] < -300, position
            assert not state['canvas'].visible, 'List must be fully clipped for regression'
            state['counts'] = (panel_draws, fixture.draws, fixture.filter_draws, fixture.filters)
            state['timing_start'] = len(draw_times)
        elif 5 <= n <= 14:
            assert not ui._runtime.errors, ui._runtime.errors
            assert tuple(region.view2d.region_to_view(0, 0)) == tuple(state['scroll'])
            canvas = next(iter(ui._runtime.canvases[BUI_PT_scroll_list].values()))[1]
            assert canvas is state['canvas'] and canvas.height == state['height']
            bpy.context.scene.bui_list_items[1].name = f'Live value {n}'
            region.tag_redraw()
        elif n == 15:
            assert tuple(region.view2d.region_to_view(0, 0)) == tuple(state['scroll'])
            counts = (panel_draws, fixture.draws, fixture.filter_draws, fixture.filters)
            timings = draw_times[state['timing_start']:]
            state['offscreen_work'] = {
                'callback_deltas': [b-a for a,b in zip(state['counts'], counts)],
                'native_draw_calls': len(timings),
                'median_ms': statistics.median(timings),
                'max_ms': max(timings),
            }
            if os.environ.get('BEYOND_UI_EXPECT_DEFER', '1') == '1':
                assert counts == state['counts'], state['offscreen_work']
                checks.append('Fully offscreen updates invoke zero panel, list-row or filter callbacks')
            checks.append('Ten live list updates preserve offscreen panel height and native scroll position')
            scroll('up', 100)
        elif n == 16:
            assert not errors, errors
            canvas = state['canvas']
            assert canvas.visible and not ui._runtime.errors, ui._runtime.errors
            widget = next(c.options['widget'] for c in canvas.controls.values() if c.kind == 'widget')
            labels = [c.label for child in widget.live_canvases for c in child.controls.values()]
            assert 'Live value 14' in labels, labels
            host = ui._runtime.hosts[BUI_PT_scroll_list]
            assert not bpy.app.timers.is_registered(host._resume_callback)
            checks.append('Returning to list resumes current row values and retained controls')
            scroll('down', 45)
        elif n == 17:
            assert not state['canvas'].visible
            bpy.context.scene.bui_list_items.clear()
            for i in range(3):
                item = bpy.context.scene.bui_list_items.add()
                item.uid = f'replacement-{i}'
                item.name = f'New owner {i}'
            region.tag_redraw()
        elif n == 18:
            assert not errors, errors
            scroll('up', 100)
        elif n == 19:
            assert not errors, errors
            canvas = next(iter(ui._runtime.canvases[BUI_PT_scroll_list].values()))[1]
            assert canvas.visible
            widget = next(c.options['widget'] for c in canvas.controls.values() if c.kind == 'widget')
            labels = [c.label for child in widget.live_canvases for c in child.controls.values()]
            assert 'New owner 1' in labels and 'Live value 14' not in labels, labels
            checks.append('Collection deletion/replacement while hidden is resolved on reentry; no stale rows')
            finish()
            return None
        state['stage'] += 1
        return 0.3
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=0.7)
