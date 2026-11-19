"""A real window/region, isolated RNA and screen-space hit coordinates; no desktop input."""
import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS
from mathutils import Quaternion, Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from beyond_ui import Canvas, Layout, typed_pick
from beyond_ui.search import field_rect

class PickFixture(bpy.types.PropertyGroup):
    center: bpy.props.StringProperty()

def run():
    checks=[]
    try:
        ctx=bpy.context
        win=ctx.window_manager.windows[0]
        area=next(a for a in win.screen.areas if a.type=='VIEW_3D')
        reg=next(r for r in area.regions if r.type=='WINDOW')
        with ctx.temp_override(window=win,area=area,region=reg):
            if 'ready' not in globals():
                globals()['ready']=True
                rv=ctx.region_data
                rv.view_rotation=Quaternion((1,0,0,0));rv.view_location=(0,0,0)
                rv.view_distance=12;rv.view_perspective='ORTHO'
                area.tag_redraw()
                return .3
            rv=ctx.region_data; scene=ctx.scene
            bpy.utils.register_class(PickFixture)
            bpy.types.Scene.test_typed_pick=bpy.props.PointerProperty(type=PickFixture)
            arm=bpy.data.armatures.new('Only rig')
            rig=bpy.data.objects.new('Only rig',arm);scene.collection.objects.link(rig)
            ctx.view_layer.objects.active=rig;rig.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bone=arm.edit_bones.new('Center joint');bone.head=(2,0,0);bone.tail=(3,0,0)
            bpy.ops.object.mode_set(mode='OBJECT')
            cam=scene.camera;scene.camera=None;cam.location=(-3,0,0)
            cube=scene.objects['Cube'];cube.display_type='WIRE';rig.display_type='SOLID'
            ctx.view_layer.update()
            c=Canvas();ui=Layout(c,ctx,commit=lambda a,b:None)
            ui.prop_search(scene.test_typed_pick,'center',arm,'bones',text='Center')
            center=list(c.controls.values())[-1]
            camera=ui.prop(scene,'camera')
            mode=ui.prop(rig,'display_type')
            groups=ui.prop_search(scene.test_typed_pick,'center',cube,'vertex_groups',text='')
            assert not typed_pick.supported(groups)
            assert groups.options['search_field'].open() is not None
            checks.append('Non-pickable collections remain searchable without a dropper')

            row=ui.row(align=True)
            for name in ('Try Automatic Mapping','Humanoid Standards'):
                row.group.button(name,name,lambda:None,icon='WORLD')
            c.arrange(160)
            for ctl in list(c.controls.values())[-2:]:
                lines,step,*_=ctl.options['_button_lines']
                assert len(lines)>1 and ctl.rect[3]>=len(lines)*step
                assert ''.join(''.join(lines).split())==''.join(ctl.label.split())
            checks.append('Two complete labels wrap and reserve height')
            runtime=NS(hosts={},redraw=lambda:None)
            def click(ctl):
                x,y,w,h=typed_pick.button_rect(ctl)
                assert c.event(NS(type='LEFTMOUSE',value='PRESS',shift=False,alt=False,ctrl=False),
                               x+w/2,y+h/2,(0,0,c._width,c.height),context=ctx)
                assert win.as_pointer() in typed_pick._sessions
            def event(pos,kind='LEFTMOUSE'):
                xy=location_3d_to_region_2d(reg,rv,Vector(pos))
                ev=NS(type=kind,value='PRESS',mouse_x=reg.x+round(xy.x),mouse_y=reg.y+round(xy.y))
                return typed_pick.dispatch(runtime,ctx,ev)
            click(center);event((2.5,0,0))
            assert scene.test_typed_pick.center=='Center joint',c.menu_error
            checks.append('Center prop_search picks projected pose bone in its own armature')
            click(camera);event((0,0,0))
            assert scene.camera is None and win.as_pointer() in typed_pick._sessions
            event((-3,0,0))
            assert scene.camera==cam,c.menu_error
            checks.append('Camera rejects mesh, then picks camera')
            assert not typed_pick.supported(mode) and not typed_pick.start(c,mode,ctx)
            assert not typed_pick._sessions and rig.display_type=='SOLID'
            checks.append('Display mode is a plain enum')
            click(camera);event((0,0,0),'ESC')
            assert scene.camera==cam and not typed_pick._sessions
            assert ctx.active_object==rig and ctx.mode=='OBJECT'
            checks.append('Cancel preserved selection, mode and original value')
        result=dict(passed=True,checks=checks)
    except Exception:
        result=dict(passed=False,checks=checks,error=traceback.format_exc())
    finally:
        if 'result' in locals():
            typed_pick.clear()
            Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
            bpy.ops.wm.quit_blender()

bpy.app.timers.register(run,first_interval=.5)
