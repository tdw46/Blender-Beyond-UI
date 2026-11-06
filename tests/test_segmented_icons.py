import unittest
from beyond_ui import Layout, style
from beyond_ui.gpu.icons import layer_color


class SegmentedIcons(unittest.TestCase):
    def test_segment_style_retains_action_and_selection(self):
        ui=Layout();clicked=[]
        control=ui.group.button('choice','Choice',lambda:clicked.append(True),selected=True,menu_option=True)
        action=control.action
        style(ui,enum_style='segment',icon='BUI_LENS',font_weight='bold')
        self.assertFalse(control.options['menu_option'])
        self.assertIs(control.action,action)
        self.assertTrue(control.options['selected'])
        style(ui,enum_style='menu')
        self.assertTrue(control.options['menu_option'])
        with self.assertRaises(ValueError):style(ui,enum_style='invalid')

    def test_duotone_uses_theme_or_consumer_roles_and_retains_opacity(self):
        ink=(1,1,1,.4);native={'accent':(.5,.2,.8,1),'toggle_on':(.3,.5,.8,.7)}
        self.assertEqual(layer_color(native,'accent',ink),(.5,.2,.8,.4))
        self.assertEqual(layer_color(native,'accent_2',ink),(.3,.5,.8,.4))
        self.assertEqual(layer_color(dict(native,accent_2=(.2,.9,.5,1)),'accent_2',ink),(.2,.9,.5,.4))
