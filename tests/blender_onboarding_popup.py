"""Queued native invocation + actual custom popup playback/cleanup."""
import bpy, os,sys,json,traceback,importlib.util,time
from pathlib import Path
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
state={'step':0};checks=[]
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')

def finish(error=None):
 try:addon.unregister()
 except Exception:error=(error or '')+traceback.format_exc()
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=error is None,error=error,checks=checks,version=bpy.app.version_string),indent=2))
 bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.1)

def tick():
 try:
  if not state.get('registered'):
   addon.register();bpy.context.window_manager.EnableCamKeys=False
   bpy.context.scene.camkeys_setup.dismissed=True
   state.update(registered=True,topics=list(addon.onboarding.HELP),index=0,step=0)
  topic=state['topics'][state['index']];n=state['step']
  router=addon.__beyond_ui_integration__.router;lib=addon.demo_media.LIBRARY
  if n==0:
   with bpy.context.temp_override(window=window,area=area,region=region):
    result=bpy.ops.camkeys.show_example('INVOKE_DEFAULT',example=topic)
   assert result=={'RUNNING_MODAL'},(topic,result)
   state['wait']=0
  elif n==1:
   assert router.dialogs,(topic,addon.__beyond_ui_integration__.status)
   d=next(iter(router.dialogs.values()));state['dialog']=d
   animated=topic in addon.onboarding.HELP_MEDIA
   if animated and not lib.leases and state['wait']<15:
    state['wait']+=1;return .2
   assert not lib.errors,lib.errors
   assert bool(lib.leases)==animated,(topic,len(lib.leases))
   widgets=[c.options.get('widget') for c in d.canvas.controls.values()]
   state['widgets']=[w for w in widgets if getattr(w,'library',None) is lib]
   state['frames']=[getattr(w,'frame_token',None) for w in state['widgets']]
   state['textures']={w.key:lib.frames.get(w.key) for w in state['widgets']}
   assert d.host.records[d.host.key].get('backdrop'),topic
  elif n==2:
   if topic in addon.onboarding.HELP_MEDIA:
    # Scheduler frame identity, independent of whether its bounded cache was warm.
    assert lib.leases and bpy.app.timers.is_registered(lib._timer),topic
    assert all(lib.frames.get(key) is not old for key,old in state['textures'].items()),(topic,'Playback stalled')
   with bpy.context.temp_override(window=window,area=area,region=region):window.event_simulate(type='ESC',value='PRESS')
  elif n==3:
   assert not router.dialogs,topic
   assert not lib.leases,(topic,list(lib.leases))
   assert not bpy.app.timers.is_registered(lib._timer),topic
   checks.append(dict(topic=topic,custom_popup=True,glass=True,animated=topic in addon.onboarding.HELP_MEDIA,closed_and_idle=True))
   state['index']+=1;state['step']=0
   if state['index']==len(state['topics']):finish();return None
   return .2
  state['step']+=1
  return .7
 except Exception:finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=1)
