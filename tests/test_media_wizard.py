import sys, unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from beyond_ui import Layout, wizard
from beyond_ui.media import MediaLibrary
from beyond_ui.widgets.media import MediaWidget

class Array:
    def astype(self,kind):return self
    def __imul__(self,value):return self

class Provider:
    def __init__(self):self.token=0;self.reads=0;self.closed=False
    def frame(self,key,elapsed):
        def pixels():self.reads+=1;return bytes(16)
        return self.token,2,2,pixels
    def close(self):self.closed=True

class MediaWizardTests(unittest.TestCase):
    def test_visible_cache_and_hide_lifetime(self):
        provider=Provider();library=MediaLibrary(provider,budget_bytes=1024)
        layout=Layout();widget=MediaWidget(library,'clip',layout.canvas)
        clock=[1.0];uploads=[];wakes=[]
        layout.canvas._animation_wake=lambda:wakes.append(True)
        gpu=NS(types=NS(Buffer=lambda *a:None,GPUTexture=lambda *a,**k:uploads.append(a) or object()))
        np=NS(frombuffer=lambda *a,**k:Array(),uint8=0,float32=0)
        with patch('beyond_ui.media.monotonic',lambda:clock[0]),patch.dict(sys.modules,{'gpu':gpu,'numpy':np}):
            library.leases[widget]=clock[0]
            self.assertEqual(library._tick(),.08333333333333333)
            library._tick();self.assertEqual(provider.reads,1);self.assertEqual(len(uploads),1)
            provider.token=1;library._tick();self.assertEqual(len(uploads),2)
            provider.token=0;library._tick();self.assertEqual(len(uploads),2)
            self.assertTrue(wakes)
            layout.canvas.park();self.assertIsNone(library._tick());self.assertFalse(library.leases)
            layout.canvas.visible=True;library.leases[widget]=1;clock[0]=2
            self.assertIsNone(library._tick());self.assertFalse(library.leases)

    def test_failure_is_observable_and_does_not_poll_forever(self):
        p=Provider();p.frame=lambda *args:(_ for _ in ()).throw(ValueError('missing clip'))
        library=MediaLibrary(p);layout=Layout();widget=MediaWidget(library,'broken',layout.canvas)
        library.leases[widget]=__import__('time').monotonic()
        with patch.dict(sys.modules,{'gpu':NS()}):
            self.assertIsNone(library._tick())
        self.assertIn('missing clip',library.errors['broken'])

    def test_media_responsive_height_and_no_scene_controls(self):
        layout=Layout();widget=MediaWidget(MediaLibrary(Provider()),'clip',layout.canvas,height=80)
        self.assertEqual(widget.dimensions(11,90),(90,80))
        self.assertEqual(widget.dimensions(22,180),(180,160))
        self.assertFalse(widget.route(None));self.assertEqual(widget.all_children(),())

    def test_wizard_readonly_progress_and_motion_disable(self):
        state={};layout=Layout(state=state)
        wizard(layout,0,title='Start',step=1,steps=3)
        body=wizard(layout,1,title='Next',step=2,steps=3)
        self.assertIsNotNone(body);self.assertTrue(layout.canvas.page_motion.positions)
        layout.canvas.animation.enabled=False
        self.assertEqual(layout.canvas.page_motion.position('slide',0),0)
        self.assertFalse(layout.canvas.page_motion.advance())
        with self.assertRaises(ValueError):wizard(layout,2,title='Bad',step=4,steps=3)

    def test_choice_card_reflows_without_changing_font_size(self):
        from beyond_ui.widgets.choice_card import ChoiceCard
        layout=Layout()
        card=ChoiceCard(layout.canvas,'Forced Perspective','Control proportions of parts of your character/scene independent of true camera FOV.',None,None)
        wide=card.dimensions(320,11)[1]
        narrow=card.dimensions(210,11)[1]
        self.assertGreater(narrow,wide)
        self.assertEqual(card.font_size,12)
        self.assertEqual(card.dimensions(640,22)[1],wide*2)

    def test_caption_and_wizard_options_are_native_safe(self):
        from beyond_ui.media import media
        layout=Layout();lib=MediaLibrary(Provider())
        media(layout,lib,'clip',caption='Watch a dolly zoom',caption_size=10)
        widget=list(layout.canvas.controls.values())[-1].options['widget']
        self.assertEqual(widget.caption,'Watch a dolly zoom')

    def test_multilingual_wrapping_preserves_copy(self):
        from beyond_ui.text_wrap import wrap_text
        self.assertEqual(wrap_text('Choose a workflow', 10, len), ('Choose a', 'workflow'))
        self.assertEqual(wrap_text('形状を視点に合わせて変化', 5, len), ('形状を視点', 'に合わせて', '変化'))
        self.assertEqual(wrap_text('first\nsecond', 20, len), ('first', 'second'))
        self.assertEqual(wrap_text('abcdef', 3, len), ('abc', 'def'))

    def test_badge_preserves_user_data(self):
        layout=Layout()
        with patch.object(Layout, '_text', side_effect=lambda text, text_ctxt='', translate=True: text if not translate else 'Translated'):
            layout.beyond_badge('Next', translate=False)
        self.assertEqual(list(layout.canvas.controls.values())[-1].options['widget'].text, 'Next')
