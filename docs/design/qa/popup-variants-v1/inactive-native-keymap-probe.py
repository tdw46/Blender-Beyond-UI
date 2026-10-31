import bpy,os,json
from pathlib import Path
step=0
win=bpy.context.window
area=next(a for a in win.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
def tick():
 global step
 if step==0:
  for obj in bpy.context.selected_objects: obj.select_set(False)
  for kind,val in [('MOUSEMOVE','NOTHING'),('A','PRESS'),('A','RELEASE')]:
   win.event_simulate(type=kind,value=val,x=region.x+region.width//2,y=region.y+region.height//2)
  step=1
  return 1
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(dict(passed=True,selected=len(bpy.context.selected_objects))))
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=1)
