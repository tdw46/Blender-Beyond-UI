"""Transition graph visibility, mid-drag custom activation, anchor and contexts."""
import bpy,sys,os,json,traceback,importlib.util
from pathlib import Path
source=Path(os.environ.get('CAMKEYS_SOURCE', str(Path(__file__).resolve().parents[2]/'CamKeys-beyond-ui')))
spec=importlib.util.spec_from_file_location('camkeys_curve_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon
try:
 spec.loader.exec_module(addon);addon.register()
 from camkeys_curve_qa import subject_size,utils,custom_curve_lifecycle as life
 from camkeys_curve_qa._vendor.beyond_ui import Layout
 from camkeys_curve_qa._vendor.beyond_ui.context_menu import Target
 from types import SimpleNamespace
 item=bpy.context.scene.mesh_object_items.add();item.object=bpy.data.objects['Cube']
 context=SimpleNamespace(scene=bpy.context.scene,camkeys_falloff_owner=item,camkeys_subject_transition_owner=item)
 life.prepare(context,'CAMKEYS_PT_flatten_falloff_popover')
 assert item.auto_fov_transition_front_type=='SMOOTH'
 def build():
  ui=Layout(context=bpy.context,preview=lambda data,prop:life.preview(context,data,prop))
  subject_size.draw_transition_curves(ui,item);ui.canvas.arrange(360)
  return ui,next(c.options['widget'] for c in ui.canvas.controls.values() if c.kind=='widget' and type(c.options['widget']).__name__=='CurveMapping')
 checks=[]
 for key in ('front','back'):
  item.auto_fov_subject_curve_tab=key.upper()
  ui,widget=build();assert widget.curve_lock_end
  value=subject_size.brush(item,key);mapping=utils.get_falloff_curve_mapping(value)
  points=widget.binding.read();index=max(range(len(points)),key=lambda i:points[i][0])
  hit=Target('curve',('point_field',0,index,1),widget.binding,value=lambda:0.)
  target=widget.binding.context_target(hit)
  assert not target.editable() and target.binding.read()==0.
  try:target.binding.write(.8);raise AssertionError('locked context accepted write')
  except ValueError:pass
  before=tuple(widget.binding.read());widget.binding.remove(index);assert widget.binding.read()==before
  a,b,w,h=widget.graph
  widget.event(SimpleNamespace(type='LEFTMOUSE',value='PRESS'),a+w-.1,b+h-.1)
  assert not widget.capturing
  widget.event(SimpleNamespace(type='LEFTMOUSE',value='PRESS'),a+w*.4,b+h*.2)
  widget.event(SimpleNamespace(type='MOUSEMOVE',value='NOTHING'),a+w*.42,b+h*.25)
  assert getattr(item,'auto_fov_transition_'+key+'_type')=='CUSTOM'
  assert tuple(max(mapping.curves[0].points,key=lambda p:p.location.x).location)==(1.,0.)
  widget.event(SimpleNamespace(type='LEFTMOUSE',value='RELEASE'),a+w*.42,b+h*.25)
  ui.canvas.park()
  # Existing preset/import commit route enforces the transition's end value.
  mapping.curves[0].points[-1].location=(1.,1.);mapping.update()
  life.commit_brush(context,value)
  assert tuple(mapping.curves[0].points[-1].location)==(1.,0.)
  for kind in ('LINEAR','SMOOTH','SPHERE','ROOT','SHARP','CUSTOM'):
   setattr(item,'auto_fov_transition_'+key+'_type',kind)
   ui,widget=build();assert widget.curve_lock_end;ui.canvas.park()
  checks.append(key)
 from camkeys_curve_qa import onboarding
 from camkeys_curve_qa._vendor.beyond_ui.popover import PanelContextCapture
 from camkeys_curve_qa._vendor.beyond_ui.registered_menu import ContextArguments
 with bpy.context.temp_override(transition_test_owner=item):
  captured=PanelContextCapture(bpy.context);assert captured.transition_test_owner==item
  args=ContextArguments();args.capture(captured.values)
 assert args.values()['transition_test_owner']==item
 tabs=Layout(context=bpy.context)
 onboarding.perspective_tabs(tabs,item,'auto_fov_control_mode',(('LENS','BUI_LENS'),('SUBJECT_SIZE','BUI_SUBJECT_SIZE')))
 choices=list(tabs.canvas.controls.values());assert len(choices)==2
 for width in (240,280,380):
  tabs.canvas.arrange(width)
  assert all(not c.options['menu_option'] and c.options['_inline_style']['font_weight']=='bold' for c in choices)
 choices[0].action();assert item.auto_fov_control_mode=='LENS'
 choices[1].action();assert item.auto_fov_control_mode=='SUBJECT_SIZE'
 assert choices[1].binding.context.owner()==item
 tabs.canvas.park()
 result={'passed':True,'version':bpy.app.version_string,'directions':checks,'preset_graphs':12,'retained_context':True,'segmented_exact_owner':True,'mid_drag_custom':True,'locked_endpoint':True,'context_copy_readable':True,'context_write_blocked':True}
except Exception:result={'passed':False,'error':traceback.format_exc()}
try:addon.unregister()
except Exception:pass
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));print(result)
