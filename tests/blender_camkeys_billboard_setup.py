"""Disposable Uraraka: body-only repair, actual custom dialog input and opt-in setup."""
import bpy,os,sys,json,traceback,importlib.util,time
from pathlib import Path
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
state={'step':0};checks=[];durations=[]

def finish(error=None):
 router=addon.__beyond_ui_integration__.router
 result=dict(passed=error is None,error=error,checks=checks,version=bpy.app.version_string,setup_seconds=durations,router_error=router.error,fallbacks=router.fallbacks)
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
 router.dismiss();bpy.ops.wm.quit_blender()

def click(d,control):
 x,y,w,h=d.host.canvas.overlay['rect'];a,b,c,e=control.rect;s=d.host.scale
 px=int(d.host.region.x+d.host.rect[0]+(x+a+c/2)*s)
 py=int(d.host.region.y+d.host.rect[1]+d.host.rect[3]-(y+b+e/2)*s)
 for kind,value in [('MOUSEMOVE','NOTHING'),('LEFTMOUSE','PRESS'),('LEFTMOUSE','RELEASE')]:
  bpy.context.window.event_simulate(type=kind,value=value,x=px,y=py)

def tick():
 try:
  from camkeys_qa import billboard_emulation as bb
  item=bpy.context.scene.mesh_object_items[bpy.context.scene.mesh_object_items_index];cfg=item.stepped_turnaround
  window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
  router=addon.__beyond_ui_integration__.router;n=state['step']
  if n==0:
   # Public VRM addon isn't loaded in the disposable profile; use its verified
   # live bone mapping, still validating bone existence against the saved rig.
   mapping=json.loads(Path(os.environ['CAMKEYS_BILLBOARD_MAPPING']).read_text())['mapping']
   bb.humanoid_map=lambda rig:{k:v for k,v in mapping.items() if rig is not None and v in rig.data.bones}
   cfg['enabled']=False;cfg['use_billboard_groups']=False;cfg.billboard_groups.clear()
   bb._add(cfg,'body',mapping['hips'],body=True)
   assert bb.needs_default_groups(cfg)
   with bpy.context.temp_override(window=window,area=area,region=region):
    bpy.ops.ed.undo_push(message='Before billboard setup')
    result=bpy.ops.camkeys.billboard_groups('INVOKE_DEFAULT',action='DEFAULTS',item_index=bpy.context.scene.mesh_object_items_index)
   assert result=={'RUNNING_MODAL'},result
  elif n==1:
   assert len(router.dialogs)==1,(router.error,router.fallbacks)
   d=next(iter(router.dialogs.values()))
   assert not d.host.reason,d.host.reason
   assert len([c for c in d.canvas.controls.values() if c.kind=='search'])==2
   click(d,d.canvas.controls['confirm']);state['confirmation_start']=time.perf_counter()
  elif n==2:
   assert not router.dialogs,(router.error,[(d.outcome,d.host.reason) for d in router.dialogs.values()])
   assert len(cfg.billboard_groups)==2 and cfg.billboard_ready,(len(cfg.billboard_groups),cfg.billboard_status)
   assert {g.root_bone for g in cfg.billboard_groups}=={mapping_name for mapping_name in (bb.humanoid_map(bb.rig_for(item))['hips'],bb.humanoid_map(bb.rig_for(item))['head'])}
   checks.append('Body-only setup opens a custom two-field dialog; simulated confirmation creates head/body and releases modal input')
   cfg['use_billboard_groups']=False;cfg.billboard_groups.clear()
   begin=time.perf_counter();cfg.use_billboard_groups=True;durations.append(time.perf_counter()-begin)
   assert len(cfg.billboard_groups)==2 and cfg.billboard_ready,cfg.billboard_status
   checks.append('Enabling Separate Billboards creates and compiles missing groups in the property update')
   names=[(g.name,g.root_bone) for g in cfg.billboard_groups]
   cfg.use_billboard_groups=False;cfg.use_billboard_groups=True
   assert names==[(g.name,g.root_bone) for g in cfg.billboard_groups]
   checks.append('Repeated off/on preserves existing groups without duplicates')
   # No guessed head or partial body on unmapped rigs: preserve a useful manual path.
   mapped = bb.humanoid_map
   cfg['use_billboard_groups']=False;cfg.billboard_groups.clear();bb.humanoid_map=lambda rig:{}
   cfg.use_billboard_groups=True
   assert not cfg.billboard_groups and not cfg.billboard_ready and 'head bone' in cfg.billboard_status
   with bpy.context.temp_override(window=window,area=area,region=region):
    assert bpy.ops.camkeys.billboard_groups('EXEC_DEFAULT',action='DEFAULTS',root_bone='Head',body_bone='Hips',item_index=bpy.context.scene.mesh_object_items_index)=={'FINISHED'}
   bb.humanoid_map=mapped
   assert len(cfg.billboard_groups)==2 and cfg.billboard_ready,cfg.billboard_status
   checks.append('Unmapped rig reports manual selection; explicit head/body selection succeeds without native fallback')
   # Reopen an unrelated dialog to prove input isn't stranded after confirmation.
   with bpy.context.temp_override(window=window,area=area,region=region):
    assert bpy.ops.camkeys.ui_appearance('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
  elif n==3:
   d=next(iter(router.dialogs.values()));click(d,d.canvas.controls['cancel'])
  elif n==4:
   assert not router.dialogs and not router.error,router.error
   checks.append('Subsequent Appearance dialog still opens and cancels through simulated input')
   finish();return None
  state['step']+=1;return .7
 except Exception:finish(traceback.format_exc());return None

def start():
 addon.register()
 bpy.ops.wm.open_mainfile(filepath=os.environ['BEYOND_UI_CRASH_FILE'],load_ui=True,use_scripts=False)
 bpy.context.window_manager.EnableCamKeys=False
 bpy.app.timers.register(tick,first_interval=2)
bpy.app.timers.register(start,first_interval=1)
