"""Uraraka: all six consumer popover families must paint and survive real input."""
import bpy, os, sys, json, traceback, importlib.util
from pathlib import Path
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
state={'index':0,'phase':0};checks=[]

def finish(error=None):
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=error is None,error=error,version=bpy.app.version_string,checks=checks,saved=False),indent=2))
    bpy.ops.wm.quit_blender()

def point(host):
    # A passive motion inside the popover, not on any editable field.
    x,y,w,h=host.canvas.overlay['rect'];rx,ry,rw,rh=host.rect
    return dict(x=int(host.region.x+rx+(x+8)*host.scale),y=int(host.region.y+ry+rh-(y+8)*host.scale))

def tick():
    try:
        from camkeys_qa._vendor.beyond_ui import Layout
        router=addon.__beyond_ui_integration__.router
        config=addon.__beyond_ui_integration__.ui
        window=bpy.context.window or bpy.context.window_manager.windows[0];area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
        area.spaces.active.show_region_ui=True
        region=next(r for r in area.regions if r.type=='UI')
        item=bpy.context.scene.mesh_object_items[bpy.context.scene.mesh_object_items_index]
        cases=[('CAMKEYS_PT_lens_compensation',item),('CAMKEYS_PT_dolly_expressions',item),
               ('CAMKEYS_PT_billboard_settings',item),('CAMKEYS_PT_falloff_popover',item),
               ('CAMKEYS_PT_distance_falloff_popover',item),('CAMKEYS_PT_flatten_falloff_popover',item),
               ('flatten-operator',item),('appearance-dialog',item),('billboard-dialog',item),('dolly-shapes',item)]
        if item.object and len(item.object.angle_items):cases.append(('CAMKEYS_PT_falloff_popover',item.object.angle_items[0]))
        if state['index']>=len(cases):
            assert not [f for f in router.fallbacks if 'macro-step:' not in f['route']],router.fallbacks
            finish();return None
        name,owner=cases[state['index']]
        phase=state['phase']
        def live_hosts():
            return [*router.menus.values(),*(d.host for d in router.dialogs.values())]
        if phase==0:
            with bpy.context.temp_override(window=window,area=area,region=region):
                if name.endswith('-dialog'):
                    if name=='appearance-dialog':result=bpy.ops.camkeys.ui_appearance('INVOKE_DEFAULT')
                    else:result=bpy.ops.camkeys.billboard_groups('INVOKE_DEFAULT',action='ADD')
                    assert result=={'RUNNING_MODAL'},(name,result)
                    host=next(iter(router.dialogs.values())).host
                elif name=='flatten-operator':
                    assert bpy.ops.camkeys.open_flatten_falloff_popover('INVOKE_DEFAULT')=={'FINISHED'}
                    host=next(iter(router.menus.values()))
                else:
                    host=router.host(bpy.context)
                    layout=Layout(host.canvas,bpy.context,**config.layout_options)
                    for pointer in ('camkeys_falloff_owner','camkeys_billboard_owner','camkeys_dolly_item'):
                        layout.context_pointer_set(pointer,owner)
                    panel=name
                    if name=='dolly-shapes':
                        item.dolly_expression.mode='SHAPES'
                        panel='CAMKEYS_PT_dolly_expressions'
                    layout.popover(panel=panel,text='Open')
                    opener=next(c for c in host.canvas.controls.values() if c.options.get('panel_model'))
                    # Anchor inside the sidebar: late presentation must not displace it left.
                    ax=(region.x-host.region.x-host.rect[0]+region.width*.55)/host.scale
                    opener.rect=(ax, min(90, host.canvas.height*.15),24,24)
                    assert host.canvas.open_panel(opener,host.clip,bpy.context),host.canvas.menu_error
                    assert host.canvas.overlay is not None,host.canvas.popup_fallbacks
                    router.pending=host
                    ns,op=router.idname.split('.')
                    assert getattr(getattr(bpy.ops,ns),op)('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
            state['host']=host;state['bridge']=host.bridge
            original_draw=host._draw
            def capture_draw():
                original_draw()
                capture=state.pop('capture',None)
                if capture:
                    import gpu,struct,zlib
                    _,_,w,h=gpu.state.viewport_get()
                    pixels=gpu.state.active_framebuffer_get().read_color(0,0,w,h,4,0,'UBYTE')
                    pixels.dimensions=w*h*4;raw=bytes(pixels)
                    def chunk(kind,data):
                        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
                    rows=b''.join(b'\x00'+raw[y*w*4:(y+1)*w*4] for y in reversed(range(h)))
                    Path(capture).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
            host.bridge.window_overlays[window.as_pointer()]['owners'][id(host)] = capture_draw
        elif phase==1:
            host=state['host'];assert host in live_hosts(),(name,'dismissed before input')
            assert host.canvas.overlay is not None,(name,host.canvas.menu_error)
            assert host.records[host.key]['valid'] and not host.reason,(name,host.reason)
            assert host.records[host.key].get('backdrop'),(name,host.records[host.key].get('glass_error'))
            assert host.records[host.key].get('viewport_source'),(name,'not viewport-backed glass')
            from camkeys_qa._vendor.beyond_ui.gpu import glass
            state['productions']=glass._owners[host.records[host.key]['backdrop']]['productions']
            if name.startswith('CAMKEYS_PT_') or name=='dolly-shapes':
                ox,oy,ow,oh=host.canvas.overlay['rect']
                assert host.region.x+host.rect[0]+(ox+ow)*host.scale>region.x,(name,'pushed left of sidebar')
            child=host.canvas.overlay['widget'].canvas
            assert child.controls,(name,'empty panel')
            state['count']=len(child.controls)
            window.event_simulate(type='MOUSEMOVE',value='NOTHING',**point(host))
        elif phase==2:
            host=state['host'];assert host in live_hosts(),(name,'dismissed on mouse move')
            assert host.canvas.overlay is not None,(name,host.canvas.menu_error)
            from camkeys_qa._vendor.beyond_ui.gpu import glass
            productions=glass._owners[host.records[host.key]['backdrop']]['productions']
            assert productions==state['productions'],(name,'animation recaptured backdrop',productions,state['productions'])
            if name in {'CAMKEYS_PT_flatten_falloff_popover','appearance-dialog','CAMKEYS_PT_billboard_settings'}:
                # screen.screenshot re-composites regions and omits WM callbacks.
                # Read the actual late window framebuffer in our owned test callback.
                state['capture'] = str(Path(os.environ['BEYOND_UI_TEST_RESULT']).parent/(name+'.png'))
                window.as_pointer()
                host.region.tag_redraw()

            checks.append(dict(panel=name,owner_type=owner.bl_rna.identifier,controls=state['count'],painted=True,glass=True,viewport_source=True,window_overlay=True,backdrop_reused=True,survived_mousemove=True))
        elif phase==3:
            window.event_simulate(type='ESC',value='PRESS',**point(state['host']))
        elif phase==4:
            assert not router.menus and not router.dialogs,(name,'Escape did not close')
            assert not state['bridge'].window_overlays,(name,'window draw handle leaked')
            state['index']+=1;state['phase']=-1
        state['phase']+=1
        return .25
    except Exception:
        finish(traceback.format_exc());return None

def start():
    try:
        addon.register()
        bpy.ops.wm.open_mainfile(filepath=os.environ['BEYOND_UI_CRASH_FILE'],load_ui=True,use_scripts=False)
        bpy.context.window_manager.EnableCamKeys=False
        item=bpy.context.scene.mesh_object_items[bpy.context.scene.mesh_object_items_index]
        for prop in ('auto_fov_multi_falloff_type','auto_fov_falloff_type','auto_fov_flatten_falloff_type','auto_fov_short_lens_falloff_type'):
            setattr(item,prop,'CUSTOM')
        # Exercise list contents even when the saved camera compensation is empty.
        if not len(item.lens_compensation.stops):item.lens_compensation.stops.add()
        bpy.app.timers.register(tick,first_interval=2)
    except Exception:finish(traceback.format_exc())
    return None
bpy.app.timers.register(start,first_interval=1)
