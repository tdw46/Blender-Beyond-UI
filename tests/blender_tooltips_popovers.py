"""Actual CamKeys cog, RNA/operator descriptions, tooltip rendering and fallback."""
import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS
root=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',root/'__init__.py',submodule_search_locations=[str(root)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='UI')
area.spaces.active.show_region_ui=True
state={'step':0};checks=[]

class BUI_PT_fallback(bpy.types.Panel):
    bl_label='Fallback fixture';bl_space_type='VIEW_3D';bl_region_type='WINDOW'
    def draw(self,context):self.layout.label(text='Native recovery')


def finish(error=None):
    if 'canvas' in state:state['canvas'].cancel()
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps({'passed':error is None,'error':error,'checks':checks,'version':bpy.app.version_string},indent=2))
    bpy.ops.wm.quit_blender()


def tick():
 try:
  n=state['step']
  if n==0:
   addon.register();bpy.context.window_manager.EnableCamKeys=False
   item=bpy.context.scene.mesh_object_items.add();item.object=bpy.data.objects['Cube']
   cfg=item.stepped_turnaround;cfg.use_billboard_groups=True
   g=cfg.billboard_groups.add();g.name='Body';g.root_bone='Hips'
   state['item']=item
   bpy.utils.register_class(BUI_PT_fallback)
  elif n==1:
   from camkeys_qa._vendor.beyond_ui import Layout
   from camkeys_qa._vendor.beyond_ui.tooltips import active,description
   from camkeys_qa._vendor.beyond_ui.list_identity import PendingListIdentity
   from camkeys_qa._vendor.beyond_ui.hosts.floating import FloatingHost
   integration=addon.__beyond_ui_integration__
   try:integration.list_ids.prepare(state['item'].stepped_turnaround,'billboard_groups')
   except PendingListIdentity:integration.list_ids.flush()
   with bpy.context.temp_override(window=window,area=area,region=region):
    ui=Layout(context=bpy.context,**integration.ui.layout_options)
    addon.stepped_turnaround.draw(ui,state['item']);ui.canvas.arrange(420)
    cog=next(c for c in ui.canvas.controls.values() if c.options.get('panel_model'))
    assert cog.enabled
    assert ui.canvas.open_panel(cog,(0,0,420,650),bpy.context),ui.canvas.menu_error
    assert ui.canvas.overlay and not getattr(ui.canvas,'popup_fallbacks',[])
    popup=ui.canvas.overlay['widget']; child=popup.canvas
    lists=[c.options['widget'] for c in child.controls.values() if c.kind=='widget' and hasattr(c.options['widget'],'row_map')]
    assert lists and lists[0].row_map
    checks.append('Real Billboard Emulation cog opens custom popover with nested registered list and captured owner')
    ui.canvas.cancel()
    # Render through the actual floating host: shared glass/text/motion path.
    host=FloatingHost('tooltip-fixture',bpy.context)
    ui=Layout(host.canvas,bpy.context)
    ui.prop(bpy.context.scene.render,'film_transparent')
    ui.operator('camkeys.billboard_groups',text='Create groups').action='DEFAULTS'
    ui.canvas.arrange(400);host.size()
    control=next(c for c in ui.canvas.controls.values() if c.binding is not None)
    text=description(control,bpy.context)
    assert text==bpy.types.RenderSettings.bl_rna.properties['film_transparent'].description,text
    op=next(c for c in ui.canvas.controls.values() if c.options.get('operator_id'))
    assert description(op,bpy.context)
    host.start();state.update(host=host,canvas=ui.canvas,control=control)
    x,y,w,h=control.rect
    ui.canvas.event(NS(type='MOUSEMOVE',value='NOTHING'),x+w/2,y+h/2,host.clip,context=bpy.context)
    assert active(ui.canvas) is not None
    state['text']=text
  elif n==2:
   from camkeys_qa._vendor.beyond_ui.tooltips import active
   host=state['host'];tip=active(host.canvas)
   assert tip and tip.tooltip, repr({'tip':tip, 'pending':tip.tip_pending if tip else None,'keys':host._tooltip_keys,'visible':host.canvas.visible,'record':host.records[host.key],'reason':host.reason})
   assert not bpy.app.timers.is_registered(host._tooltip_callback),'Tooltip kept polling'
   assert host.records[host.key].get('backdrop'),host.reason
   checks.append('Native property/operator descriptions, delayed tooltip, real glass draw and finite timer work')
   host.close()
   from camkeys_qa._vendor.beyond_ui import Layout
   with bpy.context.temp_override(window=window,area=area,region=region):
    ui=Layout(context=bpy.context);ui.popover('BUI_PT_fallback');ui.canvas.arrange(400)
    c=next(iter(ui.canvas.controls.values()));model=c.options['panel_model']
    def fail(*args):raise RuntimeError('Injected custom layout failure')
    model.build=fail
    assert ui.canvas.open_panel(c,(0,0,400,500),bpy.context),ui.canvas.menu_error
    assert ui.canvas.overlay is None and ui.canvas.popup_fallbacks[-1]['custom'] is False
    checks.append('Failed custom popover opens native recovery and records the original error')
  elif n==3:
   finish();return None
  state['step']+=1;return 1.0
 except Exception:
  finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=.6)
