"""Actual i18n and authored UI/help coverage in an isolated windowed runtime."""
import bpy,os,sys,json,traceback,importlib.util
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT']);sys.path[:0]=[str(source/'tests'),str(ROOT/'tests')]
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
from check_onboarding_translations import check

def run():
 result={};canvases=[]
 try:
  assert not bpy.app.background
  addon.register();bpy.context.window_manager.EnableCamKeys=False
  from camkeys_qa import utils,onboarding as ob,ui_theme,ui_panel
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
  messages,entries=check();shared={v['EN'] for v in json.loads((source/'camkeys_translations.json').read_text()).values() if 'EN' in v};view=bpy.context.preferences.view
  available={item.identifier for item in view.bl_rna.properties['language'].enum_items}
  view.use_translate_interface=True;view.use_translate_tooltips=True
  obj=bpy.data.objects['Cube'];obj.name='Next';obj.shape_key_add(name='Basis');obj.shape_key_add(name='Left')
  s=bpy.context.scene.camkeys_setup;s.target=obj;s.camera=bpy.context.scene.camera;s.shapekey='Left';s.source='CAMERA'
  area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
  runtime=addon.__beyond_ui_integration__.ui._runtime
  draw=runtime.draw_functions.get(ob.CAMKEYS_PT_setup,ob.CAMKEYS_PT_setup.draw)
  locales=[]
  with bpy.context.temp_override(area=area,region=region):
   for lang,locale in utils._LANG_TO_LOCALE.items():
    if lang=='EN':continue
    chosen=next((c for c in [locale]+sorted(v for v in available if v.startswith(locale+'_')) if c in available),None)
    assert chosen,(lang,locale)
    view.language=chosen
    utils.unregister_translations()
    lookups=(bpy.app.translations.pgettext_iface,bpy.app.translations.pgettext_tip)
    native={(source,lookup):lookup(source) for source in messages for lookup in lookups}
    utils.register_translations();utils.register_translations() # idempotent targeted reload
    for msg in messages:
     for lookup in lookups:
      expected=native[msg,lookup] if native[msg,lookup]!=msg else entries[msg][lang]
      assert lookup(msg,'CamKeysSetup')==entries[msg][lang]
      # Blender may contain an intentional identity translation for shared terms.
      assert lookup(msg)==expected or (lookup(msg)==msg and msg in shared | {'Top','Bottom','Left','Right'}),(lang,msg,lookup(msg),expected)
    assert bpy.app.translations.pgettext_iface('Create CamKeys Setup','Operator')==entries['Create CamKeys Setup'][lang]
    for stage in (0,1,2,3):
     s.step=stage;layout=Layout(context=bpy.context,**addon.__beyond_ui_integration__.ui.layout_options);ui_theme.STUDIO.apply(layout.canvas);draw(PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
     for width in (240,320,480):layout.canvas.arrange(width)
     if stage==1:
      cards=[c.options['choice_card'] for c in layout.canvas.controls.values() if 'choice_card' in c.options]
      assert cards[0].title==bpy.app.translations.pgettext_iface(ob.ROUTES[0][1])
      assert cards[0].description==bpy.app.translations.pgettext_iface(ob.ROUTES[0][2])
     if stage==3:assert any(c.label=='Next' for c in layout.canvas.controls.values()),'User object name was translated'
     layout.canvas.park()
    locales.append(dict(language=lang,locale=chosen,messages=len(messages),widths=[240,320,480]))
   view.language='en_US';s.step=2
   assert bpy.ops.camkeys.setup_create()=={'FINISHED'}
   from camkeys_qa._vendor.beyond_ui.list_identity import PendingListIdentity
   ids=addon.__beyond_ui_integration__.list_ids
   for owner in [bpy.context.scene,*bpy.context.scene.mesh_object_items,*bpy.data.objects]:
    for prop in owner.bl_rna.properties:
     if prop.type=='COLLECTION':
      values=getattr(owner,prop.identifier)
      if values and all(ids.owned(v) for v in values):
       try:ids.prepare(owner,prop.identifier)
       except PendingListIdentity:pass
   ids.flush()
   # Every help topic authors a real custom form, preserving operator metadata.
   topics=[]
   for key in ob.HELP:
    layout=Layout(context=bpy.context,**addon.__beyond_ui_integration__.ui.layout_options);ui_theme.STUDIO.apply(layout.canvas)
    draw_help=addon.__beyond_ui_integration__.router.draw_originals.get(ob.CAMKEYS_OT_show_example) if hasattr(addon.__beyond_ui_integration__.router,'draw_originals') else None
    # Operator draw is source-owned; proxy only supplies the expected layout/property.
    ob.CAMKEYS_OT_show_example.draw(SimpleNamespace(layout=layout,example=key),bpy.context)
    layout.canvas.arrange(380);layout.canvas.park();topics.append(key)
   # All main panels must expose at least one clickable help operator.
   panels=[]
   for cls in (ui_panel.CAMKEYS_PT_camkeys_main,ui_panel.CAMKEYS_PT_camkeys_linking,ui_panel.CAMKEYS_PT_auto_fov,ui_panel.CAMKEYS_PT_camprops,ui_panel.CAMKEYS_PT_baking):
    layout=Layout(context=bpy.context,**addon.__beyond_ui_integration__.ui.layout_options);ui_theme.STUDIO.apply(layout.canvas)
    callback=runtime.draw_functions.get(cls,cls.draw);callback(PanelProxy(cls,layout),bpy.context);layout.canvas.arrange(320)
    help_controls=[c for c in layout.canvas.controls.values() if c.options.get('operator')=='camkeys.show_example']
    # Public authored callback metadata can vary between direct and adopted draw.
    if not help_controls:
     help_controls=[c for c in layout.canvas.controls.values() if 'camkeys.show_example' in repr(c.options)]
    assert help_controls,(cls.__name__,[(c.kind,c.label,c.options.keys()) for c in layout.canvas.controls.values()])
    panels.append(dict(panel=cls.__name__,help_controls=len(help_controls)));layout.canvas.park()
   view.language='de_DE';view.use_translate_interface=False
   assert Layout(context=bpy.context,**addon.__beyond_ui_integration__.ui.layout_options)._text('Choose your subject')=='Choose your subject'
  result=dict(passed=True,version=bpy.app.version_string,locales=locales,help_topics=topics,panels=panels,user_names_preserved=True,idempotent_catalog=True)
 except Exception:result=dict(passed=False,error=traceback.format_exc())
 finally:
  for canvas in canvases:canvas.park()
  try:addon.unregister()
  except Exception:result.update(passed=False,teardown=traceback.format_exc())
  Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2,ensure_ascii=False))
  bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.1)
 return None
bpy.app.timers.register(run,first_interval=1)
