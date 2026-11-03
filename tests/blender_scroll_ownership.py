"""No-focus native sidebar -> custom list wheel routing; no scene is loaded/saved."""
import bpy,sys,os,json,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import registered_lists_fixture as data
from beyond_ui import AddonUI

class BUI_PT_scroll_ownership(bpy.types.Panel):
    bl_label='Scroll ownership'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Scroll Ownership'
    def draw(self,context):
        for i in range(3):self.layout.label(text='Native scrolling starts outside the list')
        self.layout.template_list('BUI_UL_registered','registered',context.scene,'bui_list_items',context.scene,'bui_list_active',rows=5)
        for i in range(45):self.layout.label(text=f'Below list {i}')

ui=AddonUI('scroll_ownership',layout_options={'list_identity':lambda owner,prop,item:item.uid})
state={'stage':0,'events':[]};checks=[]
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
area.spaces.active.show_region_ui=True
region=next(r for r in area.regions if r.type=='UI')

def finish(error=None):
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=error is None,error=error,checks=checks,events=state['events'],version=bpy.app.version_string),indent=2))
    ui.unregister();data.unregister();bpy.ops.wm.quit_blender()

def list_state():
    host=ui._runtime.hosts[BUI_PT_scroll_ownership]
    record=next(r for r in host.records.values() if r['valid'])
    c=next(c for c in record['canvas'].controls.values() if c.kind=='widget')
    return record,c,c.options['widget']

def point():
    r,c,w=list_state();x,y,ww,hh=r['rect'];s=ww/r['canvas']._width
    # Hit a row interior below the selected row's embedded fields.
    return int(region.x+x+(c.rect[0]+c.rect[2]*.5)*s),int(region.y+y+hh-(c.rect[1]+min(w.viewport*.65,110))*s)

def send(x,y,kind="WHEELDOWNMOUSE"):
    window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
    window.event_simulate(type=kind,value='PRESS',x=x,y=y)

def tick():
    try:
        n=state['stage']
        if n==0:
            data.register(50);ui.register(BUI_PT_scroll_ownership)
            old=ui._runtime.dispatch_event
            def observe(op,ctx,event):
                result=old(op,ctx,event)
                if event.type in {'WHEELDOWNMOUSE','WHEELUPMOUSE'}:
                    state['events'].append(sorted(result))
                    # Inactive windows do not execute native region keymaps.
                    # Exercise the native consumer explicitly after pass-through.
                    if result == {'PASS_THROUGH'}:
                        with bpy.context.temp_override(window=window,area=area,region=region):
                            if event.type=='WHEELUPMOUSE':bpy.ops.view2d.scroll_up()
                            else:bpy.ops.view2d.scroll_down()
                return result
            ui._runtime.dispatch_event=observe
        elif n==1:
            region.active_panel_category='Scroll Ownership'
        elif n==2:
            record,control,widget=list_state()
            assert ui._runtime.hosts[BUI_PT_scroll_ownership].bridge
            assert not ui._runtime.errors,ui._runtime.errors
            state['offset']=widget.offset;state['view']=region.view2d.region_to_view(0,0)[1]
            # A real scroll starts on ordinary labels before the custom list.
            x,y,w,h=record['rect'];s=w/record['canvas']._width
            send(int(region.x+x+w*.5),int(region.y+y+h-15*s))
        elif n==3:
            assert state['events'] and state['events'][-1]==['PASS_THROUGH'],state['events']
            send(*point())
        elif n==4:
            send(*point())
        elif n==5:
            record,control,widget=list_state()
            assert widget.offset==state['offset'],(widget.offset,state['offset'])
            assert all(v==['PASS_THROUGH'] for v in state['events']),state['events']
            assert region.view2d.region_to_view(0,0)[1]!=state['view'],'Native sidebar did not move'
            checks.append('Queued wheel events pass through after entering list; explicit native View2D consumer moves sidebar')
        elif n==6:
            state['list_before']=list_state()[2].offset
            send(*point())
        elif n==7:
            assert state['events'][-1]==['RUNNING_MODAL'],state['events']
            assert list_state()[2].offset>state['list_before'],(list_state()[2].offset,state['list_before'])
            checks.append('After quiet interval a new wheel gesture scrolls the list immediately')
            widget=list_state()[2];widget.scroll_to(widget.limit)
            state['edge_view']=region.view2d.region_to_view(0,0)[1]
            send(*point())
        elif n==8:
            widget=list_state()[2]
            assert state['events'][-1]==['PASS_THROUGH'],state['events']
            assert widget.offset==widget.limit
            assert region.view2d.region_to_view(0,0)[1]<state['edge_view']
            checks.append('At bottom, continued downward wheel passes to native parent without changing list offset')
            send(*point())
        elif n==9:
            assert state['events'][-1]==['PASS_THROUGH'],state['events']
            list_state()[2].scroll_to(0)
        elif n==10:
            state['edge_view']=region.view2d.region_to_view(0,0)[1]
            send(*point(),kind='WHEELUPMOUSE')
        elif n==11:
            assert state['events'][-1]==['PASS_THROUGH'],state['events']
            assert list_state()[2].offset==0
            assert region.view2d.region_to_view(0,0)[1]>state['edge_view']
            checks.append('At top, continued upward wheel passes to native parent without changing list offset')
            assert not ui._runtime.errors and not ui._runtime.input_errors
            finish();return None
        state['stage']+=1
        return 1 if n in (0,1) else (.45 if n in (5,9) else .07)
    except Exception:finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=1)
