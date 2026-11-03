"""All CamKeys routes retain step 3 when a double-click reaches the new page."""
import bpy, os, sys, json, traceback, importlib.util
from pathlib import Path
from types import SimpleNamespace as NS

source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
checks=[]

def run():
 try:
  addon.register()
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
  ob=addon.onboarding
  runtime=addon.__beyond_ui_integration__.ui._runtime
  area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
  region=next(r for r in area.regions if r.type=='WINDOW')
  target=bpy.data.objects['Cube'];target.shape_key_add(name='Basis');target.shape_key_add(name='Smile')
  with bpy.context.temp_override(area=area,region=region):
   state=bpy.context.scene.camkeys_setup;state.target=target;state.source='VIEWPORT'
   area.spaces.active.region_3d.view_perspective='PERSP'
   area.spaces.active.region_3d.update()
   def page():
    layout=Layout(context=bpy.context)
    runtime.draw_functions[ob.CAMKEYS_PT_setup](PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
    layout.canvas.arrange(420)
    return layout.canvas
   def click(canvas,label,value):
    control=next(c for c in canvas.controls.values() if c.label==label)
    x,y,w,h=control.rect
    assert canvas.event(NS(type='LEFTMOUSE',value=value),x+w/2,y+h/2,(0,0,420,canvas.height),context=bpy.context)
   for route in ('ANGLES','PERSPECTIVE','DOLLY'):
    state.route=route;state.step=1;state.dismissed=False;state.force=bool(bpy.context.scene.mesh_object_items)
    first=page();click(first,'Next','PRESS');first.park()
    assert state.step==2 and ob.visible(bpy.context), (route,state.step,state.error)
    second=page();click(second,'Open full controls','DOUBLE_CLICK')
    assert state.step==2 and ob.visible(bpy.context), route
    assert not state.dismissed
    click(second,'Open full controls','PRESS');second.park()
    assert not ob.visible(bpy.context), route
    checks.append(route+': Next reaches step 3, double-click cannot exit, deliberate Open still works')
  result=dict(passed=True,checks=checks,version=bpy.app.version_string,status=runtime.status())
 except Exception:
  result=dict(passed=False,checks=checks,error=traceback.format_exc())
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(run,first_interval=1)
