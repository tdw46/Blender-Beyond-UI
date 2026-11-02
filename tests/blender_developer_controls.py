"""Exact owner paths and developer actions, without an active native button."""
import bpy,json,os,sys,traceback
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from beyond_ui import Layout
from beyond_ui.context_menu import Entry,Target,Menu
from beyond_ui.context_fields import property_row
from beyond_ui.tooltips import description

class QA_MT_developer(bpy.types.Menu):
    bl_label='Developer menu'
    def draw(self,context):self.layout.operator('wm.save_as_mainfile')
class QA_PT_developer(bpy.types.Panel):
    bl_label='Developer panel';bl_space_type='VIEW_3D';bl_region_type='WINDOW'
    def draw(self,context):self.layout.prop(context.scene.render,'film_transparent')
class Context:
    window_manager=NS(clipboard='',keyconfigs=bpy.context.window_manager.keyconfigs)
    def __getattr__(self,name):return getattr(bpy.context,name)

checks=[]
try:
    ctx=Context();obj=bpy.context.object
    for cls in (QA_MT_developer,QA_PT_developer):bpy.utils.register_class(cls)
    view=ctx.preferences.view
    for developer,python in ((False,False),(True,False),(False,True),(True,True)):
        view.show_developer_ui=developer;view.show_tooltips_python=python
        ui=Layout(context=ctx)
        control=ui.prop(obj,'location',index=1)
        ui.operator('wm.save_as_mainfile',text='Save').filepath='/tmp/Developer QA.blend'
        ui.menu('QA_MT_developer');ui.popover('QA_PT_developer');ui.canvas.arrange(400)
        text=description(control,ctx)
        assert ('Python: Object.location[1]' in text)==(developer or python),text
        if developer or python:assert control.binding.context.paths()[1] in text,text
        op=next(c for c in ui.canvas.controls.values() if c.options.get('operator_id'))
        optext=description(op,ctx)
        assert ('Python: bpy.ops.wm.save_as_mainfile(' in optext)==(developer or python),optext
        control.options['context_menu']=lambda t,c:[Entry('EXTRA','Consumer action')]
        assert ui.canvas.open_context(control,20,20,(0,0,640,900),context=ctx),ui.canvas.menu_error
        menu=ui.canvas.context_menu;keys=[r.key for r in menu.page.rows]
        assert {'PATH','FULL_PATH','RESET','EXTRA'}<=set(keys),keys
        assert ('API' in keys)==developer,keys
        menu.choose(keys.index('FULL_PATH'),ctx)
        assert ctx.window_manager.clipboard==control.binding.context.paths()[1],ctx.window_manager.clipboard
        assert eval(ctx.window_manager.clipboard)==obj.location[1]
        assert ui.canvas.open_context(op,20,20,(0,0,640,900),context=ctx),ui.canvas.menu_error
        keys=[r.key for r in ui.canvas.context_menu.page.rows]
        assert ('COMMAND' in keys)==developer and ('API' in keys)==developer,keys
        ui.canvas.cancel()
        for c in ui.canvas.controls.values():
            if c.options.get('panel_model') or c.options.get('menu_model'):
                rows=list(c.options['context_menu'](Target(c.key,payload=c),ctx))
                assert {'FAVORITES','SHORTCUT'} <= {r.key for r in rows}
                assert ('COMMAND' in [r.key for r in rows])==developer
                if developer:
                    row=next(r for r in rows if r.key=='COMMAND');row.action(None,ctx)
                    assert 'name=' in ctx.window_manager.clipboard
                if c.options.get('menu_model'):
                    authored,_=c.options['menu_model'].rows(ctx)
                    assert ('Python: bpy.ops.wm.save_as_mainfile(' in authored[0].tooltip(ctx))==(developer or python)
        row=property_row(obj,'location',index=2,commit=lambda a,b:None)
        assert ('Object.location[2]' in row.tooltip(ctx))==(developer or python)
    checks.append('All four preference combinations; component clipboard; contributed-menu preservation; operator/menu/popover developer actions; inline field help')
    result={'passed':True,'checks':checks,'version':bpy.app.version_string}
except Exception:
    result={'passed':False,'error':traceback.format_exc(),'checks':checks}
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));print(result)
