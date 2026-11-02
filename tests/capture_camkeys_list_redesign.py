"""Real consumer rows, shared search semantics, retained layouts and GPU captures."""
import bpy,gpu,sys,os,json,traceback,importlib.util,time,statistics
from pathlib import Path
from mathutils import Matrix
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT)]
from capture_controls import png
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
out=Path(os.environ['BEYOND_UI_TEST_RESULT']).with_suffix('');out.mkdir(exist_ok=True)

def run():
    try:
        from camkeys_qa._vendor.beyond_ui import Layout,style as bui_style
        from camkeys_qa._vendor.beyond_ui.gpu import glass,skin,typography
        from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state,measure
        from camkeys_qa._vendor.beyond_ui.search import clear_rect,field_rect
        from camkeys_qa._vendor.beyond_ui.list_identity import PendingListIdentity
        from camkeys_qa import ui_theme
        from menu_motion_batch import configure
        batch,batch_info=configure()
        obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis')
        for name,value in [('Cam_Left',.251),('Cam_Right',0),('Cam_Bottom',0),('Cam_Top',.221)]:
            obj.shape_key_add(name=name).value=value
            item=obj.angle_items.add();item.name=name;item.shapekey=name
        obj.angle_items_index=0
        integration=addon.__beyond_ui_integration__
        try:integration.list_ids.prepare(obj,'angle_items')
        except PendingListIdentity:integration.list_ids.flush()
        area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='UI')
        records=[];timings=[]
        with bpy.context.temp_override(area=area,region=region):
            ui=Layout(context=bpy.context,**integration.ui.layout_options)
            ui_theme.STUDIO.apply(ui.canvas)
            ui.title(text='CamKeys (Camera Angles + ShapeKeys)')
            row=ui.row();row.template_list('CAMSHAPEMATIC_UL_angle_items','',obj,'angle_items',obj,'angle_items_index',rows=4)
            bui_style(row,ui_theme.TWO_LINE_LIST)
            actions=row.column(align=True)
            for op,icon in [('add_angle_item','ADD'),('remove_angle_item','REMOVE')]:actions.operator('camkeys.'+op,text='',icon=icon)
            actions.menu('CAMKEYS_MT_camkeys_angle_items_menu',text='',icon='DOWNARROW_HLT');actions.separator()
            for op,icon in [('move_angle_item_up','TRIA_UP'),('move_angle_item_down','TRIA_DOWN')]:actions.operator('camkeys.'+op,text='',icon=icon)
            canvas=ui.canvas;canvas.panel_layout=True
            fonts=typography.Fonts()
            canvas.set_text_measure(lambda text,role:measure(typography.face(fonts,role),canvas.theme.font_size*(12/11 if role=='title' else 1),text)[0],'fixture')
            canvas.arrange(360)
            widget=next(c.options['widget'] for c in canvas.controls.values() if c.kind=='widget')
            child=widget.row_map[0][0]
            search=next(c for c in child.controls.values() if c.kind=='search')
            name=next(c for c in child.controls.values() if c.kind=='text')
            assert search.options['search_icon']=='SHAPEKEY_DATA',search.options
            assert abs(name.rect[0]-(search.rect[0]+child.theme.icon_size+6))<.01,(name.rect,search.rect)
            label=next(c for c in child.controls.values() if c.kind=='label' and c.label=='0.251')
            builds=widget.builds;obj.data.shape_keys.key_blocks['Cam_Left'].value=.750;widget.refresh_display()
            assert label.label=='0.750' and widget.builds==builds
            obj.data.shape_keys.key_blocks['Cam_Left'].value=.251;widget.refresh_display()
            model=search.options['search_field'];model.open()
            assert all(row[2]=='SHAPEKEY_DATA' for row in model.widget.items)
            assert child.open_context(search,*search.rect[:2],(0,0,child._width,child.height),context=bpy.context)
            child.close_context()
            x,y,w,h=clear_rect(field_rect(search))
            assert child.event(NS(type='LEFTMOUSE',value='PRESS'),x+w/2,y+h/2,(0,0,child._width,child.height),context=bpy.context)
            assert obj.angle_items[0].shapekey=='' and not child.overlay
            obj.angle_items[0].shapekey='Cam_Left';widget.refresh_display()
            for entry in widget.row_map.values():
                for control in entry[0].controls.values():control.motion.clear()
            for width in (360,280):
                canvas.arrange(width)
                for dpi in (1,1.5,2):
                    w,h=int((width+32)*dpi),int((canvas.height+32)*dpi)
                    off=gpu.types.GPUOffScreen(w,h);under=gpu.types.GPUOffScreen(w,h);key=('list-redesign',width,dpi)
                    with off.bind(),gpu_state(),gpu.matrix.push_pop(),gpu.matrix.push_pop_projection():
                        gpu.matrix.load_matrix(Matrix.Identity(4));gpu.matrix.load_projection_matrix(Matrix(((2/w,0,0,-1),(0,2/h,0,-1),(0,0,1,0),(0,0,0,1))))
                        with under.bind():
                            gpu.state.viewport_set(0,0,w,h);gpu.state.active_framebuffer_get().clear(color=(.08,.11,.14,1))
                            skin.draw((0,0,w*.48,h),(.13,.22,.25,1),radius=0,border=0)
                            skin.draw((w*.8,0,w*.2,h),(.18,.16,.15,1),radius=0,border=0)
                        gpu.state.viewport_set(0,0,w,h);gpu.state.scissor_set(0,0,w,h)
                        assert glass.prepare_texture(key,1,under.texture_color,(0,0,w,h))
                        fb=gpu.state.active_framebuffer_get();rect=(16*dpi,16*dpi,width*dpi,canvas.height*dpi)
                        for frame in range(24):
                            fb.clear(color=(.08,.1,.12,1));t=time.perf_counter()
                            assert glass.lens(key,rect,canvas.theme.radius*dpi,(0,0,0,0),blur=.3)
                            with batch():canvas.paint(rect,(0,0,w,h),font=fonts,preferences=bpy.context.preferences,backdrop=key)
                            if frame>=4:timings.append((time.perf_counter()-t)*1000)
                        p=fb.read_color(0,0,w,h,4,0,'UBYTE');p.dimensions=w*h*4
                        filename=f'list-{width}-{dpi:g}x.png';png(out/filename,w,h,bytes(p))
                        records.append(dict(file=filename,width=width,scale=dpi,rows=[dict(index=i,controls=[dict(kind=c.kind,label=c.label,rect=c.rect,icon=c.options.get('icon')) for c in entry[0].controls.values()]) for i,entry in widget.row_map.items()]))
                    glass.release(key);off.free();under.free()
            canvas.park();fonts.close()
        result=dict(passed=True,version=bpy.app.version_string,backend=gpu.platform.backend_type_get(),captures=records,live_values=True,clear_action=True,search_icons=True,right_click=True,timing_ms=dict(median=statistics.median(timings),max=max(timings)),timing_scope='Warm CPU paint submission only; readback excluded, 20 samples per width/scale; not paired speed qualification')
    except Exception:result=dict(passed=False,error=traceback.format_exc())
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));bpy.ops.wm.quit_blender();return None

def start():
    addon.register();bpy.context.window_manager.EnableCamKeys=False
    bpy.app.timers.register(run,first_interval=2);return None
bpy.app.timers.register(start,first_interval=1)
