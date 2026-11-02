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
                  timing_scope='Python panel authoring and paint CPU time, not GPU frame time')
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
        n=state['step']; runtime=addon.__beyond_ui_integration__.ui._runtime
        w=state['window']; area=state['area']; region=state['region']; obj=state['object']
        if n==0:
            region.active_panel_category='Hardware QA'
            region.tag_redraw()
        elif n==1:
            assert all(h.bridge is not None for h in runtime.hosts.values()), runtime.status
            state['checks'].append('All six native adapters admitted; no native panel fallback')
            state['samples']=[resources()]
            state['rotation']=area.spaces.active.region_3d.view_rotation.copy()
        elif 2<=n<=31:
            values={item.shapekey:round(obj.data.shape_keys.key_blocks[item.shapekey].value,5) for item in obj.angle_items if item.shapekey in obj.data.shape_keys.key_blocks}
            state['outputs'].append(values)
            shown=[]
            for cache in runtime.canvases.values():
                for _,canvas in cache.values():
                    if canvas.visible: shown.extend(labels(canvas))
            state.setdefault('matching_samples',0)
            if any(f'{value:.3f}' in shown for value in values.values()): state['matching_samples']+=1
            state['last_labels']=shown
            rv=area.spaces.active.region_3d
            rv.view_rotation=Quaternion((0,0,1),(n-2)*.065) @ state['rotation']
            rv.update(); area.tag_redraw()
        elif n==32:
            assert len({json.dumps(v,sort_keys=True) for v in state['outputs']})>2, 'Viewport movement did not change shape keys'
            assert state['matching_samples']>10, ('Live value labels not refreshed',state['matching_samples'],state['last_labels'])
            assert not runtime.errors and not runtime.input_errors, runtime.status
            state['checks'].append('Viewport movement changes real Uraraka shape keys and visible list values')
            state['samples'].append(resources())
            return advance(3)
        elif n==33:
            state['idle_start']=(time.perf_counter(),time.process_time(),resources())
            state['idle_capture_start']=(len(state['capture_ms']),state['drives'])
            return advance(30)
        elif n==34:
            wall,cpu,before=state['idle_start']; elapsed=time.perf_counter()-wall; consumed=time.process_time()-cpu
            after=resources(); state['samples'].append(after)
            state['idle']=dict(seconds=elapsed,cpu_seconds=consumed,one_core_percent=100*consumed/elapsed,machine_percent=100*consumed/elapsed/(os.cpu_count() or 1),before=before,after=after,
                               draw_delta=after['draws']-before['draws'],paint_delta=after['paints']-before['paints'])
            capture_start,drive_start=state['idle_capture_start']
            state['idle']['capture']=stats(state['capture_ms'][capture_start:])
            state['idle']['drive_calls']=state['drives']-drive_start
            assert after['glass_owners']==before['glass_owners'] and after['canvases']==before['canvases'], 'Idle resource owners grew'
            assert not runtime.errors and not runtime.input_errors, runtime.status
            state['checks'].append('30-second untouched idle sample; stable retained resource owners and no runtime errors')
            bpy.context.window_manager.EnableCamKeys=False
            return advance(2)
        elif n==35:
            state['disabled_start']=(time.perf_counter(),time.process_time())
            return advance(5)
        elif n==36:
            wall,cpu=state['disabled_start']; elapsed=time.perf_counter()-wall; consumed=time.process_time()-cpu
            state['disabled_idle']=dict(seconds=elapsed,cpu_seconds=consumed,machine_percent=100*consumed/elapsed/(os.cpu_count() or 1))
            finish(); return None
        return advance(.15 if 2<=n<=31 else 1)
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
