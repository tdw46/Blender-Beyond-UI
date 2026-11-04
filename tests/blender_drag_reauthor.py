"""Native N-panel scalar drag across conditional accessories retains scroll."""
import os,sys,json,traceback
from pathlib import Path
import bpy
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT))
from beyond_ui import AddonUI
from beyond_ui.hosts.addon import Runtime
from beyond_ui.scalar_geometry import slider_parts

class BUI_PT_drag_reauthor(bpy.types.Panel):
    bl_label='Conditional slider';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Drag QA'
    def draw(self,context):
        for i in range(8):self.layout.label(text=f'Heading {i}')
        row=self.layout.row();row.prop(context.scene,'bui_drag_value',text='Lens',slider=True)
        row.operator('wm.search_menu',text='',icon='SPHERE' if context.scene.bui_drag_value>50 else 'LINCURVE')
        for i in range(40):self.layout.label(text=f'Below {i}')

commits=[];ui=AddonUI('drag_reauthor',commit=lambda a,b:commits.append((a,b)))
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
area.spaces.active.show_region_ui=True
region=next(r for r in area.regions if r.type=='UI');state={'step':0};checks=[]
def current():
    record=next(r for r in ui._runtime.hosts[BUI_PT_drag_reauthor].records.values() if r['valid'])
    return record,record['canvas']
def emit(kind,value='PRESS',fraction=.3):
    record,canvas=current();control=next(c for c in canvas.controls.values() if c.kind=='number')
    _,(tx,ty,tw),_=slider_parts(control.rect,bool(control.label),stacked=control.options.get('_slider_stacked'),
        label_width=control.options.get('_slider_label_width'),label_band=control.options.get('_label_band',24),value_width=control.options.get('value_width',53))
    rx,ry,rw,rh=record['rect'];x=int(region.x+rx+(tx+fraction*tw)*rw/canvas._width);y=int(region.y+ry+rh-ty*rh/canvas.height)
    assert region.y<=y<region.y+region.height,(y,region.y,region.height)
    window.event_simulate(type=kind,value=value,x=x,y=y)
def finish(error=None):
    ui.unregister()
    if BUI_PT_drag_reauthor.is_registered:bpy.utils.unregister_class(BUI_PT_drag_reauthor)
    del bpy.types.Scene.bui_drag_value
    result=dict(passed=error is None,error=error,checks=checks,commits=commits,version=bpy.app.version_string)
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));bpy.ops.wm.quit_blender()
def tick():
    try:
        n=state['step']
        if n==0:
            bpy.types.Scene.bui_drag_value=bpy.props.FloatProperty(default=30,min=0,max=100)
            bpy.utils.register_class(BUI_PT_drag_reauthor)
            ui._runtime=Runtime(ui,[BUI_PT_drag_reauthor],adopt=True);ui._runtime.register()
        elif n==1:region.active_panel_category='Drag QA'
        elif n==2:
            with bpy.context.temp_override(window=window,area=area,region=region):
                for _ in range(2):bpy.ops.view2d.scroll_down()
        elif n==3:
            record,canvas=current();state.update(canvas=canvas,height=canvas.height,scroll=tuple(region.view2d.region_to_view(0,0)))
            emit('MOUSEMOVE','NOTHING');emit('LEFTMOUSE')
        elif n==4:
            assert state['canvas'].edit is not None,'Mouse press did not begin edit'
            emit('MOUSEMOVE','NOTHING',.7)
        elif n==5:
            _,canvas=current();assert canvas is state['canvas'];assert canvas.edit is not None
            assert bpy.context.scene.bui_drag_value>50,bpy.context.scene.bui_drag_value
            assert canvas.height==state['height'];assert tuple(region.view2d.region_to_view(0,0))==state['scroll']
            emit('MOUSEMOVE','NOTHING',.4)
        elif n==6:
            assert current()[1] is state['canvas'];assert state['canvas'].edit is not None
            assert bpy.context.scene.bui_drag_value<50
            emit('MOUSEMOVE','NOTHING',.8)
        elif n==7:
            assert current()[1] is state['canvas'];assert state['canvas'].edit is not None
            assert bpy.context.scene.bui_drag_value>50
            emit('LEFTMOUSE','RELEASE',.8)
        elif n==8:
            assert len(commits)==1,commits
            assert bpy.context.scene.bui_drag_value>50
            assert tuple(region.view2d.region_to_view(0,0))==state['scroll']
            canvas=current()[1];assert canvas.edit is None
            assert any(c.options.get('icon')=='SPHERE' for c in canvas.controls.values())
            checks.append('Real simulated drag crosses conditional icon threshold three times without release, rollback, canvas replacement or scroll jump; one commit and fresh accessory after release')
            finish();return None
        assert not ui._runtime.errors,ui._runtime.errors
        state['step']+=1;area.tag_redraw();return .35
    except Exception:finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=.7)
