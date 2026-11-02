"""Real modal input survives a consumer ERROR report and accepts the next click."""
import bpy, json, os, sys, traceback, io
from contextlib import redirect_stderr
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import AddonUI

class RECOVERY_OT_refuse(bpy.types.Operator):
    bl_idname='recovery.refuse'
    bl_label='Refuse invalid action'
    def execute(self, context):
        self.report({'ERROR'}, 'The body group contains all remaining bones and cannot be removed')
        return {'CANCELLED'}

class RECOVERY_PT_panel(bpy.types.Panel):
    bl_idname='RECOVERY_PT_panel'
    bl_label='Input recovery'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='Recovery'
    def draw(self, context):
        self.layout.operator('recovery.refuse')
        self.layout.prop(context.scene.render, 'film_transparent')

ui=AddonUI(__name__)
state={'phase':0}
window=bpy.context.window
area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='UI')

def click(kind):
    host=ui._runtime.hosts[RECOVERY_PT_panel]
    rec=next(r for r in host.records.values() if r['valid'])
    canvas=rec['canvas']; control=next(c for c in canvas.controls.values() if c.kind==kind)
    x,y,w,h=control.rect; rx,ry,rw,rh=rec['rect']
    point=dict(x=int(region.x+rx+(x+w/2)*rw/canvas._width),y=int(region.y+ry+rh-(y+h/2)*rh/canvas.height))
    window.event_simulate(type='MOUSEMOVE',value='NOTHING',**point)
    window.event_simulate(type='LEFTMOUSE',value='PRESS',**point)
    window.event_simulate(type='LEFTMOUSE',value='RELEASE',**point)

def tick():
    try:
        phase=state['phase']
        if phase==0:
            bpy.utils.register_class(RECOVERY_OT_refuse)
            area.spaces.active.show_region_ui=True
            ui.register(RECOVERY_PT_panel)
        elif phase==1:
            region.active_panel_category='Recovery';area.tag_redraw()
        elif phase==2:
            assert ui._runtime.running
            state['dispatch'] = ui._runtime.dispatch_event
            def expected_refusal(operator, context, event):
                captured = io.StringIO()
                with redirect_stderr(captured):
                    result = state['dispatch'](operator, context, event)
                if captured.getvalue():
                    assert 'The body group contains all remaining bones' in captured.getvalue()
                    state['expected_traceback'] = captured.getvalue()
                return result
            ui._runtime.dispatch_event = expected_refusal
            click('button')
        elif phase==3:
            errors=ui.status['input_errors']
            assert 'cannot be removed' in errors['RECOVERY_PT_panel']['error'], errors
            state['error']=errors
            assert state.get('expected_traceback')
            ui._runtime.dispatch_event=state['dispatch']
            state['value']=bpy.context.scene.render.film_transparent
            click('toggle')
        elif phase==4:
            assert bpy.context.scene.render.film_transparent != state['value']
            assert ui._runtime.running
            assert any(o.bl_idname==ui._runtime.input_id.split('.')[0].upper()+'_OT_input' for o in window.modal_operators)
            Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=True,version=bpy.app.version_string,refusal=state['error'],next_click_worked=True),indent=2))
            ui.unregister();bpy.utils.unregister_class(RECOVERY_OT_refuse);bpy.ops.wm.quit_blender();return None
        state['phase']+=1
        return .6
    except Exception:
        Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=False,error=traceback.format_exc()),indent=2))
        bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=1)
