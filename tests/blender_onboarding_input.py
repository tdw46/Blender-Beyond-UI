"""Owned test-window eyedropper selection/cancel, without desktop input."""
import bpy, os,sys,json,traceback,importlib.util
from pathlib import Path
from bpy_extras import view3d_utils
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
state={'step':0};checks=[]
def finish(error=None):
 try:addon.unregister()
 except Exception:error=(error or '')+traceback.format_exc()
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=error is None,error=error,checks=checks,version=bpy.app.version_string),indent=2))
 bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.1)
def tick():
 try:
  with bpy.context.temp_override(window=window,area=area,region=region):
   n=state['step']
   if n==0:
    addon.register();bpy.context.window_manager.EnableCamKeys=False
    bpy.context.scene.camkeys_setup.dismissed=True
    state['selection']=tuple(bpy.context.selected_objects);state['active']=bpy.context.view_layer.objects.active
    assert bpy.ops.camkeys.setup_pick_subject('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
   elif n==1:
    loc=view3d_utils.location_3d_to_region_2d(region,area.spaces.active.region_3d,bpy.data.objects['Cube'].matrix_world.translation)
    assert loc is not None
    x,y=int(region.x+loc.x),int(region.y+loc.y)
    window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
    window.event_simulate(type='LEFTMOUSE',value='PRESS',x=x,y=y)
    window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=x,y=y)
   elif n==2:
    assert bpy.context.scene.camkeys_setup.target==bpy.data.objects['Cube'],'Eyedropper did not pick cube'
    assert tuple(bpy.context.selected_objects)==state['selection'] and bpy.context.view_layer.objects.active==state['active']
    checks.append('Queued viewport click picks subject without changing active object or selection')
    original=addon.onboarding.CAMKEYS_OT_setup_pick_subject.cancel
    def observed(self,context):state['cancelled']=True;original(self,context)
    addon.onboarding.CAMKEYS_OT_setup_pick_subject.cancel=observed
    assert bpy.ops.camkeys.setup_pick_subject('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
   elif n==3:window.event_simulate(type='ESC',value='PRESS')
   elif n==4:
    assert state.get('cancelled')
    assert bpy.context.scene.camkeys_setup.target==bpy.data.objects['Cube']
    checks.append('Escape cancels eyedropper and restores cursor without changing subject')
    finish();return None
  state['step']+=1;return .5
 except Exception:finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=1)
