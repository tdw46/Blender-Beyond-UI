"""Actual file-open cycles must renew hosts and preserve rasterized BUI text."""
import bpy, blf, gpu, sys, os, json, traceback
from pathlib import Path
from mathutils import Matrix
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from beyond_ui import AddonUI
from beyond_ui.gpu import typography
from beyond_ui.gpu.paint import gpu_state
from capture_controls import png
OUT = Path(os.environ['BEYOND_UI_TEST_RESULT']).parent
state = {'cycle': 0, 'checks': []}

class FILELOAD_PT_fixture(bpy.types.Panel):
    bl_label = 'File load resources'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'File load'
    def draw(self, context):
        self.layout.label(text='CamKeys text survives file switching')
        self.layout.prop(context.scene.render, 'resolution_percentage')

ui = AddonUI('bui_file_load_fixture')
ui.register(FILELOAD_PT_fixture)


def pixels(font):
    target = gpu.types.GPUOffScreen(500, 100)
    try:
        with target.bind(), gpu_state(), gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
            fb = gpu.state.active_framebuffer_get()
            fb.clear(color=(0, 0, 0, 1))
            gpu.state.blend_set('ALPHA')
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(Matrix(((2/500,0,0,-1),(0,2/100,0,-1),(0,0,-1,0),(0,0,0,1))))
            for role, y in [('body', 20), ('title', 60)]:
                face = typography.face(font, role)
                blf.size(face, 24)
                blf.position(face, 12, y, 0)
                typography.draw_text(face, 'CamKeys 250.0 (mm)', (1,1,1,1), {'outline':False,'shadow':False})
            typography.flush_text(font)
            raw = fb.read_color(0,0,500,100,4,0,'UBYTE')
            raw.dimensions = 500*100*4
            return bytes(raw)
    finally:
        target.free()


def finish(error=None):
    try:
        ui.unregister()
        assert typography._owners == 0
    except Exception:
        error = (error or '') + traceback.format_exc()
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps({
        'passed':error is None, 'version':bpy.app.version_string,
        'backend':gpu.platform.backend_type_get(), 'checks':state['checks'], 'error':error,
    }, indent=2))
    bpy.ops.wm.quit_blender()


def run():
    try:
        rt = ui._runtime
        host = rt.hosts[FILELOAD_PT_fixture]
        assert host.bridge is not None, host.reason
        image = pixels(host.font)
        assert sum(image[::4]) > 10000, 'No text pixels'
        if state['cycle'] == 0:
            state['reference'] = image
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'first.blend'))
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'second.blend'))
        else:
            assert host is not state['old_host']
            assert state['old_host'].closed and state['old_font'].closed
            assert not state['old_host'].handlers and not state['old_host'].records
            assert image == state['reference'], 'Text changed or vanished after file open'
            assert typography._owners == 1, typography._owners
            state['checks'].append(f"File open {state['cycle']}: fresh host, old resources released, identical body/bold pixels")
        png(OUT/f"text-{state['cycle']}.png",500,100,image)
        if state['cycle'] == 3:
            # Undo/value refresh must retain warm resources.
            rt.refresh()
            assert rt.hosts[FILELOAD_PT_fixture] is host and not host.font.closed
            state['checks'].append('Ordinary refresh retains the current host/fonts')
            # Failed-load completion uses the same bounded restart handler when available.
            if hasattr(bpy.app.handlers, 'load_post_fail'):
                before = next(cb for collection,cb in rt.handlers if collection is bpy.app.handlers.load_pre)
                failed = next(cb for collection,cb in rt.handlers if collection is bpy.app.handlers.load_post_fail)
                before('fixture-failure');failed('fixture-failure');rt.start()
                recovered = rt.hosts[FILELOAD_PT_fixture]
                assert pixels(recovered.font) == state['reference']
                state['checks'].append('Failed-load callback restarts text resources')
            finish();return None
        state['old_host'], state['old_font'] = host,host.font
        state['cycle'] += 1
        bpy.ops.wm.open_mainfile(filepath=str(OUT/('first.blend' if state['cycle']%2 else 'second.blend')))
        return .5
    except Exception:
        finish(traceback.format_exc());return None

bpy.app.timers.register(run, first_interval=1, persistent=True)
