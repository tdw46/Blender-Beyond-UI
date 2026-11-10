"""Real BUI GPU reference capture; isolated Blender, no live-file writes."""
import bpy,gpu,sys,os,json,traceback,importlib.util,time
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from capture_controls import png
source=Path(os.environ.get('CAMKEYS_SOURCE', str(Path(__file__).resolve().parents[2]/'CamKeys-beyond-ui')))
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
OUT=Path(os.environ.get('BUI_CAPTURE_OUTPUT', str(ROOT/'docs/design/qa/subject-controls-v2')));OUT.mkdir(parents=True,exist_ok=True)
def run():
 fonts=None;canvas=None
 try:
  from camkeys_qa import subject_size,ui_theme
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa._vendor.beyond_ui.gpu import glass,skin,typography
  from camkeys_qa._vendor.beyond_ui.gpu.paint import gpu_state,measure
  item=bpy.context.scene.mesh_object_items.add();item.auto_fov_control_mode='SUBJECT_SIZE'
  item.auto_fov_size_front=1.6;item.auto_fov_size_back=.65
  layout=Layout(context=bpy.context);ui_theme.STUDIO.apply(layout.canvas)
  if os.environ.get('BUI_CAPTURE_PICKER'):
   from camkeys_qa import onboarding
   from camkeys_qa._vendor import beyond_ui as bui
   item.auto_fov_control_mode=os.environ.get('BUI_CAPTURE_MODE','LENS')
   item.auto_fov_depth_mode=os.environ.get('BUI_CAPTURE_DEPTH_MODE','VOLUME')
   bui.header(layout,'Forced Perspective',icon=bui.Artwork('BUI_FORCED_PERSPECTIVE','VIEW_CAMERA'),size=42,divider=True,title_style={'font_size':18})
   onboarding.apparent_focal_controls(layout,item,bpy.context,wizard=True)
  elif os.environ.get('BUI_CAPTURE_CURVE'):
   for key in ('front','back'):subject_size.prepare_curve(item,key)
   subject_size.draw_transition_curves(layout,item)
  else:subject_size.draw(layout,item)
  canvas=layout.canvas;canvas.panel_layout=True
  fonts=typography.Fonts();canvas.set_text_measure(lambda t,r:measure(typography.face(fonts,r),canvas.theme.font_size,t)[0],'fixture')
  width=int(os.environ.get('BUI_CAPTURE_WIDTH','380'));canvas.arrange(width);dpi=float(os.environ.get('BUI_CAPTURE_SCALE','2'));tag=os.environ.get('BUI_CAPTURE_TAG','');w,h=int((width+24)*dpi),int((canvas.height+24)*dpi)
  off=gpu.types.GPUOffScreen(w,h,format='RGBA8');under=gpu.types.GPUOffScreen(w,h,format='RGBA8');key='subject-planes'
  with off.bind(),gpu_state(),gpu.matrix.push_pop(),gpu.matrix.push_pop_projection():
   gpu.matrix.load_matrix(Matrix.Identity(4));gpu.matrix.load_projection_matrix(Matrix(((2/w,0,0,-1),(0,2/h,0,-1),(0,0,1,0),(0,0,0,1))))
   with under.bind():
    gpu.state.viewport_set(0,0,w,h);gpu.state.scissor_set(0,0,w,h);gpu.state.active_framebuffer_get().clear(color=(.07,.09,.12,1))
    skin.draw((0,0,w*.42,h),(.1,.16,.2,1),radius=0,border=0);skin.draw((w*.78,0,w*.22,h),(.18,.12,.1,1),radius=0,border=0)
   gpu.state.viewport_set(0,0,w,h);gpu.state.scissor_set(0,0,w,h)
   assert glass.prepare_texture(key,1,under.texture_color,(0,0,w,h)),glass.error
   rect=(12*dpi,12*dpi,width*dpi,canvas.height*dpi);times=[]
   for frame in range(12):
    fb=gpu.state.active_framebuffer_get();fb.clear(color=(.07,.09,.12,1));glass.lens(key,rect,24,(0,0,0,0),blur=.3)
    start=time.perf_counter();canvas.paint(rect,(0,0,w,h),font=fonts,preferences=bpy.context.preferences,backdrop=key);times.append((time.perf_counter()-start)*1000)
   pixels=fb.read_color(0,0,w,h,4,0,'UBYTE');pixels.dimensions=w*h*4;png(OUT/('actual'+tag+'.png'),w,h,bytes(pixels))
  canvas.park();glass.release(key);off.free();under.free()
  result={'passed':True,'version':bpy.app.version_string,'backend':gpu.platform.backend_type_get(),'width':w,'height':h,'warm_submit_ms':times[2:],'glass':True,'controls':len(canvas.controls)}
 except Exception:result={'passed':False,'error':traceback.format_exc()}
 finally:
  if canvas:canvas.park()
  if fonts:fonts.close()
  (OUT/('runtime'+os.environ.get('BUI_CAPTURE_TAG','')+'.json')).write_text(json.dumps(result,indent=2));Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2));addon.unregister()
  bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.2)
 return None
addon.register();bpy.context.window_manager.EnableCamKeys=False;bpy.app.timers.register(run,first_interval=1)
