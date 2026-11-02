"""Real consumer callback naming and retained artwork/header regression."""
import bpy,os,sys,json,traceback,importlib.util
from pathlib import Path
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
def run():
    checks=[]
    try:
        addon.register()
        from camkeys_qa import ui_theme,properties
        from camkeys_qa._vendor.beyond_ui import Layout,header,heading
        from camkeys_qa._vendor.beyond_ui.gpu import icons
        obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis');obj.shape_key_add(name='Smile');obj.shape_key_add(name='Wide Smile')
        angle=obj.angle_items.add();angle.name='Angle 1'
        assert angle.name=='Angle 1'
        angle.shapekey='Smile';assert angle.name=='Smile'
        angle.shapekey='Wide Smile';assert angle.name=='Wide Smile'
        angle.shapekey='';assert angle.name=='Wide Smile'
        angle.shapekey='missing';assert angle.name=='Wide Smile'
        other=obj.angle_items.add();other.name='Angle 2';other.shapekey='Smile'
        assert obj.angle_items[0].name=='Wide Smile' and obj.angle_items[1].name=='Smile'
        properties.AngleItem.shapekey=bpy.props.StringProperty(name='Shapekey',update=properties.update_angle_shapekey_name)
        assert obj.angle_items[1].shapekey=='Smile'
        obj.angle_items[1].shapekey='Wide Smile'
        assert obj.angle_items[1].name=='Wide Smile'
        checks.append('Native RNA selection renames only exact angle; new, cleared and invalid selections preserve titles')
        assert ui_theme.ARTWORK.loaded and len(ui_theme.ARTWORK.assets)==5
        if not bpy.app.background:
            icons.prepare()
            assert len(icons._artwork['camkeys.studio']['textures'])==2
        ui=Layout();ui_theme.STUDIO.apply(ui.canvas)
        header(ui,'CamKeys',subtitle='Camera-driven expressions',icon=ui_theme.artwork('logo'))
        heading(ui,'Tracked Objects',icon=ui_theme.artwork('objects'))
        for width in (240,360,520):
            ui.canvas.arrange(width)
            assert len(ui.canvas.controls)==4
        checks.append('Five artwork descriptors; header layouts fit narrow/wide bounds' if bpy.app.background else 'Five icons share two retained textures; header layouts fit narrow/wide bounds')
        ui.canvas.park();addon.unregister()
        assert 'camkeys.studio' not in icons._artwork
        checks.append('Addon teardown releases artwork namespace and textures')
        result={'passed':True,'version':bpy.app.version_string,'checks':checks}
    except Exception:result={'passed':False,'checks':checks,'error':traceback.format_exc()}
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
    bpy.ops.wm.quit_blender()
if bpy.app.background:run()
else:bpy.app.timers.register(run,first_interval=.5)
