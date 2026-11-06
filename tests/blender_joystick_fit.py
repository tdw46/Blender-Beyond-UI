"""Dense width sweep catches intermediate wrapping and hysteresis."""
import bpy,sys,os,json,traceback,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=Path(os.environ.get('CAMKEYS_SOURCE', str(Path(__file__).resolve().parents[2]/'CamKeys-beyond-ui')))
spec=importlib.util.spec_from_file_location('camkeys_fit',SOURCE/'__init__.py',submodule_search_locations=[str(SOURCE)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon
try:
 spec.loader.exec_module(addon);addon.register()
 from camkeys_fit import subject_size,ui_theme
 from camkeys_fit._vendor.beyond_ui import Layout,style
 from camkeys_fit._vendor.beyond_ui.flow import Plan
 item=bpy.context.scene.mesh_object_items.add()
 ui=Layout(context=bpy.context);ui_theme.STUDIO.apply(ui.canvas);ui.canvas.panel_layout=True
 subject_size.draw(ui,item)
 identities=[id(c) for c in ui.canvas.controls.values()]
 measured={};states=set()
 for width in list(range(500,219,-1))+list(range(220,501)):
  ui.canvas.arrange(width)
  current=tuple(sorted(ui.canvas._responsive_fit_states));states.update(current)
  if width in measured:assert current==measured[width],('hysteresis',width,current,measured[width])
  measured[width]=current
  assert identities==[id(c) for c in ui.canvas.controls.values()]
  for profile in ui.canvas._responsive_fit_profiles:
   pad,values,reset=profile['parts']
   assert abs(pad.rect[2]-(64 if 'view_planes.compact' in current else 90))<1e-5,(width,current,pad.rect)
   assert abs(pad.rect[1]+pad.rect[3]/2-values.rect[1]-values.rect[3]/2)<1e-5,('fields wrapped',width,pad.rect,values.rect)
   if reset.options.get('display')!='none':
    assert abs(pad.rect[1]+pad.rect[3]/2-reset.rect[1]-reset.rect[3]/2)<1e-5,('reset wrapped',width)
   fields=[c for c in values.children if not hasattr(c,'children')]
   assert all(not c.options.get('_entry_stacked') for c in fields),('XY stacked',width)
 assert states=={'view_planes.header','view_planes.compact'},states
 # More parent padding must cause the same content-fit stages at a wider host width.
 before=next(w for w in range(500,219,-1) if measured[w]==('view_planes.header',))
 style(ui,scope='group',padding=(0,20))
 after=None
 for width in range(550,219,-1):
  ui.canvas.arrange(width)
  if ui.canvas._responsive_fit_states.get('view_planes.header'):after=width;break
 assert after==before+40,(before,after)
 ui.canvas.park()
 result={'passed':True,'version':bpy.app.version_string,'resize_checks':562,'reset_header_threshold':before,'with_extra_padding':after,'states':sorted(states)}
except Exception:result={'passed':False,'error':traceback.format_exc()}
try:addon.unregister()
except Exception:pass
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));print(result)
