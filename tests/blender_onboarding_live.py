"""Actual event-only setup, live property, viewport/camera framing and lock regression."""
import bpy, os, sys, json, traceback, importlib.util
from pathlib import Path
from mathutils import Vector
source=Path(os.environ['BEYOND_UI_CAMKEYS_ROOT'])
spec=importlib.util.spec_from_file_location('camkeys_qa',source/'__init__.py',submodule_search_locations=[str(source)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
checks=[]
def run():
 try:
  addon.register();bpy.context.window_manager.EnableCamKeys=False
  from camkeys_qa import onboarding_view as ov,utils,onboarding as ob
  from camkeys_qa._vendor.beyond_ui import Layout
  from camkeys_qa._vendor.beyond_ui.hosts.addon import PanelProxy
  from camkeys_qa._vendor.beyond_ui.numeric import Numeric
  scene=bpy.context.scene;s=scene.camkeys_setup;obj=bpy.data.objects['Cube']
  area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
  with bpy.context.temp_override(area=area,region=region):
   rv=area.spaces.active.region_3d;rv.view_perspective='PERSP';rv.view_distance=12;rv.update()
   scene.camera=None;s.target=obj;s.source='VIEWPORT';s.route='PERSPECTIVE';s.step=1
   assert bpy.ops.camkeys.setup_navigate()=={'FINISHED'},s.error
   item=ov.prepared_item(s,bpy.context);assert s.step==2 and item and item.auto_fov_enabled
   assert any(m.type=='NODES' for m in obj.modifiers)
   layout=Layout(context=bpy.context);ob.CAMKEYS_PT_setup.draw(PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
   field=next(c for c in layout.canvas.controls.values() if c.label=='Apparent focal length')
   assert field.binding.context.name=='auto_fov_max_strength' and field.binding.context.resolve()==item
   def verts(value):
    field.binding.write(value);utils.invalidate_all_caches();utils.update_auto_fov_correction(scene)
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();dg.update()
    evaluated=obj.evaluated_get(dg);mesh=evaluated.to_mesh()
    try:return [v.co.copy() for v in mesh.vertices]
    finally:evaluated.to_mesh_clear()
   a,b=verts(90),verts(180)
   delta=max((x-y).length for x,y in zip(a,b));assert delta>1e-5,delta
   layout.canvas.park()
   focal=item.auto_fov_max_strength;mods=len(obj.modifiers)
   assert bpy.ops.camkeys.setup_create()=={'FINISHED'} and item.auto_fov_max_strength==focal
   assert bpy.ops.camkeys.setup_navigate(action='BACK')=={'FINISHED'}
   assert bpy.ops.camkeys.setup_navigate(action='BACK')=={'FINISHED'}
   assert bpy.ops.camkeys.setup_navigate()=={'FINISHED'}
   assert len(obj.modifiers)==mods and len(scene.mesh_object_items)==1 and item.auto_fov_max_strength==focal
   checks.append(dict(check='effect prepared before step, actual evaluated vertices change, Back/Next retains edits without duplication',vertex_delta=delta))
   s.step=1;s.route='DOLLY';s.source='VIEWPORT'
   assert bpy.ops.camkeys.setup_navigate()=={'FINISHED'},s.error
   assert scene.UseViewportInsteadOfCamera and scene.camera is None
   assert not item.auto_fov_dolly_lock.active
   layout=Layout(context=bpy.context);ob.CAMKEYS_PT_setup.draw(PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
   assert not any(c.binding and getattr(c.binding.context,'name','')=='camera' for c in layout.canvas.controls.values())
   assert {'Snap to Front View','Dolly at Current View'} <= {c.label for c in layout.canvas.controls.values()}
   layout.canvas.park()
   assert bpy.ops.camkeys.setup_snap_front()=={'FINISHED'},s.error
   bpy.context.view_layer.update();rv.update()
   dg=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(dg)
   clip=[rv.perspective_matrix @ (evaluated.matrix_world @ Vector(c)).to_4d() for c in evaluated.bound_box]
   extent=max(max(abs(p.x/p.w),abs(p.y/p.w)) for p in clip)
   assert .70<extent<.80,extent
   before=rv.view_matrix.copy();assert bpy.ops.camkeys.setup_dolly_current()=={'FINISHED'},s.error
   lock=item.auto_fov_dolly_lock;assert lock.active and lock.viewport_source
   assert max(abs(before[i][j]-rv.view_matrix[i][j]) for i in range(4) for j in range(4))<1e-4
   rv.view_distance*=1.1;rv.update();utils.invalidate_all_caches();utils.update_auto_fov_correction(scene)
   before=rv.view_matrix.copy();assert bpy.ops.camkeys.setup_dolly_current()=={'FINISHED'},s.error
   assert max(abs(before[i][j]-rv.view_matrix[i][j]) for i in range(4) for j in range(4))<1e-4
   assert bpy.ops.camkeys.setup_snap_front()=={'FINISHED'} and not lock.active
   checks.append(dict(check='viewport default without scene camera; 75 percent front fit; current-view lock and recapture do not jump',extent=extent))
   camera=bpy.data.objects['Camera'];s.source='CAMERA';assert s.error
   assert scene.UseViewportInsteadOfCamera
   s.camera=camera;assert not s.error and scene.camera==camera and not scene.UseViewportInsteadOfCamera
   layout=Layout(context=bpy.context);ob.CAMKEYS_PT_setup.draw(PanelProxy(ob.CAMKEYS_PT_setup,layout),bpy.context)
   assert any(c.binding and getattr(c.binding.context,'name','')=='camera' for c in layout.canvas.controls.values())
   layout.canvas.park()
   obj.rotation_euler=(.2,0,.4);camera.data.shift_x=.12;camera.data.shift_y=-.08
   scene.render.resolution_x=900;scene.render.resolution_y=1600
   assert bpy.ops.camkeys.setup_snap_front()=={'FINISHED'},s.error
   from bpy_extras.object_utils import world_to_camera_view
   dg=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(dg)
   projected=[world_to_camera_view(scene,camera,evaluated.matrix_world@Vector(c)) for c in evaluated.bound_box]
   extent=max(max(abs(2*p.x-1),abs(2*p.y-1)) for p in projected)
   assert .70<extent<.80,extent
   before=camera.matrix_world.copy();assert bpy.ops.camkeys.setup_dolly_current()=={'FINISHED'},s.error
   assert lock.active and not lock.viewport_source and lock.camera==camera
   assert camera.matrix_world==before
   numeric=Numeric(camera.data.bl_rna.properties['lens'],bpy.context,presentation={'units':'mm','precision':1})
   assert abs(numeric.parse('5cm',50)-50)<1e-4 and numeric.parse('75 (mm)',50)==75
   assert bpy.ops.camkeys.setup_create()=={'FINISHED'} and s.step==3
   checks.append(dict(check='selected camera, rotated local-front mesh, shifted portrait frame, fixed camera and real native lens codec',extent=extent,lens_unit=camera.data.bl_rna.properties['lens'].unit))
   ov.unlock_here(item,bpy.context)
   constraint=camera.constraints.new('LIMIT_LOCATION');constraint.use_min_x=constraint.use_max_x=True;constraint.min_x=constraint.max_x=999
   before=camera.matrix_basis.copy()
   try:ov.snap_front(s,bpy.context,item)
   except ValueError:pass
   else:raise AssertionError('constrained camera accepted')
   assert max(abs(before[i][j]-camera.matrix_basis[i][j]) for i in range(4) for j in range(4))<1e-4
   checks.append('constrained camera rejected and original transform restored')
   camera.constraints.remove(constraint)
   lattice=bpy.data.objects.new('Setup Cage',bpy.data.lattices.new('Setup Cage'))
   scene.collection.objects.link(lattice);lattice.scale=(2,1,3);s.target=lattice
   cage=scene.mesh_object_items.add();cage.object=lattice
   bpy.context.view_layer.update();ov.snap_front(s,bpy.context,cage)
   evaluated=lattice.evaluated_get(bpy.context.evaluated_depsgraph_get())
   points=[world_to_camera_view(scene,camera,evaluated.matrix_world@Vector(c)) for c in evaluated.bound_box]
   extent=max(max(abs(2*p.x-1),abs(2*p.y-1)) for p in points)
   assert .70<extent<.80,extent
   checks.append(dict(check='lattice cage front framing',extent=extent))
  addon.unregister();result=dict(passed=True,version=bpy.app.version_string,checks=checks)
 except Exception:result=dict(passed=False,version=bpy.app.version_string,checks=checks,error=traceback.format_exc())
 Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
 bpy.app.timers.register(lambda:(bpy.ops.wm.quit_blender(),None)[1],first_interval=.1)
bpy.app.timers.register(run,first_interval=2)
