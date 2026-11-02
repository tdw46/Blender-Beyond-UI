import unittest
from beyond_ui import Layout,StyleSheet,style
from beyond_ui.value_feedback import ValueFeedback,normalize

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.ui=Layout();self.c=self.ui.canvas
        self.control=self.ui.label(text='0.000')
        self.c.arrange(200);self.time=0;self.wakes=[]
        self.c._animation_wake=lambda:self.wakes.append(self.time)
        self.f=ValueFeedback(self.c,clock=lambda:self.time);self.c.value_feedback=self.f

    def test_first_read_idle_retarget_and_exact_settle(self):
        self.f.observe(self.control,0);self.assertFalse(self.f.advance());self.assertFalse(self.wakes)
        self.time=.1;self.f.observe(self.control,.2);self.assertEqual(self.f.amount(self.control),1)
        self.time=.3;self.f.observe(self.control,.4)
        self.time=.53;self.assertGreater(self.f.amount(self.control),.9)
        self.time=.8;self.assertFalse(self.f.advance());self.assertEqual(self.f.amount(self.control),0)
        count=len(self.wakes)
        for i in range(1000):self.f.observe(self.control,.4)
        self.assertEqual(len(self.wakes),count)

    def test_disabled_readonly_values_and_zero_geometry_work(self):
        self.control.options['enabled']=False
        count=self.c.layout_count
        self.f.observe(self.control,(0,0));self.f.observe(self.control,(1,0))
        self.assertEqual(self.f.amount(self.control),1)
        self.assertEqual(self.c.layout_count,count)
        self.f.configure({'enabled':False});self.f.observe(self.control,(2,0))
        self.assertFalse(self.f.active);self.assertFalse(self.f.values)

    def test_per_control_theme_settings_and_parent_disable(self):
        style(self.ui,value_feedback={'hold':.5,'fade':.1,'role':'slider_fill'})
        self.f.observe(self.control,'0');self.f.observe(self.control,'1')
        self.time=.55;self.assertAlmostEqual(self.f.amount(self.control),.5)
        sheet=StyleSheet(value_feedback={'enabled':False});sheet.apply(self.c)
        self.assertFalse(self.f.active)
        child=Layout().canvas;child.value_feedback.parent=self.f
        c=child.label('x','value');child.value_feedback.observe(c,'0');child.value_feedback.observe(c,'1')
        self.assertFalse(child.value_feedback.active)

    def test_epsilon_hidden_clipped_and_deleted_controls(self):
        self.f.observe(self.control,0.0);self.f.observe(self.control,1e-8)
        self.assertFalse(self.wakes)
        self.f.observe(self.control,1);self.assertTrue(self.f.active)
        self.assertFalse(self.f.advance((1000,1000,10,10)))
        self.f.observe(self.control,2);self.assertFalse(self.f.active) # Quiet baseline after cull
        self.f.observe(self.control,3);self.c.park()
        self.assertFalse(self.f.active);self.assertFalse(self.f.values)
        self.c.visible=True;self.f.observe(self.control,4)
        self.c.controls.clear();self.c.invalidate();self.assertFalse(self.f.values)

    def test_invalid_settings(self):
        for value in [{'hold':float('nan')},{'fade':-1},{'role':'orange'},{'enabled':1},{'epsilon':2}]:
            with self.assertRaises(ValueError):normalize(value)

    def test_wrapping_preserves_controls_and_minimum_lanes(self):
        from beyond_ui import style
        ui=Layout();row=ui.row();style(row,scope='group',flex_wrap=True,gap=8)
        a=row.label(text='Snap to View');style(row,min_width=135)
        b=row.label(text='Bake Keyframes');style(row,min_width=135)
        ui.canvas.arrange(220);one,two=ui.canvas.controls.values()
        self.assertGreaterEqual(two.rect[1],one.rect[1]+one.rect[3]+8)
        ui.canvas.arrange(400)
        self.assertEqual(one.rect[1],two.rect[1])
        self.assertEqual(len(ui.canvas.controls),2)
