"""Disposable consumer state/recording/media lifecycle regression."""
import bpy, os,sys, json,importlib.util,traceback
from pathlib import Path
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
checks=[]
try:
 addon.register()
 bpy.context.window_manager.EnableCamKeys=False
 from camkeys_qa import onboarding as ob, demo_media, ui_theme
 from camkeys_qa._vendor.beyond_ui import Layout
 from camkeys_qa._vendor.beyond_ui.layout_recording import Tape
 from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
 state=bpy.context.scene.camkeys_setup
 assert state.source=='VIEWPORT' and bpy.context.scene.UseViewportInsteadOfCamera
 assert ob.HELP_MEDIA['apparent_fov']=='camprops_comparison'
 checks.append('Viewport defaults shared by CamKeys/CamProps; Lens Tricks maps to the supplied comparison clip')
 assert ob.visible(bpy.context)
 assert bpy.ops.camkeys.setup_navigate() == {'CANCELLED'}
 assert not bpy.context.scene.mesh_object_items
 obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis');obj.shape_key_add(name='Smile')
 state.target=obj;state.camera=bpy.context.scene.camera
 assert state.mesh==obj
 assert bpy.ops.camkeys.setup_navigate() == {'FINISHED'} and state.step==1
 assert bpy.ops.camkeys.setup_navigate(route='ANGLES') == {'FINISHED'} and state.step==2
 state.shapekey='Smile';state.source='CAMERA'
 area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
 with bpy.context.temp_override(area=area,region=region):
  for stage,route in ((0,'ANGLES'),(1,'ANGLES'),(2,'ANGLES'),(2,'PERSPECTIVE'),(2,'DOLLY'),(3,'ANGLES'),(3,'PERSPECTIVE'),(3,'DOLLY')):
   state.step=stage;state.route=route
   t=Tape();ob.CAMKEYS_PT_setup.draw(PanelProxy(ob.CAMKEYS_PT_setup,t.root),bpy.context)
   layout=Layout(context=bpy.context);ui_theme.STUDIO.apply(layout.canvas);t.play(layout);layout.canvas.arrange(320)
   assert layout.canvas.height>100
   assert all(c.rect[2]>=0 for c in layout.canvas.controls.values())
   for width in (240,320,480):
    layout.canvas.arrange(width)
    for c in layout.canvas.controls.values():
     if 'choice_card' in c.options:
      card=c.options['choice_card']
      assert c.binding is not None
      assert c.rect[3]>=card.height
   if stage==3:
    back=[c for c in layout.canvas.controls.values() if c.label=='Back']
    assert len(back)==1 and back[0].options['icon']=='BUI_BACK' and back[0].options['text_alignment']=='LEFT'
   if stage==1:
    choices=[c for c in layout.canvas.controls.values() if 'choice_card' in c.options]
    assert len(choices)==3
    choices[1].options['action_event']()
    assert state.route=='PERSPECTIVE'
    choices[0].options['action_event']()
    assert state.route=='ANGLES'
    checks.append('whole-card selection retains exact enum binding; 240/320/480 widths')
   layout.canvas.park()
   checks.append(f'recorded and arranged {stage}/{route}')
  state.step=2;state.route='ANGLES'
  assert bpy.ops.camkeys.setup_create()=={'FINISHED'},state.error
  assert len(obj.angle_items)==1 and obj.angle_items[0].shapekey=='Smile'
  assert bpy.ops.camkeys.setup_create()=={'CANCELLED'} and len(obj.angle_items)==1
  checks.append('camera-angle creation + repeat-click idempotency')
  # Both effect routes exercise the existing engine, not a cosmetic ready screen.
  camera=state.camera
  for route in ('PERSPECTIVE','DOLLY'):
   state.step=2;state.route=route
   if route=='PERSPECTIVE':
    state.camera=None;bpy.context.scene.camera=None
    state.source='CAMERA';assert ob.validate(state,workflow=True)
    state.source='VIEWPORT';assert not ob.validate(state,workflow=True)
   else:
    state.camera=camera;bpy.context.scene.camera=camera
   outcome=bpy.ops.camkeys.setup_create()
   assert outcome=={'FINISHED'},(route,state.error)
   item=bpy.context.scene.mesh_object_items[0]
   assert item.auto_fov_enabled
   assert bpy.context.scene.UseViewportInsteadOfCamera==(route=='PERSPECTIVE')
   if route=='PERSPECTIVE':assert bpy.context.scene.camera is None
   before=len(obj.angle_items)
   assert bpy.ops.camkeys.setup_navigate(action='BACK')=={'FINISHED'} and state.step==2
   assert len(obj.angle_items)==before
   if route=='DOLLY':
    assert item.auto_fov_dolly_lock.active
    item.auto_fov_dolly_lock.active=False
   checks.append(route+' creates an enabled, functional effect')
  state.step=2;state.route='ANGLES';state.source='CAMERA'
  assert bpy.ops.camkeys.setup_capture()=={'FINISHED'}
  assert state.captured
  # Read-only detection first, then the existing auto-add operator on confirmation.
  for name in ('Cam_Left','Cam_Right','Cam_Top','Cam_Bottom'):obj.shape_key_add(name=name)
  from camkeys_qa.directional_shapes import detect
  assert not detect(['EyeLookLeft','SmileRight'])
  for names in [('左','右','上','下'),('왼쪽','오른쪽','위','아래'),
                ('Izquierda','Derecha','Arriba','Abajo'),('Gauche','Droite','Haut','Bas'),
                ('Links','Rechts','Oben','Unten'),('Лево','Право','Верх','Низ'),
                ('Sinistra','Destra','Alto','Basso'),('Esquerda','Direita','Cima','Baixo'),
                ('視角左側','視角右側','視角頂部','視角底部'),
                ('镜头左侧','镜头右侧','镜头顶部','镜头底部')]:
   assert [r[0] for r in detect(names)]==['Left','Right','Top','Bottom'],names
  assert not detect(['左','Cam_Left']), 'Ambiguous aliases must remain manual'
  assert not detect(['Cam_Left','Camera_Left'])
  assert detect(['Left','Cam_Left'])[0][1]=='Left'
  from types import SimpleNamespace
  cfg=[SimpleNamespace(name='Cam_Top',offset_x_deg=-30,offset_y_deg=0,offset_z_deg=0)]
  assert detect(['Cam_Top'],cfg)==(('Top','Cam_Top',(-30,0,0)),)
  presets=[(e.name,e.offset_x_deg,e.offset_y_deg,e.offset_z_deg) for e in bpy.context.scene.camkeys_auto_add_entries]
  ob.refresh_detected(state,bpy.context);state.manual_angles=False;state.step=2;state.route='ANGLES'
  assert len(state.detected)==4
  before=len(obj.angle_items)
  state.detected[-1].enabled=False
  assert bpy.ops.camkeys.setup_create()=={'FINISHED'},state.error
  assert len(obj.angle_items)==before+3
  assert {a.shapekey for a in list(obj.angle_items)[before:]}=={'Cam_Left','Cam_Right','Cam_Top'}
  assert all(abs(a.target_vector.length-1)<1e-5 for a in list(obj.angle_items)[before:])
  state.step=2
  assert bpy.ops.camkeys.setup_create()=={'FINISHED'} and len(obj.angle_items)==before+3
  assert presets==[(e.name,e.offset_x_deg,e.offset_y_deg,e.offset_z_deg) for e in bpy.context.scene.camkeys_auto_add_entries]
  assert bpy.ops.camkeys.setup_navigate(action='MANUAL')=={'FINISHED'} and state.manual_angles and state.step==2
  assert bpy.ops.camkeys.auto_add_directional_shapekeys(entries_json='[]')=={'CANCELLED'}
  assert len(obj.angle_items)==before+3
  checks.append('Directional detection, ambiguity rejection, selected confirmation, normalized offsets, duplicate skip, unchanged presets and Add More manual path')
  state.step=3

  assert bpy.ops.camkeys.setup_navigate(action='OPEN')=={'FINISHED'}
  assert not ob.visible(bpy.context)
  assert bpy.ops.camkeys.setup_navigate(action='START')=={'FINISHED'} and ob.visible(bpy.context)
  assert set(ob.HELP_MEDIA)<=set(ob.HELP)
  assert len(demo_media.LIBRARY.provider.clips)==8
  assert set(ob.HELP_MEDIA.values())<=set(demo_media.LIBRARY.provider.clips)
  for key in demo_media.LIBRARY.provider.clips:
   frame=demo_media.LIBRARY.provider.frame(key,0);assert len(frame[3]())==frame[1]*frame[2]*4
   meta=demo_media.LIBRARY.provider.clips[key][0]
   assert demo_media.LIBRARY.provider.frame(key,meta['duration_ms']*100)[0]>=0
  checks.append('eight pinned clips decoded; full-duration timelines and loops')
 addon.unregister()
 assert not hasattr(bpy.types.Scene,'camkeys_setup')
 checks.append('registration/teardown and no background playback')
 result=dict(passed=True,version=bpy.app.version_string,checks=checks)
except Exception:result=dict(passed=False,version=bpy.app.version_string,checks=checks,error=traceback.format_exc())
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
