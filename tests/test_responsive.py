import unittest
from beyond_ui import Layout, style
from beyond_ui.responsive import normalize_rules, resolve


class ResponsiveStyleTests(unittest.TestCase):
    def test_roundtrip_preserves_owner_and_base(self):
        ui=Layout(); group=ui.column(); control=group.label(text='Persistent')
        style(group,scope='group',gap=12,font_size=14,
              responsive=[{'max_width':280,'style':{'gap':6,'font_size':12}}])
        ui.canvas.arrange(400)
        original=control.options['_inline_style'].copy()
        ui.canvas.arrange(240)
        self.assertEqual(group.group.options['gap'],6)
        self.assertEqual(control.options['_inline_style']['font_size'],12)
        self.assertFalse(resolve(ui.canvas,250))
        ui.canvas.arrange(400)
        self.assertEqual(group.group.options['gap'],12)
        self.assertEqual(control.options['_inline_style'],original)
        self.assertIs(ui.canvas.controls[control.key],control)

    def test_nested_breakpoints_restore_in_reverse_order(self):
        ui=Layout(); parent=ui.column(); child=parent.column(); c=child.label(text='Nested')
        style(parent,scope='group',font_size=14,
              responsive=[{'max_width':300,'style':{'font_size':12}}])
        style(child,scope='group',responsive=[{'max_width':260,'style':{'font_size':10}}])
        for width,expected in ((400,14),(240,10),(280,12),(400,14),(240,10),(400,14)):
            ui.canvas.arrange(width)
            self.assertEqual(c.options['_inline_style']['font_size'],expected)

    def test_invalid_rules_fail_before_mutation(self):
        for rule in (None,[{'style':None}],[{'max_width':-1}],
                     [{'style':{'unknown':1}}],[{'style':{'responsive':[]}}],
                     [{'min_width':300,'max_width':200}]):
            with self.assertRaises(ValueError): normalize_rules(rule)

    def test_hidden_control_cancels_capture_and_reappears(self):
        ui=Layout(); group=ui.column(); c=group.label(text='Hide')
        style(group,scope='group',responsive=[{'max_width':280,'style':{'display':'none'}}])
        from types import SimpleNamespace
        c.options['widget']=SimpleNamespace(blur=lambda:None)
        ui.canvas.arrange(400); ui.canvas.keyboard_focus=c
        ui.canvas.arrange(240)
        self.assertIsNone(ui.canvas.keyboard_focus)
        ui.canvas.arrange(400)
        self.assertNotEqual(group.group.options.get('display'),'none')

    def test_named_fit_state_and_restore(self):
        ui=Layout();group=ui.column();c=group.label(text='Fit')
        style(group,scope='group',gap=10,responsive=[
            {'when':'planes.compact','style':{'gap':4,'font_size':12}}])
        self.assertTrue(resolve(ui.canvas,400,fit_states={'planes.compact':True}))
        self.assertEqual(group.group.options['gap'],4)
        self.assertFalse(resolve(ui.canvas,400,fit_states={'planes.compact':True}))
        self.assertTrue(resolve(ui.canvas,400,fit_states={}))
        self.assertEqual(group.group.options['gap'],10)
        self.assertNotIn('font_size',c.options.get('_inline_style',{}))
        for when in (True,'',23,'nodot'):
            with self.assertRaises(ValueError):normalize_rules([{'when':when,'style':{}}])
