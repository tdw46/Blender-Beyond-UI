"""Windowed NVIDIA/Metal fixture: copied scene, live outputs, warm CPU and idle."""
import bpy, gpu, os, sys, json, time, traceback, importlib.util, statistics, ctypes
from pathlib import Path
from mathutils import Quaternion

source = Path(os.environ['BEYOND_UI_CAMKEYS_ROOT']).resolve()
spec = importlib.util.spec_from_file_location('camkeys_qa', source/'__init__.py', submodule_search_locations=[str(source)])
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
state = {'step': 0, 'draw_ms': [], 'paint_ms': [], 'outputs': [], 'checks': [], 'capture_ms': [], 'drives': 0}

def memory():
    if sys.platform != 'win32':
        return {}
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in ('peak_working', 'working', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle), ctypes.byref(counters), counters.cb)
    return {'working_mib': counters.working/1048576, 'private_mib': counters.private/1048576}

def resources():
    from camkeys_qa._vendor.beyond_ui.gpu import glass
    runtime = addon.__beyond_ui_integration__.ui._runtime
    return dict(memory=memory(), canvases=sum(len(v) for v in runtime.canvases.values()),
                host_records=sum(len(h.records) for h in runtime.hosts.values()),
                glass_owners=len(glass._owners), glass_productions=sum(v.get('productions',0) for v in glass._owners.values()),
                draws=len(state['draw_ms']), paints=len(state['paint_ms']))

def stats(values):
    ordered=sorted(values)
    return dict(samples=len(values), median_ms=statistics.median(values), p95_ms=ordered[min(len(values)-1,int(len(values)*.95))], max_ms=max(values)) if values else {}

def finish(error=None):
    config = addon.__beyond_ui_integration__.ui
    runtime = config._runtime if config else None
    result = dict(passed=error is None, error=error, checks=state['checks'], version=bpy.app.version_string,
                  backend=gpu.platform.backend_type_get(), renderer=gpu.platform.renderer_get(),
                  addon_source=addon.__file__, status=runtime.status() if runtime else None, saved=False,
                  warm_draw=stats(state['draw_ms'][5:]), warm_paint=stats(state['paint_ms'][5:]),
                  idle=state.get('idle'), disabled_idle=state.get('disabled_idle'), resources=state.get('samples'), outputs=state['outputs'],
                  timing_scope='Dependency and live-binding correctness, not a performance measurement', authored_calls=state.get('authors'))
    if runtime:
        addon.unregister()
        from camkeys_qa._vendor.beyond_ui.gpu import glass
        result['glass_owners_after_unregister']=len(glass._owners)
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result, indent=2, default=str))
    bpy.ops.wm.quit_blender()

def labels(canvas):
    for control in canvas.controls.values():
        yield control.label
        widget=control.options.get('widget')
        for child in getattr(widget,'live_canvases',()):
            yield from labels(child)

def tick():
    try:
        n=state['step'];rt=addon.__beyond_ui_integration__.ui._runtime
        area=state['area'];region=state['region'];obj=state['object'];scene=bpy.context.scene
        panel=addon.auto_load.get_module('ui_panel')
        main=panel.CAMKEYS_PT_camkeys_main;link=panel.CAMKEYS_PT_camkeys_linking
        def visible(cls):
            return next(c for _,c in rt.canvases[cls].values() if c.visible)
        def check():
            assert not rt.errors and not rt.input_errors,rt.status()
            assert all(h.bridge for h in rt.hosts.values())
        if n==0:
            state['authors']={}
            for cls,fn in tuple(rt.draw_functions.items()):
                def counted(*args,_cls=cls,_fn=fn,**kw):
                    state['authors'][_cls.__name__]=state['authors'].get(_cls.__name__,0)+1
                    return _fn(*args,**kw)
                rt.draw_functions[cls]=counted
            rt.refresh();region.active_panel_category='Hardware QA';area.tag_redraw()
        elif n==1:
            check();state['initial']=state['authors'][link.__name__];state['outputs']=[]
            state['rotation']=area.spaces.active.region_3d.view_rotation.copy()
        elif 2<=n<=15:
            rv=area.spaces.active.region_3d
            rv.view_rotation=Quaternion((0,0,1),(n-2)*.08)@state['rotation'];rv.update()
            area.tag_redraw()
            state['outputs'].append([b.value for b in obj.data.shape_keys.key_blocks])
            child_labels=list(labels(visible(link)))
            assert any(f'{obj.data.shape_keys.key_blocks[i.shapekey].value:.3f}' in child_labels for i in obj.angle_items if i.shapekey in obj.data.shape_keys.key_blocks),child_labels
        elif n==16:
            check();assert state['authors'][link.__name__]==state['initial'],state['authors']
            assert len({tuple(v) for v in state['outputs']})>2
            state['checks'].append('Moving viewport and live values reuse panel authoring; labels remain current')
            item=obj.angle_items[obj.angle_items_index]
            item.falloff_type='SHARP' if item.falloff_type=='LINEAR' else 'LINEAR'
        elif n==17:
            check();assert state['authors'][link.__name__]>state['initial']
            state['checks'].append('Falloff label change invalidates authored content')
            scene.camkeys_props.show_help_cam_angles=not scene.camkeys_props.show_help_cam_angles
        elif n==18:
            check();obj.angle_items_index=(obj.angle_items_index+1)%len(obj.angle_items)
        elif n==19:
            check();state['item']=obj.angle_items[obj.angle_items_index]
            state['item'].distance_only=True
        elif n==20:
            check();assert any(c.options.get('widget') and c.options['widget'].name=='CAMKEYS_UL_distance_stops' for c in visible(link).controls.values())
            state['item'].distance_only=False
            state['checks'].append('Help, active item and distance mode refresh their controls')
        elif n==21:
            check();obj.angle_items.move(2,3)
        elif n==22:
            check()
            w=next(c.options['widget'] for c in visible(link).controls.values() if c.options.get('widget') and c.options['widget'].name=='CAMSHAPEMATIC_UL_angle_items')
            assert all(w.source.valid_item(entry[2]) for entry in w.row_map.values())
            state['checks'].append('Same-size external row reorder keeps exact current ownership')
            obj.angle_items.remove(len(obj.angle_items)-1)
        elif n==23:
            check();state['checks'].append('Deletion refreshes without stale-owner errors')
            region.active_panel_category='CamKeys'
            with bpy.context.temp_override(window=state['window'],area=area,region=region):
                for _ in range(50):bpy.ops.view2d.scroll_up()
        elif n==24:
            check();visible(main);state['main_count']=state['authors'][main.__name__]
        elif 25<=n<=28:
            check();assert state['authors'][main.__name__]==state['main_count']
            area.spaces.active.lens+=1
        elif n==29:
            check();assert state['authors'][main.__name__]==state['main_count']
            state['checks'].append('Unchanged main panel authoring skipped while editable lens remains live')
            scene.UseViewportInsteadOfCamera=False
        elif n==30:
            check();assert state['authors'][main.__name__]>state['main_count']
            state['checks'].append('Camera/viewport branch change rebuilds correct controls')
            finish();return None
        area.tag_redraw();return advance(.18 if 2<=n<=15 else .5)
    except Exception:
        finish(traceback.format_exc());return None

