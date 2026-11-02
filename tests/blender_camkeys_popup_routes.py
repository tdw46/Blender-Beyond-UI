"""Historical consumer fixture; use blender_camkeys_popover_audit for late-window captures."""
import bpy, gpu, sys, os, json, traceback, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from capture_controls import png
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
window=bpy.context.window
area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
ui_region=next(r for r in area.regions if r.type=='UI')
area.spaces.active.show_region_ui=True
state=dict(step=0,captures=[],geometry=[],pending=None,live_values=[])
handle=None
out=Path(os.environ['BEYOND_UI_TEST_RESULT']).with_suffix('');out.mkdir(exist_ok=True)

def capture():
    if not state['pending'] or bpy.context.region.as_pointer()!=region.as_pointer():return
    w,h=region.width,region.height
    pixels=gpu.state.active_framebuffer_get().read_color(0,0,w,h,4,0,'UBYTE')
    pixels.dimensions=w*h*4
    png(out/(state['pending']+'.png'),w,h,bytes(pixels))
    state['captures'].append(state['pending']);state['pending']=None

def geometry(host):
    x,y,w,h=host.canvas.overlay['rect']; rx,ry,rw,rh=host.rect;scale=host.scale
    assert x>=0 and y>=0 and x+w<=rw/scale+.01 and y+h<=rh/scale+.01
    # Window-level presentation includes the sidebar instead of displacing popups.
    if ui_region.width>1 and ui_region.x<region.x+region.width:
        assert region.x+rx+rw>=ui_region.x+ui_region.width-.01
    record=host.records[host.key]
    assert record.get('valid') and not host.reason, host.reason
    widget=host.canvas.overlay.get('widget')
    if hasattr(widget,'model') and hasattr(widget.model,'context'):
        with bpy.context.temp_override(window=window,area=area,region=ui_region):
            assert widget.valid(widget.model.context,poll=False)
    assert record.get('backdrop') is not None, record.get('glass_error')
    state['geometry'].append(dict(surface=host.canvas.overlay['rect'],host=host.rect,sidebar=(ui_region.x,ui_region.width),glass=True))

def close_event():
    window.event_simulate(type='ESC',value='PRESS',x=region.x+20,y=region.y+40)
    window.event_simulate(type='ESC',value='RELEASE',x=region.x+20,y=region.y+40)

def finish(error=None):
    global handle
    if handle:bpy.types.SpaceView3D.draw_handler_remove(handle,'WINDOW');handle=None
    h=getattr(addon,'__beyond_ui_integration__',None)
    if h and h.router:h.router.dismiss()
    result=dict(passed=error is None,error=error,version=bpy.app.version_string,captures=state['captures'],geometry=state['geometry'],live_values=state['live_values'])
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
    bpy.ops.wm.quit_blender()

def tick():
    global handle
    try:
        n=state['step']
        if n==0:
            addon.register();bpy.context.window_manager.EnableCamKeys=False
            item=bpy.context.scene.mesh_object_items.add();item.object=bpy.data.objects['Cube']
            bpy.context.scene.mesh_object_items_index=0
            item.auto_fov_flatten_falloff_type='CUSTOM';item.auto_fov_short_lens_falloff_type='CUSTOM'
        elif n==1:
            ui_region.active_panel_category='CamKeys'
            from camkeys_qa._vendor.beyond_ui import Layout
            from camkeys_qa._vendor.beyond_ui.list_identity import PendingListIdentity
            obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis');shape=obj.shape_key_add(name='Cam_Left')
            row=obj.angle_items.add();row.name='Cam_Left';row.shapekey='Cam_Left';obj.angle_items_index=0
            integration=addon.__beyond_ui_integration__
            try:integration.list_ids.prepare(obj,'angle_items')
            except PendingListIdentity:integration.list_ids.flush()
            with bpy.context.temp_override(window=window,area=area,region=ui_region):
                layout=Layout(context=bpy.context,**integration.ui.layout_options)
                layout.template_list('CAMSHAPEMATIC_UL_angle_items','',obj,'angle_items',obj,'angle_items_index',rows=4)
                layout.canvas.arrange(420)
                widget=next(c.options['widget'] for c in layout.canvas.controls.values() if c.kind=='widget')
                child=next(iter(widget.row_map.values()))[0]
                label=next((c for c in child.controls.values() if c.kind=='label' and c.label==f'{shape.value:.3f}'),None)
                assert label is not None, [(c.kind,c.label) for c in child.controls.values()]
                builds=widget.builds
                for value in (0.251,0.75,0.221):
                    shape.value=value;widget.refresh_display()
                    assert label.label==f'{value:.3f}',label.label
                    assert widget.builds==builds
                    state['live_values'].append(label.label)
                layout.canvas.park()
            with bpy.context.temp_override(window=window,area=area,region=ui_region):
                assert bpy.ops.camkeys.ui_appearance('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
            handle=bpy.types.SpaceView3D.draw_handler_add(capture,(),'WINDOW','POST_PIXEL')
            state['pending']='appearance';region.tag_redraw()
        elif n==2:
            geometry(next(iter(addon.__beyond_ui_integration__.router.dialogs.values())).host)
            close_event()
        elif n==3:
            router=addon.__beyond_ui_integration__.router
            assert not router.dialogs
            with bpy.context.temp_override(window=window,area=area,region=ui_region):
                assert bpy.ops.camkeys.open_flatten_falloff_popover('INVOKE_DEFAULT')=={'FINISHED'}
            assert router.menus and not any(f['route']=='call_panel' for f in router.fallbacks),router.fallbacks
            host=next(iter(router.menus.values()))
            child=host.canvas.overlay['widget'].canvas
            assert any(c.kind=='widget' and getattr(c.options['widget'],'brush',False) for c in child.controls.values())
            # Register after the new popup draw callback to capture its final pixels.
            bpy.types.SpaceView3D.draw_handler_remove(handle,'WINDOW')
            handle=bpy.types.SpaceView3D.draw_handler_add(capture,(),'WINDOW','POST_PIXEL')
            state['pending']='custom-falloff';region.tag_redraw()
        elif n==4:
            geometry(next(iter(addon.__beyond_ui_integration__.router.menus.values())))
            close_event()
        elif n==5:
            assert not addon.__beyond_ui_integration__.router.menus
            assert state['captures']==['appearance','custom-falloff'],state
            addon.unregister();finish();return None
        state['step']+=1
        return .7
    except Exception:
        finish(traceback.format_exc());return None
bpy.app.timers.register(tick,first_interval=1)
