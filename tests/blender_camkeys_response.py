"""Consumer response layout and owner-relative capture metadata; no saved scene."""
import bpy,os,sys,json,importlib.util,traceback,math
from pathlib import Path
from mathutils import Matrix
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
checks=[]
try:
 addon.register()
 bpy.context.window_manager.EnableCamKeys=False
 from camkeys_qa.capture_display import direction_angles,capture_summary
 from camkeys_qa import ui_lists,ui_theme
 from camkeys_qa._vendor.beyond_ui import Layout
 from camkeys_qa._vendor.beyond_ui.layout_recording import Tape
 assert direction_angles((0,-1,0),2)==(0,0,0)
 assert direction_angles((1,-1,0),2)==(0,45,0)
 assert direction_angles((0,-1,1),2)==(45,0,0)
 assert direction_angles((1,0,1),1)==(0,45,0)
 assert direction_angles((0,0,0),2) is None
 obj=bpy.data.objects['Cube'];obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Cam_Left')
 obj.matrix_world=Matrix.Rotation(math.pi/2,4,'X')
 angle=obj.angle_items.add();angle.target_vector=(1,0,1);angle.shapekey=key.name
 key.value=0
 assert capture_summary(angle,obj,bpy.context)=='(0, 45, 0)°'
 checks.append('Pitch/yaw/zero-roll offsets correct for Z-up and imported Y-up; invalid capture explicit')
 def record():
  t=Tape();ui_lists.AngleItems_UL.draw_item(None,bpy.context,t.root,obj,angle,0,obj,'angle_items_index',0);return t
 tape=record();ui=Layout(context=bpy.context);ui_theme.STUDIO.apply(ui.canvas);tape.play(ui);ui.canvas.arrange(340)
 label=next(c for c in ui.canvas.controls.values() if c.label=='(0, 45, 0)°')
 search=next(c for c in ui.canvas.controls.values() if c.kind=='search')
 assert abs(label.rect[0]-search.rect[0])<.01
 assert label.options['color_role']=='accent'
 value=next(c for c in ui.canvas.controls.values() if c.label=='0.000')
 ui.canvas.value_feedback.observe(value,value.label,0)
 key.value=.25;assert tape.patch_display(record());assert value.label=='0.250'
 ui.canvas.value_feedback.observe(value,value.label,.1);assert ui.canvas.value_feedback.amount(value,.1)==1
 assert ui.canvas.value_feedback.amount(value,1)==0
 assert any(c.options.get('icon')=='RESTRICT_RENDER_OFF' for c in ui.canvas.controls.values())
 checks.append('Angle metadata aligns with search border; native name/search/capture retained; literal live values highlight and settle')
 ui.canvas.park();addon.unregister()
 result=dict(passed=True,version=bpy.app.version_string,checks=checks)
except Exception:result=dict(passed=False,checks=checks,error=traceback.format_exc())
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
