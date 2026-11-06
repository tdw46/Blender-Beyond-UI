"""Real invoke routing into the existing curve panel and velocity scheduling."""
import bpy,sys,os,json,traceback,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];source=Path(os.environ.get('CAMKEYS_SOURCE', str(Path(__file__).resolve().parents[2]/'CamKeys-beyond-ui')))
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
state={'step':0}
def tick():
 try:
  if state['step']==0:
   addon.register();bpy.context.window_manager.EnableCamKeys=False
   item=bpy.context.scene.mesh_object_items.add();item.object=bpy.data.objects['Cube'];item.auto_fov_transition_front_type='CUSTOM';state['item']=item
   area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
   with bpy.context.temp_override(area=area,region=region,camkeys_falloff_owner=item,camkeys_subject_transition_owner=item):
    assert bpy.ops.camkeys.open_subject_transition('INVOKE_DEFAULT',direction='FRONT')=={'FINISHED'}
   state['step']=1;return .6
  router=addon.__beyond_ui_integration__.router
  assert router.menus and not any(x['route']=='call_panel' for x in router.fallbacks),router.fallbacks
  host=next(iter(router.menus.values()));widget=host.canvas.overlay['widget'];child=widget.canvas
  assert any(c.kind=='widget' and getattr(c.options['widget'],'brush',False) for c in child.controls.values())
  assert any(c.label=='Front View Plane' for c in child.controls.values())
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa import subject_size
  from types import SimpleNamespace
  ui=Layout(context=bpy.context);subject_size.draw(ui,state['item']);ui.canvas.arrange(380)
  control=next(c for c in ui.canvas.controls.values() if c.kind=='widget' and c.options['widget'].__class__.__name__=='Joystick');pad=control.options['widget']
  pad.clock=lambda:1.;pad.event(SimpleNamespace(type='LEFTMOUSE',value='PRESS'),94,52);ui.canvas.widget_capture=control;pad.clock=lambda:1.05
  ui.canvas.advance_animations((0,0,380,ui.canvas.height));assert state['item'].auto_fov_offset_front[0]>0
  ui.canvas.advance_animations((10000,10000,1,1));assert ui.canvas.widget_capture is None and not pad.capturing
  assert tuple(state['item'].auto_fov_offset_front)==(0.,0.)
  ui.canvas.park();router.dismiss()
  result={'passed':True,'version':bpy.app.version_string,'custom_curve_routed':True,'fallbacks':router.fallbacks,'velocity_scheduled':True,'offscreen_cancelled':True}
 except Exception:result={'passed':False,'error':traceback.format_exc()}
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));addon.unregister();bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.2)
 return None
bpy.app.timers.register(tick,first_interval=1)
