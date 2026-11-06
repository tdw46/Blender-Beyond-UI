import unittest
from types import SimpleNamespace
from beyond_ui import Layout,style,StyleSheet
from beyond_ui.stylesheet import accent_palette

class AccentSlots(unittest.TestCase):
    def test_slots_inherit_without_recoloring_data(self):
        base={'accent':(.8,.2,.1,1),'toggle_on':(.1,.7,.5,.7),'selected':(.1,.3,.2,.4),'text':(.9,.9,.9,1),'input':(.1,.1,.1,.6),'surfaces':{'selected':((.1,.3,.2,.4),)*2},'authored_value':(.4,.2,.8,1)}
        c=SimpleNamespace(options={'_inline_style':{'accent_slot':2}})
        p=accent_palette(base,c)
        self.assertEqual(p['slider_fill'],(.1,.7,.5,1))
        self.assertEqual(p['selected'][3],.4)
        self.assertIs(p,accent_palette(base,c))
        self.assertEqual(p['authored_value'],base['authored_value'])
        custom={**base,'accent_2':(.5,.8,.1,1)}
        self.assertEqual(accent_palette(custom,c)['slider_fill'],custom['accent_2'])
        self.assertEqual(base['accent'],(.8,.2,.1,1))
    def test_group_and_per_control_override(self):
        ui=Layout();row=ui.row();style(row,scope='group',accent_slot=2)
        a=row.label(text='A');b=row.label(text='B');style(row,accent_slot=1)
        self.assertEqual(a.options['_inline_style']['accent_slot'],2)
        self.assertEqual(b.options['_inline_style']['accent_slot'],1)
        for value in (0,9,True,1.5):
            with self.assertRaises(ValueError):style(row,accent_slot=value)
        StyleSheet(colors={'accent_1':'#ff6655','accent_2':'#66ffbb'})
