"""Real Blender GPU captures of approved wizard; disposable profile, no scene save."""
import bpy,gpu,os,sys,json,traceback,importlib.util,time
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from capture_controls import png
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
OUT=Path(os.environ.get('BEYOND_UI_CAPTURE_OUTPUT',str(ROOT/'docs/design/qa/camkeys-onboarding-v2')));OUT.mkdir(parents=True,exist_ok=True)

def run():
 fonts=None; canvases=[]; result={}
 try:
  from camkeys_qa import onboarding as ob,ui_theme,demo_media
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
  from camkeys_qa._vendor.beyond_ui.gpu import glass,skin,typography,style
  from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state,measure
  if os.environ.get('BEYOND_UI_CAPTURE_LOCALE'):
   bpy.context.preferences.view.language=os.environ['BEYOND_UI_CAPTURE_LOCALE']
   bpy.context.preferences.view.use_translate_interface=True
   bpy.context.preferences.view.use_translate_tooltips=True
  fonts=typography.Fonts();state=bpy.context.scene.camkeys_setup
  existing=next((item.object for item in bpy.context.scene.mesh_object_items if item.object and getattr(item.object.data,'shape_keys',None)),None)
  if existing is None:
   existing=bpy.data.objects.get('Cube')
   existing.shape_key_add(name='Basis');existing.shape_key_add(name='Smile')
  state.target=existing;state.camera=bpy.context.scene.camera;state.shapekey=existing.data.shape_keys.key_blocks[-1].name
  state.source='VIEWPORT';state.force=True;state.summary='Your camera angle is ready. Orbit the view to see your character respond.'
  area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
  runtime=addon.__beyond_ui_integration__.ui._runtime
  draw=runtime.draw_functions.get(ob.CAMKEYS_PT_setup,ob.CAMKEYS_PT_setup.draw)
  records=[]; copy_records={}
  glyphs=set(); outline_radii=[]
  original_icon, original_outline = style.icon, skin.inset_outline
  def observed_icon(glyph,*args,**kwargs):
   glyphs.add(glyph);return original_icon(glyph,*args,**kwargs)
  def observed_outline(rect,palette,scale=1,radius=6):
   outline_radii.append(radius);return original_outline(rect,palette,scale,radius)
  style.icon,skin.inset_outline=observed_icon,observed_outline
  with bpy.context.temp_override(area=area,region=region):
   stages=[('target',0,'ANGLES'),('workflow',1,'ANGLES'),('detected',2,'ANGLES'),('angles',2,'ANGLES'),('perspective',2,'PERSPECTIVE'),('dolly',2,'DOLLY'),('ready',3,'ANGLES')]
   if os.environ.get('BEYOND_UI_CAPTURE_HELP'):stages=[(key,-1,'ANGLES') for key in os.environ['BEYOND_UI_CAPTURE_HELP'].split(',')]
   for slug,stage,route in stages:
    if os.environ.get('BEYOND_UI_CAPTURE_STAGES') and slug not in os.environ['BEYOND_UI_CAPTURE_STAGES'].split(','):continue
    glyphs.clear();outline_radii.clear()
    state.step=stage;state.route=route;state.manual_angles=slug!='detected'
    if stage==2 and route in {'PERSPECTIVE','DOLLY'}:
     state.step=1
     assert bpy.ops.camkeys.setup_navigate()=={'FINISHED'},state.error
     assert ob.onboarding_view.prepared_item(state,bpy.context) is not None
    layout=Layout(context=bpy.context);ui_theme.STUDIO.apply(layout.canvas)
    if stage<0:
     from types import SimpleNamespace
     ob.CAMKEYS_OT_show_example.draw(SimpleNamespace(layout=layout,example=slug),bpy.context)
    else:draw(PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
    canvas=layout.canvas;canvas.panel_layout=True;canvases.append(canvas)
    copy_records[slug]=[]
    for control in canvas.controls.values():
     if control.label:copy_records[slug].append(control.label)
     widget=control.options.get('widget')
     if getattr(widget,'caption',''):copy_records[slug].append(widget.caption)
     card=control.options.get('choice_card')
     if card:copy_records[slug].extend([card.title,card.description])
    canvas.set_text_measure(lambda t,r:measure(typography.face(fonts,r),canvas.theme.font_size,t)[0],'fixture')
    width=320;canvas.arrange(width);dpi=2
    if slug in {'perspective','dolly'}:
     from camkeys_qa._vendor.beyond_ui.scalar_geometry import slider_parts
     numeric=next(c for c in canvas.controls.values() if c.label in {'Apparent focal length','Start lens'})
     value=slider_parts(numeric.rect,True,stacked=numeric.options.get('_slider_stacked'),label_band=numeric.options.get('_label_band',24))[2]
     help_control=min((c for c in canvas.controls.values() if c.kind=='button' and not c.label and c.rect[0]>numeric.rect[0]),key=lambda c:abs(c.rect[1]+c.rect[3]/2-(value[1]+value[3]/2)))
     assert abs(help_control.rect[1]+help_control.rect[3]/2-(value[1]+value[3]/2))<.01
    w,h=int((width+24)*dpi),int((canvas.height+24)*dpi)
    off=gpu.types.GPUOffScreen(w,h,format='RGBA8');under=gpu.types.GPUOffScreen(w,h,format='RGBA8');key=('onboarding',slug)
    timings=[];frame_tokens=[]
    try:
     with off.bind(),gpu_state(),gpu.matrix.push_pop(),gpu.matrix.push_pop_projection():
      gpu.matrix.load_matrix(Matrix.Identity(4));gpu.matrix.load_projection_matrix(Matrix(((2/w,0,0,-1),(0,2/h,0,-1),(0,0,1,0),(0,0,0,1))))
      with under.bind():
       gpu.state.viewport_set(0,0,w,h);gpu.state.scissor_set(0,0,w,h)
       gpu.state.active_framebuffer_get().clear(color=(.07,.09,.12,1))
       skin.draw((0,0,w*.42,h),(.1,.16,.2,1),radius=0,border=0)
       skin.draw((w*.78,0,w*.22,h),(.18,.12,.1,1),radius=0,border=0)
      gpu.state.viewport_set(0,0,w,h);gpu.state.scissor_set(0,0,w,h)
      assert glass.prepare_texture(key,1,under.texture_color,(0,0,w,h)),glass.error
      rect=(12*dpi,12*dpi,width*dpi,canvas.height*dpi)
      for frame in range(12 if slug=='angles' else 2):
       fb=gpu.state.active_framebuffer_get();fb.clear(color=(.07,.09,.12,1))
       glass.lens(key,rect,12*dpi,(0,0,0,0),blur=.3)
       canvas.paint(rect,(0,0,w,h),font=fonts,preferences=bpy.context.preferences,backdrop=key)
       demo_media.LIBRARY.started=time.monotonic()-frame*.1
       demo_media.LIBRARY._tick()
       assert not demo_media.LIBRARY.errors,demo_media.LIBRARY.errors
       fb.clear(color=(.07,.09,.12,1));glass.lens(key,rect,12*dpi,(0,0,0,0),blur=.3)
       start=time.perf_counter();canvas.paint(rect,(0,0,w,h),font=fonts,preferences=bpy.context.preferences,backdrop=key);timings.append((time.perf_counter()-start)*1000)
       pixels=fb.read_color(0,0,w,h,4,0,'UBYTE');pixels.dimensions=w*h*4
       if slug=='angles':
        folder=OUT/'motion';folder.mkdir(exist_ok=True);png(folder/f'{frame:03}.png',w,h,bytes(pixels))
       if frame==1:png(OUT/f'{slug}.png',w,h,bytes(pixels))
      expected={'BUI_ADJUSTMENTS','BUI_CLAPPERBOARD','BUI_LAYERS','BUI_APERTURE'} if slug=='ready' else {'BUI_EXTERNAL'}
      if stage>0:expected.add('BUI_BACK')
      if stage<0:expected=set()
      assert expected.issubset(glyphs),(slug,expected-glyphs)
      if stage>=0:assert (17 if stage==2 else 16) in outline_radii,(slug,outline_radii)
      records.append(dict(stage=slug,width=w,height=h,controls=len(canvas.controls),warm_submit_ms=timings[1:],texture_bytes=demo_media.LIBRARY.bytes,glass=True,required_icons=sorted(expected),button_rims_match=True))
    finally:
     canvas.park();glass.release(key);off.free();under.free()
   for canvas in canvases:canvas.park()
   style.icon,skin.inset_outline=original_icon,original_outline
   assert demo_media.LIBRARY._tick() is None
   result=dict(passed=True,version=bpy.app.version_string,backend=gpu.platform.backend_type_get(),records=records,hidden_stopped=True,
       source_scene=bpy.data.filepath,limits=['Offscreen component captures with real BUI shared glass, not a screenshot of the live N panel.','Source media sampled at 10 FPS; all durations preserved.'])
 except Exception:result=dict(passed=False,error=traceback.format_exc())
 finally:
  for canvas in canvases:canvas.park()
  if fonts:fonts.close()
  (OUT/'copy.json').write_text(json.dumps(copy_records,indent=2,ensure_ascii=False))
  (OUT/'runtime.json').write_text(json.dumps(result,indent=2,default=str))
  Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2,default=str))
  addon.unregister()
  bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.2)
 return None

def start():
 addon.register()
 if os.environ.get('BEYOND_UI_CRASH_FILE'):
  bpy.ops.wm.open_mainfile(filepath=os.environ['BEYOND_UI_CRASH_FILE'],load_ui=False,use_scripts=False)
 bpy.context.window_manager.EnableCamKeys=False
 bpy.app.timers.register(run,first_interval=1)
 return None
bpy.app.timers.register(start,first_interval=1)
