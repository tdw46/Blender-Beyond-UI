"""Disposable native row baseline using the consumer's unchanged draw_item."""
import bpy,gpu,sys,os,json,traceback,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from capture_controls import png
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
out=Path(os.environ['BEYOND_UI_TEST_RESULT']).with_suffix('');out.mkdir(exist_ok=True)
class BUI_PT_native_list_baseline(bpy.types.Panel):
    bl_label='Native CamKeys row baseline'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Native QA'
    def draw(self,context):
        obj=bpy.data.objects['Cube']
        self.layout.template_list('CAMSHAPEMATIC_UL_angle_items','native_qa',obj,'angle_items',obj,'angle_items_index',rows=4)
state={'step':0};handle=None

def capture():
    if not state.get('pending') or bpy.context.region!=region:return
    w,h=region.width,region.height;p=gpu.state.active_framebuffer_get().read_color(0,0,w,h,4,0,'UBYTE');p.dimensions=w*h*4
    png(out/'native.png',w,h,bytes(p));state['pending']=False

def tick():
    global region,area,handle
    try:
        n=state['step']
        if n==0:
            addon.register();bpy.context.window_manager.EnableCamKeys=False
            obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis')
            for name,value in [('Cam_Left',.251),('Cam_Right',0),('Cam_Bottom',0),('Cam_Top',.221)]:
                key=obj.shape_key_add(name=name);key.value=value
                item=obj.angle_items.add();item.name=name;item.shapekey=name
            obj.angle_items_index=0
            bpy.utils.register_class(BUI_PT_native_list_baseline)
            area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');area.spaces.active.show_region_ui=True
            region=next(r for r in area.regions if r.type=='UI')
            icons=bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items
            state['icons']={k.name:next((i.identifier for i in icons if i.value==bpy.types.UILayout.icon(k)),None) for k in obj.data.shape_keys.key_blocks}
        elif n==1:
            region.active_panel_category='Native QA';handle=bpy.types.SpaceView3D.draw_handler_add(capture,(),'UI','POST_PIXEL')
        elif n==2:state['pending']=True
        elif n==3:
            assert (out/'native.png').exists()
            Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=True,version=bpy.app.version_string,icons=state['icons'])))
            bpy.types.SpaceView3D.draw_handler_remove(handle,'UI');bpy.ops.wm.quit_blender();return None
        state['step']+=1
        if n>0:area.tag_redraw()
        return 1
    except Exception:
        Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=False,error=traceback.format_exc())))
        bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=1)
