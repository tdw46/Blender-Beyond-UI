import json
from pathlib import Path
import tempfile
import unittest
import zlib
from beyond_ui import Artwork, ArtworkLibrary, Layout, header, heading
from beyond_ui.gpu import icons
from beyond_ui.layout_recording import Tape

class ArtworkTests(unittest.TestCase):
    def test_native_headers_keep_fallback_icon_and_labels(self):
        seen=[]
        class Native:
            def row(self,**kw):return self
            def column(self,**kw):return self
            def label(self,**kw):seen.append(kw)
        header(Native(),'Studio',subtitle='Camera-driven',icon=Artwork('test:logo','CAMERA_DATA'))
        self.assertEqual(seen[0]['icon'],'CAMERA_DATA')
        self.assertEqual([v['text'] for v in seen[1:]],['Studio','Camera-driven'])

    def test_recorded_headers_retain_controls_and_size(self):
        def make():
            tape=Tape();header(tape.root,'Studio',subtitle='Camera-driven',icon=Artwork('test:logo'),size=40)
            heading(tape.root,'Geometry',icon=Artwork('test:mesh'),size=22)
            return tape
        tape=make();ui=Layout();tape.play(ui);ui.canvas.panel_layout=True
        for width in (220,360,520):
            ui.canvas.arrange(width)
            controls=list(ui.canvas.controls.values())
            self.assertGreaterEqual(controls[0].rect[2],40)
            self.assertGreaterEqual(controls[0].rect[3],40)
            self.assertLessEqual(controls[-1].rect[0]+controls[-1].rect[2],width)
            self.assertEqual(controls[0].options['icon_size'],40)
        count=len(ui.canvas.controls)
        self.assertTrue(tape.patch_display(make()))
        self.assertEqual(len(ui.canvas.controls),count)

    def test_explicit_load_validation_and_idempotent_close(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'pixels.zlib').write_bytes(zlib.compress(bytes([255,0,0,255])*4))
            data={'sources':{'s':{'size':[2,2],'file':'pixels.zlib'}},'icons':{'logo':{'source':'s','rect':[0,0,2,2],'fallback':'CAMERA_DATA'}}}
            p=root/'pack.json';p.write_text(json.dumps(data))
            lib=ArtworkLibrary('test.art');lib.load(p);lib.load(p)
            self.assertEqual(lib['logo'].token,'test.art:logo')
            self.assertEqual(len(icons._artwork['test.art']['textures']),0)
            lib.close();lib.close();self.assertNotIn('test.art',icons._artwork)
            data['icons']['logo']['rect']=[0,0,3,2];p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):lib.load(p)
            self.assertFalse(lib.loaded)

    def test_header_cross_axis_alignment_and_configurable_elements(self):
        for alignment, factor in [('start',0),('center',.5),('end',1)]:
            ui=Layout();header(ui,'Studio',subtitle='Camera-driven expressions',icon=Artwork('test:logo'),
                              size=56, align_items=alignment, divider=True, divider_height=32,
                              title_style={'font_size':18,'line_height':25,'color':'#ABCDEF'},
                              subtitle_style={'font_size':12,'line_height':19}, text_gap=3,
                              divider_style={'divider_width':2,'color':'#FFFFFF66'})
            ui.canvas.panel_layout=True;ui.canvas.arrange(360)
            icon,line,title,subtitle=ui.canvas.controls.values()
            self.assertEqual(title.options['font_size'],18)
            self.assertEqual(subtitle.options['color_role'],'muted')
            self.assertEqual(line.options['divider_width'],2)
            self.assertTrue(line.options['vertical'])
            text_height=subtitle.rect[1]+subtitle.rect[3]-title.rect[1]
            self.assertAlmostEqual(title.rect[1]-icon.rect[1],(icon.rect[3]-text_height)*factor)
            self.assertAlmostEqual(line.rect[1]-icon.rect[1],(icon.rect[3]-line.rect[3])*factor)

    def test_header_centering_survives_narrow_wrapping_and_recording(self):
        tape=Tape();header(tape.root,'Forced Perspective',subtitle='Lens, depth and camera effects',
                           icon=Artwork('test:lens'),size=72,divider=True,
                           title_style={'font_size':20,'line_height':28},subtitle_style={'font_size':14,'line_height':23})
        ui=Layout();tape.play(ui);ui.canvas.panel_layout=True
        for width in (240,280,400,520):
            ui.canvas.arrange(width)
            icon,line,title,subtitle=ui.canvas.controls.values()
            text_center=(title.rect[1]+subtitle.rect[1]+subtitle.rect[3])/2
            self.assertAlmostEqual(icon.rect[1]+icon.rect[3]/2,text_center)
            self.assertAlmostEqual(line.rect[1]+line.rect[3]/2,text_center)
            self.assertLessEqual(subtitle.rect[0]+subtitle.rect[2],width)
            for control in (title,subtitle):
                self.assertGreaterEqual(control.rect[3],len(control.options["_wrapped_lines"])*control.options["line_height"])
            self.assertGreaterEqual(subtitle.rect[1],title.rect[1]+title.rect[3])
