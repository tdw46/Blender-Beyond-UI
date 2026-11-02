"""A running consumer modal must survive adoption, teardown and re-adoption."""
import bpy, os, sys, json, traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import AddonUI
from beyond_ui.invoke_routing import Router

state = dict(ticks=0, stop=False, phase=0, routes=[])

class LIFECYCLE_OT_engine(bpy.types.Operator):
    bl_idname = 'lifecycle.engine'
    bl_label = 'Live consumer engine'
    value: bpy.props.IntProperty(default=37)

    def execute(self, context):
        state['engine'] = self
        state['timer'] = context.window_manager.event_timer_add(.03, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if state['stop']:
                context.window_manager.event_timer_remove(state['timer'])
                state['ended'] = True
                return {'CANCELLED'}
            state['ticks'] += 1
        return {'PASS_THROUGH'}

class LIFECYCLE_OT_popup(bpy.types.Operator):
    bl_idname = 'lifecycle.popup'
    bl_label = 'Existing modal with custom dialog'
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=333)
    def modal(self, context, event):
        return {'PASS_THROUGH'}
    def execute(self, context):
        return {'FINISHED'}

classes = (LIFECYCLE_OT_engine, LIFECYCLE_OT_popup)
router = Router(SimpleNamespace(owner=__name__, ui=AddonUI(__name__)), classes)

def result(passed, **extra):
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=passed, version=bpy.app.version_string, ticks=state['ticks'], routes=state['routes'], **extra), indent=2))
    bpy.ops.wm.quit_blender()

def run():
    try:
        phase = state['phase']
        if phase == 0:
            for cls in classes: bpy.utils.register_class(cls)
            assert bpy.ops.lifecycle.engine() == {'RUNNING_MODAL'}
            state['pointer'] = state['engine'].as_pointer()
            state['rna'] = LIFECYCLE_OT_engine.bl_rna.as_pointer()
        elif phase in (1, 3):
            assert state['ticks'] > state.get('last_ticks', 0)
            router.register()
            assert set(classes) == router.in_place
            def dialog(op, context, event, **kw):
                state['routes'].append(kw['width'])
                return {'CANCELLED'}
            router.dialog = dialog
            assert bpy.ops.lifecycle.popup('INVOKE_DEFAULT') == {'CANCELLED'}
        elif phase in (2, 4):
            assert state['ticks'] > state['last_ticks']
            assert state['engine'].as_pointer() == state['pointer']
            assert state['engine'].value == 37
            assert LIFECYCLE_OT_engine.bl_rna.as_pointer() == state['rna']
            router.close()
        elif phase == 5:
            assert state['ticks'] > state['last_ticks']
            assert state['engine'].as_pointer() == state['pointer']
            state['stop'] = True
        elif phase == 6:
            assert state.get('ended')
            assert state['routes'] == [333, 333]
            for cls in reversed(classes): bpy.utils.unregister_class(cls)
            result(True, instance_preserved=True, restored_modal_dispatch=True, custom_invoke_preserved=True)
            return None
        state['last_ticks'] = state['ticks']
        state['phase'] += 1
        return .35
    except Exception:
        result(False, error=traceback.format_exc())
        return None

bpy.app.timers.register(run, first_interval=1)
