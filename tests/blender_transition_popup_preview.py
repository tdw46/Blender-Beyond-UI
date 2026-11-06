"""Real invoke routing into the existing curve panel and velocity scheduling."""
import bpy,sys,os,json,traceback,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];source=Path(os.environ.get('CAMKEYS_SOURCE', str(Path(__file__).resolve().parents[2]/'CamKeys-beyond-ui')))
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
state={'step':0}
direction=os.environ.get('BUI_TRANSITION_DIRECTION','FRONT')
key=direction.lower()
def tick():
 try:
  if state['step']==0:
   addon.register();bpy.context.window_manager.EnableCamKeys=False
   item=bpy.context.scene.mesh_object_items.add();item.object=bpy.data.objects['Cube'];item.auto_fov_transition_front_type='SMOOTH';state['item']=item
   area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
   with bpy.context.temp_override(area=area,region=region,camkeys_falloff_owner=item,camkeys_subject_transition_owner=item):
    assert bpy.ops.camkeys.open_subject_transition('INVOKE_DEFAULT',direction=direction)=={'FINISHED'}
   state['step']=1;return .6
  router=addon.__beyond_ui_integration__.router
  assert router.menus and not any(x['route']=='call_panel' for x in router.fallbacks),router.fallbacks
  host=next(iter(router.menus.values()));widget=host.canvas.overlay['widget'];child=widget.canvas
  assert any(c.kind=='widget' and getattr(c.options['widget'],'brush',False) for c in child.controls.values())
  assert any(c.label=='Front View Plane' for c in child.controls.values())
  curve=next(c.options['widget'] for c in child.controls.values() if c.kind=='widget' and getattr(c.options['widget'],'brush',False))
  from types import SimpleNamespace
  from camkeys_qa import utils,custom_curve_lifecycle as life
  item=state['item'];item.auto_fov_control_mode='SUBJECT_SIZE';item.auto_fov_size_front=2.;item.auto_fov_size_back=.5
  item.auto_fov_transition_front=1.;item.auto_fov_transition_back=1.;item.auto_fov_enabled=True
  spec2=importlib.util.spec_from_file_location('probe_fixture',source/'tests/blender_ray_volume.py');f=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(f)
  variant='legacy_4_2' if bpy.app.version<(4,5,0) else 'native_4_5' if bpy.app.version<(5,1,0) else 'native_5_1'
  g=f.load(source/'assets/geometry'/f'{variant}.blend')
  cam=bpy.context.scene.camera;cam.location=(0,0,0);cam.rotation_euler=(0,0,0);g.nodes['CK_AUTO_FOV_CAM_INFO'].inputs['Object'].default_value=cam
  mesh=bpy.data.meshes.new('Transition focus');mesh.from_pydata([(-.2,-.2,.8),(.2,.2,1.2)],[],[])
  focus=bpy.data.objects.new('Transition focus',mesh);bpy.context.scene.collection.objects.link(focus)
  mesh=bpy.data.meshes.new('Transition probes');mesh.from_pydata([(.1,0,.64),(.1,0,1.36)],[],[])
  obj=bpy.data.objects.new('Transition probes',mesh);bpy.context.scene.collection.objects.link(obj)
  common={'Camera Forward':(0,0,1),'Use Focus Center':True,'Focus Center':(0,0,1),'Use External Focus Object':True,'Focus Object':focus,'Projection Near':.01}
  def drive(scene):
   utils._drive_auto_fov_for_item(item,target_obj=obj,group=g,focus_center=(0,0,1),projection_values=common)
   f.assign(next(m for m in obj.modifiers if m.type=='NODES'),common)
  def coords():return [tuple(v.co) for v in f.read(obj).vertices]
  life._refresh=drive
  drive(bpy.context.scene);baseline=coords()
  a,b,w,h=curve.graph
  curve.event(SimpleNamespace(type='LEFTMOUSE',value='PRESS'),a+w*.4,b+h*.2)
  curve.event(SimpleNamespace(type='MOUSEMOVE',value='NOTHING'),a+w*.42,b+h*.25)
  assert getattr(state['item'],'auto_fov_transition_'+key+'_type')=='CUSTOM', ('NOT_CUSTOM',widget.model.pointers.values())
  assert curve.capturing
  life._flush_previews();updated=coords()
  assert max(abs(a-b) for x,y in zip(baseline,updated) for a,b in zip(x,y))>1e-4,(baseline,updated)
  assert [tuple(p.location) for p in g.nodes['CK_SUBJECT_'+direction+'_CURVE'].mapping.curves[0].points]==list(curve.binding.read())
  curve.event(SimpleNamespace(type='LEFTMOUSE',value='RELEASE'),a+w*.42,b+h*.25)
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
  result={'passed':True,'version':bpy.app.version_string,'custom_curve_routed':True,'geometry_changed_mid_drag':True,'owner_retained':True,'direction':direction,'fallbacks':router.fallbacks,'velocity_scheduled':True,'offscreen_cancelled':True}
 except Exception:result={'passed':False,'error':traceback.format_exc()}
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));addon.unregister();bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.2)
 return None
bpy.app.timers.register(tick,first_interval=1)
