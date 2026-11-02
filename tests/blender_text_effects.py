"""Native BLF outline/shadow pixels, batched text and disabling in isolated GPU contexts."""
import bpy,blf,gpu,sys,os,json,traceback
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from capture_controls import png
from beyond_ui.gpu import typography
from beyond_ui.gpu.paint import gpu_state
from menu_motion_batch import configure
OUT=ROOT/'docs/design/qa/text-effects-v1'
OUT.mkdir(parents=True,exist_ok=True)

def run():
    font=target=None
    try:
        font=typography.Fonts();target=gpu.types.GPUOffScreen(720,160)
        batch,info=configure()
        def capture(effects,batched):
            with target.bind(),gpu_state(),gpu.matrix.push_pop(),gpu.matrix.push_pop_projection():
                fb=gpu.state.active_framebuffer_get();fb.clear(color=(.18,.2,.22,1))
                gpu.state.blend_set('ALPHA');gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix(((2/720,0,0,-1),(0,2/160,0,-1),(0,0,-1,0),(0,0,0,1))))
                from contextlib import nullcontext
                with batch() if batched else nullcontext():
                    for role,y,value,size in [('title',101,'CamKeys · Outline and shadow',28),('body',50,'Angle Sensitivity    22.5 (°)    HOW TO',25)]:
                        f=typography.face(font,role);blf.size(f,size);blf.position(f,22,y,0)
                        typography.draw_text(f,value,(.88,.92,.95,1),effects,2)
                    typography.flush_text(font)
                data=bytes(fb.read_color(0,0,720,160,4,0,'UBYTE').to_list()) if False else fb.read_color(0,0,720,160,4,0,'UBYTE')
                data.dimensions=720*160*4
                return bytes(data)
        off={'outline':False,'shadow':False}
        plain=capture(off,False);styled=capture(None,False);batched=capture(None,True)
        assert styled!=plain,'No visible native effects'
        assert styled==batched,'Native batching changed text/effects pixels'
        assert capture(off,False)==plain,'Disabling did not restore plain text'
        png(OUT/('plain-'+bpy.app.version_string.split()[0]+'.png'),720,160,plain)
        png(OUT/('styled-'+bpy.app.version_string.split()[0]+'.png'),720,160,styled)
        result={'passed':True,'version':bpy.app.version_string,'checks':['Native outline and drop-shadow pixels present','Native text batch exactly matches standalone output','Disabling restores original pixels'],'native_text_batch':info}
    except Exception: result={'passed':False,'error':traceback.format_exc()}
    finally:
        if target:target.free()
        if font is not None:font.close()
    Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(run,first_interval=1)
