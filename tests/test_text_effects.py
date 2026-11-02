import sys, unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from beyond_ui import Layout, StyleSheet, style
from beyond_ui.text_effects import normalize
from beyond_ui.gpu.typography import draw_text

class TextEffectsTests(unittest.TestCase):
    def test_configuration_inherits_and_can_disable(self):
        base = {'text_effects': {'shadow_opacity': .1}}
        # Use the actual complete palette because sheets also derive surfaces.
        from beyond_ui.gpu.style import reference_palette
        base = dict(reference_palette(), **base)
        sheet = StyleSheet(text_effects={'outline':False})
        self.assertEqual(dict(sheet.palette(base)['text_effects']), {'outline':False, 'shadow_opacity':.1})
        ui = Layout(); c = ui.label(text='Example')
        style(ui, text_effects={'outline':False, 'shadow':False})
        self.assertEqual(dict(c.options['_inline_sheet'].palette(base)['text_effects']), {'outline':False,'shadow':False,'shadow_opacity':.1})
        for value in ({'outline':1},{'shadow_opacity':float('nan')},{'shadow_blur':6},{'shadow_offset':(9,0)},{'unknown':True}):
            with self.assertRaises(ValueError): normalize(value)

    def test_native_effects_draw_foreground_once_and_clear_font_state(self):
        blf = SimpleNamespace(SHADOW=4, shadow=Mock(),shadow_offset=Mock(),enable=Mock(),disable=Mock(),color=Mock(),draw=Mock())
        ink=(.8,.9,1,.5)
        with patch.dict(sys.modules, blf=blf):
            draw_text(3,'Hello',ink,scale=2)
            self.assertEqual(blf.draw.call_count,2)
            self.assertEqual(blf.color.call_args_list[0].args,(3,.8,.9,1,0))
            self.assertEqual(blf.color.call_args_list[1].args,(3,*ink))
            self.assertEqual(blf.shadow.call_args_list[0].args,(3,3,0,0,0,.1))
            self.assertEqual(blf.shadow_offset.call_args_list[0].args,(3,0,-2))
            blf.disable.assert_called_with(3,4)
            blf.draw.reset_mock()
            draw_text(3,'Hello',ink,{'shadow':False,'outline':False})
            self.assertEqual(blf.draw.call_count,1)

    def test_failure_and_missing_capability_do_not_leak_shadow(self):
        blf=SimpleNamespace(SHADOW=4,shadow=Mock(),shadow_offset=Mock(),enable=Mock(),disable=Mock(),color=Mock(),draw=Mock(side_effect=RuntimeError('draw failed')))
        with patch.dict(sys.modules,blf=blf):
            with self.assertRaises(RuntimeError):draw_text(3,'Hi',(1,1,1,1))
            blf.disable.assert_called_with(3,4)
        simple=SimpleNamespace(color=Mock(),draw=Mock())
        with patch.dict(sys.modules,blf=simple): draw_text(3,'Hi',(1,1,1,1))
        simple.draw.assert_called_once_with(3,'Hi')
