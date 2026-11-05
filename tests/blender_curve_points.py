"""Real packed CurveMap RNA: insertion, dragging, rollback, handles, stale owners."""
import bpy,json,os,sys
from pathlib import Path
from types import SimpleNamespace as Event
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from beyond_ui.widgets import CurveMapping
from beyond_ui.widgets.rna import curve_mapping
from beyond_ui.widgets.context import target
from beyond_ui.widgets.metrics import CURVE
mat=bpy.data.materials.new('Curve transaction');mat.use_nodes=True
node=mat.node_tree.nodes.new('ShaderNodeRGBCurve');node.mapping.initialize()
commits=[];channel=[0]
b,mapping,curve=curve_mapping(node,'mapping',lambda a,b:commits.append((a,b)),channel)
curve().points[0].handle_type='VECTOR';curve().points[1].handle_type='AUTO_CLAMPED';mapping.update()
w=CurveMapping(b)
def state():return tuple((tuple(p.location),p.handle_type) for p in curve().points)
def e(kind,x=300,y=250,value='PRESS'):return w.event(Event(type=kind,value=value),x,y)
original=state();e('LEFTMOUSE');assert len(curve().points)==3
e('MOUSEMOVE',400,210);e('ESC');assert state()==original and not commits
e('LEFTMOUSE');e('LEFTMOUSE',value='RELEASE');assert len(commits)==1 and len(curve().points)==3
assert curve().points[0].handle_type=='VECTOR' and curve().points[-1].handle_type=='AUTO_CLAMPED'
e('LEFTMOUSE',value='DOUBLE_CLICK');e('LEFTMOUSE',value='RELEASE');assert len(curve().points)==3
hit=target(w,'curve',550,145);assert hit.part[0]=='point'
e('LEFTMOUSE',550,145);assert state()==original and len(commits)==2
assert not hit.binding.valid(), 'Removed point context redirected to a different owner'
# Commit failure rolls back coordinates and interpolation metadata together.
def fail(a,b):raise RuntimeError('host undo failure')
b2,_,_=curve_mapping(node,'mapping',fail,channel);w=CurveMapping(b2)
e('LEFTMOUSE')
try:e('LEFTMOUSE',value='RELEASE')
except RuntimeError:pass
else:raise AssertionError('Expected failed commit')
assert state()==original
# Switching channels/external edits cannot redirect cancellation to new data.
w=CurveMapping(b);b.refresh();e('LEFTMOUSE');channel[0]=1
other=tuple(tuple(p.location) for p in mapping.curves[1].points)
e('ESC');assert tuple(tuple(p.location) for p in mapping.curves[1].points)==other
bpy.data.materials.remove(mat)
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps({'passed':True,'version':bpy.app.version_string,'checks':['single_click_add','insert_drag_cancel','remove_button','minimum_points','handle_preservation','commit_failure','stale_context','channel_guard']}))