def advance(delay):
    state['step']+=1
    return delay

def start():
    try:
        # Put the live list first only in this disposable profile, to expose it.
        from camkeys_qa import ui_panel
        ui_panel.CAMKEYS_PT_camkeys_linking.bl_order=-10
        addon.register()
        linking=addon.auto_load.get_module('ui_panel').CAMKEYS_PT_camkeys_linking
        bpy.utils.unregister_class(linking)
        linking.bl_category='Hardware QA'
        bpy.utils.register_class(linking)
        bpy.ops.wm.open_mainfile(filepath=os.environ['BEYOND_UI_CRASH_FILE'],load_ui=False,use_scripts=False)
        bpy.app.timers.register(configure,first_interval=2)
    except Exception:
        finish(traceback.format_exc())
    return None

def configure():
    try:
        scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'
        w=bpy.context.window or bpy.context.window_manager.windows[0]; area=next(a for a in w.screen.areas if a.type=='VIEW_3D')
        area.spaces.active.show_region_ui=True
        region=next(r for r in area.regions if r.type=='UI')
        item=next(item for item in scene.mesh_object_items if item.object and item.object.angle_items and item.object.data.shape_keys)
        scene.mesh_object_items_index=list(scene.mesh_object_items).index(item)
        bpy.context.view_layer.objects.active=item.object; item.object.select_set(True)
        with bpy.context.temp_override(window=w,area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
            scene.UseViewportInsteadOfCamera=True
            bpy.context.window_manager.EnableCamKeys=True
        runtime=addon.__beyond_ui_integration__.ui._runtime
        capture=addon.utils.capture_camkeys_update_state
        drive=addon.utils._drive_camkeys_outputs
        def timed_capture(*args,**kwargs):
            begin=time.perf_counter()
            try:return capture(*args,**kwargs)
            finally:state['capture_ms'].append((time.perf_counter()-begin)*1000)
        def counted_drive(*args,**kwargs):
            state['drives']+=1
            return drive(*args,**kwargs)
        addon.utils.capture_camkeys_update_state=timed_capture
        addon.utils._drive_camkeys_outputs=counted_drive
        original=runtime.draw
        def draw(*args,**kwargs):
            begin=time.perf_counter()
            try:return original(*args,**kwargs)
            finally:state['draw_ms'].append((time.perf_counter()-begin)*1000)
        runtime.draw=draw
        from camkeys_qa._vendor.beyond_ui.hosts.panel import PanelHost
        paint=PanelHost._paint
        def timed_paint(self,*args,**kwargs):
            begin=time.perf_counter()
            try:return paint(self,*args,**kwargs)
            finally:state['paint_ms'].append((time.perf_counter()-begin)*1000)
        PanelHost._paint=timed_paint
        state.update(window=w,area=area,region=region,object=item.object)
        bpy.app.timers.register(tick,first_interval=4)
    except Exception:
        finish(traceback.format_exc())
    return None

bpy.app.timers.register(start,first_interval=1)
